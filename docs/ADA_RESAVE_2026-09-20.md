# Ada GUI export versus working native resave

## Subsequent menu/preview repair

The application now regenerates menu counts and positions on explicit Save,
including reopening and saving an already-broken map with no edits. New500
markers use `((x-y+301)//3,(x+y-495)//3)`; this matches all4 Ada positions exactly.
Independent native500 controls have at most1 horizontal pixel rounding difference;
valid native positions on unchanged castles are retained, not reprojected.
Preview uses3cells/pixel and black margins, with icons sharing the lobby positions.
Artwork remains schematic. `tests/test_menu_export.py` checks Ada metadata against
the native resave, all numbered sections unchanged, preview bounds, native-marker
retention, new500 castles/removal/undo. Seven relevant tests pass.
The 123410 region-cell changes and startup deaths are NOT resolved by this patch.
Original maps remain unchanged.

User reports `2v2 Ada_gui.map` has unusable lobby positions and immediate lord
deaths; `2v2 Ada.map`, resaved in the built-in editor, works. Both are size500.
Originals were read only, snapshotted, and SHA256 rechecked unchanged.
Reproduce with `research/analyze_ada_resave.py`; full byte/word/entity evidence and decoded
preview PNGs are in `output/ada-resave-2026-09-20/`.

| Source | SHA256 |
|---|---|
| GUI | 6edf1c549aeb0837dcec4c7f65121a7439acc2703fc594777432a3d37c97c38f |
| Native | 4b93b8416708d3d11b4e5e736a7f71c6a1728d7992fa5457a074215e19333bde |

## Confirmed lobby and preview defects

Both files have U2 player count4. GUI U4 has all8 marker pairs set toFFFFFFFF,
meaning absent. Native U4 has P1(40,126), P2(73,159), P3(130,36), P4(163,69),
with P5–P8 absent. The writer updates markers only for400 maps. This is a real
500-map export omission, not a missing castle or incorrect player count.
Additionally U4 payload+0x0c changes1→0; its exact meaning is not established.

Preview is fresh, not the empty template. Both decode to40512 bytes, but GUI
uses all200x200 pixels while the native map occupies x18..183,y17..182 inside
black margins. GUI scale200/500 is wrong for native500 alignment. A roughly
1/3 scale is corroborated by Ada and two independent500 maps (3v3 Einstein
SquaD and -3vs3- 500 by sverko). Do not assert an exact x-rounding formula:
simple `(x-y+C)//3` fails across these samples by one pixel. A formula fitting
Ada alone would overfit. All20 checked native500 y markers fit `(x+y-495)//3`.
GUI preview is intentionally schematic; native terrain artwork is a separate gap.

U3 embedded filename remains `ref_00_base_500.map` in GUI; native sets
`2v2 Ada.map`. Description, preview extension and trailing data are preserved.

## Castles and lords

Both have36 buildings (four complete nine-record castle groups) and4 active
lords. Keep slots1/10/19/28, owners1..4, global IDs5/15/25/35, anchors
(347,527),(446,527),(347,258),(446,258) are unchanged. Lord slots1..4 and
global IDs14/24/34/44 are unchanged, each has150000 HP in BOTH files.
Sections1190/1191 and1035 are unchanged; building0x2a8 group-root IDs are
unchanged. This is not the previously repaired stale-group-ID discrepancy.
Native simulation moves each lord(+2,+2), changes movement/timing fields and
updates8 occupancy cells; slot0 also receives transient unit data.

Correct pre-game HP does not establish successful game initialization. This pair
does not isolate the single cause of startup deaths. Missing lobby positions,
derived navigation and player/cache initialization must be distinguished.

## Native resave rebuilds non-cosmetic data

| Section | Changed cells | Observation |
|---|---:|---|
| 3021 | 123410 | Region1 splits into0..9; lord cells move from region1 to3 |
| 3003 | 17782 | 16480 land flags→0;1298→0x80;4 add0x10000000 |
| 3030 | 3454 | Derived neighbor/passability candidates change |
| 3007 | 3361 | Display/edge variants change |
| 3006 | 782 | 0→122 auxiliary cliff values |
| 3009 | 100 | Previouslyzero values become8..62 |

Heights3005/3045, surface3037 and variation3008 are byte-identical. Both contain
17778 cells at height130. Native resave is rebuilding derived data around the
existing design, not fixing it by repainting heights or variation. The GUI
height service only writes3005/3045, retaining stale flat-template dependencies.
Native also changes3036 and3934, whose exact interpretation remains incomplete.

Player2022 changes35 bytes total. At offsets2088/2148/22dc P1–P4 become3,
other players become4; P1–P4 offset2b64 becomes792. Names/necessity unknown.
Section1171 at byte offsets1000/2000/3000/4000 becomes17 (not the1 observed in
the earlier height resave). Section1096 fills lists containing lord global IDs
and player IDs. Do not copy these wholesale or treat arbitrary constants as fixes.
Some differences are ordinary simulation advancement during editor resave.

## Required tool work

1. Implement and independently verify500 lobby marker projection and matching
   preview geometry. Refresh menu data on save of already-broken imports too:
   current writer skips metadata work when the keep signature has not changed.
2. Rebuild verified height/edge/navigation dependencies after terrain edits;
   structural byte-preservation tests alone cannot establish playability.
3. Investigate lord/player initialization with controlled game checks. A repaired
   marker header alone is not proof that immediate deaths are resolved.
4. Update embedded filename on explicit save without modifying unrelated headers.

The original audit changed no live maps. See the subsequent repair above for
the implemented subset; remaining gameplay failures must not be called fixed.
