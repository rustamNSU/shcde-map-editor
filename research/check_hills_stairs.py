"""Read-only ref12 geometry, stair and connectivity investigation."""
from pathlib import Path
import json,csv
import numpy as np
from PIL import Image
from maptool import MapFile,require
from research.analyze_references import grids,hist,bounds,XY,sha,compare,objects,ENTITY_LAYOUTS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/hills-stairs-2026-09-19'
SOURCE=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps/ref_12_ladders_and_hills_400.map')
FIELDS=(3003,3037,3005,3045,3006,3007,3043,3021,3030,3012)

def main():
    raw=SOURCE.read_bytes();m=MapFile(raw);g=grids(m)
    require(all(s['error'] is None for s in m.sections),'Decode error')
    OUT.mkdir(exist_ok=True);snap=OUT/SOURCE.name
    if snap.exists():require(snap.read_bytes()==raw,'Different snapshot')
    else:snap.write_bytes(raw)
    inside=(g[3003]&0x30)==0
    masks={'walls':inside&((g[3003]&0x100)!=0),'stairs':inside&((g[3003]&0x800)!=0),
           'raised_terrain':inside&(g[3045]>8)&((g[3003]&0x900)==0)}
    lookup={tuple(p):i for i,p in enumerate(XY.tolist())}
    r=dict(source=str(SOURCE),sha256=sha(raw),groups={},entities={k:objects(m,k,v) for k,v in ENTITY_LAYOUTS.items()})
    for name,mask in masks.items():
        left=set(np.flatnonzero(mask).tolist());groups=[]
        while left:
            i=left.pop();ids=[i];todo=[i]
            while todo:
                i=todo.pop();x,y=XY[i]
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    j=lookup.get((int(x+dx),int(y+dy)))
                    if j in left:left.remove(j);todo.append(j);ids.append(j)
            ids=np.array(sorted(ids))
            groups.append(dict(cells=len(ids),bounds=bounds(ids),layers={str(sid):hist(g[sid][ids]) for sid in FIELDS}))
        r['groups'][name]=sorted(groups,key=lambda c:(c['bounds'][0],c['bounds'][1]))
    target=inside&((g[3005]!=8)|(g[3045]!=8)|((g[3003]&0x900)!=0))
    with (OUT/'cells.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['index','x','y',*FIELDS])
        for i in np.flatnonzero(target):w.writerow([int(i),*XY[i].tolist(),*[int(g[sid][i]) for sid in FIELDS]])
    r['height_delta_match']={name:dict(cells=int(mask.sum()),matches=int(np.count_nonzero(mask & (g[3006].astype(int)==g[3005].astype(int)-g[3045].astype(int))))) for name,mask in masks.items()}
    r['regions']=[]
    for region in np.unique(g[3021][inside]):
        mask=inside&(g[3021]==region);ids=np.flatnonzero(mask)
        r['regions'].append(dict(id=int(region),cells=len(ids),bounds=bounds(ids),logic=hist(g[3003][mask]),height=hist(g[3005][mask])))
    im=Image.new('RGB',(800,800),'#202025');pix=im.load()
    for i,(x,y) in enumerate(XY):
        if not inside[i]:continue
        h=int(g[3005][i]);c=(min(255,70+h),min(255,65+h),min(255,40+h))
        if g[3003][i]&0x80:c=(160,60,180)
        if masks['walls'][i]:c=(255,70,70)
        if masks['stairs'][i]:c=(40,220,255)
        pix[int(x),int(y)]=c
    im.crop((190,190,610,610)).resize((840,840),Image.Resampling.NEAREST).save(OUT/'geometry.png')
    (OUT/'diff_ref11.json').write_text(json.dumps(compare(ROOT/'output/walls-2026-09-19/ref_11_walls_400.map',snap),indent=2),encoding='utf-8')
    require(SOURCE.read_bytes()==raw,'Source changed');r['source_unchanged']=True
    (OUT/'findings.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
    for name,groups in r['groups'].items():
        print(name)
        for c in groups:print(c['cells'],c['bounds'],{k:v for k,v in c['layers'].items() if k in ('3003','3005','3045','3006','3021')})
    print('delta',r['height_delta_match'])
    print('entities',{k:v['nonempty_records'] for k,v in r['entities'].items()})

if __name__=='__main__':main()
