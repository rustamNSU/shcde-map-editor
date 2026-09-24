"""Read-only texture-layer investigation on copied reference maps."""
import json
import hashlib
from pathlib import Path
import numpy as np
from maptool import MapFile
from semantics import tile_index

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'output/references-2026-09-19'

def histogram(a):
    v, n = np.unique(a, return_counts=True)
    return {str(int(k)): int(c) for k, c in zip(v, n)}

def main():
    reports, arrays = {}, {}
    for path in sorted((DATA / 'maps').glob('ref_*.map')):
        raw = path.read_bytes()
        m = MapFile(raw)
        grids = {s['id']: np.frombuffer(s['decoded'], dtype={1:'u1',2:'<u2',4:'<u4'}[s['size']//320800]).copy()
                 for s in m.sections if s['size'] in (320800,641600,1283200)}
        inside = (grids[3003] & 0x30) == 0
        masks = {'interior':inside, 'plain': inside & (grids[3003]==0x8000) & (grids[3037]==0) & (grids[3005]==8),
                 'earth_stones':inside & (grids[3037]==2), 'sand':inside & (grids[3037]==64),
                 'iron':inside & ((grids[3003]&0x80000)!=0), 'stone':inside & ((grids[3003]&0x20000)!=0)}
        reports[path.stem] = {'sha256':hashlib.sha256(raw).hexdigest(), 'groups':{}}
        for name, mask in masks.items():
            if not mask.any(): continue
            reports[path.stem]['groups'][name] = {'count':int(mask.sum()),'layers':{str(sid):histogram(a[mask]) for sid,a in grids.items()}}
        arrays[path.stem] = grids
    base = arrays['ref_00_base_500']
    comparisons = {}
    for name, g in arrays.items():
        common = ((base[3003]&0x30)==0) & ((g[3003]&0x30)==0)
        comparisons[name] = {str(sid): {'changed_common':int(np.count_nonzero(a[common]!=base[sid][common])),
                                      'changed_all':int(np.count_nonzero(a!=base[sid]))} for sid,a in g.items()}
    # Identical metadata-free cell sample, at explicit coordinates.
    samples = {}
    for name,g in arrays.items():
        samples[name] = {f'{x},{y}':{str(sid):int(a[tile_index(x,y)]) for sid,a in g.items()}
                         for x,y in [(390,390),(391,390),(392,390),(400,400),(401,400)]}
    target = DATA / 'texture_analysis.json'
    target.write_text(json.dumps({'maps':reports,'versus_base500':comparisons,'samples':samples},ensure_ascii=False,indent=2),encoding='utf-8')
    for name in ['ref_00_base_500','ref_07_earth&stones_texture_400','ref_07_sand_400','ref_06_iron_400','ref_07_stones_400']:
        print(name)
        for group,r in reports[name]['groups'].items():
            if group=='interior':continue
            print(group,r['count'], {sid: (len(h),list(h.items())[:8]) for sid,h in r['layers'].items() if len(h)>1 or any(int(k) for k in h)})
    print('Saved',target)

if __name__=='__main__':main()
