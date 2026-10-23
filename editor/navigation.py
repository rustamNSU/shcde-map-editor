"""Offline native-rule navigation rebuild, saved as one undoable document edit.

Source: pinned CrusaderDE.dll D86F0, DAA50, DE6A0 and E49D0. This loads
our own compiled port, never the installed game library or a running process.
"""
import ctypes
import struct
from pathlib import Path
import numpy as np
from .geometry import MapGeometry

TOPOLOGY_SECTIONS = frozenset((3003, 3005, 3004, 3012, 3020, 4013, 1014))
_library = None
_neighbors = None


def neighbors():
    global _neighbors
    if _neighbors is None:
        g = MapGeometry
        rows = []
        for dx, dy in ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)):
            x, y = g.x + dx, g.y + dy
            valid = (x >= 0) & (x < 800) & (y >= 0) & (y < 800)
            row = np.full(g.count, -1, dtype=np.int32)
            row[valid] = g.index_grid[y[valid], x[valid]]
            rows.append(row)
        _neighbors = np.ascontiguousarray(np.stack(rows, axis=1))
        _neighbors.flags.writeable = False
    return _neighbors


def _native():
    global _library
    if _library is None:
        path = Path(__file__).resolve().parent / 'assets/native/navigation.dll'
        _library = ctypes.CDLL(str(path))
        fn = _library.rebuild_navigation
        fn.argtypes = [ctypes.c_int] + [ctypes.c_void_p] * 9 + [ctypes.c_int]
        fn.restype = ctypes.c_int
        _library.label_components.argtypes = [ctypes.c_int] + [ctypes.c_void_p] * 5
        _library.label_components.restype = ctypes.c_int
    return _library.rebuild_navigation


def calculate(document):
    d = document
    slots = d.grid(3012)
    buildings = np.frombuffer(d.section(4013)['decoded'], dtype=np.uint8).reshape(-1, 812)
    type_by_slot = buildings[:, 0xd2:0xd4].copy().view('<i2').ravel()
    if np.any(slots >= len(type_by_slot)):
        raise ValueError('Invalid building slot in navigation grid')
    types = np.ascontiguousarray(type_by_slot[slots])
    veg_slots = d.grid(3004)
    trees = np.frombuffer(d.section(1014)['decoded'], dtype=np.uint8).reshape(-1, 156)
    tree_types = trees[:, 0x46:0x48].copy().view('<i2').ravel()
    if np.any(veg_slots >= len(tree_types)):
        raise ValueError('Invalid vegetation slot in navigation grid')
    t = tree_types[veg_slots]
    tree_pass = np.asarray((veg_slots != 0) & (t >= 5) & (t != 15), dtype=np.uint8)
    edges = np.zeros(d.geometry.count, dtype=np.uint8)
    components = np.zeros(d.geometry.count, dtype=np.uint16)
    arrays = (d.grid(3003), d.grid(3005), d.grid(3020), slots, types, tree_pass,
              neighbors(), edges, components)
    count = _native()(d.geometry.count, *(a.ctypes.data for a in arrays), 1)
    gates = [row for row in buildings[1:] if int.from_bytes(row[0xd0:0xd2], 'little')
             and int.from_bytes(row[0xd2:0xd4], 'little') in (45, 46, 47)]
    if gates:
        _gate_edges(d, edges, gates, tree_pass, closed=False)
        # C4BF0 temporarily closes every gate before the component flood fill.
        component_edges = edges.copy()
        _gate_edges(d, component_edges, gates, tree_pass, closed=True)
        count = _library.label_components(d.geometry.count,
            *(a.ctypes.data for a in (d.grid(3003), tree_pass, neighbors(), component_edges, components)))
    return edges, components, count


def _gate_edges(d, edges, gates, tree_pass, closed):
    """D8CE0: two entrance links, with C4BF0's temporary closed-state pass."""
    logic, base, current = d.grid(3003), d.grid(3045), d.grid(3005)
    def index(x, y):
        if not (0 <= x < 800 and 0 <= y < 800): return -1
        return int(d.geometry.index_grid[y, x])
    def link(a, b, out_bit, in_bit, blocked):
        if a < 0 or b < 0: return
        if blocked:
            edges[a] &= np.uint8(255 ^ out_bit)
            edges[b] &= np.uint8(255 ^ in_bit)
        else:
            edges[a] |= np.uint8(out_bit)
            edges[b] |= np.uint8(in_bit)
    def obstacle(i):
        return i < 0 or (bool(logic[i] & 0x4a5014b1) and
                         not (bool(logic[i] & 0x1000) and tree_pass[i]))
    for row in gates:
        raw = row.tobytes()
        x, y = struct.unpack_from('<hh', raw, 0xee)
        size = struct.unpack_from('<i', raw, 0xf8)[0]
        if not 1 <= size <= 32: continue
        shut = closed or raw[0x2a2] == 2
        orientation = struct.unpack_from('<h', raw, 0x102)[0]
        if orientation != 80:
            xx = x + size // 2
            a, b = index(xx, y-1), index(xx, y)
            blocked = shut or obstacle(a) or (a >= 0 and b >= 0 and abs(int(base[a])-int(base[b])) > 16)
            link(a, b, 16, 1, blocked)
            a, b = index(xx, y+size), index(xx, y+size-1)
            blocked = shut or obstacle(a) or (a >= 0 and b >= 0 and abs(int(base[a])-int(base[b])) > 16)
            link(a, b, 1, 16, blocked)
        else:
            yy = y + size // 2
            a, b = index(x-1, yy), index(x, yy)
            # Native left-side tree branch bypasses the height comparison.
            tree_branch = a >= 0 and bool(logic[a] & 0x1000) and bool(tree_pass[a])
            blocked = shut or obstacle(a) or (a >= 0 and b >= 0 and not tree_branch
                         and abs(int(current[a])-int(base[b])) > 16)
            link(a, b, 4, 64, blocked)
            a, b = index(x+size, yy), index(x+size-1, yy)
            blocked = shut or obstacle(a) or (a >= 0 and b >= 0 and abs(int(current[a])-int(base[b])) > 16)
            link(a, b, 64, 4, blocked)


def rebuild(document):
    edges, components, count = calculate(document)
    changed = 0
    # Border edges are guarded by the storage diamond and are rebuilt too.
    for sid, values in ((3030, edges), (3021, components)):
        ids = np.flatnonzero(document.grid(sid) != values)
        changed += document.change(sid, ids, values[ids], 'Rebuild navigation')
    return dict(changed_field_values=changed, components=count)
