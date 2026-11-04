# 04. Интеграция Carrier Command 2 / CC2X

Schema-2 addon screen declarations and the owned main menu share one validated
SDK descriptor. Referenced Lua helpers remain byte-identical in owner namespaces;
profile hashes/edits are preserved. Other cc2x resources retain native review.
See [ADR-0033](adr/0033-validated-screen-extension-packaging.md).

Beta 9 pins reviewed SDK 0.8.1 and preserves the existing framework/menu
capabilities, adding `waypoint-origin-v1` and `screen-source-edits-v1`. A known
older installed runtime is eligible for the existing closed-game upgrade with
backup and Undo. A newer unsupported Workshop source is identified as a source
library mismatch, not blamed on a correct installed loader. Unknown installed
loaders stay untouched and blocked. This pin does not certify new real-game
acceptance; see [ADR-0032](adr/0032-reviewed-sdk-provider-synchronization.md).

Beta 8 streams discovery of Workshop and local resource files without retaining
unchecked content. Use the same bounded resource policy through selected-input
reads, installed originals, staging and activation/reuse verification. A larger
data-resource budget grants no additional native approval; source folders and
game/SDK assets remain read-only. Closed-game deferral and rollback are unchanged.
See [ADR-0031](adr/0031-streamed-resource-discovery-and-budgets.md).

Current GUI discovery includes `%APPDATA%\Carrier Command 2\mods` on Windows
and `~/Library/Application Support/Carrier Command 2/mods` on macOS, alongside
Workshop, game-folder collections and user-added roots. This is read-in-place
discovery, with no author-file copies or automatic selection. The owned
`CC2-MCE` output is excluded. See ADR-0026.

ADR-0025 replaces Steam URL launch with the local executable and game working
directory. Startup refresh restores only the verified remembered selection.
Its activation enables exactly the generated package. Beta 6 does not establish
the requested main-menu lock: the menu world clears ordinary resource overlays.
ADR-0030 delivers the owned policy through the reviewed SDK stock-screen
extension boundary. Its schema-1 `content/cc2x/screen_extensions.json` maps
`scripts/screen_menu_main.lua` to `cc2x/ui/modloader_menu.lua` inside the same
package. The matching reviewed runtime must load it after stock screen code and
before `begin()`; ordinary mod activation alone is insufficient.

The candidate retains ADR-0029's requested
noninteractive CC2 ModLoader header and compact selected-mod line to the main
menu, retaining ADR-0028's gray Mods entry, navigation guard and stale-state
handling. The Workshop uploader behind that entry remains inaccessible; other
menus and gameplay remain available. Vanilla, Workshop and author files
stay unchanged. A generic reviewed SDK capability supplies delivery; gameplay
policy remains in the generated package. Undo restores the prior build's menu behavior; unloading the
generated set removes its menu changes. An empty selection adds no label or
guard. The exact final Windows pair passed the managed-menu checks recorded in
[menu verification](verification/main-menu-v4.md). Wider runtime gates remain separate.
See [ADR-0030](adr/0030-sdk-screen-extension-delivery.md).

New Lua-only package contract: `<cc2mce schema="1" type="mod" id="example"
sdk="cc2x" api="8" lua_api="2"><requires id="cc2x.runtime"/></cc2mce>`.
The SDK Lua API version and reviewed `lua-mod-api-v2` capability must both be
available. C API 8 alone is insufficient. Steam Required Items advertises the
SDK dependency; the matching ModLoader still installs its native bootstrap.
Native authors retain the C/C++ route. A package using the new named C
extension declares `framework_api="1"`; analysis requires reviewed
`runtime_framework_api >= 1` and `framework-c-api-v1`. A mixed package declares
both API requirements. Existing packages without these attributes retain their
previous behavior, and exact native hash review remains mandatory.
See ADR-0024; the new migration has not yet reached complete game acceptance.

Exact previous-runtime whitelist разрешает обратимое обновление общего SDK; неизвестный dinput8.dll сохраняется. Bundled runtime проверяется по hash до dependency fallback. [ADR-0019](adr/0019-reviewed-runtime-upgrade-and-built-in-dependency.md).

Кандидат 0.4.0b2 содержит SDK API 8 и точные review-профили Hold/Modes/Brake/v46,
проверенные вместе на Windows client 1.5.18. Client-only scope хранится в runtime
review metadata и документации SDK, без отдельного предупреждения в ModLoader;
dedicated/client offsets не смешиваются. [ADR-0020](adr/0020-scoped-client-sdk-candidate.md),
[ADR-0022](adr/0022-sdk-release-status-outside-modloader-ui.md).

Локальная новая версия может соседствовать в списке с подписанной Workshop-
версией того же package. Выбор переключается явно, подписка не переписывается.
[ADR-0021](adr/0021-explicit-package-version-selection.md).

SDK API config_dir соответствует `<user-data>/cc2x`; только reviewed defaults
точного native hash могут автоматически создать отсутствующий INI. Существующие
settings не заменяются. Это часть transactional GUI apply, не инструкция игроку
редактировать конфиг. [ADR-0018](adr/0018-reviewed-sdk-setting-defaults.md).

Известный SDK bundle index внутри content — целевой контракт общего runtime,
а не произвольный JSON asset. Publisher сохраняет module containers и требует
API 8, точный reviewed runtime SHA и capability ordered-module-bundles-v1.
Native plugins остаются в reviewed content/cc2x. Старый выпущенный runtime не
объявляется совместимым автоматически. [ADR-0017](adr/0017-independent-lua-module-bundles.md).

**0.3.3:** read-only проверка Combined Fleet3783006839 нашла два GLSL shader и две TXTR texture по тем же logical paths в установленном rom_0. Поддержка этих resource types устранила четыре Unknown resource type blockers; текущий набор + Fleet дал plan252 resources/5 overrides/0 blockers. Пакет с Fleet не активировался нами; игровая совместимость не проверена. [ADR-0015](adr/0015-cc2-shaders-textures-and-actionable-refusals.md).

**0.3.2:** [Steam-аудит](19-STEAM-DISTRIBUTION-AUDIT.md) сверяет официальный UGC контракт и текущий CC2X0.5.1: plugins из активных Workshop папок уже обнаруживаются, первоначальный game-root bootstrap всё ещё нужен. Подготовлены авторские metadata templates; публикация/саморазмещающийся installer не сделаны. Required Items и XML requires — разные уровни.

**0.3.0:** data baselines берутся из rom_0, иначе mod_dev_kit/source, без заранее записанного списка одобренных файлов. Неизвестная game build допускает data merge, но не получает разрешения native/runtime. Порядок во вкладке — порядок слияния файлов внутри единого output, не обещание нового CC2X DLL resource/loading hook. No-base data replacement явно включена владельцем. [ADR-0012](adr/0012-user-ordered-patches-and-system-language.md).

**0.2.2:** владелец разрешил автоматическую подготовку mods/libraries при первом запуске; только внутри выбранной проверенной игры после portable placement. Existing file/junction/permission error не обходится, SDK/vanilla/Workshop остаются read-only. После неудачного изменения UI возвращает реальную активацию и разрешает запуск прежнего набора, если нет незавершённой транзакции. [ADR-0011](adr/0011-truthful-checkboxes-and-minimal-interface.md).

**0.2.1:** пользователь разрешил автоматическое применение по галочке без дополнительных подтверждений. Единый локальный output — пользовательский `mods/CC2-MCE`, имя в игре «CC2 Engine — мои моды». Исторические активные собственные hash-папки архивируются обратимо в служебный cache. Перед записью игра закрыта; при открытой игре UI ожидает и повторяет автоматически. Снятие всех галочек очищает active_mod_folders. Workshop/vanilla/SDK/executable не изменяются. [ADR-0010](adr/0010-checkbox-auto-apply-and-stable-output.md) заменяет прежние шаги кнопок/имя output.

## 1. Подтверждённые факты

1. Игра позволяет устанавливать Workshop-моды и выбирать активные в меню. Если два мода содержат один и тот же игровой файл, штатное меню не даёт активировать оба. После изменения модов необходим рестарт. Источник: официальная документация Geometa.
2. В игре присутствует Mod SDK (`mod_dev_kit` в дистрибутиве); исходные файлы/ресурсы для конкретной сборки должны быть проверены на месте перед merger.
3. Для Windows Steam Workshop обычно хранится в `<SteamLibrary>/steamapps/workshop/content/1489630/<item-id>/`. Не считать `C:/Program Files (x86)/Steam` универсальным местом: библиотек может быть несколько.
4. CC2X — `dinput8.dll` рядом с `carrier_command.exe`, расширяет Lua и умеет грузить **32-bit Windows DLL** из активированных модов: `content/cc2x/*.dll`.
5. CC2X, согласно текущему `README_PLAYERS.txt`, поддерживает CC2 **1.5.18 Windows**, не поддерживает VR, dedicated server или macOS. Не строить вывод «CC2-MCE совместим» из факта работы CC2X: независимый offline-merge может существовать и без CC2X.
6. CC2X (`docs/PLUGINS.md`) вызывает `cc2x_plugin_load` в loader lock (`DllMain`) и запрещает там запуск потоков, ожидания и `LoadLibrary`. Для будущего плагина обязательна отдельная review.

## Поддержка Windows и macOS в CC2-MCE

Офлайн-приложение CC2-MCE обязано работать на Windows и macOS без CC2X, Windows-эмуляции и консольных действий игрока ([ADR-0007](adr/0007-gui-first-user-experience.md)). Это требование к приложению, а не утверждение о нативной доступности CC2/Mod SDK на macOS. На Mac допускается обработка доступных каталогов модов и верифицированного baseline, выбранных через GUI; целевая сборка игры определяется входами, а не ОС запуска. CLI остаётся только техническим adapter для разработки.

Размещение Steam library, local mods и SDK проверяется отдельно для каждой ОС в M0; Windows-пути не используются как fallback для macOS. Пока игровой runtime/layout macOS не подтверждён, нельзя обещать автоматическую установку или игровой smoke на Mac. Ограничения Windows-only CC2X сохраняются; DLL обнаруживаются и блокируют сборку по той же политике на обеих ОС.

## 2. Input adapter

**0.2.0:** [SDK declaration](17-LIBRARY-SDK.md) классифицирует library по mod.xml и разрешает зависимости независимо от Workshop/local location. Обычные моды без секции сохраняют стандартное поведение. Пользователь явно разрешил активацию и тест AI Bridge + Island Airfields: новый GUI publisher создаёт output в настоящем `%APPDATA%/Carrier Command 2/mods`, включает его через backup-protected mods.xml при закрытой игре и при необходимости копирует предоставленный reviewed runtime из libraries. Правила не перезаписывать vanilla/SDK/Workshop/executable/неизвестный dinput8 сохраняются; прежний запрет любой записи mods.xml относится к историческому read-only срезу. [ADR-0009](adr/0009-package-activation-and-library-sdk.md).

Реализованы Steam auto-discovery и `<game>/mods/<id>/content`, `<game>/libraries/<id>/content` как входы Engine ([ADR-0008](adr/0008-portable-discovery-and-library-collections.md)). Это не означает, что CC2 сама загружает эти два каталога. Workshop читается на месте во всех найденных библиотеках, DLL не исполняются. Upstream CC2X документирует `<game>/cc2x/plugins` как developer fallback; произвольная libraries требует отдельного проверенного профиля/пакета, не слияния DLL в инъектор.

- Сканировать игровые моды по `<mod>/content/**`; `mod.xml` и `thumbnail.png` — метаданные пакета, **не** сливаемые «по общему пути» игровые ресурсы.
- На M0 взять реальные локальные/Workshop моды и проверить точную схему их `mod.xml` (например, XML `data` + атрибуты); **не конструировать metadata из догадок**.
- Строить `logical_path` относительно `content`, например `scripts/screen_radar.lua`, сохраняя исходный путь.
- Исключать собственный `merged` output из discovery, даже если он лежит в просматриваемом каталоге.
- Учитывать симлинки/junction, регистр пути, относительные ссылки, обратные слэши.

## 3. Baseline adapter

- `game_build`/`game_exe_hash` определяются один раз до build; baseline SDK выбирается вручную либо по верифицированной установленной игре.
- Проверить, что файл из SDK соответствует runtime-пути модов. **Формат представления объектов в SDK и layout готового мода не всегда обязаны совпадать.** Нужен mapping по подтверждённым примерам.
- Если оригинального файла нет: запрет автоматического 3-way для двух независимых разных версий; `no_base` или явная поддержка новых файлов через `add/add` policy.
- Не скачивать и не распространять собственные файлы игры в составе движка.

## 4. Output adapter (локальный merged mod)

Предполагаемая форма:

```text
<CC2 local mods>/CC2-Merged-<profile>/
  mod.xml                # генерируется по подтверждённому шаблону CC2
  thumbnail.png          # опционально, если подтверждён формат
  content/
    ...                  # уникальные и объединённые игровые ресурсы
  [внешний manifest/отчёт в config_dir CC2-MCE]
```

**Не размещать JSON manifest произвольно в `content/`**, пока не доказано, что игра игнорирует неизвестные assets. Manifest храним в рабочей директории движка или вне `content` и при совместимости — рядом с output модом.

В MVP установка означает сборку во внешнем staging. Перенос в локальный каталог/активация в игре — только после успешного теста на установленной игре, с явным действием пользователя. Исходные моды остаются нетронутыми, их отключение пользователь выполняет штатно.

## 5. Нативные плагины CC2X — критическое исключение

Отключение исходного мода в меню приводит к тому, что CC2X **перестаёт видеть его DLL** на следующем запуске. Простое слияние Lua и XML не сохраняет функциональность таких модов автоматически.

**MVP policy:**

- Сканировать `content/cc2x/*.dll` и сопутствующие assets;
- Если активная комбинация содержит DLL — `native_plugin_review_required`, сборка installable пакета блокируется по умолчанию;
- Переупаковка plugin DLL возможна **только в отдельном явно подтверждённом режиме после технической и лицензионной проверки**: отсутствие коллизий имён, корректное `plugin_dir`, конфиги, load order, совместимость патчей и лицензий, доверенность бинарника;
- DLL не объединяются побайтово. Конфликты хуков/адресов и API не решаются text merger. CC2X уже отклоняет overlapping patches, что не заменяет тест совместимости;
- Включение нативных модов требует собственных in-game тестов и публикации исходников там, где этого требует CC2X/GPL.

## 6. Multiplayer

Официальная документация сообщает, что при подключении к серверу клиент получает серверные моды и временно отключает свои локальные. Локально собранный мод не гарантирует совместимость всех клиентов; CC2X отдельно не имеет multiplayer transport для своего Lua API. **MVP — singleplayer/local tests only**; multiplayer — исследовательская задача, не обещанная возможность.

## 7. Не изменять в MVP

- `carrier_command.exe`, `dinput8.dll`, Steam Workshop subscriptions;
- `%APPDATA%/Carrier Command 2/mods.xml`;
- файлы ванили/Mod SDK;
- DLL и конфиги сторонних модов.

Текущий read-only срез проверен на inventory реальных Workshop-модов macOS, но не на запуске merged пакета; конкретные подтверждённые/неподтверждённые результаты — [M0 validation](12-M0-VALIDATION.md).

## 8. Milestone 0: обязательные эксперименты на установленной игре

1. Один минимальный local mod: структуру пакета и `mod.xml` подтвердить скриншотом/тестом.
2. Два local mods с одним Lua-файлом: подтвердить блокировку и затем запуск merged output.
3. Один мод с дополнительным ресурсом: понять поведение `content/`.
4. Один CC2X plugin mod: подтвердить, что выключение исходного мода отключает DLL и что список загруженных DLL виден в `cc2x.log`.
5. Повторить после game update/проверить build fingerprint.
