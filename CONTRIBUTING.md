# CONTRIBUTING

## Принципы работы

ТЗ и ADR — часть кода: изменение алгоритма/правил безопасности без обновления документов и тестов не принимается.

## Branch / PR convention

- Ветки: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `spike/<topic>`.
- PR описывает: проблему, ссылку на PRD requirement (FR-XX), решение, альтернативы, риски, тесты, затронутые форматы модов, обновлённые документы.
- При изменении публичного контракта (JSON schema, CLI, status) добавить/изменить ADR, миграцию или release note.
- Для security issues не прикладывать опасные архивы/исполняемые DLL и не публиковать личные пути.

## Технический запуск (только разработчикам и CI)

Пользовательская версия обязана работать через GUI без команд и ручной установки инструментов; эти инструкции не являются способом установки для игроков. Есть тестовый GUI поиска/анализа; готовая пользовательская поставка ещё требует [UX/UI gates](docs/13-UX-UI.md).

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

Windows package/activation/rollback и bounded game startup проверены в 0.2.0. Replay plan, manual resolution, полноценный gameplay, macOS и clean-machine/accessibility gates ещё не подтверждены. Настроенный Windows/macOS workflow не заменяет эту приёмку; факты — в [M0 validation](docs/12-M0-VALIDATION.md).

## Сборка Windows exe для разработчиков

**0.2.0:** результат называется `dist/CC2Engine.exe`; приведённые ниже записи о 0.1.0 — история первого packaging spike. Bat при необходимости запускает `tools/prepare_windows_tools.py` (developer Git + Zig), затем regression suite, PyInstaller и frozen tool/GUI smoke. В exe входят hash-verified Git/Lua; пользователю устанавливать инструменты не нужно. Исходник Lua скачивается только при developer build и проверяется по официальному фиксированному SHA до extraction/compilation. Binary dependencies/notices/source references Git и Lua хранятся в сгенерированном tools_data; их integrity manifest включён в engine hash. Существующий `uv.lock` фиксирует Python dependencies; exact native tool hashes находятся в manifest.

Новый сервис `workflow.py` и schema v2 публикуют игровой пакет и выполняют явную обратимую активацию; raw developer CLI output не заменяет этот путь. SDK XML: [17](docs/17-LIBRARY-SDK.md). `tools/exercise_real_pair.py` / `launch_real_pair.py` — отдельный **изменяющий игру** локальный harness конкретно разрешённого пользователем теста AI Bridge + Island Airfields, не CI и не команда для игрока. `install_local_build.py` устанавливает только этот собственный exe с backup предыдущей известной сборки. Никогда не запускать эти harness на чужой установке без соответствующего запроса.

Текущий portable workflow и пакеты `mods`/`libraries`: [ADR-0008](docs/adr/0008-portable-discovery-and-library-collections.md). Для запуска исходников остаётся `python -m cc2_mce.gui` (только разработчикам). Тесты реального Tk display помечают недоступную среду как skip; это не macOS GUI acceptance. Автопоиск ничего не создаёт, два собственных каталога создаются только явным действием в окне.

После упаковки bat запускает `tools/check_windows_bundle.py`: проверка packaged source/schema, открытие и закрытие GUI без developer tools в PATH и запись `dist/CC2ModLoader-0.1.0.build.json` с artifact/engine/source/build-input hashes, `base_sha256: null`, `mod_order: []`. По умолчанию helper не сканирует настоящие моды. Необязательный developer-флаг `--inventory` добавляет read-only обнаружение реальной игры/Workshop и входные хеши; игра и плагины не запускаются. Наличие exe/build.json не закрывает игровые gates.

`build_windows.bat` использует Python 3.12+ из PATH или Windows launcher `py -3`, создаёт/переиспользует `.build-venv`, устанавливает проект и PyInstaller 6.22.3, запускает регрессии и собирает `CC2ModLoader-0.1.0.spec`. Скрипт переходит в каталог репозитория независимо от исходного рабочего каталога. Без аргументов оставляет результат/ошибку на экране; для автоматизации есть `build_windows.bat --no-pause` с сохранением кода завершения. Это подготовка developer-машины, не шаги для игрока.

Результат — `dist/CC2ModLoader-0.1.0.exe`, one-file GUI без консоли. Spec включает локальную JSON-схему и исходники пакета: `engine_hash()` должен совпадать в исходниках и распакованной поставке. Тест `tests/test_windows_bundle.py` проверяет это в build-окружении; без PyInstaller он явно пропускается. Контракт отчёта v1 не изменён. Проверка 2026-10-29: Windows 10 x64, Python 3.14.0, 93 passed / 2 skipped (создание symlink недоступно), Ruff и mypy проходят.

Локально проверены открытие и штатное закрытие окна из отдельного временного каталога с PATH только системных каталогов Windows; байты packaged schema/source сверены с исходниками. Рядом с текущим артефактом сохранён локальный `*.build.json` с SHA-256 exe/движка/источников и пределами проверки. Это не чистая ОС, не игровой тест и не подтверждение macOS. Git и Lua validator не включены, пользовательские release gates остаются открытыми; Python runtime и tkinter включены PyInstaller. Версии остальных build/runtime зависимостей пока не закреплены отдельным distribution lock.

## Требования к тестам

Начинать с synthetic fixture и ожидаемого результата; не добавлять чужие Lua/XML файлы из платной игры в публичный репозиторий без прав. Golden корпус отдельно от unit тестов, с фиксацией sha256 и версии merge backend.

## Документация

Добавление новых форматов сопровождается точной спецификацией ключей/взаимодействий; XML generic merge по любому id без schema review запрещён. Всё, что не подтверждено на игре, помечать `hypothesis`/`pending validation`.
