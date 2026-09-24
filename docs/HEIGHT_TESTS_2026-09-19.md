# User-requested height-only tests

## Disc plateau appearance follow-up

User reports plateau-looking center despite requesting earth, and that earth can
be painted back. The current game-folder etest_disc_plato.map was checked against
the generated archive: byte-identical SHA256
6c4304f4077c3d831a36b07a47a4948e483de02330e8df60440e4c0a26a20eed.
Thus no newly saved post-paint state is present in that file at this check.
All2500 center cells still have3037=0,3003=0x8000,current/base height130,
3006=0,3007=16. It was not accidentally painted sand or plateau in the file.
Compare built-in ref05 high plateau: all117 height130 cells have3037=8, not sand64.
Its boundary also has0x80 logic and additional display-layer changes.

The user's visual observation suggests runtime graphics/reconstruction depends
on more than the stored surface byte (height/neighbors/derived state). It does
not prove a specific height-to-texture rule or that plateau is literally sand.
The saved plateau surface flag exists, while elevation and surface remain
separate fields. A saved post-earth-paint version is needed to inspect that edit.
Numeric evidence: output/height-tests-2026-09-19/disc_surface_check.json.

Created from ref_00_base_400.map by research/make_height_tests.py. Originals unchanged.
Game Maps and output/height-tests-2026-09-19 contain:

- etest_disc_plato.map: inclusive x375..424,y375..424,50x50 cells,height130;
  exterior ordinary ground8. Jump at boundary122.
- etest_smooth_plato.map: same cap, height falls2 per Chebyshev-distance ring;
 61 rings to height8. A square truncated-pyramid terrain shape. Not a disk.
- etest_height_steps_01_30.map:30 independent one-cell-wide strips, spaced6
  cells along increasing x. Strip d at x=310+6*(d-1),y396..403. Heights along
  increasing y are8+7d,8+6d,...,8+d,8. Highest218 at d30. No IsStairs flags:
  these are terrain height probes, not constructed wall stairs.

Changed only3005 current height and3045 base height. All other section raw bytes
preserved, including3037 (earth),3003,3006,3021,3030,noise and preview. Compressed
block sizes and catalog offsets necessarily updated. All sections decode and
all target heights verified after writing. Manifest records hashes and coordinates.

This deliberately tests what the game rebuilds from height alone. Existing
connectivity/edge flags were NOT synthesized; observed movement cannot establish
a universal engine step threshold unless load/recalculation behavior is resolved.
Paths may bypass a strip along flat neighboring ground: observe the route, not
just whether a unit eventually reaches a destination. View at default rotation
or use coordinates to identify strips; screen left/right changes with rotation.
Preview remains the original flat preview; open maps to inspect geometry.

uint8 allows0..255 numerically, not a proof all values are valid gameplay terrain.
These tests use8..218. Await user observations/saved loaded versions before
claiming rendering or walkability works.
