# ADR-0036: reviewed SDK 0.10 provider for carrier navigation

Status: implemented for beta 11 candidate, 2026-11-07. Extends ADR-0019 and
ADR-0032; publication and packaged-game acceptance remain separate.

Promote the current Windows 1.5.18-r2 provider to CC2X SDK **0.10.0-dev**, SHA-256
`2e799fd21ee3571b7d316cf0f25e7649e55b52a2777b2dc0bb84751018dc7ad5`.
Synchronize the bundled DLL, reviewed profile and source-build restore lock.
The C API 8 prefix, framework API 1 and Lua API 2 remain supported. New optional
engine interfaces do not move gameplay policy into ModLoader.

The source snapshot is SDK commit `50f197b406314c52ac53148bdddd599eeb1a0007`.
The owner accepted Carrier: Autopilot Waypoints alpha.4 in the ordinary Steam
installation with Revolution through the existing ModLoader GUI transaction.
This is scoped SDK/gameplay evidence; it does not certify the newly frozen
beta 11 executable, every gameplay case, combat expenditure or multiplayer.

Preserve the exact tested DLL and its original dirty build record. Do not rebuild
it solely to change provenance labels. A packaging-only alternative accepts this
record only with a profile-pinned `SDK-RELEASE.json` checksum. That receipt must
identify the exact runtime, original compiled revision, committed snapshot and
exact-binary owner acceptance. The packager still verifies every compiled source
hash against the committed source archive or explicitly listed generated input.
Missing/corrupt receipts and arbitrary working-tree replacements remain rejected.
The ordinary clean-build provenance route remains supported.

Retain the previously reviewed 0.8.1 and published 0.9 exact hashes as previous
runtimes eligible for the existing journaled upgrade. Unknown installed loaders
and unknown source DLLs remain blocked. No rollback, path or native safety gate
changes. Workshop originals and the game executable remain untouched.

Schema 2 and existing report/status contracts remain unchanged. The profile's
optional `runtime_review.source_snapshot_manifest_sha256` identifies the pinned
upstream snapshot receipt; it is packaging provenance, not permission inferred
from mod metadata. Preserve all 14 offline language catalogs byte-for-byte.

Use owned fixtures for pinned snapshot acceptance, wrong pin/runtime/source/build,
absent acceptance, false verification and changed compiled/generated inputs.
Run existing reversible-upgrade, source-conflict, unknown-loader and source-build
restore tests. Verify the actual PE32 hash, API levels, one bundled provider,
36 upstream native suites and the source/license payload without loading the DLL.
Keep Windows/macOS shared-code CI, frozen GUI smoke and game acceptance distinct.

Recommend a ModLoader release explicitly supporting the required SDK. Selecting
the SDK and gameplay mod invokes normal automatic application, with a recognized
runtime backup. A manual game-folder DLL must be copied again after an SDK runtime
update; a Workshop download alone does not replace it. Future SDK hashes still
need a reviewed ModLoader update.
