"""Layer-specific, in-memory rectangular map clipboard; no entity references copied."""
from dataclasses import dataclass
import numpy as np
from .services import EntityService

FIELDS={'surface':(3037,3008,3003,3007),'height':(3005,3045),'noise':(3008,)}

def eligible(document,ids,layer):
    d=document
    ok=d.geometry.playable[ids].copy()
    if layer=='noise':return ok
    logic=d.grid(3003)[ids]
    if layer=='surface':
        ok &= np.isin(logic,[0x8000,0x28000,0x88000,0x20008000])
        ok &= (d.grid(3005)[ids]==8)&(d.grid(3045)[ids]==8)
    else:
        ok &= np.isin(logic,[0,0x80,0x8000,0x8080,0x10000000,0x10000080,0x10008000,0x10008080])
        ok &= d.grid(3005)[ids]==d.grid(3045)[ids]
    for sid in (3012,3010,3004):ok &= d.grid(sid)[ids]==0
    units=[r['tile_id'] for r in EntityService(d).records('units') if r['coordinates_match']]
    if units:ok &= ~np.isin(ids,units)
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
                changed+=document.change(sid,ids,values[positions],'Paste '+self.layer)
        return dict(eligible_cells=len(ids),skipped_cells=self.width*self.height-len(ids),changed_field_values=changed)
