# Castle orientation in the renamed save reference

Source: `ref_from_save_castle_orientation.map` (the file matching the user's
ref_castle_orientation description). SHA256
`8c7b66247b771de21099749e8bc0a2fcd4f31810781efeb8a5d5c93f4c956f78`.
Read only; snapshot and relative-layout JSON under
`output/castle-orientation-2026-09-21/`. Reproduce: `research/analyze_castle_orientation.py`.
Size400,122 active building records. This is a populated save, not a clean prefab.

## Confirmed: same building IDs, different group geometry

Coordinates below use horizontal x/right and vertical y/down in the GUI cell
grid. Offsets are relative to the upper-left corner of the7x7 keep.

| Owner | Keep origin | Keep ID | Doorway center ID73 | Campfire ID55 | Entrance side |
|---|---|---:|---|---|---|
| P1 |332,486|41|+3,+7|0,+8|Below|
| P2 |455,363|41|+3,-1|0,-8|Above|
| P3 |327,317|41|-1,+3|-8,0|Left|

The7x7 campfire sits beyond the one-cell doorway strip. All three doorway IDs
are reused rather than replaced with new orientation IDs:

| Owner | ID71 | ID73 | ID72 |
|---|---|---|---|
| P1 |+2,+7|+3,+7|+4,+7|
| P2 |+4,-1|+3,-1|+2,-1|
| P3 |-1,+2|-1,+3|-1,+4|

P1 keep/door/camp records slots1..5 share group-root8050; P2 slots10..14
share8060; P3 slots19..23 share8070, matching their respective keep global IDs.
Each has four nearby stockpile records ID10, with separate stockpile group roots:

| Owner | Stockpile anchors relative to keep |
|---|---|
| P1 |(+7,+2),(+10,+2),(+7,+5),(+10,+5)|
| P2 |(-5,0),(-2,0),(-5,+3),(-2,+3)|
| P3 |(0,+7),(+3,+7),(0,+10),(+3,+10)|

Do not assume a rotation of the entire current bounding rectangle reproduces
these stockpile positions. Right-facing entrance is not present in this sample.

## Entry-point caveat

The primary keep's access coordinate pair at file4013 record+0xfe remains
keep+(3,7) in ALL THREE examples, despite the doorway being above/left. Its
other coordinate pair+0x260 remains keep+(3,2). Thus the generic building access
pair alone does not identify this group's actual passage. Doorway records have
their own access positions; cell heights, logic, graphic variants and navigation
must be studied together. Script Extender names the access pair, but does not
provide a verified standalone castle rotation field. Differences in small words
may be production/simulation state; do not call them orientation flags without
independent evidence. Keep type41 is verified identical.

## Implications for the editor

Represent orientation as a complete layout: keep, three doorway records, camp,
stockpile arrangement, linked coordinates, occupancy and dependent grids. Current
placement only has the downward template. Current render.castle_parts assumes
downward offsets and would misidentify rotated castle footprints/area centers;
the wall-area center should use the actual associated ID73 location. Group
removal and selection also need to recognize each complete layout.
Do not transplant populated player/unit/economy records from this save into
new-map prefabs. No new orientation controls or placement changes were added by
this research task; this establishes three layouts, not safe arbitrary rotation.

## Container observation

This save has a591-byte length-prefixed block between U4 and ud, rather than97
bytes seen in earlier saves. The source reader now recognizes precisely97/591,
validates the following directory, and preserves all bytes. Exact parse/rebuild
roundtrip succeeds. Extension contents remain opaque. Portable EXE not rebuilt
as part of this research-only request.
