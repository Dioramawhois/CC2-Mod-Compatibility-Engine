# 19. Steam: библиотеки, зависимости и запуск CC2 ModLoader

Проверено 2026-11-02. Результат — аудит, решение и шаблоны для автора, **не опубликованный Steam item**. Рабочая установка ModLoader остаётся локальной. Никакие Workshop/vanilla/SDK источники при аудите не изменены.

## Вывод для продукта

Практический путь: **один раз установить ModLoader через GUI → подписываться на моды и библиотеки в Workshop → выбирать моды галочкой → запускать игру из ModLoader**. При первом запуске будущий installer сам находит игру, ставит собственный exe/ярлык и проверенный runtime, готовит папки; игрок не устанавливает Python/Git/Lua и не редактирует XML. Текущий portable exe уже обнаруживает игру и готовит папки, но ещё просит разместить его рядом с игрой: полноценный саморазмещающийся installer не реализован.

«Подписаться на зависимость и запускать штатный CC2 без первоначальной установки» **не подтверждено и текущей архитектурой не обеспечено**. Для этого нужен официальный запуск нашего bootstrap/launcher со стороны игры или её Steam-пакета. Простая запись зависимости не создаёт такого запуска.

## Что на самом деле делает Steam

`AddDependency(parent, child)` задаёт soft dependency между Workshop items: связь показывается на странице и читается через UGC API. `AddAppDependency(item, appid)` также мягкая, для приложения/DLC; пригодность проверяет приложение. Это не гарантия автоматической установки/запуска требуемого приложения. `SubscribeItem` ставит конкретный item в очередь загрузки. Нельзя считать наличие Required Items доказательством загрузки/активации всей цепочки. [Официальный контракт ISteamUGC](https://partner.steamgames.com/doc/api/ISteamUGC#AddDependency).

После загрузки приложение должно проверить Installed/NeedsUpdate и дождаться завершения download перед чтением файлов. Установка UGC и запуск кода — разные события. Наш офлайн resolver читает уже существующие папки и отлавливает изменение хешей перед apply; полноценное управление загрузками Steam API пока отсутствует. [Workshop implementation](https://partner.steamgames.com/doc/features/workshop/implementation#ConsumingContent).

Steam install scripts относятся к depot приложения/DLC: файл помечается в depot manifest и подписывается при upload; Steam выполняет такие scripts при запуске приложения. `Run Process` может запускать first-run installer. Положенный в Workshop `installscript.vdf` не становится таким script. macOS Run Process не поддерживается. [Valve: InstallScripts](https://partner.steamgames.com/doc/sdk/installscripts).

## Проверенный путь загрузки CC2X

Проверены текущие локальные `cc2x/src/cc2x.c` (load_plugin/load_mod_plugins/load_plugins, строки 700–824), README и предоставленный runtime 0.5.1/API4. Историческое утверждение, что loader видит только game-root/cc2x/plugins, **устарело**: новая реализация уже читает active_mod_folders из пользовательского mods.xml и ищет content/cc2x/*.dll в активных локальных и Workshop пакетах. Затем проверяются старые ручные game-root/cc2x/plugins. Одинаковое имя DLL загружается один раз; очередность текстового merge не является управлением хуками DLL. [Текущий upstream](https://github.com/Dioramawhois/Carrier-Command-2-extender/blob/main/src/cc2x.c).

Но эту функцию сначала должен выполнить сам CC2X: текущий bootstrap — `dinput8.dll` рядом с `carrier_command.exe`. Его присутствие только в Workshop/content не запускает его. В обычном Windows DLL search order папка exe участвует в поиске, произвольные каталоги Workshop не добавляются рекурсивно. Это вывод из фактического bootstrap и правил Windows, а не универсальный запрет на другие будущие loader-архитектуры. [Microsoft: DLL search order](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order).

Реальный локальный тест ранее подтвердил загрузку Island Airfields из собственного merged mod через этот runtime и достижение меню. Это доказывает путь DLL, но не устанавливает свежую Workshop acceptance: загрузка собственного опубликованного library item, чистая машина, полный gameplay и macOS native runtime здесь не проверены. Официальные страницы Geometa по modding найдены в поиске, но при открытии дали HTTP404; их содержание не использовано как свежее доказательство uploader behavior. Правило текущего uploader «mod.xml/thumbnail/content» есть в локальном CC2X GUIDE; фактический upload необходимо проверить отдельно.

## Два уровня зависимостей

| Уровень | Для чего нужен | Чего не обеспечивает |
|---|---|---|
| Steam Required Items: авторский мод → CC2X Runtime item | На странице видно требование, Steam хранит связь по PublishedFileId | Запуск dinput8, merge, библиотечный тип нашего приложения |
| mod.xml: requires id=cc2x.runtime | ModLoader находит библиотеку по стабильному ID, автоматически добавляет перед модом | Подписку/скачивание отсутствующего item |
| mod.xml: type=library | Пакет показывается в «Библиотеках», обычные пакеты без секции остаются модами | Одобрение произвольной DLL или автоматическое исполнение произвольного Lua |

Автор указывает **оба** уровня. Реальный Workshop item ID появляется только после публикации. Stable package ID `cc2x.runtime` уже существует в SDK-контракте и не меняется вместе с локальной папкой/Workshop ID. Runtime имеет `content/dinput8.dll`; plugin — `content/cc2x/plugin.dll`, Lua — документированные игровые script paths. DLL остаются отдельными файлами под одним runtime, не компилируются в единый injector. Произвольный Lua файл не запускается от одной метки library. [SDK-контракт](17-LIBRARY-SDK.md).

ModLoader сканирует все установленное из Workshop и local roots, автоматически разрешает dependencies и копирует проверенные payload в один активный CC2-MCE. Поэтому оригинальные plugin items не надо дополнительно включать в меню игры: runtime видит их копии в активном output. Missing dependency, неоднозначный ID, неподдержанная game/runtime/plugin версия дают понятный отказ с сохранением прежнего набора. Подписка автора не разрешает неизвестный native код.

## Сравнение каналов

| Канал | Действие игрока | Обновления | Решение |
|---|---|---|---|
| Только Workshop metadata/runtime item | Подписка; первоначальный bootstrap всё равно нужен | Payload доставляет Steam, новый native hash ещё должен пройти review | Делать как dependency hub, не называть installer |
| GUI installer/portable + Workshop | Один первоначальный GUI запуск; затем ModLoader | Моды/библиотеки через Steam, сам exe отдельным release | Основной доступный путь; installer/ярлык ещё разработать |
| Собственное Steam приложение Player Tools | Установить/запустить из библиотеки Steam | Свои depots и launch option | Хороший конечный канал, требует своего AppID и одобрения |
| Официальная интеграция Geometa | Обычный запуск CC2 после подписки | Через разработчика игры | Единственный рассмотренный путь убрать первоначальный сторонний bootstrap из UX |
| exe в Workshop/content | Найти файл и запустить вручную | Файл обновляет Steam, автозапуска нет | Запасной транспорт, плохой основной UX |
| Ручные Steam launch options/правка VDF | Техническая настройка игроком | Не решает доставку runtime | Не соответствует GUI-only требованию |

Отдельный Player Tools канал допустим к рассмотрению: Valve прямо перечисляет Player Tools среди категорий non-game software, но принятие конкретного продукта не гарантировано. Нужны onboarding, собственный AppID, сборка/store review; на текущей странице указаны $100 за продукт и минимальные сроки: 30 дней после оплаты, публичный Coming Soon минимум две недели. [Steam Direct](https://partner.steamgames.com/steamdirect).

Своё приложение получает собственные depots и launch executable. Чужой AppID1489630 не даёт нам publisher rights или возможность добавить launcher в штатный CC2 package. Для build/upload Valve требует соответствующие права аккаунта. [SteamPipe initial setup](https://partner.steamgames.com/doc/sdk/uploading#Initial_Setup_for_New_SteamPipe_Apps).

## Лицензии и состав поставки

Текущий CC2X README/лицензия заявляют GPL-3.0-or-later; у самого ModLoader выбор публичной лицензии пока отложен в pyproject. Значит «готово к публичному распространению» сейчас утверждать нельзя. Не включать game assets, декомпиляцию, saves, чужие моды или DLL в metadata-шаблоны. Runtime public archive требует соответствующих исходников/уведомлений для точного бинарника. Bundled Git распространяется отдельным инструментом, Lua имеет свои notices; notices/source archives уже включаются toolchain preparation.

Не добавлять `steam_api.dll` в CC2X/GPL код в рамках этой задачи: Valve отдельно предупреждает о несовместимости Steamworks SDK с некоторыми copyleft-лицензиями. Точная правовая допустимость зависит от состава и разрешений, а не от одного слова GPL. Пока выбран офлайн discovery и обычный Steam URL запуск без Steamworks SDK. [Valve: open-source distribution](https://partner.steamgames.com/doc/sdk/uploading/distributing_opensource).

## Конкретная подготовка к публикации

Подготовлены [шаблоны](../distribution/workshop/README.md): runtime library metadata, зависимый мод и текст Workshop страницы с честной инструкцией первого запуска. Они не содержат исполняемых файлов и не создают фальшивый PublishedFileId. Перед private upload автор собирает **свой** лицензированный runtime payload, preview и соответствующие исходники; uploader/Steam page создают реальный ID. В Required Items каждого зависимого мода выбирается этот item, в XML — `cc2x.runtime`.

Проверка private acceptance обязательна до обещания «нативно»: новый Windows профиль/чистая машина, подписка на мод и реально установленная dependency, первый GUI bootstrap без команд, plugin DLL путь из активного output в свежем логе, AI Bridge + Island Airfields с конфликтом, reorder, удаление мода, Steam update и rollback, неизвестная DLL, offline и несколько Steam libraries. Для macOS отдельно data merging/GUI/tool bundle; Windows CC2X DLL на Mac не обещается.

Результат аудита не требует публиковать что-либо от имени пользователя. Ни item ID, ни Steamworks app/depot, ни свежая private upload acceptance пока не созданы.
