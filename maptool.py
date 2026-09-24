"""Lossless Stronghold map container reader, extractor and section patcher.

Container layout informed by sourcehold/sourcehold-maps (MIT).
DE changes and validation are documented in README.md.
"""
import argparse
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path

import dclimplode


def require(condition, message):
    if not condition:
        raise ValueError(message)


def u32(data, offset=0):
    require(0 <= offset <= len(data) - 4, 'Truncated uint32')
    return struct.unpack_from('<I', data, offset)[0]


def decode(raw):
    require(len(raw) >= 12, 'Truncated compression header')
    size, packed, crc = struct.unpack_from('<3I', raw)
    require(packed == len(raw) - 12, 'Compressed size mismatch')
    result = dclimplode.decompressobj().decompress(bytes(raw[12:]))
    require(len(result) == size, 'Uncompressed size mismatch')
    require(zlib.crc32(result) == crc, 'CRC32 mismatch')
    return result


def encode(data):
    compressor = dclimplode.compressobj(dclimplode.CMP_BINARY, 4096)
    packed = compressor.compress(data) + compressor.flush()
    return struct.pack('<3I', len(data), len(packed), zlib.crc32(data)) + packed


class MapFile:
    def __init__(self, data):
        self.data = data
        require(u32(data) in (0xFFFFFFFF, 0xFFFFFFFE), 'Unrecognized map magic')
        p = 8 + u32(data, 4)
        preview_end = 20 + u32(data, 12)
        require(preview_end <= p <= len(data), 'Preview block out of bounds')
        self.preview = decode(data[8:preview_end])
        # Some real maps append descriptive text inside the outer preview block.
        self.preview_extra = data[preview_end:p]
        # DE reference description uses: text bytes followed by uint32 byte count.
        self.preview_text_bytes = None
        if len(self.preview_extra) >= 4 and u32(self.preview_extra, len(self.preview_extra)-4) == len(self.preview_extra)-4:
            self.preview_text_bytes = self.preview_extra[:-4]
        end = p + 4 + u32(data, p)
        self.description = decode(data[p + 12:end])
        p = end
        self.headers = {}
        for name in ('u1', 'u2', 'u3', 'u4'):
            size = u32(data, p)
            require(p + 4 + size <= len(data), 'Truncated header')
            self.headers[name] = {'offset': p, 'size': size,
                                  'hex': data[p + 4:p + 4 + size].hex()}
            p += 4 + size
        # Examined DE .msv saves have length-prefixed97 or591-byte blocks here,
        # before the usual four-byte ud. Renaming to .map leaves it intact.
        # Recognize only this observed variant, without scanning arbitrary bytes
        # for something that resembles a directory. Keep its contents opaque.
        self.save_extension = None
        def directory_shape(at):
            if not 0 <= at <= len(data) - 32:
                return False
            size = u32(data, at)
            return (size >= 36 and (size - 36) % 20 == 0
                    and at + size <= len(data)
                    and 0 < u32(data, at + 8) <= (size - 36) // 20)
        if not directory_shape(p + 4) and u32(data, p) in (97, 591):
            extension_size=u32(data,p)
            end = p + 4 + extension_size
            require(directory_shape(end + 4), 'Invalid save extension/directory')
            self.save_extension = dict(offset=p, size=extension_size, hex=data[p + 4:end].hex())
            p = end
        p += 4  # ud, retained verbatim
        self.directory_offset = p
        self.directory_size = u32(data, p)
        require(self.directory_size >= 36 and (self.directory_size - 36) % 20 == 0,
                'Unrecognized directory size')
        self.capacity = (self.directory_size - 36) // 20
        self.count = u32(data, p + 8)
        require(self.count <= self.capacity, 'Invalid section count')
        self.version = u32(data, p + 12)
        self.base = p + self.directory_size
        require(self.base + u32(data, p + 4) <= len(data), 'Truncated section area')
        self.arrays = [list(struct.unpack_from('<%dI' % self.capacity, data,
                      p + 32 + self.capacity * 4 * j)) for j in range(5)]
        self.sections = []
        previous_end = 0
        ids = set()
        for i in range(self.count):
            size, length, sid, compressed, offset = [a[i] for a in self.arrays]
            require(sid not in ids, 'Duplicate section ID')
            ids.add(sid)
            require(compressed in (0, 1), 'Unknown compression flag')
            require(offset == previous_end, 'Noncontiguous section layout')
            require(offset + length <= u32(data, p + 4), 'Section out of bounds')
            raw = data[self.base + offset:self.base + offset + length]
            section = dict(id=sid, size=size, stored_size=length, compressed=compressed,
                           relative_offset=offset, offset=self.base + offset,
                           raw=raw, decoded=None, error=None)
            try:
                decoded = decode(raw) if compressed else raw
                require(len(decoded) == size, 'Directory size mismatch')
                section['decoded'] = decoded
            except (ValueError, RuntimeError) as error:
                section['error'] = str(error)
            self.sections.append(section)
            previous_end = offset + length
        require(previous_end == u32(data, p + 4), 'Unaccounted section data')
        self.trailing = data[self.base + previous_end:]

    def section(self, sid):
        return next(s for s in self.sections if s['id'] == sid)

    def menu_metadata(self):
        """Confirmed prefix fields; offsets refer to payload after length word.

        Start markers are preview/menu coordinates, NOT terrain tile coordinates.
        Unknown header fields are deliberately left uninterpreted.
        """
        u2 = bytes.fromhex(self.headers['u2']['hex'])
        u4 = bytes.fromhex(self.headers['u4']['hex'])
        result = {}
        if len(u2) >= 28:
            result['players_count'] = u32(u2, 24)
        if len(u4) >= 80:
            result['start_markers'] = []
            for i in range(8):
                x, y = struct.unpack_from('<2I', u4, 16 + 8*i)
                result['start_markers'].append(dict(player=i+1, x=x, y=y,
                    present=x != 0xFFFFFFFF and y != 0xFFFFFFFF))
        if len(u4) >= 84:
            result['map_size'] = u32(u4, 80)
        return result

    def rebuild(self, replacements=None, recovered_sections=()):
        replacements = replacements or {}
        require(set(replacements) <= {s['id'] for s in self.sections}, 'Unknown section ID')
        prefix = bytearray(self.data[:self.base])
        chunks = []
        offset = 0
        for i, section in enumerate(self.sections):
            sid = section['id']
            size = section['size']
            raw = section['raw']
            if sid in replacements and replacements[sid] != section['decoded']:
                require(section['error'] is None or sid in recovered_sections, 'Cannot edit undecoded section')
                payload = replacements[sid]
                require(len(payload) == size, 'Replacement must retain decoded section size')
                raw = encode(payload) if section['compressed'] else payload
            for j, value in enumerate((size, len(raw), sid, section['compressed'], offset)):
                struct.pack_into('<I', prefix, self.directory_offset + 32 +
                                 j * self.capacity * 4 + i * 4, value)
            chunks.append(raw)
            offset += len(raw)
        struct.pack_into('<I', prefix, self.directory_offset + 4, offset)
        return bytes(prefix) + b''.join(chunks) + self.trailing

    def manifest(self):
        items = []
        for section in self.sections:
            item = {k: v for k, v in section.items() if k not in ('raw', 'decoded')}
            decoded = section['decoded']
            if decoded is not None:
                item['sha256_decoded'] = hashlib.sha256(decoded).hexdigest()
                if len(decoded) == 4:
                    item['uint32'] = u32(decoded)
            items.append(item)
        return dict(file_size=len(self.data), sha256=hashlib.sha256(self.data).hexdigest(),
                    magic=hex(u32(self.data)), directory_offset=self.directory_offset,
                    directory_size=self.directory_size, capacity=self.capacity,
                    version=self.version, section_count=self.count, data_offset=self.base,
                    trailing_bytes=len(self.trailing), preview_extra_bytes=len(self.preview_extra),
                    preview_text_hex=self.preview_text_bytes.hex() if self.preview_text_bytes is not None else None,
                    headers=self.headers, save_extension=self.save_extension,
                    menu_metadata=self.menu_metadata(), sections=items)


def save_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def export_images(map_file, output):
    from PIL import Image
    preview = map_file.preview
    side = math.isqrt(len(preview) - 512)
    require(side * side == len(preview) - 512, 'Unexpected preview dimensions')
    palette = []
    for (value,) in struct.iter_unpack('<H', preview[:512]):
        palette.extend(((value >> shift & 31) * 255 // 31) for shift in (10, 5, 0))
    im = Image.frombytes('P', (side, side), preview[512:])
    im.putpalette(palette)
    im.convert('RGB').save(output / 'preview.png')
    # DE candidate tile layers, interpreted using an 800-row diamond.
    # Labels/coordinates are hypotheses, not verified editor semantics.
    for sid in (3037, 3005, 3045, 3049, 3003):
        try:
            payload = map_file.section(sid)['decoded']
        except StopIteration:
            continue
        width = 4 if sid == 3003 else 1
        if payload is None or len(payload) != 320800 * width:
            continue
        values = list(struct.unpack('<320800' + ('I' if width == 4 else 'B'), payload))
        colors = {v: ((v * 73 + 53) % 220 + 20, (v * 131 + 83) % 220 + 20,
                      (v * 197 + 29) % 220 + 20) if v else (22, 26, 32) for v in set(values)}
        layer = Image.new('RGB', (800, 800), (4, 7, 12))
        pixels = layer.load()
        index = 0
        for y in range(800):
            count = 2 * min(y + 1, 800 - y)
            start = (800 - count) // 2
            for x in range(count):
                pixels[start + x, y] = colors[values[index]]
                index += 1
        require(index == len(values), 'Tile count mismatch')
        layer.save(output / ('layer_%d.png' % sid))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    extract = commands.add_parser('extract')
    extract.add_argument('map', type=Path)
    extract.add_argument('folder', type=Path)
    repack = commands.add_parser('repack')
    repack.add_argument('map', type=Path)
    repack.add_argument('output', type=Path)
    repack.add_argument('--section', type=int)
    repack.add_argument('--payload', type=Path)
    diff = commands.add_parser('diff')
    diff.add_argument('map', type=Path)
    diff.add_argument('other', type=Path)
    args = parser.parse_args()
    original = args.map.read_bytes()
    parsed = MapFile(original)
    if args.command == 'extract':
        args.folder.mkdir(parents=True, exist_ok=False)
        (args.folder / 'raw').mkdir()
        (args.folder / 'decoded').mkdir()
        (args.folder / 'original.map').write_bytes(original)
        (args.folder / 'prefix.bin').write_bytes(original[:parsed.base])
        for s in parsed.sections:
            (args.folder / 'raw' / ('%d.bin' % s['id'])).write_bytes(s['raw'])
            if s['decoded'] is not None:
                (args.folder / 'decoded' / ('%d.bin' % s['id'])).write_bytes(s['decoded'])
        (args.folder / 'manifest.json').write_text(json.dumps(parsed.manifest(), indent=2), encoding='utf-8')
        export_images(parsed, args.folder)
        require(parsed.rebuild() == original, 'Lossless roundtrip failed')
        print(json.dumps({'sections': parsed.count, 'undecoded': [s['id'] for s in parsed.sections if s['error']],
                          'lossless_roundtrip': True, 'output': str(args.folder.resolve())}))
    elif args.command == 'repack':
        require((args.section is None) == (args.payload is None), 'Use --section and --payload together')
        replacement = {} if args.section is None else {args.section: args.payload.read_bytes()}
        rebuilt = parsed.rebuild(replacement)
        check = MapFile(rebuilt)
        for sid, payload in replacement.items():
            require(check.section(sid)['decoded'] == payload, 'Replacement readback failed')
        save_new(args.output, rebuilt)
        print('Wrote', args.output)
    else:
        other = MapFile(args.other.read_bytes())
        first = {s['id']: s for s in parsed.sections}
        second = {s['id']: s for s in other.sections}
        result = {'prefix_changed': original[:parsed.base] != other.data[:other.base], 'sections': []}
        for sid in sorted(set(first) | set(second)):
            a, b = first.get(sid), second.get(sid)
            if a is None or b is None:
                result['sections'].append({'id': sid, 'added_or_removed': True})
                continue
            if a['raw'] == b['raw']:
                continue
            x, y = a['decoded'], b['decoded']
            item = {'id': sid, 'decoded_available': x is not None and y is not None}
            if item['decoded_available']:
                offsets = [i for i, (v, w) in enumerate(zip(x, y)) if v != w]
                item.update(changed_bytes=len(offsets) + abs(len(x) - len(y)),
                            first_offsets=offsets[:32], sizes=[len(x), len(y)])
            result['sections'].append(item)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
