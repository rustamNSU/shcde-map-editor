# Wall, tower, keep and gatehouse heights

Read-only native research,2026-10-23, pinned CrusaderDE.dll SHA256
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.
RVA addresses use image base`0x180000000`. No game/application code or EXE changed.

## Native surface-height table

The following values are **engine height units**, not map tiles. On ordinary
unmodified terrain, ground height is8. The third column evaluates the native
surface-height calculation at that ground height.

| Structure | Height above ground | Surface height on ground8 |
|---|---:|---:|
|Low wall|60|68|
|High wall|90|98|
|Crenellated wall, low-wall level|68|76|
|Crenellated wall, normal high level|98|106|
|Lookout tower, type74|296|304|
|Perimeter tower, type75|148|156|
|Defense tower, type76|180|188|
|Square tower, type77|192|200|
|Round tower, type78|192|200|
|Normal Crusader keep, type41|92|100|
|Small stone gatehouse, type46|128|136|
|Large stone gatehouse, type45|128|136|

Conceptually `surface_height = ground_height + structure_offset`, but the
storage and lookup path differs for walls, elevated buildings and gatehouses.
The gatehouse surface-query result is also not exactly its normal unit-Z sum;
see below before using this table as a projectile/physical-unit simulation.

## Ordinary walls and crenellation

Native wall placement **`0x6F230`** adds90 for mapper25(high wall),60 for
mapper46(low wall). The height is written into the **byte** current-height
grid, section3005. Base terrain is retained separately in3045. The ordinary
base8 reference values are98 and68. Walls on base80 have top170; on base130,
top220, as independently observed in the saved hill/stair reference.

Mapper26(`MAPPER_CRENAL`) sets flag`0x200` and calls **`0x5C0E0`**:

```cpp
// Four cardinal neighbors. A low wall is counted separately from a high wall.
useLowLevel = lowWallNeighbors > 0 && otherWallNeighbors == 0;
heightIncrement = useLowLevel ? 68 : 98;
```

It marks alternating cells with`0x400000` when x/y parity differs. The native
names `CrenelatedLow` and `CrenelatedHigh` describe parts/flags of crenellation;
they must not be interpreted as a separate68/98 height selector. Both parts
receive the selected level increment. The higher marker affects movement
eligibility separately. AI mapper35(`MAPPER_CRENAL2`) has a specialized+68 path.

Obstacle/cover helper **`0x6B530`** additionally uses+10 for the lower
crenellation part (`0x200`) or+20 for the alternating higher part (`0x400000`).
On base8, the high-level crenellated surface is106 and these decoded barrier
heights are116/126. At the low-wall level the surface is76 and barriers86/96.
The helper encodes height/flags in its return; these are decoded magnitudes,
not literal raw unsigned return values or measured sprite-pixel heights.

Usual wall properties are`0x100`; low wall adds`0x10000`; crenellation
adds`0x200` and may add`0x400000`. Native storage writes are byte-sized, so
extreme terrain elevations can wrap the wall-height byte instead of preserving
the unbounded arithmetic sum. The table describes ordinary non-overflow cases.

## Elevated buildings: why tower heights can exceed255

**`0xC07C0`** returns the additional building height by actual building type.
The complete switch is:

| Native type | Return |
|---:|---:|
|40 KeepOne|64|
|41 KeepTwo|92|
|42 KeepThree|190|
|45 GateMain,46 GateInner|128|
|69 SiegeTower structure|118|
|74 Lookout tower|296|
|75 Perimeter tower|148|
|76 Defense tower|180|
|77 Square tower,78 Round tower|192|
|Other types|0|

Only type41 is the verified normal Crusader starting keep in the bundled
prefab; the other keep-model returns are raw native switch entries, not proof
that every old keep model is constructible in current Crusader.

Unlike walls, the tower and keep reference footprints retain current/base
grid height8. Their roof/platform cells have elevated flag`0x10000000`.
Callers add the C07C0 result with wider arithmetic;296 is not truncated into a
single terrain byte. Native movement-height comparisons use these sums with
the usual16-unit tolerance, for example at`0x699D3..0x69A5F`.

The unit structure has two corresponding values:

```text
unit +0xB6: r_HeightElevation
unit +0xB8: additional signed height offset (SDK name N0000006A)
effective unit Z = signed16(B6) + signed16(B8)
```

**`0x184FD0`** normally assigns an elevated building's C07C0 result to B8
and its building-record ground height to B6. Special states/units can take
other branches. Projectile/position code consumes the B6+B8 sum; the terrain
height field alone does not describe a unit standing on a tower.

## Gatehouse: three different numbers

The small5×5 gatehouse is building46; the large7×7 gatehouse is45. Both native
reference footprints contain current3005=98 and base3045=8, with ordinary wall
properties0x100. These raw map values are not the full gatehouse platform height.

Surface query **`0x6B910`** explicitly treats types45/46 differently:

```cpp
if (buildingSlot == 0)
    return currentHeight[tile];
if (buildingType == 45 || buildingType == 46)
    return baseHeight[tile] + buildingHeight(buildingSlot);
return currentHeight[tile] + buildingHeight(buildingSlot);
```

Thus the gatehouse query gives8+128=**136**. Unit-height comparisons actually
consume this query, e.g`0x121429..0x12144B`, against B6+B8 with tolerance16.

However, ordinary gatehouse-roof units take the wall-with-structure branch of
**`0x184FD0`**, which assigns B8=40. Their normal B6 follows the raw wall-height
grid98 through **`0x19B260`**, giving normal unit Z **138**. The query target136
and the unit's138 are distinct native values. This report does not assign an
unverified physical explanation to the two-unit difference. Underpass/special
state branches and additional unit effects can change the offset.

For flat ground height G, in the ordinary state:

```text
gate raw cell height = G + 90
gate native surface query = G + 128
gate ordinary roof-unit Z = G + 90 + 40 = G + 130
```

## Evidence

- Existing native wall and hill/stair references:
  [WALLS_2026-09-19.md](WALLS_2026-09-19.md),
  [HILLS_STAIRS_2026-09-19.md](HILLS_STAIRS_2026-09-19.md).
- Current bundled building prefab arrays: `editor/assets/templates/buildings.json`;
  original hashes are recorded in [BUILDING_CATALOG_2026-10-23.md](BUILDING_CATALOG_2026-10-23.md).
- Native C/assembly exports:
  `output/navigation-update-2026-10-23/native/nav_building_height.*`,
  `output/wood-wall-2026-10-23/native/wood_native_6f230.*`,
  `output/wall-height-2026-10-23/native/height_native_5c0e0.*`,
  `height_native_6b910.*`, `height_native_184fd0.*`.
- `research/wood_wall_height_replay.py` executes the original C07C0,6B910,
  184FD0 and cover-height instructions in an isolated Unicorn emulator.
  All12 synthetic cases passed. Output:
  `output/wall-height-2026-10-23/native-height-replay.json`.

These are height calculations. They are not a complete ranged attack-range,
line-of-sight, cover or projectile-collision formula.
