"""Layer-specific, in-memory rectangular map clipboard; no entity references copied."""
from dataclasses import dataclass
import numpy as np
from .services import terrain_eligible

FIELDS={'surface':(3037,3008,3003,3007),'height':(3005,3045),'noise':(3008,)}

def eligible(document,ids,layer):
    d=document
    ok=d.geometry.playable[ids].copy()
    if layer=='noise':return ok
    # Surface clipboard retains terrain flags but not water depth/base height;
    # keep water conversion in TerrainService instead of creating partial water.
    ok &= terrain_eligible(d,ids,height=layer=='height')
    if layer=='surface':ok &= (d.grid(3003)[ids]&np.uint32(0x300001))==0
    return ok

@dataclass
class MapClipboard:
    layer:str
    width:int
    height:int
    dx:np.ndarray
    dy:np.ndarray
    values:dict

    @classmethod
    def copy(cls,document,selection,layer):
        if layer not in FIELDS:raise ValueError('Unsupported clipboard layer')
        x,y,w,h=selection
        ids=document.geometry.rectangle(x,y,w,h)
        ids=ids[eligible(document,ids,layer)]
        if not len(ids):raise ValueError('Selection has no supported cells to copy on this layer')
        g=document.geometry
        return cls(layer,w,h,(g.x[ids]-x).copy(),(g.y[ids]-y).copy(),
                   {sid:document.grid(sid)[ids].copy() for sid in FIELDS[layer]})

    def paste(self,document,x,y):
        g=document.geometry;xx=self.dx+x;yy=self.dy+y
        positions=np.flatnonzero((xx>=0)&(xx<800)&(yy>=0)&(yy<800))
        ids=g.index_grid[yy[positions],xx[positions]]
        valid=ids>=0;positions=positions[valid];ids=ids[valid]
        valid=eligible(document,ids,self.layer);positions=positions[valid];ids=ids[valid]
        changed=0
        with document.transaction('Paste '+self.layer):
            for sid,values in self.values.items():
                pasted=values[positions]
                if sid==3003:
                    pasted=(pasted&np.uint32(0xffffdfff))|(document.grid(3003)[ids]&np.uint32(0x2000))
                changed+=document.change(sid,ids,pasted,'Paste '+self.layer)
            if self.layer=='height':
                changed+=document.change(3003,ids,document.grid(3003)[ids]&np.uint32(0xffffff7f),'Clear previous cliff flags')
        return dict(eligible_cells=len(ids),skipped_cells=self.width*self.height-len(ids),changed_field_values=changed)
