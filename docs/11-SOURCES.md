# 11. Первоисточники и проверенные основания

Проверено по открытым источникам 2026-10-25. Источники ниже — для проверки реализации. Любые гипотезы отдельно помечены «проверить на M0».

## Официальное и игровое

- [Geometa: Using Modifications](https://geometa.co.uk/wiki/carrier_command_2/view/using_modifications) — Workshop, ручное включение, запрет одновременно активировать моды с одинаковыми файловыми путями, multiplayer behavior.
- [CC2 Steam News](https://steamcommunity.com/app/1489630/announcements/) — v1.5.10 добавил modifiable `constants.txt`, v1.5.8 дал shared Lua libraries.
- [SteamDB: обновление 1.2.0 и Mod SDK](https://steamdb.info/patchnotes/8245308/) — поставка Mod SDK с asset sources (исторический факт, актуальный layout проверять локально).
- [SteamDB: Depot Win32](https://steamdb.info/depot/1489631/history/) — подтверждение наличия `mod_dev_kit` в файлах дистрибутива.
- [CC2 community knowledgebase: General Mod Advice](https://github-wiki-see.page/m/cc2modteam/knowledgebase/wiki/General-Mod-Advice) — модель «replace by file», примеры модифицируемого контента.

## CC2X

- [Dioramawhois/Carrier-Command-2-extender README](https://github.com/Dioramawhois/Carrier-Command-2-extender) — dinput8, plugin loader, license.
- [CC2X docs/PLUGINS.md](https://raw.githubusercontent.com/Dioramawhois/Carrier-Command-2-extender/main/docs/PLUGINS.md) — DLL x86, `content/cc2x`, plugin load, loader lock, GPL, `cc2x.log`.
- [CC2X docs/README_PLAYERS.txt](https://raw.githubusercontent.com/Dioramawhois/Carrier-Command-2-extender/main/docs/README_PLAYERS.txt) — game 1.5.18 Windows, unsupported VR/server/macOS.

## Готовые merger/инструменты

- [w3scriptmerge](https://github.com/apocalyptech/w3scriptmerge) — Python 3, BSD-3-Clause, GNU diff/diff3, архитектура baseline/source/merged.
- [Исходник w3scriptmerge.py](https://raw.githubusercontent.com/apocalyptech/w3scriptmerge/master/w3scriptmerge.py) — конкретная схема последовательного `diff3` и ограничение своей conflict detection эвристики.
- [Git: merge-file](https://git-scm.com/docs/git-merge-file) — CLI/API/exit behavior.
- [libgit2: git_merge_file](https://libgit2.org/docs/reference/main/merge/git_merge_file.html) — 3-way merge in memory без репозитория.
- [Witcher 2 Script Merger](https://github.com/pjominet/w2sm) — UI/packaging, README предупреждает о «MIT Non-Commercial», не использовать код без проверки.
- [WitcherScriptMerger](https://github.com/AnotherSymbiote/WitcherScriptMerger) — KDiff3, XML/scripts, GPL-2.0.
- [semantic-merge](https://github.com/gaurvinayak/semantic-merge) — tree-sitter AST-aware, перечень языков **без Lua**, MIT, Node >=18.
- [KDiff3](https://github.com/KDE/kdiff3) — GUI для разрешения конфликтов.

## Что НЕ было подтверждено первоисточником в ходе этой фиксации

- точная схема `mod.xml` и локальных модов на конкретном ПК;
- точное и универсальное отображение файлов Mod SDK в `content/` по всем классам ресурсов;
- работа `git merge-file` на реальном наборе пользовательских CC2 модов;
- возможность динамического hook’а CC2X для ресурсов без дополнительной работы;
- совместимость конкретных пар Workshop-модов и native DLL.

**Правило:** гипотезы не становятся фактом в коде, issue или README до теста/подтверждения. Если обнаружена ошибка в источнике, обновить этот список и затронутые ADR.
