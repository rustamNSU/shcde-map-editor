# Direct-game terrain step experiment: user observations

Map: etest_height_steps_01_30_castles.map. Generated from the two-castle empty
400 map by changing ONLY3005 and3045; graphics-related fields, logic and region
labels were kept as in the flat source. Exact coordinates and hashes in
output/height-steps-castles-2026-09-19/manifest.json.

User reports:
- At strip16 the unit can climb to the top.
- Beyond16 it cannot climb even the first raised cell.
- Starting at strip19, some cells render black/glitched.

Strip d has eight cells from8+7*d down to8. Therefore:

|Strip|First rise from ground|Top|
|---:|---:|---:|
|16|8→24 (delta16)|120|
|17|8→25 (delta17)|127|
|18|8→26 (delta18)|134|
|19|8→27 (delta19)|141|
|30|8→38 (delta30)|218|

This supports a step-up movement limit of16 in this tested direct-game context.
The17 failure already happens at height25, so it cannot be explained simply by
a maximum absolute elevation near130. Unit type, direction/downhill and movement
mode are not independently tested. Wall-stair decrement16 in ref12 corroborates
but does not prove a universal threshold for every unit and terrain state.

Black cells do NOT establish a maximum usable height. The height byte can encode
0..255, but legal runtime combinations may be more restrictive. This test changes
step size and maximum height together, and its narrow ridges have abrupt lateral
drops while derived display fields remain untouched. Need exact black-cell
coordinates/heights and controlled height-vs-gradient experiments to distinguish
absolute-height limit from rendering/reconstruction issues. Do not label141 as
the engine's maximum height or130 as a proven cap. Recorded normal game-created
walls also reach220, although those are a different geometry/material case.
