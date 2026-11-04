# ADR-0033: package validated SDK screen extensions with the managed menu

Status: accepted for beta 9, 2026-11-04. Extends ADR-0030 and ADR-0032.

The current Island Airfields declares schema-2 screen extensions. The blanket
native classification of `cc2x/**` incorrectly rejected its JSON descriptor as a
DLL; replacing that descriptor with the owned menu would lose mod functionality.

Recognize only `cc2x/screen_extensions.json` and explicitly referenced Lua as
typed SDK metadata. Validate schemas, duplicate keys, exact types, capabilities,
paths, ownership, Lua syntax and SDK bounds before activation. All other native
files retain their existing review gate; no mod Lua runs in developer checks.

Copy helpers byte-identically into deterministic owner namespaces under
`cc2x/ui/`. Rewrite only source references. Preserve profile hashes, offsets,
removals and inserted strings without applying edits to disk or guessing a base.
Combine distinct targets in mod order, append the managed menu, and record
descriptor/source/output hashes. Shared helpers are copied once but count once
per reference toward the SDK read budget.

Reject duplicate screen targets with their participants: the SDK disallows
duplicates in one package. This is a packaging limitation, not a claim that
ordinary Git-merged changes to one screen conflict. Do not concatenate entries,
strip profiles or guess profile composition. Preserve the 16-entry / 64 KiB
descriptor and 4 MiB source bounds including the owned menu.

Current Island Airfields supplies three distinct targets and two helpers;
ModLoader's main menu is a fourth target. Schema 2 permits the profile-less
managed-menu entry. Existing transactions, source revalidation, closed-game
deferral, Undo and unknown-loader protection remain.

Regressions cover schemas, namespaces, shared sources, profile preservation,
syntax/capability/path/budget failures, collisions and removal/rollback. The SDK
still checks actual in-memory hashes and may skip unknown screen sources.
Packaging does not establish gameplay compatibility. Fresh GUI/game acceptance
must identify the exact final EXE/runtime pair separately.
