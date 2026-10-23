# Native saved-map radar renderer, 2026-10-23

This is file-only research against the pinned `CrusaderDE.dll`, SHA256
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.
The game, application, maps and release EXE were not modified or executed.
The existing Ghidra database was opened with `-readOnly -noanalysis` and its
in-memory changes were discarded. All addresses below are module RVAs.

The exact thumbnail-producing function is **0xF4DF0**. It draws a cell-colour
radar image. It does not render terrain/building sprites, call a scene capture,
or load GFX sprite atlases to produce the embedded image. This corrects the
unverified “scene/sprite thumbnail renderer” description in the older report.

## Producer, serializer and decoder are distinct

| Entry | Verified behavior |
|---|---|
| `DLL_SaveSaveGame`, `0x86F80` | Native save wrapper, already exported in the runtime-format audit |
| Save container, `0x52B0` | At `0x54C0` calls `0xF4DF0` with radar context `0x3496220`; at `0x54DB` compresses returned bytes at `0x3496298` with `0x8310`; writes the outer thumbnail block |
| Radar producer, `0xF4DF0` | Allocates/clears a 160,000-byte RGB32 scratch image, allocates 40,000 indices, renders cells, builds RGB555 palette, returns `0x9E40` = 40,512 |
| `DLL_GetSaveRadar`, `0x84290` | Calls `0xF4DF0`, copies sixteen keep-coordinate integers from `0x34A9B18`, expands palette/index data using `0xF6FB0`, returns current map size |
| `DLL_UnpackRadarToARGB`, `0x87B80` | Requires a decompressed size of 40,512, decompresses with `0xCFE0`, then calls `0xF6FB0` |
| Palette/index expansion, `0xF6FB0` | Expands RGB555 to four-byte colour pixels and reverses row order for the Unity texture buffer |

The producer writes its 512 palette bytes at context `+0x78` and its 40,000
index bytes at `+0x278`. Therefore the serializer's input at `0x3496298`
begins with the palette, as the independently decoded map files established.
`0x52B0` is a real producer caller, not evidence that serialization itself
creates a picture by converting arbitrary map grids.

`0xF5A40`, exported as `native_minimap_candidate`, is an adjacent renderer
sharing several colours and grids. The confirmed save path calls `0xF4DF0`;
the adjacent function should not be substituted for that entry.

## Cell inputs

| Runtime RVA | Persisted equivalent | Exact use in `0xF4DF0` |
|---|---|---|
| `0x48F71B0` | 3003, uint32 | Logic flags; terrain colour precedence and building/tree overrides |
| `0x4A312B0` | 3037, uint8 | Surface bits |
| `0x485A770` | 3008, uint16 | `noise & 3` or `noise & 7` selects table colour |
| `0x4DDD350` | 3005, uint8 | Ordinary-ground palette changes above height16 |
| `0x4F64CF0` | 3007, uint16 | Pitch colour override when bit `0x2000` is set |
| `0x4C559B0` | 3010, int16 | Unit slot occupying a sampled cell |
| `0x4B6AA50` | 3012, int16 | Building slot, used to find keep-marker positions |
| `0x4EC82B0` | No descriptor in pinned save registry | Runtime cell lighting, SDK `LuminescenceLayer`, TileManager `+0xE69500` |

Height3005's ordinary-ground threshold is different from our current preview's
gradient over base-height3045. The native radar producer does not read3045.
The lack of a saved lighting descriptor is a concrete obstacle to claiming an
arbitrary map can already be reproduced exactly from saved bytes alone.

Unit colour handling precedes terrain handling. It reads runtime1168-byte unit
records, owner/type/special fields, the owner remap at `0x2C3CE0`, and owner colour
table `0x312880`. Some types are forced to the neutral colour `0xFFF0DCC8`, some
use one of four owner variants selected by context `+0x40`, and some special
visibility/state cases fall back to terrain. These are actual unit-record rules,
not simply the tile's building owner. Their runtime-to-file translation requires
the separately established unit record offset adjustment.

Buildings contribute flat colours via their flags in3003. When sampled building
type is40..44, the producer records the first encountered cell per owner as a
separate keep-marker pair `(destinationX, destinationY+1)`. It does **not** draw
the little keep artwork into the palette/index image. The separate marker array
is the one serialized into U4 and returned by `DLL_GetSaveRadar`.

## Native colour precedence

The full raw32-bit table values and RGB triples are extracted reproducibly in
`output/preview-native-2026-10-23/tables-and-projection.json`.
The conditions below describe code order, not independent layers to blend.

First choose terrain colour, except cells with logic `&0x30`, whose base is zero:

| Priority | Condition | Table RVA | Noise selector |
|---:|---|---:|---:|
| 1 | Logic `&1` (sea) | `0x3126B8` | `&7` |
| 2 | Logic `&0x200000` (ford) | `0x3126E8` | `&7` |
| 3 | Logic `&0x100000` (river) | `0x3126D8` | `&3` |
| 4 | Logic `&0x20000` (stone) | `0x312718` | `&7` |
| 5 | Logic `&0x80` | `0x312738` | `&3` |
| 6 | Logic `&0x40000` | `0x312748` | `&3` |
| 7 | Surface `&0x40` | `0x3127E8` | `&3` |
| 8 | Surface `&0x20` | `0x312768` | `&3` |
| 9 | Surface `&0x10` and logic `&0x8000` | `0x312818` | `&3` |
| 10 | Surface `&0x80` and logic `&0x8000` | `0x312808` | `&3` |
| 11 | Surface `&1` and logic `&0x8000` | `0x3127F8` | `&3` |
| 12 | Logic `&0x80000` (iron) | `0x312778` | `&3` |
| 13 | Logic `&0xA0000000` (swamp/pitch) | `0x312788` | `&3` |
| 14 | Surface `&2` or logic `&8` | `0x3127B8` | `&7` |
| 15 | Height3005 `>16` | `0x3127E8` | `&3` |
| 16 | Ordinary ground | `0x312798` | `&7` |

Then override that result in this order:

1. Logic `&0x40000000`: table `0x312708`, noise `&3`.
2. Otherwise logic `&0x3000`: tree/proximity table `0x3127D8`, noise `&3`.
3. Otherwise logic `&8`: if misc-display3007 `&0x2000`, fixed `0xFF243024`.
4. Otherwise the first matching mask in the following ordered table overrides.
   A zero mask terminates the search and retains the existing terrain colour.

| Mask | Colour |
|---:|---:|
| `0x400` | `0xFF544A46` |
| `0x2` | `0xFF544A46` |
| `0x10000000` | `0xFFA07850` |
| `0x300` | `0xFFC8C8C8` |
| `0x400000` | `0xFFC8C8C8` |
| `0x800` | `0xFFA0A0A0` |
| `0x0F000000` | `0xFF5A4129` |
| `0` | Terminator; stored following colour `0xFF003200` is not used by this search |

Finally apply cell lighting to terrain-path pixels. If lighting byte is2,
leave the colour unchanged. Otherwise fetch multiplier from32-bit table
`0x312690` at index `(lightingByte & 0xFE)`. The eight contiguous values are
`120,110,100,90,80,70,60,50`. The byte mask is an exact native operation; it
is not evidence that all eight entries are reachable here. Each masked colour
channel is multiplied/divided by100, capped at its channel maximum, masked
again, and recombined with alphaFF. Unit-colour paths bypass this terrain
lighting block. Do not replace this calculation with a height gradient.

Examples of native ordinary-ground RGB values before lighting, noise0..7:
`(196,160,113)`, `(163,128,89)`, `(204,168,130)`, `(212,185,155)`,
`(204,168,130)`, `(196,160,113)`, `(163,136,89)`, `(204,176,122)`.
The speckling is a direct consequence of3008 choosing these discrete entries.

## Raster/projection parameters

The producer does not call a general image resizer. It scans800 source rows,
only drawing rows divisible by the selected step. A runtime lookup at
`0x3B4ACE4` maps scan positions to packed tile IDs. Its cursor starts at810
plus rotation offset, then increments alternately400/401 per source row.
The number of columns examined alternates `W`/`W+1`, where runtime W is read
from `0x3A11E68`. This table construction and W's ordinary initialized value
were not reconstructed in this task; the cursor increments are established
independently of that value.

Rotation state at `0x60AD40C` selects these lookup-index offsets:
0/default→8, 6→`0x4E528`, 4→`0x9CA48`, 2→`0xEAF68`, followed by the common
`+0x322`. Adjacent rotations are separated by320800 lookup entries.

For sampled source row `r` and column `c`, compute signed integers:

```text
q = c - trunc(margin / 2) + xdelta
t = floor(r / step) - margin + ydelta
accept only 0 <= q < xlimit and 0 <= t < ylimit
x = trunc(2*q / step) + xoffset
y = t + yoffset
write scratch[y*200 + x] = colour
if step == 1: also write scratch[y*200 + x + 1] = colour
```

| Size | step | margin | xdelta | ydelta | xoffset | yoffset | xlimit | ylimit |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 160 | 1 | 320 | 0 | 0 | 20 | 20 | 80 | 160 |
| 200 | 1 | 300 | 0 | 0 | 0 | 0 | 100 | 200 |
| 300 | 2 | 125 | -50 | 0 | 12 | 25 | 170 | 150 |
| 400 | 2 | 200 | 0 | 100 | 0 | 0 | 200 | 200 |
| 500 | 3 | 33 | -32 | 0 | 0 | 0 | 300 | 200 |
| 600 | 3 | 100 | 0 | 66 | 0 | 0 | 300 | 200 |
| 700 | 4 | 0 | 2 | 0 | 0 | 0 | 400 | 200 |
| 800 | 4 | 0 | 0 | 0 | 0 | 0 | 400 | 200 |

The scratch image starts black. Later source columns can overwrite earlier
columns after integer division, so traversal order matters. The table above is
the native branch data, not a validated replacement for the lookup itself.

## Palette and texture expansion

After rasterization, traverse the40,000 RGB32 pixels in row-major order.
For each pixel `p`, native RGB555 conversion is:

```text
v = ((p >> 9) & 0x7C00) | ((p >> 6) & 0x03E0) | ((p >> 3) & 0x001F)
```

Linear-search the already used palette entries. If absent and fewer than256
entries exist, append `v` and use its index. If the palette is full, an unseen
colour becomes index0. This is not MEDIANCUT, nearest-colour matching, or
dithering. Quantization is the fixed RGB888→RGB555 bit reduction.

The producer's256-entry local palette is not cleared before use. It initializes
used entries, then copies all512 bytes from that stack array to output.
Consequently unused palette-tail bytes are not a deterministic visual target;
visible decoded pixels, used palette entries and the index plane are meaningful
validation targets. This is established by assembly `0xF58C0..0xF59A3`.

`0xF6FB0` expands each5-bit component by left-shifting3, yielding0..248, and
sets alpha255. It writes indexed source row0 into texture row199, then walks
the destination rows backwards. This accounts for Unity's texture orientation;
inspection PNGs decoding the stored row-major raster should use a consistent
orientation when comparing.

## Reproduction and remaining limits

Canonical exports are `output/preview-native-2026-10-23/native/*.c` and adjacent
`*.asm`. The first exploratory `pass1` and `pass2` exports are retained, but the
canonical set explicitly joins compiler-unwind chunks and has complete assembly.

`research/preview_native_functions.txt` lists the ranges for the existing
`MapFormatExport.java`. Run Ghidra with the existing StaticDamage project,
`-process CrusaderDE.snapshot.dll -readOnly -noanalysis -scriptPath research
-postScript MapFormatExport.java <output>/native research/preview_native_functions.txt`.
Use JDK21; workspace-local APPDATA was `output/ghidra-user`.

`python -m research.preview_native_extract` uses local pefile/capstone to read
the pinned DLL snapshot and regenerate `tables-and-projection.json` and
`targeted-xrefs.json`. It checks the SHA256 and never executes the DLL.

Confirmed: producer chain, saved byte format, exact colour tables and flag
precedence, all eight size branches, unit/building treatment, dynamic shade
input, palette algorithm, and texture expansion. Not completed: offline lookup
construction, lighting regeneration, all runtime context initialization and
unit visibility/owner remapping from saved state, and a pixel-exact replay
against native reference images. No offline-match claim is made.

An implementation can port these rules, but a table extraction alone does not
make it ready to replace the application renderer. The same-map visual
comparison in `MAP_PREVIEW_RESEARCH_2026-10-23.md` measures the current schematic
output's difference, not the accuracy of a native port.
