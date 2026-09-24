# Height-map native resave: preview and non-texture differences

Compared live `etest_height_00.map` and `etest_height_00_resave.map` read-only.
Immutable snapshots, SHA256 hashes, decoded previews and complete section diff:
`output/height-resave-2026-09-20/`. Reproduce with `research/analyze_height_resave.py`.
This is a comparison of one edit/resave session, not proof that every changed
field is necessary for every export. No source map or generated gameplay map
was written by this audit.

## Why the menu image was empty

The original decoded preview is BYTE-IDENTICAL to bundled empty-400.map's preview.
The current writer preserves that bitmap even after changing terrain/buildings.
The native editor replaced it with a view of the four castles and height edges.

| Data | Export | Native resave |
|---|---|---|
| U2 player count | 4 | 4, unchanged |
| U4 P1 marker | (21,110) | unchanged |
| U4 P2 marker | (80,164) | unchanged |
| U4 P3 marker | (100,19) | unchanged |
| U4 P4 marker | (144,103) | unchanged |
| U4 map size | 400 | unchanged |
| U3 embedded filename | ref_00_base_400.map | etest_height_00_resave.map |
| Decoded preview | 40512 bytes | same length, new content |

Thus the missing castles in the thumbnail are NOT missing castle markers in this
sample. U1/U2/U4 payloads are identical. Only U3 changed among those four headers.
Preview:256 RGB555 colors (512 bytes), then200x200 palette indices (40000 bytes).
181 palette bytes and39936 indices changed. Description and preview-extra bytes
are unchanged. Numbered sections are not where this menu image is stored.

The required preview-writing operation is established: render a current-map image,
quantize to the palette/index format, compress with the existing DCL block encoder,
write decoded length/compressed length/CRC and update the outer preview length.
Preserve preview-extra/description bytes and allow following blocks to move.
The script verifies IN MEMORY that replacing just the preview with the native
resave's preview leaves all numbered sections byte-identical and preserves menu
markers. This verifies the container operation, not a new general renderer.

A renderer still needs implementation: copying an empty preview is wrong, and
copying this specific resave's bitmap onto another map would also be wrong.
The exact native scene/sprite renderer has not been recovered. A schematic
terrain/building renderer can produce structurally valid, current thumbnails,
but it must not be represented as identical to the game's native preview.
The embedded U3 filename also needs updating on Save As, with its string length
and block length adjusted. Its prefix/unknown suffix must be preserved.

## Changes other than the preview or surface textures

**Important invariant:**3005 current height,3045 base height,3037 surface material
and3008 noise are ALL byte-identical. The resave did not clamp0 back to8 or130
to another value. This does not establish that arbitrary0-height land is safe.

| Section | Change | Interpretation / limit |
|---|---|---|
| 3003 | 28330 cells | Logic flags rebuilt; not merely a surface texture |
| 3006 | 911 cells:463 become8,448 become122 | Height-edge-related auxiliary data;122 equals130-8 here, not a universal formula |
| 3007 | 2959 cells | Tile display/auxiliary flags |
| 3009 | 100 cells | Additional tile data; exact purpose unresolved |
| 3030 | 2020 cells | Candidate neighboring-cell transition masks; not fully decoded |
| 3021 | 11400 cells | Connected-region labels rebuilt for the two raised areas |
| 3036 | 13296 changed bytes | Unidentified derived layer; not established as purely graphical |
| 3934 | 9504 changed bytes | Unknown; also changes during unrelated resaves |

For height130 cells specifically,3021 changes region1 into two regions of5329
cells each (73x73), plus742 cells labeled0. This shows a concrete missing
connected-region rebuild in the exported height edit. It cannot be dismissed as
a cosmetic cliff texture. We can omit a cliff-painting GUI, but correct terrain
editing still needs the appropriate backend edge/connectivity regeneration.
Do not blindly copy labels2/3 into other maps: connectivity depends on geometry.

## Entity/player changes

- Both files have36 buildings,4 active lords and no vegetation. All building
  identity/owner/origin/footprint/occupancy summaries are identical.
- Four lords moved by(+1,+1); all retain150000HP before and after.3010 updates
  eight cells accordingly. This is consistent with editor-session simulation;
  it is not evidence of missing or repaired lords.
- Building records differ in200 bytes at timer/access/other fields; record-local
  uint16 offsets14,18,c0,fe,27c,2bc,2c4. Keep group identities remain stable.
- Global-ID counter1035, lord lookups1190/1191, building grid3012 and vegetation
  table1014/grid3004 are unchanged.
- For P1..P4,2022 offsets2088/2148/22dc become3;2b64 becomes904/904/1061/1000.
  These fields remain unnamed in the inspected Script Extender. Do not claim
  these are alive flags or required preview fields.
- Section1171 changes four uint32s at1000/2000/3000/4000 from0 to1. This matches
  the four unit-slot numbers at stride1000, but is only a correlation. The field
  purpose is not established; do not initialize arbitrary records from it.
- Other changed sections:1017,1091,1023,1024,1018,1019,1046,1040,1052,1053,
  1055,1079,1096,1126. Many contain history/timer/unknown state; complete bytes
  and counts are in comparison.json. No universal initialization rule follows.

## Scope of this application update

Implemented separate low-height warning below8, independent persistent dismissal
and Settings toggle. Values0..255 remain allowed; below8 and above130 render red.
This build does not claim to repair preview generation or terrain connectivity.
The comparison establishes their separate backend requirements; a valid thumbnail
alone does not make the height-edited map's navigation correct.
