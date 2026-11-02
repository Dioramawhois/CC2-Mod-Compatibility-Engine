# 22. Общий CC2X SDK и отдельные моды

Решение владельца: 2026-11-02. Развиваем существующий CC2X, сохраняя его runtime
ID `cc2x.runtime`. ModLoader и Island Airfields сохраняют свои проекты и Workshop
идентичности. Это карта переноса; объединённый runtime ещё не реализован.

## Границы продуктов

| Проект | Содержимое |
|---|---|
| CC2X SDK | Один bootstrap/runtime, проверенные профили игры, hooks/transactions, world API, server sessions, очереди команд; после согласования условий — Lua host, публичный cc2 API, общие registry/UI/resource операции из Bridge |
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
отдельным поставщиком конкурирующей dinput8.dll: его runtime-компоненты после
разрешения условий переноса становятся модулями общего SDK.

Общий C-префикс API 4 сохранён. API 5-8 Bridge нельзя механически приклеить к
нашему заголовку: хвосты расходились. Сессионное расширение v1 уже переведено
на именованный query с проверкой ABI. Новые capabilities делаются по тому же
принципу; signatures и release contracts публикуются после реализации и тестов.
Bridge Host/SDK wrappers адаптируются на согласованный API, неизвестные старые
binary layouts не принимаются автоматически. `cc2x` остаётся совместимым Lua
интерфейсом; `cc2` — фасад для новых модов, после реального переноса host.

Планируемые общие компоненты Bridge: `src/runtime` (host, mod discovery,
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

Для cc2mods подготовлены три отдельных исходных проекта. Из upstream сохранены
byte-identical C sources/tests/config examples, GPL и авторство Yolo /
totolerigolo118. Старые UI generators сохранены как reference. Небезопасные
installer/game-launch scripts не включались. Исходники F-16/F-15 и других Bridge
mods сейчас только инвентаризованы, без публичного копирования assets.

Все три plugin DLL собраны через один внешний SDK. Исходные C fixtures прошли:
Hold — 636 проверок, Modes — 292, Brake — 334; всего 1262, без ошибок. Это fake
game/API tests, а не запуск DLL в игре. Четыре теста extraction также прошли.

При разборе Brake обнаружена отдельная интеграционная несовместимость:
upstream ожидает `1.5.18-win32-6ae228f3`, наш SDK возвращает `1.5.18-win32-r2`.
Сам PE timestamp совпадает, но плагин намеренно проверяет оба признака и может
отказаться загружаться. До runtime-поставки нужен общий контракт профиля,
основанный на проверенном executable fingerprint, и regression его consumer.
Строковые display names не должны становиться неявным ABI. Проверки bytes/PE
ради совместимости не отключаются. Исходный plugin сохранён byte-identical;
его адаптация будет отдельным проверяемым изменением.

Первый результат — source separation и сборка native plugins, не готовые player
packages. Для Hold и Modes нужно закончить генерацию UI из легальной локальной
игры; для Brake исходный standalone mod folder ещё не существовал. Новые
Workshop IDs не придумываются. Публикация обновлений существующих items — после
полного package/runtime acceptance.

## Сборный output ModLoader должен сохранять границы Lua-модулей

Это обязательная доработка перед включением нескольких Bridge модов вместе.
Сейчас Bridge выбирает один bridge.json на активный игровой package. Если
объединить два `content/bridge.json` и `bridge/main.lua` обычным приоритетом
файлов, один мод исчезнет либо смешается с другим. Так делать нельзя.

Целевой bundle сохраняет отдельный code namespace для каждого исходного мода,
например `content/cc2x-modules/<stable-package-id>/...`, и явный индекс модулей
в metadata сборки. Это проектируемый контракт, пока не реализованный формат.
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
2. **Сейчас:** сохранить точные условия разрешения на Bridge. Владелец сообщил,
   что разрешение есть и уточнит условия. До этого его собственный код/assets
   не публикуются в общем GPL SDK.
3. Перенести один Lua host и фасад без gameplay; одна toolchain/build matrix,
   source lock/notices, ABI и native profile regressions.
4. Сделать module bundle/index и проверку нескольких модов. Регрессия обязательна:
   два одинаковых entry filename и local ID не должны терять одну из реализаций;
   disable/reorder/dependency cycle проверяются через публичный SDK.
5. Перенести generic vehicle/UI capabilities. Отдельно собрать F-16/F-15 как
   consumer SDK, затем Hold/Modes/Brake и существующие аэродромы. Проверить пары
   и все поддержанные сочетания, независимость настроек и отсутствие конфликтов hooks.
6. Обычный host+remote client и dedicated: permission, disconnect/reconnect,
   одинаковый catalog, late join и save/reload. Только затем public native release
   и новые reviewed hashes в ModLoader.

Исходная установленная игра, активные моды и публичная Windows beta в ходе
этой подготовки не меняются. Подготовленные source projects не объявляются
установленными модами или проверенным мультиплеером.
