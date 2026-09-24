# Texture variation investigation, 2026-09-19

## Follow-up: painted map saved and compared

`etest_noise_00000_textures.map`, SHA256
`70456f8ad98e02b250e5f7e6f2a263d165d4cee0b1d89876c1e25704e66bf53b`,
was compared with the archived exact generated zero-noise baseline.
Reproduce with `research/check_painted_noise.py`. Snapshot, full section diff, grouped
findings and all 9479 cells with changed logic/surface are in
`output/noise-painted-2026-09-19/` (painted_cells.csv).

**Section3008 is byte-identical over all641600 bytes. Zero cells changed.**
All123504 interior cells remain noise0, including all9479 with changed logic or
surface. Therefore this brush-edit/save session did not regenerate the noise.

Examples (counts are exact logic/surface combinations):

|Material|Count|Logic|Surface|Example x,y|Noise before/after|
|---|---:|---|---:|---|---|
|earth&stones decoration|578|0x8000|2|440,506|0/0|
|sand|545|0x8000|64|464,479|0/0|
|stone resource|545|0x28000|0|311,401|0/0|
|iron resource|545|0x88000|0|406,358|0/0|
|oasis|545|0x8000|16|487,435|0/0|
|sea|545|0x1|0|488,385|0/0|

Other grids did change:3003(5334 cells),3037(4437),3005(4113),3045(3023),
3007(3198),3036(97706), among others. Of3036 changes,89863 occur on interior
cells with unchanged logic, surface and both heights. This is evidence of broad
auxiliary-state changes on loading/editing/saving the patched map, but does not
isolate which operation caused them or prove3036 is a graphics cache.

Conclusion strengthened: noise is persistent per-cell data independent of the
painted material. Exact rendering function and native runtime-field mapping are
still unresolved. Original user map unchanged (rehash/readback verified).

## Follow-up: user tested constant-noise maps in game

The user loaded etest_noise_00000, etest_noise_32767 and etest_noise_00001 and
provided screenshots in that order. Each was generated from base500 by changing
only section3008 on interior land; the generator verified all other sections and
header bytes unchanged. All three show visibly repetitive ground. Screenshots
use different zoom levels, so motif scale and pixel differences cannot be treated
as a controlled comparison of values. No same-zoom original control was supplied.

The user also reports that painting stone, iron and other surfaces on these maps
produces unusual appearance. Those newly painted surfaces are not pictured in
the supplied screenshots. Combined with the controlled file change, this is
evidence that3008 affects terrain rendering and is shared per-cell variation data,
not an earth-only material parameter. Whether painting preserves its exact bytes
requires a saved painted map; that has not been checked.

The earlier uncertainty about whether3008 affects rendering is now narrowed by
the in-game experiment. Exact bit interpretation, noise-to-atlas mapping and
the native runtime field identity remain unproven. Constant0 is not established
as 'disable noise'; it is simply an input that causes repetitive rendering.

Screenshot provenance (user labels):
- 0: codex-clipboard-4af9dbdc-7172-40ae-9cf7-11877bbfb4b3.png
- 32767: codex-clipboard-144fb405-c372-4b29-8fe8-c9091fdf23ed.png
- 1: codex-clipboard-9314a896-8f58-4190-a8d5-7f6cc4ddd82d.png

The following sections record the earlier file-only investigation.

## Scope and reproducibility

Read-only analysis of all 29 copied references, including empty 160/200/500,
pure resave, earth & stones, sand, iron and stone resource. Run
`.\.venv\Scripts\python.exe -m research.analyze_textures.py` from this repository.
Output: `output/references-2026-09-19/texture_analysis.json` includes source hashes,
per-material/per-layer histograms, same-coordinate samples and comparisons against base500.
No original maps or copied map bytes are modified. No game rendering was performed.

## Direct file observations

All 24 sections with lengths compatible with uint8/uint16/uint32[320800] were
examined, not just the surface flags. That is a candidate-grid scan; dimensions
alone are not proof of semantics.

Section 3008 is uncompressed, 641600 bytes, interpreted as uint16 LE[320800].
In the 123504 interior cells of ref_00_base_500:

- 3003 is uniformly 0x8000 (land).
- 3037 is uniformly 0 (default surface).
- 3005 and 3045 are uniformly 8.
- 3008 has 14974 distinct values.
- 3036 has 437 distinct values; its interpretation remains unresolved.

Three adjacent cells in that empty map:

| x,y | 3003 | 3037 | 3005 | 3008 | 3036 |
|---|---|---|---|---|---|
|390,390|32768|0|8|14345|4552|
|391,390|32768|0|8|20379|4616|
|392,390|32768|0|8|7043|2|

Therefore the saved data of uniform ground is not just one repeated material ID.
Distinct numbers in 3008 are NOT counts of texture images.

| Sample/material mask | Cells | 3003 | 3037 | 3007 | Distinct 3008 |
|---|---:|---|---|---|---:|
|earth&stones surface|197|0x8000|2|16|197|
|sand surface|117|0x8000|64|16|117|
|iron resource|1|0x88000|0|2064|1|
|stone resource|1415|0x28000|0|2064|1389|

All rows have height 8. Earth&stones decoration and stone resource are different
representations: the former uses surface flags, the latter logic resource flags.
Iron has only one resource cell in the provided reference; its intra-material
variation cannot be established with that one sample.

Whole-section equality controls (320800 uint16 values, not a small patch):

- base500 = resave500 = ref02 for 3008.
- iron400 = earth&stones400 = sand400 for 3008.
- base160 = base200 for 3008.
- All 29 maps divide into 8 distinct SHA-256 groups for 3008.
- base500 differs from iron/earth&stones/sand at every position in 3008.

Thus 3008 can persist across material changes and resaves, and can differ between
maps. The mixed creation history does not establish precisely when it is generated.
It is not evidence that every new map receives a unique seed (160/200 are equal).

## Local source corroboration and limits

Script Extender `src/SHCDESE.BepInEx/Interop/GameTileManagerView.cs` defines:

- `TileRandomNoiseGrid`, uint16 per tile, documented as Random Noise Variation Grid.
- `Logic2Grid`, byte material/surface flags.
- `GFXGrid`, int32 graphics descriptors with atlas-related comments.
- `AlphaGFXGrid`, atlas/image descriptors for building graphics.
- `MiscDisplayGrid`, rendering flags, with flat ground 16 and rocks/boulders 2064.

`src/SHCDESE.BepInEx/API/GameTileManagerAPI.cs` explicitly copies RandomNoise on
SEMA export (line 1401) and restores it on import (line 1791), independently of
Logic and Logic2. SEMA is the extender's own area format, not the game's .map format.

The file evidence and runtime source make 3008 a strong candidate for the saved
random-noise grid, and 3007 a candidate for MiscDisplayGrid. This investigation
does NOT directly trace the native .map loader to prove those mappings.
No direct final GFX array was identified: among the 24 exact-size candidate grids,
the only uint32[320800] section is 3003 (logic). This does not exclude alternative
packing or graphics information elsewhere.

## What is and is not established

Established: uniform terrain retains varying per-cell auxiliary values; material
flags alone do not exhaust the saved cell data; resource and decorative stone
are represented differently; noise-like values survive material changes.

Strong interpretation: per-cell noise contributes to graphical variation,
consistent with the separate random-noise and graphics grids in Script Extender.

Not established: exact noise-to-image formula, texture count per material, atlas
indices, edge blending rules, macro pattern meaning of 3036, and whether a reload
always produces pixel-identical game rendering. The current semantic renderer
uses invented flat colors and cannot answer those rendering questions.

To reproduce the actual appearance, the next useful investigation is native
terrain-to-GFX selection and the game's texture atlases, not merely more material
flag IDs. Original map files remain untouched.
