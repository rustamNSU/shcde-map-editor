# Native castle terrain clearing and construction bounds

Static research, 2026-10-23. Installed `CrusaderDE.dll` SHA256 is
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.
All locations below are RVAs from image base `0x180000000`. The DLL was only
read. Ghidra ran against the existing snapshot with `-readOnly -noanalysis`;
no game process or native game DLL was launched, and no installed game file or
original map changed. The later verification section describes isolated
original-instruction execution in the Unicorn emulator.

## Map size presets

The extracted stock GUI `FRONT_EditorSetup.xaml`, lines113–224, has exactly
these eight map-size buttons: **160, 200, 300, 400, 500, 600, 700, 800**.
Native region-size helper `0xCF4A0` also explicitly branches on those sizes.
This establishes the supported GUI presets. It does not prove that the native
binary rejects every other positive size: editor setup `0x85E90` stores its
size argument, and the radius switch below has a default branch.

## Wall, gate and tower range

Native helper **`0x6AF00`** reads TileManager+`0x204E7E4`, the map size at
DLL+`0x60AD594`. Its exact switch is:

| Map size | Own keep radius R | Own square side 2R+1 | Same-team keep radius floor(R/2) |
|---:|---:|---:|---:|
|160|45|91|22|
|200|50|101|25|
|300|60|121|30|
|400|70|141|35|
|500|80|161|40|
|600|90|181|45|
|700|100|201|50|
|800|100|201|50|
|Any other value|70|141|35|

This is a switch, not an unrestricted `size/10+30` formula. The160 and800
entries are significant exceptions to that extrapolation.

**`0xEEF90`** is the range rejection helper. For a valid tile `(x,y)` it accepts
if an existing own keep satisfies

```cpp
max(abs(x - ownKeepX), abs(y - ownKeepY)) <= R;
```

Otherwise it scans players1–8 and accepts a keep with the same team value at
DLL+`0x37EDF3C + player*4` if the same distance is at most integer `R/2`.
Keep existence is its nonzero keep ID. If no keep qualifies it returns1 and
writes placement error18 (`0x12`) at DLL+`0x60AD4B4`.
Distance helper **`0x79C0`** stores absolute dx, dy, min and max; this caller
reads its **max** result, so the area is an axis-aligned square in tile space.

The center comes from player resource record+`0x98/+0x9C` (stride`0x583C`),
already expressed in tiles. It is not the keep footprint origin or a world
coordinate requiring division by8. Setter **`0xD0630`**, kind0, computes this
access tile from the keep origin and native orientation: default/15 adds(3,7),
orientation2 adds(-1,3),4 adds(3,-1),6 adds(7,3). The actual saved player fields
are preferable when available; a rendered doorway is not a reliable replacement
for the native access point on every orientation.

Wall validator **`0x7A3B0`** calls the radius helper and `0xEEF90` for successive
wall path tiles. Generic building validator **`0x77E60`** uses the same check for
gate and tower footprint tiles: call sites`0x783C0` and`0x783EA`. Each footprint
tile must pass, so a large tower cannot extend its far edge outside the square
merely because its origin is inside. Request IDs100–104,110–114,140–147 useR;
98(killing pit),99(pitch ditch),105(drawbridge),312(dog cage) useR+5.

Both callers gate this range branch on nonzero native DWORD at **`0x8574B90`**.
Its exact named menu setting remains unverified in the existing research. The
restriction therefore must not be described as exclusive to multiplayer on
the basis of this branch alone. Other terrain, enemy proximity and building
eligibility checks also apply; the colored square is a range guide, not a
promise that every included tile is buildable.

## Why loading a map changes terrain around a castle

Custom-map setup **`0x94350`** deletes old starting keep/storage groups at call
sites`0x95895/0x958AA` and recreates starting castles through building placement
`0x6D580` at`0x95B5E/0x95EDA/0x9604A`. Mapper61 maps to building41(KeepTwo).
The keep constructor is **`0x74DA0`**. It calls terrain brush **`0x6FE90`** on
every keep tile at`0x7500C` and every7×7 campground tile at`0x7566A`.

The constructor samples the original keep-origin surface byte and tests mask
`0x90` (oasis grass or thick foliage). This selects:

| Origin surface | Brush index | Point count | Manhattan radius | Requested surface |
|---|---:|---:|---:|---|
|`surface & 0x90 == 0`|6|85|6|2: dirt/stones|
|`surface & 0x90 != 0`|3|13|2|128: thick foliage|

Point counts are direct DWORDs at table **`0x2D1C38`**. Point helper`0x6A620`
delegates to **`0xE3360`**, a BFS over cardinal directions0,2,4,6. Enumerating
the first85 points includes the center and the complete Manhattan radius6
diamond (`1+2r(r+1)=85`). The first13 points similarly give radius2.

Thus the geometric warning region is the union of the keep square and camp
square, each expanded by a diamond of the selected radius. For a normal7×7
keep at `(x,y)` and7×7 camp at `(x,y+8)`, the radius6 union spans
**x-6..x+12 and y-6..y+20**, with diagonal-cut corners. It is not a rectangular
border and not a Euclidean circle. Near a map boundary the native BFS counts
discovered border cells but does not expand them; the first85/13 points may
therefore extend farther in another direction than a simply clipped diamond.
The overlay replays that queue when its interior fast path touches a border.
Camp offsets come from table`0x2D3210` and
depend on keep type and orientation. Existing records should be linked by
their parent keep slot (file building+`0x192`), rather than assuming the camp
is always below the keep.

## Which cells the brush can actually change

The geometry alone is a potential rewrite area. The branch skips cells with
logic masks`0x10000400`, `0x100`, `0x60300001`, nonzero building reference3012,
or nonzero vegetation reference3004. Ordinary dirt additionally excludes
stone/iron/impassable-edge bits(mask`0xA0080`) and surface beach bit`0x20`.
The outer loop skips the reality edge; the editor also clips its warning to
playable tiles.

The accepted branch clears display bit`0x20` in3007, applies
`logic &= 0x1FC5FF3E`, preserves pitch-trap logic for requested dirt2, and writes
surface2 or128. These surface requests preserve height in this branch.

There is one additional state-dependent check: **`0x64A50(0x20)`** tests the
eight surface neighbors around the TileManager's cached tile
(+`0x204E810/+0x204E814`) and writes +`0x204E818`. Brush`0x6FE90` does not update
those cached fields itself. Consequently a pure map-file overlay cannot
predict that condition exactly without knowing the surrounding placement
state. Building recreation order can also change which future footprint
cells were already occupied when each brush call ran.

The editor therefore displays **potential native terrain rewriting** in amber,
filters the proven per-cell blockers and changes no terrain. A marked oasis
near a ground-origin castle can become dirt when the native game recreates
that castle; this explains the reported missing oasis. No campfire exemption
from ordinary building placement was found: tile validator`0x7B060` returns2
for a nonzero3012 reference, regardless of the linked building type.

## Reproduction and limits

Run `python -m research.castle_bounds_audit` with Python containing pefile and
Capstone. It verifies the DLL hash and writes static tables plus relevant
assembly to `output/castle-bounds-2026-10-23/`. Ghidra request lists are
`research/castle_bounds_requests*.txt`; exports are under that output's
`native/` folder. Extra navigation helpers requested during this research are
under `output/navigation-update-2026-10-23/native/` with `nav_` prefixes.

The generic placement function's Ghidra decompilation hit an instruction-flow
limit because its switch targets were not all recovered in the shared DB.
The range cases were independently decoded from its literal two-stage jump
table (`0x798F4/0x79914`) and Capstone assembly. The radius helper, range
checker, keep constructor and brush have both assembly and C reconstructions.
Static evidence is strong for these formulas and potential rewrite geometry;
this pass did not execute a new in-game multiplayer or terrain-load test.

Additional offline instruction replay is in
`research/castle_bounds_verify_components.py`. Unicorn executes the pinned
DLL instructions against synthetic memory, without loading that DLL natively:

| Native routine | Comparison | Result |
|---|---|---|
|`0xE49D0`|Full320800-cell component scan; separated land/sea/river/ford/high plateau islands|0 mismatches|
|`0xDE6A0`|400 reciprocal cleanup sources; random edge bytes, mixed terrain/obstacles|0 mismatches|
|`0xD8CE0`|80 gate cases: both orientations, sizes5/7, open/closed, unequal base/current heights, obstacles|0 mismatches|

The generic byte-fill helper`0x7490` is replaced with an equivalent write into
Unicorn memory. No edge/component decision is stubbed. These tests omit the
vegetation pass-through exception and populated gate-manager bookkeeping.
Probe labels are land1, sea0, river0, ford2, high plateau3. In particular,
nonzero stored sea/river component labels can be stale file state rather
than a requirement for the rebuilt labels to match them. The replay result
is `output/navigation-update-2026-10-23/component-native-comparison.json`.
