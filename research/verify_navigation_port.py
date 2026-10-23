"""Compare the editor port to original D86F0 instructions in offline Unicorn.

Uses existing local Dashboard research tooling; never loads the game DLL natively.
Output is reproducible synthetic evidence, not a live game test.
"""
from pathlib import Path
import sys
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT.parent / 'shc-dashboard/artifacts/production-static'
sys.path.append('C:/Program Files/Python39/Lib/site-packages')
sys.path.append(str(Path.home()/'AppData/Roaming/Python/Python39/site-packages'))
sys.path.insert(0, str(DASHBOARD))
from verify_tile_height import HeightReplay, BASE, TM, FLAGS, HEIGHT, EDGES, CONTEXT
from editor.navigation import _native, neighbors
from editor.geometry import MapGeometry


def main():
    rng = np.random.default_rng(20261023)
    g = MapGeometry
    n = g.count
    logic = np.full(n, 0x8000, dtype=np.uint32)
    height = np.full(n, 80, dtype=np.uint8)
    damage = np.zeros(n, dtype=np.int8)
    slots = np.zeros(n, dtype=np.uint16)
    tree_slots = np.zeros(n, dtype=np.uint16)
    centers = g.index_grid[240:560:8, 240:560:8].ravel()
    centers = centers[centers >= 0]
    touched = np.unique(np.concatenate((centers, neighbors()[centers].ravel())))
    touched = touched[touched >= 0]
    flags = [0, 0x8000, 0x100, 0x800, 0x1000, 0x400, 0x2, 0x402,
             0x200000, 0x10000000, 0x400000, 0x800000, 0x100000, 0x80,
             0x10, 0x20, 0x20008000, 0x28000, 0x88000]
    logic[touched] = rng.choice(flags, len(touched)).astype(np.uint32)
    height[touched] = rng.integers(0, 256, len(touched), dtype=np.uint8)
    damage[touched] = rng.integers(-128, 128, len(touched), dtype=np.int8)
    btypes = np.array([0, 11, 40, 41, 42, 45, 46, 47, 69, 73, 74, 75, 76, 77,
                       78, 153, 157, 190, 239], dtype=np.int16)
    slots[touched] = rng.integers(0, len(btypes), len(touched), dtype=np.uint16)
    types = np.ascontiguousarray(btypes[slots])
    tree_slots[touched] = rng.integers(0, 20, len(touched), dtype=np.uint16)
    tree_pass = np.asarray((tree_slots >= 5) & (tree_slots != 15), dtype=np.uint8)
    edges = np.zeros(n, dtype=np.uint8)
    components = np.zeros(n, dtype=np.uint16)
    _native()(n, *(a.ctypes.data for a in (logic, height, damage, slots, types,
               tree_pass, neighbors(), edges, components)), 0)
    r = HeightReplay()
    for offset, data in ((0x48f71b0,logic), (0x4ddd350,height), (0x5001730,damage),
                         (0x4b6aa50,slots), (0x4ace010,tree_slots)):
        r.uc.mem_write(BASE+offset, data.tobytes())
    # Row deltas are the native packed-diamond directions, not an 800-wide square.
    for y in range(1,799):
        i = int(g.index_grid[y,400])
        delta = (neighbors()[i]-i).astype('<i4')
        r.uc.mem_write(TM+y*32, delta.tobytes())
    for slot, typ in enumerate(btypes):
        r.write(BASE+0x64ccbb0+0x5c+slot*812+0xd2,int(typ),2)
    for slot in range(20):
        r.write(BASE+0x32de440+0x18+slot*156+0x52,slot,2)
    mismatches = []
    for i in centers:
        r.function(0xd86f0,CONTEXT,int(g.y[i]),int(i))
        actual = r.read(EDGES+int(i),1)
        if actual != int(edges[i]):
            mismatches.append(dict(tile=int(i),native=actual,port=int(edges[i]),
                                   source_flags=hex(int(logic[i]))))
    result = dict(cases=len(centers),mismatches=mismatches,
                  dll_sha256='fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2',
                  scope='D86F0 before deferred reciprocal-edge cleanup; synthetic mixed flags/heights/signed damage/buildings/vegetation')
    out=ROOT/'output/navigation-update-2026-10-23/port-comparison.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(cases=len(centers),mismatches=len(mismatches))))
    if mismatches:
        print(json.dumps(mismatches[:8],indent=2))
        raise SystemExit(1)


if __name__=='__main__':main()
