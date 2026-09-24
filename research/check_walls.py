"""Read-only isolated wall reference inspection."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from maptool import MapFile,require
from research.analyze_references import grids,hist,bounds,XY,sha,objects,ENTITY_LAYOUTS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/walls-2026-09-19'
SOURCE=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps/ref_11_walls_400.map')

def main():
    raw=SOURCE.read_bytes();m=MapFile(raw);g=grids(m)
    require(all(s['error'] is None for s in m.sections),'Decode failed')
    OUT.mkdir(exist_ok=True)
    snap=OUT/SOURCE.name
    if snap.exists():require(snap.read_bytes()==raw,'Snapshot changed')
    else:snap.write_bytes(raw)
    wall=(g[3003]&0x100)!=0
    index={tuple(p):i for i,p in enumerate(XY.tolist())}
    left=set(np.flatnonzero(wall).tolist());components=[]
    while left:
        seed=left.pop();ids=[seed];todo=[seed]
        while todo:
            i=todo.pop();x,y=XY[i]
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                j=index.get((int(x+dx),int(y+dy)))
                if j in left:left.remove(j);todo.append(j);ids.append(j)
        components.append(ids)
    report=dict(source=str(SOURCE),sha256=sha(raw),wall_cells=int(wall.sum()),components=[],
                entities={k:objects(m,k,v) for k,v in ENTITY_LAYOUTS.items()},layers={})
    for ids in sorted(components,key=lambda a:(bounds(np.array(a))[0],bounds(np.array(a))[1])):
        report['components'].append(dict(cells=len(ids),bounds=bounds(np.array(ids)),
            layers={str(sid):hist(a[ids]) for sid,a in g.items()}))
    inside=(g[3003]&0x30)==0
    for sid,a in g.items():
        nonzero=np.flatnonzero((a!=0)&inside)
        report['layers'][str(sid)]=dict(interior_hist=hist(a[inside]),wall_hist=hist(a[wall]),
                                      offwall_hist=hist(a[inside&~wall]),nonzero_bounds=bounds(nonzero))
    for sid in (3006,3049,3020,3043):
        a=g[sid];ids=np.flatnonzero((a!=0)&inside)
        report['layers'][str(sid)]['samples']=[dict(x=int(XY[i,0]),y=int(XY[i,1]),value=int(a[i]),wall=bool(wall[i])) for i in ids[:30]]
    im=Image.new('RGB',(800,800),'#25252a');p=im.load()
    for i,(x,y) in enumerate(XY):
        if inside[i]:p[int(x),int(y)]=(150,135,100)
        if wall[i]:p[int(x),int(y)]=(255,100,90)
        elif g[3006][i]:p[int(x),int(y)]=(80,120,255)
    im.save(OUT/'wall_mask.png')
    require(SOURCE.read_bytes()==raw,'Source changed')
    report['source_unchanged']=True
    (OUT/'findings.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('walls',report['wall_cells'],'components',len(components))
    for c in report['components']:
        print(c['cells'],c['bounds'],{k:v for k,v in c['layers'].items() if k in ('3003','3005','3045','3006','3049','3020','3043','3012')})
    for sid in ('3006','3049','3020','3043'):
        print(sid,report['layers'][sid])
    print('entities',{k:v['nonempty_records'] for k,v in report['entities'].items()})

if __name__=='__main__':main()
