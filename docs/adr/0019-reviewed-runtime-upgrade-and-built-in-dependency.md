# ADR-0019: обратимое обновление проверенного общего SDK

Статус: реализован механизм; новые production hashes требуют отдельной приёмки.
Дата: 2026-11-03. Уточняет runtime lifecycle ADR-0009.

Новая общая библиотека должна обновлять известный старый runtime без ручного
удаления DLL и сохранять неизвестный загрузчик пользователя. Профиль точного
game EXE содержит expected runtime hash и optional `previous_runtime_sha256`.
Только эти предыдущие hashes допустимы для обновления. Source wrappers старого
SDK сохраняются и записываются в optional `runtime_inputs` package schema v2;
их DLL не подменяют текущий runtime. DLL никогда не сливаются.

Порядок поиска: установленный exact runtime, hash-addressed app runtime_data,
libraries. Bundled bytes обязательно проверяются. Наличие runtime directory или
метки library само по себе ничего не разрешает. Механизм не включает новый DLL
в публичный профиль автоматически.

Если dependency `cc2x.runtime` отсутствует среди source packages, точный
доступный reviewed runtime удовлетворяет её без фиктивного мода. Реальный
поставщик из Workshop/libraries имеет обычный приоритет dependency resolution;
cycles/ambiguous/missing других зависимостей остаются ошибками. Прямая попытка
выбрать отсутствующий source ID не маскируется dependency fallback.

До записи DLL stage фиксирует original backup hash, staged inode, exact game
identity и runtime target. Recovery journal публикуется до atomic replace.
Installation на свободное место использует no-overwrite hard link, upgrade —
hash-guarded atomic replace на том же volume. Ошибка/прерывание/Undo восстанавливает
предыдущий известный runtime либо удаляет собственную новую установку. Это
заменяет прежнее разрешение оставлять newly installed SDK после Undo.

Внешняя замена DLL, включая такой же hash с иным inode, или обновление EXE
останавливает runtime rollback и сохраняет journal/backup.
Собственные resource/settings изменения откатываются до проверки runtime, чтобы
внешняя замена DLL не удерживала новый payload вместо прежней рабочей сборки.
Recovery повторяем; уже восстановленный исходный hash принимается. Неизвестные DLL не удаляются
и не перезаписываются. Игра должна быть закрыта перед apply/recovery/Undo.

Fixtures до реализации: upgrade/Undo, initial install, обычный сбой и interruption
после публикации DLL, unknown runtime, внешний writer, прежний source wrapper,
изменённый EXE, exact/corrupt bundled bytes и missing fallback. Native fixtures
содержат только copy-only синтетические bytes и никогда не загружаются.
