# CONTRIBUTING

## Принципы работы

ТЗ и ADR — часть кода: изменение алгоритма/правил безопасности без обновления документов и тестов не принимается.

## Branch / PR convention

- Ветки: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `spike/<topic>`.
- PR описывает: проблему, ссылку на PRD requirement (FR-XX), решение, альтернативы, риски, тесты, затронутые форматы модов, обновлённые документы.
- При изменении публичного контракта (JSON schema, CLI, status) добавить/изменить ADR, миграцию или release note.
- Для security issues не прикладывать опасные архивы/исполняемые DLL и не публиковать личные пути.

## Технический запуск (только разработчикам и CI)

Пользовательская версия обязана работать через GUI без команд и ручной установки инструментов; эти инструкции не являются способом установки для игроков. Оконное приложение пока не реализовано, текущий срез — внутреннее ядро ([UX/UI](docs/13-UX-UI.md)).

Для разработки нужны Python 3.12+ и Git; для строгого Lua syntax smoke — `luac` именно 5.3. Подготовка окружения и проверки:

```text
uv sync --frozen --extra dev
uv run cc2-mce --version
uv run cc2-mce --config examples/mce.synthetic.toml build --dry-run
uv run pytest -q
uv run ruff check cc2_mce tests
uv run ruff format --check cc2_mce tests
uv run mypy cc2_mce
```

Альтернатива без uv: `python -m venv .venv`, активировать окружение средствами ОС и выполнить `python -m pip install -e ".[dev]"`. [uv.lock](uv.lock) фиксирует версии; CLI при scan/build ничего не скачивает.

[Синтетический пример](examples/mce.synthetic.toml) не содержит игровых assets: ожидаемый payload SHA-256 `40aaab939321f1fd22699ac0d8edd75cb7a219e73705e511f1027aa484617929`. Payload не записывается на диск, `installable` всегда false. Для реального developer-анализа нужен явный hash-bound baseline manifest и проверка executable; формат/аргументы — в [внутреннем CLI-контракте](docs/05-CLI-AND-DATA-CONTRACTS.md). Игрока нельзя просить составлять этот manifest: пользовательский GUI обязан проверять mapping сам и блокировать неподтверждённую базу.

Пока нет GUI, готовой desktop-поставки, installable packaging/rollback, replay plan, manual resolution и игрового smoke. Настроенный Windows/macOS workflow ещё не доказывает пройденную GUI-приёмку или доступность всех runtime; факты — в [M0 validation](docs/12-M0-VALIDATION.md).

## Требования к тестам

Начинать с synthetic fixture и ожидаемого результата; не добавлять чужие Lua/XML файлы из платной игры в публичный репозиторий без прав. Golden корпус отдельно от unit тестов, с фиксацией sha256 и версии merge backend.

## Документация

Добавление новых форматов сопровождается точной спецификацией ключей/взаимодействий; XML generic merge по любому id без schema review запрещён. Всё, что не подтверждено на игре, помечать `hypothesis`/`pending validation`.
