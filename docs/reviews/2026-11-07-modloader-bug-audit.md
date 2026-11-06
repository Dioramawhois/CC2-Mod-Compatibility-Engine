# CC2 ModLoader beta 12 bug audit

Date: 2026-11-07. Audited application code: release `v0.4.0b12`, commit
`ff1d16222ce68bde1f522479d73f4d85426e18b0`; isolated worktree base
`3941dc11df8a39a0de029937b1baddb17e8919df` adds only its verification receipt.
Corrections are unreleased source changes on `codex/modloader-bug-audit`.
Decision record: [ADR-0038](../adr/0038-launch-recovery-and-provider-audit-fixes.md).

## Scope and evidence

Reviewed SDK signature/provider selection and cache lifecycle, discovery and
dependency availability, activation/Undo/recovery, final game launch, GUI row
ownership and error reconciliation. Confirmed findings use deterministic fault
injection against owned temporary data. Fixture DLLs are inert bytes, game
spawns are mocks, and GUI regressions use real Tk widgets. No fixture loads a
DLL or executes mod Lua. The Git merge and Lua syntax boundaries retain their
existing verification requirements.

The eight entries below group related symptoms by correction. A01 includes both
the two-instance launch race and the independently reproduced external game-start
rollback. P1 means unsafe changes to files used by a detected running game; P2
means a blocked workflow or incorrect selected/applied state; P3 means orphaned
owned staging without a live-set change. These are engineering priorities, not
claims of security exploitation or observed damage to the owner's installation.

| ID | Priority | Confirmed trigger and beta 12 behavior | Source correction |
| --- | --- | --- | --- |
| A01 | P1 | Another instance launches between package replacement and commit, or the game becomes detected during apply. Launch lacks the shared lock; the apply error path rolls resources/native runtime back while the game is running. | Hold the activation lock through final launch validation and spawn; reject pending recovery; defer rollback with the journal intact after game detection; recheck closure at recovery/native mutation boundaries. |
| A02 | P2 | A partial write of `pending.json` occurs before changing the live set. The next recovery cannot parse it, indefinitely blocking launch/Undo. Both apply and Undo reproduce. | Write and flush a temporary journal, then publish it atomically without overwriting an existing journal. Interrupted temporary writes leave the intact working set usable. |
| A03 | P3 | An activation-backup write fails after native/settings staging. Owned temporary DLLs, caches and package stage remain without any recovery journal. | Track owned preparation files by identity and clean unpublished artifacts on failure; preserve unknown replacements and published recovery inputs. |
| A04 | P2 | An unselected SDK source is quarantined although the installed authenticated SDK can satisfy the selected consumer. An earlier availability check rejects the consumer before verified runtime provision. | Make dependency availability aware of the verified provider and remove the duplicate GUI gate. Explicit bad-source selection and unknown-loader refusals remain. |
| A05 | P2 | Passive discovery sees a package change from library to mod. Shared ID-keyed row cleanup destroys its new checkbox while leaving the old section's widget visible. The unchanged next scan keeps the broken display. | Remove stale cross-section ownership before either render pass; cover both directions and preserve unrelated widgets. |
| A06 | P2 | An external runtime prevents the native part of Undo after resource restoration. The GUI still checks the newer set and says it is active, offering controls blocked by pending recovery. | Show explicit recovery-required state, derive selection only from verified active resource files or mark it unknown, cancel auto-launch, and clear recovery controls after a successful retry. |
| A07 | P2 | A future application bundles a newer signed SDK but an older valid source/cached receipt is available. The unsigned profile's implicit sequence zero lets the old SDK downgrade or suppress the newer fallback. | Verify the bundled signed anchor and use its sequence/identity in provider comparison, including same-sequence ambiguity. Retain the richer fallback review. |
| A08 | P2 | `remember()` saves 257 legitimate receipts; the next analysis exceeds the reader's 256-entry limit and refuses even an empty selection. Unrelated filenames also consume the limit. | Use reverified runtime/sequence indexes and a bounded legacy fallback. Preserve historical receipts for installed/Undo recognition; normal selection does not scan the full history. |

A07 is a forward-lifecycle reproduction: beta 12 currently bundles the same
official SDK 0.10 sequence-1 runtime as its released descriptor. The synthetic
newer-bundle/older-source cases prove the defect without claiming a downgrade
already happened to that real release. A08 likewise uses generated signed
fixture releases rather than inventing 257 real SDK updates.

## Regression coverage

- [Transaction publication and process-state faults](../../tests/test_transaction_publication_safety.py): partial apply/Undo journal writes, pre-journal backup/publication failure, closed-game recovery and shared launch locking.
- [Verified runtime dependency fallback](../../tests/test_verified_runtime_dependency_fallback.py): quarantined dependencies with verified provision and strict explicitly selected/unknown-loader rejection.
- [Provider lifecycle](../../tests/test_runtime_provider_lifecycle.py): bundled sequence floors, ambiguity, 257 normal receipts, legacy cache compatibility and historical provider recognition.
- [Real Tk state regressions](../../tests/test_gui_audit_regressions.py): cross-section row changes, verified/unknown partial Undo state, recovery retry and quarantined SDK use.
- Existing launch diagnostic/export and 14-language placeholder/coverage fixtures include the new recovery messages and pending-recovery launch reason.

Final integrated source validation on Windows, Python 3.12.15:

- Full suite: **669 passed, 10 skipped, 0 failed** in 213.94 seconds.
- Seven skips require unavailable symlink creation; two require the optional
  Lua interpreter. Syntax validation has its separate bundled-tool boundary.
  One existing Tk discovery case skipped during window construction in the full
  process; that exact case passed in a fresh process (1 passed, 0 skipped).
  The seven new Tk regression cases passed. A skip is not GUI acceptance.
- Ruff check passed; Ruff format check passed for 87 files; mypy passed for all
  32 application source files. `git diff --check` passed.
- Read-only analysis of the real installed collection found 22 packages, no
  inventory diagnostics and no blockers for the eight currently selected mods.
  SDK runtime remained `2e799fd21ee3571b7d316cf0f25e7649e55b52a2777b2dc0bb84751018dc7ad5`.
  Observed game/application/runtime/manifest/activation and receipt-cache hashes
  were unchanged; no apply or game spawn was attempted.

Exact source hashes, check counts, skipped cases and evidence digests are retained
in the [verification receipt](../verification/MODLOADER_AUDIT_2026-11-07.json).
This records source validation, not a rebuilt or installed executable. No macOS
CI/package or new live game run was performed for these corrections; beta 12's
earlier release checks do not certify the changed source.

## Remaining boundaries

The shared lock coordinates ModLoader instances, not external Steam launches.
An external process can still start between a process-state check and a single
filesystem operation. The correction avoids deliberate mutation after detection;
it does not claim an atomic operating-system lock against every external launch.

Existing corrupt/externally changed journals, packages or DLLs remain preserved
refusals. The audit does not silently delete uncertain recovery data. Cache
migration retains bounded input processing; a missing or invalid proof never
authenticates unknown native bytes.

A hard process kill before journal publication can still leave inactive stage
or temporary files. The atomic publication correction prevents a partial final
journal and pre-publication live-set mutation; it does not promise cleanup by a
process that was forcibly terminated.

No new gameplay, clean-machine, multiplayer, dedicated-server or packaged macOS
acceptance is established by the fault-injection and Tk checks. Publication and
installation of a new executable are separate from these source corrections.
