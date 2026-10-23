# Player gold in maps and new-game initialization

## Answer

For an ordinary **new multiplayer/skirmish match**, editing a player's stored
gold in the `.map` does not determine the starting treasury. Native startup
clears the saved resources and initializes starting gold from the match setup.
The current-treasury field and the starting-gold configuration are different.

This is research only. No map, game library, preview code or release EXE changed.

## Stored player state

The pinned native section registry maps section **2022** to runtime RVA
`0x379ADD0`. Its decoded size is 203,292 bytes: nine player records of 22,588
bytes (`0x583C`), including neutral slot 0.

| Field | Offset within each record | Storage |
|---|---:|---|
| Incoming gold | `0x4A8` | uint32 in the current SDK |
| Stored goods vector | `0x4D0` | 25 four-byte values |
| Current treasury, `r_TotalGoodsGold` | `0x50C` | signed int32, little endian |

For player ID `p`, the current treasury is at this **decoded-section** offset:

```python
gold = struct.unpack_from('<i', player_section_2022, p * 0x583C + 0x50C)[0]
```

This is not an absolute offset in the compressed `.map` file. The same field is
the one exposed by Script Extender's `GetGold`/`SetGold` API. Current SDK:
`src/SHCDESE.BepInEx/Interop/GamePlayerResources.cs:343`.

Read-only reference checks found zero treasury in every slot of both native
editor maps `2v2 Ada.map` and `etest_oasis_grid_3_castles_400_r.map`. Native
startup code, rather than those sample values alone, proves the reset behavior.
Renamed live-save references retain nonzero current treasury values; they are
snapshots, not proof those values survive a new multiplayer start.

## Normal new-match path

Managed startup applies multiplayer setup, loads the selected map and starts
the new match. The setup contains `starting_goods_level`, `fairness`, player/AI
slots and advanced options. It does not supply an arbitrary gold integer for
each player.

Native map initialization at RVA **`0x94350`** clears the saved goods vector for
players 1 through 8, including treasury `+0x50C`. The existing full decompile is
`output/castle-bounds-2026-10-23/native/map_load.c:928` onward.

Its first cleared address is P1's goods start:

```text
0x379ADD0 + 1*0x583C + 0x4D0 = 0x37A0ADC
P1 treasury = 0x379ADD0 + 1*0x583C + 0x50C = 0x37A0B18
```

The loop advances by `0x583C` and covers P1..P8. It is not a selective reset of
only null resources or a display cache.

The same native function has an earlier saved-multiplayer branch: when its
second argument (`bMultiplayerSave`) is nonzero, it returns before this clear
loop (`map_load.c:858`–`:869`). The reset conclusion applies to ordinary fresh
matches, not every invocation of this function.

Native starting-resource initialization at RVA **`0xD1170`** sets incoming gold
`+0x4A8` using a human/AI gold table at RVA **`0x2D4DA0`**:

```text
row = (starting_goods_level - 1) * 5 + (fairness - 1)
table_address = module + 0x2D4DA0 + row*8 + (is_AI ? 4 : 0)
```

The human no-gold option can force the human value to zero; special-mode
multipliers are separate. See [native evidence and limits](PLAYER_GOLD_NATIVE_2026-10-23.md)
for the exact initialization chain. Do not confuse incoming gold `+0x4A8` with
the current treasury `+0x50C` when inspecting an intermediate startup state.

The managed UI independently uses `GameData.starting_gold_table`, indexed by
goods level minus one, fairness minus one, and human/AI. For goods levels 1 and
2, fairness modes 1..5 display:

| Fairness index | Human gold | AI gold |
|---:|---:|---:|
| 1 | 8,000 | 2,000 |
| 2 | 4,000 | 2,000 |
| 3 | 2,000 | 2,000 |
| 4 | 2,000 | 4,000 |
| 5 | 2,000 | 8,000 |

These are the table values before special-mode modifiers. Source references:
`GameData.cs:1400`; `CrusaderDE/FRONT_Multiplayer.cs:6515` and `:8788`, under
`C:/repositories/shcde_reverse/ilspy/Assembly-CSharp/`.

## Saved games and scenarios

Loading an actual saved game uses `DLL_LoadSaveGame` at RVA `0x853F0`, which
restores section data through loader `0x87D0`. This is a different path from
starting a fresh multiplayer game on the map. The saved-multiplayer branch
inside `0x94350` also skips the new-match clear described above. A renamed save opened through
the normal new-match path is still subject to new-match initialization.
No modified save was tested in a running game during this research.

Scenario starting gold is a separate configuration feature. The managed editor
handles `scenario_start_goods[15]` through command 2004 and `special_start_gold`
through command 2006 (`MainViewModel.cs:39272`/`:39278`). This does not establish
a per-player gold override for ordinary multiplayer maps. The stock scenario
panel routes multiplayer maps to its message editor instead of the ordinary
scenario-starting-goods controls (`HUD_Scenario.cs:478`).

## Editor implication

A player-state inspector may accurately display stored treasury, but labeling
that field “starting gold” for multiplayer maps would be misleading. An
ordinary multiplayer map cannot force custom per-player starting treasury
merely by editing section 2022. Match setup governs the normal start amount.

## Provenance

Native DLL SHA256:
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.
Section binding: `research/native_section_registry_2026-10-23.json`, descriptor
2022. Additional startup evidence is under `output/gold-startup-2026-10-23`.
All addresses are module RVAs unless described as decoded-section offsets.
