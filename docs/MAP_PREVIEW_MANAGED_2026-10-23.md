# Managed map-preview chain, 2026-10-23

Read-only research. The managed UI receives native-produced pixels. No Unity
screenshot/scene-capture step occurs in the traced map-save or preview chain.
Managed code alone does not establish the native pixel algorithm; do not infer
sprite rendering from `Texture2D`, `TextureSource`, or `Image` UI consumers.

## Sources and provenance

Source references below are relative to
`C:/repositories/shcde_reverse/ilspy/Assembly-CSharp/`, an existing decompile whose
`.csproj` references the installed Steam game's Managed directory.

The current installed `Assembly-CSharp.dll` is 3,693,056 bytes, SHA256
`BC8B6A395F01D48557DB413600C8DD8D1FDFD3ABDF97BFBBB68A3C56B04FD789`.
Script Extender's `deps/Assembly-CSharp-publicized.dll` differs: 3,691,008 bytes,
SHA256 `8B7431F072BCD76556D3D07E91B6890BC33F04C3050A74475AFB61C7CCA8A26A`.

`research/inspect_managed_preview.ps1` reads installed PE metadata/IL without
executing the assembly. Evidence is in
`output/preview-managed-2026-10-23/installed-assembly-preview.json`.
Run from this repository with PowerShell 7/.NET:

```powershell
pwsh -NoProfile -File research/inspect_managed_preview.ps1
```

## Native producers and ordinary save

| Source | Verified action |
|---|---|
| `CrusaderDE/HUD_IngameMenu.cs:937` | `SaveMapEditor`; line948 calls `SaveSaveGameOrMap(..., mapSave:true)` after setting the `.map` path and AI patrolling action |
| `EditorDirector.cs:885` | Sets map name, computes camera/rotation center; line895 calls `EngineInterface.SaveSaveGame`. It supplies no pixel/screenshot buffer |
| `EngineInterface.cs:6626` | Checks `SafeToSave`, locks, encodes UTF16 path; line6637 calls native `DLL_SaveSaveGame` |
| `EngineInterface.cs:3805` | `[DllImport("CrusaderDE")] DLL_SaveSaveGame(byte* path, int length, int screenCentreX, int screenCentreY, int realScreenCentreX, int realScreenCentreY, bool lockMap, bool tempLockOnly, bool mapSave)` |
| `EngineInterface.cs:6871` | `getSaveRadar`: allocates16 Int32s for8 keep-coordinate pairs plus160000 image bytes; line6881 calls `world_size = DLL_GetSaveRadar(dest, keeps)` |
| `EngineInterface.cs:3873` | `[DllImport("CrusaderDE")] int DLL_GetSaveRadar(byte* dest, int* keeps)` |

`CrusaderDE/HUD_LoadSaveRequester.cs:835` and
`CrusaderDE/MainViewModel.cs:38290` each define `updateSaveRadarTexture`.
They call `getSaveRadar` at843/38298, then feed its output to textures at861/38316.
World sizes160/300/500/700 select separate border UI overlays. The main-view-model
method returns the keep coordinates separately at38318.

## Embedded-thumbnail decode and texture consumers

`MapFileManager.cs:1767`, `GetRadarFromFile`, reads the first negative Int32,
the next positive preview-block length, and that block from file offset8.
Line1800 calls `EngineInterface.unpackSavedRadar`.

`EngineInterface.cs:6852` allocates160000 bytes, calls
`DLL_UnpackRadarToARGB` at6861, and returns its decoded output. Import at3861:
`[DllImport("CrusaderDE")] int DLL_UnpackRadarToARGB(byte* source, byte* dest)`.

`MapFileManager.GetRadarPreview` at1808 and `GetLoadSaveRadarPreview` at1820
both create `Texture2D(200,200,TextureFormat.BGRA32,mipChain:false)`, use point
filtering, upload `SetPixelData(bytes,0)`, and apply. They do not generate pixels.
The import's ARGB name is compatible with the explicitly BGRA byte consumer;
do not infer literal byte order only from the native export name.

The embedded format is **not PNG**. Independent project evidence in
`PREVIEW_EXPORT_2026-09-20.md` establishes the DCL-compressed block containing
512-byte little-endian RGB555 palette +40000 uint8 indices. The native decoder
converts this into200x200x4 BGRA bytes for Unity.

## PNG and custom previews are separate

`CrusaderDE/HUD_WorkshopUploader.cs:225-229` first native-saves the map, reads its
embedded preview back, then calls `GetRadarPreview(...).EncodeToPNG()` and writes
separate `Upload.png` for Steam. PNG is a derivative export after saving.

Script Extender's
`src/SHCDESE.BepInEx/ManagedHooks/MapFileManager_Hooks.cs:21` intercepts file
preview reads for archives. Lines31/47-59 load optional custom `preview.png` and
convert `GetPixels32()` RGBA to BGRA manually. This custom archive feature does
not establish the ordinary `.map` producer or change its indexed file format.

## Installed-assembly confirmation and limits

The direct PE inspection confirms imports from `CrusaderDE`:

| Import/method | Token or IL RVA |
|---|---:|
| `DLL_SaveSaveGame` | token `0x06000091` |
| `DLL_UnpackRadarToARGB` | token `0x0600009F` |
| `DLL_GetSaveRadar` | token `0x060000A2` |
| `SaveSaveGame` | IL RVA `0xC17C` |
| `unpackSavedRadar` | IL RVA `0xCA28` |
| `getSaveRadar` | IL RVA `0xCABC` |
| `MapFileManager.GetRadarPreview` | IL RVA `0x19124` |
| `MapFileManager.GetLoadSaveRadarPreview` | IL RVA `0x19184` |

The wrapper IL confirms160000-byte buffers,16 keep Int32s, the native call
tokens above, and texture constants200x200/format14(BGRA32).

Live minimap pixels are another native output: `EngineInterface.cs:3837/6783`
imports/calls `DLL_RunTick(...,byte* radarMap,...)`; `Director.cs:490` passes its
buffer to `GameMap.processTestMap`, which stores it at912;
`GameMap.ApplyRadarMap` at1609 uploads it. Keep this path distinct from the
200x200 save-preview API.

No `ScreenCapture`/`CaptureScreenshot` producer was found in the managed save
chain. `ReadPixels` appears in general `GPUTextureScaler`, outside this chain.
Native palette lookup, projection, object treatment, and compression must be
established from native code. No game/app/map/EXE changes or broad exports were
made during this investigation.
