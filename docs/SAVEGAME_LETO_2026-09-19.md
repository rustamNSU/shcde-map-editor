# Renamed multiplayer save: Leto vs FBI

## Result

Follow-up: [map-editor resave comparison](LETO_EDITOR_RESAVE_2026-09-19.md).
The identity and numbers below describe the archived original, before that resave.
The resave retained workers/resources, evolved movement/economy, and cleared 220
zero-HP unit records. Thus the original 1460 `active_count` was a record count,
not proof of 1460 living units.

The user's `Maps/leto vs fbi 10.map` is byte-identical to
`Saves/leto vs fbi 10 .msv` (the original filename has a space before `.msv`).
Both are 3,864,831 bytes, SHA-256:
`40d3cc85bcadc434028c7e10928ecd455d01f437d068fb6e35f61e382349a5d9`.
Changing the extension did not transform the data. The user reports that the
built-in editor opens it with workers, units and some movement preserved. The
agent inspected files only, without loading or modifying the game.

This is a populated simulation snapshot in a closely related map container.
It greatly expands our evidence beyond initial castles and lords. It does not
establish that every `.msv` is interchangeable with every `.map`, or that a new
game launched from the renamed file retains every saved setting/resource.

## Evidence and reproduction

`output/leto-save-2026-09-19/` contains snapshots of the renamed map, seven related
Leto saves, and the local map matching the embedded filename. All nine source
files were rehashed unchanged after analysis. All decoded successfully and
rebuild byte-identically with the updated reader.

- `manifest.json`: exact container offsets, section sizes and hashes.
- `findings.json`: counts, checks, resource values, caveats and research-source hashes.
- `units.csv`: all 1,460 decoded active unit records and selected dynamic fields.
- `worker_links.csv`: building-to-worker relationships and reciprocal checks.
- `players.csv`, `resources.csv`: player fields and storage cross-checks.
- `baseline_diff.json`: comparison with `001 3 green Fenrir.map`.
- `related_saves.json`: independent checks on seven Leto save snapshots.

Run [`research/analyze_savegame.py`](../research/analyze_savegame.py) with a **new** evidence folder:

```powershell
.\.venv\Scripts\python.exe -m research.analyze_savegame.py --output output/leto-save-next-analysis
.\.venv\Scripts\python.exe -m unittest -q
```

Validation after implementation: all 18 tests passed in 29.568 seconds, including
the existing 14 tests and four new savegame regression tests.

Runtime research sources: Script Extender commit
`78a7595067fa297798720b56664d7df955aa7150`, `GameUnit.cs`,
`GamePlayerResources.cs`, `GameBuilding.cs`; Rust Stats commit
`abae71e59417f6afcdf59fed2c450719dbd58fa1`, `instructions/player.md`,
`building.md`, `enums.md`. Exact source hashes are archived. Runtime-derived names
remain interpretations unless supported by the cross-checks described below.

## 1. New container variant

The earlier parser stopped with `Unrecognized directory size`. After the usual
U1-U4 blocks, these saves contain an additional length-prefixed block:

| Absolute file offset in the renamed map | Data |
|---:|---|
| 22644 | uint32 value 97: observed extension payload length |
| 22648 | 97 payload bytes, beginning `66 00 00 00`, remaining bytes zero |
| 22745 | Usual four-byte `ud`, zero in this sample |
| 22749 | Section directory, size 4036, capacity 200, count 175, version 236 |
| 26785 | Numbered section data, length 3,838,046 |

The same 97-byte payload occurs in all seven inspected Leto saves. Its meaning is
unknown; it is not identified as a player name, network flag or universal save tag.
`MapFile.save_extension` now preserves it and the manifest reports its location.
Detection is structural, not extension-based: the normal directory must be absent
at its expected location, the observed length must be 97, and the following directory
must pass structural checks. Other unobserved prefix variants remain unsupported.
Existing section checks still validate lengths, decompression and CRC32.

Rebuild preserves this extension exactly. No conversion or byte deletion is needed
to parse the original `.msv`. Tests cover all seven roundtrips, prefix preservation
under a compressed-section edit, and rejection of malformed extension data.

## 2. Comparison with an ordinary map

U3 embeds `001 3 green Fenrir.map`; the corresponding local map exists. Its directory
is also version 236, but has 174 sections. Comparing it with the save gives:

- 102 shared sections have identical decoded bytes.
- 72 shared sections differ; no shared section changes decoded length.
- Section 1208 is present only in the save, four zero bytes. It also exists in the
  earlier 175-section reference inventory, so it is not established as save-only.
- Noise 3008, base height 3045, vegetation 1014/3004 and several other layers match.
- Ordinary map: 20 active buildings, no active units; save: 638 buildings, 1,460 units.

The name and unchanged layers support a shared map origin. The local map is not
proven to be the exact pre-match file, and gameplay changes many things at once.
This comparison cannot assign each changed section to a single action.

The usual map sections already contain room for dynamic game state: no separate
worker-only section or larger unit record was needed. The known record sizes and
coordinate offsets continue to work on this much richer sample.

## 3. Units, buildings and occupancy

All 638 decoded building anchors and all 1,460 decoded unit positions agree with
their packed tile IDs. Building-grid references resolve to 638 active building
slots with no dangling slots; vegetation records and references are empty.

Examples of unit types, using numeric names from the Stats enum:

| Unit type | Count |
|---|---:|
| 78 Bedouin camel lancer | 684 |
| 60 Portable shield | 142 |
| 30 Engineer | 133 |
| 74 Arabian horseman | 84 |
| 3 Woodcutter | 60 |
| 18 Poleturner | 54 |
| 16 Baker | 48 |
| 28 Knight | 45 |
| 1 Peasant | 33 |
| 55 Lord | 4 |

Full type counts are in `findings.json`. Owner counts are P2=910, P3=505,
P1=18, P4=18 and owner 0=9. These are record counts, not UI army/population totals.

**3010 is not a complete enumeration of units.** It references only 502 distinct
active slots while the unit table contains 1,460. No grid reference points to a
missing active slot. Stacking, hidden units and other state may contribute; the
exact grid/list semantics are not recovered. Do not delete a unit merely because
its own current tile does not point back to its slot. Continue reading the table.

## 4. Workers: reciprocal links now corroborated

The following file offsets were checked against actual populated records:

| Section / record | Offset and type | Meaning supported by cross-links |
|---|---|---|
| 4013, building stride 812 | +0x19E, +0x1A0, +0x1A2 uint16 | First three worker slot references |
| 4013 | +0x1A4 uint32 in runtime layout | Fourth worker slot candidate; upper half zero across all seven samples |
| 3015, unit stride 1168 | +0x338 uint16 | Associated building slot for the checked worker relationships |
| 3015 | +0x368 uint32 | Associated building global ID for those relationships |

All 237 nonzero building worker references in the renamed map identify an active
unit, whose associated building slot, global ID and owner match the source building.
These workers include 60 woodcutters, 54 poleturners, 48 bakers, 18 quarry masons,
18 millers, 14 fletchers, 10 innkeepers, 9 quarry grunts and 6 wheat farmers.

Across the seven related saves, **1,443 of 1,443 nonzero building worker references**
match both reciprocal slot and global ID. This is strong file-level evidence for
these links, although unused fields and lifecycle transitions remain untested.

Do not interpret +0x338 as a universally valid production link on every unit:
1,245 active units have a nonzero value there, but only 315 also match the building
global ID at +0x368. Other types/states can retain stale or differently used data.
The 237 reciprocal building-list references are the stronger verified subset.

## 5. Player resources, including gold

Section 2022 still has nine records of stride `0x583C`, indexed by player ID
including slot zero. The stored-goods vector begins at record +0x4D0, 25 entries
with stride 4. Gold is signed int32 at +0x50C; other goods are read as uint32.

The gold location is independently suggested by both runtime sources. Stats uses
gold as its base, with keep ID at -0x478; the already verified file keep link is
+0x94, yielding `0x94 + 0x478 = 0x50C`. Script Extender lists the same gold offset.
The observed values are plausible but have not yet been checked against this save's
in-game treasury display or a controlled gold-only change.

| Field | File offset within player record | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|---:|
| Gold candidate | 0x50C | 2000 | 5997 | 1784 | 2000 |
| Wood | 0x4D8 | 100 | 45 | 26 | 0 |
| Stone | 0x4E0 | 48 | 20 | 21 | 0 |
| Bread | 0x4F8 | 0 | 101 | 42 | 0 |
| Spears | 0x51C | 0 | 4 | 5 | 0 |
| Population candidate | 0x78 | 4 | 158 | 104 | 4 |
| Army candidate | 0x53C | 12 | 736 | 386 | 12 |

Storage independently corroborates the goods layout. Building records have a
parallel candidate goods vector at +0x120 with stride 4. For each player, sum its
type 10 stockpile, type 19 granary and type 11 armoury records. **All 23 goods other
than the null entry and gold match the player totals**, across every player slot
in all seven saves. Many comparisons are zero; the nonzero comparisons, including
the values above, provide the useful evidence. Full comparisons are archived.

Gold does not match the storage-building sum (which is zero), consistent with a
treasury value rather than physical stored goods. The null entry differs too;
do not call it a commodity or assume zero is required. Incoming goods and economy
modifiers were not independently validated in this investigation.

The files demonstrate persistent per-player resources in this container. They do
not establish which values a new-match setup overrides, or that changing only the
player total correctly changes physical stored goods. Editing wood/food/weapons
may require synchronizing the storage records. Do not implement a generic resource
writer from the player vector alone.

## 6. Movement and path-related fields

The existing current position triple works on all 1,460 units. Selected neighboring
fields suggested by `GameUnit.cs` plus the previously observed +4 file displacement
also strongly cross-check. This does not justify shifting the entire runtime struct.

| Candidate meaning | File offsets / types | Coordinate-to-ID matches |
|---|---|---:|
| Current position (known) | X/Y uint16 +0xC4/+0xC6, ID uint32 +0xD4 | 1460/1460 |
| Target position | X/Y +0xC8/+0xCA, ID +0xD8 | 1433/1460 |
| Previous position | X/Y +0xCC/+0xCE, ID +0xDC | 1458/1460 |
| Next position | X/Y +0xE0/+0xE2, ID +0xE4 | 1458/1460 |

Target mismatches: 24 all-zero triples, plus three wheat farmers with nonzero
coordinate/ID disagreement. Previous mismatches: two all-zero triples. Next
mismatches: a peasant and a portable shield with nonzero X/Y but zero tile ID.
These can be inactive/cached/state-dependent fields; they are not proof of corruption.
1,001 units have target X/Y differing from current X/Y, which alone does not prove
that all 1,001 were moving at the instant of saving.

Additional uint16 candidates: path flags +0xF6, movement substep +0xF8,
path index +0xFA, path length +0xFC. Flag distribution: 2 on 737 records,
0 on 500, 1 on 220 and 5 on 3. Bit 2 is associated with movement in runtime
comments, but a saved value alone is not a validated moving/idle classification.

Example: unit slot 10, poleturner P2, current (444,278), target (449,281),
previous (416,276), flags 2, substep 2, path index 30 and length 34; linked
building slot 373, global ID 128462. The full route representation and resume
rules remain unknown. Preserve path state for unchanged units; moving/cloning
workers must eventually handle or correctly reset it.

## 7. Consequences for the editor and next useful checks

We can add save-backed inspection without requiring users to rename `.msv` files.
Resources, worker/building relationships and candidate movement overlays are useful
new inspection features. This work adds a reader variant and research reports,
not a GUI or supported state-editing operations.

Do not use an active save as the default blank-map template: it contains production,
orders, workers, inventories and other live state. A clean scenario export from a
save would need an explicit policy for preserving or resetting each subsystem.

The most useful next observations are:

1. Check P2/P3 treasury against 5997/1784 in the **original save**, recording whether
   time advanced; identify which player corresponds to which name separately.
2. Compare original save, built-in-editor resave and new game launched from that map.
   Track resources, worker links and orders separately to identify initialization.
3. A controlled idle/order/arrival save sequence for one unit can isolate route
   fields; a paused gold-only or single-resource transaction can test resource writes.

The existing seven related saves are already archived and useful. They are not
assumed to be chronological or one uninterrupted match, and broad differences
between them should not be treated as single-variable experiments.
