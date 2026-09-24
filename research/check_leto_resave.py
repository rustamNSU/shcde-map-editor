"""Archive and compare the editor-resaved Leto map; never modify inputs."""
import argparse
from collections import Counter
from pathlib import Path
import struct

import numpy as np

from research.analyze_savegame import comparison, csv_rows, inspect, sha, write_json
from maptool import MapFile, require

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / 'output/leto-save-2026-09-19/snapshots/leto vs fbi 10.map'
AFTER = Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps/leto vs fbi 10.map')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    raw_a, raw_b = BEFORE.read_bytes(), AFTER.read_bytes()
    a, b = MapFile(raw_a), MapFile(raw_b)
    for label, raw, m in [('before', raw_a, a), ('after', raw_b, b)]:
        require(m.rebuild() == raw, 'Roundtrip failed')
        require(all(s['error'] is None for s in m.sections), 'Decode error')
        (args.output / (label + '.map')).write_bytes(raw)
        write_json(args.output / (label + '.manifest.json'), m.manifest())
    x, xu, xw, _ = inspect(a, {})
    y, yu, yw, yr = inspect(b, {})
    aa, bb = ({u['global_id']: u for u in rows} for rows in (xu, yu))
    require(len(aa) == len(xu) and len(bb) == len(yu), 'Duplicate unit global IDs')
    common = sorted(aa.keys() & bb.keys())
    changes = []
    for gid in common:
        fields = [k for k in aa[gid] if aa[gid][k] != bb[gid][k]]
        if fields:
            changes.append(dict(global_id=gid, slot=aa[gid]['slot'], type=aa[gid]['type'],
                                changes={k: [aa[gid][k], bb[gid][k]] for k in fields}))
    cleared = []
    for gid in sorted(aa.keys() - bb.keys()):
        u = aa[gid]
        offset = u['slot'] * 1168
        def value(m, at, fmt):
            return struct.unpack_from(fmt, m.section(3015)['decoded'], offset + at)[0]
        cleared.append(dict(slot=u['slot'], global_id=gid, type=u['type'], owner=u['owner'],
            before_state=u['state'], after_state=value(b, 0x8c, '<H'),
            hp_candidate=value(a, 0x3c8, '<I'), max_hp_candidate=value(a, 0x3cc, '<I'),
            hp_percent_candidate=value(a, 0x2d4, '<H'),
            path_flags_candidate=u['path_flags_candidate'],
            after_record_all_zero=not any(b.section(3015)['decoded'][offset:offset+1168])))
    diffs = comparison(a, b)
    headers = {key: [a.headers[key]['hex'], b.headers[key]['hex']]
               for key in a.headers if a.headers[key]['hex'] != b.headers[key]['hex']}
    players = []
    for old, new in zip(x['players'], y['players']):
        changed = {key: [old[key], new[key]] for key in old if old[key] != new[key]}
        if changed:
            players.append(dict(player=old['player'], changes=changed))
    summary = dict(before_sha256=sha(raw_a), after_sha256=sha(raw_b),
        sizes=[len(raw_a), len(raw_b)], sections=Counter(r['status'] for r in diffs),
        entity_counts=[x['entity_counts'], y['entity_counts']],
        removed_unit_records=len(cleared), new_unit_records=len(bb.keys()-aa.keys()),
        cleared_types=Counter(r['type'] for r in cleared),
        cleared_owners=Counter(r['owner'] for r in cleared),
        cleared_zero_hp=sum(r['hp_candidate'] == r['hp_percent_candidate'] == 0 for r in cleared),
        cleared_records_all_zero=sum(r['after_record_all_zero'] for r in cleared),
        surviving_units=len(common),
        survivor_field_change_counts={key: sum(aa[g][key] != bb[g][key] for g in common) for key in xu[0]},
        header_changes=headers, menu_unchanged=x['menu'] == y['menu'],
        save_extension_payload_unchanged=a.save_extension['hex'] == b.save_extension['hex'],
        preview_palette_changed_bytes=sum(v != w for v, w in zip(a.preview[:512], b.preview[:512])),
        preview_index_changed_bytes=sum(v != w for v, w in zip(a.preview[512:], b.preview[512:])),
        worker_links=[len(xw), len(yw)], reciprocal_after=y['worker_links_reciprocal'],
        worker_assignments_unchanged=xw == yw,
        storage_mismatches_excluding_null_gold=[r for r in yr if not r['equal'] and r['good'] not in ('null','gold')],
        player_changes=players)
    # Inspect the actual height exception rather than claiming the terrain was identical.
    for sid in (3005, 3045, 3037, 3008):
        before, after = (np.frombuffer(m.section(sid)['decoded'], dtype='u1') for m in (a, b))
        summary['section_%s_changed_bytes' % sid] = int(np.count_nonzero(before != after))
    csv_rows(args.output / 'cleared_units.csv', cleared)
    csv_rows(args.output / 'after_units.csv', yu)
    csv_rows(args.output / 'after_players.csv', y['players'])
    write_json(args.output / 'unit_changes.json', changes)
    write_json(args.output / 'section_diff.json', diffs)
    write_json(args.output / 'after_analysis.json', y)
    require(BEFORE.read_bytes() == raw_a and AFTER.read_bytes() == raw_b, 'Source changed')
    summary['source_integrity'] = 'Both source hashes rechecked unchanged'
    write_json(args.output / 'findings.json', summary)
    print(__import__('json').dumps(summary, indent=2))


if __name__ == '__main__':
    main()
