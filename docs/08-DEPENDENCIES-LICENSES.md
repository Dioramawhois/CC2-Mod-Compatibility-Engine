# 08. Исследование готовых решений, зависимостей и лицензий

## 1. Решение «не писать merger с нуля»

| Проект | Роль | Лицензия / оговорка | Решение |
|---|---|---|---|
| [apocalyptech/w3scriptmerge](https://github.com/apocalyptech/w3scriptmerge) | Python 3 CLI: поиск пересекающихся файлов, работа с базовым скриптом, N-way merge через GNU diff3 | BSD-3-Clause (`COPYING.txt`) | **Приоритетный референс/кандидат на форк**, окончательный fork vs reimplementation после M0 spike |
| [git merge-file](https://git-scm.com/docs/git-merge-file) | Надёжный готовый текстовый 3-way merge | Внешний Git binary: проверить bundled distribution/обязательства при упаковке | **MVP merge backend**, вызывает subprocess |
| [libgit2 `git_merge_file`](https://libgit2.org/docs/reference/main/merge/git_merge_file.html) | In-memory native merge без Git-репозитория | GPLv2 с linking exception (проверять точный текст и библиотеки сборки) | Альтернатива на этапе native bridge/перфоманса |
| [KDE/KDiff3](https://github.com/KDE/kdiff3) | GUI/manual three-way conflict resolution | GPL-лицензию и поставку сверять с конкретным релизом | P1: внешний инструмент, не встраивать сразу |
| [gaurvinayak/semantic-merge](https://github.com/gaurvinayak/semantic-merge) | AST 3-way merge, tree-sitter, CLI JS/TS | MIT; **Lua не заявлена** | P2 эксперимент/архитектурные идеи, **не** готовый Lua merger |
| [pjominet/w2sm](https://github.com/pjominet/w2sm) | Witcher 2 GUI, merge workflow, packaging | README называет «MIT License - Non-Commercial»: нестандартное ограничение, осторожно | Анализ UI/UX, **код не переносить** без правовой проверки |
| [AnotherSymbiote/WitcherScriptMerger](https://github.com/AnotherSymbiote/WitcherScriptMerger) | Сканирование, XML/.ws, KDiff3, package | GPL-2.0, внешние зависимости отдельно | Архитектурный пример, не default codebase |
| [Dioramawhois/Carrier-Command-2-extender](https://github.com/Dioramawhois/Carrier-Command-2-extender) | CC2 native API / hooks / Lua | GPL-3.0-or-later; автор указывает требования к исходному коду плагинов | P2 bridge, не зависимость MVP |
| tree-sitter-lua / Lua 5.3 validation | Lua structural analysis and syntax | Уточнить точные пакеты, версии, licences при внедрении | P2 / validator на MVP |

**Важно:** таблица отражает проверенные README и лицензии по состоянию на 2026-10-25. **Не** утверждает, что все эти компоненты юридически совместимы при механическом копировании в один бинарник.

## 2. Почему fork w3scriptmerge — условный, а не безоговорочный

Плюсы: простой Python, хорошая объектная модель `base + mod versions + merged`, готовая N-way итерация. Минусы: работает с `.ws` и Witcher 3, использует GNU `diff3`, содержит game-specific сканирование bundle/encoding. Более того, авторский код распознаёт конфликт по наличию имени временного каталога в выводе — наш pipeline **должен** опираться на exit-status/structured diagnostics, а не наследовать этот эвристический критерий.

**Decision gate M0:** сопоставить трудоёмкость чистого адаптера с форком. Если ~70% исходника окажется Witcher-specific — брать архитектурную идею и Git backend, не форкать весь скрипт. При заимствовании кода сохранить BSD notice/copyright.

## 3. Пакетирование и лицензия CC2-MCE

**Лицензия репозитория — GPL-3.0-or-later**, выбрана владельцем 2026-11-02; полный текст в LICENSE. Сторонние компоненты сохраняют свои лицензии. В первом срезе есть собственный Python-код, без vendored upstream исходников; нельзя выдавать LICENSE-файл без решения автора. До выбора лицензии не публиковать пакет.

Если будет создан плагин через `cc2x.h`, ориентироваться на опубликованные условия **GPL-3.0-or-later / GPL-compatible с исходниками плагина**, не думать, что изолированный Python CLI автоматически обязан становиться GPL из-за будущего моста.

**Нельзя:** переупаковывать чужие DLL, авторские assets модов или файлы игры для публичного распространения без проверки прав. Локальная сборка для личного применения и публичное распространение — разные модели использования.

## 4. Version pinning и dependency gates

- Версию Python/пакетного менеджера выбрать в M0 и фиксировать в `pyproject.toml` + lock-файле; одна поддерживаемая runtime-матрица для Windows и macOS с явными минимальными версиями ОС и архитектурами CPU.
- Все обязательные зависимости CLI и сборки, включая Git и Lua 5.3 validator, должны работать на обеих ОС без Windows-эмуляции. Описать установку и проверить доступность/лицензии конкретных версий для каждой ОС/архитектуры; Windows-only зависимости не допускаются в общем pipeline.
- Проверить `git --version`, documented behavior exit codes и одинаковый merge-результат на Windows и macOS.
- Записывать версии внешних инструментов в manifest и CI.
- Для `tree-sitter-lua` в P2 зафиксировать grammar commit/версию (иначе не воспроизводится AST).
- Не скачивать бинарные зависимости по непроверенным URL при `cc2-mce build`.

## Зависимости первого среза

Python >=3.12; runtime `jsonschema` (MIT) для локальной валидации собственного отчёта, без загрузки удалённых схем. Dev: pytest (MIT), Ruff (MIT), mypy (MIT), types-jsonschema (Apache-2.0). Версии/транзитивные зависимости зафиксированы в [uv.lock](../uv.lock), проверка лицензий всей поставки остаётся release gate. Git и `luac` — внешние инструменты, не поставляются внутри пакета. Установка зависимостей происходит отдельно, scan/build сеть не используют. Собственный тонкий Git adapter выбран в [ADR-0006](adr/0006-read-only-first-slice.md).

## Поставка графического приложения (обязательный P0)

Текущий developer-срез использует внешние Git/luac; это не модель установки для игроков. Пользовательская Windows/macOS поставка должна включать проверенные runtime, Git backend и Lua 5.3 validator для каждой поддерживаемой ОС/архитектуры, без ручных developer tools, настройки PATH или скачиваний при первом запуске. Собственный merge вместо Git ради упаковки не вводится.

Перед выбором GUI toolkit/упаковщика проверить лицензию, доступность, системные диалоги, фоновые операции, доступность для диктора и размер/запуск готовой сборки на обеих ОС. Решение — отдельный ADR после runnable spike. Для включённых Git/Lua/runtime/GUI-компонентов и транзитивных библиотек нужны точные версии, SBOM, notices и выполнение source/redistribution обязательств; текущий lock Python-пакетов этого не заменяет. Пока лицензии/поставка не проверены, нельзя выдавать wheel или требование «установите Git» за готовое пользовательское приложение. См. [ADR-0007](adr/0007-gui-first-user-experience.md).

## 5. Первоисточники

В 0.2.0 Windows exe включены Git 2.56.0.windows.2 с рекурсивно найденными DLL dependencies и upstream notices, а также luac 5.3.6, собранный из официального source archive SHA `fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60`. Lua source/readme-license включены; Git source reference и точные binary hashes записаны в bundled manifest. В 0.4.0b1 лицензия проекта выбрана; публичная beta включает notices, точные tool sources/build recipes, SBOM и checksums. Это не сертификация чистой ОС или macOS-пакета. CC2X runtime/DLL плагина не вендорятся в exe, берутся из предоставленных пользователем/Workshop файлов при совпадении reviewed hashes; source assets игры не поставляются.

### Локальная Windows-упаковка (2026-10-29)

Developer build использует уже выбранный в `build_windows.bat` PyInstaller, теперь закреплённый на 6.22.3. В metadata установленного пакета указана GPLv2-or-later со специальным исключением для сборки и распространения non-free приложений; полный текст сохранён upstream в `pyinstaller-6.22.3.dist-info/licenses/COPYING.txt`. Локальная сборка не является разрешением публичного распространения: лицензия проекта, notices/SBOM и проверка всех транзитивных компонентов остаются release gates. Нового merge backend нет, Git и Lua validator в exe не включены.

Ссылки на первичные README и инструкции доступны в [11-SOURCES.md](11-SOURCES.md).
