# ADR-0018: настройки native-мода без ручного редактирования INI

Статус: реализовано для завершения GUI-only сценария. Дата: 2026-11-03.

Modes и Brake без настроек наблюдают за игрой, но ничего не меняют. Одной копии
DLL недостаточно. Для точного reviewed native hash профиль может содержать
`config_defaults`: безопасное имя INI → UTF-8 текст с проверенными defaults.
Декларация мода или имя файла не дают такого разрешения неизвестному DLL.

При выборе мода workflow создаёт только отсутствующие настройки в собственном
SDK namespace `<user-data>/cc2x`. Существующие пользовательские значения остаются
без изменений. Нет действий через консоль, ручного копирования или редактирования
INI. Другие папки, nested paths, reserved Windows names, DLL и произвольные
source-provided настройки запрещены. Несовместимые defaults двух approved
providers блокируют набор независимо от порядка патчей.

Settings публикуются полным файлом через no-overwrite hard link. Предварительно
подготовленный inode, hash и cache identity записываются в recovery journal.
Это позволяет после сбоя отличить собственное создание от файла другого writer,
даже если байты совпали. Ошибка/прерывание/Undo удаляет только matching собственные
файлы; изменённые пользовательские файлы сохраняются. Cache link удаляется после
commit, настройки остаются. Не поддерживающая операцию файловая система приводит
к обычному безопасному отказу, без частичного применения.

Package schema v2 имеет optional `config_defaults` с desired hash, approved
provider hashes и policy `create-missing-preserve-user`, без пользовательских
значений. Повторный apply восстанавливает отсутствующие settings и проверенный
runtime, даже если payload/build ID не изменился. Ранее здесь был false-success
раннего возврата без восстановления удалённого runtime.

Регрессии: создание/Undo, user preservation, modified-file preservation,
ordinary failure, interruption/recovery, same-bytes race, deleted settings/runtime,
unsafe filenames, unknown native и conflicting providers. Все DLL в fixtures —
синтетические byte-copy данные, никогда не загружаются. Config defaults не
доказывают игровой эффект или multiplayer: они требуют соответствующего review.
