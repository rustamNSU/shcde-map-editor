# Leto save after a built-in map-editor session

Compared the archived original renamed save with the user's updated
`Maps/leto vs fbi 10.map`. The user reports resaving in the map editor. This is
an open/session/save comparison, not an isolated serialization-only experiment.
Both inputs were read-only and rechecked unchanged during analysis.

| | Before | After |
|---|---|---|
| Bytes | 3,864,831 | 3,841,117 |
| SHA-256 | `40d3cc85bcadc434028c7e10928ecd455d01f437d068fb6e35f61e382349a5d9` | `d71374ce598b8af227404d666d09539044bcd0e03cf08c5a196a6508c8f024a4` |
| Version / sections | 236 / 175 | 236 / 175 |

Both decode without errors and rebuild byte-identically. Of the numbered sections,
135 are unchanged and 40 have changed decoded bytes; none was added or removed.
Evidence: `output/leto-resave-2026-09-19/`, with before/after snapshots, manifests,
full section diff, player and unit changes, and cleared-unit CSV.
Reproduce with `research/check_leto_resave.py --output <new evidence directory>` using the
project Python environment. The script preserves sources and verifies readback.

## Economy and workers persist and evolve

| Field | P2 before → after | P3 before → after |
|---|---|---|
| Gold candidate, player +0x50C | 5997 → 6058 | 1784 → 1852 |
| Wood | 45 → 46 | 26 → 28 |
| Bread | 101 → 108 | 42 → 63 |
| Flour | 7 → 9 | 34 → 32 |
| Spears | 4 → 5 | 5 → 2 |
| Population candidate | 158 → 158 | 104 → 104 |
| Army candidate | 736 → 711 | 386 → 190 |

P1/P4 gold remains 2000. Further changes are recorded in `findings.json`.
All 23 non-null/non-gold stored-goods totals still match the storage-building
inventories for every player. Gold remains a strongly supported field interpretation,
not a direct UI-confirmed observation.

All 638 building records counted by the current decoder remain. The exact set of
237 building-worker assignments remains unchanged, and all reciprocal slot/global-ID
links still agree. Workers were not stripped from the resaved map.

The combination of changed inventories, gold and unit positions strongly supports
simulation updates during the editor session. It does not isolate how much happens
on loading, while the editor is open, or at saving; no exact elapsed ticks were measured.

## Important correction: occupied records are not necessarily living units

The decoder's `active_count` decreases from 1460 to 1240. Global-ID comparison
finds 220 removed records, no newly appearing units, and 1240 retained units in the
same slots with unchanged type, owner and controller.

All 220 removed records had state=2, candidate current HP at +0x3C8=0, candidate
health percentage at +0x2D4=0, and path flags candidate +0xF6=1 before the resave.
They comprise **all** zero-HP records counted by the old decoder in this snapshot.
All 1240 retained counted records have nonzero candidate HP afterward.

Removed records: 174 type-78 camel lancers, 43 knights, 2 slaves, 1 portable shield;
25 belonged to P2 and 195 to P3. Their state is zero afterward. 219 records become
entirely zero; slot 1560 retains only bytes +0x3DC/+0x3DD (`76 01`), whose meaning
is not established here.

This strongly supports cleanup of dead-unit records, rather than removal of 220
living troops. It also shows that state=2 alone does not prove a unit is alive.
Keep `active_count` as an existing decoder term for compatibility, but label it
as a record count in research and future UI until lifecycle semantics are established.
Do not conclude that flag value 1 universally means dead: the observation is from
one paired snapshot. Do not change general filtering based on one unit population.

P2's army candidate decreases by 25, agreeing with its removed record count;
P3's decreases by 196 while 195 records disappear. Do not equate this counter with
the number of surviving unit-table records or claim full accounting is solved.

## Movement continues rather than being reset wholesale

Among the same 1240 retained global IDs:

- 772 current packed tile IDs change; all current coordinate triples remain valid.
- 768 next-position candidate IDs and 60 target-position candidate IDs change.
- 769 path-index candidates, 697 movement substeps, 70 path lengths and 136 path
  flag values change.
- 9 associated-building slot/global-ID candidate pairs change. These are not changes
  to the 237 reciprocal building worker assignments, which remain identical.

The state is retained and evolves rather than being replaced by a static set of
freshly placed units. The complete route encoding and safe rules for resetting orders
are still unknown. `unit_changes.json` records field-level deltas by global ID.

## Header and terrain changes

- The same 97-byte extension payload survives the map-editor resave. Its absolute
  offset shifts with prefix size. It cannot be treated as a reliable marker of an
  untouched save file, nor should it be stripped simply because the extension is `.map`.
- U3 embedded filename changes from `001 3 green Fenrir.map` to `leto vs fbi 10.map`.
- U4 payload +0x04 uint32 changes 1→0. This is a candidate mode/status field;
  its meaning is not established by one pair. Menu player count, markers and size
  remain unchanged.
- Preview palette has 105 changed bytes; index raster has 3014 changed bytes.
- Surface 3037, noise 3008 and base height 3045 remain byte-identical.
- Current height 3005 changes at one cell, (417,487), from 8 to 0. Cause unknown.
- Logic 3003 and auxiliary layers including 3006/3007/3021/3030/3036 change.
  Do not classify every such difference as a resave normalization: simulation
  updates and moving objects are confounding factors in this sample.

## Implications

The built-in editor can resave this populated simulation state while retaining
workers and resources; it does not automatically make a clean starting map. This
does not establish what a newly launched match will preserve or override.

For future controlled field experiments, an ordinary editor session is not a
no-change baseline: units and production can evolve, and dead records can disappear.
The future app should distinguish record occupancy from living-unit count and
preserve original state during read-only inspection.
