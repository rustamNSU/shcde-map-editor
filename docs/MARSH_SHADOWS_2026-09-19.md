# Marsh lettering and shadows

## Editor support (2026-09-21)

Marsh is available in the terrain palette and CLI (`material: "marsh"`). Uses
the reference tuple:3003=0x20008000,3037=0,3007=16, restricted to flat unoccupied
ground at height8. Painting another material over marsh removes the swamp flag.
Brushes, PNG/JSON masks, symmetry, undo and optional fixed variation are shared
with other terrain. Mask capture includes marsh. Schematic rendering uses muted
green; exact native edge/interior artwork is not simulated. No unrelated grids
or saved simulation state are imported from the marsh reference.

Read-only check by `research/check_marsh_shadows.py`; outputs in
`output/marsh-shadows-2026-09-19/`. Sword input is the original archived
`examples/1x1 - sword no lions.map`, legacy version170 (400-axis storage).
The zero-noise copy changes only1008, so all observations on other layers apply
to that copy as well. Reference marsh uses DE version236 (800-axis storage).

## Lettering

The decoded mask reproduces the central RY-L lettering and small outlined squares.
All334 marsh cells are within x165..236,y189..209. Every one has:

- logic1003 =0x20008000 (land|swamp);
- surface1037 =0: no oasis bit;
- height1005 =8;
- grids1006=0,1007=16,1009=0,1049=0;
- grid1036=1 (its exact meaning is not established).

The2589 cells of ref_08_march_400 have the exact same logic/surface/height tuple
and the same values in corresponding3006/3007/3009/3049. Thus no separate
marsh subtype was found in these fields. Noise and1036/3036 differ across maps;
this is not a controlled single-variable rendering comparison.

Count of cardinal marsh neighbors in lettering:326 cells have2,7 have3,1 has1,
none have4. In the wide reference:2426 have4,37 have3,105 have2,21 have1.
This strongly supports edge/interior-dependent graphics as the explanation for
the observed brush-width effect. Exact native sprite selection remains untraced.
The observation does not prove a universal 'one-cell swamp always looks like
oasis' rule.

Script Extender TileProperty.cs explicitly describes IsSwamp as passable but
unbuildable. TilePropertyMasks.cs includes it in the vegetation-placement
obstruction mask, but not in its basic unit-impassability mask. Hence visual
resemblance to oasis does not imply its placement/buildability properties.

## Shadows: evidence and unresolved mapping

Script Extender GameTileManagerView.cs has a runtime byte LuminesenceGrid whose
comment suggests shadows/light, explicitly with uncertainty. GameTile_Hooks.cs
hooks GameTile_SetTileColor and accepts a light argument; graphics contain
additional runtime layers. Neither source alone identifies a .map section.

We tested1006/3006 as a CANDIDATE, not an established shadow layer:

- All three isolated-tree references have3006 uniformly zero.
- The keep reference has only9 nonzero cells (value10), around x404..408,y398..402.
- Empty500 and reference marsh have none.
- Original Sword has1920 nonzero1006 cells, values8,10,18,64,72,255.

These findings do not establish this section as a complete saved shadow map.
Do not claim that its zero values mean trees have no rendered shadows. Runtime
generation, sprite alpha and other layers remain possibilities, not proven facts.
No wall-only controlled reference was tested here. Exact shadow generation and
file dependencies remain open.

The generated images are categorical masks with invented colors, not game
texture renders. In sword_center.png magenta=marsh, green=oasis.
