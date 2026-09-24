# Image mask format

Import with Brush → Import, then stamp using the chosen terrain or height.
PNG pixels map directly to cells, maximum 120 × 120. White paints; black or
transparent pixels skip. Brightness and alpha must both be at least 128 to paint.
The image is a binary brush shape, not a full-color image or grayscale heightmap.
No automatic resizing or rotation is applied. Mask rotation/mirroring controls
remain available. Imported masks are stored as JSON in the Roaming Patterns folder.

## Prompt to give another agent

Create a downloadable PNG brush mask for my Stronghold map editor depicting
[DESCRIBE THE SHAPE HERE]. Use code to produce the final pixel-exact PNG.
Make it exactly 120 × 120 pixels, viewed flat from above, with no isometric
projection. One pixel equals one terrain cell. Use only opaque white (#FFFFFF)
for cells to paint and opaque black (#000000) for cells to leave unchanged.
No gray, antialiasing, gradients, shadows, text, grid lines, border or mockup.
Keep the shape inside the canvas, with a small black margin. Return the actual
PNG file, named map_mask.png, not just a preview or instructions.

Alternative native JSON format:
`{"version":1,"name":"My mask","cells":[[0,1,0],[1,1,1],[0,1,0]]}`.
Rows are top-to-bottom; columns left-to-right in map cell coordinates.

Optional `"tags":["letters","symbols"]` organizes JSON masks. Use the tag dropdown
above the gallery to show All, Untagged or one tag. Select a mask and click Edit
tags to assign comma-separated tags (up to40 characters each, case-insensitive).
Masks folder opens `%APPDATA%/SHCDEMapEditor/Patterns`. Tags are stored in each
JSON; copying that file carries its tags with it. PNG imports start untagged.
Invert mask flips filled/empty cells only inside the mask rectangle, without
modifying the saved file. A fully filled mask becomes an empty brush when inverted.
CLI stamp supports `"invert":true`, alongside rotation and mirror.

## Texture variation

View → Variation shows section 3008 values on a fixed grayscale range0–65535.
Use Variation (N) to paint a constant value with this mask. For combined terrain
and variation stamping, use Paint and enable Apply with terrain painting in the
Texture variation/noise panel. Inspector shows the numeric texture_noise value.
Exact game texture selection remains unknown.

Right-click a mask for Edit tags or Edit mask. The pixel editor supports 1–120
rows/columns, click/drag painting, expansion, and Invert. Save updates the current
library mask and closes; Save As creates a new named/tagged copy. Create and PNG/JSON
Import open this editor before writing anything. Cancel leaves the library unchanged.
All saved masks use the app Patterns folder, without a save-folder dialog.
