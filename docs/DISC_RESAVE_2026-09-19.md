# Abrupt plateau, no-brush load/save control

User reports only opening and saving etest_disc_plato_resave.map. Compared to
archived generated etest_disc_plato.map; original untouched. Snapshot, hashes,
full diff and all grid statistics: output/disc-resave-comparison/.

Unchanged byte-for-byte: surface3037 (all zero), both heights3005/3045, noise3008.
This disproves assuming a load/save always derives3037=8 from height130.
The prior smooth repaint file did gain elevation flags; it is a different
geometry AND includes brushing, so this control cannot isolate its brush effect.

Six candidate tile grids change without any brush action:

|Section|Changed cells|Effect|
|---|---:|---|
|3003|2500|Cap interior48x48:0x8000→0;perimeter196:0x8000→0x80|
|3006|99|0→122, equal130-8, on two sides of cap|
|3007|891|196 cap-border cells acquire2064/2065/2066;695 other cells become0|
|3021|2500|Interior2304 changes region1→2;perimeter196 region1→0|
|3030|588|Neighborhood/path masks change around cap border|
|3036|965|All outside50x50 cap;no center value changes|

All2500 cap heights remain130.196 perimeter cells are exactly the one-cell
outline (2500-48*48), consistent with the impassable edge flag and zero region.
The48x48 top becomes a separate connected region2; outer ground retains1.
This is saved connectivity evidence, not a live pathfinding test.

No interaction is needed for these derived states to change. The pair does not
distinguish load-time, update-loop or save-time recalculation. Metadata, preview
and3934 also change; do not conflate them with terrain editing.

Important revised conclusion: the plateau-like appearance reported by the user
can occur while3037 remains0. Neither3037 alone nor a universal automatic
height130→surface8 rule describes the engine. Exact graphics selection remains
open.3006's122 on99 cells supports an oriented visible-height-drop interpretation,
but is not a recovered universal formula.
