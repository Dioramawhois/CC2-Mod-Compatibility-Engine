# ADR-0020: проверенный клиентский SDK в локальном кандидате 0.4.0b2

Статус: реализован для локальной клиентской приёмки, не объявлен полным релизом.
Дата: 2026-11-03. Дополняет ADR-0017/0018/0019 и уточняет этапы docs/22.

Сам publisher без доступного API 8 runtime оставлял новый набор недоступным в GUI.
После проверки реальной клиентской игры кандидат включает точные bytes общего
SDK 0.6.0-dev и точные проверенные hashes Hold/Modes/Brake/Island Airfields v46.
Старый v45 profile сохраняется. Никакой неизвестной DLL не разрешается по имени,
расположению, происхождению от команды или декларации library.

Основание review: известный EXE, PE32/API-prefix/native guards, clean source build,
19 native/SDK и 19 Python regressions, загрузка всех plugins вместе, два готовых
custom definitions, реальное создание F-16/F-15, сохранение в новый пустой slot,
загрузка того же save с ID 102/103 и повторный успешный spawn в новой session generation.
Read-only snapshot после reload подтвердил сохранённые vehicle IDs и dock/carrier.
Авторские Lua/DLL исполнялись только внутри игры. До/после проверки сохранены и
восстановлены прежние runtime, output, activation/Undo и пользовательские save files.

В bundle лежат лицензии/notices, исходный clean build report и source commit
`2eecbd93c3555fed9a2b3f25e5b9c91abb55196f`. Runtime выбирается только по expected
SHA профиля; повреждённый bundle блокируется. Upgrade только с прежнего exact
0.5.1 hash и через journal ADR-0019. Моды и их настройки не встраиваются в DLL:
native plugins остаются самостоятельными approved copies, Lua — отдельными contexts.

Это отдельный **client-candidate** этап, а не закрытие полного native release gate
из docs/22. Публичная beta 0.4.0b1 и установленная exe не заменяются автоматически.
Полный stable/native релиз, remote multiplayer, dedicated, смена каталога в saves,
полный полёт/посадка и clean-machine/macOS acceptance остаются открытыми.
Профиль не утверждает прохождение этих проверок.

Package schema v2 сохраняет optional `runtime_review`: stage, source/version,
verified/unverified scopes, evidence hash и явные multiplayer/dedicated false.
GUI использует существующий постоянный notice без новых кнопок: SDK проверен в
одиночной игре; multiplayer/dedicated не проверены. Он виден и без перезаписи
ресурсов, сочетается с existing override warning и восстанавливается при reopening.
Все 14 offline catalogs содержат эти сообщения. Обычный data-only набор такого
предупреждения не получает. Readiness в GUI означает применённый пакет, а не
полную совместимость всех gameplay-механик.

Fixtures до реализации проверили binding profile/DLL/PE/provenance/licenses,
ограниченный список INI defaults, native notice без collision, совместное
предупреждение с именами участников и отсутствие native notice у data-only sets.
