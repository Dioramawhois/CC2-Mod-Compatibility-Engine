# ADR-0008: Автопоиск игры и коллекции модов/библиотек

- **Статус:** Accepted для discovery/GUI. Runtime и игровой packaging остаются открытыми gates.
- **Уточняет:** ADR-0006 (Steam libraries), ADR-0007 (первый запуск), discovery в плане 14.

## Решение

1. Сначала проверяется игра рядом с приложением: frozen Windows использует каталог `sys.executable`, не cwd/временную папку PyInstaller. Затем читаются зарегистрированные Steam roots, `libraryfolders.vdf` и `appmanifest_1489630.acf`. Поддержаны современный и старый quoted KeyValues, дополнительные диски, пробелы и Unicode. Соседняя игра имеет приоритет; несколько остальных установок требуют выбора в GUI.
2. Windows portable exe должен находиться рядом с `carrier_command.exe`. Из другой папки приложение находит игру и показывает, куда перенести exe; анализ и запуск игры до переноса заблокированы. Самокопирования в игру нет. Это ограничение не требует помещать будущую macOS `.app` внутрь игрового bundle; общие discovery/validation правила совпадают.
3. Workshop читается на месте: `<SteamLibrary>/steamapps/workshop/content/1489630/<id>/content`. Дополнительно читается `<game>/mods/<id>/content`. Источники не переносятся/переименовываются. Совпадение ID в разных коллекциях блокируется, не задаёт приоритет.
4. `<game>/libraries/<id>/content` — отдельная коллекция библиотечных пакетов. Используются существующие content/mod.xml правила, Lua и DLL различаются по фактическим ресурсам. Плоский каталог случайных DLL/Lua не считается готовым пакетом. Зависимости и порядок загрузки не выводятся из догадок.
5. Только кнопка «Подготовить папки» создаёт `mods` и `libraries` под выбранной игрой. Существующие файлы и ссылки/junction блокируются; автопоиск ничего не создаёт. Vanilla/SDK, Workshop, mods.xml, executable и dinput8.dll не изменяются.
6. Целевая модель: один runtime-загрузчик `dinput8.dll`, отдельные native plugins, Lua как проверяемые ресурсы. DLL не сливаются и не перекомпилируются. Текущий CC2X читает `content/cc2x` включённых модов; `<game>/cc2x/plugins` — developer fallback, не поддержка произвольной libraries. Профильный reader/переупаковка, companion assets/plugin_dir требуют отдельного spike и game smoke. Здесь DLL не загружаются и блокируют автоматическую сборку.
7. Найденный executable подтверждает расположение, не game build/vanilla mapping. Создание synthetic baseline из установленных скриптов удалено из GUI. Создание игрового пакета отключено до baseline/backend/validation/staging gates; есть только read-only анализ. JSON schema v1 и developer CLI аргументы не меняются.
8. Поиск/scan/анализ работают вне Tk thread; смена выбора инвалидирует старый результат. Metadata ограничены 1 MiB, 8192 токенами, глубиной 16 и 64 Steam libraries; используются существующие filesystem adapters. Невалидная Steam metadata показывает предупреждение, неподтверждённый путь не становится установкой.

## Проверки и пределы

Fixtures покрывают дополнительные Steam libraries, legacy VDF, appid, traversal/DoS/encoding, отсутствующий executable, ссылки (если ОС разрешает fixture), выбор установки и подготовку папок. Реальные Tk widgets проверяют Workshop/local имена, Lua/DLL inventory, отказ, фоновые результаты и invalidation. На этой Windows-машине read-only поиск нашёл одну установленную игру и 9 Workshop пакетов; GUI показал все 9. Это не game smoke, clean-machine, macOS execution или работающий runtime/пакет.

Upstream: [CC2X PLUGINS](https://github.com/Dioramawhois/Carrier-Command-2-extender/blob/main/docs/PLUGINS.md). План 14 остаётся проектом за пределами принятых здесь discovery-решений.
