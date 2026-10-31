# 12. M0: локальная проверка и неподтверждённые gates

**Дата:** 2026-10-26; дополнено 2026-10-28. **Статус:** частичное discovery, M0 не завершён. Это журнал проверяемых результатов первого среза, не отчёт об успешном запуске merged мода в игре.

## Подтверждено локально

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
