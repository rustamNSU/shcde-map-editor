"""Extract isolated vegetation records and their local grids; originals read only."""
import hashlib,json
from pathlib import Path
import numpy as np
from maptool import MapFile
from semantics import ENTITY_LAYOUTS,entity_report,tile_index

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'output/trees-2026-09-20/ref_13_trees.map'
raw=source.read_bytes(); m=MapFile(raw)
names={1:'Chestnut',2:'Oak',3:'Pine',4:'Birch',5:'Shrub 1A',10:'Shrub 2A',16:'Shrub 3A',17:'Shrub 3B',18:'Shrub 3C',19:'Shrub 3D'}
items={}
for r in entity_report(m,ENTITY_LAYOUTS['vegetation'])['records']:
    radius=1 if r['type'] in (1,2,3,4) else 0
    cells=[(x,y) for y in range(-radius,radius+1) for x in range(-radius,radius+1)]
    ids=[tile_index(r['x']+x,r['y']+y) for x,y in cells]
    items[str(r['type'])]=dict(name=names[r['type']],anchor=[r['x'],r['y']],cells=cells,
        data=m.section(1014)['decoded'][r['slot']*156:(r['slot']+1)*156].hex(),
        grids={str(sid):np.frombuffer(m.section(sid)['decoded'],dt)[ids].tolist()
               for sid,dt in [(3003,'<u4'),(3007,'<u2'),(3030,'u1'),(3021,'<u2')]})
(ROOT/'editor/assets/templates/trees.json').write_text(json.dumps(dict(source=source.name,sha256=hashlib.sha256(raw).hexdigest(),items=items),indent=2))
