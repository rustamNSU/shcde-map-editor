# Current-map export preview

User requested preview-only implementation. `editor/preview.py` renders a200x200
schematic square overview from the current document, with surface/resource colors,
height shading, objects, trees and small player-colored keep icons. No Qt or game
assets required. This is not the exact native scene/sprite thumbnail renderer.
Castles on400 maps use the corroborated menu-marker projection;500 uses the map
geometry projection for thumbnail icons, without modifying500 header markers.

The image is quantized to256 colors and encoded as512 bytes of little-endian
RGB555 palette plus40000 indexed pixels. MapWriter.header compresses this using
the existing DCL encoder and replaces only the outer preview block. It preserves
preview extra/description bytes and shifts the following header/directory by
reassembling the prefix. Numbered-section offsets remain relative to their base.
Readback verifies every edited/unrelated section and the entire expected prefix.

Save As always refreshes the preview, including opened maps with an old stale
thumbnail and no new edits. `serialize(document)` retains byte-identical no-op
behavior; changed documents refresh automatically. Explicit
`serialize(document,refresh_preview=True)` refreshes an unchanged document too.
GUI and CLI Save As share this code. Thumbnail generation never edits map state
or introduces an undo command. Existing files remain protected against overwrite.

Embedded U3 filename, height/path fields, native cliff rendering and500 menu
marker calculation are unchanged in this task. Export warnings now describe the
schematic preview rather than claiming the source preview is retained.

Verification: tests/test_preview.py covers400/500 palette data, keep visibility, undo
to byte-identical input, stale-preview-only export, original section preservation,
description/preview extensions, save prefix and trailing data. Existing editor
and UI tests cover Save As and normal editing. Reviewed output:
output/preview-2026-09-20/height-map-preview.png, rendered read-only from the user's
etest_height_00 snapshot. This shows all four castles instead of empty ground.
All23 focused preview/editor/UI tests passed.
