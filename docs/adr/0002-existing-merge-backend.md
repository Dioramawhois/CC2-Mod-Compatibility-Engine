# ADR-0002: Используем готовый diff3/Git backend

- **Статус:** Accepted; выбор тонкого адаптера уточнён [ADR-0006](0006-read-only-first-slice.md), игровой spike M0 ещё открыт
- **Дата:** 2026-10-25

## Контекст

Задача не требует писать собственный алгоритм diff3. Есть Python `w3scriptmerge` (BSD-3-Clause), Git merge-file и libgit2. Первый использует GNU diff3 и содержит game-specific логику.

## Решение

Для MVP взять **готовый `git merge-file -p`**, адаптировать объектную модель `base / mod variants / merged` из `w3scriptmerge`. На Milestone 0 определить, выгоднее ли форкнуть конкретный файл w3scriptmerge или самостоятельно реализовать тонкий CC2-адаптер поверх Git. Использовать только корректную обработку return-code и структурированных конфликтов; не копировать эвристику поиска временного каталога в конфликтном выводе.

## Последствия

+ Используем проверенный diff3, ускоряем MVP.
+ Portable core вне game/CC2X.
- Git binary — внешняя dependency; нужно `doctor`/проверка версии и корректная обработка ошибок.
- `git merge-file` — текстовый, не semantic и не binary merger.

## Альтернатива

`libgit2 git_merge_file` (C API in-memory) — возможно для будущей интеграции/скорости, не обязательна в Python MVP.
