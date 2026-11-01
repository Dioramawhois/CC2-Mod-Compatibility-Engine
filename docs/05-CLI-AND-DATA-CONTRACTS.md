# 05. CLI и контракты данных (проект, v0.1)

**Назначение:** внутренний контракт для разработчиков/CI, не инструкция для игроков. Пользовательский интерфейс — обязательный GUI без терминала ([UX/UI](13-UX-UI.md), [ADR-0007](adr/0007-gui-first-user-experience.md)). GUI должен использовать application service/структурированные результаты; JSON/CLI не становятся обязательным пользовательским шагом.

**Статус 0.1.0.dev1:** реализованы `doctor`, `scan`, `plan`, `build --dry-run`, `report`. `build` без `--dry-run` и `build --plan` отклоняются с exit 2; устанавливаемый пакет не создаётся. Ниже отдельно описаны текущий read-only контракт и будущая упаковка; см. [ADR-0006](adr/0006-read-only-first-slice.md).

## 1. CLI

**0.2.0:** GUI использует отдельный `workflow.py` и [package.schema.json](../cc2_mce/schemas/package.schema.json), schema v2: installable допускается только без blockers, с known game/baseline/toolchain/native identity. Есть atomic staging, recovery journal и подтверждаемая GUI активация. Старый report v1 остаётся неустанавливаемым; source properties расширены optional `package_kind`, `package_id`, `dependencies`, `sdk`, `api`. SDK declaration описана в [17](17-LIBRARY-SDK.md). CLI не требуется игроку, raw developer outputs не равны игровому пакету. [ADR-0009](adr/0009-package-activation-and-library-sdk.md).

Автоматический поиск Workshop теперь использует общий Steam adapter: registry/default roots, bounded `libraryfolders.vdf`, дополнительные библиотеки. Аргументы CLI и JSON schema v1 не меняются; GUI показывает расположения отдельно от отчёта и не превращает наличие игры в доверенный baseline. Изменение discovery и portable policy: [ADR-0008](adr/0008-portable-discovery-and-library-collections.md).

```text
cc2-mce doctor --game <GAME_DIR> --baseline <SDK_DIR>
cc2-mce scan --mods-dir <LOCAL_DIR> --workshop-dir <WORKSHOP_DIR> --json scan.json
cc2-mce plan --mods <ID1> <ID2> [ID3...] --baseline <SDK_DIR> --json plan.json
cc2-mce build --mods <ID1> <ID2> --baseline <SDK_DIR> \
  --output <OUTPUT_DIR> --dry-run --report report.json
cc2-mce build --plan plan.json --output <OUTPUT_DIR> --report report.json
cc2-mce report <REPORT_JSON>
```

`--dry-run`: вообще не создаёт installable package, но может писать отчёт по явно указанному пути. `build` без `--dry-run` создаёт output только при отсутствии blockers. `doctor` выполняет предварительную диагностику версии игры, Git, SDK, путей и валидаторов.

CLI, параметры, коды завершения и JSON-контракты одинаковы на Windows и macOS. `doctor` проверяет доступность и версии Python, Git и Lua 5.3 validator для текущей ОС/архитектуры; Windows-only бинарник не считается доступным инструментом на macOS. Ошибка обязательной зависимости блокирует соответствующую операцию, а не включает небезопасный fallback. Пути каталогов — нативные для host-ОС; относительные игровые пути в JSON всегда используют `/`. Отсутствие игры на host не препятствует `scan` и тестам на synthetic fixtures; реальный merge требует подтверждённой базы целевой сборки.

### Реализованное подмножество

- `--config <PATH>` указывается перед подкомандой; относительные пути TOML считаются от каталога конфигурации.
- `--mods-dir`/`--workshop-dir` повторяемы. `--mods` принимает точные ID каталогов или пути к отдельным модам; порядок аргументов сохраняется. Без явных каталогов проверяется только стандартная Steam library текущей ОС; дополнительные библиотеки — через аргументы/TOML. `scan` не выбирает все моды для merge автоматически.
- Доступны `--git <EXECUTABLE>` и `--luac <EXECUTABLE>` для доверенных внешних инструментов; `--game-executable <PATH>` проверяет baseline игры по SHA-256. Игра/Lua/DLL модов не запускаются.
- `report` проверяет и повторно выводит JSON; для сохранённого `status: blocked` возвращает 2 (не пытается восстановить исходный exit 3..5 из чужого отчёта).
- Любой текущий отчёт имеет `dry_run: true`, `installable: false`. `status: ok` означает успешный анализ, не готовность к установке. Для баз используется `no_base`, не `no-base`.
- `--json` и `--report` — алиасы для нового JSON-файла вне входных корней; существующий файл не перезаписывается. Путь отчёта должен иметь существующего родителя без симлинков/junction; распознаваемые корни Steam/игры/SDK также запрещены. `--output` при dry-run только проверяется на пересечение с источниками, каталог не создаётся.
- Отсутствующий/wrong-version Lua 5.3 validator даёт `needs_review` (exit 2) для Lua, `doctor` даёт exit 5. Сбой запуска/timeout инструмента — `tool_error` (exit 5). При нескольких проблемах берётся наибольший exit code из 2..5.
- Нельзя отключать strict validation или разрешать binary/native через TOML. Lua/XML/текст проверяются и при copy/dedup. Типы вне allowlist требуют review.

## 2. Код завершения

| Exit | Смысл |
|---|---|
| 0 | Успех, нет блокирующих проблем |
| 2 | Неразрешённый merge conflict / review blocker |
| 3 | Неподходящая/отсутствующая игровая база |
| 4 | Ошибка входного файла/параметров/unsafe path |
| 5 | Ошибка системного инструмента (Git, Lua validator) |
| 6 | Ошибка при создании staged package |

## 3. Пример project config (`mce.toml`)

```toml
schema_version = 1
profile = "singleplayer-test"
game_dir = "D:/SteamLibrary/steamapps/common/Carrier Command 2"
baseline_dir = "D:/SteamLibrary/steamapps/common/Carrier Command 2/mod_dev_kit"
local_mods_dir = "C:/Users/USER/AppData/Roaming/Carrier Command 2/mods"
workshop_dirs = ["D:/SteamLibrary/steamapps/workshop/content/1489630"]
output_dir = "D:/CC2-MCE/staging"
mod_order = ["mod-a", "mod-b"]
strict_validation = true
native_plugin_policy = "block"
binary_conflict_policy = "block"
```

Это Windows-пример конфигурации; тот же набор ключей обязателен на macOS, где пользователь задаёт нативные абсолютные пути. Пути демонстрационные, не обязаны соответствовать размещению local mods у конкретной версии CC2. Реальные каталоги macOS/SDK подтверждаются в M0, не выводятся из Windows layout. Не сохранять личные пути пользователей любой ОС в общие issue без редактирования.

## 4. JSON отчёт

Исполняемая схема: [report.schema.json](../cc2_mce/schemas/report.schema.json). Она проверяется перед выдачей CLI и командой `report`; схемы из отчётов не загружаются из сети. Текущие обязательные поля включают `command`, `engine_sha256`, `dry_run`, `blockers`, `warnings`; ниже — иллюстрация будущего отчёта, не валидный fixture текущей схемы.

Текущий `engine_sha256` — digest относительных имён и байтов Python-модулей и packaged JSON schema (без абсолютных путей); версии зависимостей фиксируются в lock. В `sources` перечисляются ресурсные SHA-256 и metadata hash в общем source fingerprint. Для merge сохраняются `baseline_sha256`, `source_sha256`, `output_sha256`, `mod_order`, `tools`, `policies`, `build_id`; блокирующий файл не имеет выходного хеша. `conflict_ids` стабильны при тех же входах/порядке. Hunk coordinates и diff preview — следующий срез.

```json
{
  "schema_version": 1,
  "engine_version": "0.1.0-dev",
  "status": "blocked",
  "installable": false,
  "game": {"version": "1.5.18", "executable_sha256": "<SHA256>"},
  "baseline": {"path_hint": "mod_dev_kit", "fingerprint": "<SHA256>"},
  "mod_order": ["mod-a", "mod-b"],
  "sources": [
    {"id": "mod-a", "sha256": "<SHA256>"},
    {"id": "mod-b", "sha256": "<SHA256>"}
  ],
  "files": [
    {
      "logical_path": "scripts/screen_radar.lua",
      "strategy": "text-3way",
      "status": "conflict",
      "sources": ["mod-a", "mod-b"],
      "baseline_sha256": "<SHA256>",
      "output_sha256": null,
      "conflict_ids": ["c-0001"]
    }
  ],
  "conflicts": [
    {
      "id": "c-0001",
      "kind": "edit_edit_conflict",
      "file": "scripts/screen_radar.lua",
      "mods": ["mod-a", "mod-b"],
      "resolution": "unresolved"
    }
  ]
}
```

`<SHA256>` — **местозаполнитель**, невалидное production-значение. Для реального `manifest.json` нужны действительные 64 hex символа и соответствующая JSON schema.

## 5. Инварианты manifest

- Все входы указаны по SHA-256; порядок стабилен;
- `game` и `baseline` обязательны для output с real merge;
- каждое решение о конфликте связывается с тремя/несколькими исходными SHA-256, стратегией, engine version и base hash;
- `installable: true` допустимо только для успешно проверенного и упакованного пакета;
- schema_version обновляется при несовместимых изменениях;
- paths в отчёте относительные, абсолютные пути отдельно redacted;
- запрещено добавлять manifest в игровой `content` без подтверждённой поддержки.

## 6. Baseline manifest первого среза

`<baseline>/baseline-manifest.json` содержит строго `schema_version: 1`, `kind: synthetic|game`, `complete: false`, `game: {version, executable_sha256}` и массив `files: [{logical_path, source_path, sha256}]`. Пути относительны baseline root, недоверенные/повторные ключи JSON и case/Unicode collisions запрещены; все SHA-256 проверяются по реальным байтам. Пример — [synthetic manifest](../tests/fixtures/golden/base/baseline-manifest.json).

`kind: synthetic` допускает только `version: synthetic-*` и `executable_sha256: null`, отчёт не называет такую базу проверенной игровой. Для `kind: game` обязательны заявленная версия и совпадение SHA-256 явно переданного `--game-executable`. Это пользовательское свидетельство mapping, а не автоматическое доказательство происхождения SDK: соответствие SDK этой сборке ещё проверяется M0. Манифест не должен собираться из изменённых файлов мода.

Mapping пока неполный (`complete: false`): отсутствие записи не доказывает, что ресурс новый. Разные версии без указанного оригинала дают `no_base`; автоматический add/add доступен только доменному API при явно доказанном отсутствии базы, CLI такую политику пока не включает. Baseline и исходники перечитываются/хешируются после анализа; изменение, добавление или удаление ресурса блокирует результат.

## GUI package v2: постоянная папка и пустой набор (0.2.1)

**UX 0.2.2:** JSON schema v2 не меняется. Report при отказе описывает отклонённый requested набор; не считается текущей активацией. GUI отдельно хранит applied ID, возвращает к ним галочки, сохраняет rejected report для добровольного экспорта и выводит названия/ресурс через чистый presenter. Нельзя выдавать mod_order отклонённого report за включённый состав. [ADR-0011](adr/0011-truthful-checkboxes-and-minimal-interface.md).

Новые manifests включают `output_folder: "CC2-MCE"`; поле необязательное при чтении прежних v2 пакетов для миграции. `mod_order` допускает 0..32 уникальных ID: пустой набор имеет пустые sources/files/payload, а активация — пустой active_mod_folders. Все source/base/output/engine/tool hashes и внутренний build_id сохраняются. Обратно совместимое расширение schema v2 не меняет developer CLI/report v1. Постоянный путь не является build identity; reuse/undo сравнивают manifest и все файлы. [ADR-0010](adr/0010-checkbox-auto-apply-and-stable-output.md).

## 7. Ручное разрешение в P1

Хранить `resolution` и `input_fingerprints`; разрешение автоматически аннулируется при изменении любого участвующего исходника/базы. Внешний редактор открывает только копии во временном каталоге, не исходный Workshop мод. Валидация после редактирования обязательна.
