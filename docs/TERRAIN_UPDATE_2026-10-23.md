# Terrain and height editing, 23 October 2026

The service layer now edits the DLL's native map sizes160,200,300,400,500,600,
700 and800. Ordinary terrain textures can be painted on elevated terrain; the
former requirement that current and default heights both equal8 was removed.
Building/tree/unit cells, reserved flags and map boundaries stay protected.

The palette includes sea, river, ford, beach, pitch, impassable rocks, middle
plateau and high plateau. Ground textures preserve existing elevation. Sea and
beach set current/default heights to0. River and ford retain default height and
set current height to default−8 when the prior current height is at least8;
otherwise they retain current height. This preserves beach/river history instead
of forcing every river's default height to0. Marsh/pitch use height8. Plateau
presets use80 and130 with surface bits4 and8. Replacing water with ground
restores default height, at least8. Pitch combines the marsh and pitch flags.

These rules are based on file-only Ghidra reconstruction of native terrain
brush RVA`0x6FE90` and preset brush`0x6FA10`, checked against the29 archived map
references in [REFERENCE_ANALYSIS_2026-09-19.md](REFERENCE_ANALYSIS_2026-09-19.md).
Reproducible height export ranges are in `research/height_brush_requests.txt`.
Local decompilations are in `output/terrain-native-2026-10-23/`; the terrain
brush is in `output/castle-bounds-2026-10-23/native/terrain_foundation.c`.

`HeightService.paint_values(indices, heights)` applies corresponding absolute
integer heights0–255, including zero. It skips protected cells, writes current
and default height together and clears old impassable-edge bit`0x80`, matching
the explicit clearing step in native height brushes. Scalar painting delegates
to this API. Heights outside the ordinary8–130 editor interval remain possible.
This absolute-value interface does not reproduce the stock brush's gradual
raise/even operations or its8–156 clamp.

The document transaction rebuilds native navigation edges3030 and connected
components3021 with the same undo command. Those derived arrays can legitimately
change in boundary cells. Undo restores them with the original edit. Full cliff,
shoreline and terrain graphic generation is not yet ported: native brushes mark
neighbouring graphics dirty through leaf`0x72520`, then later engine passes
generate additional fields. Native editor resave and in-game visual validation
remain relevant, especially for abrupt plateaus and shorelines.

Surface clipboard works at elevated heights and keeps destination tree proximity
flags. Water is excluded from surface-only clipboard because its depth needs
both height layers, which that clipboard does not carry. Height clipboard shares
the object checks and explicit old-cliff clearing step.
