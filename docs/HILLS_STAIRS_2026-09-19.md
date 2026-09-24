# ref12: stairs, residual elevated walls, slopes

Source ref_12_ladders_and_hills_400.map is copied and read-only verified in
output/hills-stairs-2026-09-19. research/check_hills_stairs.py exports findings.json,
all raised/wall cells in cells.csv, geometry.png, and a raw comparison to ref11.
Ref11 is NOT a clean causal baseline: wall geometry was replaced, not just extended.

## Stairs

These are terrain wall-stair tiles, not ladder-carrier unit objects or building
records. Stair logic=0x900 (IsWall|IsStairs), normal high wall=0x100,
low wall=0x10100. All stairs use owner3043 as recorded in the report.

|Structure|Coordinates|Heights along increasing x|
|---|---|---|
|High wall +5 stairs|x392..397,y521|98,82,66,50,34,18|
|Low wall +3 stairs|x395..398,y542|68,52,36,20|
|Elevated high wall +13 stairs|x424..437,y472|220,204,188,172,156,140,124,108,92,76,60,44,28,12|

Ordinary ground is8; stair decrements are16 between consecutive stair tiles.
The final transition to ground need not be16 (10,12,4 here).
Building table is empty; there are3 unrelated unit records (types22,22,28).

## Residual elevation under walls

At(424,472):logic0x100,surface8,base3045=130,height3005=220,3006=212,region3021=1.
The high-wall top remains90 above the stored high-plateau base even though the
surrounding stairs have base8. This explains the long stair geometry from the
stored data, not a distinct special ladder type.

At(405,485):isolated high wall,base80,top170,3006=162,region2. No stair link.
The after-demolition state was not saved/provided; do not claim to know exactly
which residual flags prevent rebuilding from this pre-demolition snapshot.

## Correction to3006 interpretation

The ref11 equality3006=height-base was valid for flat ground only. In ref12 it
fails on both elevated wall anchors:220-130=90 but3006=212;170-80=90 but3006=162.
Both equal top minus surrounding flat-ground height8 instead.
On natural raised terrain3005=3045 but3006 is often nonzero (1272 of2631 cells).
Thus3006 depends on more than local base height; a terrain/display drop metric
is a candidate, not established semantics. Tests of max drop to4 neighbors,
8 neighbors and selected forward neighbors do not match all2656 elevated tiles;
do not encode any of those as a universal formula.

## Slopes and connectivity

Top raised component:x354..422,y267..325,2099 cells,heights9..130. All its171
logic0x80 cells have region0; remaining1928 raised cells have region1, shared
with the plain and stair-connected walls. This supports the user's accessible
smoothed transition: elevation alone does not imply an isolated region.

Second raised component:x424..458,y436..464,532 cells,heights9..124.91 edge
cells region0;441 cells region1. Across entire map the region0 cells are exactly
the262 cells with ImpassableEdge0x80. The only region2 cell is the isolated wall.
These are saved connectivity labels, not a live unit movement test. Nonzero
region does not imply buildability: cells may have logic0 rather than IsLand.

An external editor can represent arbitrary terrain heights and ramps and wall
stairs from these layers; king-of-the-hill terrain is plausible. Reliable writing
still requires the slope/edge and connectivity update rules, plus in-game tests.
The threshold rule deciding0x80 from neighboring heights is not yet established.
