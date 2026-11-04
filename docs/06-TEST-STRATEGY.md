# 06. Стратегия тестирования и Definition of Done

ADR-0032 fixtures exercise a Workshop SDK source update while removing a
gameplay mod, reversible previous-to-current runtime installation, a current
installed provider with an unsupported source DLL, an unknown installed loader
and an older reviewed source that must not downgrade the provider. Verify the
source/installed diagnostic codes separately, blocked participant provenance,
SDK row feedback and all 14 offline catalogs. Never execute fixture DLL bytes.
SDK provenance/ABI review, upstream offline tests and these synthetic checks
do not replace fresh exact-binary game-menu/gameplay acceptance. See
[ADR-0032](adr/0032-reviewed-sdk-provider-synchronization.md).

ADR-0031 regressions cover a resource above the former 16 MiB limit and an
installed collection above 256 MiB without retaining every resource in memory.
Exercise streamed discovery, lazy-content size/hash revalidation, explicit
small limits, replacement per-file/aggregate bounds, metadata isolation and
16 MiB text-processing limits despite larger binary-copy capacity,
selected-input preflight, generated output and activation/reuse verification.
Verify the existing source report/hash contract for unchanged bytes. These
offline filesystem/package checks do not certify new gameplay or turn beta 7's
exact-binary menu evidence into beta 8 acceptance.

ADR-0030 adds the missing delivery gate. Package fixtures verify the schema-1
screen declaration, owned extension source, inventory/provenance hashes,
historical policies, empty selection and Undo. SDK fixtures cover exact screen
matching, validated paths, active-package scope and execution after stock code
but before `begin()`. Keep the UI behavior checks below, using only owned code.
Before release, launch the exact candidate/runtime in the real game, record
extension delivery for the main menu, confirm the badge and attempt to open
Mods. Check ordinary navigation and a launch without the managed extension.
Beta 6's isolated callback tests did not prove this boundary and the owner
reported that Mods remained clickable. The final beta 7 Windows pair passed
the scoped live menu checks in [menu verification](verification/main-menu-v4.md);
these do not establish full gameplay or multiplayer acceptance.

ADR-0029 adds owned Lua fixtures for the noninteractive brand/selected-mod label
above the main menu's first ordinary header, once per frame and absent from
other screens. Cover source order, Unicode truncation to at most 140 characters,
control-character normalization, Lua escaping, repeated/recreated UI objects,
empty selection and restoration of prior build behavior. Verify final Lua
syntax, input/adapter/output hashes and all three accepted policy values.
These fixtures do not establish fresh in-game visual or gameplay acceptance.

ADR-0028 fixtures require the main-menu Mods list item's third (enabled)
argument to be false for the current localized label, even if a synthetic UI
reports a click. Direct Mods navigation is rejected; stale Mods state returns
to main before update. Unrelated list items/screens and ordinary callbacks
retain their arguments and behavior. Cover recreated UI objects, real Lua
syntax validation, adapter/input/output hashes, historical package policy values,
and empty-selection/Undo behavior. Execute only the owned synthetic Lua fixture,
never a user's mod Lua. These checks are not fresh in-game visual acceptance.

ADR-0026 GUI fixtures cover Workshop/game-folder/user-data mods together,
exclusion of the owned generated output, and a user-data `mods` folder created
after startup. Passive discovery preserves the active selection, leaves new
mods unchecked and does not queue a rebuild merely for an unselected mod.

ADR-0025 regressions cover direct executable spawning, changed activation/game/
payload refusal, forced startup analysis, new/removed Workshop files, remembered
selection recovery, and generated-menu hashing/syntax/rollback. The owned Lua
UI fixture checks disabled rows/buttons and stale keyboard/dialog actions;
no user mod Lua is executed by it. Real game-menu checks remain separate.

CI builds the official Lua 5.3.6 source archive with its published size/SHA-256
using the runner's C compiler. All Windows/macOS jobs execute the owned Lua UI
contract and syntax fixtures with this interpreter/validator. A source checkout
without a validator skips those optional local fixtures explicitly; the frozen
Windows build has its separately pinned shipped validator.

Version-selection fixtures: source choice, duplicate selection refusal,
dependency preference/ambiguity, ID shadow, fixed-output switch/Undo и реальные
Tk checkbox success/rejection. Не требуется менять Workshop для теста обновления.

Client-candidate regressions проверяют shipped PE32/hash/source provenance,
approved defaults и отсутствие SDK test-build notice при наличии runtime_review,
в том числе в восстановленном manifest. При пересечении модов сохраняется обычный
override notice с участниками/ресурсом. [ADR-0022](adr/0022-sdk-release-status-outside-modloader-ui.md).
Release fixtures отклоняют изменённые DLL/source/generated
headers/notices и dirty/mismatched source commit; pinned Git source приводится
только к подтверждённым build report line endings. Реальная одиночная приёмка
spawn/save/reload описана отдельно в docs/22; это не network/flight acceptance.

Runtime upgrade fixtures проверяют initial install/upgrade/Undo, failure/crash recovery, unknown/external writers, old wrappers и corrupt bundle; native bytes не исполняются. [ADR-0019](adr/0019-reviewed-runtime-upgrade-and-built-in-dependency.md).

SDK settings: fixtures покрывают create/undo/preserve, ordinary failure и
interruption/recovery, writer race с одинаковыми bytes, path scope, удалённые
settings/runtime и conflicting approved defaults. Проверяется реальная файловая
транзакция; native fixtures не исполняются. [ADR-0018](adr/0018-reviewed-sdk-setting-defaults.md).

Module bundle fixtures до реализации: одинаковые filenames у разных owners,
порядок/зависимости, disable/update/rebuild/rollback, три manifest layouts,
duplicate/oversized/deep/unsafe metadata, все Lua entries, неизвестный native,
namespace injection и output depth. Packaging использует fake runtime/syntax
boundary; shared files — настоящий Git. Bundled luac, SDK reader и игра требуют
отдельного evidence. [ADR-0017](adr/0017-independent-lua-module-bundles.md).

**0.3.3:** fixtures до реализации воспроизводят `.glsl`/`.txtr` отказы и общий needs_review banner. Real Git text merge, UTF-8 refusal, byte-identical TXTR copy, strict/ordered collision и malformed header в обоих положениях/режимах; UI file/reason и Lua-tool diagnosis. Mac CI fixture следует реальному host, Windows/Darwin layouts проверяются явно. Реальный Fleet read-only plan без blockers не равен game acceptance. [ADR-0015](adr/0015-cc2-shaders-textures-and-actionable-refusals.md).

**0.3.1:** 183 Windows tests passed, 3 symlink skips. Проверки всех 12 дополнительных каталогов: полные 174 IDs, непустые строки, неизменные placeholders и успешный format; locale mapping включая zh-Hant/TW, generated name c ModLoader/авторскими именами, frozen exe/title/hash data. Raw machine outputs не равны профессиональной лингвистической редактуре; primary labels проверены отдельно. CI перенесён с retired macos-14 на macos-15. [ADR-0013](adr/0013-modloader-brand-and-offline-language-pack.md).

**Регрессии 0.3.0:** local original без profile hash, case-independent lookup, no-base replacement/strict refusal, поздние hunks с сохранением независимых изменений, повторная ранняя версия как поздний патч, apply policy replay. GUI порядок автоматически меняет payload, сохраняется в preferences; выбранная вкладка имеет больший padding. RU/EN/system и повторное открытие после language selection, catalog coverage, names/paths/parameters сохранены. Build пишет JUnit counts, sidecar берёт реальные результаты. Реальный read-only Revolution plan — отдельное evidence уровня файлов, не gameplay. [ADR-0012](adr/0012-user-ordered-patches-and-system-language.md).

**Регрессии 0.2.2:** отказ real Git и ошибка apply снимают новую галочку, оставляют рабочие галочки/payload и разрешают launch; названы моды/ресурс; пассивный scan/невыбранный новый мод не стирают отказ; обязательная зависимость объясняет возврат галочки. Первый запуск создаёт каталоги автоматически, а файл на месте libraries сохраняется и блокирует scan. На главном экране одна кнопка запуска и меню; отдельные pure feedback tests проверяют removal/source-update/long names. [Аудит](18-UX-AUDIT.md), [ADR-0011](adr/0011-truthful-checkboxes-and-minimal-interface.md).

**Регрессии 0.2.1:** одна папка при разных наборах; исчезновение obsolete files; пустой выбор; отказ неизвестной папке; config-write rollback; прерывание между двумя rename и recovery; миграция прежнего hash-output; undo payload/config и повторный запуск после game XML formatting. GUI fixtures проверяют применение только по галочке без askyesno, debounce, сохранение рабочего набора при конфликте, ожидание закрытия игры и автоматическую пересборку обновлённого source. Это дополняет/уточняет U-003/U-005/U-006/U-009 по [ADR-0010](adr/0010-checkbox-auto-apply-and-stable-output.md), не заменяя отдельные macOS/clean-machine/gameplay gates.

## Обязательная GUI-приёмка

Первая пользовательская версия — графическое приложение без обязательных команд ([UX/UI](13-UX-UI.md), [ADR-0007](adr/0007-gui-first-user-experience.md)). Ниже CLI-тесты относятся к внутреннему ядру/CI, не заменяют UI/e2e и проверку готовой поставки на чистой ОС без developer tools. GUI ещё не реализован; тесты UX ниже — требования, не уже пройденные результаты.

## Выполнение первого среза (для разработчиков)

`uv sync --frozen --extra dev`, затем `uv run pytest -q`, `uv run ruff check cc2_mce tests`, `uv run ruff format --check cc2_mce tests`, `uv run mypy cc2_mce`. [Golden corpus](../tests/fixtures/golden/) полностью синтетический, его байты защищены `.gitattributes` от автоконвертации EOL. Интеграционные тесты вызывают настоящий Git; Lua 5.3 subprocess boundary проверяется mock, полноценный настоящий Lua validator в локальном окружении пока отсутствует.

[CI](../.github/workflows/ci.yml) на Windows/macOS с Python 3.12/3.13 запускает одинаковый golden hash. Наличие workflow не означает прошедший удалённый CI или завершённый M1; версия Git runner может различаться, сравнивается payload, а не окружение. M-016/M-029 packaging/rollback и игровые tests пока не реализованы. Текущие ограничения: [M0 validation](12-M0-VALIDATION.md).

## 1. Уровни тестов

0.2.0: `test_workflow.py` покрывает настоящий Git с canonical EOL, создание game mod, активацию/rollback, running-game/source-change gates, отказ unknown DLL, посторонний executable в reused output, write failure, зависимости/циклы и реальное переписывание XML игрой. `test_metadata.py` покрывает default-mod и opt-in library XML. Настоящие Tk buttons проверяют check→apply→activation. Frozen smoke запускает bundled Git/luac без developer PATH. Свежий game log подтвердил plugin из AI Bridge + Island Airfields, пользователь подтвердил меню; полный flight/AI-command gameplay не проверен.

`tests/test_installation.py` проверяет bounded Steam metadata, secondary/legacy libraries, appid, traversal/DoS, adjacent priority и управляемые каталоги. `tests/test_gui_discovery.py` использует настоящие Tk widgets для mods/libraries, portable placement, фонового scan, invalidation и native refusal без запуска DLL/Lua. Недоступный GUI display явно пропускает GUI tests и не считается GUI acceptance. На текущей Windows проверены read-only обнаружение установленной CC2 и отображение 9 настоящих Workshop пакетов; игровой запуск не выполнялся.

- `unit`: планировщик, path normalization, change-set, status transitions, policy selection, hashing.
- `integration`: реальные вызовы `git merge-file` на fixtures, разные EOL/BOM, staging + atomic rename, error codes.
- `format`: Lua 5.3 syntax (`luac -p`) и XML parser, фикстуры из разрешённых оригиналов.
- `gui/e2e`: первый запуск, file dialogs, выбор модов, понятные сообщения, прогресс/отмена, создание/экспорт/восстановление; реальные widgets/application service без обхода blockers.
- `distribution/usability`: готовая сборка на чистых Windows/macOS без Python/Git/Lua в PATH, отсутствие консольных окон/команд, walkthrough с обычным пользователем и доступность.
- `system (manual)`: локальный CC2, запуск merged mod, включение/выключение в меню, поведение CC2X.
- `regression`: проверенный golden corpus пар модов и N-mod наборов, хешированный output.
- `security`: недоверенные каталоги, симлинки/junction, zip slip (если появится архивация), XXE, большие файлы/DoS.
- `cross-platform`: обязательная CI-матрица Windows + macOS для CLI smoke, unit/integration/format и staging/rollback; одинаковые fixtures с сохранением исходных EOL/BOM, фиксированными версиями инструментов и сравнением статусов/конфликтов/хешей payload. Игровые тесты отделяются от host-проверок: поддержка macOS CLI не зависит от наличия нативной CC2 на Mac.

## 2. Обязательная матрица кейсов

| Test ID | Сценарий | Ожидаемый статус |
|---|---|---|
| M-001 | A меняет строку 1, B строку 10 | clean |
| M-002 | A и B меняют ту же строку одинаково | clean / identical change |
| M-003 | A и B меняют ту же строку по-разному | conflict |
| M-004 | A удаляет участок, B редактирует его | delete_modify_conflict |
| M-005 | A добавляет функцию, B другую рядом | может быть текстовый conflict; AST в P2 |
| M-006 | A и B добавляют новый идентичный файл без B | identical |
| M-007 | A и B добавляют разные новые файлы одного пути | add_add_conflict |
| M-008 | Оригинал отсутствует / hash mismatch | no_base |
| M-009 | Пара PNG с одним logical path | unsupported_binary |
| M-010 | DLL в `content/cc2x/` | native_plugin_review_required |
| M-011 | Конфликт EOL/BOM/UTF-16 | encoding_conflict или валидный обратимый merge |
| M-012 | Lua не парсится после clean merge | validation_error |
| M-013 | XML не well-formed | validation_error |
| M-014 | Дубли из каталогов с различием регистра | input_error |
| M-015 | Symlink на родительский или внешний каталог | input_error |
| M-016 | Утраченная запись в staging / crash | rollback к предыдущей сборке |
| M-017 | Три мода, конфликт только A и C | обнаружить несмотря на порядок |
| M-018 | Смена mod order | manifest отражает порядок и возможную разницу |
| M-019 | Изменение mod file после cached resolution | resolution invalidated |
| M-020 | В пакете встречаются conflict markers | block publish |
| M-021 | Тот же набор входов повторно | одинаковый payload hash |
| M-022 | Нет установленной игры, synthetic fixtures | unit/integration успешны |
| M-023 | XXE в XML и traversal в metadata | безопасный отказ |
| M-024 | Workshop обновлён во время сборки | hash mismatch и безопасный abort |
| M-025 | Внутренний CLI/core на Windows и macOS утверждённых версий/архитектур | одинаковые developer-команды, JSON-контракты и коды завершения; не замена GUI-приёмке |
| M-026 | Одни байтовые fixtures, база, mod order, политики и версии инструментов на обеих ОС | одинаковые статусы, конфликты и хеши payload; допустимые отличия окружения/времени/локальных путей документированы |
| M-027 | Нативные пути с пробелами/кириллицей, case-sensitive и case-insensitive ФС, коллизии регистра/NFC/NFD | безопасный доступ на обеих ОС; неоднозначные игровые пути — input_error, без тихой перезаписи |
| M-028 | Git или Lua 5.3 validator отсутствует/не подходит для host-ОС | doctor сообщает причину; обязательная операция блокируется без fallback |
| M-029 | Staging/publish/rollback на Windows и macOS, включая занятый output | предыдущая сборка сохранена при ошибке, частичный пакет не публикуется |

### UX/UI и готовая поставка (P0)

| Test ID | Сценарий | Проверяемый результат |
|---|---|---|
| U-001 | Чистые Windows/macOS без developer tools | Готовое приложение устанавливается/открывается обычным способом, всё работает без терминала, отдельного Python/Git/Lua и всплывающей консоли |
| U-002 | Игра/моды не найдены, несколько установок, отказ в доступе | Понятное сообщение, системный выбор папки, проверка и сохранение настроек; нет команд или ручного конфига |
| U-003 | Выбор/поиск модов и смена порядка после проверки | Названия/авторы видимы, состав явный; готовность предыдущего плана сброшена, повторная проверка обязательна |
| U-004 | no_base/conflict/native/binary/validation/tool error | Человеческая причина и безопасное действие, технические детали необязательны; нельзя обойти блокировку кнопкой |
| U-005 | Долгая операция, повторный клик, отмена/закрытие окна | UI отзывчив, прогресс честный, дублирование операции исключено, частичный output не публикуется |
| U-006 | Создание и восстановление после сбоя | Только подтверждённый актуальный план, предыдущая сборка сохранена, отдельные состояния проверки/создания/включения, исходники нетронуты |
| U-007 | Экспорт отчёта и справка | Системный save dialog, защита источников/личных путей, нет автоотправки и команд в инструкции |
| U-008 | Клавиатура, диктор, масштаб 100–200%, длинные/недоверенные названия | Все действия доступны, фокус/labels корректны, ничего не обрезано, статусы не только цветом; текст не исполняется как HTML/команды |
| U-009 | Повторный запуск/обновление Workshop/игры без сети | Каталоги проверены заново, устаревший план недействителен, offline workflow не требует downloads |
| U-010 | Игрок вне команды разработки проходит основной сценарий | Обходится экранами/пользовательской справкой без помощи командами; UX-тупики исправлены до релиза |

GUI automation на synthetic corpus, clean-machine поставка и игровой smoke — три разных вида доказательства. Красивый макет или проход CLI не закрывают U-001..U-010.

## 3. Golden corpus

Минимально: 2 набора фиктивных Lua/текстовых файлов, 2 XML файла, 3-модовый fixture, 1 binary collision, 1 CC2X DLL case; после Milestone 0 — отдельные **не распространяемые** реальные игровые примеры из установленного SDK. Реальные чужие assets в публичном репозитории только при явно достаточной лицензии.

Golden tests должны сравнивать `status`, `conflicts`, содержимое merged файл или digest и JSON report schema. Не делать snapshot абсолютных путей / timestamps.

## 4. Ручное in-game тестирование

1. Зафиксировать версию игры, локальный набор модов и SHA256.
2. Создать бэкап сохранения (моды влияют на состояние игры после отключения).
3. Проверить, что два исходных мода конфликтуют штатно.
4. Отключить оригинальные версии, включить только merged mod, перезапустить игру.
5. Проверить обе независимые функции в интерфейсе/в бою, в логах нет Lua errors.
6. Для CC2X кейса проверить `cc2x.log`, факт загрузки плагинов и отсутствие overlap patch refusal, не считать одного успешного старта достаточным.
7. Выйти, отключить merged mod и вернуть исходную конфигурацию.

## 5. Exit-gates milestones

- **M0:** воспроизведена структура mod.xml, mod_dev_kit baseline mapping, запуск обычного локального мода, minimal goldens; утверждена матрица версий/архитектур Windows и macOS, Python/Git/Lua validator и способы их установки на обеих ОС. Непроверенный запуск самой игры на macOS отмечается отдельно, не подменяет host-проверку CLI.
- **M1:** M-001..M-004/M-006..M-010/M-014/M-016/M-017/M-021 и JSON schema на Windows + macOS; M-025..M-028 для доступных команд/валидаторов этапа; output ещё может быть dry-run.
- **M1-UI:** U-002..U-005/U-007..U-009 для read-only сценария на обеих ОС; создание отключено, если packaging не реализован. UI toolkit/упаковка/доступность проверены runnable spike.
- **M2:** M-011..M-013/M-018..M-020/M-023..M-029 и U-001..U-010 на Windows + macOS, включая полноценный GUI build/валидацию/staging/rollback и готовую поставку без ручных runtime/команд; in-game Lua test и package recognized by CC2 на подтверждённой целевой игровой платформе.
- **M3:** schema-aware XML + расширенные game-case tests.
- **M4+:** экспериментальный Lua AST + сравнительный benchmark против Git, отсутствие регрессий.

## 6. Definition of Done любой задачи

- Тест воспроизводит дефект/требование до исправления, успешен после.
- Документы/ADR/API и changelog обновлены при изменении поведения.
- Нет неявной записи в чужие каталоги, нет auto-winner и silent fallback.
- Для пользовательской функции есть GUI-сценарий без терминала, понятные состояния/следующие действия и соответствующие UI tests. CLI-only решение не закрывает пользовательское требование; для первой поставки обязательны clean-machine и usability gates.
- Для output указаны SHA-256 и источники, CI тесты зелёные на Windows и macOS; платформенные изменения покрыты регрессией на обеих ОС.
- Для package изменений — staging/rollback на обеих host-ОС и ручной CC2 smoke на подтверждённой целевой игровой платформе до релиза. Для CC2X plugin — отдельный Windows CC2 smoke; успешный CLI-тест на Mac не доказывает игровую совместимость.
