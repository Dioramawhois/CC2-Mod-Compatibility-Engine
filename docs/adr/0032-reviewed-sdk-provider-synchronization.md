# ADR-0032: synchronize the reviewed SDK provider and identify source mismatches

Status: accepted for beta 9, 2026-11-04. Refines ADR-0019's reviewed runtime
upgrade and built-in dependency policy; it does not relax native approval.

## Problem

A player tried to uncheck Island Airfields after Steam had updated the selected
SDK package. ModLoader still pinned SDK 0.7.1 while the downloaded package
contained SDK 0.8.1. Rebuilding the remaining libraries rejected the source DLL
with `runtime_conflict`, the same code used for an incompatible loader already
installed in the game. The diagnostic therefore blamed the installed loader
and did not identify the library responsible for the rejected change.

Treating the new source hash as merely another previous version would hide the
mismatch: ModLoader would continue selecting the older bundled provider. The
runtime/profile/source pin must be promoted together after review.

## Decision

1. Select the reviewed SDK **0.8.1-client-beta.1** provider for the supported
   Windows game profile. Its DLL SHA-256 is
   `98ba9bfbc217767ecc5a30aaa3cd5de8d3d7de1f9e8a9164cd0e0e32a6bed085`;
   its source revision is `f322938094bf7ea9e30f3be841b3c744687385b8`.
   Update the bundled dependency, profile and source-archive restore lock
   consistently. Retain exact-source/license provenance.
2. Preserve existing reviewed capabilities and add `waypoint-origin-v1` and
   `screen-source-edits-v1`. These are framework capabilities; gameplay policy
   and content still belong to separately selected mods. API compatibility
   review and offline SDK tests do not certify new gameplay behavior.
3. Retain the reviewed 0.7.1 hash
   `c741ed111cdb186463c01f6e9e189fb80ee15b43bc52e6bacdd92fe88ee95d12`
   as a previous runtime eligible for a journaled upgrade. The current provider
   stays 0.8.1 when a selected source package contains a reviewed previous DLL.
   Never add an unreviewed future hash as a previous version to bypass review.
4. Use `runtime_source_conflict` when a selected source package contains a
   runtime outside the current/previous reviewed set. Add a `files` record for
   `dinput8.dll` with that status, strategy `blocked`, participant source hashes,
   null output hash and diagnostics. Add a blocker with the same code and file.
5. Reserve `runtime_conflict` for an incompatible installed game-folder loader.
   Preserve that external file. No source-package approval authorizes replacing
   an unknown installed loader, and the current runtime is never inferred from
   a filename or a DLL supplied by an unreviewed package.
6. Explain the source mismatch separately in all 14 offline catalogs. The
   rejection feedback identifies its SDK participant even when the action was
   removing another gameplay mod. Preserve the actual applied checkboxes,
   working package and available rollback; do not show SDK test-status notices.
7. Keep schema version 2. Status/code fields already accept strings; the new
   values and ordinary blocked-file record are additive. Source hashes, runtime
   input hashes, provider selection, mod order and output provenance retain
   their existing meanings. DLLs remain byte-identical separate files.
8. Use the existing closed-game apply transaction, runtime backup, integrity
   checks, recovery journal and Undo for a supported provider upgrade. Workshop
   source files, vanilla files and the game executable remain untouched.

## Validation and scope

Synthetic fixtures exercise a source SDK update followed by removing the
gameplay mod, old-to-current installation and Undo, unsupported source bytes
with a correct installed runtime, an unknown installed loader, and a reviewed
old source with a current provider. The source conflict must name the SDK in
the report and GUI feedback. Fixture DLL bytes are never executed.

Review upstream runtime provenance and ABI-prefix compatibility before
promoting the dependency. Keep SDK offline tests, application regressions,
frozen-GUI tests and real-game acceptance distinct. Beta 7's exact 0.7.1 menu
evidence remains historical; it does not certify the new beta 9/0.8.1 pair.
Remote multiplayer, dedicated-server, clean-machine and packaged macOS
acceptance remain separate release gates.
