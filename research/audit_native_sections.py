"""Read the pinned DLL's save/load descriptors and compare archived map sections.

No process access, DLL execution, map writes or optional disassembly packages.
Run from the repository root: python -m research.audit_native_sections
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from maptool import MapFile, require

ROOT = Path(__file__).resolve().parents[1]
DLL = Path('C:/Program Files (x86)/Steam/steamapps/common/Stronghold Crusader Definitive Edition') / 'Stronghold Crusader Definitive Edition_Data/Plugins/x86_64/CrusaderDE.dll'
EXTENDER = ROOT.parent / 'shcde-script-extender'
DLL_SHA256 = 'fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2'
REGISTRY_RVA = 0x336b20
TILE_MANAGER_RVA = 0x405edb0
IDENTIFIED_BINDINGS = {
    1035: dict(binding='Next global ID', evidence='Native assign-then-increment at 0x9BF12/0x9BF24'),
    1047: dict(binding='Scenario selection index', evidence='0x87C40 stores scenario argument minus one'),
    1040: dict(binding='GameRandomStruct', record_size=40016),
    4013: dict(binding='Building records', record_size=812, slots=4000, runtime_to_file_delta=0),
    1014: dict(binding='Vegetation records', record_size=156, slots=4000, runtime_to_file_delta=-12),
    3015: dict(binding='Unit records', record_size=1168, slots=10000, runtime_to_file_delta=4),
    2022: dict(binding='Player resources records', record_size=0x583c, slots=9),
    1171: dict(binding='Per-unit packed path plans', record_size=1000, slots=10000,
               evidence='0x67E8400 + GameUnitManager.PackedPathPlanBlockOffset(0xB4FE78)'),
    1016: dict(binding='Tribe records, overlapping prefix of section 2016', record_size=1672,
               slots=1500, runtime_to_file_delta=2),
    2016: dict(binding='Tribe records', record_size=1672, slots=4500, runtime_to_file_delta=2),
    2025: dict(binding='Projectile records', record_size=232, slots=6000, runtime_to_file_delta=-20),
    1031: dict(binding='Connection/gate records', record_size=516, slots=200),
    1038: dict(binding='Auxiliary vegetation descriptors', record_size=32, slots=4000,
               evidence='0x107290 allocates/writes this 32-byte array'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class PEImage:
    """Minimal bounded PE32+ file reader. Never loads executable code."""
    def __init__(self, data):
        self.data = data
        require(data[:2] == b'MZ' and len(data) >= 0x40, 'Missing DOS header')
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        require(pe + 24 <= len(data) and data[pe:pe+4] == b'PE\0\0', 'Missing PE header')
        machine, count = struct.unpack_from('<HH', data, pe + 4)
        optional_size = struct.unpack_from('<H', data, pe + 20)[0]
        opt = pe + 24
        require(machine == 0x8664 and optional_size >= 112 and
                opt + optional_size + count * 40 <= len(data), 'Unsupported/truncated PE')
        require(struct.unpack_from('<H', data, opt)[0] == 0x20b, 'Expected PE32+')
        self.base = struct.unpack_from('<Q', data, opt + 24)[0]
        self.image_size = struct.unpack_from('<I', data, opt + 56)[0]
        self.sections = []
        for i in range(count):
            off = opt + optional_size + i * 40
            virtual_size, rva, raw_size, raw_at = struct.unpack_from('<IIII', data, off + 8)
            self.sections.append((rva, virtual_size, raw_size, raw_at))

    def read(self, rva, size):
        require(rva >= 0 and size >= 0, 'Negative PE range')
        for start, _, raw_size, raw_at in self.sections:
            delta = rva - start
            if 0 <= delta and delta + size <= raw_size:
                require(raw_at + delta + size <= len(self.data), 'Truncated raw section')
                return self.data[raw_at + delta:raw_at + delta + size]
        raise ValueError('RVA has no complete file-backed range: %#x' % rva)


def read_registry(image):
    rows = []
    for i in range(400):
        rva = REGISTRY_RVA + i * 24
        ptr, disabled, size, compressed, sid, reserved = struct.unpack('<QIIHHI', image.read(rva, 24))
        if ptr == 0:
            break
        require(image.base <= ptr < image.base + image.image_size, 'Descriptor pointer outside image')
        require(disabled in (0, 1) and compressed in (0, 1) and size > 0 and sid > 0,
                'Invalid section descriptor')
        require(sid not in {r['id'] for r in rows}, 'Duplicate descriptor ID')
        rows.append(dict(id=sid, descriptor_rva=hex(rva), runtime_rva=hex(ptr-image.base),
                         decoded_size=size, compressed=bool(compressed),
                         save_enabled_by_default=disabled == 0, reserved=reserved))
    else:
        raise ValueError('Missing descriptor terminator')
    require(len(rows) == 212 and sum(r['save_enabled_by_default'] for r in rows) == 175,
            'Pinned registry shape changed')
    return rows


def annotate(rows, header):
    # Names are corroborating SDK labels. Direct pointer identity alone does not
    # establish every field's gameplay meaning or a safe write recipe.
    text = header.read_text(encoding='utf-8-sig')
    fields = {}
    widths = {'uint8_t': 1, 'int8_t': 1, 'uint16_t': 2, 'int16_t': 2,
              'int32_t': 4, 'uint32_t': 4, 'TilePropertyFlag': 4,
              'TileType16': 1, 'ProjectileType': 2}
    for typ, name, offset in re.findall(r'\b(\w+)\s+(\w+)\[320800\];\s*//0x([0-9A-Fa-f]+)', text):
        fields[int(offset, 16)] = (name, widths.get(typ))
    for row in rows:
        if row['id'] in IDENTIFIED_BINDINGS:
            row.update(IDENTIFIED_BINDINGS[row['id']])
            if 'slots' in row:
                require(row['decoded_size'] == row['record_size'] * row['slots'], 'Record extent mismatch')
        offset = int(row['runtime_rva'], 16) - TILE_MANAGER_RVA
        if offset in fields:
            name, width = fields[offset]
            row.update(sdk_member='GameTileManager.' + name, manager_offset=hex(offset),
                       sdk_element_width=width,
                       persisted_cell_width=row['decoded_size'] // 320800
                       if row['decoded_size'] % 320800 == 0 else None)
            row['width_matches_sdk'] = row['decoded_size'] == 320800 * width if width else None
    return rows


def compare_map(path, rows):
    data = path.read_bytes()
    parsed = MapFile(data)
    active = {r['id']: r for r in rows if r['save_enabled_by_default']}
    mismatches = []
    ids = {s['id'] for s in parsed.sections}
    for s in parsed.sections:
        row = active.get(s['id'])
        if row is None:
            mismatches.append(dict(id=s['id'], issue='not in default-enabled registry'))
        elif s['size'] != row['decoded_size'] or bool(s['compressed']) != row['compressed']:
            mismatches.append(dict(id=s['id'], issue='size/compression differs',
                                   file_size=s['size'], registry_size=row['decoded_size'],
                                   file_compressed=bool(s['compressed']), registry_compressed=row['compressed']))
    errors = [{'id': s['id'], 'error': s['error']} for s in parsed.sections if s['error']]
    result = dict(path=str(path.resolve()), sha256=sha(data), version=parsed.version,
                  section_count=parsed.count, mismatches=mismatches,
                  absent_default_ids=sorted(set(active)-ids), decode_errors=errors,
                  byte_exact_roundtrip=parsed.rebuild() == data)
    if parsed.version == 236:
        result['saved_path_check'] = saved_path_check(parsed)
    require(sha(path.read_bytes()) == result['sha256'], 'Source changed during audit')
    return result


def saved_path_check(parsed):
    """Cross-check section 1171 with the established +4 file-unit displacement.

    Counts are typed/non-cleared records, not a living-unit census. Only exact
    path state 2 is used for the stronger cursor/direction checks.
    """
    units, paths = (parsed.section(sid)['decoded'] for sid in (3015, 1171))
    require(units is not None and paths is not None and len(units) == 10000 * 1168
            and len(paths) == 10000 * 1000, 'Unexpected unit/path table extent')
    records = 0
    nonempty = 0
    state2 = 0
    failures = []
    examples = []
    for slot in range(1, 10000):
        at = slot * 1168
        alive, kind = struct.unpack_from('<HH', units, at + 0x8c)
        if alive in (0, 3) or kind == 0:
            continue
        records += 1
        path_state = struct.unpack_from('<H', units, at + 0xf6)[0]
        index, length = struct.unpack_from('<HH', units, at + 0xfa)
        nonempty += length > 0
        if path_state != 2:
            continue
        state2 += 1
        if not 0 <= index <= length <= 2000:
            failures.append(dict(slot=slot, issue='cursor/length range', index=index, length=length))
            continue
        encoded = paths[slot * 1000:slot * 1000 + (length + 1) // 2]
        directions = [(encoded[n // 2] >> (4 * (n % 2))) & 15 for n in range(length)]
        if any(d > 7 for d in directions):
            failures.append(dict(slot=slot, issue='direction outside 0..7'))
        if len(examples) < 8:
            examples.append(dict(slot=slot, type=kind, path_index=index,
                                 path_length=length, first_directions=directions[:12]))
    return dict(typed_noncleared_records=records, records_with_nonzero_path_length=nonempty,
                path_state_2_records=state2, failures=failures, examples=examples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, default=DLL)
    parser.add_argument('--output', type=Path, default=ROOT/'output/runtime-audit-2026-10-23')
    parser.add_argument('--map', type=Path, action='append', default=[])
    args = parser.parse_args()
    raw = args.dll.read_bytes()
    require(sha(raw) == DLL_SHA256, 'DLL differs from pinned research version')
    header = EXTENDER/'ReverseEngineering/structs/TileManager.h'
    rows = annotate(read_registry(PEImage(raw)), header)
    result = dict(file_only=True, game_process_accessed=False, map_files_written=0,
                  dll_path=str(args.dll), dll_sha256=sha(raw), registry_rva=hex(REGISTRY_RVA),
                  descriptor_stride=24, descriptor_count=len(rows), default_enabled_count=175,
                  sdk_header=str(header), sdk_header_sha256=sha(header.read_bytes()),
                  source_files=[dict(path=str(p), sha256=sha(p.read_bytes())) for p in
                                [EXTENDER/'src/SHCDESE.BepInEx/Interop'/name for name in
                                 ('GameUnitManager.cs', 'GameTribeManager.cs', 'GameTribe.cs',
                                  'GameProjectile.cs', 'GameVegetation.cs', 'GameRandomStruct.cs')]],
                  descriptors=rows)
    args.output.mkdir(parents=True, exist_ok=True)
    registry = args.output/'native-section-registry.json'
    registry.write_text(json.dumps(result, indent=2), encoding='utf-8')
    paths = args.map or sorted((ROOT/'output/references-2026-09-19/maps').glob('*.map'))
    require(paths, 'No archived maps supplied/found')
    checks = []
    for path in paths:
        check = compare_map(path, rows)
        checks.append(check)
        print('%s: v%d, %d sections, %d descriptor differences, roundtrip=%s' %
              (path.name, check['version'], check['section_count'], len(check['mismatches']), check['byte_exact_roundtrip']), flush=True)
    (args.output/'map-checks.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    require(sha(args.dll.read_bytes()) == DLL_SHA256, 'DLL changed during audit')
    print('Registry: %d descriptors, 175 enabled; %d map comparisons; sources unchanged.' % (len(rows), len(checks)))


if __name__ == '__main__':
    main()
