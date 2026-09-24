# What we know, what remains, and how to start the editor

Consolidated 2026-09-19 from the local code, reference analyses and later game
experiments. This is the current decision guide; the linked reports retain exact
sample counts, hashes and full diffs. It does not claim a complete format specification.

Later evidence: [Leto save investigation](SAVEGAME_LETO_2026-09-19.md). The renamed
map is identical to its original .msv. The reader now preserves the observed extra
97-byte save-prefix block. Populated saves corroborate worker links and stored
resources; gold and movement interpretations have specific remaining checks.
They support richer inspection, not unrestricted simulation-state editing.

The [editor-resave follow-up](LETO_EDITOR_RESAVE_2026-09-19.md) retains resources
and worker assignments while movement and economy evolve. It clears 220 zero-HP
records: the existing `active_count` must not be presented as a living-unit count.
The opaque 97-byte prefix persists even after a map-editor resave.

## Decision

We can start the application now. Complete reverse engineering is not a prerequisite
for a viewer or an editor that starts from a known-good map and preserves opaque data.
The first app should open existing DE maps, display schematic terrain and objects,
inspect cells, support undo/redo for narrowly defined edits, and save a new file.
New maps should initially mean copies of validated templates with fixed size and
player setup. General creation from zero bytes is a later capability.

Unknown values can be inherited from a template. A value that was harmless before
an edit is not necessarily valid after it: connectivity, object references and
allocation state are the main examples. Defaults therefore belong to an operation
and a tested template profile, not just to a field.

## Evidence levels

| Label | Meaning |
|---|---|
| Confirmed on samples | File comparisons or invariants establish the stated field in the named samples |
| Game-observed | The user tested the generated map; the observation has the scope described in its report |
| Interpretation | Consistent with file data and external runtime research, but not completely traced |
| Unknown | Retain bytes; do not assign a meaning or a universal default |

Section IDs below are decimal. Hex offsets are relative to a record or header
payload, not absolute file offsets. Integers are little-endian. Most detailed
reference work covers DE directory version 236; do not generalize to every version.

## 1. Container, compression and compatibility

Implemented in [`maptool.py`](../maptool.py): magic, compressed preview, description,
length-prefixed U1-U4 blocks, directory, numbered sections and trailing bytes.
The directory has five arrays: decoded sizes, stored sizes, IDs, compression flags
and relative offsets. Capacity is `(directory_size - 36) / 20`; the main DE batch
has capacity 200 and 175 populated sections. A compressed block contains decoded
size, compressed size and CRC32 followed by PKWARE DCL data.

Unmodified rebuilds preserve the original bytes, including unknown sections and
trailing data. Replacing a decoded section recompresses that section if needed and
updates sizes/offsets. Current replacements must retain decoded length; adding or
removing directory entries and editing prefix blocks are not supported writer APIs.
`menu_metadata()` reads known header fields but does not write them.

Five example maps pass byte-identical rebuild tests, including a legacy example;
semantic decoding is DE-specific. The 29 archived DE references were reported to
decode and rebuild identically. The original Einstein 3v3 has an exceptional 1190
block that cannot be decoded normally; it is preserved opaque and cannot be patched.
That exception does not apply to every map's 1190. The parser currently requires
contiguous section storage and compression flags 0/1, so unsupported layouts must
be reported rather than silently normalized.

The observed save variant also roundtrips across seven Leto .msv files. Its opaque
prefix extension is retained; no filename-extension change is needed for parsing.

Sources: [`README`](../README.md), [`reference analysis`](REFERENCE_ANALYSIS_2026-09-19.md),
[`tests`](../tests/test_maptool.py), [`semantic tests`](../tests/test_semantics.py).

## 2. Coordinates and playable area

DE sample grids contain 320,800 cells packed into an 800-row diamond. Row lengths
are `2, 4, ..., 800, 800, ..., 4, 2`. `tile_index` and `tile_xy` in
[`semantics.py`](../semantics.py) implement the conversion; all indices are checked
for roundtrip identity in the existing test suite.

Logical map size is section 1050, uint32. The interior mask excluding
RealityEdge/MapBorder matches a centered diamond with side `S - 4` and
`(S - 4) * (S - 2) / 2` cells across the 29 references of size 160/200/400/500.
This does not recover all border layers or make map resizing a supported operation.
World coordinates for the tested starting buildings equal tile coordinates times 8.

## 3. Terrain and cell layers

| Section | Element | Established use and limitation |
|---|---|---|
| 3003 | uint32 | Terrain/object logic flags; full valid combinations and update rules incomplete |
| 3037 | uint8 | Surface and elevation-level flags; not a final texture ID |
| 3005 | uint8 | Current/top height |
| 3045 | uint8 | Base height; can differ from current height |
| 3008 | uint16 | Persistent per-cell variation affecting rendering; exact native mapping unresolved |
| 3004 | uint16 | Vegetation slot references into 1014 |
| 3012 | uint16 | Building slot references into 4013 |
| 3010 | uint16 | Unit slot references into 3015 |
| 3049 | uint8 | Building type on occupied cells, not record slot |
| 3043 | uint8 | Wall ownership: tested 0=P1, 5=P6; zero on nonwalls is not ownership |
| 3021 | uint16 | Saved connectivity/region labels in tested terrain; exact reconstruction unknown |
| 3030 | uint8 | Changes around connectivity boundaries; complete mask semantics unknown |
| 3006 | uint8 | Height/display-related observations; neither a general current-minus-base formula nor a complete shadow map |
| 3007 | uint16 | Display-related candidate; flat ground 16, resource samples 2064; update rules incomplete |
| 3009, 3036 | uint16 | Auxiliary state; 3036 has structured patterns but no proven graphics-cache meaning |

The [full inventory](SECTION_STATUS_2026-09-19.md) lists all 175 section IDs,
including unknown sections. Constant values across samples do not prove irrelevance.

Observed surface values: earth 0, scrub 1, earth-and-stones decoration 2,
mid-plateau marker 4, high-plateau marker 8, oasis 16, beach 32, sand 64,
thick scrub 128. Arbitrary combinations are not validated.

Observed logic values: land `0x8000`, rocks `0x8080`, stone resource `0x28000`,
iron `0x88000`, sea `0x1`, river `0x100000`, ford `0x200000`, marsh `0x20008000`,
pitch-on-marsh `0xA0008000`. Decorative stones and mineable stone are different.
These values are decoding facts, not complete brush recipes.

Ordinary ground height is 8 in the reference templates; plateau samples use 80
and 130. River current and base heights can differ because of editing history.
The height fields can store 0..255, but this is not a validated safe gameplay range.

## 4. Graphics, heights, walls and movement

- Noise 3008 survives resaves and material painting unchanged in tested pairs.
  Constant-noise tests caused repetitive graphics. Zero is not a proven neutral
  or disabled-noise setting; preserve template variation initially.
- Final appearance depends on more than 3037. A smooth height-only map later
  repainted/resaved gained plateau flags at heights 80/130. An abrupt plateau
  opened/resaved without brushing retained surface 0. No universal height-to-surface
  conversion has been recovered.
- A no-brush abrupt-plateau resave changed 3003/3006/3007/3021/3030/3036 without
  changing either height or noise. Its top became a separate region, with an
  impassable perimeter. Exact load/update/save responsibilities remain unisolated.
- Direct game loading and opening in the built-in editor can behave differently.
  Do not assume a direct game load repairs every stale layer.
- The user climbed strips with step delta 16 and could not enter strips above 16
  in the tested setup. This is not yet universal across units, directions or states.
  Black cells from strip 19 do not establish an absolute elevation limit.
- Plain wall segments and stairs in the samples are grid data, not building
  records. High wall logic is `0x100`, low wall `0x10100`, stair `0x900`.
  On flat base 8, wall tops are 98/68; stair sequences descend in steps of 16.
  Elevated high-wall tops of 170/220 were also recorded.
- 3006 equals top-minus-base on the flat wall sample, but fails that formula on
  elevated walls and natural slopes. Neighbor-drop formulas tested so far also fail.
  Suspected high-wall uint8 wraparound remains unproven numerically.
- Region labels support connectivity analysis but do not establish buildability
  or prove live pathfinding. No complete persisted shadow map has been identified.
- Marsh lettering uses the same logic/surface/height tuple as broad marsh;
  edge/interior differences likely affect graphics, but the sprite rule is unknown.

Evidence: [textures](TEXTURE_ANALYSIS_2026-09-19.md),
[marsh/shadows](MARSH_SHADOWS_2026-09-19.md), [walls](WALLS_2026-09-19.md),
[hills/stairs](HILLS_STAIRS_2026-09-19.md), [height probes](HEIGHT_TESTS_2026-09-19.md),
[movement observations](HEIGHT_STEPS_GAME_RESULTS_2026-09-19.md),
[earth repaint](SMOOTH_EARTH_COMPARISON_2026-09-19.md),
[no-brush control](DISC_RESAVE_2026-09-19.md).

## 5. Entities and players

The following are verified file layouts, not copied runtime offsets. State/type
and listed tile/world coordinate components are uint16; global IDs and packed tile
IDs are uint32. Complete record schemas and allocation lifecycles remain unknown.

| Array | Stride / slots | State / type | Global ID | Tile X / Y | Packed tile ID |
|---|---|---|---|---|---|
| Vegetation 1014 | 156 / 4000 | 0x44 / 0x46 | 0x4C | 0x62 / 0x64 | 0x68 |
| Buildings 4013 | 812 / 4000 | 0xD0 / 0xD2 | 0xD8 | 0xEE / 0xF0 | 0xF4 |
| Units 3015 | 1168 / 10000 | 0x8C / 0x8E | 0x98 | 0xC4 / 0xC6 | 0xD4 |

Buildings: owner uint16 at 0xD6; world X/Y at 0xE8/0xEA; square footprint side
uint32 at 0xF8; access coordinates at 0xFE/0x100. Vegetation world X/Y is
0x5C/0x5E. Unit owner is at 0x80 and controller byte at 0x96; type 55 is the
tested lord. Unit slot zero contains a reserved/scratch-like copy, not another
placed lord. Cell references are slot indices, not global IDs.

Desert vegetation IDs tested: 1 olive, 2 palm, 3 coconut palm. Runtime enum names
do not match these landscape-specific visuals. Nearby TreeProximity masks vary
in the examples; growth/resource fields and general placement rules remain open.
Type 104 holes are building-table objects with 6x6 or 9x9 footprints, not height cuts.

The tested starting complex has nine building records and one lord:

| Type | Relative position to keep | Footprint |
|---|---|---|
| 41 KeepTwo | (0,0) | 7x7 |
| 71 / 73 / 72 doors | (2,7) / (3,7) / (4,7) | 1x1 each |
| 55 Campground | (0,8) | 7x7 |
| 10 stockpile parts | (7,2), (10,2), (7,5), (10,5) | 2x2 each |

Total footprint references: 117. No universal group field is established.
Moving a complex requires embedded coordinates and tile IDs, grids, unit state
and player links, not merely the keep's primary position.

Populated-save follow-up adds 1,443 reciprocal worker references across seven
samples. It also shows that 3010 references only a subset of active unit slots;
read the full unit table. Full offsets and exceptions are in the save report.

Players 2022 has nine records of stride 0x583C. Tested uint32 links:
0x94 keep slot, 0xBC first stockpile slot, 0x1D4 Campground slot. Associated
coordinate/tile-ID fields are corroborated; runtime names can be misleading.
1190 holds tested lord-slot lookups (uint16), 1191 lord-global-ID lookups (uint32).
1035 acts as the next global-ID counter in the cloning experiment. 1047 is used
as a source-specific building allocation/high-water assumption, not a recovered
general allocator. 1051 is not the menu player count.

Stored goods at player +0x4D0 (stride 4) now cross-check against storage-building
inventories for 23 non-null/non-gold entries across seven saves. Gold at +0x50C is
a strongly supported candidate, awaiting direct UI or controlled-change validation.
This does not establish which fields new-match initialization overrides.

The three-castle generator relocated and cloned complete complexes, with 27 building
records and three lords. The user confirmed the map works. It depends on the
specific source's available slots and allocation history; its inferred-field
scans must not become a universal relocation algorithm without further evidence.

Sources: [reference layouts](REFERENCE_ANALYSIS_2026-09-19.md),
[three-castle experiment](THREE_CASTLE_GRID_2026-09-19.md),
[`research/make_three_castle_grid.py`](../research/make_three_castle_grid.py).

## 6. Menu, preview and description

U2 payload +0x18 is menu player count (uint32). U4 +0x10 holds eight uint32 X/Y
marker pairs with stride 8; both 0xFFFFFFFF means absent. U4 +0x50 is map size.
U3 contains an embedded filename. These offsets exclude block length prefixes.

For the tested size-400 KeepTwo maps, marker projection
`((x-y+197)//2, (x+y-598)//2)` matched 23 keeps across six maps. Other sizes and
keep variants need validation. Markers are distinct from the preview raster.

Preview decoding is known: 512 bytes of RGB555 palette plus 200x200 uint8 indices.
An approximate schematic preview is a possible future writer feature; reproducing
the native renderer is not required to design the app. Neither preview writer nor
header-update API is currently implemented. Validate any new encoder in the game.

The three-player generated map kept two-player menu data and an old preview until
the user resaved it. Count/markers/filename/preview must be handled explicitly when
layout changes. Full lobby AI/team setup is still unknown.

DE description text in the tested pair lives after the compressed preview stream,
followed by a uint32 byte count; the old description block stayed unchanged.
ASCII is confirmed; Unicode encoding and a general text writer are not.

Source: [menu metadata](MENU_METADATA_2026-09-19.md) and reference analysis.

## 7. Default policy for the first app

These are proposed implementation rules, not claims of newly tested behavior.

| Data / operation | Initial policy | Why / restriction |
|---|---|---|
| Unknown sections and record bytes | Preserve source bytes | No arbitrary zero-fill or invented meaning |
| New document | Clone an archived known-good template | Retain version, size, borders and player setup together |
| Noise 3008 | Retain complete template grid | Constant noise visibly changes rendering |
| Unknown game settings, AI, events, resources | Keep the template preset | Do not present them as configurable yet |
| Untouched objects | Retain records and links | Unknown fields may carry live references |
| Flat-earth template | Retain its complete coherent layers | Land=0x8000, surface=0, heights=8 alone are insufficient to manufacture a map |
| Oasis/surface-only brush | First experimental edit on unoccupied flat land in a supported profile | Existing grid experiment is useful evidence, not proof of every surface brush |
| Height, water, cliffs, walls | Inspect first; experimental writing only with explicit operation scope | Existing derived layers can become stale |
| Connectivity / borders | Preserve while geometry is unchanged | Cannot use one default region for arbitrary geometry |
| Add/delete/move arbitrary objects | Defer until complete operation rules exist | Empty-looking slots alone do not establish allocator validity |
| Castle placement | Existing source-specific experiment, then a validated template operation | Retain full complex, lord, lookup tables and player links |
| Menu and preview | Preserve for unchanged maps; update before claiming a finished layout-changing export | Stale menu state already occurred in the tested generator |
| Map resizing / format conversion | Initially unsupported | Border generation and cross-version layouts are incomplete |

A template profile should record its source hash, version, size, biome/setup,
section lengths, permitted operations, static checks and game-test results.
Template import must not silently convert an unknown map into a supported profile.

## 8. What still needs understanding, by feature

| Priority | Question | Smallest useful next evidence | Blocks |
|---|---|---|---|
| P0 implementation | Header and preview writing | Implement from known layout; roundtrip and verify an exported copy in game | Finished export after layout/player changes |
| P0 research | Which layers a simple surface brush must change | Same baseline, no-brush resave control, one small oasis/earth edit; compare direct-load and editor-resave behavior | Promoting first brush from experiment to supported operation |
| P1 research | Slope edges, 3006/3007, region 3021 and masks 3030 | Existing plateau controls first; isolate height, gradient and brush effects; test movement/buildability | Reliable height/water/wall brushes |
| P1 research | Allocation/freeing and all object references | One object, two objects, delete one, add again; compare slots, IDs, counters and grids | General object placement/deletion |
| P1 research | Ownership and player state | Same unit in same position for P1/P8; separate player/AI/team changes | Owner editing and arbitrary player presets |
| P1 research | Group transforms | Expand/delete stockpile; other keep types; rotation-specific samples | Copy/paste, rotation, symmetry with objects |
| P2 research | Exact graphics, atlas choice and shadows | Trace existing native/runtime source and compare controlled visual samples | Faithful renderer; not schematic editing |
| P2 research | Remaining settings and events | One setting/event change per pair, with control resaves | Mission/settings UI; can inherit preset now |
| P2 research | Unicode and other versions/sizes | Non-ASCII text pair; targeted version and marker-projection checks | Those specific export features |

Before asking for maps, check live Maps and archived outputs: a base400 and
two-castle base400 already exist, as do the abrupt no-brush resave and later
references. Older reports asking for base400 are historical. The matching
no-brush control for the generated smooth plateau is still described as missing.
Do not request the entire original reference batch again.

## 9. Application sequence and acceptance criteria

1. **Viewer and inspector.** Reuse `MapFile` and `semantics.py` behind a document
   model. Open map, pan/zoom schematic layers, select tile/entity, show coordinates,
   flags/heights, player markers and preview. Unsupported semantic layouts can
   remain container-only. Keep the original bytes immutable. Acceptance: fixture
   coordinates and entities match the current reports; opening never writes files.
2. **Document editing foundation.** Represent each command as an explicit set of
   changes, including all affected sections; provide undo/redo and dirty state.
   Save As creates a new file with readback and changed-section checks. Acceptance:
   no-op save is byte-identical, undo restores original output, and unrelated raw
   blocks and trailing bytes survive. This can be built before new research.
3. **First limited brush.** Start with the existing oasis-on-flat-unoccupied-land
   experiment, bounded by the template profile and occupancy checks. Add header/
   preview writing for changed layouts. Acceptance: controlled fixtures and direct
   game tests cover the operation; surface decoding alone is not the acceptance test.
4. **Template-based new maps.** Offer validated size/player presets; preserve
   unknown data and noise. Acceptance: each preset loads as intended in the game,
   and menu count/markers/preview agree with gameplay. Do not require the built-in
   editor as an invisible mandatory repair step.
5. **Expand feature by feature.** Add height tools, entity lifecycle, group transforms
   and broader settings as their dependency rules become known. Each operation
   declares required sections/profile and rejects unsupported cases.

The UI should use a schematic renderer initially. Game-like sprites, exact shadows,
complete decoding of all 175 sections and arbitrary object placement are not
prerequisites for the first usable app. The UI framework is not selected here.

## 10. Existing tools and baseline verification

`maptool.py`: inspect/extract/diff/rebuild container data. `semantics.py`: DE grid
coordinates, entity interpretation and a schematic image. `research/analyze_references.py`
and `research/reference_findings.py`: reference evidence. `check_*.py`: topic-specific
checks. `make_*.py`: experiment generators with source assumptions and potential
writes to live Maps; inspect before running, do not invoke as generic app APIs.

Run the existing baseline from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest -q
```

This checks container preservation, controlled section patching, coordinate
conversion, entity/reference fixtures and descriptions. It does not test arbitrary
gameplay validity, a GUI or generic generation. Game observations remain explicitly
attributed to the user and their particular experiments.

Baseline rerun during this consolidation: all 14 tests passed in 21.621 seconds.
Only documentation was changed; no map experiments or application implementation
were performed as part of this consolidation.
