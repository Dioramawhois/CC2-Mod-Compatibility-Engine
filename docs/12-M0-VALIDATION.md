# 12. M0: локальная проверка и неподтверждённые gates

## 0.2.1 — постоянный output и автоматический GUI (2026-11-02)

157 тестов прошли, 3 symlink fixtures пропущены из-за Windows privileges; Ruff и mypy Windows/darwin прошли (darwin static analysis не означает macOS execution). Установленная frozen сборка автоматически сохранила текущий состав Island Airfields + AI Bridge + SDK, заменила hash-output на `mods/CC2-MCE`, убрала прежние собственные активные/неактивные hash-пакеты в служебный cache. Payload hashes всех трёх файлов совпали с прежним активным пакетом. В GUI нет кнопок проверки/применения; фактическое состояние показано именами модов.

Свежий запуск CC2 с постоянной папкой подтвердил plugin load в cc2x.log; Toolhelp snapshot показал загруженный `mods/CC2-MCE/content/cc2x/cc2x_island_airfields.dll` и игровой dinput8.dll. Игра закрыта штатно, готовый GUI оставлен открытым. `build/evidence/20261101T221338Z/{auto-apply.json,runtime-evidence.json,package-report.json}` и `dist/CC2Engine.build.json` фиксируют scope/hashes. Текущий menu rendering отдельно не подтверждался, пользовательское подтверждение меню было на прежнем запуске идентичного merged Lua/native payload. Full flight/AI command gameplay, clean-machine/macOS execution gates остаются открытыми. [ADR-0010](adr/0010-checkbox-auto-apply-and-stable-output.md).

## Исторические результаты M0

**Дата:** 2026-10-26; дополнено 2026-10-28. **Статус:** частичное discovery, M0 не завершён. Это журнал проверяемых результатов первого среза, не отчёт об успешном запуске merged мода в игре.

## Подтверждено локально

### Windows package/runtime proof — 2026-11-01

- AI Bridge (3828182483) + Island Airfields (3826940003): SDK/runtime screen_vehicle_control.lua совпали raw hash `626e269b88bb35d870b5a69a017bfb728f74181c2be79f3c032c14bea14908aa`. LF-normalized настоящий Git дал clean, output hash `95b72ac1198e64369563b9dc45cfb64e4131c06f26fa30ef08cd31bcd9dd34a6`; luac 5.3.6 syntax-only прошёл. Обе авторские части кода сохранены.
- Plugin скопирован без изменения: SHA `60383f2845a5d5dc601f6196fb3716340aa0ca21437052ad1bbd7681b384591d`. Предоставленный SDK/content/dinput8.dll SHA `2453ba5a368943812954902685211db497d30d3052939f91d826d0c4883280ba` распознан и установлен, исходник сохранён.
- Создан и реально активирован отдельный combined mod. Свежий cc2x.log: CC2X 0.5.1, 1.5.18-win32-r2, Island Airfields v45 active и plugin loaded из `CC2-MCE: AI Bridge + Island Airfields`. Пользователь подтвердил видимое меню игры; захват изображения агентом не служит visual proof.
- После закрытия CC2 её сериализатор переписал отступы и повторил тот же active path. Recovery теперь сравнивает известную структуру/единственный distinct пакет; прежний mods.xml восстановлен в реальной установке, backups сохранены. Источники Workshop/SDK/rom_0 не изменялись; сохранения до запуска скопированы в локальное evidence, чужие assets в репозиторий не добавлены.
- Пределы: полёт/посадка, полный AI client command channel, macOS execution и чистая ОС не проверены. AI Bridge сам содержит авторский Windows command path другого профиля; это не исправляется догадкой в merge. Полный generic MVP не объявляется принятым на основании одного startup proof.

### Windows discovery/GUI (текущий прототип)

- Автопоиск через registry → libraryfolders.vdf → appmanifest_1489630.acf нашёл одну установленную CC2 и её Workshop без ручного ввода пути. В реальном Tk GUI автоматически показаны все 9 Workshop пакетов; локальные `mods`/`libraries` в установке отсутствовали и при поиске не создавались.
- На Windows пройдены synthetic discovery и Tk regression tests; новая exe-сборка включает schema/исходники для engine hash. Проверки путей для Darwin есть на fixtures и mypy, но не заменяют запуск на macOS.
- Игра и native DLL не запускались, vanilla/SDK/Workshop/mods.xml/dinput8.dll не изменялись. Build mapping, реальный Lua 5.3, package/runtime и полный игровой smoke остаются неподтверждёнными. Discovery не означает, что `rom_0` или SDK автоматически признаны корректной базой.

### Исторические проверки первого среза

- macOS host: доступна установка `carriercommand.app` в стандартной Steam library; внутри обнаружены `Contents/Resources/rom_0/scripts`. Это не доказательство, что runtime-ресурсы подходят как baseline текущей сборки.
- В одном легитимно установленном Workshop-моде прочитаны metadata `<data name="…" author="…" description="…">` и layout `content/game_objects/*.xml`. Перед XML declaration есть пустая строка; read-only metadata adapter допускает этот вариант без переписывания файла. Содержимое assets не копировалось в проект.
- `cc2-mce scan` прочитал 9 установленных Workshop-модов, 135 игровых ресурсов. Это inventory, не утверждение совместимости модов. Полные пользовательские пути и чужие игровые assets не включены в документацию.
- Git: `2.50.1 (Apple Git-155)`; Python локальных тестов: 3.13.12, macOS arm64. Реальный `git merge-file` проверен на synthetic clean/conflict/N-way случаях.
- Установленный `luac` сообщает **5.5.0**, не требуемую 5.3. Для Lua анализ обязан выдавать review blocker; настоящий синтаксический smoke Lua 5.3 не пройден. Subprocess boundary проверяется отдельными тестами с mock.

### Дополнение: Mac runtime, 2026-10-28

- В одной локальной Steam-установке обнаружены **два** `x86_64` executable: внешний `carriercommand.app/Contents/MacOS/build_mac` со строкой `v1.5.17`, SHA-256 `53d8bb02e0fb2b3be764f5d49f8a0e60cf83819ba704e31f3ce75cdef66fd823`, и вложенный `carriercommand.app/build_mac.app/Contents/MacOS/build_mac` со строкой `v1.5.18`, SHA-256 `053f026b63ff9611a2eb28fb583031ef091200efc6d8cab1487121575d107b7f`. `CFBundleShortVersionString=1.0` не используется как версия игры.
- Кнопка Steam Play 2026-10-28 запустила внешний путь `v1.5.17`; локальный кэш Steam указывает `carriercommand.app`. Вложенный `v1.5.18` запустился напрямую и был отмечен Steam как запущенная игра. Почему обе версии оказались в одной установке, не подтверждено.
- При **прямом запуске** игры с `DYLD_INSERT_LIBRARIES` тестовая `x86_64` dylib выполнила конструктор внутри процесса. Внутри процесса через `dlsym` разрешились `lua_gettop` и `lua_pushcclosure`. После проверки игра завершена, executable hash не изменился; файлы игры и модов не редактировались.
- Разбор Ghidra показал, что `mm_lua::reset` создаёт Lua state и **выполняет скриптовые модули до возврата**. Для `cc2x` API нужен hook до первого выполнения модуля. Статические кандидаты для lifecycle из файлов CC2X пока не подтверждены вызовами в игре. Подробнее: [исследование Mac runtime](15-MAC-RUNTIME-FEASIBILITY.md).
- Developer spike [Mac Lua bridge](../experiments/mac_runtime/README.md) установил отдельный guarded hook до `luaL_loadbufferx` в **обеих** версиях. Каждая создала 20 Lua-состояний; каждая дала **20 PASS, 0 FAIL** в самопроверке. На отдельном неподдерживаемом `x86_64` executable хеш-guard отключил hooks, процесс завершился нормально. Это не доказывает работу реального мода, инъекцию через Steam Play или полноценный сеанс.

## Проверка первого среза

- `uv sync --frozen --extra dev`: окружение восстановлено по lock.
- `pytest -q`: **84 passed** на локальной macOS/Python 3.13.12.
- Ruff lint и format-check: успешно; mypy strict: без ошибок в 12 исходных модулях; `pip check` и `uv lock --check`: успешно.
- Wheel собран, установлен в отдельное временное окружение вне проекта; entry point, packaged JSON schema и synthetic golden CLI проверены. Временные данные удалены, публичная публикация не выполнялась.
- Повторный read-only scan 9 модов/135 ресурсов дал тот же агрегированный fingerprint: изменений отслеживаемых источников во время проверки не обнаружено.
- `doctor` корректно возвращает exit 5 для несовместимого Lua 5.5 вместо требуемого 5.3, не создавая installable output.

## Не подтверждено

- `CFBundleShortVersionString` сообщает `1.0` для обоих app bundles; игровые версии определяются по executable. Их соответствие Mod SDK и Windows-сборке не подтверждено.
- `mod_dev_kit` не найден в ограниченно проверенных каталогах; это не доказывает его отсутствие на всей машине. Mapping SDK -> runtime и набор оригинальных Lua/XML ещё не подтверждены.
- Нет реального merge на проверенной базе, генерации/активации пакета, game smoke, rollback или проверки нативного plugin loader. Текущий Mac spike даёт только API 0, без world/session hooks и загрузки плагинов.
- Нет выполненного Windows запуска или удалённого CI. Workflow задан для Windows/macOS и Python 3.12/3.13; это тестовая кандидатная матрица, не гарантия поддержки всех версий ОС/CPU.
- Полноценный игровой smoke на Mac, инъекция через Steam Play/GUI, Steam overlay/cloud/multiplayer, схема output mod.xml и требования пакета должны проверяться отдельно. Краткий прямой запуск процесса для инъекционного probe не равен прохождению игрового acceptance.

## Что работает без закрытия M0

Read-only CLI 0.1.0.dev1 и synthetic golden: `uv run cc2-mce --config examples/mce.synthetic.toml build --dry-run`. Результат: `clean`, обе независимые правки сохранены, SHA-256 `40aaab939321f1fd22699ac0d8edd75cb7a219e73705e511f1027aa484617929`, `installable: false`. Исходники и baseline не переписываются, output directory не создаётся.

## Следующие обязательные шаги

1. Получить и проверить оригинальный SDK той же сборки; составить явный hash-bound baseline manifest без копирования модифицированных файлов в базу.
2. Подтвердить mod.xml/output layout и полноценный запуск игры с минимальным законным локальным модом; проверить прямой запуск через будущий GUI и Steam-сервисы.
3. Обеспечить Lua 5.3 validator для обеих host-ОС, выполнить реальные format tests.
4. Выполнить Windows/macOS CI, утвердить минимальные версии ОС и CPU-архитектуры.
5. Только затем реализовывать PackageBuilder с atomic staging, rollback и ручным игровым smoke; до этого не объявлять пакет устанавливаемым.
