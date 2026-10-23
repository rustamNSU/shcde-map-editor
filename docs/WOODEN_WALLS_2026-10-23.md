# Wooden-wall remnants in Crusader DE

Research date:2026-10-23. This is read-only research; no game files, map inputs,
application code or EXE were changed. DLL SHA256:
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.
Native locations below are RVAs from image base`0x180000000`.

## Result

The game retains wooden-wall names, GUI identifiers and a placement sound.
However, the normal `WOOD_WALL` route constructs Crusader's **low stone wall**.
It does not establish a second, hidden working wooden palisade. A separate
wooden-wall material, usable placement route and matching world graphics have
not been demonstrated.

| Identifier/data | Value | Verified current meaning |
|---|---:|---|
|`STRUCT_WOOD_WALL`|110|GUI/tool identifier used by the Low Wall button; not an ordinary building record type with an updater|
|`MAPPER_WOODWALL`|46 (`0x2E`)|Native low-wall construction path|
|`MAPPER_WALL`|25 (`0x19`)|Native ordinary high-wall construction path|
|`r_WoodwallAvailable`|Map rules+`0x288`, UInt16|Legacy-named availability field associated with that tool; changing it does not select a different wall material|
|`woodwall_placement`|Retained sound asset|Evidence of retained naming/audio, not proof of wooden world graphics|

## Native placement and payment

**`0x6F230`** is the native wall-building execution path. For newly built
ordinary segments it distinguishes mapper46 from mapper25:

```cpp
// Simplified relevant branch; this is not the whole placement function.
if (mapper == 46) {
    currentHeight += 60;
    properties |= 0x10000; // low wall
} else if (mapper == 25) {
    currentHeight += 90;
}
properties |= 0x100;       // wall
```

The AI wall builder **`0x6CB20`** independently handles mapper46 as height+60
and properties`0x10100`. Existing native reference maps give exactly:

| Wall | Properties3003 | Height above base | Top on base8 |
|---|---:|---:|---:|
|Low wall|`0x10100`|60|68|
|High wall|`0x100`|90|98|

Ordinary wall segments are stored in map grids, without one building-table
record per segment. The current editor already exposes these as **Low wall**
and **High wall**. See [the original wall reference analysis](WALLS_2026-09-19.md).

At the end of`0x6F230`, mapper46 contributes to `low_count`. Payment helper
**`0xC8CC0`**, in the ordinary charged gameplay path, computes:

```text
q = previous_remainder + 2 * high_count + low_count
stone_charge = floor(q / 4)
new_remainder = q & 3
```

Preview calls do not advance the accumulator. The helper calls resource removal
**`0xB7D80`** with **resource4 = STORED_STONE_BLOCKS**, directly visible at
`0xC8D44` and call`0xC8D5F`. Thus cumulative normal construction costs one stone
per four low-wall cells or two high-wall cells. This route does not charge wood.
Free-building/editor/special-mode branches are separate from this normal path.

The Ghidra C and assembly exports are in
`output/wood-wall-2026-10-23/native/wood_native_6f230.*`,
`wood_native_6cb20.*` and`wood_native_c8cc0.*`.

## Stock GUI and resources

The Extender checkout examined was
`5908e1f12437deb7ef5f5b1dc2d64e301178fba3`.

- `src/SHCDESE.BepInEx/Interop/EStructs.cs:231`: struct110.
- `Interop/Enums.cs:275`: mapper46, evaluated from enum assignments.
- `Detours/BulkBuildingDetours.cs:234–268`: describes low-wall stone costs and
  explicitly routes `MAPPER_WOODWALL` through `GetLowWallCostMultiplierInternal`.
- `deps/Override/Assets/GUI/XAMLResources/HUD_Main.xaml:268–282`: comment
  `wood wall / low wall`; `ButtonBuildWoodenWall` binds `STRUCT_WOOD_WALL` and
  tooltip016. The retained names are visible in source.
- The stock installed `Assets/Text/crusader.txt:132` resolves tooltip016 to
  **Low Wall**.

This was also checked directly in the stock game's serialized resources,
independently of the Extender override copy:

| Stock file | File offset | Data |
|---|---:|---|
|`..._Data/sharedassets1.assets`|`0x3662BB96`|`wood wall / low wall` comment|
|Same|`0x3662BBDC`|`ButtonBuildWoodenWall`, struct110 binding and tooltip016|
|`..._Data/resources.assets`|`0x33A7F2`|Sound configuration`fx\\woodwall_placement.wav`|
|Same|`0x3481F4`|AudioClip named`woodwall_placement`|

UI atlas keys C003/C004 remain the icons used by that low-wall button. Their
presence and the sound do not identify a separate world-rendering material.

## SDK updater-table pitfall

`BuildingFunctionsVTable.cs:148` declares a member named `WoodWallUpdate`.
That declaration must not be treated as proof of a native wooden-wall updater.

The real native dispatch call is at **`0xC64AD`**, through table
**`0x2DEAE0`**. At logical index110, the bytes decode to
`0x001E002100070020`, packed data rather than an executable pointer. The nearby
entries111–114 likewise contain data, not updater addresses. No real
`WoodWallUpdate` function is established by that SDK declaration. Virtual
GUI/tool enums and actual building-update-table entries are different domains.
Raw evidence is in`output/wood-wall-2026-10-23/native_audit.json`.

## Wooden gates are a separate remnant

Generic wood-gate building type47 does have a nontrivial native update function
at **`0xA5C80`**, handling gate state/navigation. That alone does not make it
constructible: the generic placement switch's type47 branch supplies no
constructor in the inspected path.

The stock-style HUD comments out the wooden-gate menu and directional buttons
(`HUD_Main.xaml:1072–1085`, `1783–1860`). The same commented markup occurs in
stock`sharedassets1.assets` at`0x366362FE` and`0x366411CE`. Stock text still has
Small/Large Wooden Gatehouse names. Generic struct47/mapper103 and directional
structs127–130/mappers140–143 remain in enums.

These are useful legacy research leads, not evidence that choosing a hidden
ID will produce a fully working wooden wall or wooden gate. Complete world
graphics coverage and a working stock construction experiment remain unverified.
