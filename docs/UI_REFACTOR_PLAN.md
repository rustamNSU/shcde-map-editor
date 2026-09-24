# UI refactoring proposal — 2026-09-20

Status: implementation authorized and completed for UI refactoring plus selection
Clear/Esc and optional paint-inside-selection. New tools in work-order steps 3–4
remain follow-ups. The existing dark visual style is retained, along with
flat square-cell canvas, map bounds, castle display, recent maps and right-drag pan.

## Research and decisions

Reviewed the current build_left/build_right, paint/selection handling and material
registry in editor/gui.py and editor/services.py, plus official editor manuals.

| Reference | Documented pattern | Proposed use here |
|---|---|---|
| [Tiled terrains](https://docs.mapeditor.org/en/latest/manual/terrain/) | Terrains have names, colors and optional tile icons; terrain choice is separate from the editing tool. | Visible named material swatches, distinct from brush shape. |
| [Krita brush presets](https://docs.krita.org/en/reference_manual/dockers/brush_preset_docker.html) | Clicking a preset icon selects a brush. | Visible mask thumbnails with names and selected-state border. |
| [GIMP tools](https://docs.gimp.org/3.0/en/gimp-tools.html) | Toolbox and tool options; some tools are grouped/hidden by default. | Direct tool buttons plus nearby contextual controls. Keep our small tool set ungrouped. |

These are workflow references, not a claim to reproduce those apps. Tiled's
automatic terrain transitions require terrain data/rules; our binary terrain
dependencies are still incomplete, so this UI change must not imply autotiling.

## Current problems

- Inspect/Paint/Select/Pan require opening a combo box.
- Square/circle and reusable masks are separate dropdowns, obscuring active brush.
- Eight materials occupy one dropdown instead of a browsable palette.
- Brush, selection and mask controls remain displayed together even when irrelevant.
- Long explanatory labels and the large inspector displace frequent controls.
- Selection currently supports rectangular fill only; painting does not respect
  its bounds, and there is no prominent clear-selection action.

## Proposed layout

| Left: tools and brush, ~240 px | Center: canvas, flexible | Right: terrain and views, ~280 px |
|---|---|---|
| Paint / Select / Inspect / Pan buttons | Existing 2D map | Full terrain palette, two columns |
| Square / Circle / Mask buttons | Cell-accurate brush preview | All six normal materials |
| Size − / numeric cells / + and slider | Selection outline | Stone / Iron resource swatches |
| Tool-specific options | Right/middle drag navigation | Experimental-resource toggle beside resources |
| Visible mask thumbnail library | Coordinates and zoom in status bar | Surface / Height buttons |
| Compact history at bottom | | Grid, objects, castle areas, opacity |
| | | Minimap + compact inspector |

Top menu bar: File, Edit, View, Help. Help contains Hotkeys and About.
Keep a separate quick-action toolbar: New 400, New 500, Open, Recent maps,
Undo, Redo, Fit, Validate, Save As, Settings. Move About and long instructions into Help rather
than using permanent side-panel space. Core tools and all eight material choices
stay visible at 1280x800, 100% scaling. At 1000x700 or high DPI, allow local panel
scrolling with no clipped controls. Do not introduce hidden material categories.

## Interaction specification

1. Tool buttons: two-by-two grid, icon + short label + shortcut tooltip, one active
   tool visibly selected. Paint (B), rectangle Select (M), Inspect (I), Pan (H).
   Right/middle drag always temporarily pans and returns to the chosen tool.
   Shortcuts must not steal text input while typing into fields.
2. Brush buttons: Square, Circle, Mask, directly visible below tools. A visible
   size row has −, an editable numeric field, and +. Each click changes size by
   exactly one cell; minimum is 1 and − is disabled there. Retain direct typing
   for large brushes, alongside a synchronized slider. Commit valid typed values
   on Enter or focus loss; reject invalid input with a clear message. Do not
   silently cap typed sizes at the existing 101-cell limit. Proposed new maximum
   is the current map size (400 or 500), shown beside the field and in its tooltip;
   confirm large-brush performance before shipping this increase. Clamp restored
   preferences when opening a smaller map. Square/circle cursor preview shows
   actual affected cells clipped to playable bounds. Mask size is intrinsic;
   show its dimensions and disable these size controls in mask mode rather than
   pretending they scale the mask. Existing custom-mask limit remains separate.
3. Mask gallery: small monochrome cell previews and names, locally scrollable.
   Keep Create, Import, From selection. Rotation left/right buttons and Mirror
   replace the angle dropdown; show resulting angle. Clicking a mask selects
   Paint + Mask. Regular shapes leave mask mode. No material baked into masks.
4. Terrain palette: two-column named swatches for Earth, Oasis, Sand, Scrub,
   Thick scrub, Earth stones; Stone and Iron below with Experimental badges.
   Use existing schematic colors, visible selected border and checkmark.
   No reliance on color alone. All entries remain visible; unsupported resource
   painting stays gated by explicit opt-in. Selecting a terrain changes material,
   not tool, so choosing a fill material does not destroy the selection workflow.
5. Selection: show dimensions, Fill with <material>, Clear selection, Save mask.
   Disable actions without a valid selection. Esc clears selection/cancels an
   uncommitted gesture without changing map bytes. Phase 1 retains current fill
   behavior; selection-clipped painting is a separately tested phase 2 change.
6. View controls: Surface/Height visible buttons, existing grid/objects/area
   toggles and opacity. Height remains read-only. Keep material palette visible
   while changing views. View choices and opacity never enter map undo history.
7. Inspector: concise cell/entity summary on click, optional expanded Details
   for raw values. Preserve access to current information; reduce always-visible
   empty space. Minimap remains visible when space permits.
8. Status bar: cell coordinates, zoom, active tool/material/brush; after edits
   retain eligible/skipped counts. Long help text moves to tooltips/help.
9. Hover tips: all tool buttons, brush shapes, terrain swatches, mask thumbnails,
   sliders, view toggles and toolbar actions have concise tooltips. Show action
   name, what it does, and assigned shortcut when present. Include units and
   relevant limits (brush size in cells, mask intrinsic size, experimental
   resource status). Disabled controls explain why they are unavailable; use
   the control's container if Qt does not show tips on the disabled widget.
   Use a short standard hover delay, no clicks required. Tips disappear on
   leaving the control and do not interrupt painting or follow the canvas cursor.
   Keep essential labels visible: tooltips supplement them.
10. Help > Hotkeys opens a separate modeless window titled Hotkeys. Group rows
    into File, Editing, Tools, View/navigation, with Action, Shortcut and Context
    columns. Add a separate Mouse controls group for right/middle drag and wheel.
    The editor remains usable while this reference window is open; clicking
    Hotkeys again raises the existing window. Include Close and normal window
    controls. Display only implemented bindings; proposed shortcuts appear only
    once their actions are available. Read-only reference in this phase, not a
    shortcut-customization interface.

## Hotkeys reference contents

Current bindings to retain: New 400, Open, Save As, Undo, Redo use the app's actual
Qt standard key bindings; Fit map uses F. Show their resolved Windows labels and
all registered alternatives rather than duplicating hardcoded shortcut strings.
Make clear that the current New shortcut creates a 400 map and Save performs
Save As. New 500 and other commands with no binding need not be listed as hotkeys.

Planned additions in this refactor: B Paint, M Select, I Inspect, H Pan. Esc
selection/gesture behavior is added with phase 2 and documented then. Display
contexts such as canvas/editor focus and explain that letter shortcuts do not
trigger when typing in text or numeric inputs. Mouse navigation has its own
entries; right-drag remains navigation, independent of the active tool.

## Implementation structure

- Extract ToolPanel, BrushPanel, MaterialPalette, ViewPanel and InspectorPanel
  from the large EditorWindow. It retains document I/O and orchestration.
- Introduce a small EditorState for tool, material, brush shape/size and mask
  transform. Panels update this state through signals; canvas consumes it.
  Do not read editing semantics from combo-box indices or visible labels.
- Use stable material IDs and a small presentation registry for names, colors
  and experimental status. Keep TerrainService as the enforcement point.
- Centralize action IDs, labels, help descriptions, shortcuts and contexts in
  an action registry. Menu, toolbar and tool buttons invoke the same actions.
  Tooltips and the Hotkeys window derive bindings from those actions so help
  cannot drift from actual behavior. Keep mouse gesture descriptions alongside
  the registered navigation behavior. Add a reusable HotkeysWindow component.
- Keep selection geometry independent of widgets so future selection-clipped
  operations can be shared with headless commands; no GUI-only binary mutations.
- Preserve CLI recipes, MapDocument/history and lossless MapWriter contracts.
- Expand the shared regular-brush geometry limit together with the UI, so typed
  large sizes work in GUI and agent recipes consistently. Use vectorized cell
  operations and an efficient preview for large brushes; avoid per-cell painter
  calls or recomputing the whole brush for every interpolated cursor step where
  this causes stalls. Retain one undo command per stroke and protected-cell rules.
- Persist brush size/shape, material, mask path/transform and existing view
  preferences in settings.json. Restore missing masks to Square. Do not persist
  transient selection, active drag or experimental-resource permission silently.
  Keep recent-files.json and mask files compatible. Add Reset UI settings.

## Work order

1. Refactor existing controls: visible tools, shapes and materials; mask gallery;
   compact layout; −/+ brush size controls and typed large-brush support;
   hover tips; Help menu and Hotkeys window; component extraction
   and shared UI state. Existing editing
   behavior stays intact. This is the first deliverable after plan approval.
2. Improve selection workflow: Clear/Esc, precise preview, optional explicit
   Paint inside selection toggle (initially off), tested clipping for brushes
   and stamps, one undo command per stroke/fill.
3. Add genuinely new tools in separate changes: material eyedropper, line and
   rectangle painting, then connected-region fill with preview/cancel and the
   same protected-cell rules. These are proposed follow-ups, not current features.
4. Later research-driven additions: entity placement, height/water edits and
   terrain transitions, once backend behavior is established. 3D stays later.

## Acceptance checks

- Every current tool, basic brush shape and material selectable in one click
  without opening a list. Named current choice is always apparent.
- Validate 1280x800 and 1440x940 plus 1000x700 and Windows DPI scaling. Common
  paint controls remain reachable and the canvas keeps useful working space.
- Switch tool/material/mask in varied order; check state and cursor agree.
- Verify −/+ increments of exactly one, minimum 1, synchronized slider/input,
  typed sizes above 101 and at the map-size maximum, invalid entries, smaller-map
  preference restoration, and disabled sizing for intrinsic masks. Measure
  preview/drag responsiveness at large sizes on both 400 and 500 maps and check
  undo, boundary protection and headless geometry parity.
- Hover tips identify actions and correct bindings, including disabled reasons.
  Help > Hotkeys opens one reusable window, lists actual bindings and mouse
  gestures, and closes without closing the editor. Confirm every listed shortcut
  invokes the documented action in its stated context; typing remains unaffected.
- Right drag still never paints. Painting, selection fill and stamping preserve
  undo/redo, protected cells and source files. UI settings do not dirty maps.
- Restart restores valid preferences; deleted masks and malformed settings recover.
- Existing headless tests pass; focused Qt tests use stable controls/state, not
  old combo indices. Compare native Qt screenshots of palette and selection modes.
- Rebuild only dist/SHCDEMapEditor.exe. If open, ask user to close and wait.
  No alternate release folders or extra executable copies.
