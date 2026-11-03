# 22. Общий CC2X SDK и отдельные моды

Решение владельца: 2026-11-02. Развиваем существующий CC2X, сохраняя его runtime
ID `cc2x.runtime`. ModLoader и Island Airfields сохраняют свои проекты и Workshop
идентичности. Объединённый development runtime уже собирается; текущие проверки
и оставшиеся ограничения описаны ниже. Это ещё не готовый игровой релиз.

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
EXE не объявляется поддерживающим новый формат. До реальной активации нужен
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
4. **SDK reader сделан; ModLoader publisher остаётся:** module bundle/index и
   проверка нескольких модов. Регрессия:
   два одинаковых entry filename и local ID не должны терять одну из реализаций;
   disable/reorder/dependency cycle проверяются через публичный SDK.
5. **Generic vehicle/UI перенесены.** F-16/F-15 выделен отдельным consumer
   в `cc2mods-separated/cc2-aircraft`, 57 исходных файлов с прежними IDs и ресурсами.
   Hold/Modes/Brake и аэродромы собираются с общим заголовком; Brake адаптирован
   к каноническому профилю без удаления PE/native-byte guards. Проверить пары
   и все поддержанные сочетания, независимость настроек и отсутствие конфликтов hooks.
6. Обычный host+remote client и dedicated: permission, disconnect/reconnect,
   одинаковый catalog, late join и save/reload. Только затем public native release
   и новые reviewed hashes в ModLoader.

Исходная установленная игра, активные моды и публичная Windows beta в ходе
этой подготовки не меняются. Подготовленные source projects не объявляются
установленными модами или проверенным мультиплеером.

## Фактическая проверка объединённого SDK

Обычный `build.py --test` собирает одну Windows x86 dinput8.dll и выполняет
18 C/C++/Lua SDK regression executables. Используются настоящий SDK и его Lua
facade, fake game API и собственные synthetic modules; авторские игровые
Lua/DLL в утилитах разработки не исполняются. Дополнительно пройдены 10 Python
проверок source extraction/distribution. Контроль DLL исключает встроенные
сценарии F-16/F-15, research activation и marker обхода incompatibility policy.

Read-only проверка установленного EXE SHA `461e1262…effe42a` подтвердила PE,
lifecycle/throttle, Lua ABI, World API, 26 animation sites, hangar entries и UI
injection helpers. Это static profile evidence; новый runtime ещё не проверен
свежим запуском игры. Новые native hashes в trusted profiles не добавлены.
Host/client, dedicated, каталог сохранений и полный ModLoader publisher остаются
незакрытыми. Права команды больше не являются блокировкой.
