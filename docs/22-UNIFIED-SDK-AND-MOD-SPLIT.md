# 22. Общий CC2X SDK и отдельные моды

Решение владельца: 2026-11-02. Развиваем существующий CC2X, сохраняя его runtime
ID `cc2x.runtime`. ModLoader и Island Airfields сохраняют свои проекты и Workshop
идентичности. Общий runtime и отдельные полные пакеты собраны, совместная
одиночная сессия со spawn/save/reload проверена. Кандидат ModLoader 0.4.0b2
включает этот SDK и точные native-профили. Это клиентский кандидат; полный
сетевой/native релиз ещё не объявлен. См. ADR-0020 и границы ниже.

Локальный пакет следующей версии аэродромов сохраняет ID 3826940003. Resolver
и GUI позволяют явно переключиться с Workshop-источника на локальный без записи
в Workshop; две версии вместе не включаются. См. ADR-0021.

## Границы продуктов

| Проект | Содержимое |
|---|---|
| CC2X SDK | Один bootstrap/runtime, проверенные профили игры, hooks/transactions, world API, server sessions, очереди команд, Lua host, публичный cc2 API, общие registry/UI/resource операции из Bridge |
| Island Airfields | Правила посадки, полётный алгоритм, очереди аэродромов, настройки и игровой UI. Низкоуровневые необходимые операции предоставляются SDK |
| F-16/F-15 | Lua-регистрация, XML/модели/текстуры/иконки и управление самолётами. Имена самолётов и hotkeys не становятся ветками C++ SDK |
| Hold copies | Копии кнопок, выбор панелей и правила синхронизации Hold |
| Modes CC2 | ECO/NORMAL/FLANK, ограничения тяги, UI и настройки |
| Manual landing brake | Политика ручной посадки/торможения и настройки |
| CC2 ModLoader | Поиск/выбор/порядок, Git merge игровых ресурсов, транзакционная активация, установка проверенного runtime и запуск. Python/Git не объявляются частью игрового Lua API |

SDK предоставляет общие операции движка. Игровая политика остаётся в модах;
её постепенно переносим в Lua после появления проверенных публичных primitives.
Нужную механику в конкретном native tick можно оставить в небольшом C/C++ plugin.
Рабочий C flight director не переписывается вслепую ради формального «всё в Lua».

## Одно ядро и совместимый API

Исходная база — текущая ветка существующего CC2X. Вторую копию
`third_party/cc2x` из Bridge в SDK не вкладываем. Native Bridge перестаёт быть
отдельным поставщиком конкурирующей dinput8.dll: его runtime-компоненты уже
включены в общий SDK. Владелец подтвердил все разрешения своей команды;
GPL-3.0-or-later, исходные notices и MIT notice Lua сохранены.

Общий C-префикс API 4 сохранён; его размер — `CC2X_API_V4_SIZE`, а не sizeof
расширенного заголовка. Принят командный API 8 Native Bridge. Сессионное расширение
v1 остаётся отдельным именованным query с проверкой ABI. Старый черновой API 5
с сессионными полями несовместим по хвосту и требует пересборки потребителей.
Числовая версия не доказывает совместимость неизвестного fork. `cc2x` остаётся
Lua-интерфейсом, `cc2` — работающий фасад независимого host.

Перенесённые общие компоненты Bridge: `src/runtime` (host, mod discovery,
early declaration), `src/api/vehicle` (generic definition registry/adapter),
`src/api/ui` (asset registry/atlas), generic native operations и `sdk/cc2.lua`.
Условия конкретного gameplay мода, клавиши F5/F8, множители скорости и aircraft
ресурсы в runtime не включаются. Research/probes и test-mods остаются fixtures,
не поставляются игроку вместе с SDK.

Глобальное отключение проверок несовместимости из Bridge не переносится как
поведение SDK по умолчанию. Предупреждения ModLoader сохраняются; отсутствие
конфликтов data-пакета и допуск native plugins проверяются отдельно.

## Отдельные репозитории модов

Разработчик мода использует общий SDK по sibling checkout, `--sdk` или
`CC2X_SDK_DIR`. SDK не копируется внутрь каждого мода. Мод может содержать Lua,
resources и при необходимости свой `content/cc2x/<plugin>.dll`; DLL не склеиваются.

Для cc2mods подготовлены три отдельных исходных проекта. Первоначальное
извлечение сохраняет byte-identical C sources/tests/config examples, GPL и авторство Yolo /
totolerigolo118. Старые UI generators сохранены как reference и не вызываются
новой сборкой. В частности, исходный Modes script содержит также команды установки:
он не является поддержанным install entrypoint нового проекта. Отдельные старые
installer/game-launch scripts не переносились. С подтверждённым разрешением
команды F-16/F-15 теперь выделен четвёртым локальным Git project: 57 исходных
файлов с SHA-locked extraction, прежними mod.xml, owner ID, entry и resources.
SDK/DLL в нём не вендорятся. Новый публичный Workshop item не создавался.

Все три plugin DLL собраны через один внешний SDK. Исходные C fixtures прошли:
Hold — 636 проверок, Modes — 292, Brake после адаптации — 335; всего 1263,
без ошибок. Это fake game/API tests, а не запуск DLL в игре. Extraction
cc2mods и aircraft проверены на временных fixtures отдельно.

При разборе Brake обнаружена отдельная интеграционная несовместимость:
upstream ожидает `1.5.18-win32-6ae228f3`, наш SDK возвращает `1.5.18-win32-r2`.
PE timestamp совпадает; исправлено каноническое имя профиля и проверка размера
API prefix вместо sizeof расширенного API 8. Адреса, PE/native-byte guards
сохранены. Regression сначала воспроизвёл отказ, затем прошёл, включая
неправильные сочетания profile/timestamp. Изменение отдельно закоммичено и
описано в ADAPTATIONS.md; upstream hash manifest остаётся provenance исходника,
а не ложным утверждением о неизменности текущего адаптированного C файла.

Первый результат — source separation и сборка native plugins, не готовые player
packages. Для Hold и Modes нужно закончить генерацию UI из легальной локальной
игры; для Brake исходный standalone mod folder ещё не существовал. Новые
Workshop IDs не придумываются. Публикация обновлений существующих items — после
полного package/runtime acceptance.

## Сборный output ModLoader должен сохранять границы Lua-модулей

Это обязательная доработка перед включением нескольких Bridge модов вместе.
Исторический Bridge выбирал один bridge.json на активный игровой package. Если
объединить два `content/bridge.json` и `bridge/main.lua` обычным приоритетом
файлов, один мод исчезнет либо смешается с другим. Так делать нельзя.

Общий SDK уже читает отдельные контейнеры
`content/cc2x-modules/<package-key>/mod.xml` и `content/...` каждого исходного
мода. Индекс `content/cc2x-modules/index.json` имеет вид
`{"schema":1,"packages":["source-a","source-b"]}`. Порядок сохраняется;
повторные ID модулей отклоняются все, остальные модули остаются. Лимиты — 64 KiB
и 256 entries; traversal, reparse points, пропуски, вложенные индексы, повторные
ключи и неизвестная schema отклоняют весь bundle без частичной активации.
SDK reader и development publisher реализованы с регрессиями. Publisher
сохраняет private bytes, source/manifest/output hashes и транзакцию обычной
сборки; metadata/code не перезаписываются поздним модом. Старый выпущенный beta
EXE не объявляется поддерживающим новый формат. В кандидате 0.4.0b2 есть
reviewed capability profile точного runtime и отдельный игровой прогон.
[ADR-0017](adr/0017-independent-lua-module-bundles.md).
Общие игровые resources продолжают проходить Git merge с выбранным порядком.
SDK получает несколько module contexts из одного активного CC2-MCE package;
entry/require paths ограничиваются соответствующим code root, а доступ к
merged resources описывается явно. Исходный авторский standalone bridge.json
остаётся поддержан. Одна подписка или случайно найденная папка не активируют код.

Индекс сохраняет owner/local IDs, зависимости, порядок и hashes. Module execution
не пересортировывается по ID в обход GUI merge order. Числовые definition IDs
не должны сдвигаться от перестановки патчей. Для save/network нужны mapping и
catalog fingerprint; чужой catalog не принимается молча. Существующие ID теста
F-16/F-15 сохраняются при переносе того же каталога.

## Один источник активации для всех видов модулей

Нативные plugins и Lua host читают один startup snapshot активных
packages, полностью подготовленный до вызова первого plugin load. Порядок и
ошибки не могут расходиться между двумя загрузчиками. Перенесены ограничения
секции, исключение comments и предварительный snapshot из Bridge. C-core тест
проверяет path после active_mod_folders, comments, дубликаты и malformed input;
модульный discovery дополнительно проверяет manifests, границы путей и IDs.
Имя capabilities не должно маскировать неполную или недостоверную активацию.

## Мультиплеер и платформы

Общая база не даёт готовую сетевую репликацию. Gameplay-команды исполняет host,
проверяет права/сессию, рассылает итог через подтверждённые engine operations.
Waypoint publication уже исправлена в development аэродромов; docking/physics,
late join, save/reload требуют отдельного прогона.

Не обещаем, что всем модам достаточно SDK только на хосте: новые custom types
и client UI могут потребовать SDK и согласованный catalog у клиентов. Workshop
передаёт content, но не устанавливает автоматически native bootstrap.
Dedicated получает собственный проверенный executable profile и bootstrap;
client offsets не переиспользуются. UI модули должны отделяться от headless
компонентов. Windows/macOS desktop ModLoader не равен поддержке native SDK на Mac.

## Очерёдность реализации и приёмка

1. **Сделано:** устранена коллизия session ABI, общий C-префикс сверён; source
   extraction cc2mods фиксирует commit/SHA, не меняет upstream и не вендорит SDK.
2. **Разрешено владельцем:** Native Bridge и cc2mods — наработки своей команды;
   владелец явно подтвердил наличие всех разрешений на объединение. Перенос
   выполняется в существующий GPL-3.0-or-later SDK с сохранением исходного
   авторства и сторонних notices. Разрешения больше не блокируют работу.
3. **Сделано для development:** один Lua host и фасад, одна Zig 0.15.2 toolchain,
   source lock/notices, ABI и native profile regressions. Native SEH сохранён
   через отдельный C boundary, Visual Studio не нужен. Исследовательские probes
   и обход предупреждений несовместимости исключены из production runtime.
4. **SDK reader и ModLoader publisher реализованы:** module bundle/index сохраняет
   независимые code roots в одной папке. 27 regressions покрывают одинаковые имена,
   порядок, зависимости, disable/update, небезопасный input и rollback. Отдельный
   roundtrip проверен с настоящими bundled luac и C++ SDK reader, без исполнения
   авторского Lua. См. ADR-0017.
5. **Generic vehicle/UI перенесены.** F-16/F-15 выделен отдельным consumer
   в `cc2mods-separated/cc2-aircraft`, 57 исходных файлов с прежними IDs и ресурсами.
   Hold/Modes/Brake и аэродромы собираются с общим заголовком; Brake адаптирован
   к каноническому профилю без удаления PE/native-byte guards. Проверить пары
   и все поддержанные сочетания, независимость настроек и отсутствие конфликтов hooks.
6. **Проверен одиночный client-candidate:** одновременная загрузка всех модов,
   aircraft Lua lifecycle, реальные spawn и save/reload того же каталога. ADR-0020
   разрешает точные reviewed hashes в локальном кандидате с постоянным warning.
   Это не закрывает полный native release gate.
7. Обычный host+remote client и dedicated: permission, disconnect/reconnect,
   одинаковый catalog, late join и сетевой save/reload. Только затем полный
   public native release; dedicated требует своего executable profile/bootstrap.

Vanilla, EXE, Mod SDK и Workshop не меняются. Явно запрошенные игровые проверки
используют обратимую замену только известного runtime и generated output/activation;
публичная Windows beta не заменяется development сборкой. Source candidates не
объявляются готовым multiplayer-релизом.

## Фактическая проверка объединённого SDK

Обычный `build.py --test` собирает одну Windows x86 dinput8.dll и выполняет
19 C/C++/Lua SDK regression executables. Используются настоящий SDK и его Lua
facade, fake game API и собственные synthetic modules; авторские игровые
Lua/DLL в утилитах разработки не исполняются. Дополнительно пройдены 19 Python
проверок extraction/distribution/packaging. Контроль DLL исключает встроенные
сценарии F-16/F-15, research activation и marker обхода incompatibility policy.

Read-only проверка установленного EXE SHA `461e1262…effe42a` подтвердила PE,
lifecycle/throttle, Lua ABI, World API, 26 animation sites, hangar entries и UI
injection helpers. Это static profile evidence.

Свежий baseline запуск общего SDK подтвердил attach, legacy Island Airfields v45,
Lua integration и server ticks. Пользователь подтвердил обычное меню; runtime
0.5.1 затем восстановлен с проверкой exact hash.

Из чистых Git checkouts собраны SDK и четыре полных package-format candidates:
Hold copies, Modes, Manual landing brake, F-16/F-15. SDK не вложен в моды;
сохранены identities, лицензии, source/resource hashes и 57 исходных файлов aircraft.
API-prefix adaptations Hold/Modes имеют собственные failing-before regressions.
637/293/335 C checks относятся к fake game, а не к настоящей игре.

Совместный реальный запуск AI Bridge + Island Airfields v46 + Hold + Modes +
Brake + aircraft подтвердил загрузку четырёх plugins, два early vehicle definitions
без diagnostics и публикацию шести atlas regions. Итоговый прогон выполнен через
настоящий fixed-output workflow: 118 ресурсов, AI Bridge/Island Airfields overlap
обработан Git с явной отметкой overridden. Aircraft module on_load/on_update
работал в новом мире без ошибок Lua. После исправления definition hooks F-16/F-15
готовы как definitions 102/103 и реально созданы в ангаре carrier 2 (vehicles 5/6).
Новый save записан в пустой slot и загружен через игровой GUI; read-only snapshot
подтвердил прежние vehicle/definition IDs и docking. Повторный F-16 spawn после
reload (vehicle 7, session generation 2) успешен. Существующие saves не загружались.
После проверки прежние runtime, output, activation/Undo и save snapshot восстановлены.

ModLoader source также реализует reviewed config defaults (ADR-0018) и
transactional known-runtime upgrade/dependency fallback (ADR-0019). Неизвестный
runtime сохраняется; source settings не дают неизвестной DLL прав на запись.
В профиль client-candidate добавлены только точные проверенные native hashes;
shipped SDK SHA `ce4fc1c883c70af6c40f5431003d17584e9b2becb502ac840d22f73be9d7a7f3`
получен из clean SDK commit `2eecbd93c3555fed9a2b3f25e5b9c91abb55196f`.
Host/remote, dedicated, смена каталога определений между saves, полный полёт/посадка,
чистая ОС и macOS binary acceptance остаются отдельными незакрытыми gates.
Права команды не являются блокировкой. SDK не компилирует моды внутрь себя:
native DLL остаются отдельными plugins, Lua — отдельными контекстами.

Первая проверка нового мира выявила: module on_load/on_update работает без Lua
errors, но vehicle definitions не готовы. Loader/reset и name-map expansion
вызывались только из удалённого research probe. Два нужных generic hooks перенесены
в production definition adapter с теми же exact-byte guards; regression использует
сам production adapter, проверяет atomic install/abort, relocation и произвольный
размер каталога. Никакой F-16/F-15 policy или research activation в SDK не возвращено.
Исправленный runtime прошёл описанную выше повторную проверку нового мира,
реального spawn и save/reload. Это не доказательство remote multiplayer.
