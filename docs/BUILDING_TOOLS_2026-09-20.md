# Experimental building tools

Castle repair follow-up: the castle prefab now comes from isolated `ref_12_castle`
with explicit group-ID remapping and player initialization/removal symmetry.
Dead linked lords are removed too. See `CASTLE_AUDIT_2026-09-20.md` for evidence,
regression coverage and the remaining game-validation limit.

The user authorized placement/removal and a limited GUI catalog. Original maps
were read only. Main reference snapshot: `output/buildings-2026-09-20/` with
`inventory.json` (112 building records). SHA256 of `ref_11_buidlings_400.map`:
`52514e52710005786836b1d1e323f5ff1a3013f05cfe1d6040b6a95d00b58d24`.
Flat wall/stair profiles come from `ref_12_ladders_and_hills_400.map` and the
previously documented wall experiments. Rebuild the compact bundled catalog
with `research/build_building_catalog.py`; JSON contains exact records and cell masks.

## Catalog and measurements

Dimensions below are cells. Field size means layout envelope, not a solid building.

|GUI name|Building type ID|Footprint / linked parts|
|---|---:|---|
|Castle|41,71,73,72,55,10×4|7×7 keep; three doorway cells; 7×7 camp; four 2×2 stockpiles; one lord unit|
|Hovel|1|4×4|
|Woodcutter|3|3×3|
|Ox tether|4|2×2|
|Iron mine|5|4×4; no separate pile in reference|
|Hunter's post|7|3×3|
|Armoury|11|4×4|
|Fletcher / Blacksmith / Poleturner / Armourer / Tanner|12 /13 /14 /15 /16|4×4 each|
|Bakery / Brewery|17 /18|4×4 each|
|Granary|19|4×4|
|Quarry + pile|20 +21|6×6 plus 2×2 at quarry offset(7,2)|
|Inn|22|5×5|
|Wheat farm|30|3×3 farmhouse; 9×9 field envelope; 45 building-reference cells|
|Hops farm|31|3×3 farmhouse; 9×9 field envelope; 33 building-reference cells|
|Apple orchard|32|3×3 farmhouse; 10×10 envelope; eight vegetation records of type15|
|Dairy farm|33|3×3 farmhouse; 10×10 envelope; 32 building-reference cells|
|Mill|34|3×3|
|Small gate|46|5×5; reference passage along Y|
|Large gate|45|7×7; reference passage along X|
|Drawbridge (with gate)|49|5×5; attached below small gate or right of large gate|
|Lookout / Perimeter / Defense / Square / Round tower|74 /75 /76 /77 /78|3×3 /4×4 /5×5 /6×6 /6×6|
|Low wall / High wall / High wall + stairs|No building record|1 cell /1 cell /6-cell horizontal profile|

User correction recorded: type36 small church,37 church,38 cathedral. Display
names are corrected in the inspector; these are not added to the selected palette.
SE/stats still use generic Tower1–5 enums; GUI uses the user's proper names.

## Composite details and additional findings

- Castle stockpile origins relative to keep: (7,2),(10,2),(7,5),(10,5).
  Keep at(x,y), doors at(x+2..4,y+7), camp at(x,y+8). Nine building records
  total, plus the lord in3015. Castle stamps reserve the complete12×15 envelope.
- 4013 stride812: state+D0,type+D2,owner+D6,gid+D8; world+E8/EA,
  tile+EE/F0,index+F4,side+F8,access+FE/100. Tile origins also occur at+8C,+C8
  and in the36-entry array+1C8..254. +260 is a coordinate pair when present.
- **+90 is not a tile ID**. +8C is the observed bottom-right tile field.
- +192 is a contextual building link: quarry to pile, castle children to keep.
  It must not be interpreted as universally meaning quarry.
- New finding: section1031 is consistent with a516-byte gate/connection record
  array. Three gate controls occur at slots1,2,3. Gate building+2D2 refers to
  those slots. Record+0C is building slot,+14 its global ID,+18 owner;
  +1C/+20 and+28/+2C are endpoint coordinates,+24/+30 endpoint tile IDs.
  +08 is a separate global ID. Corroborated against both small gates and big gate;
  semantics of remaining manager fields are not fully known.
- Player2022 links use access coordinates, not always the building origin.
  +94 keep,+BC first stockpile,+E4 first granary,+10C first armoury,+1D4 camp.
  Camp link points to(x+3,y), not its standard access field. Lord lookup sections
  1190/1191 and player+21F8/+21FC update with the castle; housing+74 updates.
- Historical assumption about1047 being an allocation high-water mark is wrong:
  this sample has1047=26 with112 active buildings. Writer does not modify it.

## Behavior and limits

- GUI Build(G), Remove(D), visible scrollable catalog, player1–8 selector,
  footprint previews, tooltips, Hotkeys entries. Right/middle-drag still pans.
- Headless `BuildingService` and JSON `place_building`/`remove_building` operations.
  Entity, grid and player edits share one transaction and undo/redo command.
- Prefabs use source default terrain, including resource/field cells. This is
  map design, not paid gameplay construction. Existing buildings/units/vegetation,
  map edges and non-flat terrain block placement. One castle per player.
- Removal recognizes matching catalog groups after saving and reopening;
  castle stockpile/door/camp clicks resolve to the castle, quarry pile to quarry,
  orchard gaps to orchard, and attached drawbridge to its gate group.
- Imported buildings containing goods or assigned workers are refused, rather
  than leaving dangling live-save state. Unknown layouts are also refused.
  Flat wall removal erases a single cell. Terrain textures/minerals remain.
- Fresh entities occupy clean zero slots; global IDs advance1035. Do not reuse
  dead-but-nonzero simulation slots. Static references/readback are validated.
- Only observed orientations are included. Additional small/large gate and
  drawbridge directions need reference evidence; no fabricated rotation selector.
  Current bridges are convenient gate+bridge groups, not standalone free placement.
- Local path-region IDs are separated, but complete connectivity/directional
  cache regeneration is **not established**. Tests are structural, not proof of
  game movement, allocation counters, farm productivity or rendering.
- Castle changes update menu player count. 400-map start markers use the
  previously corroborated projection. 500-map markers retain source values and
  validation warns to resave in the game editor. Menu preview is retained.

Validate representative exports in the built-in editor and game before treating
building writing as stable. Tests cover both sizes, every prefab, linked records,
source-byte preservation, export/reopen, child removal, undo/redo, collision and
boundary rejection, atomic recipes, and native Qt placement/removal.

## Build verification

- Full suite:39 tests passed.
- Source and packaged native Qt self-tests passed, including placement/removal,
  undo, export and reopening. Reports/screenshots/maps:
  `output/buildings-2026-09-20/ui-smoke/` and `packaged-smoke/`.
- Replaced the normal `dist/SHCDEMapEditor.exe` (69,742,952 bytes); no alternate
  executable copies or user processes were created/terminated for the update.
  SHA256: `65fa73b894dfe7389426bf7a967b7905595177855a508702a67da5dea7c33d21`.
- Original live reference SHA256 was rechecked and remains unchanged.
- Game/editor load and gameplay have not been tested by this implementation run.
