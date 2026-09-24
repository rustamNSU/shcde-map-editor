"""Create explicitly requested etest copies; never overwrite source/existing maps."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from maptool import MapFile, require, u32

VALUES = (0, 1, 2, 3, 255, 256, 16384, 32767)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    original = args.source.read_bytes()
    source = MapFile(original)
    read = lambda sid, dtype: np.frombuffer(source.section(sid)['decoded'], dtype=dtype)
    logic, surface, height = read(3003, '<u4'), read(3037, 'u1'), read(3005, 'u1')
    interior = (logic & 0x30) == 0
    require(bool(interior.any()), 'No playable interior')
    require(bool(np.all(logic[interior] == 0x8000)), 'Interior is not all ordinary land')
    require(bool(np.all(surface[interior] == 0)), 'Interior has painted surfaces')
    require(bool(np.all(height[interior] == 8)), 'Interior is not flat default ground')
    for sid in (3004, 3010, 3012):
        require(not np.any(read(sid, '<u2')[interior]), 'Interior has entity references')
    noise = read(3008, '<u2')
    require(len(noise) == len(interior), 'Invalid noise dimensions')
    names = ['etest_noise_original.map'] + [f'etest_noise_{v:05d}.map' for v in VALUES]
    for folder in (args.destination, args.archive):
        require(not any((folder / name).exists() for name in names), 'A test map already exists')
    require(not (args.archive / 'manifest.json').exists(), 'Manifest already exists')
    prepared = [(names[0], original, None, 0)]
    for name, value in zip(names[1:], VALUES):
        changed = noise.copy()
        changed[interior] = value
        result = source.rebuild({3008: changed.tobytes()})
        check = MapFile(result)
        require(result[:source.base] == original[:source.base], 'Header/catalog changed')
        require(check.trailing == source.trailing, 'Trailing data changed')
        for section in source.sections:
            if section['id'] != 3008:
                require(check.section(section['id'])['raw'] == section['raw'], 'Unrelated section changed')
        actual = np.frombuffer(check.section(3008)['decoded'], dtype='<u2')
        require(np.all(actual[interior] == value), 'Noise value not applied')
        require(np.array_equal(actual[~interior], noise[~interior]), 'Outside/border noise changed')
        require(all(s['error'] is None for s in check.sections), 'Invalid rebuilt section')
        prepared.append((name, result, value, int(np.count_nonzero(actual != noise))))
    require(args.source.read_bytes() == original, 'Source changed during preparation')
    manifest = dict(source=str(args.source.resolve()), source_sha256=sha(original),
                    size=u32(source.section(1050)['decoded']), target_section=3008,
                    interior_cells=int(interior.sum()), variants=[])
    for folder in (args.archive, args.destination):
        folder.mkdir(parents=True, exist_ok=True)
        for name, data, value, count in prepared:
            with (folder / name).open('xb') as f:
                f.write(data)
            require((folder / name).read_bytes() == data, 'Written file mismatch')
    for name, data, value, count in prepared:
        manifest['variants'].append(dict(name=name, value=value, changed_cells=count,
                                        sha256=sha(data), game_path=str((args.destination/name).resolve())))
    require(args.source.read_bytes() == original, 'Source changed')
    manifest['source_unchanged'] = True
    with (args.archive / 'manifest.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
