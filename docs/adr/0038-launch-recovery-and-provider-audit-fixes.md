# ADR-0038: Launch, recovery and SDK provider audit corrections

Status: source implementation with Windows regression verification, 2026-11-07.
Extends ADR-0010/0034/0035/0037.
This is not a release or fresh gameplay acceptance record.

## Problem and scope

An audit of beta 12 reproduced unsafe recovery when the game starts during an
apply, a launch/apply interleaving across application instances, partial journal
publication, pre-journal staging leaks, incorrect GUI recovery/row state and
SDK provider lifecycle failures. See the [audit report](../reviews/2026-11-07-modloader-bug-audit.md).
All reproductions use owned fixtures, inert DLL bytes and mocked process starts.

## Transaction and launch boundaries

Serialize the final launch checks and process creation with the same per-user
activation lock as apply, Undo and recovery. A pending journal blocks launching
even when the fixed package path is unchanged. Preserve the existing executable,
activation, package and runtime verification; a GUI precheck alone is insufficient.

Check game state after acquiring the lock and before recovery mutations. If a
game is detected after publication begins, preserve the journal and backups and
defer recovery until closure. Do not enter rollback merely because detecting a
running game raised an apply error. External Steam launches cannot be serialized
by this application lock; process checks reduce that remaining external race,
and the application must never intentionally recover after detecting the game.

Publish complete recovery journals through a flushed same-directory temporary
file and an atomic exclusive publication. No active package/config/runtime
mutation precedes publication. An incomplete temporary write must not create a
malformed `pending.json`. Clean owned pre-journal stage artifacts on ordinary
failure, preserving unknown replacements and all source files. Existing corrupt
journals remain a refusal, not permission to discard uncertain recovery data.

## SDK provider selection and cache

Seed the provider sequence floor and signed identity from the verified bundled
receipt, requiring agreement with the bundled profile. An older signed source
or cached installed provider cannot supersede a newer bundled fallback. Signed
sequence ambiguity must include the bundled release. Preserve legacy reviewed
unsigned profiles and the richer review evidence for the unchanged fallback.

Keep immutable signed receipts and use verified indexes for exact runtime and
release-sequence lookup. Normal selection must not enumerate all historical
receipts. Support bounded migration of legacy receipts without losing installed
or Undo recognition because there are more than 256 entries. Reverify signatures,
game/runtime identity and index consistency. Invalid unrelated cache contents
grant no approval. No runtime is selected solely because a receipt exists.

Resolve unavailable dependencies with the effective verified runtime provider.
A quarantined unselected SDK source may remain diagnosed without rejecting a
consumer whose SDK dependency is already supplied. Explicitly selecting the
bad source, unresolved non-SDK dependencies and unknown installed loaders retain
their blocking behavior. The GUI uses this backend decision rather than a
duplicated earlier availability gate.

## GUI and contracts

On incomplete recovery, cancel requested automatic launch, block unsafe controls
and show a recovery-specific explanation with a refresh/retry action. Reconcile
checkboxes only from verified owned active resource files; otherwise show unknown
state. Even a verified resource selection does not imply native recovery is done.
An eventual successful recovery must leave this state without requiring restart.

Reconcile row ownership before rendering Mods and Libraries so a package changing
kind has exactly one row in its new section. Preserve unrelated widgets, scroll
behavior and ordinary checkbox application.

No package schema or report metadata fields change: package schema 2, signed
provider schema 1 and diagnostic schema 1 remain. Preserve source/base/engine
hashes, recorded provider provenance and reproducible mod order. Add all recovery
messages to all 14 offline catalogs; no external translation services are used.

## Verification limits

Regression fixtures cover interrupted journal writes, staging failures, launch
interleavings, running-game recovery refusal, provider downgrade/cache migration,
quarantined dependencies and real Tk row/recovery behavior. Full source checks,
frozen application checks, macOS checks and live game acceptance must each be
reported separately. No fixture executes mod Lua or fixture DLLs.
