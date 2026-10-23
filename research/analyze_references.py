"""Read-only reference-map research. Copies originals, hashes inputs, reports facts.

Does not write maps to the game directory or produce modified map files.
Names are experiment labels, not proof that edits were isolated.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image, ImageDraw

from maptool import MapFile, require, u32
from semantics import ENTITY_LAYOUTS, tile_xy, tile_index

GRID_TYPES = {3003: '<u4', 3037: 'u1', 3043: 'u1', 3004: '<u2',
              3020: 'u1', 3036: '<u2', 3005: 'u1', 3045: 'u1',
              3006: 'u1', 3007: '<u2', 3008: '<u2', 3009: '<u2',
              3010: '<u2', 3030: 'u1', 3026: '<u2', 3118: 'u1',
              3012: '<u2', 3021: '<u2', 3049: 'u1', 3028: 'u1',
              3029: 'u1', 3101: 'u1', 3103: 'u1', 3104: 'u1'}
XY = np.array([tile_xy(i) for i in range(320800)], dtype=np.int16)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def hist(values):
    keys, counts = np.unique(values, return_counts=True)
    return {str(int(k)): int(n) for k, n in zip(keys, counts)}


def bounds(indices):
    if not len(indices):
        return None
    points = XY[indices]
    return [int(points[:, 0].min()), int(points[:, 1].min()),
            int(points[:, 0].max()), int(points[:, 1].max())]


def grids(m):
    sections = {s['id']: s for s in m.sections}
    result = {}
    for sid, dtype in GRID_TYPES.items():
        s = sections.get(sid)
        if s is not None and s['decoded'] is not None:
            v = np.frombuffer(s['decoded'], dtype=dtype)
            require(len(v) == 320800, 'Unexpected grid count')
            result[sid] = v
    return result


def objects(m, kind, layout):
    sid, stride, alive, type_offset, gid, xo, yo, tid, grid_id = layout
    b = m.section(sid)['decoded']
    require(b is not None and len(b) % stride == 0, 'Bad object section')
    reference = np.frombuffer(m.section(grid_id)['decoded'], dtype='<u2')
    counts = np.bincount(reference, minlength=len(b) // stride)
    records = []
    states = Counter()
    for slot in range(1, len(b) // stride):
        base = slot * stride
        h = lambda off: struct.unpack_from('<H', b, base + off)[0]
        u = lambda off: u32(b, base + off)
        state, typ, global_id = h(alive), h(type_offset), u(gid)
        states[state] += 1
        # Include typed/inactive records, not just the runtime active-state filter.
        if not (state or typ or global_id):
            continue
        x, y, index = h(xo), h(yo), u(tid)
        try:
            match = tile_index(x, y) == index
        except ValueError:
            match = False
        rec = dict(slot=slot, state=state, type=typ, global_id=global_id,
                   x=x, y=y, tile_id=index, coordinates_match=match,
                   referenced_cells=int(counts[slot]) if slot < len(counts) else 0,
                   record_sha256=sha(b[base:base + stride]))
        if kind == 'buildings':
            rec.update(owner=h(0xD6), world_x=h(0xE8), world_y=h(0xEA),
                       height=h(0xEC), footprint_side=u(0xF8), access_x=h(0xFE), access_y=h(0x100),
                       hp=struct.unpack_from('<h', b, base + 0x10C)[0], max_hp=h(0x10E),
                       housing=h(0x196), sprite_atlas=h(4), sprite_color=u(8))
            inds = np.flatnonzero(reference == slot) if slot else np.array([], dtype=int)
            rec['reference_bounds'] = bounds(inds)
        elif kind == 'vegetation':
            rec.update(world_x=h(0x5C), world_y=h(0x5E),
                       hp=h(0x72), felled_state=h(0x76),
                       resource_state=struct.unpack_from('<h', b, base + 0x78)[0], growth_stage=u(0x80),
                       growth_progress=u(0x84))
        elif kind == 'units':
            rec.update(owner=u(0x80), controller=b[base + 0x96])
        records.append(rec)
    refs = [int(v) for v in np.unique(reference) if v]
    return dict(section=sid, stride=stride, capacity=len(b) // stride,
                state_histogram=dict(states), nonempty_records=len(records),
                slot_zero_nonzero=any(b[:stride]), slot_zero_sha256=sha(b[:stride]),
                references=refs, records=records)


def preview_image(m):
    p = m.preview
    side = int((len(p) - 512) ** 0.5)
    require(side * side == len(p) - 512, 'Unexpected preview')
    im = Image.frombytes('P', (side, side), p[512:])
    palette = []
    for (v,) in struct.iter_unpack('<H', p[:512]):
        palette.extend(((v >> shift & 31) * 255 // 31) for shift in (10, 5, 0))
    im.putpalette(palette)
    return im.convert('RGB')


def survey(path, out):
    data = path.read_bytes()
    m = MapFile(data)
    require(m.rebuild() == data, 'Non-identical reconstruction')
    g = grids(m)
    # Border mask only excludes known edge bits; no assumptions about filename size.
    interior = (g[3003] & 0x30) == 0
    size = u32(m.section(1050)['decoded'])
    r = dict(file=path.name, sha256=sha(data), version=m.version, size=size,
             sections=m.count, compressed_sections=sum(s['compressed'] for s in m.sections),
             opaque=[s['id'] for s in m.sections if s['error']], roundtrip=True,
             description_hex=m.description.hex(),
             description_text=m.description.split(b'\0')[0].decode('utf-8', errors='replace'),
             preview_extra_hex=m.preview_extra.hex(), grids={},
             preview_text=m.preview_text_bytes.decode('utf-8', errors='replace') if m.preview_text_bytes is not None else None,
             objects={k: objects(m, k, v) for k, v in ENTITY_LAYOUTS.items()},
             interior_cells=int(interior.sum()), interior_bounds=bounds(np.flatnonzero(interior)))
    for sid, a in g.items():
        r['grids'][str(sid)] = dict(histogram=hist(a), interior_histogram=hist(a[interior]))
    # Full inventory preserves unknown section hashes/sizes instead of assuming them irrelevant.
    write_json(out / (path.stem + '.manifest.json'), m.manifest())
    write_json(out / (path.stem + '.json'), r)
    preview_image(m).save(out / (path.stem + '.png'))
    return r


def compare(left_path, right_path):
    a, b = MapFile(left_path.read_bytes()), MapFile(right_path.read_bytes())
    aa, bb = {s['id']: s for s in a.sections}, {s['id']: s for s in b.sections}
    result = dict(left=left_path.name, right=right_path.name,
                  description_changed=a.description != b.description,
                  preview_changed=a.preview != b.preview,
                  preview_extra_changed=a.preview_extra != b.preview_extra,
                  headers_changed=[k for k in a.headers if a.headers[k]['hex'] != b.headers[k]['hex']],
                  sections=[])
    for sid in sorted(set(aa) | set(bb)):
        if sid not in aa or sid not in bb:
            result['sections'].append(dict(id=sid, added_or_removed=True))
            continue
        sa, sb = aa[sid], bb[sid]
        if sa['raw'] == sb['raw']:
            continue
        x, y = sa['decoded'], sb['decoded']
        s = dict(id=sid, decoded_available=x is not None and y is not None)
        if x is not None and y is not None:
            n = min(len(x), len(y))
            offsets = np.flatnonzero(np.frombuffer(x[:n], dtype='u1') != np.frombuffer(y[:n], dtype='u1'))
            s.update(changed_bytes=int(len(offsets) + abs(len(x)-len(y))),
                     lengths=[len(x), len(y)], first_byte_offsets=offsets[:48].tolist())
            if not len(offsets) and len(x) == len(y):
                s['compressed_representation_only'] = True
            if sid in GRID_TYPES and len(x) == len(y):
                v, w = np.frombuffer(x, dtype=GRID_TYPES[sid]), np.frombuffer(y, dtype=GRID_TYPES[sid])
                indices = np.flatnonzero(v != w)
                pairs = Counter(zip(v[indices].tolist(), w[indices].tolist()))
                s.update(changed_cells=len(indices), bounds=bounds(indices),
                         transitions=[dict(before=k[0], after=k[1], count=c) for k,c in pairs.most_common(30)],
                         first_cells=[dict(index=int(i), x=int(XY[i,0]), y=int(XY[i,1]),
                                           before=int(v[i]), after=int(w[i])) for i in indices[:16]])
            for kind, layout in ENTITY_LAYOUTS.items():
                if sid == layout[0] and len(x) == len(y):
                    stride = layout[1]
                    slots = np.unique(offsets // stride)
                    field_offsets = Counter((offsets % stride).tolist())
                    s.update(object_kind=kind, changed_slots=slots.tolist(),
                             changed_fields=[dict(offset=k, slots=n) for k,n in field_offsets.most_common()])
            if len(offsets) <= 160 and len(x) == len(y):
                s['byte_changes'] = [[int(i), x[i], y[i]] for i in offsets]
        result['sections'].append(s)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pairs-only', action='store_true')
    args = parser.parse_args()
    paths = sorted([p for p in args.source.glob('*.map') if re.match(r'^ref_\d', p.name)],
                   key=lambda p: (p.stat().st_mtime_ns, p.name))
    require(bool(paths), 'No reference maps')
    args.output.mkdir(parents=True, exist_ok=args.pairs_only)
    snapshot = args.output / 'maps'
    if not args.pairs_only:
        snapshot.mkdir()
        provenance = []
        for p in paths:
            data = p.read_bytes()
            (snapshot / p.name).write_bytes(data)
            require(sha((snapshot / p.name).read_bytes()) == sha(data), 'Copy mismatch')
            provenance.append(dict(name=p.name, source=str(p.resolve()), bytes=len(data),
                                   sha256=sha(data), mtime_ns=p.stat().st_mtime_ns))
        write_json(args.output / 'provenance.json', provenance)
        out = args.output / 'survey'
        out.mkdir()
        inventory = []
        for i, p in enumerate(paths):
            r = survey(snapshot / p.name, out)
            inventory.append({k:v for k,v in r.items() if k not in ('grids','objects','description_hex','preview_extra_hex')})
            print('SURVEY', i+1, p.name, r['size'], r['opaque'],
                  {k:v['nonempty_records'] for k,v in r['objects'].items()}, flush=True)
        write_json(args.output / 'inventory.json', inventory)
        sheet = Image.new('RGB', (1000, ((len(paths)+3)//4)*240), '#151922')
        draw = ImageDraw.Draw(sheet)
        for i,p in enumerate(paths):
            x,y=(i%4)*250,(i//4)*240
            sheet.paste(Image.open(out/(p.stem+'.png')).resize((200,200)),(x+25,y))
            label=p.stem
            draw.text((x+5,y+203), label[:34], fill='white')
            if len(label)>34: draw.text((x+5,y+218),label[34:],fill='white')
        sheet.save(args.output/'previews.png')
    pairsdir=args.output/'pairs'
    pairsdir.mkdir(exist_ok=True)
    summaries=[]
    for i in range(1,len(paths)):
        left,right=snapshot/paths[i-1].name,snapshot/paths[i].name
        result=compare(left,right)
        name='%02d__%s__TO__%s.json'%(i,left.stem,right.stem)
        write_json(pairsdir/name,result)
        summaries.append(dict(left=left.name,right=right.name, report=name,
                              changed_sections=[s['id'] for s in result['sections']
                                                if s.get('changed_bytes',1)>0]))
        print('PAIR',i,right.name,flush=True)
    write_json(args.output/'pair_index.json',summaries)
    # Rehash live sources after the whole run. All operations above are read-only there.
    prov=json.loads((args.output/'provenance.json').read_text(encoding='utf-8'))
    for p in prov:
        require(sha(Path(p['source']).read_bytes())==p['sha256'],'Source changed during run')
    write_json(args.output/'source_integrity.json',dict(checked=len(prov), unchanged=True))


if __name__=='__main__':
    main()
