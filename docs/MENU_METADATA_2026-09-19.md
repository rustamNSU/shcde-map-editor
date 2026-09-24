# Menu metadata: three-castle map and editor resave

Compared `etest_oasis_grid_3_castles_400.map` with the user's `_r.map` resave.
The user confirmed the generated map works in game. The generator updated game
objects but retained the two-player source's menu headers and preview.
No game map was changed during this comparison.

## Header fields

These blocks precede the numbered section directory. U2/U4 are parser labels.
Offsets below are relative to the payload, excluding its uint32 length prefix.
Integers are little endian.

| Block and offset | Meaning | Generated | Editor resave |
|---|---|---|---|
| U2 +0x18, uint32 | Menu player count | 2 | 3 |
| U4 +0x10, uint32 x/y | P1 menu marker | (33,169) | (98,98) |
| U4 +0x18, uint32 x/y | P2 menu marker | (176,22) | (156,18) |
| U4 +0x20, uint32 x/y | P3 menu marker | absent | (176,38) |
| U4 +0x50, uint32 | Map size | 400 | 400 |

U4 has eight marker pairs, starting at +0x10 with stride 8. An absent pair has
both coordinates 0xFFFFFFFF. P4–P8 remain absent. These are menu/minimap
coordinates, separate from gameplay tile coordinates. This establishes the
stored markers, not the complete algorithm assigning AI and teams at startup.
The U2 count interpretation is also supported by vendor/sourcehold-maps/sourcehold/maps/U2.py.

U3's embedded name changed from `ref_00_base_400_castles.map` to
`etest_oasis_grid_3_castles_400_r.map`.

For DE size-400 maps with KeepTwo origin (x,y), the empirical projection is:

```python
marker_x = (x - y + 197) // 2
marker_y = (x + y - 598) // 2
```

Verified on 23 keeps across six maps, including independent reference/example
maps. Do not apply this formula unchanged to size 500 or other keep types.

## Preview

The decoded preview is 40512 bytes: a 512-byte palette of 256 RGB555 uint16
entries, followed by 200×200 uint8 pixel indices. The resave changed 102 palette
bytes and 30131 pixel indices. It now depicts the grid and three castles.
The preview raster is separate from player markers. Exact reproduction of the
game's preview renderer is not implemented.

Exports: `output/three-castle-resave/before_preview.png` and `after_preview.png`.

## Numbered sections

3037 surface, 3008 noise, 3005 current height and 3045 base height are byte
identical. The resave did not change these terrain/material fields.
1035 global-ID counter, 1190 lord-slot lookup and 1191 lord-ID lookup also match.
All 27 building records retain their core identity, owner, placement, footprint
and references. The three lords moved slightly; keep access coordinates and
some timers changed during the editor session.

Other changes include 28749 cells in 3036 and smaller changes in logic/auxiliary
grids. These do not prove that 3036 is a graphics cache. See diff.json for all
changed sections. Unknown player fields in 2022 changed too; their meaning is
not established. Section 1051 went from 2 to 1 while the menu count became 3:
1051 must not be interpreted as the player count.

## Implementation and evidence

`MapFile.menu_metadata()` now reads player count, eight markers and map size;
manifest output includes these fields. `research/check_menu_resave.py` verifies the
comparison and independent marker projection checks. Evidence, hashes and the
full diff are in `output/three-castle-resave/`.

Future generators must update the menu count, markers, embedded filename and
preview alongside the actual objects. The existing generator is not yet a
complete menu/preview writer.
