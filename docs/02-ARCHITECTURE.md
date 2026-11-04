# 02. Архитектура

ADR-0035 makes partial discovery explicit for the GUI while keeping strict
core/developer discovery as the default. Inventory issues carry bounded source
context, participate in fingerprints and block unavailable selected sources or
dependencies. A separate non-installable diagnostic envelope supports details
and export before any package plan exists. Row reconciliation and control
availability consume that state; native approval and transaction boundaries do
not change. See [ADR-0035](adr/0035-partial-inventory-diagnostics-and-ux-controls.md).

ADR-0032 promotes the reviewed SDK 0.8.1 provider, bundled binary and dependency
restore pin together. Preserve earlier reviewed hashes only as previous
versions for supported upgrades/source recognition; they do not override the
chosen provider. Separate source-package runtime diagnostics from installed
loader approval. Native approval, source integrity and transactional recovery
remain distinct from resource merge policy. See
[ADR-0032](adr/0032-reviewed-sdk-provider-synchronization.md).

ADR-0031 separates streamed discovery from materialized selected inputs.
Resource snapshots retain paths, byte sizes, type headers and SHA-256 rather
than whole unchecked mod contents. Default resource bounds are 512 MiB/file,
16 GiB/discovery, and 1 GiB each for selected input and generated output.
Text-processing inputs retain 16 MiB/file, including originals; indexing a
larger text file does not authorize Git/Lua/XML/JSON processing of it.
Metadata/configuration retain separate smaller bounds. Deferred reads recheck
the snapshot's size/hash through the same safe regular-file boundary. Reports
do not load content, and existing schemas/hashes keep their meaning. The
16/256 MiB values in the historical prototype section below are superseded by
[ADR-0031](adr/0031-streamed-resource-discovery-and-budgets.md).

ADR-0030 replaces ordinary menu-resource delivery with a generic reviewed SDK
screen extension. Stage `content/cc2x/screen_extensions.json` (schema 1) pointing
from `scripts/screen_menu_main.lua` to owned `cc2x/ui/modloader_menu.lua`.
The SDK executes it after the matching stock screen and before `begin()`, even
when main-menu resource overlays are disabled. New provenance uses
`sdk-screen-extension-v4`; historical policies remain readable. No vanilla or
author files are edited. Final Windows managed-menu acceptance is recorded in
[menu verification](verification/main-menu-v4.md); wider runtime gates remain separate.
See [ADR-0030](adr/0030-sdk-screen-extension-delivery.md).

ADR-0029 defines the owned `managed_menu` policy behavior with a
noninteractive CC2 ModLoader header and selected source names above the main
menu's first ordinary header, once per frame. Normalize control characters,
bound the name line to 140 Unicode characters and escape it as a Lua literal.
Keep ADR-0028's disabled localized Mods entry, rejected navigation and stale
state handling; unrelated screens and callbacks retain their behavior.
Historical resource-decorator provenance used `modloader-main-menu-v3`. See
[ADR-0029](adr/0029-main-menu-modloader-badge.md).

GUI source-root refresh includes the existing game-user `mods` directory on
every scan, using the same `game_user_dir()` location as activation. Optional
absent user folders are omitted; existing files/links still reach the normal
path validation. Scan/report identity and generated-output exclusion stay in
the discovery adapter. ADR-0026.

`game_launch` validates the applied package/activation and spawns the discovered
executable directly. `managed_menu` supplies an owned Lua extension
inside the generated package, with provenance in schema v2. Initial discovery
always refreshes the remembered selected set before auto-launch. ADR-0025.

Framework migration: source metadata includes optional `lua_api` and
`framework_api`. Analysis requires the reviewed runtime's corresponding API
level and matching capability. Gameplay stays in separate modules or native
plugins; the supplied ports use Lua. Both frontends share SDK mechanisms.
See ADR-0024.

`sdk_runtime` отделяет runtime stage/install/recovery от resource merge; journal фиксирует backup, EXE и inode до atomic publication. [ADR-0019](adr/0019-reviewed-runtime-upgrade-and-built-in-dependency.md).

Client-candidate содержит hash-addressed runtime_data с точными DLL/provenance/
notices и scope review. Profile разрешает только прошедшие проверку native bytes;
optional report.runtime_review сохраняет технический scope review и не создаёт
предупреждение GUI о тестовой сборке SDK, в том числе при reopening.
Release publisher отдельно сохраняет соответствующие SDK/toolchain sources.
[ADR-0020](adr/0020-scoped-client-sdk-candidate.md),
[ADR-0022](adr/0022-sdk-release-status-outside-modloader-ui.md).

Resolver различает уникальный source id и canonical package_id нескольких версий.
Explicit selection задаёт единственную версию для dependency resolution; GUI
переключает source checkbox до транзакции. [ADR-0021](adr/0021-explicit-package-version-selection.md).

`sdk_settings` отделяет approved defaults от исходных модов, публикует missing
INI атомарно без overwrite и участвует в общем journal/rollback по hash/inode.
Profile входит в engine hash, пользовательские значения — нет.
[ADR-0018](adr/0018-reviewed-sdk-setting-defaults.md).

`module_bundles` валидирует metadata и сохраняет самостоятельные VM contexts
внутри одного game package. Discovery фиксирует mod.xml bytes и legacy root
inputs; workflow объединяет private records с обычным merge report и использует
существующий transactional publisher. [ADR-0017](adr/0017-independent-lua-module-bundles.md).

**0.3.3:** classifier включает `.glsl` text и TXTR-magic `.txtr` binary; merge проверяет kinds всех вариантов перед copy/priority. UI использует исходный diagnostic needs_review и первый logical_path вместо общей заглушки. Схема не меняется. [ADR-0015](adr/0015-cc2-shaders-textures-and-actionable-refusals.md).

**0.3.2:** чистый ui_feedback строит OverrideWarning из существующих report.files/status/strategy/source_sha256/mod_order. GUI хранит предупреждение активного набора отдельно от отказа нового запроса, восстанавливает из manifest и отображает после apply. Merge/JSON schema не меняются. [ADR-0014](adr/0014-persistent-override-warning-and-workshop-delivery.md).

**0.3.0:** `preferences` хранит language/patch policy/per-game order атомарно; `i18n` + `translations` локализуют UI и diagnostics. GUI передаёт явный порядок в resolve_selection/analyze; apply воспроизводит merge_policy. Локальный baseline resolver использует ограниченный, case/Unicode-consistent поиск rom_0/SDK и записывает реальный SHA/source. Git `--theirs` разрешает только спорные hunks в режиме ordered-patches; no-base data получает отдельную whole-file strategy. [ADR-0012](adr/0012-user-ordered-patches-and-system-language.md).

**0.2.2:** GUI хранит раздельно requested и applied ID; окончательный отказ восстанавливает applied selection, а не оставляет ложную галочку. Чистый `ui_feedback` форматирует уже структурированные blockers с именами/ресурсом; merge-правила не меняет. Первый scan готовит собственные каталоги, passive scan не сбрасывает отказ и не пересобирает изменения только невыбранных пакетов. [ADR-0011](adr/0011-truthful-checkboxes-and-minimal-interface.md).

**0.2.1:** GUI debounce/проверка/применение автоматически следуют за галочкой; устаревшие результаты не публикуются. Один destination `mods/CC2-MCE` заменяется через полный stage и сохранение предыдущей собственной папки в служебный cache под OS lock. Pending journal позволяет восстановить payload/config при ошибке и перед следующей записью после прерывания процесса. Undo восстанавливает обе части. Источники и неизвестные outputs не перезаписываются. Контроль source updates повторным bounded scan, game-running wait и empty-set activation описаны в [ADR-0010](adr/0010-checkbox-auto-apply-and-stable-output.md), заменяющем immutable hash-named output ADR-0009.

## 1. Стиль

**0.2.0:** `workflow` теперь реализует plan→stage→publish→activation, `toolchain` проверяет bundled Git/luac manifest, `locking` изолирует операции двух экземпляров, game profiles связывают executable/base/native hashes. GUI использует этот сервис и actual activation state, не CLI/raw stdout. «Применить к игре» и recovery journal реализованы для проверенного Windows layout; historical read-only описания ниже не определяют этот pipeline. [ADR-0009](adr/0009-package-activation-and-library-sdk.md).

Текущий adapter `installation.py` читает bounded Steam KeyValues/manifest и проверяет соседнюю игру; он общий для GUI и поиска Workshop в CLI. GUI выполняет discovery/scan/анализ в фоне, разделяет `mods` и `libraries`, игнорирует результаты старого выбора. Найденная игра не создаёт synthetic baseline и не разрешает native plugin loading; создание пакета отключено. См. [ADR-0008](adr/0008-portable-discovery-and-library-collections.md).

**Hexagonal / ports-and-adapters:** чистое доменное ядро, адаптеры Steam/файловой системы/Git/SDK, стратегии по форматам. В будущем integration-host (CC2X) не должен менять контракт `MergeEngine`.

Windows и macOS — обязательные host-платформы графического приложения ([ADR-0005](adr/0005-windows-macos-support.md), [ADR-0007](adr/0007-gui-first-user-experience.md)). Поиск Steam, конфигурационных каталогов и инструментов, работа с файловой системой изолируются в адаптерах; Windows API, registry и CC2X не могут быть обязательными зависимостями ядра/общего workflow. CLI остаётся developer/CI adapter, не интерфейсом игрока.

```text
 GUI (P0) / CLI (dev, CI)
             |
        Application / BuildService
             |
   +---------+-----------------------+
   |         |                       |
ModDiscovery BaselineResolver    BuildPlanner
   |         |                       |
   +----> FileRegistry/ConflictGraph <+
                    |
               MergeEngine
              /    |      \
          Text    XML      Lua AST [P2]
           |     [P1]            |
       Git merge-file        tree-sitter
                    |
          ValidationPipeline
                    |
          Staging/PackageBuilder
                    |
       merged local CC2 mod + manifest/report
```

## Граница пользовательского интерфейса (P0, ещё не реализована)

GUI использует прикладной сервис с типизированными запросами/результатами анализа и сборки, а не требует ввода CLI, парсинга stdout или открытия JSON игроком. Текущая логика CLI при добавлении GUI выносится/переиспользуется в application layer, не дублируется на кнопках; правила merge и блокировки остаются в ядре. Выбор UI toolkit/упаковщика — отдельный implementation spike с проверкой Windows/macOS, лицензии и доступности; технология пока не назначена.

Discovery/hash/Git/validation выполняются в фоновой задаче/процессе, не в UI thread. Прогресс и отмена проходят через явный контракт; отмена прекращает безопасные шаги, не публикует частичный output. При финальном atomic publish интерфейс честно показывает завершающий этап. Изменение выбора/путей/порядка/источников аннулирует BuildPlan; статус кнопки создания выводится из актуальных engine gates, не из сохранённого сообщения об успехе.

Поиск игры/базы, настройки, file dialogs, открытие папки и экспорт — платформенные UI-адаптеры; исходные каталоги неизменны. Runtime/Git/Lua validator обнаруживаются в проверенной поставке, без зависимости от пользовательского PATH и ручной установки инструментов. Права доступа запрашиваются только к нужным каталогам, без обязательного повышения привилегий. Имена/описания модов отображаются как недоверенный текст. Видимые сообщения и действия сопоставлены внутренним статусам в [UX/UI](13-UX-UI.md).

## 2. Основные сущности

- `ModRef`: `id`, `name`, `kind (local/workshop)`, `root`, `selected`, `source_hash`, `metadata`, `dependency_notes`.
- `FileRef`: `logical_path`, `source_mod`, `source_path`, `sha256`, `kind`, `encoding`, `size`.
- `BaselineRef`: `game_build`, `sdk_root`, `logical_path`, `sha256`, `verified`.
- `ChangeSet`: патч `baseline -> mod-file` с метаданными происхождения.
- `Conflict`: `id`, `file`, `participants`, `kind`, `hunks`, `diagnostics`, `state`.
- `MergeResult`: `file`, `status`, `content_hash`, `sources`, `strategy`, `conflicts`, `warnings`.
- `BuildPlan`: фиксированный порядок модов, политики, ожидаемые outputs, blockers.
- `BuildManifest`: версия engine/config, игра/база, входы и хеши, маппинг выходов, решения.

`logical_path` — строго путь **внутри `content/`**, а не абсолютный путь к исходнику. Нормализация должна отклонять traversal, UNC, drive letters, NUL, альтернативные разделители/резервированные имена Windows. Структура root модов подтверждается в M0.

Host-пути Windows/macOS обрабатываются через файловый адаптер отдельно от игровых путей. Для `logical_path` используются `/` и единые правила casefold на обеих ОС независимо от чувствительности файловой системы к регистру; исходное написание сохраняется. Неоднозначные коллизии регистра и Unicode NFC/NFD отклоняются, а не исправляются молча. EOL/BOM и сортировка входов не должны зависеть от host-ОС: одинаковые байты, конфиг и версии инструментов дают одинаковые статусы и payload.

## 3. Алгоритм (файл с N вариантами)

1. Определить `V0` — ванильный файл из подтверждённого SDK *той же сборки игры*.
2. Собрать версии `Vi` от каждого выбранного мода, отсортировать по явно заданному `mod_order` (никакого недетерминированного порядка ОС).
3. Убрать побайтно идентичные дубли; если моды содержат уникальный новый путь без `V0`, проверить конфликты «add/add» отдельно, не создавать фиктивную пустую базу без явного правила.
4. Для каждого мода вычислить `ChangeSet(V0, Vi)` и индексы изменённых областей. Провести предварительный конфликтный анализ всех участников относительно одной базы.
5. Положить `accumulator = V1`; для `i=2..N` вызвать `merge_file(base=V0, ours=accumulator, theirs=Vi)`. На каждом шаге сохранять статус/диагностику. **Не публиковать** промежуточный результат с конфликтами.
6. Проверить выходной файл парсером и политиками типов. Сомнительные результаты — `needs_review`, даже при exit-code 0.
7. Обновить manifest, общий BuildPlan и только после полного успеха опубликовать отдельный staging пакет атомарным rename внутри одного тома.

**Ограничение:** последовательный 3-way merge N файлов не является полноценным семантическим N-way merge, порядок может изменить количество конфликтов и текст результата. Релиз обязан фиксировать `mod_order` и проверять тесты на чувствительность к порядку; порядок не используется как молчаливый приоритет, подменяющий чужие изменения.

## 4. Status model

- `clean`: слияние без текстовых конфликтов + валидный формат (это **не** доказательство игровой совместимости).
- `identical`: все версии данного файла одинаковы.
- `copied`: файл встретился один раз, перенесён без слияния.
- `conflict`: перекрывающиеся текстовые правки.
- `needs_review`: технически валидный, но потенциально неоднозначный результат.
- `no_base`: оригинал не найден / невозможно подтвердить сборку.
- `unsupported_binary`: нет безопасной merge-стратегии.
- `native_plugin_review_required`: DLL или сопутствующие native assets.
- `validation_error`: результат не прошёл синтаксическую/структурную проверку.
- `input_error`: недоверенный/опасный/испорченный источник.

**`installable = true` только если ни один ресурс не находится в блокирующем статусе**, пакет поддерживается CC2 и подтверждён корректный metadata-format.

## 5. Границы модулей

- `discovery`: только читает пути, метаданные, парсит manifest модов, не правит их.
- `baseline`: строгая связка game build + SDK + hash; отдельный manual override.
- `merge`: чистые операции над байтами/строками; не знают, где установлена игра.
- `validation`: семантически узкие проверки; не переписывает исходники.
- `package`: output в `staging/<build-id>.tmp`, sanitization и atomic publish.
- `reports`: единый JSON, human report через форматтер.

## 6. Безопасность и транзакционность

Схема `plan -> stage -> validate -> publish`: все ошибки оставляют предыдущую собранную версию неизменной. Исходные моды всегда read-only. Нельзя менять `%APPDATA%/.../mods.xml` в MVP. Staging нельзя размещать внутри сканируемых модов, чтобы не получить рекурсивную сборку самой себя. Буферизация изменений и file locks должны исключать частичный installable output.

## Реализация первого среза

В 0.1.0.dev1 границы представлены небольшими модулями: `filesystem`/`discovery` читают входы, `baseline` проверяет явный mapping, `merge` получает байты и использует Git adapter, `validation` проверяет синтаксис, `planner` связывает результаты с provenance, `reports`/`cli` выпускают JSON. Нет PackageBuilder, atomic staging, file locks, кэша или report JSONL. Данные ограничены 16 MiB на файл, 256 MiB на scan, 20 000 entries, depth 32 и 32 выбранными модами; превышение — `input_error`.

Снимки исходников в памяти проверяются повторным discovery/hash после анализа, но это не гарантия защиты от всех конкурентных замен каталогов недоверенным процессом. Packaging запрещён, пока filesystem publish boundary и race-tests не реализованы. Подробности: [ADR-0006](adr/0006-read-only-first-slice.md).

## 7. Наблюдаемость

Логи JSONL (планируется): `build_id`, `mod_id`, `logical_path`, `strategy`, `duration_ms`, `status`, `conflict_id`. Не логировать содержимое личных путей по умолчанию в публикуемых отчётах; export redaction.
