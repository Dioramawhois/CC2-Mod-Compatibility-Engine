# ADR-0003: Fail-closed, строгие базы и provenance

- **Статус:** Accepted
- **Дата:** 2026-10-25

## Контекст

Ложно успешный merge хуже явного конфликта: игра загружает мод, который молча потерял изменения. Изменения Workshop и версии SDK ведут к устаревшим решениям.

## Решение

1. Нет достоверного `B` (оригинал той же сборки) — нет automatic three-way merge.
2. Для каждого файла хранить base hash, source hashes, стратегию, порядок модов, выходной хеш, errors.
3. Неразрешённый конфликт, invalid syntax, binary collision, native plugin — **не устанавливать** автоматически.
4. Исходные моды всегда read-only, output только staging/managed dir, rollback.
5. Manual resolution действителен только для конкретного набора source hashes.

## Последствия

+ Воспроизводимость и контроль повреждения сборок.
- Больше блокировок, меньше «магического» автослияния.

## Отвергнуто

Last-mod-wins, silent fallback, guessing baseline, in-place modification.
