# Handoff for the next agent

Repository layout: `app.py`, `maptool.py`, and `semantics.py` remain at the root
because the GUI/CLI and packaged build import them. App code is under `editor/`,
unit tests under `tests/`, and reproducible reference analysis and experiment
scripts under `research/`. Run those scripts from the repository root with
`python -m research.<script_name>` so imports and project-relative paths work.
The release README is for app users; keep research tooling out of it.

Release README is now the current user guide (English): quick single-EXE start,
recommended native Map Editor resave, full tool/layer/building/mask/symmetry/
clipboard/hotkey reference. Three screenshot assets under docs/images were
captured from isolated temporary settings and in-memory sample maps. Help >
Hotkeys dynamically lists QAction shortcuts; its mouse section now includes
selection and paste placement. Settings > Reset no longer references removed
view-layer buttons. Rebuilt usual dist EXE and SHA256SUMS after the GUI fixes.

Bundled defaults: editor/assets/patterns has 186 JSON glyph masks from the earlier
Pixel Operator Mono/Mono Bold (124) and Perfect DOS VGA 437 (62) imports, plus
their source license notices. PyInstaller spec includes the directory. On every
GUI startup, PatternLibrary.install_defaults copies only missing JSON names to
the per-user Roaming Patterns folder using exclusive create; existing files stay
byte-identical and custom masks stay untouched. This also restores a deleted
default on a later start. Tests use temporary settings/Patterns, never real
Roaming. .gitignore excludes builds, caches, vendored code and output, while
keeping editor/assets/patterns tracked as release inputs.

MapClipboard in editor/clipboard.py supports rectangular layer-data copy/paste.
Ctrl+C copies current selected canvas layer (Select retains layer); Ctrl+V arms
original-size rectangle, next left click anchors top-left, Esc/right-click cancels.
Surface copies3037+3008+known terrain3003/3007; height3005+3045; noise3008 only.
Shared backend snapshot remains across documents in same window; no disk/OS
clipboard writes. Paste ignores brush/mask/symmetry/selection clip, single undo.
Source/destination use terrain/height protections; unsupported/occupied/border
cells skipped. Does not copy entities or regenerate unknown navigation data.


Castle placement hover previews wall area when Castle areas enabled, surface
view: owner color/current opacity, entrance anchor+(3,7),radius70/80 for400/500,
clipped to playable cells. Existing red/green footprint remains above it. Owner
and view-setting changes invalidate preview. No document mutation on hover.


Quick controls are QGraphicsView-child overlays (NOT viewport children: Qt
scrolls viewport children when panning). Regression verifies pan/zoom positions.
Controls are inset14px: brush shape/size at
top-left for Paint/Height/Variation/Vegetation, active height/noise control at
top-right. Existing widgets/signals reparented, not duplicated. Resize filter
keeps corners anchored; narrow canvas stacks right control beneath brush.
Mask library remains at top of left dock, titled Masks.


Close warnings: main can_discard includes pending brush cells as well as dirty
document. MaskEditor.reject (Cancel/Escape/window X) compares editable pixels,
dimensions,name,tags against initial state and asks Discard/Cancel, defaultCancel.
Zoom alone is not an edit. Discard never writes masks/maps or recent history.


Tool buttons occupy the top of the CENTER map column, between the side docks.
Document toolbar remains full width. Tools row scrolls horizontally on narrow
windows; it must not be added as a full-width QMainWindow toolbar.
Right View & symmetry group precedes terrain/buildings, combining grid/objects/
castle visibility + opacity with symmetry toggles (disabled for nonbrush tools).
Duplicate Surface/Height/Variation buttons removed; tool selection controls view.
Mask editor has percentage/slider/+/- zoom and Fit mask,1..64 display pixels
per mask cell; low zoom hides grid for readability. Dimensions/data unchanged.


Mask gallery height is now200px (previously100). TreeService.anchors spaces
actual stroke cells with four-cell Chebyshev spacing instead of requiring both
world coordinates divisible by4; thin off-grid lines previously yielded no trees
before symmetry. Mirrors still applied after spacing; center overlap protection
retained. GUI regression covers horizontal/vertical/diagonal 1-cell lines, all
mod4 offsets, each symmetry mode,400/500, and undo.


Mask pixel editor: editor/mask_editor.py, max120x120 across Pattern/PNG/capture.
Gallery right-click Edit tags/Edit mask, plus Edit button. Create and imports open
editor before saving. Save atomically replaces selected library JSON; Save As
creates exclusive named/tagged copy, retaining original. All writes in Patterns.
Canvas click toggles, drag paints, dimension spins/+Row/+Column expand; Invert
changes working pixels. Cancel leaves files untouched. Tests use isolated paths.

Mask library UX: Invert mask checkbox swaps bits within mask rectangle (supports
empty result from solid mask), with saved source unchanged. EditorState persists
mask_invert/mask_tag; CLI stamp accepts invert. Optional JSON tags array remains
version1 compatible; old masks untagged. Case-normalized tags filter gallery via
All/Untagged/custom combo. Edit tags atomically updates selected library JSON
preserving other keys; Masks folder opens Roaming Patterns via QDesktopServices.
Import/create/capture reset filter to All and select new mask. Active mask name
stays visible when browsing another tag. No changes to real masks during tests.

Marsh added to terrain palette/shared TerrainService (material='marsh'): reference
logic0x20008000, surface0, display3007=16 on flat unoccupied land. Repainting
marsh with ordinary terrain clears its flag; resource conversion works both ways.
Masks/symmetry/fixed variation/CLI reuse terrain tools. Renderer distinguishes
marsh by logic, never by surface0 alone; captured masks include marsh cells.
Native edge graphics remain outside schematic GUI rendering.
User canceled castle-orientation feature after testing; retain evidence only.

New orientation evidence: docs/CASTLE_ORIENTATION_2026-09-21.md. Renamed save
ref_from_save_castle_orientation contains three keeps ALL type41: door/camp below
(P1), above(P2), left(P3). IDs71/73/72 reused with different relative coordinates;
stockpiles also repositioned. No verified standalone rotation flag. Generic keep
access+0xfe stays(+3,+7) regardless, so do not equate it with the group's passage.
Current overlay/removal assume downward layout and need adaptation for future
orientation support. Populated-save state must not become a prefab wholesale.
Parser source accepts observed591-byte save extension as well as97; exact
roundtrip confirmed. Audit/snapshot under output/castle-orientation-2026-09-21.
No orientation GUI implementation or EXE rebuild in this research task.

Ada menu/preview repair implemented: editor/menu.py shares castle_markers between
header and preview. Explicit saves refresh counts/markers even if no keep changed;
500 new/missing markers use((x-y+301)//3,(x+y-495)//3), exact for Ada and within
one horizontal pixel on independent controls. Valid unchanged native positions
are preserved. Preview500 now uses3cells/pixel with black margins, not2.5.
Low-level no-op serialize remains lossless. Seven menu/preview/overwrite tests
passed; preserved every numbered Ada section. This fixes missing lobby markers
and scale, NOT native artwork, navigation regeneration or proven lord survival.

Latest confirmed failure: read docs/ADA_RESAVE_2026-09-20.md before more export
work. User GUI2v2 Ada500 has4-player count but ALL markers absent (writer only
handles400); native resave supplies4positions. Preview geometry also wrong500:
GUI fills200square, native166square with black margins. Same36 buildings/4lords,
HP150000 and1190/1191 unchanged; stale group IDs are NOT this discrepancy.
123410 region3021 cells rebuilt,17782logic cells plus edge/mask data; heights,
surface and variation unchanged. Startup death cause not isolated. Comparison
script research/analyze_ada_resave.py and immutable snapshots/fullreport under output/ada-
resave-2026-09-20. Subsequent menu/preview repair is described above.

Contextual panels: Trees tool renamed Vegetation (T), species moved to left.
Left groups follow active tool: height only Height, variation only Variation,
species only Vegetation, owner only Build. Terrain painting retains fixed-variation
checkbox plus remembered value hint, not the variation slider. Shared brush/mask
and symmetry shown for Paint/Height/Variation/Vegetation; selection also Select.
Right palette only Paint; building catalog only Build; View remains available.
Tool switching preserves values. Internal GUI tool key is now Vegetation.

User-authorized overwrite workflow supersedes the old never-overwrite GUI rule:
Save/Ctrl+S replaces current .map only after a path-specific replacement warning;
Save As/Ctrl+Shift+S can also replace with confirmation. New maps and imported
.msv use Save As first. MapWriter.save_as defaults to no overwrite; explicit
overwrite=True validates a sibling temporary file then atomically os.replace,
cleaning the temp on failure. No backup-map clutter. Discard still never saves.
last_map_directory persists on successful Open/Save; both dialogs use it, with
recent-file folders as fallback. Tests use isolated preferences/files.

Canvas center guides: both dashed axes are always drawn for every tool and layer,
regardless of symmetrical painting toggles. Those toggles affect edits only.

Variation editing: visible Variation (N) tool and Texture variation/noise panel,
uint16 target slider/input 0..65535. Apply with terrain painting optionally writes
3008 only on eligible terrain cells in the same undo transaction. Variation-only
brush, masks, symmetry and selection fill edit playable3008, preserving other grids.
Shared VariationService and CLI set_variation; paint/stamp accept variation.
Stone/iron no longer require experimental opt-in; normal terrain also clears
resource logic/display. Legacy experimental_resources argument remains accepted
for old recipes but has no gating effect. Specific resource warning removed;
this UI policy change does not prove all derived game behavior.

PNG mask import: PatternLibrary.load accepts PNG as well as JSON. One pixel per
cell, maximum120x120; brightness>=128 and alpha>=128 paint. Imports become JSON
in isolated Patterns library and are selected automatically. Prompt and contract:
docs/IMAGE_MASK_PROMPT.md. View/Noise displays existing3008 uint16 values on fixed
0..65535 grayscale, without editing data. Inspector includes texture_noise.

App icon: user-approved map-and-pencil artwork lives in editor/assets/app-icon.png.
app-icon.ico contains Windows sizes16..256; the PyInstaller spec embeds it in
the EXE and bundles it for QApplication.setWindowIcon in editor/gui.py.
Preserve the approved artwork when rebuilding.

Recent-history contamination fixed: GUI tests used custom settings_path but real
Roaming RecentFiles. EditorWindow now roots recent-files.json and Patterns beside
its settings file, isolating test/self-test runs. Removed44 known temporary test
entries from user's history, preserved4 genuine map entries. Recent maps has
Clear list (history only; no map deletion). Discard on close only saves UI prefs;
it never exports a map or remembers a file. Regression checks guard this behavior
and compare real Roaming history bytes before/after the UI test suite.
15 checks passed; rebuilt the usual EXE and refreshed its checksum with editor
closed. Real history verified unchanged by the repaired tests.

Preview-only update: editor/preview.py generates fresh schematic200x200 indexed
RGB555 thumbnails (terrain/height shading/trees/buildings/castle icons). Save As
always refreshes, even with no new edits; low-level no-op serialize remains
byte-identical. Preview text/description/save extension/trailing data and numbered
sections preserved. See docs/PREVIEW_EXPORT_2026-09-20.md. U3 filename and height/
path regeneration deliberately unchanged. Exact native artwork not reproduced.
23 preview/editor/UI tests passed. Preview update built into the usual EXE with
editor closed and dist/SHA256SUMS.txt refreshed.

Latest native resave evidence: docs/HEIGHT_RESAVE_2026-09-20.md and reproducible
research/analyze_height_resave.py. etest_height_00 had correct4-player markers/count but
retained the empty template preview and embedded filename. Native resave rewrites
preview/U3; heights/surface/noise unchanged.3021 regenerates two5329-cell regions
plus742 blocked edge cells at height130;3030/3003/3006 also change. These are not
all cosmetic. Unknown player/1171 changes are not proven required initialization.
Low-height warning now also exists below8, with independent persistent dismissal
hide_low_height_warning and Settings toggle; red indicator outside8..130.
Low-warning EXE rebuilt in place with editor closed; SHA256SUMS refreshed.

Height safety UX: brush target starts at8 each session (previous target ignored).
Crossing from<=130 to>130 shows a warning, still permits255. Don't-show-again
persists as hide_high_height_warning in Roaming settings; Settings can re-enable.
Height numeric value and slider handle/filled track are red above130 regardless
of warning suppression. Warning is once per threshold crossing, not each step.
14 related GUI/height/display tests passed. Rebuilt the usual EXE with this
height warning/default update and refreshed SHA256SUMS.txt while editor closed.

Latest change: symmetrical painting controls in Tools. Horizontal axis mirrors
top/bottom; vertical mirrors left/right; both yield four quarters. Defaults off,
saved in Roaming settings via EditorState. Geometry reflects actual cells about
playable bounds; masks, stroke preview, height, terrain, trees and selection fills
share this mapping. Selection clip applies after reflection. Build/Remove unchanged.
Tree anchors are spaced BEFORE reflection, deduplicated, and opposite overlapping
3x3 footprints at centerlines are skipped together. One stroke/one undo command.
Source tests pass; symmetry EXE rebuilt after the user closed the editor.
Updated dist/SHCDEMapEditor.exe in place and refreshed dist/SHA256SUMS.txt.

Current user task unfinished: create etest_new_creation from an empty400 map
entirely through the GUI, resembling sword1v1 with two hill watcher castles.
INA CUP 01 1v1 SworD was the stated default reference (P1/P2 north/south,
P3/P4 side hills80). Tree tool and castle plateau changes are built into the
usual dist/SHCDEMapEditor.exe; SHA256SUMS.txt updated. Editor was closed before
replacement and the new EXE is now open on an untouched empty map.
GUI drawing blocked: @oai/sky get_window_state screenshot capture fails twice
with SetIsBorderRequired / interface unsupported0x80004002. Text-only UIA works
and confirms Trees controls; no observed canvas image/coordinates available.
Do NOT claim etest_new_creation was created; no script substitute is authorized
for this explicitly GUI-only exercise. Continue GUI creation when capture works.

Trees: see docs/TREES_2026-09-20.md. TreeService uses ref_13 isolated records and
local grids; GUI Trees(T), visible species buttons, brush spacing4, Remove(D)
on an isolated tree. CLI plant_trees/remove_tree. Castle placement now supports
flat plateaus with translated grid/entity elevations; derived hill edges remain
experimental. Original reference snapshots stay read only.

Castle placement regression: user reported lords dying even after native editor
resave. Read `docs/CASTLE_AUDIT_2026-09-20.md` before changing it.
ref_12 confirms a lord is present with150000HP, but all nine generated building
records retain stale group-root global IDs at file0x2a8. Player2022 initialization
also omits five fields present in native and previously working castle maps.
Repair now in source: castle prefab extracted from hashed isolated ref_12,
group-root IDs remapped, player civilian count/access words/0x489c initialized
and cleared on removal without resetting resources. Removal includes dead linked
lords. Validator detects stale group IDs on rewritten keeps. Regression coverage
includes add/remove/re-add, owner1/8,400/500, reopen, undo and dead-lord cleanup.
Game survival after repair remains unverified; do not claim no possible issues.
Original audit snapshots remain preserved separately from the repaired writer.

## Goal and working style

Height tool (E): target0..255 slider/input/step buttons, shared HeightService and
CLI set_height. Changes3005+3045 only; ordinary unoccupied terrain, no invented
cliff/path-cache regeneration. Treat export as experimental (prior steep-step
game glitches). Height view has a fixed jet LUT/colorbar0..255, with object and
castle overlays suppressed to retain data colors. Castle opacity has a synced
slider/input/step buttons. Ctrl during regular terrain/height strokes locks to
the dominant horizontal/vertical axis until released; anchors at stroke start
or last painted point if pressed mid-stroke. See tests/test_height_editor.py and UI tests.

Opening `3v3 Einstein v1.1.map` revealed opaque1190 (blast error), not a filename
problem. Optional entity/player metadata stays opaque and byte-preserved; do not
pass None to numpy. Castle edits can reconstruct1190 from2022 lord slots,1191
global IDs and matching live lord records (owner/type/gid), only when consistent.
Recovery is undoable; undo restores the original opaque bytes. Castle removal
preserves base terrain heights. Height view/target changes activate Height tool;
Paint returns to Surface. Height painting also accepts unoccupied cliff/elevated
terrain flags; walls/buildings/water/units remain protected. Failed edits report
visible errors instead of fleeting status messages.
Save As appends .map if absent, preserving version dots (v1.1 → v1.1.map).

Building owner uses OwnerPanel: eight exclusive colored P1–P8 buttons in two
rows, sourced from PLAYER_COLORS; white border marks selection. No numeric
owner field. This chooses the owner of newly placed buildings/walls.

Navigation update: right-click cancels the active tool/placement and pending
stroke, clears selection and returns to Inspect. It does not pan or delete.
Middle-button drag (or Pan tool + left drag) pans. Wheel zoom explicitly anchors
to the wheel event position with NoAnchor and scene correction; do not restore
implicit AnchorUnderMouse. Keep mouse help/tooltips consistent.

Building tools implemented experimentally (2026-09-20): read
`docs/BUILDING_TOOLS_2026-09-20.md`. `editor/buildings.py` supplies shared placement,
group removal and prefabs extracted by `research/build_building_catalog.py` from the hashed
snapshot `output/buildings-2026-09-20/ref_11_buidlings_400.map`. GUI Build/Remove
and JSON recipes use the same transactional backend. 34 palette choices include
nine-record castles plus lord, quarry plus pile, farm fields/orchard trees,
gate-management records, workshops, named towers and flat walls/stairs.
Only reference orientations are implemented; missing gate/bridge orientations
were requested. Do not infer rotation by changing one sprite field.
Imported populated buildings with workers/goods cannot be removed yet. Derived
pathfinding needs game testing. Building operations are NOT generally validated
live-save mutations. Source reference originals remain untouched.
Correction: 1047 is NOT established as a building allocation high-water mark;
the new sample has value26 with112 active buildings. Never use that old assumption.

Executable updates: always replace `dist/SHCDEMapEditor.exe`. If the editor is
open or Windows locks that file, tell the user to close it and wait before
replacing it. Do not terminate their editor, create alternate release folders,
or leave additional executable copies as a workaround. This is an explicit
user preference (2026-09-20).

UI refactor implemented: `editor/panels.py` contains reusable visible tool,
brush, terrain, view and inspector panels plus HotkeysWindow. `editor/state.py`
holds shared UI choices. GUI actions register shortcuts/help together; canvas
shortcuts must not fire inside text/numeric inputs. Regular brushes support
1..map-size (400/500), batched strokes and raster previews; masks retain their
intrinsic dimensions. Keep JSON CLI geometry consistent. `tests/test_ui_refactor.py`
checks controls, preference persistence, selection clipping and sweep parity.
Castle area overlay: 400 maps use radius 70 (141x141); 500 maps use radius 80
(161x161), based on the user's follow-up observation. Both center on the middle
doorway. This supersedes the earlier provisional 141x141 overlay on 500 maps.

Implementation authorized and first application built (2026-09-20). Read
`docs/APP.md` for GUI, agent CLI, architecture, packaging and remaining limits.
`editor/` is the shared backend + GUI; `app.py` is the entry point. Keep backend
imports independent of Qt and expose editing services through GUI and CLI.
`tests/test_editor.py` adds preservation/transaction/geometry/CLI tests. Do not treat
structural tests as proof that new resource edits work correctly in game.

GUI requirements (2026-09-20): approved layout implemented. Initial
new-map presets are 400 and 500, derived from existing empty reference-map bytes.
Keep source/template bytes immutable; edit an in-memory document and write only on
explicit Save/Export. Final Windows distribution must be a single portable .exe
with no user-installed Python/packages or installer. See APP.md for implemented
features; concept images are not evidence of editing support.

Build an autonomous external map editor for Stronghold Crusader Definitive Edition.
Current stage: reverse engineer the binary format using reference maps, implement
lossless parsing and controlled generators, validate experiments in the actual game
with the user. The format is NOT fully understood. A first GUI and headless
editing API now exist; the complete map editor is still under development.

The user wants an alternative to the built-in map editor and will continue
reverse engineering the map format. See `docs/PROJECT_CONTEXT.md` for the durable
project brief and workspace-source policy. When the user adds repositories or
map-folder paths to the SHCDE workspace, inspect their instructions and relevant
docs, then record verified paths and their research role here and in that brief.
Do not assume an added workspace folder is a dependency or permission to modify it.

The user is a programmer. Explain concrete section IDs, offsets, types, coordinates,
byte differences and evidence. Separate confirmed facts, observations and hypotheses.
Russian is suitable for explanations. Do not restart the research or ask the user to
recreate references before reading the existing work. Use existing castle templates:
a starting complex includes multiple records, including the stockpile.

## Read first, in this order

0. `docs/EDITOR_READINESS.md` — consolidated known facts, remaining questions,
   template/default policy and staged application plan. Start the viewer/document
   foundation without waiting for complete format decoding. Preserve unknown
   template data; validate dependencies before promoting an edit to supported.
   Latest additional evidence: `docs/SAVEGAME_LETO_2026-09-19.md` — renamed .msv,
   save-prefix support, persistent resources, reciprocal worker links and movement
   candidates. Read this before investigating saved simulation state.
   Then `docs/LETO_EDITOR_RESAVE_2026-09-19.md`: editor resave retained resources
   and workers while state evolved; 220 zero-HP records cleared. `active_count`
   is not a living-unit count. The 97-byte prefix extension survived resaving.
1. `RESEARCH_MEMORY.md` — accumulated experiments, findings and important caveats.
   Some historical entries say pending; later results supersede those entries.
2. `docs/SECTION_STATUS_2026-09-19.md` — section inventory and known/unknown meanings.
3. `docs/REFERENCE_ANALYSIS_2026-09-19.md` — systematic reference-map analysis,
   file entity layouts and cross-checks against other projects.
4. `docs/THREE_CASTLE_GRID_2026-09-19.md` and
   `docs/MENU_METADATA_2026-09-19.md` — latest generated map and its editor resave.
5. `maptool.py` and `semantics.py` — implemented container and semantic model.

Read topic-specific reports as needed: `TEXTURE_ANALYSIS`, `MARSH_SHADOWS`,
`WALLS`, `HILLS_STAIRS`, `HEIGHT_TESTS`, `HEIGHT_STEPS_GAME_RESULTS`,
`SMOOTH_EARTH_COMPARISON`, `DISC_RESAVE` (all in `docs/`, dated 2026-09-19).
`README.md`, `RESEARCH_PLAN.md` and `docs/SCRIPT_EXTENDER_FINDINGS.md` contain
historical material. In particular, early tree/unit runtime-to-file offsets in the
Script Extender report were superseded. Prefer later evidence and current code.

## Local paths and sources

- Project: `C:\repositories\shcde-map-editor`
- Live game maps:
  `C:\Users\rustam\AppData\LocalLow\Firefly Studios\Stronghold Crusader Definitive Edition\Maps`
- Live game saves (read-only research source):
  `C:\Users\rustam\AppData\LocalLow\Firefly Studios\Stronghold Crusader Definitive Edition\Saves`
- Script Extender: `C:\repositories\shcde-script-extender`
  - Upstream: https://gitlab.com/rawra-stronghold-crusader/shcde-script-extender
  - Investigated revision: `78a7595067fa297798720b56664d7df955aa7150`.
    Check the actual checkout if using newer evidence.
  - Useful sources: `src/SHCDESE.BepInEx/Interop/GameTileManagerView.cs`,
    `src/SHCDESE.BepInEx/API/GameTileManagerAPI.cs`, entity/player structs and enums.
  - This is a runtime SDK, NOT a file-format specification. Use it as a read-only
    research source; the user did not request injection/hooks or modifications to it.
- Rust statistics app: `C:\repositories\shcde-stats-rust`
  - Read its `AGENTS.md`, `ALL_INFO.md`, `.memory`, and relevant `instructions/`
    and `src/` material when investigating entity/player structures.
- Economy simulator: `C:\repositories\shc-eco-simulator`
  - Read its `AGENTS.md`, `README.md`, relevant `doc/` and `simulator/` material.
    Used for independent evidence about stockpile/start-complex arrangement.
- Vendored Sourcehold research: `C:\repositories\shcde-map-editor\vendor\sourcehold-maps`
  - Legacy-format knowledge is useful but must be verified for DE.
- `examples/`: copied user maps. `output/`: archived experiments, reference
  snapshots, SHA-256 provenance, section diffs, reports and diagnostic images.
  The main reference batch is `output/references-2026-09-19/` (29 original refs).
  Later references and resaves also exist in live Maps and their experiment archives.

## Latest completed result (2026-09-19)

Latest follow-up: `leto vs fbi 10.map` is byte-identical to `leto vs fbi 10 .msv`.
Reader now preserves an observed 97-byte length-prefixed extension before ud and
the directory. Seven related saves roundtrip. Evidence: `output/leto-save-2026-09-19/`.
638 buildings and 1460 units decode in the target; 3010 references only 502 distinct
unit slots, so do not use it as a complete unit list. Across seven saves, 1443
building-worker links reciprocate; 23 non-null/non-gold stored-goods totals match
storage buildings. Player 2022+0x50C gold candidate: P2=5997/P3=1784, awaiting
in-game corroboration. Worker and movement file offsets/limits are in the new
report. All 18 tests pass. Do not treat active saves as clean new-map templates.

Earlier result:
Generated `etest_oasis_grid_3_castles_400.map`: P1 keep at (397,397),
P2 at (375,260), P3 at (415,260); one-cell oasis grid with pitch 5 leaves
4x4 earth interiors. Complete complexes: 27 building records and three lords.
The user confirmed it works in game. Original generator retained stale menu
metadata and preview from a two-player source; user fixed these by editor resave
to `etest_oasis_grid_3_castles_400_r.map`. The comparison is complete.

- U2 payload +0x18 uint32: menu player count, 2→3.
- U4 payload +0x10: eight pairs of uint32 x/y, stride 8; absent = both 0xFFFFFFFF.
  New P1/P2/P3 markers: (98,98), (156,18), (176,38).
- U4 payload +0x50: map size 400. These offsets exclude each block's length prefix.
- Preview: 512-byte RGB555 palette plus 200x200 uint8 indices, independent of markers.
- Terrain sections 3037/3008/3005/3045 and ID sections 1035/1190/1191 were unchanged.
- `MapFile.menu_metadata()` now reads these header fields. `research/check_menu_resave.py`
  verifies evidence including 23 keep-marker projection checks. All 14 unit tests passed.
- Evidence: `output/three-castle-resave/`; original generated map:
  `output/three-castle-oasis-grid/`.

The generator still needs proper menu count/markers/filename/preview updates before
it is a complete writer. The exact native preview renderer and complete lobby
AI/team assignment logic are not established. No map was edited during comparison.
No new map experiment is pending from this handoff. Follow the current user request
for the next task; this historical status does not limit future authorized work.

## Guardrails and research gaps

- Preserve original user maps. Create separately named outputs for authorized
  experiments; do not overwrite existing maps. Keep archived copies and hashes.
- Preserve unknown sections/bytes; verify changed-section scope and readback.
- Runtime offsets are not automatically file offsets. Global IDs are not slot IDs.
- A castle is a group: the known template has five castle-related parts plus four
  stockpile parts. Moving only primary x/y leaves embedded references inconsistent.
- Surface 3037 alone does not determine appearance. Noise 3008 varies per cell;
  its exact mapping to graphics is unknown. Do not claim 3036 is a proven graphics cache.
- Editor opening/resaving can rebuild terrain boundaries and derived layers.
  Direct game loading is a separate experiment; user confirmed different behavior.
- Climb delta 16 was observed in the tested strips. Height fields are uint8, but
  255 is a storage limit, not a proven universally safe terrain+wall height.
  Suspected wall-height wraparound is not numerically proven from the screenshot.
- Shadow runtime data exists; the complete on-disk shadow mapping is not known.
- General allocation/deletion, all entity fields, derived grids and arbitrary map
  generation remain incomplete. Experimental prefab tools use clean zero slots;
  do not promote structural checks to proof of in-game behavior.

## Running and extending the tools

Use PowerShell in the project root and the existing `.venv`:

```powershell
.\.venv\Scripts\python.exe -m unittest -q
.\.venv\Scripts\python.exe -m research.check_menu_resave
```

Dependencies are in `requirements.txt`. `research/analyze_references.py` and `research/check_*.py`
produce research evidence. Inspect paths/arguments before running scripts;
`research/make_*.py` scripts write maps and may contain experiment-specific assumptions.
Consult CLI help/source instead of guessing interfaces. Do not regenerate every
experiment merely to recover context. Update focused docs and `RESEARCH_MEMORY.md`
after new findings, recording what was verified and what remains unknown.
