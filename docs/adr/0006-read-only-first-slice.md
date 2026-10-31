# ADR-0006: Тонкий Git adapter и read-only первый срез

- **Статус:** Accepted как технический developer-срез 0.1.0.dev1; игровые gates M0 открыты. Пользовательский продукт — обязательный GUI по [ADR-0007](0007-gui-first-user-experience.md), не этот CLI-прототип.
- **Дата:** 2026-10-26
- **Уточняет:** ADR-0002, CLI/JSON контракт v1

## Контекст

Есть спецификации, локальная установка CC2 macOS и Workshop-моды. Подтверждённого SDK mapping, Lua 5.3 validator и игрового acceptance пока нет. Нельзя безопасно объявлять произвольный каталог ванильной базой или создавать устанавливаемый пакет по выдуманному mod.xml.

## Решение

1. Первый исполнимый срез — `doctor`, `scan`, `plan`, `build --dry-run`, `report`; `build` без dry-run и plan replay пока явно отклоняются. Все отчёты имеют `installable: false`, payload остаётся только в памяти/временных Git-копиях.
2. Реализовать собственный тонкий Python adapter к `git merge-file -p`, без форка или переноса Witcher-specific кода w3scriptmerge. Архитектурная идея общей базы сохраняется; сторонний код не копируется. Это решение не заменяет игровой spike.
3. При N модах выполнить попарный Git preflight относительно общей базы, затем последовательный accumulator с той же базой. Первый конфликт блокирует файл. Exit 0/1..127/остальные различаются как success/conflict/tool error; timeout и subprocess без shell обязательны.
4. База принимается только по явному `baseline-manifest.json`: schema v1, kind, game identity, logical-to-source mapping и действительные SHA-256. `kind: game` дополнительно требует совпадения явно переданного executable hash. Происхождение и принадлежность SDK всё ещё проверяются M0: пользовательский mapping не является подписью доверенного издателя.
5. `kind: synthetic` допускает только synthetic game version, в отчёте помечается unverified для игры. Неполный mapping не доказывает отсутствие ресурса; разные немаппированные версии дают `no_base`. Не генерировать фиктивную пустую базу.
6. Fail-closed text allowlist UTF-8/BOM с единым LF/CRLF; Lua только syntax subprocess `luac` 5.3, XML с запретом DTD/entities. DLL и содержимое cc2x блокируются даже в unique/dedup. Входы имеют лимиты, path/case/Unicode checks и повторное hash-сравнение после анализа.
7. JSON report v1 проверяется локальной packaged schema через jsonschema. Source/base/output/engine hashes, tool versions, policy и mod_order сохраняются. Отчёт пишется только новым файлом вне источников, без overwrite. Для schema нет удалённых refs.
8. Python >=3.12; lock dev/runtime и Windows/macOS CI добавляются сразу. Локальная проверка macOS не считается выполненной Windows CI или полным M0/M1. Минимальная release-матрица ОС/архитектур ещё требует верификации.

## Последствия

+ Можно проверить safety-отказы, настоящий Git и воспроизводимость на synthetic corpus без записи в игру или Workshop.
+ Нет зависимости от Windows API, CC2X или Lua execution; game data не включаются в репозиторий.
- Нет installable пакетов, staging/rollback, hunk preview, whole-file deletion tombstones, manual resolution/cache или replay plan.
- Поиск дополнительных Steam libraries и полная runtime-матрица отложены; каталоги можно задавать явно.
- Снимки/повторные хеши обнаруживают изменения при анализе, но не заменяют защищённый publish boundary и полноценные race-tests M2.

## Проверки

Регрессионные тесты воспроизводят требования до реализации; synthetic golden сравнивает SHA-256 payload. Реальные Workshop данные допускаются только для локального read-only scan, без копирования assets. Packaging и game smoke остаются обязательными отдельными gate; см. [M0 validation](../12-M0-VALIDATION.md).
