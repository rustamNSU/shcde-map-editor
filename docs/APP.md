# Map editor 0.1

For current installation, controls, and hotkeys, use the [README guide](../README.md).
The notes below document the implementation and earlier UI iterations; some old
control locations and limits have since changed.

Recent maps > Clear list clears only the stored paths, leaving map files intact.
Discard on close does not export or autosave maps. All editor preference/history/
pattern storage follows the settings directory, so tests and packaged self-tests
using a custom settings path cannot pollute the user's Roaming recent list.

Height brush target starts at8 on every launch. Above130, the numeric value and
slider turn red and a warning explains observed game glitches. Values through255
remain available. The warning appears on crossing130; Don't show again persists
in settings.json. Settings > Warn when terrain height exceeds130 re-enables it.
Existing map heights are not changed by the startup brush default.

Heights below8 also warn and turn red. Their separate Don't show again setting
can be reset using Settings > Warn when terrain height is below8. Lower values
remain selectable; ordinary0-height terrain is not validated native behavior.

Symmetrical painting: Tools has independent horizontal-axis (top/bottom) and
vertical-axis (left/right) checkboxes. Both default off and persist in Roaming
settings.json. Both enabled mirrors a brush across all four quarters. Terrain,
height, masks, selection fills and trees use actual-cell reflections, previews,
and one undo command per stroke. Dashed centerlines show active axes. Selection
clipping and protected-cell rules still apply to mirrored sides. Buildings and
Remove are not mirrored. Opposite tree footprints too close to the centerline
are skipped together to avoid creating an asymmetric overlapping group.

The first desktop application is implemented. Run `dist/SHCDEMapEditor.exe` on
Windows x64. Python, Qt and the 400/500 templates are bundled; no installer is
needed. The one-file launcher extracts its runtime to a temporary directory.
Reusable masks live in `%APPDATA%\SHCDEMapEditor\Patterns`. The first launch
copies 186 bundled letter and digit masks (Pixel Operator Mono, Mono Bold, and
Perfect DOS VGA 437) into that folder. Later launches add any missing bundled
masks without changing existing files, including masks you edited yourself.
The bundled JSON masks and font license notices are in `editor/assets/patterns`.

The toolbar's **Recent maps** button reopens previously opened or saved maps.
`%APPDATA%\SHCDEMapEditor\recent-files.json` is created at first GUI startup
and stores up to 50 unique absolute paths, newest first. Only successful opens
and saves are recorded; new unsaved templates are not. Reopening a path moves
it to the top. Missing files produce a message without replacing the current map.

## Editing

New 400 / New 500 creates an in-memory document from hash-checked reference bytes.
Open reads an existing DE map. The canvas uses horizontal and vertical square
cells inside the diamond footprint; the gold line marks the playable boundary.
Wheel zooms around the cursor, middle-button drag pans, and Fit map restores the overview.
Right-click cancels the active tool/placement and unfinished stroke, clears the
selection and returns to Inspect without changing the map. Pan also supports left drag.
The grey outer diamond is nonplayable storage padding; the gold outline bounds
the playable map. Padding cells are protected from painting.

Choose Paint and a material, then drag. Each stroke is one undoable command.
Tools and Square/Circle/Mask shapes are direct buttons on the left. All eight
terrain swatches are visible on the right. Brush size has −/+ buttons (one cell
per click), editable numeric input and a synchronized slider. Regular brushes
support 1..400 or 1..500 according to map size; custom masks retain their original
dimensions and the 101x101 library limit. Selecting a terrain preserves the tool.
Select makes a rectangular selection; Fill selection applies the current material.
Clear or Esc clears selection/cancels an unfinished stroke. Optional Paint inside
selection clips strokes and mask stamps to its rectangle. With no selection,
painting covers the usual brush footprint. Protected cells remain skipped.
Create mask opens an 11x11 toggle grid. Masks can also be captured from a selection
or imported as JSON, rotated and mirrored. Mask painting stamps once per click.
The mask library displays thumbnails. Brush/material/mask/view preferences persist
in settings.json; missing masks fall back to Square. Experimental-resource opt-in
is not restored. Settings offers Reset UI settings without deleting masks/maps/history.
Inspect shows grid fields and entity records. Height (E) sets terrain elevation
with the current brush or selection fill. Target height has a0..255 slider,
numeric input and−/+ buttons, persisted in settings. Current and base heights
change together; occupied cells and unsupported terrain are protected. Height
exports are experimental: steep jumps can block movement or render badly;
cliff, display and pathfinding layers are not regenerated. The fixed jet height
view/colorbar spans0..255, with object/castle tinting suppressed for accurate colors.
Castle-area opacity now has a synchronized slider, numeric input and−/+ buttons.
Hold Ctrl while dragging a regular Paint/Height brush to lock to the dominant
horizontal/vertical axis. Release Ctrl to resume freehand painting.
Selecting Height view or changing the height target activates the height brush;
selecting Paint returns to Surface view. Unoccupied imported cliff/elevated terrain
can also be painted. Rejected strokes and building removals show an error dialog.

Castle removal can rebuild an unreadable1190 lord-slot lookup from matching2022
player data,1191 lord IDs and live lord records. This repair occurs only for a
castle edit and is undoable; an untouched map retains its original opaque bytes.
Removing buildings preserves the underlying base height. Verified on all eight
castles and911 cliff cells in `3v3 Einstein v1.1.map` (original unchanged).

Hover controls for tips. Help > Hotkeys opens a modeless reference generated from
actual registered actions, including standard File shortcuts and mouse gestures.
With the canvas focused: B Paint, E Height, G Build, D Remove, M Select, I Inspect, H Pan, F Fit, Esc Clear/cancel,
Ctrl+Z Undo and Ctrl+Y/Ctrl+Shift+Z Redo. Letter shortcuts do not interrupt numeric
or text entry. The Help menu also contains About.

Save (Ctrl+S) saves the current map; Save As (Ctrl+Shift+S) chooses a destination.
Replacing any existing map requires a confirmation showing its full path.
New documents and imported `.msv` files use Save As first. Both file dialogs
remember the last successful map Open/Save directory across app restarts.
Overwrite validates a temporary sibling file before atomic replacement; failed
replacement preserves the old file and removes the temporary file. No backup
maps are created. Backend callers must explicitly pass `overwrite=True`.
Unknown
sections, header extensions and untouched stored section bytes are preserved.
The writer validates and reads the result back. Closing an edited document asks
before discarding changes. There is no autosave/project format yet.

## Current scope and limitations

Save refreshes lobby player counts and start positions on both400 and500 maps,
including older exports with missing positions. Native positions for unchanged
castles are preserved.500 previews use the native three-cells-per-pixel scale
with black margins. New500 marker x rounding may differ by one preview pixel.
This menu repair does not rebuild terrain navigation or establish lord survival.

Tool panels are contextual. Vegetation (T) contains tree/shrub choices on the
left. Height and Variation show only their own sliders; Build shows ownership
and the building catalog. Paint shows the terrain palette and optional fixed
variation checkbox. Brush shape, cell size, masks and symmetry are shared across
Paint, Height, Variation and Vegetation. Changing tools preserves their values.

- Normal painting supports earth, oasis, sand, scrub, thick scrub, earth stones and marsh
  on flat unoccupied land. Nonplayable, occupied and unsupported cells are skipped.
- Stone/iron are available directly in the palette. Their multi-grid edits
  have structural tests, but game appearance and derived-data behavior need testing.
- The canvas uses schematic colors, not game textures. The Buildings list places
  reference-derived prefabs; Build uses the top-left cell as anchor and the
  colored P1–P8 buttons set ownership. The selected player has a white border.
  Green/red previews show allowed/blocked placement.
  Remove resolves linked building parts; walls are removed one cell at a time.
  Both operations support undo/redo. See `BUILDING_TOOLS_2026-09-20.md` for the
  catalog and experimental export limits. Only reference orientations are present.
- Save As generates a fresh schematic menu preview; embedded filename remains unchanged. Empty templates
  contain no castles and are not complete playable skirmish maps.
- Castle areas on 400 maps are 141x141, centered on the middle doorway, using
  the user-supplied rule. Solid player-colored footprints cover the keep, three
  doorway cells and camp (101 cells), excluding stockpiles. Area opacity defaults
  to 25% and is adjustable in View layers; castle coloring remains when areas
  are hidden. Player colors follow the stats repo's PlayerColor enum and UI
  swatches: red, orange, yellow, blue, black, violet, sky blue, green (IDs 1–8).
  On 500 maps the area is 161x161 (80 cells each side of the middle doorway),
  based on the user's follow-up observation. This adds 10 cells per side versus
  size 400. Radii are separate entries in `CASTLE_AREA_RADIUS`.
- Display preferences are created on first GUI startup in
  `%APPDATA%\SHCDEMapEditor\settings.json` and saved when changed.
- General player-resource editing, complete terrain reconstruction,
  water editing and optional 3D are future work. Do not infer their correctness
  from the inspector or from the ability to open a save renamed to `.map`.
- App-level validation is not a substitute for testing an exported map in game.

## Agent interface

The same backend serves GUI, CLI and Python. No screen automation is required.
For the windowed EXE use `--report` **before** the subcommand to obtain JSON, and
wait for the process to exit in PowerShell. Reports also require a new filename.

```powershell
$p = Start-Process .\dist\SHCDEMapEditor.exe -ArgumentList '--cli --report result.json edit --size 400 --recipe examples/editor-recipe.json --output my-map.map' -PassThru -Wait
$p.ExitCode
Get-Content result.json

.\.venv\Scripts\python.exe app.py --cli edit --size 500 --recipe examples/editor-recipe.json --dry-run
.\.venv\Scripts\python.exe app.py --cli inspect my-map.map --cell 400 400
.\.venv\Scripts\python.exe app.py --cli validate my-map.map
```

Recipe schema: `{"version":1,"operations":[...]}`. Operations execute in one
transaction and roll back together on failure. `paint` accepts `material` and
exactly one of `rect:[x,y,width,height]` or
`brush:{"x":400,"y":400,"size":9,"shape":"circle"}`. `stamp` accepts `material`,
`pattern` (JSON path relative to the recipe), `x`, `y` (upper-left), optional
`rotation` (0/90/180/270), and `mirror` (boolean). Stone/iron need no opt-in.
Optional `variation:0..65535` writes a fixed variation on eligible painted cells.
Reports include eligible/skipped/changed counts;
agents must check these because protecting a cell is not an operation error.
Dry-run applies the recipe in memory and validates it without exporting a map.

Building operations (experimental, same behavior as GUI):
`{"op":"place_building","building":"castle","x":390,"y":390,"owner":1}` and
`{"op":"remove_building","x":393,"y":397}`. Catalog keys are available from
`editor.buildings.catalog()`; Python callers use `BuildingService(document)`.
Recipes remain atomic across terrain and entity operations. Buildings currently
require clear ground at height8. Prefabs include reference ground/resource cells;
they are map-design stamps, not gameplay construction with costs.

Height recipe: `{"op":"set_height","height":128,"rect":[390,390,20,20]}`.
Accepts either `rect` or the same `brush` object as terrain painting. Uses shared
`HeightService`; undo and recipe rollback cover both height layers atomically.

Masks use `{"version":1,"name":"patch","cells":[[1,0],[1,1]]}`. Masks are
rectangular, nonempty, up to 101x101, and contain only boolean or 0/1 cells.
Brush Import also accepts PNG: one pixel per cell, white paints, black or
transparent skips (brightness and alpha threshold128). It saves a JSON mask in
the user's library and selects it. See [image mask prompt](IMAGE_MASK_PROMPT.md).
View → Variation displays texture-noise values on a fixed grayscale 0–65535 scale.
Variation (N) paints the selected value using ordinary brushes, masks, symmetry
and selection fill. Texture variation/noise → Apply with terrain painting writes
the value alongside terrain in one undo operation. A constant value produces
repeatable variation, not guaranteed identical sprites across terrain boundaries.
CLI: `{"op":"set_variation","variation":0,"rect":[390,390,20,20]}`.

```python
from editor import TemplateLibrary, TerrainService, MapWriter
doc = TemplateLibrary().create(400)
with doc.transaction('Garden'):
    cells = doc.geometry.brush(400, 400, 15, 'circle')
    result = TerrainService(doc).paint(cells, 'oasis')
doc.history.undo()
doc.history.redo()
MapWriter.save_as(doc, 'garden.map')
```

## Architecture

`document.py`: MapDocument owns original bytes, decoded grids, patches and history;
MapReader/MapWriter handle lossless I/O. Transactions group commands or roll back.
`geometry.py`: storage coordinates, playable bounds, brushes and selections.
`services.py`: TerrainService, EntityService and MapValidator centralize rules.
`buildings.py`: reference catalog, placement validation, linked records and removal.
`templates.py`: verified immutable base maps. `patterns.py`: portable JSON masks
and Roaming library. `render.py`: schematic raster generation independent of Qt.
`gui.py`: Qt input/background I/O and action registry; `panels.py`: reusable
controls and HotkeysWindow; `state.py`: Qt-independent editor choices;
`cli.py`: JSON command adapter. Large brush sweeps use row-wise vectorized unions,
and the canvas uses a raster preview instead of per-cell drawing calls.

Add capabilities to domain services first, then expose them through both adapters.
Never implement binary mutations only in a widget. Backend imports must stay
headless. Preserve original opaque bytes instead of inventing defaults. Add
meaningful roundtrip, boundary, transaction and preservation tests for new edits.

## Development and packaging

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest -q
.\.venv\Scripts\python.exe app.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm SHCDEMapEditor.spec
```

`--self-test <new-directory>` runs hidden native Qt interaction checks and writes
screenshots, an exported test map and `result.json`. It checks both bundled
templates, lossless no-op, mouse paint, undo/redo, selection fill and mask storage.
Build with Windows x64 Python. The supplied executable is unsigned.

For updates, replace `dist/SHCDEMapEditor.exe` at its usual path. If it is open,
ask the user to close the editor and wait; do not create alternate build copies
or terminate their session.

Test on a clean Windows machine and validate representative exports in game before declaring
a stable release. This repository has not been published to GitHub by this work.
