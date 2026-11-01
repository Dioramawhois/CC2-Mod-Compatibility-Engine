# ADR-0009: Рабочий Windows pipeline, активация и SDK библиотек

**Уточнение 0.2.1:** владелец явно заменил кнопки/подтверждение на автоматическое применение по галочке и потребовал постоянную папку. Эти части решения заменены [ADR-0010](0010-checkbox-auto-apply-and-stable-output.md); baseline/native/provenance ограничения сохранены.

- **Статус:** Accepted для локальной версии 0.2.0; macOS/gameplay release gates остаются отдельными.
- **Дата:** 2026-11-01.
- **Уточняет:** ADR-0006/0008: ограничения исторического read-only прототипа не являются поведением нового GUI pipeline.

## Основание и границы записи

Пользователь потребовал довести сценарий до появления модов в игре, явно поручил тестировать AI Bridge + Island Airfields, предоставил dinput8.dll в libraries и запросил декларацию библиотек в mod.xml. Это разрешает реализацию и проверку отдельного пакета, установки предоставленного проверенного runtime и обратимой активации. GUI выполняет запись только явным действием «Применить к игре» с подтверждением набора; отдельная пустая «проверка DLL» не заменяет установку. Vanilla, SDK и Workshop остаются read-only. Существующий чужой/неизвестный dinput8.dll не перезаписывается.

## Решение

1. Новый прикладной сервис `workflow.py`: разрешить зависимости → проверить точную сборку/базу → настоящий Git three-way → Lua 5.3 syntax-only → stage/validate → immutable local package → активация. GUI не вызывает CLI для публикации.
2. Доверенный профиль игры привязан к SHA-256 executable. Для известных логических путей записаны хеши оригиналов; перед merge проверяются и rom_0, и SDK source, они должны совпасть с профилем и друг с другом. Профиль содержит только хеши, игровые assets в поставку не включаются. Неизвестная сборка/база блокируется.
3. Разные **однородные** LF/CRLF у валидных UTF-8 текстов можно привести к LF для three-way. Это отдельная явная policy нового package pipeline; source/base hashes относятся к исходным байтам, output hash — к результату. BOM должен совпадать; mixed EOL, UTF-16, NUL и конфликтные маркеры блокируются. Unique files сохраняют байты. Старый строгий default core не ослаблен. Собственный Python merger больше не является default fallback.
4. Git for Windows и настоящий luac 5.3.6 включены в exe с manifest хешей и upstream notices. SHA каждого bundled executable/dependency проверяется перед использованием; GUI не ищет инструменты в пользовательском PATH. Developer build собирает luac из официального SHA-pinned source; Lua код не исполняется при validation. Frozen smoke проверяет настоящий merge и отказ invalid Lua без developer tools в PATH.
5. Native DLL не сливаются. Только точные reviewed hashes при известном runtime/game допускаются как byte-identical copy в content/cc2x; остальное — blocker. Для текущего сценария отдельно проверены PE32 export/API, существующий package layout и свежая загрузка плагина из combined mod. Автоматического доверия произвольной DLL по метке library нет.
6. Предоставленный runtime ищется в игре и внутри libraries, включая SDK/content/dinput8.dll. Разрешён только ожидаемый SHA профиля. При применении отсутствующий runtime копируется в корень игры; исходник сохраняется. Неизвестный установленный runtime блокирует операцию.
7. `<data><cc2mce schema="1" type="library" id="…" sdk="cc2x" api="4"><requires id="…"/></cc2mce></data>` — opt-in SDK contract. Без cc2mce это обычный мод независимо от каталога. Невалидная/неподдерживаемая явная декларация блокируется. Зависимости разрешаются топологически, missing/ambiguous/cyclic dependencies блокируются. Workshop и local packages классифицируются одинаково. Полный контракт: [17-LIBRARY-SDK](../17-LIBRARY-SDK.md).
8. Output — `%APPDATA%/Carrier Command 2/mods/CC2-MCE-<build-id>` с mod.xml, content и внешним к content mce-manifest.json. Новый JSON contract v2 отделён от read-only report v1. Manifest содержит source/base/output/game/engine/toolchain/runtime hashes, порядок и metadata hash. Уже существующий output сверяется полностью, включая отсутствие добавленных файлов.
9. Перед записью игра должна быть закрыта. OS-released lock исключает параллельное применение двумя копиями Engine. Публикация — rename нового собственного stage; источники повторно хешируются. Активация заменяет выбранный набор на один combined mod через доказанную active_mod_folders/path схему; backup и recovery journal пишутся перед config commit. Ошибка сохраняет старую активацию. Runtime устанавливается только если место свободно или hash совпадает.
10. «Вернуть прежние моды» восстанавливает сохранённые байты. Внешние изменения не затираются. Допускается только доказанное переписывание CC2: те же root attributes и единственный distinct active package, с изменёнными отступами/повторённым тем же path. Новый loader может оставаться установленным как самостоятельный SDK component; rollback набора не означает удаление SDK.
11. В GUI различаются выбор, готовый план и фактическая активация. Смена выбора/источников аннулирует plan; старый выбранный набор нельзя молча запустить как новый. Запись работает в фоне; закрытие окна во время commit отложено до завершения. Есть export отчёта и восстановление.

## Доказательства и незакрытые gates

На данной Windows 10 x64: executable SHA `461e12623bacb7de29ca27b4614425c87e8df2c8327a5e958a957c850effe42a`, 55 побайтно совпавших SDK/runtime scripts, Git clean для AI Bridge + Island Airfields после canonical LF, настоящая Lua 5.3 validation, новый package и mods.xml, предоставленный CC2X 0.5.1. Свежий cc2x.log называет combined mod и загруженный island-airfields v45; пользователь подтвердил видимое меню игры. Реальный rollback после выхода игры пройден. Source assets/SDK/Workshop не редактировались.

Это не доказательство посадки самолёта, полноценной работы внешнего AI client или любого произвольного сочетания. В исходном AI Bridge есть авторский hard-coded command path к другому Windows-профилю; Engine не переписывает семантику чужого скрипта при merge. macOS execution, чистая ОС, полная accessibility/usability и публичная лицензированная поставка остаются gates общего MVP. Windows shared injector означает один loader плюс отдельные плагины, а не бинарную склейку DLL.
