# Map editor review and new DLL-to-file evidence

Research date: 2026-10-23. Reviewed editor revision `15f5badfc2c434b1c85c2b9248728c8ef750f853`, its accumulated reference experiments, and current Script Extender revision `5908e1f12437deb7ef5f5b1dc2d64e301178fba3`. The September research used Extender revision `78a7595067fa297798720b56664d7df955aa7150`; source names and knowledge have changed since then.

This pass is a research/backend review before the next editor update. It adds reproducible static analysis, corrects two research-code mistakes and stale documentation, and restores missing local test fixtures. It does not add new GUI controls or rebuild the editor EXE. Original maps, saves and installed game files remain unchanged.

## 1. What the existing project does well

The editor has a working Python/PySide6 application, not just a format experiment. Its shared backend has a lossless container reader, explicit patch-based document model, transactions, undo/redo, atomic save replacement, templates, brush/mask/symmetry services, prefab building tools, vegetation and schematic previews. These are useful foundations to retain.

The strongest research practices are already present:

- Original reference bytes and hashes are archived, and unknown sections are preserved.
- Runtime offsets were checked against actual file records instead of copied blindly.
- The experiments distinguish a game load from a native editor resave.
- Populated saves revealed worker links, resources, dead records and retained movement that clean map templates could not show.
- The Ada comparison correctly records that repaired menu markers do not, by themselves, explain lord survival or navigation.

The main weakness is the gap between preserving a container correctly and constructing coherent new gameplay state. A file can pass CRC, bounds, no-op roundtrip and internal reference checks while containing stale derived terrain/path layers. Some older planning documents also describe features as unimplemented even though later source already implements them.

The container parser currently recognizes the observed97- and591-byte save-prefix extensions structurally and preserves them. This is more capable than the first September reports describe, but it does not establish support for arbitrary unseen prefix variants. The semantic backend's broad version>=200 condition also exceeds the evidence for fully understood layouts; the primary verified profile in this audit is version236.

## 2. New finding: the native section registry

The installed DLL has a descriptor table at **RVA `0x336B20`**. The save routine at **`0x52B0`** receives this table from `DLL_SaveSaveGame` at **`0x86F80`**. The load routine at **`0x87D0`** receives the same table from `DLL_LoadSaveGame` at **`0x853F0`**.

Each descriptor is 24 bytes:

```cpp
// Reconstruction of the pinned x64 DLL's descriptor storage.
struct SectionDescriptor {
    uint64_t dataAddress;       // +0x00: image VA of source/destination storage
    uint32_t saveDisabled;      // +0x08: default 0 includes this row in the save loop
    uint32_t decodedBytes;      // +0x0C
    uint16_t compressed;        // +0x10
    uint16_t sectionId;         // +0x12
    uint32_t reserved;          // +0x14: zero in the examined table
};
```

There are **212 descriptors plus a null-pointer terminator**: **175 enabled by default**, 37 disabled. Disabled rows include legacy/alternative layouts; they are not proof of unused memory. The same runtime storage can appear under several section IDs and lengths.

The save loop copies an enabled row's size, ID, compression choice and offset into its directory arrays, then copies or compresses the pointed-to bytes. The loader searches descriptor IDs to select destination storage and has explicit compatibility branches for older sections/versions. This gives a direct physical relationship between file sections and engine storage, independent of matching a few map values.

**Validation:** all 29 original reference maps and 9 additional DE maps/snapshots have version236 section IDs, decoded sizes and compression choices matching the enabled registry. All **38 files rebuild byte-exactly**. Three additional-map inputs retain an already known opaque1190 block; raw preservation still succeeds. Descriptor agreement does not mean every section was semantically decoded.

The full registry, including every unknown row and source hashes, is checked in as [native_section_registry_2026-10-23.json](../research/native_section_registry_2026-10-23.json). Reproduce extraction with [audit_native_sections.py](../research/audit_native_sections.py). No running process or game DLL execution is used.

## 3. Tile sections now bound to runtime arrays

The tile manager base is DLL RVA **`0x405EDB0`**. Below, the registry supplies the runtime storage address; current SDK headers supply the member label. A storage binding establishes identity and size, not every gameplay rule or a safe write recipe.

| File section | File element width | Runtime member / current interpretation | Storage RVA |
|---|---:|---|---|
| 3003 | 4 | `LogicLayer`: logical property flags | `0x48F71B0` |
| 3037 | 1 | `Logic2Layer`: surface flags | `0x4A312B0` |
| 3004 | 2 | `OrganismLayer`: vegetation slot references | `0x4ACE010` |
| 3012 | 2 | `StructureLayer`: building slot references | `0x4B6AA50` |
| 3010 | 2 | `ChimpLayer`: unit occupancy reference, not a complete unit list | `0x4C559B0` |
| 3049 | 1 | `StructureWasLayer`: stored building type in observed cells | `0x4C07490` |
| 3005 | 1 | `HeightLayer` | `0x4DDD350` |
| 3045 | 1 | `DefaultHeightLayer` | `0x4E2B870` |
| 3043 | 1 | `WallOwnerLayer` | `0x4E79D90` |
| 3006 | 1 | `ShowHiLayer`; complete display-height rule remains unknown | `0x4F167D0` |
| 3007 | 2 | `MiscDisplayLayer`; not a final texture ID | `0x4F64CF0` |
| 3008 | 2 | `RandomLayer`: per-cell variation; stored uncompressed | `0x485A770` |
| 3036 | 2 | `MacroLayer`; no basis to call it a generic graphics cache | `0x504FC50` |
| 3020 | 1 | `DamageLayer`; full use requires more tracing | `0x5001730` |
| 3021 | 2 | `PathConnectionLayer`: component/region labels | `0x50EC690` |
| 3030 | 1 | `PathLinkageLayer` / SDK `PathEdgeMaskGrid`: outgoing direction bits | `0x51890D0` |
| 3026 | 2 | `FlyLayer`: projectile occupancy references; decorative projectiles can also exist | `0x4CF23F0` |
| 3118 | 1 | SDK `Unknown00D30080`; storage identified, purpose still unknown | `0x4D8EE30` |
| 3028 | 1 | `AiZoneLayer` | `0x535EF90` |
| 3029 | 1 | `AiInfoLayer` | `0x53AD4B0` |
| 3101 | 1 | `AivBlockLayer` | `0x5CDAE70` |
| 3103 | 1 | `AiDangerLayer` | `0x53FB9D0` |
| 3104 | 1 | `AiProximityLayer` | `0x5449EF0` |

**Width exception:** section3009 points at **RVA `0x46848B0`**, the start of SDK `WallGfxLayer`, but persists **641600 bytes**, whereas that SDK member is declared as **320800 Int32s = 1283200 bytes**. This does not establish a one-UInt16-per-cell wall-graphics schema. Retain it as opaque auxiliary data until the discrepancy/representation is traced. A matching base pointer alone must not trigger a blanket field-width conversion.

No map painting or native graphics regeneration was implemented from these new labels.

## 4. Pathfinding is a persisted dependency of height edits

The original instruction function at **RVA `0xD86F0`** writes to the exact address registered as section3030. It reads logical flags, source/neighbor heights, building occupancy and special terrain/building conditions.

For the ordinary-ground case, the existing DLL instruction probes establish:

```text
direction bits: 0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW
ordinary edge height condition: abs(effective_neighbor_height - effective_here_height) <= 16
```

This condition alone is not the full function. Walls, stairs, elevated buildings, trees, water, gates and other flags have additional branches. An ordinary diagonal is not automatically removed merely because the adjacent cardinal heights fail. A generic pathfinder with unconditional corner cutting prevention would therefore differ from the inspected ordinary-ground builder.

The previous native probes cover 296 direction/height cases, plus a diagonal case with steep adjacent cardinal tiles. The new registry binds their runtime mask output to the persisted file section. See [height/path evidence in the Dashboard research](../../shc-dashboard/SHCDE_UNIT_PATHFINDING.md) and `shc-dashboard/artifacts/production-static/verify_tile_height.py`.

`HeightService.paint` currently changes3005 and3045, while retaining3030/3021 and the display dependencies. Building/tree removal also writes fixed reference-derived values such as3030=255 and3021=1. Such values are valid only in the source situations that established them. After changing heights, obstructions, gates or disconnected regions, there is no general guarantee that they describe the new map.

**Implication for Ada:** the old observation that a native resave changes123410 cells in3021 is now explicitly a change to the engine's saved component array. The 3030 changes are saved edge-mask changes. This strengthens the navigation interpretation, but does not isolate the cause of the reported startup deaths. Do not claim that correcting a single label or recomputing an ordinary-ground mask solves the entire case.

## 5. Section1171 contains each unit's packed route

The registry binds1171 to RVA **`0x7338278`**:

```text
unit manager base                  0x67E8400
+ native packed-path block offset  0x0B4FE78
= section1171 storage              0x7338278

10,000 units * 1,000 bytes = 10,000,000 bytes
```

Each byte stores two direction nibbles. Earlier step is the low nibble; directions0..7 have the order listed above. Capacity is **2000 tile transitions per unit**. Direction0 means north, not an end marker; the unit's stored length/cursor determines the active path span.

For unit slot `u` and path step `k`:

```python
byte = section1171[u * 1000 + k // 2]
direction = (byte >> (4 * (k % 2))) & 0xF
```

Relevant unit fields, relative to the start of the **file3015 record**:

| File offset | Type | Native runtime field |
|---|---|---|
| `0xF6` | UInt16 | `r_PathPlanStateBitFlags` (runtime `0xF2`) |
| `0xFA` | UInt16 | `r_CurrentPathPlanIndex` (runtime `0xF6`) |
| `0xFC` | UInt16 | `r_PathPlanLength` (runtime `0xF8`) |
| `0xF4` | UInt16 | Crowd delay / `r_PathPlanRelated1` (runtime `0xF0`) |
| `0x34A` | UInt16 | Actual slowdown / `r_CurrentSpeed2` (runtime `0x346`) |
| `0x34C` | UInt16 | Base slowdown / `r_CurrentSpeed` (runtime `0x348`) |
| `0x3C8` | UInt32 | `r_CurrentHealth` (runtime `0x3C4`) |

A new file-only cross-check found **737 path-state-2 unit records in the archived Leto save** and **20 in the orientation save**. All757 have cursor/length in the expected range and direction values0..7 across their declared path. Other records can retain stale plans; presence of a nonempty buffer alone does not prove movement or a living unit.

The Ada native-resave observation that1171 changes at offsets1000/2000/3000/4000 is now interpretable as changes at the starts of slots1/2/3/4's path buffers. A first byte17 decimal is0x11, encoding two NE directions if both fall inside the active declared path. It is not a universal initialization constant to copy into new maps.

Path and region arrays have different purposes. Section1171 is per-unit final route storage;3021/3030 describe map connectivity. Rebuilding one does not replace the others.

## 6. Entity offsets, additional arrays and allocator correction

The registry confirms physical source ranges for the already researched arrays:

| Section | Runtime storage RVA | Persisted extent | Observed runtime-to-file field displacement |
|---|---|---|---|
| 4013 | `0x64CCC0C` | 4000 * 812 building bytes | 0 for established fields |
| 1014 | `0x32DE464` | 4000 * 156 vegetation bytes | -12 for established semantic fields |
| 3015 | `0x67E8A58` | 10000 * 1168 unit bytes | +4 for established semantic fields |
| 2022 | `0x379ADD0` | 9 * `0x583C` player resource records | Cross-check per field; do not infer unrelated manager offsets |
| 1031 | `0x60AF684` | 200 * 516 connection/gate bytes | Already used by building prefabs; lifecycle incomplete |

These array starts need not equal the SDK's first runtime record address. For example, the unit file source starts at manager+0x658 while native unit records start at manager+0x65C. This explains the established +4 file offset difference. Vegetation is shifted in the opposite direction. Do not apply the displacement blindly to graphics headers or other record types.

Additional arrays can now be investigated through a real section binding:

- **2016:** tribe records,4500 *1672 bytes, source RVA`0x7CC6748`. **1016** stores the first1500 records from the **same source address**. The current SDK tribe array begins two bytes later, giving candidate file semantic offsets runtime+2: owner`0x04`, global ID`0x0C`, alive state`0x18`, leader unit`0x32`, unit count`0x34`. Leto has21 non-cleared/state2 tribe records under these offsets. Full membership/link invariants and write lifecycle are not established here. These are engine tribes, not necessarily the user's numbered hotkey groups.
- **2025:**6000 *232 projectile bytes, source RVA`0x2F7A694`. The native projectile allocator at`0x9BE80` uses232-byte records from manager base`0x2F7A680`; the serialized start is20 bytes later. Candidate file offsets are runtime-20: alive`0x28`, type`0x2A`, global ID`0x30`. Leto has71 state2 records under this interpretation, including arrow type1. Do not copy the unit +4 rule to projectiles.
- **1038:**4000 *32 auxiliary vegetation/organism descriptors, source RVA`0x3376A00`. Allocator`0x107290` writes its global ID at record+8, state+0x0C, type+0x10 and tile coordinates+0x12/+0x14. These are separate from the156-byte trees in1014. Their complete relation and lifecycle remain unfinished.

### Section1035 and section1047

**1035** is bound to RVA`0x3665F84`. Native allocation instructions assign its current value as a global ID and then increment it. This corroborates the existing next-ID interpretation. It is shared across kinds of objects, not a unit-slot count.

**1047** is bound to RVA`0x3665F10`. The scenario-loading helper at`0x87C40` writes `scenarioArgument - 1` there and uses it in scenario selection. **It is not a building allocation/high-water counter.** The later112-building reference already contradicted the old theory empirically; the DLL now supplies direct evidence.

Removed the incorrect `1047 >= 27` precondition from the old three-castle experiment script. Its direct empty-slot checks remain. The experimental generator was not run and no new game map was generated by it. The current GUI building writer already preserves1047.

## 7. Section1040 is deterministic RNG state

The descriptor binds1040 directly to **RVA`0x856A6D0`**, matching the current `GameRandomStruct` layout and the40016-byte file length:

| File offset | Type / count | Field |
|---|---|---|
| `0x00` | UInt16 | `CurrentValue2` |
| `0x02` | UInt16 | `CurrentValue` |
| `0x04` | UInt32 | `Seed` |
| `0x08` | 20000 UInt16s | `Values` |
| `0x9C48` | UInt32 | `NextIndex` |
| `0x9C4C` | UInt32 | `NextIndex2` |

This is not merely a map decoration/noise setting. It is distinct from the per-cell variation grid3008. Preserving a populated snapshot's RNG bytes and defining a new-match initialization policy are separate tasks; no RNG reset feature was added.

## 8. Tree resource correction and new meaning

The standing-tree resource gate previously researched in the DLL is signed `resourceState > 0`. The file displacement gives:

| File1014 record offset | Type | Meaning |
|---|---|---|
| `0x72` | UInt16 | Chopping health |
| `0x76` | UInt16 | Felled/extraction state: observed0 standing,1 felled,2 extracted |
| `0x78` | **Int16** | Remaining raw-log extraction loads |
| `0x80` | UInt32 | Growth stage |
| `0x84` | UInt32 | Growth progress |

`research/analyze_references.py` previously decoded+0x78 as UInt16. This was a concrete type error: raw0xFFFF would be reported as65535 instead of-1. It now reads Int16 and reports `felled_state` separately. A regression covers negative values, zero, positive values and felled state2.

An apple tree's type alone does not prevent woodcutting; positive resource, alive state2, growth stage<4 and a reachable approach can make it a woodcutter target. The picking/growth state is different from remaining timber loads. A later editor inspector can expose these fields with their native meanings; a blanket “cuttable” checkbox would conceal several conditions. See [woodcuttable vegetation research](../../shc-dashboard/SHCDE_WOODCUTTABLE_VEGETATION.md).

## 9. Remaining editor issues, ranked

| Priority | Issue | Concrete next work / acceptance check |
|---|---|---|
| 1 | Derived terrain and navigation coherence | Port/traverse the native update chain for edges, components and relevant display fields. Check height steps, diagonal cases, disconnected pockets, gates, walls and trees against native resaves; then test movement in game. Do not substitute a generic flood fill for the full rules. |
| 2 | Validation currently proves less than users need | Separate container validity, reference validity, derived-data coherence and actual gameplay validation. A `valid=true` structural result is not a proof that the exported map is ready to play. |
| 3 | Entity/reference lifecycle | Build a central registry for slots, global IDs, player/lord links, workers, groups and dependent objects. Keep clean-zero-slot allocation as the current restriction; do not recycle dead-but-linked records without the full cleanup rules. |
| 4 | Castle group geometry | Derive associated doorway/camp parts from validated group links and actual coordinates. Existing overlays/removal recognize the downward template; the orientation save proves different layouts with the same IDs. Stockpile is a separate subgroup. |
| 5 | Rich read-only inspector | Use the new registry to show section names/addresses/types, unit paths, tribe/projectile summaries and tree resources. Keep confidence and unknown fields visible; distinguish file offsets, runtime offsets and global vs slot IDs. |
| 6 | Version/profile handling | Use observed layouts and size signatures instead of treating every version>=200 as fully understood. Keep legacy container roundtrip distinct from DE semantic editing. Add future version migrations from evidence. |
| 7 | Remaining export/UI features | Embedded U3 filename update, precise native preview projection/artwork, additional building orientations and new brushes. These should follow the dependency work rather than hide it. |

The right first implementation is **terrain/navigation consistency plus diagnostics**, followed by richer inspection. New decorative tools can otherwise multiply the number of maps that serialize correctly but require a native editor repair.

This is a staged plan, not a claim that every priority must be finished before a useful next release. A read-only section/path inspector can ship earlier because it does not manufacture new simulation state.

## 10. Changes and validation in this review

- Added a bounded PE-file descriptor reader and an SDK-annotated registry snapshot. The reader requires the pinned DLL SHA256 and never executes it.
- Added a Ghidra read-only export script and a reproducible list of11 function/chunk ranges. The script verifies the Ghidra program hash before exporting C reconstructions and assembly. Earlier arbitrary labels were corrected after inspecting actual record strides:0x9BE80 is a projectile allocator,0x107290 an auxiliary vegetation-descriptor allocator.
- Checked38 DE reference/snapshot files against the registry and byte-exact rebuilds. Additional path checks cover757 path-state-2 records, with no cursor/length or direction-range failures.
- Corrected signed tree resources and the obsolete1047 generator guard; updated section status, readiness/context and research memory. No writer/UI behavior was expanded.
- Initial suite:96 tests, one failure and eight errors caused by missing `examples` inputs. The original sources still existed. `research/prepare_test_examples.py` restores five **hash-pinned copies** with exclusive creation and refuses changed/conflicting files; it rechecks source hashes. Copies are ignored by Git and are not bundled release inputs.
- After fixture restoration and the vegetation regression: **97 tests passed** in231.791 seconds. This includes existing backend and isolated Qt tests. The generator guard removal was subsequently syntax-checked; the writing experiment itself was not rerun.
- No game load, live save editing, game-process memory operation, network message, EXE rebuild or user-application shutdown was performed.

### Reproduction

```powershell
# File-only descriptor extraction + 29 archived reference checks:
.\.venv\Scripts\python.exe -m research.audit_native_sections

# Restore missing private fixtures from their original directory (never overwrite):
.\.venv\Scripts\python.exe -m research.prepare_test_examples --source '<original Maps directory>'
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Ghidra export uses the existing `StaticDamage` database and `-readOnly -noanalysis -scriptPath <this repo>/research -postScript MapFormatExport.java <output>/native <this repo>/research/map_format_functions.txt`. Exported C is decompiler reconstruction; consult the adjacent assembly for exact instructions. The read-only project discards in-memory analysis changes.

Evidence is under `output/runtime-audit-2026-10-23/`: registry,29-map check, nine-map extended check, three-snapshot route check,11 native function exports and test log. Test-copy source hashes are recorded in `output/test-fixture-provenance.json`.

Pinned installed DLL SHA256:

```text
fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2
```

All native addresses here are image RVAs, not raw file offsets or fixed loaded addresses. All per-record offsets are explicitly identified as file offsets or runtime offsets. Physical storage bindings, SDK labels, synthetic instruction tests and live gameplay observations remain distinct evidence levels.
