# Память исследования — актуально 2026-09-19

## 2026-09-21: castle orientations

See docs/CASTLE_ORIENTATION_2026-09-21.md. Three groups, same keep41 and door
IDs71/73/72, camp55, stock10. Actual center-door offsets(+3,+7),(+3,-1),(-1,+3).
Keep generic access coords remain(+3,+7), so geometry and dependent grids must
determine effective passage. No standalone orientation flag established.
New observed save prefix591 bytes retained losslessly; source parser updated.

## 2026-09-20: Ada500 native-resave comparison

Subsequent repair: explicit exports regenerate missing500 lobby markers and use
three-cells-per-pixel preview scale. Shared editor/menu.py preserves valid native
markers and computes new ones (Ada exact; independent x rounding within1pixel).
Seven tests passed, including no gameplay-section changes. Navigation/lord
initialization remains unresolved; this is not a complete gameplay fix.

See docs/ADA_RESAVE_2026-09-20.md. GUI export lacks all U4 lobby markers despite
four castles and correct player count. Native supplies P1(40,126),P2(73,159),
P3(130,36),P4(163,69). Preview scaling is wrong500 (200square versus166square
native content). Four lords have150000HP both before/after; lookup tables and
group-root IDs unchanged. Native rebuilds123410 region cells and derived cliff/
neighbor grids with heights/surface/variation unchanged. Immediate-death cause
still unisolated; don't claim marker/preview repair alone guarantees playability.
Original hashes verified, no maps or EXE changed by this audit.

## 2026-09-20: castle regression audit

Preview-only implementation now complete in source: see docs/PREVIEW_EXPORT_2026-09-20.md.
Fresh schematic RGB555/palette thumbnail on every Save As; no-op serialize stays
lossless.23 preview/editor/UI tests passed. Read-only etest_height_00 rendering
shows all four castles; refreshing only preview preserves all numbered sections.
U3 filename and terrain connectivity intentionally unchanged per user scope.

Height resave follow-up: docs/HEIGHT_RESAVE_2026-09-20.md. etest_height_00 original
preview equals empty template; four menu markers/count already correct. Resave
updates preview and U3 filename; raw heights/surface/noise unchanged. Height130
connected regions rebuilt (2x5329 cells,742 edges0), plus logic/auxiliary masks.
Preview-only replacement verified in memory without altering numbered sections.
No general preview renderer or path regeneration implemented in this update.
Low-height warning below8 added independently of high warning;15 checks passed.

Later: tree tool from ref_13 and flat-plateau castle support implemented, tested,
and bundled in usual EXE together with castle fixes. Tree research in
docs/TREES_2026-09-20.md. User requests GUI-only etest_new_creation sword1v1;
creation blocked by Windows screenshot helper failure0x80004002, not completed.

Follow-up: repaired tool source now uses isolated ref_12 prefab, remaps group IDs,
maintains corroborated player initialization with removal/undo symmetry, and
removes linked dead lords. Validator catches stale root IDs. See subsequent repair
section in the audit report; original comparison files retained. Runtime survival
has not yet been verified; unknown global fields and reserved unit0 are untouched.

User reports dead lords after placing castles, including after native editor
resave. Compared ref_12_castle with bundled empty400 and current writer at the
same anchor. Lord is already present and has150000HP. Confirmed stale group-root
IDs at building file0x2a8 in all nine records; missing player initialization fields
also corroborated against older refs and the user-confirmed three-castle map.
Death mechanism remains unproven. Full evidence and repair requirements:
`docs/CASTLE_AUDIT_2026-09-20.md`; reproducible `research/audit_castle_reference.py`.
No application edits or EXE replacement in this audit. Original map unchanged.

## Задача и ограничения пользователя

- 2026-09-19: пользователь просит свести известное/неизвестное и оценить старт
  приложения с defaults для части неизвестных данных. Сводка и план:
  `docs/EDITOR_READINESS.md`. Рекомендация: начать viewer/document/Save As,
  новые карты создавать из проверенных шаблонов; неизвестные байты сохранять,
  не занулять. Поддержку каждой операции определять её зависимостями и проверками.
  Это план, а не уже созданный UI или доказательство безопасности новых кистей.
  При подготовке сводки существующие 14 unit tests прошли за 21.621 с.
- Конечная цель: автономный внешний редактор, способный создавать рабочие SHC DE карты.
- Сейчас исследовать формат; не исправлять и не менять карты пользователя.
- Script Extender предоставлен как источник изученных структур/ID, не для внедрения в игру.
- Использовать также исследования Rust Stats и Eco Simulator; не путать их модель/адреса с файлом.
- Референсы изготовлены со смешанной историей: иногда новая основа, иногда удаление/замена.
- Позднее пользователь явно разрешил создать новые etest_* карты с изменённым noise,
  выбрав ref_00_base_500 вместо отсутствующей empty400. Оригиналы по-прежнему не менять.
  Созданы 9 карт в игровой Maps и output/noise-tests-2026-09-19: контрольная original,
  константы 0,1,2,3,255,256,16384,32767. Изменена только секция3008 на123504 внутренних
  клетках обычной земли. Все прочие байты/граница сохранены; readback проверен.
  Скрипт research/make_noise_tests.py; manifest.json содержит SHA и параметры. Пользователь
  проверил0/32767/1 в игре: три скриншота показывают повторяющуюся землю при разном
  масштабе. Также сообщает необычный вид вновь нарисованных stone/iron/other surfaces.
  Это подтверждает влияние3008 на rendering и поддерживает общий per-cell variation,
  а не earth-only параметр. Формула выбора картинки и точные биты ещё неизвестны;
  теперь получено etest_noise_00000_textures.map:3008 побайтно идентичен исходной
  etest_noise_00000 (все641600 байт),0 изменённых noise-клеток. Все9479 клеток с
  изменёнными logic/surface сохраняют noise0. Stone545,iron545,sand545,earth&stones578.
  3036 меняется на97706 клетках, включая89863 с прежними материалом/высотами:
  причина не изолирована (load/edit/save), не объявлять доказанным graphics cache.
  research/check_painted_noise.py и output/noise-painted-2026-09-19 содержат сравнение и CSV.
- Составные здания учитывать как группы записей. У одного старого Einstein 3v3 есть лишний
  Hovel owner 1, slot 2, (398,153), 4×4; пользователь просил не исправлять.

## Где что лежит

- `maptool.py`: контейнер, DCL, CRC32, сохранение неизвестных блоков и хвоста.
- `semantics.py`: проверенные файловые поля, координаты, чтение объектов.
- `research/analyze_references.py`: воспроизводимый read-only сбор 29 карт, каталогов, гистограмм, diff.
- `research/reference_findings.py`: межсекционные/геометрические проверки текущего набора.
- `output/references-2026-09-19/`: оригинальные копии, SHA-256, 29 surveys, 28 pair diffs,
  findings, контактный лист, источники с commit и hash. Source integrity: 29/29 неизменны.
- `docs/REFERENCE_ANALYSIS_2026-09-19.md`: основной актуальный отчёт, все карты и пробелы.
- `docs/SCRIPT_EXTENDER_FINDINGS.md`: исторический первый анализ, offsets в разделе 4 устарели!

## Установленные факты

- Leto editor resave: docs/LETO_EDITOR_RESAVE_2026-09-19.md,
  output/leto-resave-2026-09-19, research/check_leto_resave.py.40 sections changed/135 identical.
  Buildings638 and237 reciprocal worker assignments preserved; records1460→1240.
  All220 removed records previously state2 but HP candidate+3C8=0 and percentage
  +2D4=0; strongly supports dead-record cleanup. No new unit gids;772 surviving
  current tile IDs changed. Do not call active_count living units. P2/P3 gold
  candidates5997→6058/1784→1852; physical inventories still match player totals.
  Same97-byte save prefix survives; U4+04 1→0 meaning unknown. Surface/noise/base
  height unchanged; current height(417,487)8→0. Editor session evolves simulation,
  not a serialization-only control. Both sources read-only/hashed/roundtrip verified.

- Save follow-up: `Maps/leto vs fbi 10.map` and `Saves/leto vs fbi 10 .msv`
  are byte-identical SHA256 40d3cc85bcadc434028c7e10928ecd455d01f437d068fb6e35f61e382349a5d9.
  New 97-byte length-prefixed block before ud/directory; now preserved by MapFile.
  Seven related saves decode/roundtrip, nine inputs archived and unchanged.
  Target:638 buildings/1460 units, all primary coordinate triples match; unit grid
  references only502 distinct slots.237 reciprocal worker links,1443 across7 saves:
  building4013 +19E/+1A0/+1A2 u16 and +1A4 u32 candidate -> unit slot;
  worker3015 +338 u16 building slot/+368 u32 building gid. Applies to checked workers,
  not arbitrary units. Player2022 goods vector+4D0 matches storage-building vector
  +120 (types10/19/11) for all23 non-null/non-gold goods across7 saves.
  Gold int32 candidate+50C: P1/P4=2000,P2=5997,P3=1784; no game UI confirmation yet.
  Movement candidates target C8/CA/D8,previous CC/CE/DC,next E0/E2/E4;
  matches1433/1458/1458 of1460, with explicit null/state-dependent exceptions.
  Details docs/SAVEGAME_LETO_2026-09-19.md; research/analyze_savegame.py and
  output/leto-save-2026-09-19 (JSON/CSV/snapshots).18 tests pass; original saves/maps
  untouched. No generic resource/order writer or save-to-clean-map conversion proven.

- Three-castle map works per user, but generator retained the source two-player
  menu prefix and preview. Editor `_r` fixes it: U2 payload+0x18 count 2→3;
  U4 payload+0x10 has eight uint32 x/y marker pairs, absent=0xFFFFFFFF each.
  P1 (33,169)→(98,98), P2 (176,22)→(156,18), P3 absent→(176,38).
  U4+0x50 map size400. Markers are separate from game coordinates and raster.
  Empirical400 KeepTwo projection ((x-y+197)//2,(x+y-598)//2) verified23 keeps;
  NOT a universal formula for500. Preview512-byte RGB555 palette+200×200 indices;
  102 palettebytes and30131 indices changed.3037/3008/3005/3045/1035/1190/1191
  unchanged;27 buildings retain core fields.1051 is NOT count (2→1).
  Added MapFile.menu_metadata(),research/check_menu_resave.py; docs/MENU_METADATA_2026-09-19.md.
  output/three-castle-resave holds diff,images,hashes. Future generator must also
  update prefix+preview; this comparison did not edit game maps.

- Все 29 refs: version 236, capacity 200, sections 175, все compressed CRC/размеры верны;
  byte-exact rebuild. 45 секций варьируются, 130 постоянны (не значит «не используются»).
- 320800 packed tiles в ромбе 800 строк. Внутренняя маска без border bits:
  сторона S−4, количество (S−4)(S−2)/2; точное совпадение на всех 29 размера160/200/400/500.
- 3003 uint32 logic; 3037 byte surface; 3005 current height; 3045 base height.
- Surface: scrub1, earth+stones2, mid plateau4, high plateau8, oasis16, beach32, sand64, thick scrub128.
- Logic примеры: earth0x8000, rocks0x8080, stone0x28000, iron0x88000,
  sea1, river0x100000, ford0x200000, marsh0x20008000, pitch0xA0008000.
- Flat height8, tested mid80/high130. River inherits 581 zero base-height tiles from beach;
  don't invent universal rules from that mixed-history observation.
- File trees 1014 stride156: state44,type46,gid4C,world5C/5E,tileXY62/64,tileID68 (hex).
  Runtime SE equivalent semantic fields are +0xC; not blanket translation for graphics.
  Desert refs: olive1,palm2,coconut3 (SE tree names differ). All3 coordinates and refs verified.
- File units 3015 stride1168: state8C,type8E,gid98,owner80,controller96byte,
  tileXY C4/C6,tileID D4. Runtime semantic fields are -4; don't generalize to all fields.
  Slot0 contains scratch/reserved copy; exclude it from placed units. Both castle refs have
  one lord type55 at slot1; eight lords in each Einstein now decode with matching references.
- File buildings4013 stride812: stateD0,typeD2,ownerD6,gidD8,worldE8/EA,
  tileXY EE/F0,tileID F4,sideF8,access FE/100. File anchor differs from Stats anchor by D0.
- Starting complex: 41 at(0,0)7×7;71(2,7),73(3,7),72(4,7)1×1;
  55(0,8)7×7; four10 at(7,2),(10,2),(7,5),(10,5)2×2. Total9 records/117 reference cells.
  Eco Simulator stockpile pattern confirmed. No generic group-ID field established.
- 2022:9*0x583C player entries. Links94→keep1,BC→stockpile6,1D4→campground5.
  Runtime name KeepDoorId at1D4 misleading for samples: points to type55, not type73.
- Holes sample:9 objects type104/STRUCT_POND, six6×6+three9×9, total459 occupied cells.
- DE custom description: bytes after compressed preview + uint32 byte length; legacy
  1000-byte Description unchanged. ASCII21 proved; Cyrillic encoding untested.
- Pure resave changes1017,1023,1024,1040,1046,1052,1091,1096,1126,3934.
  Palette unused bytes can change while rendered preview stays identical.

## Не делать неверных выводов

- SUPERSEDED pending request (completed below): map400, P1castlecenter,P2/P3 spaced in corner(s),
  oasis grid1-cell lines pitch5 leaving4x4 earth interiors. Asked geometry scope
  clarification (onecorner vs separate; fullgrid assumed). Castle relocation/
  creation not completed: discovered extra embedded footprint tile IDs in building
  records and unit target/previous/cache coords, plus player lord tables1190/1191.
  Cannot simply change primaryxy. Requested user-created ref_grid_castles_400
  with desired3 castles so their interlinked state can remain intact. Prepared
  research/make_oasis_grid.py CLI(source,destination,archive),requires3 keeps owners1/2/3,
  changes ONLY3037 on plain ground to16 where x%5==0 or y%5==0; footprints
  excluded. No output map created yet, awaiting source/layout answer.

- User rejected asking them to place castles; implemented template relocation and
  cloning. Created Maps/etest_oasis_grid_3_castles_400.map, P1keep397397,
  P2keep375260,P3keep415260; full oasis grid pitch5/width1,4x4 earth,footprints
  retained. research/make_three_castle_grid.py infers positions from paired sourcecomplexes,
  remaps building/unit/player coords, embedded IDs, colors, global IDs, lord
  tables1190/1191,counter1035.27parts+3lords,117cells/player,all static refs pass.
  Source-specific allocator assumption1047already27; user confirmed game works.
  Menu metadata/preview were stale; editor resave comparison is documented above.
  docs/THREE_CASTLE_GRID_2026-09-19.md; output/three-castle-oasis-grid/manifest.json.

- User built walls on high strips in-game; some become unexpectedly short.
  Screenshot codex-clipboard-b208e17b-cb3b-4f9d-bd9a-c6e83d19a447.png shows tall
  wall runs followed by low segments. Consistent with uint8 wrap of top height,
  not numerically proven without saved after-build cell values. Candidate high
  wall formula(base+90)%256:base166→0,248→82,252→86. Plain integer sum<=255
  would imply base<=165 for90-height wall, but not validated as universal safe
  construction rule. Do not report screenshot as proof of exact arithmetic.

- User wanted castles near height strips for building experiments. Created
  etest_height_steps_near_castles.map from original2-castlebase: kept castles intact,
  placed a full4-strip set near each. X365/385/405/425 steps4/8/12/16, tops252/248.
  P1 ground y523 ascending toward decreasingy;P2 groundy269 toward increasingy.
  252 raisedcells, only3005/3045 changed; no entity overlap. Archive/manifest
  output/height-steps-near-castles/. No assertion all towers fit on one-cell strips
  or construction range checks pass; game testing pending.255 is cellfield cap,
  not proven combined terrain+structure/render height limit.

- User requested thin terrain strips steps4/8/12/16 to aroundheight500. Explained
  uint8 height limit255; created feasible maximal test instead, no wraparound:
  etest_height_max_steps_04_08_12_16_castles.map from original2-castlebase.
  x355/385/415/445 respectively,ground starty430,ascending toward decreasingy;
  tops252/248/248/248,steps61/30/20/15. Only3005/3045 changed. Archive/manifest
  output/height-max-steps-2026-09-19.255 is storage max,not established safe engine
  terrain max. No claimed workaround for500. User tests direct-game loading.

- User direct-game strip results:can climb entirestrip16, beyond16 cannot take
  first raised step;black/glitched cells start in some cells ofstrip19. Values:
  d16 first24/top120;d17 first25/top127;d18 first26/top134;d19 first27/top141.
  Supports climb delta16 in tested context, NOT absolute height cap. Black cells
  confounded by top height,gradient,lateral cliffs and unchanged derived layers.
  Do not declare130/141 maximum terrain height; exact black positions unknown.
  docs/HEIGHT_STEPS_GAME_RESULTS_2026-09-19.md.

- User reports direct-game disc plateau has abrupt height edge WITHOUT rocks,
  whereas editor makes rock boundary. Supports editor-specific preprocessing;
  gameplay cell/path state still not inspected. Repeated requested strip test:
  Maps/etest_height_steps_01_30_castles.map from untouched ref_00_base_400_castles,
 30 strips at x310+6*(d-1),y396..403;heights8+7d down to8,d1..30. Only3005/3045,
 210 raised cells, castles/logic/surface/noise/regions unchanged. Archive and exact
 coordinates output/height-steps-castles-2026-09-19/manifest.json. Direct-game
 movement test pending; watch for bypass paths around one-cell strips.

- Direct-game experiment: user supplied ref_00_base_400_castles (two keeps P1 at
 403,534;P2 at399,243) and requested center plateau without editor preprocessing.
 Created Maps/etest_disc_plato_castles.map from it: only3005+3045 center50x50
 x/y375..424 changed8→130, same method as original disc test. All other section
 raw bytes preserved, including flags/surfaces/regions and both castles; no
 center object overlap. Archive+hashes output/height-castles-2026-09-19/manifest.json.
 User will launch directly in game; result pending. No editor/game launched by agent.

- No-brush etest_disc_plato_resave compared:3037 stays0 byte-identical; heights
  andnoise also unchanged. So load/save does NOT universally turnheight130 into
  surface8. Six grids autochange:3003 capinterior2304→0/perimeter196→0x80;
  3021 capinterior→region2/perimeter→0;3006 99cells→122;3007 891;3030 588;
  3036 965 all outsidecap. Separates derived-state rebuilding from brush, but
  not load vs save timing; disc control not identical geometry to smoothrepaint.
  docs/DISC_RESAVE_2026-09-19.md + output/disc-resave-comparison/.

- Smooth earth repaint comparison: docs/SMOOTH_EARTH_COMPARISON_2026-09-19.md.
  etest_smooth_plato_fix_to_earth vs generated:3005/3045/noise unchanged.3037
  center2500 cells0→8 atz130;154 slopecells0→4 atz80. So3037 is NOT a final
  texture ID and0 is not the complete visual definition of earth; elevation
  markers included.3003 changes26596,3006 13359,3007 13298,3036 5769 cells.
  Cannot attribute all to brush: first load/reconstruction/save confounded.
  No no-brush resave of same original yet.3036=1 NOT proven to mean earth.

- User authorized height experiments from new ref_00_base_400. research/make_height_tests.py
  created etest_disc_plato (50x50 x/y375..424,z130), etest_smooth_plato (same cap,
  drop2 per ring,61 rings to8), etest_height_steps_01_30 (d1..30 at x310+6*(d-1),
  y396..403,8+7d down to8). Game Maps+output/height-tests-2026-09-19.
  ONLY3005/3045 changed; earth/logic/noise/3006/connectivity preserved. These test
  runtime reconstruction; don't infer universal step threshold from cached region
  labels or a unit bypassing thin strip. Details docs/HEIGHT_TESTS_2026-09-19.md.
  User sees plateau-like center; live disc file checked byte-identical to generated,
  all2500 center surface3037=0/logic0x8000/heights130. Builtin ref05 surface8,
  sand flag64 distinct. Runtime appearance dependence suspected, exact rule unknown;
  no saved post-earth-repaint change available in disc file at this check.

- ref12 hills/stairs: see docs/HILLS_STAIRS_2026-09-19.md and research/check_hills_stairs.py.
  Stairs are logic0x900 wall-grid cells, no building records.5 steps from wall98,
  3 from68,13 from220, decrements16. Elevated wall(424,472):base130,top220,3006=212;
  isolated(405,485):base80,top170,3006=162. This DISPROVES universal3006=top-base.
  Natural slopes also have nonzero3006 with current=base. Exact formula unknown.
  All262 ImpassableEdge0x80 tiles region3021=0; isolated wall region2; other
  interior region1 including smoothed raised terrain and stairs. Saved labels
  support connectivity, not a live pathfinding/buildability guarantee. Post-wall
  demolition residual state not supplied; cannot attribute rebuild failure exactly.

- ref_11_walls_400 inspected:182 wall cells; left rectangle74 x243..263/y381..398,
  center100 x404/y375..474, right8 x551..553/y411..413. Owner3043=0/5/0 ->P1/P6/P1,
  corroborated by SE UI WallOwnerGrid+1. High walls logic0x100,height98,base8,3006=90;
  small right low wall logic0x10100,height68,base8,3006=60. 3006 zero off walls,
  equals height-base on all182: NOT a complete shadow mask. No building records
  or3012 refs. 3021 distinguishes enclosed304-cell and1-cell interiors.
  See docs/WALLS_2026-09-19.md, research/check_walls.py, output/walls-2026-09-19.

- Sword RY-L title/squares:334 marsh cells x165..236,y189..209, logic0x20008000,
  surface0,height8. Same tuple as2589 reference marsh cells; no special subtype
  found. Lettering has0 cells with4 cardinal marsh neighbors; wide reference2426.
  Edge-dependent rendering strongly suggested, exact sprite rule unproven.
  Docs MARSH_SHADOWS_2026-09-19.md; research/check_marsh_shadows.py outputs topology/masks.
  Shadows: runtime LuminesenceGrid exists but file mapping NOT proven. Candidate
  3006 zero on all3 isolated tree refs; keep only9 nonzero cells. Do not call3006
  a confirmed complete shadow map. Need renderer/native mapping research.

- Texture follow-up: see docs/TEXTURE_ANALYSIS_2026-09-19.md and research/analyze_textures.py.
  3008 is uint16[320800], uncompressed, strong candidate for runtime RandomNoise,
  not a proven loader mapping. Empty500 interior: 14974 unique values despite
  uniform material/height. Entire 3008 equal in iron/earth&stones/sand refs;
  also stable base500/resave/ref02. Across29 there are8 hash groups. Values are
  NOT image IDs or texture counts. 3036 has437 values on empty500, still unknown.
  Exact noise-to-GFX/atlas mapping and actual rendered texture variants unproven.

- Не считать runtime struct размер/смещения автоматически файловыми.
- Не считать ID0 placed entity, числа объекты = логические здания, границу square=diamond.
- Не менять только один известный bit и объявлять карту рабочей: производные слои
  3006/3007/3009/3021/3030/3036, ссылки, free lists и другие секции ещё не полностью известны.
- Не называть global ID индексом слота; ссылки клеток — слоты, а global ID другой счётчик.
- Не переносить на весь формат/все биомы имя type104 Pond или generic tree enum.

## Достаточность

Достаточно для продолжения чтения/просмотрщика и подтверждённой модели.
Недостаточно для полного формата и безопасного произвольного создания/удаления.
Дальше нужны адресные цепочки: empty400/resave; archerP1/P8/pair/delete;
hovel/add/delete; stockpile/add extension/delete; Unicode description. Не просить повторять всю пачку.

## 2026-09-20 — first desktop editor and shared headless backend

Implementation authorized after GUI review. See docs/APP.md and editor/.
New 400/500 maps use immutable hash-checked bundled reference bytes. Flat 2D
square-cell canvas, actual diamond playable boundary, brush/selection, undo/redo,
Roaming masks, read-only entity/height inspection and exclusive Save As work.
CLI JSON recipes and Python API share the GUI's domain services; transactions roll
back atomically. No source maps were modified. Experimental stone/iron explicitly
require opt-in; derived fields and game behavior still need in-game validation.
Preview/name updates, general entity editing, castle construction overlay and 3D
remain unimplemented. Empty templates do not contain playable starting castles.

Verification: all 26 unittest tests pass. Native Qt diagnostic tests painting,
selection, undo/redo, mask storage, export/readback and template no-op identity.
Final PyInstaller single-file Windows x64 EXE is 69,701,236 bytes. Copied only EXE
to a fresh temporary folder, restricted PATH to Windows/System32 and Windows,
then successfully ran both packaged GUI diagnostic and CLI 500-map export
(exit 0 each). This was this host, not a clean VM. The 500 output equals bundled
reference SHA-256 cea477bcb5416503aec888badbc44caf71253683998cf4337e401237662b2fa9.
Evidence: output/portable-diagnostic and output/portable-cli.json.
Artifact: dist/SHCDEMapEditor.exe, hash: dist/SHA256SUMS.txt.
No GitHub release was published.

## 2026-09-20 — castle display correction

Castle footprint now colors the 7x7 keep, three doorway cells, and 7x7 camp
(101 cells) using owner color, excluding stockpiles. Middle doorway type73 is
the overlay center. Matched five-part reference geometry in existing castle maps.
User supplied 141x141 area for 400 maps (70 cells each side of entrance); requested
same provisional area on 500 pending their game test. Size rules kept separately.
Palette: stats repo src/engine/enums.rs PlayerColor; exact UI swatches from
ui/app.slint: red, orange, yellow, blue, black, violet, sky blue, green for1..8.
Opacity defaults25%, configurable with area visibility in View layers; settings
created on first GUI start in APPDATA/SHCDEMapEditor/settings.json. Solid castle
footprints stay visible when area overlay hidden. This changes display only.
Tests verify101-cell footprint,141-cell bounds, center, blending, stockpile
exclusion and persistence. Current main EXE was locked by running user session;
new executable built separately in dist/castle-update to avoid interrupting it.

## 2026-09-20 — recent maps

Toolbar Recent maps dialog reopens full paths. Roaming/SHCDEMapEditor/recent-files.json
(version1, files array) is created on first GUI startup. Successful GUI opens
(including recent reopen) and Save As record an absolute path, deduplicate and
move it to front, cap at50. Unsaved templates and failed operations do not record.
Missing recent files report an error and preserve current document. Recent opens
use the same unsaved-changes protection as normal open. Backend: editor/recent.py.
Verified cap/order/dedup/reload/corrupt recovery, plus actual asynchronous GUI open,
Save As and reopen callbacks with isolated temporary history. Main EXE updates
in place only; never create alternate release folders if user has it open.

## 2026-09-20 — implemented reviewed UI refactor

Visible tool/shape buttons and eight named terrain swatches replace hidden lists.
Custom masks use thumbnails, rotation buttons and mirror. Size −/+ changes one
cell; editable input and slider support1..400/500 with minimum1. Masks retain
intrinsic dimensions. Shared EditorState and extracted Qt panels separate view
controls from domain mutations. Action registration feeds tooltips and modeless
Help > Hotkeys; canvas shortcuts avoid text/numeric fields. Settings restores
brush/material/mask transforms and view choices, falls back for missing masks,
and supports reset without deleting maps/masks/recent files. Resource opt-in is
not silently restored. Selection Clear/Esc and optional stroke/stamp clipping
implemented; later eyedropper/shape/flood tools remain follow-ups.

Geometry uses row-wise batched sweep unions matching discrete interpolation;
raster previews avoid per-cell painter loops. A500-cell long diagonal sweep
measured ~16ms on this host (geometry only). Existing lossless I/O contracts,
400/500 references, recent files and original maps preserved.

Verification: full34-test suite passed; subsequent focused4 Qt tests passed after
shortcut assertions. Source packaged diagnostic checks direct size typing250,
−/+, visible palette, tool key, Hotkeys window and prior paint/undo/export tests.
Native renders reviewed at1000x700,1280x800,1440x940 and150% Qt scale; sidepanels
scroll for lower content on smaller windows. Evidence output/refactor-review,
output/refactor-final-source. Main EXE rebuilt in place after checking not open.

## 2026-09-20 — 500-map wall-building overlay extent

User reports castle wall-building area on size500 extends10 additional cells on
each side compared with size400, for161x161 total. Updated CASTLE_AREA_RADIUS
from500:70 to500:80;400 stays70 (141x141). Center stays the middle doorway.
Supersedes the earlier provisional equal radius. This is user-reported evidence,
not an independently decoded engine rule. Tooltip/About/docs updated. Focused
render tests pass: centered 400/500 extents, exact tinted area counts excluding
solid101-cell castle, alpha blend, and cells just outside500 bounds remain unchanged.
