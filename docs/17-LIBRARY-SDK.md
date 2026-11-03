# 17. SDK: моды и библиотеки в Steam Workshop

Новый development publisher сохраняет самостоятельные Bridge VM в отдельных
контейнерах одного output, без merge их manifests/entry Lua. Приоритеты manifest
и обязательный runtime capability описаны в [ADR-0017](adr/0017-independent-lua-module-bundles.md).
Обычные game Lua overlays продолжают прежний pipeline; метка library не
заменяет проверку runtime/DLL и не добавляет сетевой транспорт.

**Распространение:** [полный аудит Steam](19-STEAM-DISTRIBUTION-AUDIT.md) и [metadata для авторов](../distribution/workshop/README.md). Steam Required Items — soft relation по PublishedFileId; requires — локальная зависимость по package ID. Для первого запуска bootstrap нужен отдельно, подписка его не устанавливает автоматически. DLL остаются отдельными plugin файлами под общим runtime; компиляции всех библиотек в один injector нет.

Это контракт для авторов пакетов. Игрок выбирает готовый пакет в GUI и не редактирует XML/JSON.

## mod.xml

Сохраняется обычный CC2 layout: mod.xml, optional thumbnail.png, content. Дополнительная секция находится в mod.xml, который входит в Workshop package. Пример: [library-mod.xml](../examples/library-mod.xml).

Для локальной обёртки предоставленного runtime CC2X 0.5.1 есть отдельный [cc2x-runtime-mod.xml](../examples/cc2x-runtime-mod.xml): library ID `cc2x.runtime`, SDK `cc2x`, API 4. Он не изменяет DLL и не заменяет проверку её hash/совместимости; отсутствие mod.xml в существующей папке SDK сохраняет default-классификацию обычного мода.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<data name="Example Library" author="Author" description="CC2X library">
  <cc2mce schema="1" type="library" id="example.library" sdk="cc2x" api="4">
    <requires id="example.base"/>
  </cc2mce>
</data>
```

| Поле | Значение |
|---|---|
| `schema` | Обязательно `1`; неизвестная версия не угадывается |
| `type` | `library` или `mod` |
| `id` | Стабильный package ID; если отсутствует, ID папки/Workshop item. Один безопасный компонент без traversal, slash или reserved Windows names |
| `sdk` | Optional `cc2x`; неизвестный SDK блокируется |
| `api` | Минимальный CC2X API как целое 0..10000; без поля — 0 |
| `requires/@id` | Package ID зависимости; исходный folder/Workshop ID также разрешается |

Нет секции `cc2mce` — это **обычный мод**. Нахождение в папке libraries само по себе не превращает пакет в библиотеку. Duplicate sections, неизвестные атрибуты/элементы, повторные/self dependencies, malformed XML и DTD/entities запрещены. Отсутствие секции не означает заявления об отсутствии runtime-зависимостей: фактические DLL всё равно обнаруживаются.

## Ресурсы и исполнение

```text
MyLibrary/
  mod.xml
  content/
    scripts/library_custom_5.lua
    cc2x/cc2x_example.dll
```

Lua размещается по настоящим игровым logical paths. Для обычных Lua расширений CC2 использует library_custom_0..9; автор должен выбрать/задокументировать слот и способ подключения. Metadata не заставляет произвольный Lua-файл автоматически исполняться. Одинаковые пути остаются кандидатами на проверенный three-way, разные новые файлы без общей базы не склеиваются. Нельзя молча переназначать слот или менять смысл скрипта.

DLL остаётся отдельным плагином с ABI CC2X, попадает в content/cc2x активированного combined mod вместе со всеми поддержанными ресурсами. Единственный runtime dinput8.dll находится рядом с игрой. Метка library не разрешает исполнять неизвестный бинарник: нужны поддержанные game/runtime и reviewed plugin identity. Companion assets, plugin_dir, API и filename collisions проверяются; неопределённый случай блокируется.

Зависимости ищутся среди Workshop, local mods и libraries, добавляются перед зависимым пакетом и записываются в mod_order. Цикл, missing dependency или неоднозначный ID блокирует применение. Отдельного ручного перемещения подписки Workshop в игру не требуется; sources читаются на месте, output создаётся отдельно.

## Контракты и проверка

Discovery report v1 дополнен optional package_kind/package_id/dependencies/sdk/api, старые отчёты остаются валидны. Game-ready package использует manifest/schema v2; наличие type=library само по себе не ставит installable=true. Любое изменение mod.xml меняет source hash и отменяет ранее проверенный plan.

Дополнительная секция mod.xml использована в реально активированном combined mod: игра дошла до меню и CC2X прочитал имя пакета. Реальная публикация/повторная загрузка собственного Workshop library item в этой задаче не выполнялась. Upstream CC2X layout: [plugin guide](https://github.com/Dioramawhois/Carrier-Command-2-extender/blob/main/docs/PLUGINS.md).
