# ADR-0015: игровые шейдеры/текстуры и конкретная причина отказа

- **Статус:** Accepted
- **Дата:** 2026-11-02
- **Основание:** пользователь увидел «Это изменение пока нельзя безопасно подключить» при включении Papa Bear's Combined Fleet (Rev1.6).

Read-only воспроизведение текущего applied набора плюс Workshop3783006839 показало ровно четыре needs_review/Unknown resource type: shaders/screen_crt.glsl, shaders/screen_crt_hud.glsl, textures/button_panels/index_surface_0.txtr и textures/screen_ui/index_surface_0.txtr. Это был пробел классификатора, не доказанный merge conflict. Все четыре пути существуют в установленном rom_0, шейдеры также в Mod SDK. Текстуры имеют magic TXTR. Источники не менялись, моды/шейдеры не исполнялись.

## Решение

1. `.glsl` — текстовый игровой ресурс: UTF-8/EOL/conflict-marker validation, byte copy для unique, настоящий Git three-way для пересечений и прежний ordered-patches policy. Специальные CC2 shader directives не переписываются. Проверка GLSL compiler/GPU/link stage не реализована и не заявляется.
2. `.txtr` — известный binary resource только при magic TXTR. Unique/identical сохраняются побайтно; разные варианты блокируются в strict или заменяются целиком поздним модом с overridden/ordered-binary-replacement и постоянным предупреждением. Полный decoder/validator внутренней структуры TXTR не реализован: magic — классификация, не обещание валидности текстуры.
3. Проверяются типы **всех** вариантов. Неизвестный/повреждённый header поздней или ранней текстуры не обходится дедупликацией/приоритетом. Остальные неизвестные форматы по-прежнему блокируются; DLL native review не ослаблен.
4. needs_review больше не превращается в безликое утверждение о безопасности. Unknown type называет файл и отсутствие поддержки. Missing/wrong Lua validator объясняет сбой встроенного инструмента. Другие diagnostics доступны в подробностях; основной banner также содержит первый проблемный путь. Все 14 языков обновлены.
5. Контракт report v1/v2 не меняется: те же kind/status/strategy/diagnostics/hashes. Изменяются допустимые известные resource types и UI projection, поэтому fixtures/specs/changelog обновлены.

Проверки до реализации воспроизвели оба неподдержанных формата и две нечитаемые ошибки. Regression покрывает real Git shader merge, невалидный UTF-8, TXTR byte identity/strict conflict/ordered replacement и неизвестный header в каждом положении. Реальный read-only plan текущего набора плюс Combined Fleet после исправления имеет ноль blockers; это **не игровая acceptance** и не включает пользовательский мод автоматически.

Отдельно CI macos-15 выявил Windows-only fixture builder: он создавал carrier_command.exe, тогда как inspect_game справедливо искал macOS app executable. Синтетическая фабрика теперь следует host по умолчанию; Windows-specific tests указывают Windows явно. Добавлен тест обоих layouts и отказа противоположного host. Production game discovery не ослабляется. Успех CI не заменяет сертификацию packaged macOS приложения.
