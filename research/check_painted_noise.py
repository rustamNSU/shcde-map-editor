"""Compare user-painted zero-noise map with the exact generated baseline."""
from pathlib import Path
import csv
import json
import numpy as np
from maptool import MapFile, require
from research.analyze_references import grids, compare, hist, bounds, XY, sha

ROOT = Path(__file__).resolve().parents[1]
LIVE = Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps/etest_noise_00000_textures.map')
BASE = ROOT/'output/noise-tests-2026-09-19/etest_noise_00000.map'
OUT = ROOT/'output/noise-painted-2026-09-19'

def main():
    OUT.mkdir(exist_ok=True)
    raw = LIVE.read_bytes()
    copy = OUT/LIVE.name
    if copy.exists():
        require(copy.read_bytes() == raw, 'Snapshot differs; use a new output directory')
    else:
        copy.write_bytes(raw)
    a, b = MapFile(BASE.read_bytes()), MapFile(raw)
    require(all(s['error'] is None for s in b.sections), 'Decode error')
    aa, bb = grids(a), grids(b)
    inside = (aa[3003]&0x30)==0
    painted = inside & ((aa[3003]!=bb[3003]) | (aa[3037]!=bb[3037]))
    result = dict(source=str(LIVE),sha256=sha(raw),baseline_sha256=sha(BASE.read_bytes()),
                  noise_section_identical=a.section(3008)['decoded']==b.section(3008)['decoded'],
                  noise_changes_all=int(np.count_nonzero(aa[3008]!=bb[3008])),
                  interior_noise=hist(bb[3008][inside]), painted_cells=int(painted.sum()),
                  painted_noise=hist(bb[3008][painted]),groups=[])
    delta3036=aa[3036]!=bb[3036]
    result['layer3036_changes_outside_material_mask']=int(np.count_nonzero(delta3036 & ~painted))
    result['layer3036_changes_plain_unchanged_height']=int(np.count_nonzero(delta3036 & inside & ~painted & (aa[3005]==bb[3005]) & (aa[3045]==bb[3045])))
    tuples = np.stack([bb[3003][painted],bb[3037][painted]],axis=1)
    for logic,surface in np.unique(tuples,axis=0):
        mask=painted & (bb[3003]==logic) & (bb[3037]==surface)
        ids=np.flatnonzero(mask)
        result['groups'].append(dict(logic=hex(int(logic)),surface=int(surface),count=len(ids),
                                    bounds=bounds(ids),noise=hist(bb[3008][mask]),
                                    samples=[dict(x=int(XY[i,0]),y=int(XY[i,1]),index=int(i),noise=int(bb[3008][i])) for i in ids[:3]],
                                    other_layers={str(sid):hist(bb[sid][mask]) for sid in (3005,3045,3007,3009)}))
    diff=compare(BASE,copy)
    (OUT/'diff.json').write_text(json.dumps(diff,indent=2),encoding='utf-8')
    result['changed_sections']=[{'id':s['id'],'bytes':s.get('changed_bytes'), 'cells':s.get('changed_cells')} for s in diff['sections'] if s.get('changed_bytes',1)]
    with (OUT/'painted_cells.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f)
        w.writerow(['index','x','y','logic_before','logic_after','surface_before','surface_after','noise_before','noise_after'])
        for i in np.flatnonzero(painted):
            w.writerow([int(i),*XY[i].tolist(),hex(int(aa[3003][i])),hex(int(bb[3003][i])),int(aa[3037][i]),int(bb[3037][i]),int(aa[3008][i]),int(bb[3008][i])])
    require(LIVE.read_bytes()==raw,'Source changed during analysis')
    result['source_unchanged']=True
    (OUT/'findings.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('groups','changed_sections')},indent=2))

if __name__=='__main__':main()
