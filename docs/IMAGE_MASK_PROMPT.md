# Image masks and heightmaps

Brush → Import opens JSON masks directly and previews conversion for images.
Image import accepts PNG, JPEG, BMP, TIFF, GIF, WebP and other raster formats
supported by Pillow. Source images can have any dimensions or colors. Conversion
reads the source without changing it; Continue opens the mask editor before any
library file is written.

Choose an output width and height from 1–800 cells. Fit whole image preserves
the image proportions with transparent margins. Fill output crops the edges;
Stretch changes both proportions to match the chosen dimensions. Shrinking uses
pixel averaging and enlargement uses smooth interpolation. EXIF orientation is
honored. Without saved import options, a large image initially fits inside
120 × 120 cells; smaller images keep their size.

## Binary shapes

Color is converted to luminance. A cell paints when brightness reaches the
threshold and opacity reaches the minimum opacity. The default for both is128
out of255; fully transparent pixels always skip. Invert brightness reverses light
and dark before thresholding. Expand visible brightness to full contrast maps
the darkest and lightest visible pixels to0 and255.

Binary shapes apply the selected terrain, height or variation value. The normal
Invert mask checkbox swaps painted and skipped cells inside the mask rectangle.
It does not modify the saved mask. A solid shape can therefore become an empty
brush when inverted. CLI stamp supports `"invert":true` alongside rotation and
mirror.

## Height values

Choose Height values to store an absolute height for each visible pixel. Black
maps to the chosen minimum and white to the chosen maximum, with intermediate
brightness mapped using:

```text
height = min_height + floor((luminance × (max_height - min_height) + 127) / 255)
```

The mask can hold values0–255. The normal game terrain interval is8–130; the
editor warns about values outside it. Transparent pixels are holes that leave
the map unchanged. An opaque black pixel can store height0, so black and a hole
are distinct. 16-bit grayscale images are scaled to the same brightness interval
without clipping the gradient to white.

Height-mask inversion preserves the holes and reverses values within the saved
range: `inverted_height = min_height + max_height - height`. Rotation and mirror
move coverage and height values together. Use the Height tool to stamp a height
mask as actual values; other tools can use its coverage as a shape.

## Editing and library

Right-click a mask for Edit tags or Edit mask. The pixel editor supports1–800
rows/columns, expansion, zoom, Fit mask and Invert. Binary mode uses left-click
toggle and drag painting. Height mode uses left-click/drag to paint the selected
height and right-click/drag to make holes. Min/Max define its inversion range;
changing the range clamps existing values into it. Mask type switches between
binary coverage and height values.

Save updates the current library mask and closes; Save As creates a new
named/tagged copy. Cancel leaves the library unchanged. All masks are saved in
`%APPDATA%/SHCDEMapEditor/Patterns`. The Masks folder button opens this folder.
Tags are optional, case-insensitive strings up to40 characters each. The gallery
can show All, Untagged or a particular tag; copying a JSON file carries its tags.

Existing binary masks retain JSON version1:

```json
{"version":1,"name":"My mask","cells":[[0,1,0],[1,1,1],[0,1,0]],"tags":["shape"]}
```

Height masks use version2 with a separate coverage matrix. Heights in skipped
cells are retained when editing but do not change the map:

```json
{"version":2,"kind":"height","name":"My hills","cells":[[1,0],[1,1]],"heights":[[8,8],[69,130]],"height_range":[8,130],"tags":["heightmap"]}
```

Rows run top to bottom and columns left to right in map storage coordinates.

## Prompt to give another agent

Create a downloadable PNG brush mask for my Stronghold map editor depicting
[DESCRIBE THE SHAPE HERE]. Use code to produce the final pixel-exact PNG.
Make it exactly120 ×120 pixels, viewed flat from above, with no isometric
projection. One pixel equals one terrain cell. Use only opaque white (#FFFFFF)
for cells to paint and opaque black (#000000) for cells to leave unchanged.
No gray, antialiasing, gradients, shadows, text, grid lines, border or mockup.
Keep the shape inside the canvas, with a small black margin. Return the actual
PNG file named map_mask.png.

For a heightmap, request a grayscale PNG or TIFF, state the desired output
dimensions and use transparent holes where the map should remain unchanged.
Choose the black/white height range in the import dialog.

## Texture variation

View → Variation shows section3008 values on a fixed grayscale range0–65535.
Use Variation (N) to paint a constant value with this mask. For combined terrain
and variation stamping, use Paint and enable Apply with terrain painting in the
Texture variation/noise panel. Inspector shows the numeric texture_noise value.
Exact game texture selection remains unknown.
