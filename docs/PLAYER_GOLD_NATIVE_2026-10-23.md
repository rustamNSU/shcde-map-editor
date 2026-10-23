# Native player-gold initialization

File-only research, 2026-10-23. Pinned `CrusaderDE.dll` SHA256:
`fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2`.
Addresses are image RVAs, image base `0x180000000`. Ghidra used the existing
snapshot with `-readOnly -noanalysis`; it discarded in-memory analysis changes.
No game process, game/map writes, injection, or live gameplay test was used.

## Answer and field locations

The `.map` container can store player gold in section **2022**, but **a normal
new skirmish/custom multiplayer match clears those stored totals and initializes
starting resources from match setup**. Changing only the saved treasury field
does not set persistent custom starting gold for that path.

Section2022 is bound to DLL RVA `0x379ADD0`, with nine records of stride
`0x583C`. For numbered player `p` (1..8):

```text
resource_record = section2022[p * 0x583C : (p+1) * 0x583C]
total_gold      = Int32 at resource_record + 0x50C
incoming_gold   = UInt32 at resource_record + 0x4A8
```

The current SDK independently names these fields `r_TotalGoodsGold` and
`r_incomingGold` in `src/SHCDESE.BepInEx/Interop/GamePlayerResources.cs`.
They are different fields; startup seeds incoming resources after clearing totals.

## New match: exact destruction of map-stored gold

`DLL_LoadMapToPlay`, entry **`0x84AC0`**, calls skirmish handler **`0x94350`**
when native mode global `0x8EBA94 == 4`, passing its multiplayer-save argument.
The shared handler first loads the map through container loader `0x87D0`.

For the new-match branch (`multiplayerSave == 0`), the loop at **`0x957F0`**
then clears all 25 DWORD goods totals in every numbered player's resource
record. The loop starts with `RDI = DLL+0x37A0AE0` (`0x957D4`) and writes
`RDI-4` through `RDI+0x5F` inclusive (`0x957F0..0x95850`). It advances by
`0x583C` at `0x95916`, repeating for players1..8.

For player1 this is:

```text
record RVA              0x37A060C
cleared goods span      0x37A0ADC..0x37A0B3F = record+0x4D0..+0x533
total gold              0x37A0B18             = record+0x50C
```

The eight-byte store at **`0x95828`**, `[RDI+0x34] = 0`, directly clears
player1 gold and the preceding good. The same store clears each later player's gold.
This proves overwrite independently of subsequent economic processing.

## New match: replacement starting-gold source

The handler calls startup reset **`0xCF8D0`** at **`0x965E9`**. That reset calls
per-player initializer **`0xD1170`**, which loops over players1..8.

The initializer first copies the configured default starting goods. Its
instructions **`0xD1392..0xD1398`** copy global `DLL+0x37ED81C` to the player's
incoming-gold field. It then applies the skirmish starting-gold rules at
**`0xD14A3..0xD1552`**, when global `0x8574B90 != 0`:

```cpp
index = (starting_goods_level - 1) * 5 + (fairness - 1);
human_gold = Int32[DLL + 0x2D4DA0 + index * 8];
ai_gold    = Int32[DLL + 0x2D4DA4 + index * 8];
```

The two selected setup globals are `0x887ECA04` (starting goods level) and
`0x887ECAD0` (fairness). Native instructions take the selected human or AI
amount from this table, multiply it by a normally1 multiplier, and store the
result into **incoming_gold**, not directly `total_gold`.

The complete pinned table is below; each cell is `(human, AI)`, fairness1..5:

| Starting goods level | 1 | 2 | 3 | 4 | 5 |
|---:|---|---|---|---|---|
|1|(8000,2000)|(4000,2000)|(2000,2000)|(2000,4000)|(2000,8000)|
|2|(8000,2000)|(4000,2000)|(2000,2000)|(2000,4000)|(2000,8000)|
|3|(40000,3000)|(20000,7000)|(10000,10000)|(7000,20000)|(3000,40000)|
|4|(4000,500)|(2000,500)|(500,500)|(500,2000)|(500,4000)|

The human-side branch also forces incoming gold to0 when native setup flag
`0x887EE320 != 0` (`0xD1522..0xD1532`). A special scenario/advanced condition
sets the multiplier to3 (`0xD14B0..0xD14DA`); its exact predicates are
`(mode_0x3665F28 == 3 && value_0x3669040 == 1 && value_0x3669048 == 2)`
or nonzero `0x3666084`. The AI branch is selected by absent human lobby slot,
except the special player2/positive `0x366A090` case, which uses the human rule.

This report does not assign user-facing labels to every special native flag.
The later transfer of incoming gold into the treasury was not traced here;
the confirmed clear and initialization suffice to reject preservation of a
modified map treasury in a normal new match.

## Saved games and other modes

The same `0x94350` handler has an explicit **multiplayer-save early return**:
the original second argument is tested at **`0x95540`**; when nonzero it runs
the restore branch and jumps to the epilogue at **`0x955D5`**, before the goods
clear and the `0xD1170` initialization. Thus this saved-multiplayer branch must
not be described as having the new-match gold reset.

`DLL_LoadSaveGame` **`0x853F0`** separately loads the saved container with
`0x87D0`, then runs postload work. Its exported body does not call `0x94350`,
`0xCF8D0`, or `0xD1170`. Existing populated-save/resource-preservation
observations are consistent with that distinction. This is not a claim that
every postload helper or every game mode leaves every field untouched.

Campaign selection uses `0x87C40`; non-skirmish map start uses `0x8AE80`.
Those paths differ from the normal skirmish reset and were not fully audited
here. Preservation cannot be generalized to all scenario types.

## Evidence and reproduction

- Canonical exports: `output/gold-startup-2026-10-23/native/` contains C
  reconstructions and exact instruction listings for `skirmish_start`,
  `spawn_player_init`, `startup_reset`, `load_map_to_play`, `load_savegame`,
  `non_skirmish_start`, and two auxiliary helpers.
- Export request bounds: `research/gold_startup_functions.txt`; notably
  `0x94350..0x96FB0`, `0xD1170..0xD15F6`, `0xCF8D0..0xCFAC8`.
- `python -m research.audit_player_gold_startup` reads and hash-checks the
  pinned installed DLL and emits the native gold table plus calculated resource
  spans to `output/gold-startup-2026-10-23/native_gold_evidence.json`.
- Container binding is independently established in
  `docs/RUNTIME_FORMAT_AUDIT_2026-10-23.md`.

Only research files were added. The editor, packaged EXE, source maps, saves,
and installed game binaries were not changed.
