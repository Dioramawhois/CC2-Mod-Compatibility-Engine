# Workshop: подготовка авторских пакетов

Metadata-шаблоны для автора, не готовые игровые моды и не установленный загрузчик. Публичная лицензия ModLoader, точные runtime sources/notices и private upload acceptance ещё нужны. [Полный аудит](../../docs/19-STEAM-DISTRIBUTION-AUDIT.md).

- `runtime-library/mod.xml` объявляет библиотеку `cc2x.runtime` для API4. В собственный publish folder автор добавляет **свой проверенный** `content/dinput8.dll` CC2X0.5.1, preview и лицензии/доступ к соответствующим исходникам. Template не содержит DLL. Этот item доставляет runtime, но не устанавливает его рядом с игрой сам.
- `dependent-mod/mod.xml` показывает зависимость на стабильный ID. Автор переносит секцию cc2mce в свой мод и размещает собственный Lua/plugin payload по SDK-контракту. Без секции существующий мод читается обычным модом.
- `WORKSHOP_DESCRIPTION.bbcode` — заготовка страницы библиотеки. Замените `SETUP_DOWNLOAD_URL` реальным проверенным download адресом. Пока адреса/готового installer нет, это не готовая инструкция релиза.

Сначала private upload через авторский uploader. После появления настоящего PublishedFileId на странице каждого зависимого мода добавьте библиотечный item в **Required Items**. Не вписывайте выдуманный Steam ID в XML: локальная зависимость использует `cc2x.runtime`, Steam relation — реальный PublishedFileId. Установку проверьте на другом аккаунте: soft dependency не обещает автоматический bootstrap.

Первый запуск игрока должен быть через готовый GUI installer/ModLoader, затем выбор модов и «Запустить игру». Терминал и редактирование конфигов игроку не нужны. Текущий portable exe ещё требует размещения рядом с игрой; новый self-install flow описан в аудите как следующая работа.

Не публикуйте эту папку целиком без подготовки: здесь нет thumbnail, payload или Workshop ID. Не добавляйте сторонние моды/оригиналы игры. На обновлении runtime сохраняет стабильный package ID, новая DLL проходит review.
