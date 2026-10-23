# Building prefabs and castle footprint correction

The editor now has **69 reference-derived placement choices**, covering 61
primary native building types (73 including compound helpers), plus the three
wall/stair templates. These are
file prefabs, rather than calls to the game's live build command. All original
reference maps and installed game files remain unchanged.

## Sources and coverage

`research/build_building_catalog.py` reproduces the bundled catalog from the
archived native `ref_11_buidlings_400.map` (SHA256
`52514e52710005786836b1d1e323f5ff1a3013f05cfe1d6040b6a95d00b58d24`).
Castle records come from the isolated native `ref_12_castle.map` (SHA256
`d49bc802954bb0898064d24214b85491b0ad13028b9d1dd41c2a4baa7881cc6b`).
Wall/stair graphics use the existing `ref_12_ladders_and_hills_400.map` samples;
no unobserved rotation is inferred from sprite numbers.

| Category | Placement choices |
|---|---|
| Storage | Four-section stockpile, granary, armoury |
| Resources | Woodcutter, quarry and stone pile, iron mine, ox tether, pitch rig |
| Food/farms | Hunter, dairy, apple orchard, wheat farm, hops farm |
| Workshops | Fletcher, poleturner, blacksmith, tanner, armourer, bakery, mill, brewery |
| Town | Hovel, inn, market, apothecary, well, water pot |
| Religion | Small church, church, cathedral |
| Military | Stone barracks, mercenary post, Bedouin stockade, engineers guild, tunnellers guild, oil smelter, stables |
| Fortifications | Five tower types, small/large gates, both verified gate/drawbridge combinations, castle, war dog cage, killing pit, high wall, wall with stairs, low wall |
| Good things | Maypole, four observed garden variants/sizes, dancing bear, statue, shrine |
| Bad things | Gallows, cesspit, stocks, burning stake, dungeon, stretching rack, gibbet, chopping block, dunking stool |

Military buildings include their observed parade-ground records. The oil
smelter preserves both directions of its building link. Four stockpile pieces
remain one group. Nonzero group-root global IDs are relocated for all prefabs,
including self-root records, instead of only castles. Removing a child resolves
the complete group after save/reopen. Garden layout matching checks its native
size and variant so removal does not clear an unrelated larger garden area.

## Sparse castle footprint

The old castle prefab stamped and reserved a full **12 × 15 rectangle: 180
cells**. Its native structure references occupy only **117 cells**. The writer
now edits those actual cells, including the keep, doors, campfire and stockpile
pieces, plus the lord's occupied cell if it were outside those references.
Empty holes inside the enclosing rectangle are left untouched during placement
and removal. A separate building in the empty southeast corner remains intact
when the castle is removed.

This does not make campfire tiles buildable. Native placement helper RVA
`0x7B060` rejects a nonzero structure reference (`3012`), including campfire
type55. Castle-triggered terrain painting on load has a larger footprint and is
a separate behavior; the placement footprint must not be enlarged to match it.

Farm support areas remain reserved: their fields/orchard vegetation are part of
the prefab even where the building-reference grid is zero.

## Elevated placement and safety

Placement supports native map sizes 160, 200, 300, 400, 500, 600, 700 and 800.
Every required cell must lie on the same plateau: current and default heights
must agree throughout the footprint. The writer translates both height grids
and building/lord height fields by `plateau_height - 8`, preserving the source
prefab's relative walls and tower heights. Translated byte heights must remain
in 0..255. Water, occupied cells and unknown logical flags remain rejected.

Only the observed clear-ground/resource, terrain-edge and elevated-walk-surface
bits are accepted on otherwise unoccupied flat support. The prefab retains its
own building/walk-surface flags; the underlying support's `0x10000000` bit is
not copied onto a different building type. There are no new invented elevated
sprite variants: source graphics and relative display data are retained. Newly added types on
non-default-height plateaus still need native-editor resave and in-game visual
checks, especially stairs, gates and compounds touching cliff edges.

Placement and removal are atomic/undoable. Removal refuses assigned workers,
stored goods and assigned stable horses. It does not implement live demolition
accounting. Existing populated-map simulation links, caches and lifecycle
behavior remain only partly understood; broad prefab coverage does not prove
all military/worker behavior in a running match.

Still missing verified templates include wooden gates/posterns, the remaining
keep variants, outposts, siege tents, dock, beehive, pond, bear cave, witch hoist,
flogging rack, pitch ditch and additional orientations. They were not created
by changing the type field of an unrelated record.

## Regression checks

Building tests cover all catalog choices on 400/500 maps with serialization and
reopening, helper-child removal, group-root IDs, garden variants, sparse castle
holes, stable occupied-link protection and relative plateau elevation. These
are structural checks; native-editor/game validation is still necessary for
the remaining graphics and gameplay questions above.

## New map sizes

The original audited 400/500 templates remain byte-identical. For the six other
native presets, `TemplateLibrary` derives a clean map in memory from the pinned
empty500 template. It retains every unknown section, entity array and the full
stored variation/noise array. Only section1050 (map size), section3003 (native
boundary logic), section3007 (known empty ground display) and native-derived
3030/3021 (navigation edges/components) change; the U4 menu map-size word is also
updated, and a current-size schematic thumbnail is generated in the file
header. Original400/500 template thumbnails remain untouched. Projection for
the additional sizes follows map geometry; exact native thumbnail artwork and
rounding at those sizes have not been validated. This constructs a new empty
map and does not resize populated maps.

Native helpers RVA`0x71390`/`0xE8E30` outline the full800 storage diamond and
central selected-size diamond, then flood-fill the outside. On empty maps the
result has an exact algebraic form. With integer map-cell coordinates `(x,y)`:

```text
d = (abs(2*x - 799) + abs(2*y - 799)) / 2
r = map_size / 2
playable: d <= r - 2
central inner border: d == r - 1
central outer border: d == r
```

The complete-storage inner rim remains `0x20`, exterior cells `0x10`, playable
empty land `0x8000`. Four top/bottom central tip cells are `0x30` for sub800
maps, matching native write order. The complete generated logic arrays match
the native160,200,400,500 examples exactly. The playable-cell count is
`(map_size - 4) * (map_size - 2) / 2`.
