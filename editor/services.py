"""Shared semantic operations. No Qt, filesystem writes or implicit game access."""
import struct
import numpy as np
from semantics import ENTITY_LAYOUTS, entity_report
from .geometry import SUPPORTED_MAP_SIZES

MATERIALS = {
    'earth': (0, '#bca775'), 'oasis': (16, '#78a365'),
    'sand': (64, '#daca96'), 'scrub': (1, '#9b9d62'),
    'thick_scrub': (128, '#68794d'), 'earth_stones': (2, '#aa9e86'),
    'stone': (0, '#adb5bd'), 'iron': (0, '#956753'),
    'marsh': (0, '#5c7663'),
    'sea': (0, '#316b97'), 'river': (0, '#4b91ad'),
    'ford': (0, '#83b5ba'), 'beach': (32, '#e1ce97'),
    'pitch': (0, '#514c43'), 'rocks': (0, '#74716b'),
    'middle_plateau': (4, '#ab936e'), 'high_plateau': (8, '#c5b28d'),
}


TERRAIN_LOGIC_BITS = (1 | 0x80 | 0x2000 | 0x8000 | 0x20000 | 0x80000 |
                      0x100000 | 0x200000 | 0x20000000 | 0x80000000)


def terrain_eligible(document, ids, height=False):
    """Known terrain only; preserve objects, reserved flags and actual unit records."""
    d=document;logic=d.grid(3003)[ids]
    eligible=d.geometry.playable[ids] & ((logic & np.uint32(0xffffffff ^ TERRAIN_LOGIC_BITS))==0)
    if height:
        # Native height brushes exclude sea/swamp/moat/structures. Keep water
        # depth semantics separate from absolute-valued height mask painting.
        eligible &= (logic & np.uint32(0xa0300001))==0
        eligible &= d.grid(3005)[ids]==d.grid(3045)[ids]
    for sid in (3012,3010,3004):eligible &= d.grid(sid)[ids]==0
    occupied=[u['tile_id'] for u in EntityService(d).records('units') if u['coordinates_match']]
    if occupied:eligible &= ~np.isin(ids,occupied)
    return eligible


def edit_indices(document, indices):
    if document.size not in SUPPORTED_MAP_SIZES:
        raise ValueError('Unsupported native map size')
    ids=np.unique(np.asarray(indices,dtype=np.int64))
    if np.any(ids<0) or np.any(ids>=document.geometry.count):raise ValueError('Invalid tile index')
    return ids


class TerrainService:
    def __init__(self, document):
        self.document = document

    def paint(self, indices, material, experimental=False, variation=None):
        if material not in MATERIALS:
            raise ValueError('Unsupported material: ' + str(material))
        if variation is not None:
            VariationService.validate_value(variation)
        d = self.document
        ids=edit_indices(d,indices)
        logic=d.grid(3003)
        eligible=terrain_eligible(d,ids)
        allowed = ids[eligible]
        changed = 0
        with d.transaction('Paint ' + material.replace('_', ' ')):
            # Explicit base-layer behavior from native6FE90/6FA10. Tree
            # proximity is independent of the painted material and stays intact.
            old_logic=logic[allowed].copy()
            proximity=old_logic&np.uint32(0x2000)
            flags={'sea':1,'river':0x100000,'ford':0x200000,'stone':0x28000,
                   'iron':0x88000,'rocks':0x8080,'marsh':0x20008000,'pitch':0xa0008000}.get(material,0x8000)
            changed+=d.change(3003,allowed,proximity|np.uint32(flags),'Terrain properties')
            if material in ('sea','beach','marsh','pitch','middle_plateau','high_plateau'):
                value={'sea':0,'beach':0,'marsh':8,'pitch':8,'middle_plateau':80,'high_plateau':130}[material]
                changed+=d.change(3005,allowed,value,'Current height')
                changed+=d.change(3045,allowed,value,'Base height')
            elif material in ('river','ford'):
                # The native brush lowers current height only when >=8, and
                # retains default height (including pre-existing beach zero).
                values=d.grid(3005)[allowed].astype(np.int16)
                values=np.where(values>=8,d.grid(3045)[allowed].astype(np.int16)-8,values).clip(0,255)
                changed+=d.change(3005,allowed,values,'Water depth')
            else:
                # Ordinary textures work on hills. Recover former water cells
                # without flattening already elevated terrain.
                water=allowed[(old_logic&np.uint32(0x300001))!=0]
                values=np.maximum(8,d.grid(3045)[water])
                changed+=d.change(3005,water,values,'Restore land height')
                changed+=d.change(3045,water,values,'Restore land base height')
            changed+=d.change(3007,allowed,2064 if material in ('stone','iron','rocks') else 16,'Terrain display')
            changed += d.change(3037, allowed, MATERIALS[material][0], 'Surface')
            if variation is not None:
                changed += d.change(3008, allowed, variation, 'Texture variation')
        return {'requested_cells': len(ids), 'eligible_cells': len(allowed),
                'skipped_cells': int((~eligible).sum()), 'changed_field_values': changed,
                'experimental': material in ('sea','river','ford','beach','rocks','middle_plateau','high_plateau')}

    def inspect(self, x, y):
        d = self.document
        i = d.geometry.index(x, y)
        return {'x': x, 'y': y, 'index': i, 'playable': bool(d.geometry.playable[i]),
                'surface': int(d.grid(3037)[i]), 'height': int(d.grid(3005)[i]),
                'texture_noise': int(d.grid(3008)[i]),
                'base_height': int(d.grid(3045)[i]), 'logic': hex(int(d.grid(3003)[i])),
                'building_slot': int(d.grid(3012)[i]), 'unit_grid_slot': int(d.grid(3010)[i])}


class VariationService:
    """Edit only the per-cell uint16 texture variation; preserve all other data."""
    def __init__(self, document):
        self.document=document

    @staticmethod
    def validate_value(value):
        if type(value) is not int or not 0 <= value <= 65535:
            raise ValueError('Texture variation must be a whole number from 0 to 65535')

    def paint(self, indices, value):
        self.validate_value(value)
        d=self.document
        ids=edit_indices(d,indices)
        allowed=ids[d.geometry.playable[ids]]
        with d.transaction('Set texture variation'):
            changed=d.change(3008,allowed,value,'Texture variation')
        return dict(eligible_cells=len(allowed), skipped_cells=len(ids)-len(allowed),changed_field_values=changed)


class HeightService:
    """Absolute terrain heights; the document rebuilds native navigation on commit."""
    def __init__(self,document):
        self.document=document

    def paint(self,indices,height):
        if type(height) is not int or not 0<=height<=255:
            raise ValueError('Height must be a whole number from 0 to 255')
        ids=edit_indices(self.document,indices)
        return self.paint_values(ids,np.full(len(ids),height,dtype=np.uint8))

    def paint_values(self,indices,heights):
        d=self.document
        ids=np.asarray(indices,dtype=np.int64)
        values=np.asarray(heights)
        if ids.ndim!=1 or values.ndim!=1 or len(ids)!=len(values):
            raise ValueError('Each cell must have one corresponding height')
        if len(np.unique(ids))!=len(ids):raise ValueError('Duplicate height mask cells')
        edit_indices(d,ids)
        if len(values) and (values.dtype.kind not in 'iu' or np.any(values<0) or np.any(values>255)):
            raise ValueError('Heights must be whole numbers from 0 to 255')
        eligible=terrain_eligible(d,ids,height=True);allowed=ids[eligible];values=values[eligible]
        with d.transaction('Set terrain heights'):
            changed=d.change(3005,allowed,values,'Current height')
            changed+=d.change(3045,allowed,values,'Base height')
            # Both native height brushes clear old rocks/cliff bits before the
            # deferred visual pass. Do not invent the unported cliff graphics.
            changed+=d.change(3003,allowed,d.grid(3003)[allowed]&np.uint32(0xffffff7f),'Clear previous cliff flags')
        return dict(eligible_cells=len(allowed),skipped_cells=int((~eligible).sum()),
                    changed_field_values=changed,experimental=True)


class EntityService:
    def __init__(self, document):
        self.document = document

    def records(self, kind):
        if kind not in ENTITY_LAYOUTS:
            raise ValueError('Unknown entity kind')
        d = self.document
        cache = getattr(d, '_entity_cache', None)
        if cache is None or getattr(d, '_entity_cache_revision', -1) != d.revision:
            cache = d._entity_cache = {}
            d._entity_cache_revision = d.revision
        if kind not in cache:
            rows = entity_report(d, ENTITY_LAYOUTS[kind])['records']
            if kind == 'units':
                raw = d.section(3015)['decoded']
                for row in rows:
                    at = row['slot'] * 1168
                    row['owner'] = struct.unpack_from('<I', raw, at+0x80)[0]
                    row['hp_candidate'] = struct.unpack_from('<I', raw, at+0x3c8)[0]
            cache[kind] = rows
        return cache[kind]

    def at(self, x, y):
        result = []
        for kind in ENTITY_LAYOUTS:
            for row in self.records(kind):
                side = row.get('footprint_size', 1)
                if row['x'] <= x < row['x']+side and row['y'] <= y < row['y']+side:
                    result.append(dict(row, kind=kind))
        return result


class MapValidator:
    @staticmethod
    def validate(document):
        d = document
        errors, warnings = [], []
        changed = sorted(d.replacements())
        if d.size not in SUPPORTED_MAP_SIZES:
            warnings.append('Unrecognized map size: editing is unavailable')
        for sid in changed:
            from .document import GRID_TYPES, ENTITY_SECTIONS
            if sid not in GRID_TYPES and sid not in ENTITY_SECTIONS:
                errors.append('Unsupported changed section %s' % sid)
            if sid not in GRID_TYPES:
                continue
            orig = np.frombuffer(d.container.section(sid)['decoded'], dtype=d.grid(sid).dtype)
            if sid not in (3030,3021) and np.any(orig[~d.geometry.playable] != d.grid(sid)[~d.geometry.playable]):
                errors.append('Boundary cells changed in section %s' % sid)
        if any(sid in changed for sid in (4013,3015,1014)):
            gids=[]
            for kind, layout in ENTITY_LAYOUTS.items():
                report=entity_report(d,layout)
                if report['referenced_inactive_or_missing_slots']:
                    errors.append('Dangling '+kind+' references')
                if report['active_count'] != report['coordinate_matches']:
                    errors.append('Invalid '+kind+' coordinates')
                gids.extend(r['global_id'] for r in report['records'])
            if len(gids)!=len(set(gids)):
                errors.append('Duplicate entity global IDs')
            if 4013 in changed:
                from .buildings import H,I
                raw=d.section(4013)['decoded']; original=d.container.section(4013)['decoded']
                rows=EntityService(d).records('buildings')
                for keep in (r for r in rows if r['type']==41):
                    start=keep['slot']*812
                    if raw[start:start+812]==original[start:start+812]: continue
                    parts=[r for r in rows if r['owner']==keep['owner'] and
                           (r['slot']==keep['slot'] or (r['type'] in (55,71,72,73) and
                            H(raw,r['slot']*812+0x192)==keep['slot']))]
                    piles=[r for r in rows if r['type']==10 and r['owner']==keep['owner'] and
                           (r['x']-keep['x'],r['y']-keep['y']) in ((7,2),(10,2),(7,5),(10,5))]
                    first=next((r for r in piles if (r['x'],r['y'])==(keep['x']+7,keep['y']+2)),None)
                    if any(I(raw,r['slot']*812+0x2a8)!=keep['global_id'] for r in parts):
                        errors.append('Castle has stale building group IDs')
                    if first and any(I(raw,r['slot']*812+0x2a8)!=first['global_id'] for r in piles):
                        errors.append('Castle has stale stockpile group IDs')
        opaque = [s['id'] for s in d.container.sections if s['error'] and s['id'] not in changed]
        if any(s['error'] and s['id'] in changed for s in d.container.sections):
            warnings.append('Lord lookup rebuilt from cross-checked player and lord records')
        if opaque:
            warnings.append('Opaque sections preserved unchanged: ' + str(opaque))
        if changed:
            warnings.append('Export generates a schematic map preview; embedded source filename is retained')
            warnings.append('Edited gameplay behavior needs in-game verification; derived-layer rules are incomplete')
        if 4013 in changed:
            warnings.append('Experimental building edits: static reference layouts; pathfinding needs game verification')
        if 3005 in changed or 3045 in changed:
            warnings.append('Native navigation edges and components are rebuilt; visual cliffs and other terrain graphics passes are incomplete')
        if not any(r['type'] in range(40, 45) for r in EntityService(d).records('buildings')):
            warnings.append('No starting castles: this is an editor map, not a ready-to-play skirmish')
        return {'valid': not errors, 'errors': errors, 'warnings': warnings,
                'changed_sections': changed, 'map_size': d.size}
