"""Read-only DE interpretation; numeric layouts researched in SHCDE Script Extender.

Source revision and field-level evidence: docs/SCRIPT_EXTENDER_FINDINGS.md.
Runtime names are interpretations, not permission to mutate linked game state.
"""
import argparse
import bisect
from collections import Counter
import json
from pathlib import Path
import struct

from maptool import MapFile, require, u32

ROW_COUNTS = [2 * min(y + 1, 800 - y) for y in range(800)]
ROW_STARTS = [0]
for count in ROW_COUNTS:
    ROW_STARTS.append(ROW_STARTS[-1] + count)


def tile_index(x, y):
    require(0 <= y < 800, 'Y outside storage')
    left = (800 - ROW_COUNTS[y]) // 2
    require(left <= x < left + ROW_COUNTS[y], 'X outside storage diamond')
    return ROW_STARTS[y] + x - left


def tile_xy(index):
    require(0 <= index < ROW_STARTS[-1], 'Tile index outside storage')
    y = bisect.bisect_right(ROW_STARTS, index) - 1
    return (800 - ROW_COUNTS[y]) // 2 + index - ROW_STARTS[y], y


# Factual flag positions from Interop/Enums/TileProperty.cs, including unknowns.
LOGIC_FLAGS = {
    0: 'Sea', 1: 'GoodsyardRelated', 2: 'IsFarm', 3: 'PitchTrap',
    4: 'RealityEdge', 5: 'MapBorder', 6: 'Unknown6', 7: 'ImpassableEdge',
    8: 'IsWall', 9: 'CrenelatedLow', 10: 'IsBuilding', 11: 'IsStairs',
    12: 'IsTree', 13: 'TreeProximity', 14: 'PlannedMoat', 15: 'IsLand',
    16: 'IsLowWall', 17: 'HasStone', 18: 'Unknown18', 19: 'HasIron',
    20: 'River', 21: 'Ford', 22: 'CrenelatedHigh', 23: 'Unknown23',
    24: 'IsWheat', 25: 'IsHops', 26: 'IsAppleFarm', 27: 'IsFarmFence',
    28: 'IsElevated', 29: 'IsSwamp', 30: 'IsMoat', 31: 'IsPitch',
}
SURFACE_FLAGS = dict(enumerate(('Foliage', 'DirtAndStones', 'Elevation1',
                              'Elevation2', 'OasisGrass', 'BeachOrWaves',
                              'CoarseSand', 'ThickFoliage')))
BUILDING_NAMES = {1: 'Hovel', 10: 'GoodsYard', 40: 'KeepOne', 41: 'KeepTwo',
                  42: 'KeepThree', 43: 'KeepFour', 44: 'KeepFive', 55: 'Campground',
                  71: 'KeepDoorLeft', 72: 'KeepDoorRight', 73: 'KeepDoor'}
BUILDING_NAMES.update({3:'Woodcutter',4:'Ox tether',5:'Iron mine',7:'Hunter’s post',
    11:'Armoury',12:'Fletcher',13:'Blacksmith',14:'Poleturner',15:'Armourer',16:'Tanner',
    17:'Bakery',18:'Brewery',19:'Granary',20:'Stone quarry',21:'Quarry stone pile',22:'Inn',
    30:'Wheat farm',31:'Hops farm',32:'Apple orchard',33:'Dairy farm',34:'Mill',
    36:'Small church',37:'Church',38:'Cathedral',45:'Large gate',46:'Small gate',49:'Drawbridge',
    74:'Lookout tower',75:'Perimeter tower',76:'Defense tower',77:'Square tower',78:'Round tower'})
BUILDING_NAMES.update({6:'Pitch rig',8:'Mercenary post',9:'Stone barracks',23:'Apothecary',
    24:'Engineers guild',25:'Tunnellers guild',26:'Market',27:'Well',28:'Oil smelter',35:'Stables',
    51:'Oil smelter parade ground',53:'Engineers parade ground',56:'Missile parade ground',
    57:'Light infantry parade ground',58:'Heavy infantry parade ground',59:'Tunnellers parade ground',
    62:'Gallows',63:'Stocks',65:'Maypole',66:'Garden',67:'Killing pit',70:'Water pot',
    91:'Cesspit',92:'Burning stake',93:'Gibbet',94:'Dungeon',95:'Stretching rack',
    97:'Chopping block',98:'Dunking stool',99:'War dog cage',100:'Statue',101:'Shrine',
    103:'Dancing bear',108:'Bedouin stockade'})
# FILE layouts, empirically checked on 2026-09-19 references, NOT runtime offsets.
# Vegetation semantic fields are 12 bytes earlier than the SE runtime struct;
# unit semantic fields below are 4 bytes later. Never apply a blanket relocation
# to every field (graphics headers differ independently).
# sid, stride, alive, type, global id, x, y, packed tile id, reference layer
ENTITY_LAYOUTS = {
    'buildings': (4013, 812, 0xD0, 0xD2, 0xD8, 0xEE, 0xF0, 0xF4, 3012),
    'vegetation': (1014, 156, 0x44, 0x46, 0x4C, 0x62, 0x64, 0x68, 3004),
    'units': (3015, 1168, 0x8C, 0x8E, 0x98, 0xC4, 0xC6, 0xD4, 3010),
}


def flags(value, definitions):
    return [name for bit, name in definitions.items() if value & (1 << bit)]


def decoded(map_file, sid):
    data = map_file.section(sid)['decoded']
    require(data is not None, 'Section %d is opaque' % sid)
    return data


def entity_report(map_file, layout):
    sid, stride, alive, kind, gid, xo, yo, tid, grid_id = layout
    blob = decoded(map_file, sid)
    require(len(blob) % stride == 0, 'Entity array size mismatch')
    layer = decoded(map_file, grid_id)
    require(len(layer) == 320800 * 2, 'Unexpected reference layer size')
    refs = Counter(v for (v,) in struct.iter_unpack('<H', layer) if v)
    records = []
    # Slot zero is reserved; unit references show that its nonzero copy of a lord
    # is not an additional placed unit.
    for slot in range(1, len(blob) // stride):
        offset = slot * stride
        h = lambda o: struct.unpack_from('<H', blob, offset + o)[0]
        i = lambda o: u32(blob, offset + o)
        state = h(alive)
        if state in (0, 3):
            continue
        x, y, index = h(xo), h(yo), i(tid)
        try:
            coordinates_match = tile_index(x, y) == index
        except ValueError:
            coordinates_match = False
        rec = dict(slot=slot, state=state, type=h(kind), global_id=i(gid),
                   x=x, y=y, tile_id=index, coordinates_match=coordinates_match,
                   referenced_tiles=refs[slot],
                   anchor_reference=struct.unpack_from('<H', layer, index * 2)[0]
                   if 0 <= index < 320800 else None)
        if sid == 4013:
            rec.update(owner=h(0xD6), footprint_size=i(0xF8),
                       type_name=BUILDING_NAMES.get(h(kind), 'Unknown_%d' % h(kind)))
        records.append(rec)
    slots = {r['slot'] for r in records}
    return dict(section=sid, stride=stride, capacity=len(blob) // stride,
                active_count=len(records), coordinate_matches=sum(r['coordinates_match'] for r in records),
                reference_layer=grid_id, distinct_referenced_slots=len(refs),
                referenced_inactive_or_missing_slots=sorted(set(refs) - slots), records=records)


def analyze(map_file):
    require(map_file.capacity == 200 and map_file.version >= 200,
            'Semantic decoding currently supports DE layout only; legacy data stays raw')
    logic = decoded(map_file, 3003)
    surface = decoded(map_file, 3037)
    require(len(logic) == 320800 * 4 and len(surface) == 320800, 'Unexpected grid lengths')
    values = [v for (v,) in struct.iter_unpack('<I', logic)]
    hist = Counter(values)
    report = dict(version=map_file.version, map_size=u32(decoded(map_file, 1050)),
                  interpretation='SE runtime layouts cross-checked against file data; read-only',
                  logic_flag_counts={name: sum(n for v, n in hist.items() if v & (1 << bit))
                                     for bit, name in LOGIC_FLAGS.items()},
                  surface_values=[dict(value=v, count=n, flags=flags(v, SURFACE_FLAGS))
                                  for v, n in Counter(surface).most_common()],
                  entities={name: entity_report(map_file, layout) for name, layout in ENTITY_LAYOUTS.items()})
    return report


def render(map_file, path):
    """Schematic semantic view; colors are chosen here, not extracted game assets."""
    from PIL import Image, ImageDraw
    logic = [v for (v,) in struct.iter_unpack('<I', decoded(map_file, 3003))]
    surface = decoded(map_file, 3037)
    require(len(logic) == len(surface) == 320800, 'Unexpected grid lengths')
    picture = Image.new('RGB', (1060, 800), '#10151d')
    pixels = picture.load()
    for index, value in enumerate(logic):
        col = (179, 151, 103)
        if surface[index] & 16:
            col = (107, 156, 69)
        if surface[index] & 128:
            col = (61, 104, 48)
        for bit, color in [(17, (195, 201, 209)), (19, (139, 83, 57)),
                           (12, (28, 77, 39)), (20, (48, 126, 174)),
                           (0, (31, 85, 146)), (31, (65, 48, 65)),
                           (8, (118, 105, 88)), (10, (222, 179, 72))]:
            if value & (1 << bit):
                col = color
        if value & ((1 << 4) | (1 << 5)):
            col = (30, 37, 48)
        pixels[tile_xy(index)] = col
    draw = ImageDraw.Draw(picture)
    draw.text((820, 24), 'DE MAP / semantic view', fill='white')
    draw.text((820, 46), 'Interpretation: Script Extender', fill='#aab7c5')
    for row, (name, color) in enumerate([
        ('Oasis (surface bit 4)', '#6b9c45'), ('Stone (logic bit 17)', '#c3c9d1'),
        ('Iron (logic bit 19)', '#8b5339'), ('Vegetation (bit 12)', '#1c4d27'),
        ('River (bit 20)', '#307eae'), ('Sea (bit 0)', '#1f5592'),
        ('Pitch (bit 31)', '#413041'), ('Building (bit 10)', '#deb348')]):
        yy = 95 + row * 28
        draw.rectangle((820, yy, 835, yy + 15), fill=color)
        draw.text((845, yy + 2), name, fill='white')
    draw.text((820, 360), 'Schematic colors, no game sprites', fill='#aab7c5')
    picture.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    map_file = MapFile(args.map.read_bytes())
    report = analyze(map_file)
    args.folder.mkdir(parents=True, exist_ok=False)
    (args.folder / 'semantics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    render(map_file, args.folder / 'terrain.png')
    print(json.dumps({name: {k: v for k, v in item.items() if k != 'records'}
                      for name, item in report['entities'].items()}, indent=2))


if __name__ == '__main__':
    main()
