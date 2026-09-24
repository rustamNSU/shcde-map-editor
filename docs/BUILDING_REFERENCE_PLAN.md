# Building reference and next editor work

Historical planning brief, superseded by the user's implementation request.
See `BUILDING_TOOLS_2026-09-20.md` for measured footprints, implemented tools,
reference provenance and remaining limitations. The notes below describe the
earlier planning stage, not the current app's capabilities.

## User intent

- Next capability: building editing, including removal, with future placement
  and other operations supported by the same backend used by GUI and agents.
- The user is preparing a 400-size reference map containing many building types.
  Use it to establish IDs, cell footprints and how to represent/select them in
  the flat 2D editor. The attached game screenshot is a visual reference, not
  reliable evidence of exact cell dimensions.
- Build a research catalog for every type present, even if most will not be
  exposed as placement choices in the GUI. The desired GUI subset is not yet
  specified. Do not fill the toolbar/palette with every enum entry by default.
- Use existing Script Extender enums and the stats project's building research
  as cross-reference sources. Do not rediscover IDs purely from appearance.

## Located reference

User called it `ref_11_budings_400`; the current on-disk spelling is
`ref_11_buidlings_400.map` (preserve this exact filename).

Path:
`C:\Users\rustam\AppData\LocalLow\Firefly Studios\Stronghold Crusader Definitive Edition\Maps\ref_11_buidlings_400.map`

At the notes-only inspection: 3,524,504 bytes; SHA-256
`52514e52710005786836b1d1e323f5ff1a3013f05cfe1d6040b6a95d00b58d24`.
This establishes that a file exists, not that the user has finished populating
it. No building inventory or footprint measurements have been performed on
this new reference yet. Recheck its hash before analysis; the user may resave it.
Keep original read-only; archive a hashed snapshot for the actual analysis.
Do not confuse it with the older `ref_11_walls_400.map`.

## Existing evidence to reuse

- `docs/EDITOR_READINESS.md`, `docs/REFERENCE_ANALYSIS_2026-09-19.md`,
  `docs/SAVEGAME_LETO_2026-09-19.md`, `semantics.py`.
- Buildings: section 4013, 812-byte records; state +0xD0, type +0xD2,
  owner +0xD6, global ID +0xD8, tile X/Y +0xEE/+0xF0, tile index +0xF4,
  square-side field +0xF8, access coordinates +0xFE/+0x100.
- Section 3012 stores building **slot** references, not global IDs. Compare its
  actual per-slot cell mask against the footprint field; do not assume every
  building is a filled square or that a sprite's visible extent is its footprint.
- Castle complex already demonstrates multiple records for one logical object.
  Main keep, doors, camp and stockpile need explicit grouping; no universal
  grouping field has been established.
- Existing save research includes reciprocal building/worker links. Removing
  only a 4013 record or only its visible 3012 cells is not established as valid.
- Plain walls/stairs may be grid data rather than building records. Identify
  which screenshot/reference objects belong to which representation.

Source locations (read-only research):

- `C:\repositories\shcde-script-extender\src\SHCDESE.BepInEx\Interop\Enums.cs`
  and `Interop\GameBuilding.cs`; building manager APIs for runtime relationships.
- `C:\repositories\shcde-stats-rust\instructions\building.md`,
  `instructions\enums.md`, `src\engine\building.rs`, `src\engine\enums.rs`.
- Runtime offsets and enum labels are supporting evidence, not automatic proof
  of the on-disk format. Verify each ID against records in the reference.

## Analysis deliverable once the reference is ready

1. Inventory every building record and group by type; map numeric IDs to source
   enum names, retaining unknown IDs explicitly.
2. For each instance, record slot/global ID, owner, anchor, entrance/access,
   footprint field, actual occupied-cell count, bounding width/height, and exact
   cell mask. Flag holes, non-square masks, variants and rotations.
3. Produce an annotated 2D footprint sheet with IDs/names and a machine-readable
   catalog. Distinguish occupied cells, access cells, terrain/support changes
   and visual sprite extent. Mark confidence and source hash per finding.
4. Identify linked records, workers, counters, player state and affected grids.
   A populated reference establishes representation; it cannot by itself prove
   correct deletion/allocation. Use controlled before/after removal and re-add
   comparisons where existing evidence is insufficient.
5. Propose GUI treatment: exact occupied-cell hit testing and highlight,
   ID/name/owner inspector, ghost footprint for supported placement, and a
   deliberately limited placement palette. Unsupported objects remain visible
   and inspectable; unknown removal rules must not become a destructive eraser.
6. Implement verified building operations in backend services with transactions,
   undo/redo, reference validation and lossless export before wiring GUI controls.
   Validate exported operation examples in the built-in editor/game.

No map bytes, app behavior or executable changed while recording these notes.
