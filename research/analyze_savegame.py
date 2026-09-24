"""Read-only research of the renamed Leto save and related local snapshots.

Writes only a new evidence directory. Runtime-derived field names are candidates
unless cross-validated; never rewrites a game map or save.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import struct

import numpy as np

from maptool import MapFile, require, u32
from semantics import analyze, tile_index

GAME = Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition')
STATS = Path('C:/repositories/shcde-stats-rust')
EXTENDER = Path('C:/repositories/shcde-script-extender')
GOODS = ('null wood_logs wood raw_hops stone cow_hides iron raw_pitch pitch wheat '
         'bread cheese meat apples ale gold flour bows crossbows spears pikes '
         'maces swords leather_armour metal_armour').split()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def csv_rows(path, rows):
    if rows:
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def inspect(m, names):
    result = analyze(m)
    buildings = result['entities']['buildings']['records']
    units = result['entities']['units']['records']
    bb, ub, pb = (m.section(sid)['decoded'] for sid in (4013, 3015, 2022))
    require(len(pb) == 9 * 0x583c, 'Unexpected player stride/count')
    by_building = {b['slot']: b for b in buildings}
    rows = []
    checks = Counter()
    for unit in units:
        off = unit['slot'] * 1168
        h = lambda at: struct.unpack_from('<H', ub, off + at)[0]
        i = lambda at: u32(ub, off + at)
        row = dict(slot=unit['slot'], type=unit['type'],
                   type_name=names.get(unit['type'], 'unknown'), state=unit['state'],
                   owner=i(0x80), controller=ub[off + 0x96], global_id=unit['global_id'])
        for label, xo, io in [('current', 0xc4, 0xd4), ('target_candidate', 0xc8, 0xd8),
                              ('previous_candidate', 0xcc, 0xdc), ('next_candidate', 0xe0, 0xe4)]:
            x, y, index = h(xo), h(xo + 2), i(io)
            try:
                matches = tile_index(x, y) == index
            except ValueError:
                matches = False
            row.update({label + '_x': x, label + '_y': y, label + '_tile_id': index,
                        label + '_matches': matches})
            checks[label + '_matches'] += matches
            checks[label + '_all_zero'] += x == y == index == 0
        row.update(path_flags_candidate=h(0xf6), movement_substep_candidate=h(0xf8),
                   path_index_candidate=h(0xfa), path_length_candidate=h(0xfc),
                   building_slot_candidate=h(0x338), building_gid_candidate=i(0x368))
        b = by_building.get(row['building_slot_candidate'])
        row['building_pair_matches'] = bool(b and row['building_gid_candidate'] == b['global_id'])
        row['current_grid_points_to_this_slot'] = unit['anchor_reference'] == unit['slot']
        rows.append(row)
    by_unit = {u['slot']: u for u in rows}
    worker_links = []
    for b in buildings:
        for offset, fmt in ((0x19e, '<H'), (0x1a0, '<H'), (0x1a2, '<H'), (0x1a4, '<I')):
            slot = struct.unpack_from(fmt, bb, b['slot'] * 812 + offset)[0]
            if not slot:
                continue
            unit = by_unit.get(slot)
            worker_links.append(dict(building_slot=b['slot'], building_type=b['type'],
                building_owner=b['owner'], worker_field=hex(offset), unit_slot=slot,
                unit_type=unit['type'] if unit else None,
                unit_type_name=unit['type_name'] if unit else None,
                reciprocal_slot=bool(unit and unit['building_slot_candidate'] == b['slot']),
                reciprocal_gid=bool(unit and unit['building_gid_candidate'] == b['global_id']),
                same_owner=bool(unit and unit['owner'] == b['owner'])))
    players = []
    resources = []
    for player in range(9):
        off = player * 0x583c
        keep = u32(pb, off + 0x94)
        row = dict(player=player, keep_slot=keep,
                   gold_candidate=struct.unpack_from('<i', pb, off + 0x50c)[0],
                   population_candidate=u32(pb, off + 0x78),
                   army_candidate=u32(pb, off + 0x53c),
                   popularity_candidate=struct.unpack_from('<i', pb, off + 0x444)[0],
                   unit_records=sum(u['owner'] == player for u in rows),
                   building_records=sum(b['owner'] == player for b in buildings))
        for index, name in enumerate(GOODS):
            value = (struct.unpack_from('<i', pb, off + 0x4d0 + 4 * index)[0]
                     if name == 'gold' else u32(pb, off + 0x4d0 + 4 * index))
            row[name] = value
            total = sum(u32(bb, b['slot'] * 812 + 0x120 + 4 * index)
                        for b in buildings if b['owner'] == player and b['type'] in (10, 19, 11))
            resources.append(dict(player=player, good=name, player_offset=hex(0x4d0 + 4 * index),
                                  player_value=value, storage_building_sum=total,
                                  equal=value == total))
        players.append(row)
    summary = dict(menu=m.menu_metadata(), version=m.version, section_count=m.count,
        save_extension=m.save_extension,
        entity_counts={k: v['active_count'] for k, v in result['entities'].items()},
        entity_checks={k: {field: value for field, value in v.items() if field != 'records'}
                       for k, v in result['entities'].items()},
        units_by_type=dict(sorted(Counter(u['type_name'] for u in rows).items())),
        units_by_owner=dict(Counter(u['owner'] for u in rows)),
        unit_coordinate_checks=dict(checks),
        path_flags_candidate_counts=dict(Counter(u['path_flags_candidate'] for u in rows)),
        worker_links=len(worker_links),
        worker_links_reciprocal=sum(w['reciprocal_slot'] and w['reciprocal_gid'] for w in worker_links),
        storage_comparisons_nonzero=[r for r in resources if r['player_value'] or r['storage_building_sum']],
        resource_mismatches=[r for r in resources if not r['equal']], players=players)
    return summary, rows, worker_links, resources


def comparison(a, b):
    aa, bb = ({s['id']: s for s in m.sections} for m in (a, b))
    rows = []
    for sid in sorted(aa.keys() | bb.keys()):
        x, y = aa.get(sid), bb.get(sid)
        row = dict(id=sid, baseline_size=x['size'] if x else None,
                   save_size=y['size'] if y else None)
        if x is None or y is None:
            row['status'] = 'added' if x is None else 'removed'
        elif x['decoded'] is None or y['decoded'] is None:
            row.update(status='opaque', raw_equal=x['raw'] == y['raw'])
        else:
            xd, yd = x['decoded'], y['decoded']
            n = min(len(xd), len(yd))
            changed = int(np.count_nonzero(np.frombuffer(xd[:n], dtype='u1') !=
                                          np.frombuffer(yd[:n], dtype='u1'))) + abs(len(xd)-len(yd))
            row.update(status='same' if changed == 0 else 'changed', changed_bytes=changed)
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory')
    args = parser.parse_args()
    require(not args.output.exists(), 'Evidence directory already exists')
    enum_path = STATS / 'instructions/enums.md'
    enums = enum_path.read_text(encoding='utf-8')
    names = {int(number): name for number, name in re.findall(r'(\d+)=(UNIT_\w+)', enums)}
    source = GAME / 'Maps/leto vs fbi 10.map'
    baseline = GAME / 'Maps/001 3 green Fenrir.map'
    saves = sorted((GAME / 'Saves').glob('leto vs fbi*.msv'))
    require(saves, 'No related saves found')
    args.output.mkdir()
    snapshots = args.output / 'snapshots'
    snapshots.mkdir()
    inputs = {}
    def load(path):
        raw = path.read_bytes()
        (snapshots / path.name).write_bytes(raw)
        m = MapFile(raw)
        require(m.rebuild() == raw, 'Roundtrip failed: ' + path.name)
        require(all(s['error'] is None for s in m.sections), 'Decode failure: ' + path.name)
        inputs[str(path)] = dict(sha256=sha(raw), size=len(raw), roundtrip=True)
        return m
    current = load(source)
    base = load(baseline)
    write_json(args.output / 'manifest.json', current.manifest())
    summary, rows, links, resources = inspect(current, names)
    csv_rows(args.output / 'units.csv', rows)
    csv_rows(args.output / 'worker_links.csv', links)
    csv_rows(args.output / 'resources.csv', resources)
    csv_rows(args.output / 'players.csv', summary['players'])
    diffs = comparison(base, current)
    write_json(args.output / 'baseline_diff.json', diffs)
    summary['baseline_comparison'] = dict(path=str(baseline),
        caveat='Embedded filename matches; not a controlled before/after gameplay experiment.',
        statuses=dict(Counter(r['status'] for r in diffs)))
    series = []
    for path in saves:
        m = load(path)
        report, _, _, _ = inspect(m, names)
        report.update(file=path.name, sha256=sha(m.data), identical_to_renamed=m.data == current.data)
        series.append(report)
    write_json(args.output / 'related_saves.json', series)
    summary['identical_original_saves'] = [s['file'] for s in series if s['identical_to_renamed']]
    source_paths = [enum_path, STATS/'instructions/player.md', STATS/'instructions/building.md',
                   EXTENDER/'src/SHCDESE.BepInEx/Interop/GameUnit.cs',
                   EXTENDER/'src/SHCDESE.BepInEx/Interop/GamePlayerResources.cs',
                   EXTENDER/'src/SHCDESE.BepInEx/Interop/GameBuilding.cs']
    summary['research_sources'] = {str(p): sha(p.read_bytes()) for p in source_paths}
    summary['interpretation_limits'] = [
        'Gold and dynamic field names need controlled in-game corroboration.',
        'Snapshot numbering is not assumed chronological or the same uninterrupted match.',
        'Runtime +4 mapping is evaluated field by field; not a blanket record transform.',
        'Unit occupancy grid is not a complete enumeration of unit records.',
        'No map or save was edited and no live-game test was performed by this script.']
    summary['inputs'] = inputs
    for path, record in inputs.items():
        require(sha(Path(path).read_bytes()) == record['sha256'], 'Input changed during analysis')
    summary['source_integrity'] = 'All source hashes rechecked unchanged'
    write_json(args.output / 'findings.json', summary)
    print(json.dumps({k: summary[k] for k in ('entity_counts', 'unit_coordinate_checks',
        'worker_links', 'worker_links_reciprocal', 'resource_mismatches',
        'baseline_comparison', 'identical_original_saves', 'source_integrity')}, indent=2))


if __name__ == '__main__':
    main()
