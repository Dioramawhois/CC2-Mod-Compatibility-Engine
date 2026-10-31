# CC2 Mod Loader (CC2-MCE)

[Русский](#русский) · [English](#english)

**Внешний полигон / External test corpus:** [totolerigolo118/carrier-command-2-mods](https://github.com/totolerigolo118/carrier-command-2-mods) — [план проверки / test scope](docs/16-EXTERNAL-TEST-CORPUS.md). Registered for future experiments; compatibility and gameplay are not yet verified.

---

## Русский

> **Версия:** 0.1.0 · **Статус:** предварительная сборка для тестирования. Не финальный продукт.
>
> Есть исходники окна на `tkinter`, встроенное текстовое слияние и запись объединённых файлов. **Готового Windows `.exe` и проверенного установочного пакета мода пока нет.** Работа в Windows-игре не подтверждена. Поддержка macOS отложена.

### Что делает

Объединяет моды Carrier Command 2, которые меняют **разные строки одного файла**. Если два мода меняют **одну и ту же строку** — программа показывает конфликт и ничего не записывает. Победитель не выбирается молча.

Оригинальные моды и файлы игры **не изменяются**.

### Как пользоваться

1. Запустите приложение (или `python -m cc2_mce.gui` из исходников).
2. Автопоиск стоковых скриптов реализован частично. Подготовка совместимого манифеста базы ещё не завершена; для сборки требуется корректная база с `baseline-manifest.json`.
3. Выберите папку с модами и отметьте моды.
4. Выберите пустую папку для результата и нажмите **«Объединить»**.

Инструкция для тестировщика: [TESTING.md](TESTING.md).

### Ограничения

- **Revolution и Island Airfields** меняют одни и те же экраны (`screen_vehicle_control.lua`, `screen_holomap.lua`) с пересекающимися правками. Автоматически не объединяются.
- Слияние проверено на текстовых файлах. Lua, XML и бинарные ресурсы обрабатываются иначе или не объединяются.
- Объединённый мод **не проверен в игре**.
- Нативные плагины (DLL) не объединяются — по политике безопасности.

### Командная строка (для разработчиков)

```bash
cc2-mce build --mods-dir DIR --mods A B --baseline DIR --output OUT   # записывает при чистом плане
cc2-mce build --dry-run ...                                           # только анализ
```

Отчёт остаётся схемой v1 только для чтения (`installable: false`).

### Сборка для Windows

Запустите `build_windows.bat` на Windows (Python 3.12+). Результат: `dist\CC2ModLoader-0.1.0.exe`. PyInstaller собирает программу только под ОС, на которой запущен.

### Тесты

```bash
pytest          # 94 теста
mypy cc2_mce    # проверка типов
```

### Документация

| Файл | Назначение |
|---|---|
| [TESTING.md](TESTING.md) | Инструкция для тестировщика |
| [CHANGELOG.md](CHANGELOG.md) | История изменений |
| [docs/01-PRODUCT-REQUIREMENTS.md](docs/01-PRODUCT-REQUIREMENTS.md) | Цели, границы, требования |
| [docs/02-ARCHITECTURE.md](docs/02-ARCHITECTURE.md) | Компоненты и потоки данных |
| [docs/03-MERGE-SPEC.md](docs/03-MERGE-SPEC.md) | Правила слияния |
| [docs/04-CC2-INTEGRATION.md](docs/04-CC2-INTEGRATION.md) | Формат модов CC2, CC2X, Workshop |
| [docs/10-SECURITY-AND-RELEASE.md](docs/10-SECURITY-AND-RELEASE.md) | Безопасная обработка модов, релиз |
| [docs/adr/](docs/adr/) | Архитектурные решения |
| [AGENTS.md](AGENTS.md) | Контекст для агентов и разработчиков |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Процесс внесения изменений |

### Что не сделано

- Игровая проверка объединённого мода на Windows.
- Финальный `.exe`, собранный на Windows.
- Зависимости библиотек из Workshop и установка через интерфейс.
- Поддержка macOS (отложена по решению владельца).
- Независимое ревью безопасности перед публикацией.

---

## English

> **Version:** 0.1.0 · **Status:** pre-release build for testing. Not a final product.
>
> Includes `tkinter` window source, built-in text merging and merged-file output. **No ready Windows `.exe` or verified installable mod package is available yet.** Windows in-game operation is unverified. macOS support is deferred.

### What it does

Merges Carrier Command 2 mods that edit **different lines of the same file**. If two mods edit **the same line**, it reports a conflict and writes nothing. It never silently picks a winner.

Original mod folders and game files are **not modified**.

### How to use

1. Start the application (or run `python -m cc2_mce.gui` from source).
2. Stock-script auto-discovery is partially implemented. Generation of a compatible baseline manifest is not complete; builds require a valid baseline containing `baseline-manifest.json`.
3. Choose the mods folder and tick the mods.
4. Choose an empty output folder and press **Merge**.

Tester instructions: [TESTING.md](TESTING.md).

### Limitations

- **Revolution and Island Airfields** edit the same screens (`screen_vehicle_control.lua`, `screen_holomap.lua`) with overlapping changes. They are not merged automatically.
- Merging is verified on text files. Lua, XML and binary resources are handled differently or not merged at all.
- The merged mod is **not yet verified in the game**.
- Native plugins (DLLs) are not merged — by security policy.

### Command line (for developers)

```bash
cc2-mce build --mods-dir DIR --mods A B --baseline DIR --output OUT   # writes on a clean plan
cc2-mce build --dry-run ...                                           # analysis only
```

The report stays the read-only v1 schema (`installable: false`).

### Windows build

Run `build_windows.bat` on Windows (Python 3.12+). Output: `dist\CC2ModLoader-0.1.0.exe`. PyInstaller builds only for the OS it runs on.

### Tests

```bash
pytest          # 94 tests
mypy cc2_mce    # type checking
```

### Documentation

| File | Purpose |
|---|---|
| [TESTING.md](TESTING.md) | Tester instructions |
| [CHANGELOG.md](CHANGELOG.md) | Change history |
| [docs/01-PRODUCT-REQUIREMENTS.md](docs/01-PRODUCT-REQUIREMENTS.md) | Goals, scope, requirements |
| [docs/02-ARCHITECTURE.md](docs/02-ARCHITECTURE.md) | Components and data flow |
| [docs/03-MERGE-SPEC.md](docs/03-MERGE-SPEC.md) | Merge rules |
| [docs/04-CC2-INTEGRATION.md](docs/04-CC2-INTEGRATION.md) | CC2 mod format, CC2X, Workshop |
| [docs/10-SECURITY-AND-RELEASE.md](docs/10-SECURITY-AND-RELEASE.md) | Safe handling of mods, release |
| [docs/adr/](docs/adr/) | Architecture decisions |
| [AGENTS.md](AGENTS.md) | Context for agents and developers |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Change process |

### Not done yet

- In-game verification of the merged mod on Windows.
- A final `.exe` built on Windows.
- Workshop library dependencies and installation through the interface.
- macOS support (deferred by owner decision).
- Independent security review before publication.
