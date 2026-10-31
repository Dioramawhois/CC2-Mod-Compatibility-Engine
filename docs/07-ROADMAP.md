# 07. Roadmap и backlog

**Принцип:** подтвердить безопасное merge-ядро на реальных данных и параллельно подготовить простой графический сценарий; пользовательский MVP — только готовое приложение Windows/macOS без терминала, а не CLI. Базовый GUI и упаковка обязательны до первого пользовательского релиза; затем расширяется семантическое понимание. Указаны gates, не календарные обещания. См. [ADR-0007](adr/0007-gui-first-user-experience.md).

## Прогресс 0.1.0.dev1 (2026-10-26)

Реализован read-only вертикальный срез: CLI `doctor/scan/plan/build --dry-run/report`, строгий scanner, hash-bound baseline mapping, Git adapter + N-way preflight, синтетические regression tests, JSON schema и конфигурация. Есть Windows/macOS workflow, но удалённый запуск не подтверждён. Реальный Workshop просканирован без изменения источников; см. [M0 validation](12-M0-VALIDATION.md).

Ни M0, ни полный M1 не объявлены закрытыми: пока нет проверенного игрового baseline/game smoke, полной runtime-матрицы и Windows execution. GUI/готовая пользовательская поставка, packaging/rollback, plan replay, дополнительные Steam libraries, hunk diagnostics и ручные resolutions остаются впереди. CLI-срез — только инструмент разработки, не пользовательский MVP.

## M0 — Discovery spike / верификация игры [P0]

- [ ] Проверить локально версию CC2 и CC2X, папки `mod_dev_kit`, `mods.xml`, Workshop, local mods; не предполагать наличие CC2X или нативной CC2 на macOS.
- [ ] Утвердить минимальные версии Windows/macOS и архитектуры CPU; проверить Python, Git и Lua 5.3 validator, установку зависимостей и доступ к входным каталогам на обеих host-ОС.
- [ ] Взять 2-3 разрешённых к анализу Lua/XML мода; зафиксировать content layout и настоящий `mod.xml`.
- [ ] Найти 3 игровых файла, у которых две независимые правки и общий оригинал.
- [ ] Проверить `git merge-file -p` на одном реальном файле и что merged local mod виден в CC2.
- [x] Выбран тонкий Git adapter без переноса стороннего кода: [ADR-0006](adr/0006-read-only-first-slice.md). Игровой M0 spike остаётся обязательным.
- [ ] Проверить ограничения лицензий для распространяемых DLL и game assets.

**Exit:** есть документированный воспроизводимый proof-of-concept на двух модах и исходном файле; утверждена runtime-матрица Windows + macOS и проверен merge backend на обеих ОС. Совместимость самой игры на macOS остаётся отдельным фактом, требующим подтверждения.

## M1 — Merge core + developer CLI [P0, технический этап]

- [ ] Python packaging/project scaffold, lint/typecheck/tests CI Windows + macOS; установка и CLI smoke на обеих ОС.
- [ ] Проверки host-путей, Unicode/case collisions и одинакового payload/status на общих байтовых fixtures.
- [ ] `ModDiscovery` + `FileRegistry` + `BaselineResolver`.
- [ ] Hashing, deduplication, path canonicalization, collision detection.
- [ ] `GitMergeAdapter` и `MergeEngine` для N>=2; statuses/report.
- [ ] `scan`, `doctor`, `plan`, `build --dry-run`.
- [ ] Security: symlink/path traversal, atomic filesystem staging, stdout/stderr handling.

**Exit:** 100% основных synthetic goldens и проверяемый JSON report на Windows и macOS, одинаковые статусы/конфликты/хеши результата при фиксированных входах и инструментах; без installable output.

## M1-UI — Базовое графическое приложение [P0]

- [ ] Проверить UI toolkit и способ поставки на Windows/macOS: системные dialogs, доступность, фоновые задачи/отмена, runtime/backend/validator и лицензии; зафиксировать выбор ADR после runnable spike.
- [ ] Реализовать первый запуск, автопоиск/выбор папок и сохранение настроек без ручных конфигов.
- [ ] Показать список модов с названиями/авторами, выбором и поиском; проверку сочетания запускать кнопкой.
- [ ] Application service/структурированные результаты переиспользуют ядро без дублирования CLI и правил safety.
- [ ] Прогресс, безопасная отмена, простые причины блокировок, необязательные подробности/экспорт, клавиатура/масштаб/экранный диктор.
- [ ] Проверить GUI на synthetic fixtures; пока packaging нет, создание явно недоступно, результат не называется устанавливаемым.

**Exit:** read-only GUI полностью проходит сценарий выбора/проверки/ошибки/отмены на обеих ОС без терминала. M0 работа с реальной базой и M1 engine развиваются параллельно; GUI spike не разрешает обходить их gates.

## M2 — Safe packaging + GUI release + game validation [P0]

- [ ] Реальный `mod.xml` через верифицированный шаблон.
- [ ] Builder для локального `content/` (не редактируя моды-источники).
- [ ] Lua 5.3 parser/luac validation, XML well-formedness.
- [ ] Strict blocking для unresolved/native/binary/no-base.
- [ ] Полноценный build, Lua/XML validation, staging и rollback на Windows и macOS без обязательной Windows-эмуляции.
- [ ] Проверка в Carrier Command 2 на Windows singleplayer; игровой запуск на macOS — только при отдельно подтверждённом runtime/layout, без обещания поддержки CC2X.
- [ ] Подключить создание к GUI: актуальный проверенный план, безопасное назначение output, подтверждение, прогресс/отмена, открытие папки и инструкция включения/возврата.
- [ ] Готовые Windows/macOS приложения с проверенными runtime/Git/Lua 5.3 без ручных developer tools; проверить подпись/доверие ОС, notices/лицензии поставки.
- [ ] Clean-machine GUI/e2e и usability walkthrough на обеих ОС без обязательных команд, конфигов или установки зависимостей.
- [ ] Пользовательская инструкция только для окон/кнопок, включая включение мода штатным меню игры и восстановление; техническая CLI-инструкция остаётся у разработчиков.

**Exit:** обычный игрок проходит установку/выбор/проверку/создание/экспорт/восстановление через GUI на чистых Windows/macOS; CC2 запускает merged mod и обе функции A+B работают на подтверждённой игровой платформе. Safety/rollback проверены; CLI-only поставка M2 не закрывает.

## M3 — Usability / XML-aware merge [P1]

- [ ] KDiff3/manual resolver с hash-bound решениями.
- [ ] XML-merge по подтверждённым правилам идентификации узлов.
- [ ] Повторная сборка при обновлении модов и кэширование неизменных файлов.
- [ ] Improved reports: per-file provenance, HTML / diff links (опционально).

**Exit:** измеримо меньше ручных конфликтов, нет пропавших изменений на golden corpus.

## M4 — Lua AST merge / эксперимент [P2]

- [ ] `tree-sitter-lua` adapter; идентичность top-level functions/variables.
- [ ] Benchmark: Git vs AST на независимых добавлениях функций.
- [ ] AST parse safety; fallback на текстовый merge при неопределённости.
- [ ] Сравнить fork идей `semantic-merge` с новой собственной минимальной Lua-адаптацией (не переписывать полный AST engine без необходимости).

**Exit:** меньше false conflicts при сохранении всех golden safety invariants.

## M5 — CC2X bridge (отдельный проектный этап) [P2]

- [ ] Доказать жизнеспособность подмены ресурсной загрузки CC2X на конкретной поддерживаемой сборке.
- [ ] Спроектировать плагин/виртуальную ФС только после анализа API/hooks и loader-lock условий.
- [ ] Переоценить GPL-совместимость и модель распространения.
- [ ] Исследовать конфликты плагинов и мультиплеер отдельно, **не** заявлять поддержку заранее.

## Первые 10 issues

1. `P0: fixture с 2 модами, изменяющими один Lua`.
2. `P0: реальный CC2 mod.xml и version mapping`.
3. `P0: scan local/workshop`.
4. `P0: canonical paths + symlink test`.
5. `P0: verified baseline resolver`.
6. `P0: GitMergeAdapter subprocess`.
7. `P0: registry + N-way planner`.
8. `P0: structured conflicts + report schema`.
9. `P0: package staging + rollback`.
10. `P0: Windows game acceptance test`.
