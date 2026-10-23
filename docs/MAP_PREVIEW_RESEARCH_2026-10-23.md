# Embedded map thumbnails: native generator versus our editor

## Finding

The picture saved inside a DE `.map` is **not a PNG**. It is a compressed,
indexed 200×200 radar image. Our editor writes a valid instance of that format,
but currently draws a schematic approximation. Saving a map in our editor
therefore replaces the native picture with a visibly different picture.

This is a rendering difference, not a failed image decoder or a PNG/JPEG
compression problem. The actual map sections are separate from the picture.

## Stored format

| Item | Format |
|---|---|
| File +0x00 | Map magic, usually `0xFFFFFFFE` in DE |
| File +0x04 | Outer thumbnail-block byte length |
| File +0x08 | Uncompressed byte length: 40,512 |
| File +0x0C | Compressed byte length |
| File +0x10 | CRC32 of the decoded thumbnail |
| File +0x14 | DCL/PKWARE compressed data |
| Decoded +0x0000 | 256 little-endian RGB555 colours, 512 bytes |
| Decoded +0x0200 | 200×200 palette-index bytes, 40,000 bytes |

Some files also have descriptive text after the compressed data but inside the
outer thumbnail block. `MapFile.preview_extra` retains this independently.
Player/keep start markers are separate: eight X/Y pairs in header U4 at +0x10,
stride 8. They are not the image pixels.

An RGB555 palette entry is `(red5 << 10) | (green5 << 5) | blue5`.
Our inspection PNGs decode this data for viewing; the PNGs are not what is
embedded in the map. The game's Steam Workshop upload path also exports a
separate PNG after reading the saved map thumbnail.

## Verified save chain

The managed GUI passes a save path and metadata to the native engine. It does
not take a Unity screenshot and pass that screenshot into the map save:

```text
HUD_IngameMenu.SaveMapEditor
  -> EditorDirector.SaveSaveGameOrMap(mapSave: true)
  -> EngineInterface.SaveSaveGame
  -> CrusaderDE!DLL_SaveSaveGame
  -> native save-container routine, RVA 0x52B0
  -> native saved-radar generator, RVA 0xF4DF0
  -> DCL compression and outer thumbnail-block write
```

The native save wrapper is RVA 0x86F80. Addresses in this report are RVAs,
relative to the module's load address, for the pinned DLL below.

Live save-menu preview uses `DLL_GetSaveRadar` (RVA `0x84290`); the wrapper allocates 160,000
bytes (200×200×4, BGRA) and sixteen keep-coordinate integers.
Reading an already saved thumbnail uses `DLL_UnpackRadarToARGB` (RVA `0x87B80`),
which decompresses the block and calls palette decoder `0xF6FB0`.
See [managed call-chain evidence](MAP_PREVIEW_MANAGED_2026-10-23.md).

## What the native renderer does

`0xF4DF0` fills a 200×200, 32-bit scratch image from packed map cells. It uses
native colour lookup tables and cell flags, with special unit/ownership cases.
It does not require terrain sprite artwork to create this stored radar image.

Confirmed input families:

| Input | Native RVA | Saved data |
|---|---:|---|
| Terrain/occupancy flags | `0x48F71B0` | Section 3003, uint32 per cell |
| Secondary terrain flags | `0x4A312B0` | Section 3037, byte per cell |
| Tile variation | `0x485A770` | Section 3008, uint16 per cell |
| Current surface height | `0x4DDD350` | Section 3005, byte per cell |
| Extra display flags | `0x4F64CF0` | Section 3007, uint16 per cell |
| Unit slot at cell | `0x4C559B0` | Section 3010, int16 per cell |
| Building slot at cell | `0x4B6AA50` | Section 3012, int16 per cell |
| Cell lighting | `0x4EC82B0` | Runtime `LuminescenceLayer`; not a saved descriptor in the pinned registry |

Tile variation selects different entries from small colour tables, explaining
much of the native speckled appearance. Lighting applies a table-based
percentage multiplier to terrain colours. Native projection has separate
parameters for each supported map size; it is not just arbitrary image resizing.

After drawing, the native function reduces each pixel to RGB555 and assigns
palette indices in first-occurrence order. It returns `0x9E40` = 40,512 bytes.
It does not call an adaptive image quantizer. If all 256 entries are used,
another previously unseen colour falls back to index 0. Unused palette entries
are copied from uninitialized local storage; matching those unused bytes is
not a meaningful visual-accuracy criterion. Exact projection, colour-table
data and the remaining derived-lighting requirements are recorded in
[the native supplement](MAP_PREVIEW_NATIVE_2026-10-23.md); this report does not
claim the current application reproduces them.

## Why our current export differs

`editor/preview.py` currently:

1. Calls our schematic `render_rgb`, using our own surface/entity colours.
2. Adds invented gradient shading from base-height section 3045.
3. Samples with an approximate inverse projection.
4. Adds simplified tree dots and hand-drawn coloured castle icons.
5. Uses Pillow MEDIANCUT to quantize to 256 colours.

Each of these differs from the native radar renderer. The existing output is
readable by the game but is not an exact visual reproduction. Save/Save As
explicitly refreshes the picture, including when opening and saving an
otherwise unchanged map. Low-level no-op serialization still preserves the
original bytes unless preview refresh is requested.

The earlier report's phrase “scene/sprite thumbnail renderer” was an
unverified description. The native code establishes a cell-colour radar
renderer instead.

## Same-map comparison

Input: `output/ada-resave-2026-09-20/2v2 Ada.map`, a saved native-editor reference.
SHA256: `4b93b8416708d3d11b4e5e736a7f71c6a1728d7992fa5457a074215e19333bde`.

Both images were decoded with the same RGB555 decoder, using the native
5-bit-channel left shift by 3. Both show stored row order; the native Unity
texture upload reverses rows to suit its texture orientation. The current picture
was generated from the exact same saved map without editing its sections:

- Native stored picture: 56 palette indices used.
- Current schematic picture: 25 palette indices used.
- 27,556 of 40,000 pixels have different decoded RGB values.
- The source map hash was checked again afterward and is unchanged.

These numbers establish the current difference; they are not an accuracy
score for an unimplemented native port. PNG evidence is in
`output/preview-comparison-2026-10-23/comparison.png`.

Reproduce from the repository root:

```powershell
.venv/Scripts/python.exe -m research.compare_map_previews `
  'output/ada-resave-2026-09-20/2v2 Ada.map' `
  --output output/preview-comparison-2026-10-23
```

## Correct implementation direction

Replace the schematic thumbnail path with an offline port of the native
radar rules: exact map-size projection, variation-based terrain colours,
flag precedence, cell lighting, unit/owner handling, and first-seen RGB555
palette construction. Validate decoded pixels against native-saved maps at
multiple sizes and with height/water/building examples. Merely reusing the
old embedded thumbnail would keep native appearance but would become stale
after edits.

This investigation changes research scripts/reports only. The application,
release EXE, installed game libraries and original maps are unchanged.

## Provenance

Native library: installed `CrusaderDE.dll`, SHA256
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.
Analysis uses file reads, read-only Ghidra exports and saved reference maps.
No running game process is needed for these findings.

Native decompilation:
`output/preview-native-2026-10-23/native/native_thumbnail_producer.c`.
Existing serializer export:
`output/runtime-audit-2026-10-23/native/save_container.c`.
