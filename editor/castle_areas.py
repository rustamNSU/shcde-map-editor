"""Read-only castle overlays reconstructed from the pinned native DLL.

Build radius: RVA 0x6AF00/0xEEF90. Terrain clearing: keep constructor
0x74DA0, brush 0x6FE90 and cardinal point enumeration 0xE3360.
The clearing result is a warning footprint: a cached beach-neighbor check and
the order in which the game recreates buildings can further suppress changes.
"""
import struct
from collections import deque
import numpy as np
from .services import EntityService


CASTLE_AREA_RADIUS = {160:45, 200:50, 300:60, 400:70, 500:80,
                      600:90, 700:100, 800:100}
_CAMP_OFFSETS = ((0,8),(8,0),(0,-8),(-8,0),
                 (0,8),(8,0),(0,-8),(-8,0),
                 (2,12),(12,2),(2,-12),(-12,2),
                 (7,2),(2,-5),(-5,0),(0,7),
                 (7,2),(2,-5),(-5,0),(0,7))
_ENTRANCE_OFFSETS = {2:(-1,3), 4:(3,-1), 6:(7,3)}


def native_build_radius(map_size):
    """Native size switch, including its default for non-preset sizes."""
    return CASTLE_AREA_RADIUS.get(map_size, 70)


def _orientation(document, row):
    if 'slot' not in row:
        return 15
    raw = document.section(4013)['decoded']
    return struct.unpack_from('<H', raw, row['slot']*812+0x92)[0]


def keep_build_center(document, keep):
    """The player's keep access tile, never an eight-unit world coordinate."""
    raw = document.section(2022)['decoded']
    at = keep['owner']*0x583c+0x94
    if raw is not None and at+12 <= len(raw):
        slot,x,y = struct.unpack_from('<III', raw, at)
        if slot == keep.get('slot') and 0 <= x < 800 and 0 <= y < 800:
            return x,y
    dx,dy = _ENTRANCE_OFFSETS.get(_orientation(document, keep), (3,7))
    return keep['x']+dx,keep['y']+dy


def castle_parts(document):
    """Match child records by their parent slot, including rotated castles."""
    records = EntityService(document).records('buildings')
    raw = document.section(4013)['decoded']
    for keep in records:
        if keep['type'] not in range(40,45) or not 1 <= keep['owner'] <= 8:
            continue
        orientation = _orientation(document, keep)
        rotation = orientation//2 if orientation in (0,2,4,6) else 0
        dx,dy = _CAMP_OFFSETS[(keep['type']-40)*4+rotation]
        camp_position = keep['x']+dx,keep['y']+dy
        # Geometric fallback also supports schematic callers without raw slots.
        expected = {(keep['x']+2,keep['y']+7):71,
                    (keep['x']+3,keep['y']+7):73,
                    (keep['x']+4,keep['y']+7):72}
        children = []
        for row in records:
            if row['owner'] != keep['owner'] or row['type'] not in (55,71,72,73):
                continue
            parent = (struct.unpack_from('<H', raw, row['slot']*812+0x192)[0]
                      if 'slot' in row else None)
            linked = parent is not None and parent == keep.get('slot')
            geometric = ((row['type'] == 55 and (row['x'],row['y']) == camp_position)
                         or ('slot' not in row and rotation == 0 and
                             expected.get((row['x'],row['y'])) == row['type']))
            if linked or geometric:
                children.append(row)
        yield keep['owner'],[keep]+children,keep_build_center(document, keep)


def _expanded_parts(document, parts, radius):
    """Union of native cardinal BFS brushes, including map-border clipping."""
    chosen = []
    g = document.geometry
    for row in parts:
        if row['type'] not in set(range(40,45)) | {55}:
            continue
        side = int(row.get('footprint_size',7))
        if not 1 <= side <= 32:
            continue
        x,y = row['x'],row['y']
        ids = g.rectangle(x-radius,y-radius,side+2*radius,side+2*radius)
        dx = np.maximum(np.maximum(x-g.x[ids],g.x[ids]-(x+side-1)),0)
        dy = np.maximum(np.maximum(y-g.y[ids],g.y[ids]-(y+side-1)),0)
        inside=ids[dx+dy <= radius]
        if len(inside) and np.all((document.grid(3003)[inside] & 0x30) == 0):
            chosen.append(inside)
            continue
        # E3360 counts discovered border cells but never expands them. Close
        # to a boundary its first85/13 points can extend beyond a clipped
        # radius6/2 diamond, so enumerate the same ordered queue there.
        points=[]
        for yy in range(y,y+side):
            for xx in range(x,x+side):
                points.extend(_native_brush_indices(document,xx,yy,1+2*radius*(radius+1)))
        chosen.append(np.asarray(points,dtype=np.int64))
    return np.unique(np.concatenate(chosen)) if chosen else np.empty(0,dtype=np.int64)


def _native_brush_indices(document, x, y, count):
    g=document.geometry
    if not (0 <= x < 800 and 0 <= y < 800) or g.index_grid[y,x] < 0:
        return []
    first=int(g.index_grid[y,x])
    found=[first]
    seen={first}
    queue=deque([(x,y,first)])
    logic=document.grid(3003)
    while queue and len(found) < count:
        xx,yy,index=queue.popleft()
        if int(logic[index]) & 0x30:
            continue
        for dx,dy in ((0,-1),(1,0),(0,1),(-1,0)):
            nx,ny=xx+dx,yy+dy
            if not (0 <= nx < 800 and 0 <= ny < 800):
                continue
            neighbor=int(g.index_grid[ny,nx])
            if neighbor < 0 or neighbor in seen:
                continue
            found.append(neighbor)
            if len(found) == count:
                break
            seen.add(neighbor)
            queue.append((nx,ny,neighbor))
    return found


def _eligible(document, ids, ordinary):
    """Proven per-cell predicates; the native cached beach guard is additional."""
    if not len(ids):
        return ids
    logic = document.grid(3003)[ids]
    allowed = (document.geometry.playable[ids] &
               ((logic & 0x70300501) == 0) &
               (document.grid(3012)[ids] == 0) &
               (document.grid(3004)[ids] == 0))
    if ordinary:
        allowed &= ((logic & 0xa0080) == 0) & ((document.grid(3037)[ids] & 0x20) == 0)
    return ids[allowed]


def _clear_indices(document, keep, parts, origin_surface=None):
    try:
        origin = document.geometry.index(keep['x'],keep['y'])
    except ValueError:
        return np.empty(0,dtype=np.int64)
    surface=int(document.grid(3037)[origin]) if origin_surface is None else origin_surface
    ordinary = surface & 0x90 == 0
    return _eligible(document,_expanded_parts(document,parts,6 if ordinary else 2),ordinary)


def existing_clear_indices(document):
    """Cells potentially repainted on castle recreation; no grids are changed."""
    choices = [_clear_indices(document,parts[0],parts)
               for owner,parts,center in castle_parts(document)]
    return np.unique(np.concatenate(choices)) if choices else np.empty(0,dtype=np.int64)


def prospective_rewrite_indices(document, x, y):
    """Warning footprint for the current castle prefab anchored at ``x,y``."""
    from .buildings import catalog
    prefab = catalog()['castle']
    dx,dy = x-prefab['anchor'][0],y-prefab['anchor'][1]
    parts = []
    for record in prefab['records']:
        if record['kind'] != 'buildings':
            continue
        raw = bytes.fromhex(record['data'])
        kind = struct.unpack_from('<H',raw,0xd2)[0]
        if kind not in set(range(40,45)) | {55}:
            continue
        xx,yy = struct.unpack_from('<HH',raw,0xee)
        parts.append(dict(type=kind,x=xx+dx,y=yy+dy,
                          footprint_size=struct.unpack_from('<I',raw,0xf8)[0]))
    keep = next(row for row in parts if row['type'] in range(40,45))
    # The prefab writes its own surface under the keep. Predict the serialized
    # map's startup recreation, rather than the terrain hidden by that prefab.
    relative=(keep['x']-x,keep['y']-y)
    index=[tuple(cell) for cell in prefab['cells']].index(relative)
    surface=int(prefab['grids']['3037'][index])
    return _clear_indices(document,keep,parts,surface)
