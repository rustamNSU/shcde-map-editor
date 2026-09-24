"""User-authorized height-only experiments. No derived-layer claims."""
from pathlib import Path
import json
import numpy as np
from maptool import MapFile,require
from research.analyze_references import grids,XY,sha

ROOT=Path(__file__).resolve().parents[1]
MAPS=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps')
OUT=ROOT/'output/height-tests-2026-09-19'

def main():
    source=MAPS/'ref_00_base_400.map';raw=source.read_bytes();m=MapFile(raw);g=grids(m)
    inside=(g[3003]&0x30)==0
    require(int(inside.sum())==78804,'Not expected 400 interior')
    require(np.all(g[3003][inside]==0x8000) and np.all(g[3037]==0),'Not empty ordinary earth')
    require(np.all(g[3005][inside]==8) and np.all(g[3045][inside]==8),'Not flat base height8')
    require(not any(np.any(g[s][inside]) for s in (3004,3010,3012)),'Objects present')
    x,y=XY[:,0].astype(int),XY[:,1].astype(int)
    square=(x>=375)&(x<=424)&(y>=375)&(y<=424)
    require(int(square.sum())==2500 and np.all(inside[square]),'Invalid square')
    abrupt=g[3005].copy();abrupt[square]=130
    # Chebyshev distance gives four planar slopes and a square plateau cap.
    distance=np.maximum(np.maximum(375-x,x-424),np.maximum(375-y,y-424))
    distance=np.maximum(distance,0)
    smooth=g[3005].copy();ramp=inside&(distance<=61)
    smooth[ramp]=np.maximum(8,130-2*distance[ramp]).astype('u1')
    steps=g[3005].copy();strips=[]
    for d in range(1,31):
        sx=310+6*(d-1);points=[]
        for k in range(8):
            sy=396+k;mask=(x==sx)&(y==sy);z=8+(7-k)*d
            require(int(mask.sum())==1 and np.all(inside[mask]),'Invalid stair coordinate')
            steps[mask]=z;points.append(dict(x=sx,y=sy,z=z))
        strips.append(dict(step=d,points=points))
    cases=[('etest_disc_plato.map',abrupt),('etest_smooth_plato.map',smooth),('etest_height_steps_01_30.map',steps)]
    for name,_ in cases:require(not (MAPS/name).exists() and not (OUT/name).exists(),'Destination exists')
    require(not (OUT/'manifest.json').exists(),'Manifest exists')
    prepared=[]
    for name,height in cases:
        base=g[3045].copy();base[inside]=height[inside]
        data=m.rebuild({3005:height.tobytes(),3045:base.tobytes()});check=MapFile(data)
        require(all(s['error'] is None for s in check.sections),'Readback error')
        require(check.preview==m.preview and check.trailing==m.trailing,'Nonheight metadata changed')
        for s in m.sections:
            if s['id'] not in (3005,3045):require(check.section(s['id'])['raw']==s['raw'],'Unrelated section changed')
        require(check.section(3005)['decoded']==height.tobytes() and check.section(3045)['decoded']==base.tobytes(),'Height mismatch')
        require(np.array_equal(height[~inside],g[3005][~inside]),'Outside height changed')
        prepared.append((name,data,dict(changed_cells=int(np.count_nonzero(height!=g[3005])),min_height=int(height[inside].min()),max_height=int(height[inside].max()))))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/source.name).write_bytes(raw)
    manifest=dict(source=str(source),source_sha256=sha(raw),changed_sections=[3005,3045],
                  preserved='All other section payloads and compression bytes, including material, noise, flags, connectivity,3006 and preview. Catalog offsets/lengths necessarily rebuilt.',
                  plateau=dict(x=[375,424],y=[375,424],cells=2500,height=130,base_height=8),
                  smooth=dict(drop_per_outward_ring=2,rings_to_base=61),strips=strips,maps=[])
    for name,data,stats in prepared:
        for folder in (OUT,MAPS):
            with (folder/name).open('xb') as f:f.write(data)
            require((folder/name).read_bytes()==data,'Disk mismatch')
        manifest['maps'].append(dict(name=name,sha256=sha(data),**stats))
    require(source.read_bytes()==raw,'Source changed');manifest['source_unchanged']=True
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest['maps'],indent=2))

if __name__=='__main__':main()
