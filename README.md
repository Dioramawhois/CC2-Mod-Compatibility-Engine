# CC2 ModLoader — CC2 Mod Compatibility Engine

[Русский](#русский) · [English](#english)

Ветка разработки готовит **0.4.0b2**: независимые Lua-модули в одной сборке,
автоматические настройки проверенных native-модов и обратимое обновление SDK.
Это кандидат следующей версии; опубликованная beta ниже остаётся 0.4.0b1.
Новые native hashes не включаются без отдельной приёмки.
[Объединение SDK и текущие проверки](docs/22-UNIFIED-SDK-AND-MOD-SPLIT.md).

## Русский

**0.4.0b1 — открытая Windows beta: CC2 ModLoader с порядком патчей, предупреждением о перезаписи и офлайн-паком 14 языков.** По умолчанию используется язык системы. Пересекающиеся изменения получают приоритет по выбранному порядку, независимые правки сохраняются через настоящий Git. Пакеты собираются в одну постоянную папку; имя в игре содержит ModLoader и названия выбранных модов. Поддержаны игровые `.glsl` shaders и `.txtr` textures; неизвестный формат теперь объясняется с конкретным путём. Полная игровая совместимость произвольных модов не гарантируется.

### Как пользоваться

1. Откройте `CC2ModLoader.exe`. Программа найдёт игру через Steam; Windows portable попросит поместить exe рядом с `carrier_command.exe`, если он запущен из другой папки.
2. Отметьте нужные моды. Workshop читается на месте, локальные пакеты — из `mods` и `libraries` рядом с игрой. Эти папки создаются автоматически при первом запуске. Дополнительные папки, выбор игры и расположение файлов доступны через **«Меню»**.
3. Проверка, разрешение зависимостей, слияние и включение происходят **сразу по галочке**, без дополнительных кнопок и подтверждений. Дождитесь строки **«Готово. Можно запускать игру»**. Верхняя строка показывает фактически включённые моды.
4. Во вкладке **«Порядок загрузки»** перетащите моды или используйте **Alt+↑ / Alt+↓**. Поздние патчи размещаются ниже. Любое изменение порядка автоматически пересобирает файлы и сохраняется. При известном оригинале Git сохраняет независимые правки и отдаёт спорные участки позднему патчу. Без оригинала или для разных binary ресурсов поздний файл заменяет ранний целиком. Оранжевое предупреждение называет участников/ресурс и остаётся у активного набора: результат в игре неизвестен. Все файлы и тип замены — в подробностях меню. Строгую проверку можно вернуть, отключив **«Приоритет поздних патчей»** в меню.
5. Нажмите **«Запустить игру»**. Для следующих открытий включите **«Меню → Запускать игру при открытии»**: приложение сначала подготовит выбранный набор и затем запустит игру. Если изменения отклонены, автозапуск отменяется. Предупреждение о перезаписи остаётся в открытом окне. Для возврата предыдущего набора используйте **«Меню → Вернуть предыдущий набор»** при закрытой игре; восстанавливаются и содержимое сборки, и активация. Диагностика и экспорт отчёта также доступны в меню.

Python, Git, Lua, терминал и ручные manifests игроку не нужны. Проверенные Git и Lua 5.3 входят в exe. Reports экспортируются только по вашему действию.

Если игра открыта, изменения применятся после её закрытия. При ошибке синтаксиса/неподдержанном DLL/другом окончательном отказе галочки и порядок возвращаются к рабочему набору, который можно запустить. Обязательные зависимости объясняют повторное включение. Путь проблемного файла доступен через меню подробностей.

**Язык:** по умолчанию язык системы. Включены русский, английский, немецкий, французский, испанский, португальский (Бразилия), итальянский, польский, турецкий, украинский, упрощённый/традиционный китайский, японский и корейский. Неподдержанная локаль использует English. Изменить выбор можно через **«Меню → Язык»**. Переводы входят в exe и работают без интернета; базовые названия элементов выверены, остальные сообщения имеют машинный перевод с проверкой параметров. Настройка сохраняется; смена языка переносит ожидающий выбор/порядок. Выбранная вкладка крупнее соседних и выделена жирным.

### Каталоги и загрузчик

```text
Carrier Command 2/
  carrier_command.exe
  CC2ModLoader.exe
  dinput8.dll                 # установленный проверенный runtime, если нужен
  mods/<mod-id>/content/...
  libraries/<package>/mod.xml
  libraries/<package>/content/...
```

Предоставленный dinput8.dll может находиться, например, в `libraries/SDK/content/dinput8.dll`: поддержанная версия будет установлена рядом с игрой при применении, исходник сохранится. Неизвестный уже установленный dinput8.dll не перезаписывается.

Результат всегда находится в одной папке пользовательского каталога CC2: `mods/CC2-MCE`, с `mod.xml`, `content` и manifest вне `content`. Название в игре — **«CC2 ModLoader: Island Airfields + AI Bridge + …»**, с фактически выбранными именами и ограничением длины. Эта папка полностью заменяется после успешной проверки, старые файлы снятых модов не остаются. Хеши хранятся внутри manifest. Резервная сборка и журнал находятся отдельно в служебной папке `cc2-mce`. Исходники Workshop, vanilla/SDK и executable игры остаются неизменны. При восстановлении SDK loader может оставаться установленным; это отдельный компонент. [ADR-0010](docs/adr/0010-checkbox-auto-apply-and-stable-output.md).

### Библиотеки через Workshop

Автор добавляет секцию `cc2mce` в обычный `mod.xml`:

```xml
<cc2mce schema="1" type="library" id="author.library" sdk="cc2x" api="4">
  <requires id="author.base"/>
</cc2mce>
```

**Нет секции — обычный мод**, независимо от папки. Есть корректная секция — библиотека в отдельной вкладке; зависимости включаются в план. Lua сохраняет настоящие игровые пути, DLL остаются отдельными плагинами одного runtime. Никакой склейки бинарников или автоматического доверия DLL по одной метке. [SDK contract](docs/17-LIBRARY-SDK.md) · [пример](examples/library-mod.xml).

### Проверки и границы

- AI Bridge + Island Airfields: общая база сверена с SDK/runtime, настоящий Git объединил правки после явной LF normalization, настоящий Lua 5.3 validator проверил результат; DLL скопирована побайтно. Свежий game log называет combined mod и Island Airfields v45, пользователь подтвердил меню.
- Проверены реальные создание/активация/откат, game XML reformat/duplicate path, source-change/running-game gates и посторонние файлы в output; frozen exe выполняет Git/Lua smoke без developer tools в PATH.
- Не проверены полноценный полёт/посадка, внешний AI command client, clean-machine certification и macOS execution. У установленного AI Bridge есть авторский command path другого Windows-профиля; Engine не переписывает семантику чужого скрипта при merge.
- Поддержка новых game/runtime/native versions требует проверенного профиля. Общий Windows/macOS MVP, доступность и публичная лицензированная поставка имеют отдельные release gates.

[Проверка](TESTING.md) · [Для разработчиков](CONTRIBUTING.md) · [CHANGELOG](CHANGELOG.md) · [ADR-0009](docs/adr/0009-package-activation-and-library-sdk.md) · [M0 evidence](docs/12-M0-VALIDATION.md)

**Внешний полигон:** [carrier-command-2-mods](https://github.com/totolerigolo118/carrier-command-2-mods) — [границы](docs/16-EXTERNAL-TEST-CORPUS.md); полная совместимость не заявляется.

## English

**0.4.0b1 Windows beta ships CC2ModLoader.exe, persistent override warnings and an offline 14-language pack.** Drag selected packages in **Load order**, or use Alt+Up/Down; every change rebuilds automatically. Later patches win overlapping Git hunks while unrelated edits survive. Installed originals are used without a file-hash allowlist; missing-base data and binary collisions use an explicit, reported later-file replacement. An orange warning names the sources/file, survives reopening and states that the in-game result is unknown; full details are in the menu. Game `.glsl` shaders use text merging; `.txtr` with TXTR magic use binary copy/whole-file replacement. Unknown types identify the file and reason. **Menu → Later patches take priority** can restore strict mode. Unsupported native code, unsafe paths and invalid syntax remain blocked.

The UI follows the system language. **Menu → Language** offers RU, EN, DE, FR, ES, PT-BR, IT, PL, TR, UK, simplified/traditional Chinese, JA and KO. Primary labels are reviewed; remaining translations are machine-assisted with complete key/parameter checks. All catalogs ship offline. Preferences persist. Checkbox changes update one `mods/CC2-MCE` folder, wait for a running game to close, and revert to the working selection/order on failure. The generated game mod name contains CC2 ModLoader and the selected mod names. Git and Lua 5.3 are bundled; players need no terminal or manual tool installation.

Workshop stays in place. Local inputs use `mods/<id>/content` and `libraries/<id>/content`. A valid `cc2mce` section in mod.xml declares a library and dependencies; unmarked packages remain ordinary mods. Native DLLs remain separate reviewed plugins of one loader. A hash-matched user-provided dinput8.dll can be installed from libraries; existing unknown loaders and unsupported game/plugin versions block application.

AI Bridge + Island Airfields were merged with real Git, syntax-checked with real Lua 5.3, packaged and activated. Fresh CC2X logs identify the combined mod and its airfields plugin; the user confirmed the game menu. Full gameplay, the external AI command client, clean-machine distribution and macOS execution remain unverified. See [SDK](docs/17-LIBRARY-SDK.md), [architecture decision](docs/adr/0009-package-activation-and-library-sdk.md) and [tests](TESTING.md).

**Steam distribution:** [audited delivery options](docs/19-STEAM-DISTRIBUTION-AUDIT.md) and [author metadata templates](distribution/workshop/README.md). Required Items are soft dependencies; an initial GUI bootstrap is still needed. No Steam publication or automatic Workshop-only installation is claimed.

## Open source / Открытый код

GPL-3.0-or-later ([LICENSE](LICENSE)); third-party terms: [NOTICE](NOTICE.md).
This is an update of the existing ModLoader, not a separate mod or new Workshop item.
**Menu → Launch game when opening ModLoader** prepares the selected set before launch;
a rejected change cancels automatic launch. A persistent override warning keeps the
window open. A full in-game UI and multiplayer are separate, unverified runtime work.
The public Windows beta does not certify a packaged macOS application or a clean OS.
Release assets include the application's source, matching Git/Lua tool sources and
build recipes, notices, SBOM and SHA256SUMS. [Release process](docs/20-RELEASE.md).
