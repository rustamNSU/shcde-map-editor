# Map editor 0.3.0 implementation

The update is confined to this repository. Installed game files and original
map/save inputs were read only. The portable release remains
`dist/SHCDEMapEditor.exe`.

## Height and navigation

`editor/native/navigation.cpp` is an offline C++ port of the pinned DLL's
edge builder and connected-region algorithms. `editor/navigation.py` supplies
the document's arrays and ports the gate entrance overrides. The application
loads its own bundled `navigation.dll`, not the game DLL, and never accesses
a running game.

| Native RVA | Implemented behavior |
|---|---|
|`0xD86F0`|Per-cell eight-direction movement edges: height, terrain, stairs, walls, elevated structures, building classification, signed damage bytes, vegetation|
|`0xDAA50`|Full edge rebuild and deferred corner queue|
|`0xDE6A0`|Reciprocal edge cleanup around queued cells|
|`0xC07C0`|Additional walk-surface height by building type|
|`0x107160`|Vegetation exception: nonzero slot, type >=5, type !=15|
|`0xD8CE0`/`0xC4BF0`|Gate entrance links and temporarily closed gates for component labeling|
|`0xE49D0`|Ascending seed scan, directed-edge flood fill, native direction order, maximum999 regions|

Ordinary neighbor height differences up to16 pass. Ordinary diagonals do not
use a blanket “both adjacent cardinal edges must pass” rule. Building and wall
branches have their own conditions. Connected-region traversal follows outgoing
edges in order W,E,N,NW,NE,S,SW,SE.

At the outer document transaction commit, changes to terrain logic, current
height, building/vegetation grids and records, or structural damage trigger
recalculation of sections3030 and3021. Recalculation patches join the original
command. Undo/redo restores all of them; a failed rebuild rolls back the entire
edit. A completed brush stroke causes one rebuild. Edit → Rebuild navigation
also repairs imported navigation without another terrain edit.

The numerical height tool remains an absolute0–255 tool, including valued
masks. It writes current/base height and applies the native explicit old-cliff
flag clearing step. This is distinct from copying the native gradual brush's
raise/even behavior and8–156 clamp. The existing warnings for extreme heights
remain.

**Limit:** full cliff/shoreline artwork, graphics-cache and every engine startup
pass are not ported. Navigation correctness is not proof of identical visual
rendering or complete simulation-state regeneration. See
[terrain details](TERRAIN_UPDATE_2026-10-23.md).

## Map sizes and castle rules

New supports160,200,300,400,500,600,700,800. Additional sizes derive from the
hash-verified empty500 template, retain opaque sections/noise/entity tables,
and update only known map-size, boundary, ground-display and navigation data.
The full boundary arrays match native160/200/400/500 reference files byte for
byte. Fresh schematic thumbnails and matching menu size accompany new presets.
Additional-size preview projections are schematic; native400/500 calibration
and valid existing markers remain preserved.

Castle placement now reserves117 actual occupied/support cells, rather than
all180 cells in its12×15 bounding rectangle. A building placed in an empty
corner survives removing the castle. Campfire, keep and stockpile cells remain
occupied.

Construction radius around the native access tile is45,50,60,70,80,90,100,100
for the eight presets. Same-team keeps contribute integer half radius in the
game. The editor shows each keep's own full area. The restriction is gated by a
native mode field whose exact menu label remains unverified; it is not proven
exclusive to multiplayer. Range is only one of the placement checks.

The optional amber overlay marks potential startup terrain repainting around
both keep and campfire, including during placement. Native surface selection
chooses either85 brush points (Manhattan radius6) or13 (radius2). Known cell
blockers filter the footprint; cached beach checks and recreation order can
further reduce it. Placement preview samples the prefab's serialized keep-origin
surface, so placing over oasis does not misleadingly show a smaller footprint
than the resulting saved castle. Displaying it changes no map bytes. Exact evidence and all
predicates are in [castle research](castle_bounds_2026-10-23.md).

## Terrain, buildings and masks

Ordinary painting works at non8 heights without flattening hills. Added sea,
river, ford, beach, pitch, rocks and80/130 plateau presets. Water preserves the
native distinction between current surface height and default height.

The building catalog contains69 verified reference presets, including military
compounds, religion, market, fear buildings and garden variants. Compound
children and group IDs are remapped; flat plateau placement translates verified
prefab elevations. Search and category controls filter the Build list. Tree
brushes now work at every native map size, retaining their verified height8
planting condition. See [catalog details](BUILDING_CATALOG_2026-10-23.md).

Images in Pillow-supported formats, including JPEG/PNG, accept arbitrary input
dimensions. The import dialog chooses output dimensions1–800, contain/cover/
stretch fitting, luminance/alpha thresholds, optional normalization, inversion
and a height range. Preview is shown before saving and settings persist.

Binary JSON remains version1 compatible. Height JSON version2 stores separate
coverage and elevations: transparent holes and painted height0 are distinct.
Transforms preserve cell/value correspondence; height inversion uses
`minimum + maximum - value`. Gallery and brush previews show height colors.
Selecting a height mask activates Height and disables the scalar target because
the mask supplies its own values. Symmetry reflects both positions and values;
the original stamp wins where reflected stamps overlap. Height-view selection
capture retains per-cell elevations. See [mask format and conversion](IMAGE_MASK_PROMPT.md).

## Reproduction and evidence

Pinned game DLL SHA256:
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.

- `research/verify_navigation_port.py`:1600 mixed syntheticD86F0 cases,
  zero differences against original instructions in Unicorn.
- `research/castle_bounds_verify_components.py`: full320800-cellE49D0 scan,
  400 randomDE6A0 cases and80D8CE0 gate cases, zero differences. The memory
  fill helper is replaced by an equivalent byte write; this is not a live game test.
- `tests/test_navigation.py`: exact edge arrays from nine archived native maps,
  available stable component references, height islands, diagonals, rollback,
  serialization and undo.
- `tests/test_map_sizes.py`: native boundary comparisons, all eight sizes,
  unknown-section retention, clean serialization and brush placement.
- `tests/test_new_gui_tools.py`: valued-mask stamping, zero/holes, mirrored
  values, one-command undo, size controls, filtering and read-only overlays.

Native construction requires MSVC x64 only when rebuilding the application:
`research/build_navigation.ps1`, then
`.venv/Scripts/python.exe -m PyInstaller --noconfirm SHCDEMapEditor.spec`.
The released single EXE bundles that compiled port and its runtime; users do
not need a compiler, Python, BepInEx or a changed game DLL.

Final test/build results are recorded in `output/release-0.3.0/`.
133 source tests passed:108 backend/integration,24 UI regressions and one added
oasis-overlay regression (six focused overlay/GUI tests passed after that fix).
The portable GUI self-test and actual-EXE CLI exports/reopens at all eight map
sizes passed. PyInstaller's user-only extraction-directory ACL blocks startup
inside the restricted execution sandbox; running the isolated packaged tests
with normal user permissions succeeds. This does not require changing game files.
