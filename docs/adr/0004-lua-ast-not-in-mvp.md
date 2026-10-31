# ADR-0004: Lua AST только после текстового MVP

- **Статус:** Accepted
- **Дата:** 2026-10-25

## Контекст

AST-aware merging способен уменьшить ложные Git conflicts, но `semantic-merge` не поддерживает Lua из коробки. Даже AST clean может создать семантический баг.

## Решение

MVP: plain Lua text 3-way + syntax validator Lua 5.3 + game smoke. P2: эксперимент `tree-sitter-lua` с identity matching функций и обязательным safety fallback.

## Условия продвижения P2 в production

- Золотые кейсы text merge без регрессии.
- Тесты parser failures, rename/delete/modify, mutual conflicting functions.
- Метрики false conflict reduction, ноль известных false-success на test corpus.

## Последствия

+ Не блокируем MVP сложным parsing.
- Часть независимых изменений рядом может конфликтовать и требовать ручной merge.
