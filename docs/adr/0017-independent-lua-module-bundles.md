# ADR-0017: отдельные Lua-модули внутри одной сборки

Статус: реализовано по запросу владельца завершить общий SDK и ModLoader.
Дата: 2026-11-03. Дополняет ADR-0009/0010/0012; native approvals не отменяет.

## Решение

`bridge.json` и собственный код независимых VM не являются обычными игровыми
overlays. Их слияние по имени файла теряет моды. Publisher сохраняет для каждого
выбранного модуля отдельный контейнер `content/cc2x-modules/m-<stable-key>/` с
исходными `mod.xml`, manifest и файлами. Индекс schema 1 перечисляет контейнеры
в порядке разрешённых зависимостей и пользовательского выбора. Внешняя папка
по-прежнему одна: `mods/CC2-MCE`, с прежней транзакцией и Undo.

Поддерживаются modern content/bridge.json, legacy content/native_bridge и
package-root bridge.json. Корневые Lua и известные ресурсы legacy-пакета входят
в snapshot; служебный .git не копируется. Код не переписывается, все Lua
проверяются syntax-only; игровые content/scripts не могут быть entries.
Неизвестные типы не разрешаются из-за помещения в private container.

Общие игровые XML/тексты/бинарные ресурсы продолжают обычный merge pipeline с
явной patch policy. Private code и manifests никогда не заменяются поздним
модом. Native DLL не копируются в private containers: остаются reviewed byte-copy
в content/cc2x. Legacy root native files требуют корректного пакета, не теряются
молча. Имена owners, entries и относительных require paths сохраняются.

Для активации обязателен точный reviewed runtime SHA профиля, API >= 8 и
capability `ordered-module-bundles-v1`. Старый runtime не становится совместимым
из-за новой версии приложения. Непрофилированный runtime блокируется.

## Контракт и проверки

Package schema v2 обратно совместимо дополняется optional ordered `modules`:
source ID, normalized owner ID, container key и source/manifest hashes. Каждый
private/generated файл также имеет обычную file record с output/source hashes;
у индекса sources — fingerprints исходных пакетов. Поле root_files в source
inventory фиксирует вне-content legacy inputs. Metadata остаётся snapshot bytes.

Manifest ограничен 64 KiB и глубиной JSON 32; duplicate keys/owners/scripts,
неподдерживаемые schema/hooks, traversal, reparse points, missing files и
зарезервированный source namespace блокируют весь publish. Все declared scripts
проверяются, а не только первый. Output ограничен byte/entry/depth budget с
учётом контейнеров. Старый рабочий набор сохраняется при любом отказе.

Регрессии используют fake reviewed runtime и syntax boundary mock для проверки
упаковки, настоящий Git для общих ресурсов и реальные staging/rollback. Отдельно
нужны настоящий bundled luac, SDK reader, Windows/macOS CI, frozen GUI и игровой
runtime acceptance. Ни один такой тест не объявляется сетевой проверкой.
