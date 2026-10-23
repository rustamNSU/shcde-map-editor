# Three-castle oasis grid experiment

Output game map: etest_oasis_grid_3_castles_400.map.
Source: ref_00_base_400_castles.map plus its original empty400 template.
No source modified. Script: research/make_three_castle_grid.py. Audit, source snapshot,
output copy and schematic: output/three-castle-oasis-grid/.

Keep origins: P1(397,397), P2(375,260), P3(415,260). Each has the original
9-part starting complex and one lord. P2/P3 keep origins separated40 cells.
Map400. Oasis lines have pitch5 and width1, plain-earth interiors4x4.
Lines cover unoccupied plain land; building footprints/approach geometry retain
their template state. Partial cells at outer playable border are expected.

## Relocation evidence

Two same-type source complexes corroborate coordinate fields by equal relative
position to respective keep anchors. This identifies packed tile IDs, uint16
tile/world pairs and uint32 player coordinate pairs without replacing all
similar-valued integers. Fields/audits in manifest.json.

Building evidence includes main position, access, cached tile indices0x8C/0xC8,
occupied tile list0x1C8..0x254 and coordinate pair0x260 where present. Unit evidence
includes current/target/previous positions, world coordinates, tile IDs and linked
production-building position. Player links relocate with the matching buildings.
P3 copies P2 templates into unused building slots19..27/unit slot3, gets unique
global IDs and player/color updates;1190/1191 lord lookup entries and1035 next
global-ID are updated. Historical correction (2026-10-23): section1047 is a
scenario selection index, not a building high-water mark. The generator's old
1047>=27 precondition has been removed; it retains direct clean-slot checks.
See [the DLL registry audit](RUNTIME_FORMAT_AUDIT_2026-10-23.md). The remaining
generator is an experimental source-specific cloning routine; its clean-slot
checks do not implement a general allocator.

Local castle grids are translated from source patches after clearing old sites
with the empty template. Noise and unknown3036 remain at destination coordinates.
Grid footprint indices, wall ownership and unit indices are remapped for P3.

## Validation and limits

- All compressed sections decode and checksums pass.
-27 active building parts and3 active lords; all tile coordinates match packed IDs.
-Each player has9 parts occupying117 referenced cells; each square footprint matches.
-No dangling building/unit grid references;30 unique global IDs.
-Player keep/stock/camp links and coordinates match.
-Destination patches do not overlap and lie inside the playable map.
-Unchanged sections preserved byte-for-byte; written copies verified.

No in-game launch test has been performed by the agent. Unknown metadata/allocator
dependencies have not been exhaustively reverse engineered; this is a test map,
not proof of a universal castle-placement serializer. Embedded preview is the
source preview; layout.png is a separate schematic, not game imagery.
