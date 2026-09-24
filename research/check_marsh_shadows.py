"""Read-only marsh topology and candidate lighting-grid investigation."""
from pathlib import Path
import json
from collections import Counter, deque
import numpy as np
from PIL import Image,ImageDraw
from maptool import MapFile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/marsh-shadows-2026-09-19'
REF=ROOT/'output/references-2026-09-19/maps'

def histogram(a):
    return {str(int(k)):int(v) for k,v in zip(*np.unique(a,return_counts=True))}

def main():
    OUT.mkdir(exist_ok=True)
    paths=[ROOT/'examples/1x1 - sword no lions.map',REF/'ref_08_march_400.map',REF/'ref_07_oasis_400.map',
           REF/'ref_09_vege_palm_400.map',REF/'ref_09_vege_coconut_palm_400.map',REF/'ref_09_vege_olivee_tree_400.map',
           REF/'ref_10_p1_or_red_castle_400.map',REF/'ref_00_base_500.map']
    reports={}
    for path in paths:
        m=MapFile(path.read_bytes());legacy=m.version<200;N=400 if legacy else 800;shift=0 if legacy else 2000
        xy=np.array([(x,y) for y in range(N) for x in range((N-2*min(y+1,N-y))//2,(N+2*min(y+1,N-y))//2)])
        grid={}
        for sid,dtype in [(1003,'<u4'),(1037,'u1'),(1005,'u1'),(1006,'u1'),(1007,'<u2'),(1008,'<u2'),(1009,'<u2'),(1036,'<u2'),(1049,'u1')]:
            grid[sid]=np.frombuffer(m.section(sid+shift)['decoded'],dtype=dtype)
        logic=grid[1003];swamp=(logic&0x20000000)!=0;oasis=(grid[1037]&16)!=0
        masks={'marsh':swamp & ((logic&0x80000000)==0),'oasis':oasis,'light_nonzero':grid[1006]!=0}
        report={'version':m.version,'axis':N,'groups':{}}
        for name,mask in masks.items():
            ids=np.flatnonzero(mask);pts=xy[ids]
            report['groups'][name]={'cells':len(ids),'bounds':[int(pts[:,0].min()),int(pts[:,1].min()),int(pts[:,0].max()),int(pts[:,1].max())] if len(ids) else None,
                'layers':{str(sid+shift):histogram(a[mask]) for sid,a in grid.items()}}
            if name=='marsh':
                cells=set(map(tuple,pts.tolist()));left=set(cells);components=[]
                while left:
                    seed=left.pop();todo=[seed];comp=[seed]
                    while todo:
                        x,y=todo.pop()
                        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                            p=(x+dx,y+dy)
                            if p in left:left.remove(p);todo.append(p);comp.append(p)
                    components.append(len(comp))
                report['groups'][name]['four_neighbor_component_sizes']=dict(Counter(components))
                report['groups'][name]['four_neighbor_counts']=dict(Counter(sum((x+dx,y+dy) in cells for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]) for x,y in cells))
        nonzero=np.flatnonzero(grid[1006])
        report['light_samples']=[{'x':int(xy[i,0]),'y':int(xy[i,1]),'value':int(grid[1006][i])} for i in nonzero[:80]]
        reports[path.stem]=report
        im=Image.new('RGB',(N,N),'#191b20');pix=im.load()
        for i,(x,y) in enumerate(xy):
            c=(166,142,100)
            if logic[i]&0x30:c=(30,30,35)
            if oasis[i]:c=(45,180,70)
            if masks['marsh'][i]:c=(235,45,165)
            if logic[i]&0x80000000:c=(40,40,40)
            pix[int(x),int(y)]=c
        im.save(OUT/(path.stem+'_terrain.png'))
        if legacy:im.crop((140,140,260,260)).resize((720,720),Image.Resampling.NEAREST).save(OUT/'sword_center.png')
    (OUT/'findings.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    for name,r in reports.items():
        print(name)
        for group,g in r['groups'].items():
            print(group,g['cells'],g['bounds'],g.get('four_neighbor_component_sizes'),g.get('four_neighbor_counts'))
            if group=='marsh':print('layers',{k:v for k,v in g['layers'].items() if int(k)%2000 != 1008})
        if 'vege' in name:print('light',r['light_samples'])

if __name__=='__main__':main()
