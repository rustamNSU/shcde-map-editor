"""Reference-derived tree brushes; grid and entity edits share one undo command."""
import json,struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from semantics import tile_index,tile_xy
from .buildings import BuildingService,I,H,relocate
from .services import EntityService
from .geometry import SUPPORTED_MAP_SIZES

@lru_cache(maxsize=1)
def tree_catalog():
    return json.loads((Path(__file__).parent/'assets/templates/trees.json').read_text())['items']

class TreeService:
    def __init__(self,document): self.document=document

    def anchors(self,indices):
        ids=np.unique(np.asarray(indices,dtype=np.int64))
        if np.any(ids<0) or np.any(ids>=self.document.geometry.count): raise ValueError('Invalid tree cells')
        g=self.document.geometry
        # Space actual stroke cells, rather than intersecting a fixed world grid.
        # A one-cell line at x/y not divisible by four used to vanish completely.
        blocked=np.zeros((800,800),dtype=bool)
        anchors=[]
        for i in ids:
            x,y=int(g.x[i]),int(g.y[i])
            if blocked[y,x]:continue
            anchors.append(i)
            blocked[max(0,y-3):min(800,y+4),max(0,x-3):min(800,x+4)]=True
        return np.asarray(anchors,dtype=np.int64)

    def paint(self,indices,kind='2',scatter=True):
        d=self.document; p=tree_catalog()[str(kind)]
        indices=np.unique(np.asarray(indices,dtype=np.int64))
        if np.any(indices<0) or np.any(indices>=d.geometry.count): raise ValueError('Invalid tree cells')
        if d.size not in SUPPORTED_MAP_SIZES: raise ValueError('Trees require a supported native map size')
        candidates=[tile_xy(int(i)) for i in (self.anchors(indices) if scatter else indices)]
        raw=bytes.fromhex(p['data']); count=0
        unit_tiles={r['tile_id'] for r in EntityService(d).records('units')}
        with d.transaction('Plant '+p['name']):
            table=bytearray(d.section(1014)['decoded'])
            free=iter(int(s) for s in np.flatnonzero(~np.any(np.frombuffer(table,dtype='u1').reshape(-1,156),axis=1)) if s)
            gid=I(d.section(1035)['decoded'],0)
            gid=max([gid]+[r['global_id']+1 for k in ('buildings','units','vegetation') for r in EntityService(d).records(k)])
            for x,y in candidates:
                cells=[(x+dx,y+dy) for dx,dy in p['cells']]
                if any(not (0<=xx<800 and 0<=yy<800) for xx,yy in cells): continue
                ids=np.array([tile_index(xx,yy) for xx,yy in cells])
                if not np.all(d.geometry.playable[ids]) or unit_tiles.intersection(ids): continue
                if any(np.any(d.grid(s)[ids]) for s in (3004,3010,3012)): continue
                if not np.all(d.grid(3003)[ids]==0x8000): continue
                if not np.all((d.grid(3005)[ids]==8)&(d.grid(3045)[ids]==8)): continue
                slot=next(free,None)
                if slot is None: raise ValueError('No clean vegetation slots remain')
                rec=relocate(raw,[dict(offset=0x5c,kind='<HH',scale=8),dict(offset=0x62,kind='<HH',scale=1),dict(offset=0x68,kind='tile')],x-p['anchor'][0],y-p['anchor'][1])
                struct.pack_into('<I',rec,0x4c,gid); gid+=1
                table[slot*156:(slot+1)*156]=rec
                for sid,values in p['grids'].items(): d.change(int(sid),ids,values,'Tree surroundings')
                d.change(3004,[tile_index(x,y)],slot,'Tree slot'); count+=1
            if count:
                d.replace_section(1014,table,'Tree records')
                d.replace_section(1035,struct.pack('<I',gid),'Next global ID')
        return dict(planted=count,experimental=True)

    def remove(self,x,y):
        d=self.document; slot=int(d.grid(3004)[tile_index(x,y)])
        if not slot: return dict(removed=0)
        table=bytearray(d.section(1014)['decoded']); rec=table[slot*156:(slot+1)*156]
        p=tree_catalog().get(str(H(rec,0x46)))
        if p is None: raise ValueError('This vegetation belongs to a different tool, such as an orchard')
        x,y=H(rec,0x62),H(rec,0x64)
        ids=np.array([tile_index(x+dx,y+dy) for dx,dy in p['cells']])
        if any(np.any(d.grid(s)[ids]) for s in (3010,3012)) or set(map(int,d.grid(3004)[ids]))-{0,slot}:
            raise ValueError('Tree surroundings overlap another object')
        if any(not np.array_equal(d.grid(int(s))[ids],v) for s,v in p['grids'].items()):
            raise ValueError('Tree surroundings differ from the isolated reference; cannot safely clear them')
        with d.transaction('Remove '+p['name']):
            for sid,val in ((3003,0x8000),(3007,16),(3030,255),(3021,1)): d.change(sid,ids,val,'Clear tree surroundings')
            d.change(3004,np.flatnonzero(d.grid(3004)==slot),0,'Clear tree slot')
            table[slot*156:(slot+1)*156]=bytes(156); d.replace_section(1014,table,'Remove tree record')
        return dict(removed=1)
