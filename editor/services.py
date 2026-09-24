"""Shared semantic operations. No Qt, filesystem writes or implicit game access."""
import struct
import numpy as np
from semantics import ENTITY_LAYOUTS, entity_report

MATERIALS = {
    'earth': (0, '#bca775'), 'oasis': (16, '#78a365'),
    'sand': (64, '#daca96'), 'scrub': (1, '#9b9d62'),
    'thick_scrub': (128, '#68794d'), 'earth_stones': (2, '#aa9e86'),
    'stone': (0, '#adb5bd'), 'iron': (0, '#956753'),
    'marsh': (0, '#5c7663'),
}


class TerrainService:
    def __init__(self, document):
        self.document = document

    def paint(self, indices, material, experimental=False, variation=None):
        if material not in MATERIALS:
            raise ValueError('Unsupported material: ' + str(material))
        resource = material in ('stone', 'iron')
        if variation is not None:
            VariationService.validate_value(variation)
        d = self.document
        if d.size not in (400, 500):
            raise ValueError('Editing is currently limited to map sizes 400 and 500')
        ids = np.unique(np.asarray(indices, dtype=np.int64))
        if np.any(ids < 0) or np.any(ids >= d.geometry.count):
            raise ValueError('Invalid tile index')
        logic, surface = d.grid(3003), d.grid(3037)
        # Start with known flat, unoccupied land; never clear buildings, units,
        # trees, water, boundary flags or unrecognized terrain by painting over it.
        eligible = (d.geometry.playable[ids] & np.isin(logic[ids], [0x8000, 0x28000, 0x88000, 0x20008000]) &
                    np.isin(surface[ids], [0, 1, 2, 16, 64, 128]) &
                    (d.grid(3005)[ids] == 8) & (d.grid(3045)[ids] == 8) &
                    (d.grid(3012)[ids] == 0) & (d.grid(3004)[ids] == 0) &
                    (d.grid(3010)[ids] == 0))
        # A populated save has units that are absent from the occupancy grid.
        units = EntityService(d).records('units')
        occupied = [u['tile_id'] for u in units if u['coordinates_match']]
        if occupied:
            eligible &= ~np.isin(ids, occupied)
        allowed = ids[eligible]
        changed = 0
        with d.transaction('Paint ' + material.replace('_', ' ')):
            if material=='marsh':
                changed += d.change(3003, allowed, 0x20008000, 'Marsh')
                changed += d.change(3007, allowed, 16, 'Marsh display')
            elif resource:
                changed += d.change(3003, allowed, 0x28000 if material == 'stone' else 0x88000, 'Resource')
                changed += d.change(3007, allowed, 2064, 'Resource display')
            else:
                resource_ids = allowed[np.isin(logic[allowed], [0x28000, 0x88000, 0x20008000])]
                changed += d.change(3003, resource_ids, 0x8000, 'Clear resource')
                changed += d.change(3007, resource_ids, 16, 'Clear resource display')
            changed += d.change(3037, allowed, MATERIALS[material][0], 'Surface')
            if variation is not None:
                changed += d.change(3008, allowed, variation, 'Texture variation')
        return {'requested_cells': len(ids), 'eligible_cells': len(allowed),
                'skipped_cells': int((~eligible).sum()), 'changed_field_values': changed,
                'experimental': False}

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
        if d.size not in (400,500): raise ValueError('Variation editing supports 400 and 500 maps')
        ids=np.unique(np.asarray(indices,dtype=np.int64))
        if np.any(ids<0) or np.any(ids>=d.geometry.count): raise ValueError('Invalid tile index')
        allowed=ids[d.geometry.playable[ids]]
        with d.transaction('Set texture variation'):
            changed=d.change(3008,allowed,value,'Texture variation')
        return dict(eligible_cells=len(allowed), skipped_cells=len(ids)-len(allowed),changed_field_values=changed)


class HeightService:
    """Height-only terrain experiments: preserve unknown derived terrain fields."""
    def __init__(self,document):
        self.document=document

    def paint(self,indices,height):
        if type(height) is not int or not 0<=height<=255:
            raise ValueError('Height must be a whole number from 0 to 255')
        d=self.document
        if d.size not in (400,500): raise ValueError('Height editing supports 400 and 500 maps')
        ids=np.unique(np.asarray(indices,dtype=np.int64))
        if np.any(ids<0) or np.any(ids>=d.geometry.count): raise ValueError('Invalid tile index')
        eligible=(d.geometry.playable[ids] & np.isin(d.grid(3003)[ids],
                  [0,0x80,0x8000,0x8080,0x10000000,0x10000080,0x10008000,0x10008080]) &
                  (d.grid(3005)[ids]==d.grid(3045)[ids]))
        for sid in (3012,3010,3004): eligible &= d.grid(sid)[ids]==0
        units=[r['tile_id'] for r in EntityService(d).records('units') if r['coordinates_match']]
        if units: eligible &= ~np.isin(ids,units)
        allowed=ids[eligible]
        with d.transaction('Set terrain height to %s' % height):
            changed=d.change(3005,allowed,height,'Current height')
            changed+=d.change(3045,allowed,height,'Base height')
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
        if d.size not in (400, 500):
            warnings.append('New-map presets cover 400 and 500; this imported size is inspection-only')
        for sid in changed:
            from .document import GRID_TYPES, ENTITY_SECTIONS
            if sid not in GRID_TYPES and sid not in ENTITY_SECTIONS:
                errors.append('Unsupported changed section %s' % sid)
            if sid not in GRID_TYPES:
                continue
            orig = np.frombuffer(d.container.section(sid)['decoded'], dtype=d.grid(sid).dtype)
            if np.any(orig[~d.geometry.playable] != d.grid(sid)[~d.geometry.playable]):
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
            warnings.append('Experimental heights: steep edges may glitch or block movement; derived terrain layers are not rebuilt')
        if not any(r['type'] in range(40, 45) for r in EntityService(d).records('buildings')):
            warnings.append('No starting castles: this is an editor map, not a ready-to-play skirmish')
        return {'valid': not errors, 'errors': errors, 'warnings': warnings,
                'changed_sections': changed, 'map_size': d.size}
