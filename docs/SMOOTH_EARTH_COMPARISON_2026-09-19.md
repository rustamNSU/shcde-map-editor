# Smooth plateau repainted to earth: actual saved differences

Compared archived generated etest_smooth_plato.map to user-saved
etest_smooth_plato_fix_to_earth.map. Snapshot and machine-readable full diff,
findings and correlations: output/smooth-earth-comparison/. Source rechecked
unchanged. User reports visible center change after painting earth.

All current/base heights (3005/3045) are byte-identical, as is noise3008.
Center remains2500 cells at130. But surface3037 is NOT cleared to0:

- All2500 center cells changed0→8, exactly height130.
-154 cells on the slope changed0→4, all at height80.
- No other3037 changes. Sand bit64 is not added.

This means calling3037 a final texture selector, or equating0 with the complete
visual state of earth, is incorrect. It is a mixed bitfield including elevation
level markers; the file confirms these exact markers after game editing/saving.
It does not isolate whether load, brush or save caused their regeneration.

Other candidate grids changed:

|Section|Changed cells|Notes|
|---|---:|---|
|3003|26596|0x8000→0, including196 perimeter cells of the cap|
|3006|13359|0→2|
|3007|13298|16→17 or18|
|3036|5769|1855 in center;3760 on unchanged flat height8 outside|
|3037|2654|2500 at130→8 and154 at80→4|

3036 gains value1 at1034 cells:684 height8,154 height80,196 height130.
Thus these new1 values follow boundaries/elevation levels, not a uniquely
identified painted-center brush footprint. Do not claim3036=1 means earth.
Additional metadata sections and preview changed, documented in diff.json.

Conclusion: height-only files receive broad derived-state changes after an
editor session. The user's visual earth repaint did not produce a simple
3037→0 edit in the saved result. The exact texture-relevant field(s) remain
unisolated because the available pair combines first load/reconstruction,
painting and save. A no-brush load/save of the SAME generated smooth original
would separate reconstruction effects from painting; it is not currently present.
