"""Derive cross-checkable findings from saved surveys and original reference copies."""
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from research.analyze_references import XY, grids, sha, write_json
from maptool import MapFile, u32, require
from semantics import tile_index

ROOT = Path(__file__).resolve().parents[1] / 'output/references-2026-09-19'


def load(name):
    return MapFile((ROOT / 'maps' / (name + '.map')).read_bytes())


def player_links(m):
    b = m.section(2022)['decoded']
    require(len(b) == 9 * 0x583C, 'Player array length')
    result = []
    for player in range(9):
        start = player * 0x583C
        u = lambda o: u32(b, start + o)
        groups = {}
        for name, off in [('keep', 0x94), ('first_stockpile', 0xBC), ('campground_candidate', 0x1D4)]:
            group = dict(zip(('slot', 'x', 'y', 'tile_id'), struct.unpack_from('<4I', b, start + off)))
            if group['slot']:
                group['coordinate_match'] = tile_index(group['x'], group['y']) == group['tile_id']
                groups[name] = group
        if groups:
            result.append(dict(player=player, housing=u(0x74), links=groups))
    return result


def composite(m, survey):
    records = survey['objects']['buildings']['records']
    require(len(records) == 9, 'Expected isolated starting complex')
    keep = next(r for r in records if r['type'] == 41)
    require(all(r['owner'] == keep['owner'] for r in records), 'Mixed ownership')
    owner = keep['owner']
    actual = []
    for rec in records:
        require(rec['coordinates_match'], 'Object coordinate mismatch')
        require(rec['world_x'] == rec['x'] * 8 and rec['world_y'] == rec['y'] * 8, 'World scale mismatch')
        require(rec['referenced_cells'] == rec['footprint_side'] ** 2, 'Footprint link count mismatch')
        actual.append(dict(slot=rec['slot'], type=rec['type'], owner=rec['owner'],
                           dx=rec['x']-keep['x'], dy=rec['y']-keep['y'],
                           side=rec['footprint_side'], tile_id=rec['tile_id'],
                           referenced_cells=rec['referenced_cells']))
    links = player_links(m)
    require(len(links) == 1 and links[0]['player'] == owner, 'Player ownership link mismatch')
    byslot = {r['slot']:r for r in records}
    for group in links[0]['links'].values():
        require(group['coordinate_match'], 'Player coordinate mismatch')
        require(group['slot'] in byslot, 'Dangling player object reference')
        group['target_type'] = byslot[group['slot']]['type']
    units = survey['objects']['units']['records']
    require(len(units) == 1 and units[0]['type'] == 55, 'Expected one lord')
    require(units[0]['owner'] == owner and units[0]['controller'] == owner, 'Lord ownership mismatch')
    require(units[0]['coordinates_match'] and units[0]['referenced_cells'] == 1, 'Lord coordinate/link mismatch')
    return dict(parts=actual, players=links, lord=units[0])


def main():
    surveys = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'survey').glob('*.json')) if '.manifest.' not in p.name]
    findings = dict(maps=len(surveys), baseline_geometry=[], materials=[], trees=[], complexes=[],
                    source_history='User: some variants started fresh, others replaced/deleted previous objects.')
    # Validate interior-mask geometry on all maps, not just a diagram.
    cache = {}
    manifests = [json.loads(p.read_text()) for p in (ROOT/'survey').glob('*.manifest.json')]
    all_ids = sorted({s['id'] for m in manifests for s in m['sections']})
    coverage = []
    for sid in all_ids:
        rows = [s for m in manifests for s in m['sections'] if s['id'] == sid]
        coverage.append(dict(id=sid, present=len(rows), decoded=len([r for r in rows if not r['error']]),
                             lengths=sorted({r['size'] for r in rows}),
                             decoded_variants=len({r.get('sha256_decoded') for r in rows})))
    findings['section_coverage'] = coverage
    findings['constant_sections'] = [r['id'] for r in coverage if r['decoded_variants'] == 1]
    for s in surveys:
        name = Path(s['file']).stem
        m = load(name)
        g = grids(m)
        side = s['size'] - 4
        offset = (800 - side) // 2
        yy = XY[:, 1].astype(np.int32) - offset
        count = 2 * np.minimum(yy+1, side-yy)
        left = (800-count)//2
        expected = (yy >= 0) & (yy < side) & (XY[:,0] >= left) & (XY[:,0] < left+count)
        observed = (g[3003] & 0x30) == 0
        require(np.array_equal(expected, observed), 'Interior geometry mismatch: '+name)
        findings['baseline_geometry'].append(dict(file=s['file'], map_size=s['size'],
                                                 interior_side=side, cells=int(observed.sum()),
                                                 expected_cells=side*(side+2)//2, exact_mask_match=True))
        interior = np.flatnonzero(observed)
        # Display actual correlated tuples; filenames do not stand in for measurements.
        states = np.stack([g[i][interior] for i in (3003,3037,3005,3045)], axis=1)
        keys, counts = np.unique(states, axis=0, return_counts=True)
        tuples = [dict(logic=int(k[0]), logic_hex=hex(int(k[0])), surface=int(k[1]),
                       height=int(k[2]), default_height=int(k[3]), cells=int(n))
                  for k,n in zip(keys,counts) if tuple(k)!=(32768,0,8,8)]
        findings['materials'].append(dict(file=s['file'], nondefault_states=tuples))
        if 'ref_09' in name:
            records = s['objects']['vegetation']['records']
            require(len(records) == 1, 'Tree count mismatch')
            tree = records[0]
            require(tree['coordinates_match'] and tree['referenced_cells'] == 1, 'Tree linkage mismatch')
            require(g[3004][tree['tile_id']] == tree['slot'], 'Tree slot mismatch')
            require(g[3003][tree['tile_id']] == 0xB000, 'Tree tile flag mismatch')
            tree_flags = np.flatnonzero((g[3003] & 0x2000)!=0)
            offsets = sorted((int(XY[i,0])-tree['x'],int(XY[i,1])-tree['y']) for i in tree_flags)
            findings['trees'].append(dict(file=s['file'], record=tree, proximity_offsets=offsets))
        if 'ref_10' in name:
            findings['complexes'].append(dict(file=s['file'], **composite(m,s)))
        if name in ['ref_08_march_400','ref_08_oil_400','ref_08_beach_400','ref_08_river_400','ref_08_ford_400']:
            cache[name] = {sid:g[sid].copy() for sid in (3003,3037,3005,3045)}
    marsh, pitch = cache['ref_08_march_400'], cache['ref_08_oil_400']
    diff = marsh[3003] != pitch[3003]
    require(int(diff.sum())==2589, 'Pitch patch size mismatch')
    require(np.all((marsh[3003][diff] ^ pitch[3003][diff]) == 0x80000000), 'Pitch bit mismatch')
    require(all(np.array_equal(marsh[s],pitch[s]) for s in (3037,3005,3045)), 'Pitch unexpectedly changes other base layers')
    findings['pitch_over_marsh'] = dict(changed_cells=int(diff.sum()), xor='0x80000000',
                                      surface_and_heights_unchanged=True)
    beach, river, ford = [cache[n] for n in ('ref_08_beach_400','ref_08_river_400','ref_08_ford_400')]
    findings['water_history'] = dict(beach_river_default_height_identical=np.array_equal(beach[3045],river[3045]),
                                     river_zero_default_height_cells=int((river[3045]==0).sum()),
                                     ford_height_zero=int((ford[3005]==0).sum()),
                                     ford_default_height_eight=int((ford[3045]==8).sum()))
    controls=[]
    for p in (ROOT/'pairs').glob('*.json'):
        d=json.loads(p.read_text(encoding='utf-8'))
        if d['right'] in ('ref_01_resave_500.map','ref_03_hill_map_description_400.map'):
            controls.append(d)
    findings['control_pairs'] = controls
    write_json(ROOT/'findings.json',findings)
    print(json.dumps(dict(maps=len(surveys),sections=len(coverage),constant=len(findings['constant_sections']),
                          geometry_verified=len(findings['baseline_geometry']),trees=len(findings['trees']),
                          complexes=len(findings['complexes'])),indent=2))


if __name__ == '__main__':
    main()
