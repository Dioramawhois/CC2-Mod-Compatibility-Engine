## Unreleased — аудит Native Bridge и cc2mods (2026-11-02)

- По запросу владельца подготовлена карта общего CC2X SDK и отдельных модов:
  учтены code namespaces в едином output, сохранение identity/catalog и сетевые
  ограничения. GPL-моды cc2mods выделяются воспроизводимо из SHA-locked sources
  через инструмент companion SDK, без его копирования в моды.
  [Статус](docs/22-UNIFIED-SDK-AND-MOD-SPLIT.md). В companion SDK уже собирается
  один runtime с независимым Lua host и registry/UI. Сторона SDK читает ordered
  module bundles; publisher в выпущенной beta ModLoader ещё не подключён.
- Владелец подтвердил все разрешения своей команды. Сохранены GPL/MIT notices
  и provenance. F-16/F-15 выделен отдельно с исходными ID и 57 файлами.
  Native/static проверки проходят; свежая игровая и multiplayer приёмка открыты.

- Проверены переданные исходники, лицензии, lifecycle и границы multiplayer.
  Обнаружен конфликт раскладки API 5 между SDK development и Native Bridge;
  companion MR переходят на именованное сессионное расширение с проверкой ABI.
- По примеру явной репликации Hold исправлена публикация изменённых waypoint
  в companion Island Airfields MR, добавлена регрессия фактического обработчика.
  Multiplayer acceptance не заявляется. [Аудит](docs/21-NATIVE-BRIDGE-AND-CC2MODS-AUDIT.md).

## 0.4.0b1 — открытая Windows beta и подготовленный запуск (2026-11-02)

- GPL-3.0-or-later выбрана владельцем: добавлены LICENSE/NOTICE и metadata проекта.
- «Меню → Запускать игру при открытии» сохраняет настройку; запуск происходит после
  проверки и активации выбранного набора. Отказ отменяет автозапуск; предупреждение
  о перезаписи остаётся доступным. Добавлены переводы в 14 offline-каталогах.
- Чистая developer-сборка получает закреплённые Git/Lua по SHA без приватного SDK.
  Добавлены bounded ZIP validation и регрессии повреждённых/опасных архивов.
- Release packager проверяет provenance/JUnit, исключает личные данные из public report,
  собирает Windows/source/tool-source assets, notices, SBOM и checksums.
- Это обновление существующего ModLoader; новых Workshop items нет. In-game UI,
  multiplayer аэродромов, clean-machine и packaged macOS certification не заявляются.
  [ADR-0016](docs/adr/0016-open-source-beta-and-prepared-launch.md).

## 0.2.0 — применение модов к игре и SDK библиотек (2026-11-01)

- Рабочий Windows GUI pipeline: проверенная база/игровой fingerprint, настоящий Git с явной LF policy, bundled luac 5.3.6, отдельный package, backup/journal-protected активация и rollback. Добавлены process/source/integrity gates, OS lock и запрет посторонних файлов в reused output.
- Предоставленный reviewed dinput8.dll из libraries распознаётся и устанавливается рядом с игрой. Native DLL сохраняются как отдельные reviewed плагины; неизвестные DLL/сборки блокируются. Публичной бинарной склейки/компиляции DLL нет.
- Добавлена opt-in cc2mce секция mod.xml для library/mod, package ID, SDK/API и зависимостей. Без секции это обычный мод независимо от каталога. Новый package manifest/schema v2; read-only report v1 расширен compatible optional source metadata.
- Реально применены AI Bridge + Island Airfields: clean Git merge после LF normalization, настоящий syntax-only checker, свежая загрузка v45 DLL из combined mod и подтверждённое пользователем меню. Реальный rollback учёл game XML reformat/duplicate path. Full gameplay и macOS/clean-machine certification не заявляются.
- Новый exe: CC2Engine.exe. Проверяется выполнение встроенных Git/Lua внутри frozen приложения без developer PATH. [ADR-0009](docs/adr/0009-package-activation-and-library-sdk.md), [SDK](docs/17-LIBRARY-SDK.md).

## Unreleased — автопоиск игры, Workshop и библиотеки

- Добавлен безопасный read-only adapter Steam VDF/ACF: registry, дополнительные библиотеки, соседняя игра, проверка appid/executable, лимиты, path/link safeguards. CLI Workshop discovery использует тот же adapter; JSON v1 не изменён.
- Windows portable требует exe рядом с carrier_command.exe и показывает найденный путь; GUI отдельно отображает Workshop/local mods и Lua/DLL-пакеты libraries. Добавлены фоновый scan/анализ, invalidation, подготовка только двух собственных каталогов по кнопке и regression/UI fixtures.
- Удалён GUI fallback, создававший synthetic baseline из непроверенных игровых скриптов. Создание игрового пакета отключено до verified baseline/staging gates; DLL не исполняются. Runtime/профильная загрузка libraries и зависимости ещё не реализованы.
- На локальной Windows автоматически найдена установленная CC2 и показаны 9 Workshop пакетов без записи в них; это не игровой тест или macOS acceptance. [ADR-0008](docs/adr/0008-portable-discovery-and-library-collections.md).

## Unreleased — локальная Windows exe-сборка (2026-10-29)

- Исправлена упаковка: spec включает JSON-схему отчёта и Python-исходники для корректного `engine_sha256`; добавлен regression fixture с совпадением хеша исходного и распакованного движка и валидацией схемы. JSON v1 не изменён.
- `build_windows.bat` работает из другого каталога, поддерживает Python launcher, переиспользует build-venv и сохраняет ошибку на экране; `--no-pause` предназначен для автоматизации. PyInstaller закреплён на 6.22.3, сборка использует общий spec.
- Собран локальный exe на Windows 10 x64 / Python 3.14.0; проверены открытие/закрытие GUI без developer tools в PATH, целостность packaged data; 93 теста проходят, 2 symlink-теста пропущены. Исправлены lint/typecheck замечания GUI без изменения его поведения.
- Git/Lua не встроены; чистая ОС, полноценный GUI workflow, macOS и игра не проверены. Это тестовая упаковка окна, не пользовательский релиз или установочный пакет мода.

## Unreleased — Windows merged-mod build (2026-10-31)

- `cc2-mce build --mods-dir DIR --mods A B --baseline DIR --output OUT` теперь записывает объединённые файлы, если весь план чистый (статусы clean/copied/identical). Конфликт, блокировка или отсутствие `--output` ничего не записывают и возвращают ненулевой код.
- Отчёт остаётся read-only схемой v1 (`installable` = false): запись файлов не меняет схему отчёта.
- Внешний `git` по-прежнему используется для трёхстороннего слияния; встроенного слияния для Windows без git ещё нет.
- Тесты: 91 проходят, включая реальную запись разных правок и отказ записи при конфликте.

# Changelog

## 0.3.3 — игровые форматы и конкретная причина отказа (2026-11-02)

- Исправлен отказ Combined Fleet на двух `.glsl` shaders и двух `.txtr` textures, подтверждённых в установленном rom_0: шейдеры обрабатываются настоящим text merge, TXTR-magic ресурсы копируются/заменяются целиком по прежней policy. Unknown header в любом варианте остаётся blocker; неизвестные типы/DLL не разрешены молча.
- Общая needs_review заглушка заменена объяснением неподдержанного типа или неисправного встроенного Lua validator, путь виден прямо в banner, diagnostics — в подробностях. Все 14 языков обновлены.
- Исправлена Windows-only фабрика synthetic game layout, обнаруженная реальным CI macos-15. Added Windows/Darwin layout regression; production discovery не ослаблен. [ADR-0015](docs/adr/0015-cc2-shaders-textures-and-actionable-refusals.md).

## 0.3.2 — предупреждение о перезаписи и аудит Steam (2026-11-02)

- Успешный ordered-patches apply оставляет заметное предупреждение с именами/порядком модов, файлом и неопределённостью результата в игре. Подробности различают конфликтующие hunks и замену целого файла; все 14 языков обновлены. Clean/identical overlap не называется несовместимостью.
- Предупреждение восстанавливается из активного manifest, переживает passive scan, обновляется при reorder и исчезает после удаления пересечения. Галочки остаются включёнными, запуск доступен; дополнительных кнопок/подтверждений нет.
- Проведён аудит Workshop Required Items, фактического CC2X0.5.1 loader, first-run bootstrap, собственного Player Tools приложения, SteamPipe и лицензий. Добавлены metadata/описание для автора без DLL, game assets и выдуманного item ID. Публикация/новый installer не выполнялись. [ADR-0014](docs/adr/0014-persistent-override-warning-and-workshop-delivery.md).

## 0.3.1 — CC2 ModLoader и 14 языков (2026-11-02)

- Возвращено название CC2 ModLoader в exe/заголовок; generated mod снова содержит названия выбранных модов. Неизвестные executables не перезаписываются, прежний собственный Engine сохраняется в backup.
- Добавлены 12 офлайн-каталогов к RU/EN: 14 основных языков, system locale mapping и native names в меню. Проверены полные message IDs/parameters; основные labels выверены, остальные переводы машинные. Никаких запросов сети в runtime.
- CI переведён с retired macos-14 на macos-15. [ADR-0013](docs/adr/0013-modloader-brand-and-offline-language-pack.md).

## 0.3.0 — порядок патчей и системный язык (2026-11-02)

- Добавлена вкладка порядка с drag/drop и Alt+↑/↓, автоматической пересборкой и сохранением. Git сохраняет независимые правки и отдаёт спорные hunks позднему патчу; без оригинала data-файл заменяется по порядку с отдельным статусом/strategy. Приоритет можно отключить для strict проверки.
- Убрана per-file baseline allowlist для data: используются реальные rom_0/SDK originals с hash/source provenance, либо явно отмеченная replacement strategy. Native/path/syntax gates сохранены.
- RU/EN с системным языком по умолчанию, сохранением выбора и переносом ожидающего выбора/порядка при смене окна. Исправлен меньший размер выбранной вкладки.
- Preferences пишутся атомарно; JSON v2 дополнен policy/baseline source. JUnit counts попадают в build sidecar. [ADR-0012](docs/adr/0012-user-ordered-patches-and-system-language.md).

## 0.2.2 — UX-аудит и честные галочки (2026-11-02)

- При конфликте/ошибке применения галочки возвращаются к реально работающему составу; новый мод не остаётся ложно отмеченным, запуск прежнего набора доступен.
- Ошибка называет отказанный мод, участников и ресурс; видна у строки и в banner, не стирается пассивным scan. Обязательная зависимость объясняет, кому нужна.
- mods/libraries готовятся автоматически при первом запуске. Главный экран сокращён до списка/результата/запуска, служебные действия перенесены в одно меню; добавлены прогресс/состояния строк, сортировка и прокрутка.
- Merge/schema/native/provenance gates сохранены. [Аудит](docs/18-UX-AUDIT.md), [ADR-0011](docs/adr/0011-truthful-checkboxes-and-minimal-interface.md).

## 0.2.1 — одна папка, применение по галочке (2026-11-02)

- Убраны обязательные кнопки проверки/применения и подтверждение набора: галочки автоматически проверяют, объединяют и включают моды; быстрые переключения используют последний выбор.
- Постоянный output `mods/CC2-MCE`, игровое имя «CC2 Engine — мои моды». Полная замена убирает остатки снятых модов; пустой выбор отключает моды. Хеши сохраняются внутри manifest, не в именах папок.
- Обновления выбранных sources пересобираются автоматически; при запущенной игре выбор ожидает её закрытия. Конфликт сохраняет прежний рабочий пакет.
- Pending journal/backup восстанавливают папку и активацию после ошибки/прерывания; undo теперь возвращает payload. Прежний hash-output мигрирует в служебный cache. Generated outputs исключены из discovery, schema v2 допускает output_folder и empty set. [ADR-0010](docs/adr/0010-checkbox-auto-apply-and-stable-output.md).

## Unreleased — native install safety gate (2026-10-31)

- Независимое ревью не нашло blocking defect в rel32, но подтвердило HIGH blocker существующего MAP_FIXED: окно отсутствия RX-страницы и потеря конкурентных изменений. Constructor не доказывает quiescence. Установка hook теперь жёстко отключена для всех профилей, без env/CLI override; SHA allowlist не расширен.
- Реальный constructor использует `hook_install.h`: staged validation, allocation, повторная проверка, patch и cleanup при отказе. Добавлены `test_hook_install.c` с mocked native ops, счётчиками remap/protect/cleanup и проверкой порядка. Это не устраняет системный page/thread риск и не даёт разрешения на injection.

## Unreleased — native bridge guard (2026-10-31)

- В существующий Mac C bridge добавлены проверка декодированной цели CALL и проверяемая rel32-арифметика до выделения stub/замены страницы; отклоняются overflow/underflow и выход за signed 32-bit displacement. Старые SHA и адреса профилей не менялись.
- Добавлены нативные тесты `make test` с UBSan: границы displacement, неверный opcode, адресные переполнения, оба исторических профиля и ASLR. Это не доказательство игровой совместимости.
- Текущий Mac executable `eb46a7accf45d1c0ddad725ac1f98f50f8baf32d89b1138800cd1f7606279520` остаётся неподдерживаемым: по старому hook-site отсутствует ожидаемый CALL. Выполнены только статическое чтение и сборка, без запуска игры/инъекции.

## Unreleased — эксперимент Mac runtime (2026-10-28)

- Добавлен developer-only `x86_64` Lua bridge для двух точных Mac-бинарников CC2 `v1.5.17` и `v1.5.18`: проверка SHA-256 и байтов hook-site для каждого, внедрение минимальной таблицы `cc2x` до выполнения скриптов. `api=0` означает отсутствие обещания совместимости с Windows CC2X.
- Добавлен ограниченный прямой запуск игры с инъекцией только в дочерний процесс и проверками неподдерживаемой сборки/архитектуры; по умолчанию выбран вложенный `v1.5.18`. Пользовательского GUI и установщика ещё нет.
- На каждой из двух сборок: 20 Lua-состояний, 20 успешных Lua self-test, 0 ошибок за ограниченный прямой запуск. Steam Play в этой установке открывает внешний `v1.5.17`; причины вложенной упаковки `v1.5.18` не установлены. Полноценный игровой сеанс, сторонние моды, save/reload и нативные плагины не проверены.
- Эксперимент меняет только память запущенного процесса; файлы игры, Workshop и `mods.xml` не переписывались. Технические подробности: [Mac runtime spike](experiments/mac_runtime/README.md).

## Unreleased — требования UX/UI (2026-10-26)

- Графическое приложение Windows/macOS перенесено из отложенных возможностей в обязательный P0 первой пользовательской версии. Консоль/команды, ручные runtime-зависимости и технические конфиги исключены из всех пользовательских сценариев; CLI остаётся только для разработки/CI.
- Добавлены [UX/UI сценарий](docs/13-UX-UI.md), [ADR-0007](docs/adr/0007-gui-first-user-experience.md), PRD FR-15..FR-20, GUI/clean-machine/usability gates и этап M1-UI. Согласованы архитектура, поставка/лицензии, риски и release checklist.
- Команды для разработчиков перенесены из пользовательского README в CONTRIBUTING. Это обновление требований/документации: GUI, готовая пользовательская поставка и packaging пока не реализованы, runtime/JSON-контракты не изменялись.

## 0.1.0.dev1 — 2026-10-26

Первый read-only срез, **не полный MVP и не готовый загрузчик/упаковщик**.

### Добавлено

- Python CLI `doctor`, `scan`, `plan`, `build --dry-run`, `report`; строгая конфигурация TOML.
- Безопасный discovery: content-relative logical paths, case/Unicode collision detection, запрет symlink/junction, ограниченные чтение/scan и SHA-256 snapshot recheck.
- Явный baseline manifest с mapping/хешами; synthetic/game provenance разделены, для game проверяется executable hash.
- Адаптер настоящего `git merge-file`, pairwise N-way preflight с общей базой, copy/dedup и fail-closed binary/native/encoding policies.
- Lua 5.3 syntax-only boundary и XML well-formedness без DTD/entities; неизвестные форматы блокируются.
- JSON schema v1 с source/base/engine/output hashes, mod order, tool versions и policy metadata. Отчёт только новым файлом вне источников.
- Синтетический golden corpus и regression/unit/integration тесты; lock зависимостей, lint/typecheck, Windows/macOS CI workflow.

### Ограничения

- `installable` всегда false; build без dry-run и replay plan отклоняются. Нет atomic package staging/rollback, manual resolution/cache или game smoke.
- Реальные Workshop-моды доступны для read-only inventory, но актуальный SDK mapping и executable build ещё не верифицированы.
- Локально выполнены macOS тесты; Windows/удалённый CI и настоящая Lua 5.3 validation не подтверждены. Полный M0/M1 остаются открытыми.
- Лицензия проекта ещё не выбрана; публичная публикация исходников/пакета требует решения владельца.
