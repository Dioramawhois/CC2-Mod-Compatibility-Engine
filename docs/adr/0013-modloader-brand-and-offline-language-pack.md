# ADR-0013: CC2 ModLoader и офлайн-пак основных языков

- **Статус:** Accepted по прямому запросу владельца 2026-11-02.
- **Версия:** 0.3.1.

1. Название приложения и заголовка — **CC2 ModLoader**, стабильный exe — **CC2ModLoader.exe**. «Engine» остаётся техническим понятием ядра/репозитория, а не пользовательским названием. Старый собственный CC2Engine.exe сохраняется в backup и убирается из игровой папки после установки новой сборки; неизвестный бинарник не перезаписывается.
2. Имя generated mod снова содержит названия выбранных модов: `CC2 ModLoader: A + B`, до 240 символов. Постоянная папка CC2-MCE и owner/schema/provenance не меняются. Locale не меняет output identity.
3. Offline catalogs: RU, EN, DE, FR, ES, PT-BR, IT, PL, TR, UK, zh-CN, zh-TW, JA, KO. Системные locale variants сопоставляются к поддержанному коду, включая traditional Chinese TW/HK/Hant; неизвестные локали используют English. Меню показывает native names.
4. Каждая дополнительная локаль содержит все 174 текущих message IDs и сохраняет named placeholders. Основные labels выверены отдельно; остальные сообщения имеют машинный перевод. Software-library terminology для CJK/KO нормализована. Полная профессиональная лингвистическая редактура не заявляется.
5. Каталоги — локальные project data, включённые в source hash и frozen bundle. Runtime Translator не делает сетевых запросов. Developer-only генератор переводит только опубликованные собственные UI messages; пользовательские имена/пути/моды/preferences не отправляются.
6. Preferences schema 1 обратно совместимо принимает новые language codes. По умолчанию остаётся system, явный выбор сохраняется. Проверки полной key/placeholder coverage обязательны.
7. CI runner macos-14 заменён на macos-15: старый image снят с поддержки 2026-11-02 по [официальному объявлению](https://github.com/actions/runner-images/issues/13518). Это смена test host, не заявление нового минимального macOS runtime или game support.

Проверки: каталоги/locale mapping, параметры и неизменность имён/путей, имя generated mod, frozen product title/executable and source data. Все прежние merge/order/native/path/syntax/rollback gates сохраняются.
