# Castle writer audit against ref_12_castle

## Subsequent tool repair

The original comparison below describes the pre-repair output, retained unchanged.
The tool now uses the isolated hashed ref_12 castle prefab, explicitly remaps
building0x2a8 group IDs and updates the five corroborated player fields. Civilian
count changes by the lord contribution; resources and unrelated player fields are
preserved. Access flags clear when their link clears, and an existing alternative
stockpile restores its access link/flag. Castle removal also removes dead linked
lord records, clears all their3010 references and player lookups. All these changes
participate in the existing transaction/undo system. Slot0 and unproven global
fields are not changed. Validator rejects stale group links on rewritten keeps.

Regression tests cover both map sizes, owners1/8, repeated placement/removal,
export/reopen, undo/redo, preserved gold/population, dead-lord cleanup, and deliberate
reintroduction of the old group-ID bug. These verify tool data consistency, not
game survival. The original source map and original audit outputs remain intact.

Validation: full discovered suite passed47 tests; the subsequently added native
reference removal/replacement test also passed. EXE replacement is pending the
user closing the running editor; do not mistake source changes for an EXE update.

The user reports dead lords even after a built-in-editor resave. This audit
reproduces the CURRENT writer, not a repaired implementation. No EXE was rebuilt.
The exact cause of the in-game death is not yet established.

## Reproduction and provenance

Run `.venv\Scripts\python.exe -m research.audit_castle_reference.py`.
Evidence: `output/castle-audit-2026-09-20/comparison.json` and three map snapshots.
Original source: live Maps/ref_12_castle.map, SHA256
`d49bc802954bb0898064d24214b85491b0ad13028b9d1dd41c2a4baa7881cc6b`.
Original was read only and rechecked unchanged. Baseline is bundled empty-400.map;
it is not established as the immediate parent of ref_12. Differences therefore
include editor history, simulation state and save noise, not just placing a castle.
The generated comparison uses that empty template and places P1 at the reference
keep anchor (401,404), through BuildingService and MapWriter.

## Confirmed layout

| Slots | Type | Origin relative to keep | Footprint |
|---|---|---|---|
| 1 | 41 keep | 0,0 | 7x7 |
| 2,3,4 | 71,73,72 doorway pieces | 2,7 / 3,7 / 4,7 | each 1x1 |
| 5 | 55 campfire | 0,8 | 7x7 |
| 6,7,8,9 | 10 stockpile parts | 7,2 / 10,2 / 7,5 / 10,5 | each 2x2 |

The reference has nine buildings and one lord (unit type55, slot1). Building
type55 and unit type55 are different namespaces. The generated group has these
same nine buildings AND a lord; absence of a lord is not the observed defect.
The reference lord is at keep+(3,2), (404,406). Generated lord is at keep+(4,3),
(405,407). Both positions are inside the upper keep rectangle. Both have health
150000 at unit file offset0x3c8, with matching max-health bytes at0x3cc. Lord slot,
owner, keep slot link, 3010 occupancy and 1190/1191 player lookup are populated.
Their presence does not establish correct runtime initialization.

## Confirmed stale building group IDs

Building record file offset0x2a8 is a group-root global ID in these samples:

| Records | ref_12 value | Generated value | Correct generated target |
|---|---:|---:|---:|
| Keep, three doorway pieces, campfire | 8046 (keep) | 4032 (old source keep) | 7923 |
| Four stockpile pieces | 8051 (first pile) | 4037 (old source pile) | 7928 |

The catalog source uses IDs4032..4041. Current placement assigns fresh primary
IDs7923..7932, but does not remap offset0x2a8. All nine records thus retain stale
group links. This relationship is independently corroborated by ref_10 P1 and P8
castle maps: group values142/147 and152/157 respectively match their own roots.
This is an actual writer bug, not harmless differing ID allocation.

## Incomplete player initialization

Section2022, P1 record stride0x583c:

| Offset | ref_12 | Current generated | Interpretation |
|---|---:|---:|---|
| 0x84 | 1 | 0 | Total civilians per Script Extender layout |
| 0xa4 | 1 | 0 | Unknown word after keep access link |
| 0xcc | 1 | 0 | Unknown word after first-stockpile access link |
| 0x1e4 | 1 | 0 | Unknown word after camp access link |
| 0x489c | 1 | 0 | Unknown player state |
| 0x2b64 | 32000 | 0 | Unknown; NOT a universal castle constant |

The first five fields are1 also for the owner of ref_10 P1 and P8, and for all
three owners in the earlier user-confirmed working three-castle generated map.
The older successful generator copied complete initialized player records;
the current implementation constructs a small subset of links on an empty player.
Do not invent names such as alive/dead flags for the unknown words.
0x2b64 differs in the successful map (0/2328/2328), so blindly setting32000 is
not justified.

## Other differences and limits

- Empty to ref_12 changes49 decoded sections; empty to generated changes17.
  The JSON lists every changed section and byte count plus all differing uint32s
  for nine building records, lord slot1 and P1. Numerical ID differences alone
  are expected because creation histories differ.
- Reference unit slot0 contains a lord-shaped record; generated slot0 is allzero.
  Older native castle references and the working three-castle map also have
  nonzero slot0. Its reserved/scratch role is unproven: do not count it as a second
  real lord or blindly clone it.
- Lord records differ in movement/path and other transient fields. The prefab
  was extracted from a populated reference's slot42 and inserted into slot1.
  Correct health/position alone does not prove those dependencies valid.
- Sections1068/1071/1072/1108/1109/1110 are1 in ref_12 and0 in empty/generated,
  but also0 in the older native single-castle refs. They are not demonstrated
  universal castle prerequisites.
- Sections1172/1173 are0 in ref_12 and older single-castle refs, but1 in the
  user-confirmed working three-castle map. They cannot simply be labeled the
  cause of death based on this diff.
- Terrain differences include3036 and3008 over large areas. There is no evidence
  that all such bytes need transplantation for one castle.

## Required repair and validation

Use an explicit verified group-root ID remap; strengthen validators beyond
primary-ID uniqueness. Rework castle player initialization using clean native
castle references, preserving other player state on populated maps. Investigate
lord initialization separately from position and health. Test placement, deletion,
undo, replacement and owner changes together so initialization has a matching
removal policy. Cover400/500 maps and multiple owners. Then test actual game load
and survival, both direct export and after built-in-editor resave. Static tests,
opening in the editor, and a rebuilt executable are not proof that lords survive.
