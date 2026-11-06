# ModLoader UX and state audit — 2026-11-04

Original assessment: the staged **0.4.0 beta 9** sources at
`dabb60e649245e0f54e41a5f80b717c390ea8960`. The read-only engineering audit
after packaging covered selection truthfulness, recovery, dependency
messages, discovery, runtime errors and the 14 offline languages. It does not
certify publication status, game-menu behavior, gameplay or multiplayer.

Resolution update: **beta 10 implements all ten original findings in source**,
with the focused regressions listed below, and adds **Disable all**. See
[ADR-0034](../adr/0034-committed-activation-and-gui-state.md) and
[ADR-0035](../adr/0035-partial-inventory-diagnostics-and-ux-controls.md).
Implementation closure is separate from the final full-suite/frozen build and
the user's real-game acceptance. Historical reproductions and line references
below describe the original beta 9 snapshot, not the corrected source.

No live game, installed runtime, Workshop package or player save was changed by
this audit. Reproductions used owned temporary game/mod fixtures. Synthetic DLL
bytes were copied and hashed only; no mod Lua or DLL was executed. Where a
launch path was exercised, process creation was replaced by a mock.

Evidence levels below distinguish actual hidden-Tk/service reproductions,
presenter or callback-port reproductions, and static consequences that still
need a dedicated GUI regression. The final source-archive smoke separately
verified 211 tracked files and 49 exact frozen inputs; it did not build another
EXE or provide clean-machine/gameplay acceptance.

## Original incidents addressed before this audit

- Beta 8 removed the prototype 16 MiB resource / 256 MiB collection startup
  failure through streamed discovery, separately bounded selected builds and
  verified lazy reads. Beta 9 retains those changes. Limits remain finite.
- Beta 9 synchronizes the reviewed provider and restore pin with SDK
  **0.8.1-client-beta.1**. It preserves unknown installed DLLs, permits a
  journaled upgrade from the reviewed older runtime, and does not treat a
  known old source package as a request to downgrade the provider.
- Selected SDK source mismatch now uses `runtime_source_conflict`, distinct
  from installed-runtime conflict. Its source record lets the notice name the
  SDK even when the attempted action removes Island Airfields.
- Declared schema-1/schema-2 screen helpers have a validated packaging path.
  Their JSON/Lua data are not rejected by the blanket unhandled-native gate.
  Duplicate SDK screen owners have explicit participants and a localized
  unsupported-combination explanation. This is separate from ordinary game
  resource merging: two mods editing the same screen file can still merge.
- All 14 catalogs contain the new source-runtime and screen-extension
  messages. Ordinary rejection restores checkboxes/order/patch policy,
  cancels automatic launch and preserves the previous output. Existing GUI
  regressions cover normal rejection, launch of the intact set, persistent
  notices and mandatory dependency rechecking.

Those pre-audit fixes did not close the findings below. The beta 10 follow-up
now supplies the implementation and regression coverage shown in the table.

## Original priorities and beta 10 source closure

| ID | Priority | Original issue | Beta 10 implementation and focused evidence |
| --- | --- | --- | --- |
| UX-01 | P1 | Committed update displayed as rejected after cleanup failure | Implemented: nonfatal post-commit housekeeping; [transaction fault injection](../../tests/test_post_commit_settings_cleanup.py). |
| UX-02 | P1 | Built-in SDK dependency crashes the success callback | Implemented: supplied provider needs no checkbox row; [GUI dependency recovery](../../tests/test_gui_state_recovery.py). |
| UX-03 | P1 | Native activation replaces saved merge order | Implemented: verified owned order takes precedence; [GUI order/adoption controls](../../tests/test_gui_state_recovery.py). |
| UX-04 | P1 | Broken source hides inventory and leaves empty diagnostics | Implemented: explicit partial inventory, quarantine and no-plan export; [domain diagnostics](../../tests/test_discovery_diagnostics.py) and [owned GUI fixtures](../../tests/test_gui_diagnostics.py). |
| UX-05 | P2 | Launch refusals discard their cause | Implemented: specific notice/export and refused readiness until explicit revalidation; [owned GUI launch guards with mock spawns](../../tests/test_gui_diagnostics.py). |
| UX-06 | P2 | Undo leaves stale dependency explanations | Implemented: notes follow restored source metadata; [GUI Undo regression](../../tests/test_gui_state_recovery.py). |
| UX-07 | P2 | Screen ownership/limit refusals lack explanation or attribution | Implemented: owner/action and measured limits with contributors; [report/presenter/workflow regressions](../../tests/test_screen_extension_refusals.py). |
| UX-08 | P2 | Lua-only screen library labeled as a DLL plugin | Implemented: actual `.dll` resource determines the label; [GUI library-label controls](../../tests/test_gui_controls_recovery.py). |
| UX-09 | P2 | Changed inventory replaces checkbox widgets | Implemented: surviving rows/variables and scroll remain stable; [GUI inventory and scroll fixtures](../../tests/test_gui_controls_recovery.py). |
| UX-10 | P2 | Undo offered without usable history | Implemented: checked availability and recheck on use; [fresh/consumed/stale history controls](../../tests/test_gui_controls_recovery.py). |

P1 means an ordinary state boundary can misrepresent the applied set, change
patch priority unexpectedly, or prevent a usable recovery/support workflow.
P2 means the safety boundary remains effective but feedback or control state
is misleading. These priorities are engineering follow-up, not a claim that
every user encounters every trigger.

## UX-01 — A housekeeping failure reverses the displayed result after commit

**Beta 10 status: implemented.** An optional cache-unlink `OSError` after commit
does not reject the applied set. Fault injection verifies new package/runtime,
guarded mock launch and subsequent Undo; pre-commit failure still rolls back.

**Reproduction:** apply text mod A, then select a synthetic reviewed native
provider with a reviewed settings default. Deny only `Path.unlink` for the
application's `config-*` cache link; allow `pending.json` removal. The actual
transaction commits the new package/settings. The GUI nevertheless restores
A checked / Native unchecked and says the previous selection was preserved.

Observed result: actual package `mod_order = [native]`, GUI applied IDs `[a]`,
no pending journal. Calling the real GUI launch path with a mock spawn was
accepted and would use the new native set, despite the old visible selection.
No process or DLL was executed.

**Cause:** `workflow.py:962–967` commits activation and removes the pending
journal, then calls `sdk_settings.cleanup` outside the transaction handler.
The cache unlink at `sdk_settings.py:137–139` can raise. The GUI treats that
post-commit exception as a rejected apply (`gui.py:589–610`, `514–540`).
Unchanged passive fingerprints return before reconciling activation.

**Remediation:** make post-commit cache pruning a nonfatal housekeeping result;
reconcile actual committed state before declaring any uncertain operation
rejected. Keep genuine pre-commit failure rollback unchanged.

**Regression:** inject this exact cache-unlink failure through real Tk and an
owned transaction. Assert new checkboxes/report match the committed package,
the update succeeds, and the launch path cannot
silently use a different set from the displayed one.

## UX-02 — An available built-in SDK is missing from the row-note lookup

**Beta 10 status: implemented.** The GUI completes apply with a runtime-provided
dependency and no library row. The owned GUI regression checks applied IDs,
Ready state and absence of a fabricated selectable provider.

**Reproduction:** use the existing runtime-upgrade fixture with a mod requiring
`cc2x.runtime`, a reviewed provider available to the service, and no separate
SDK `ModRef`. Analysis returns `selected = [app]`, dependency
`cc2x.runtime`, and no blockers. Invoking the actual successful-apply callback
through its background port raises `KeyError('cc2x.runtime')`.

The callback has already assigned the new applied IDs and cleared the dirty
flag, but the status remains “Updating the shared mod folder…”. This was a
callback-port reproduction, not a fresh full transaction through Tk for this
specific case. Backend runtime-upgrade tests already permit the plan.

**Cause:** `gui.py:1164–1169` indexes dependencies only through selected mods;
the resolver can satisfy this dependency using the built-in runtime instead.

**Remediation:** represent supplied runtime dependencies explicitly when
building dependency notes; never assume every dependency has a selectable
package row. Finish the success callback even when no SDK row exists.

**Regression:** real Tk checkbox → built-in provider → successful apply,
without a Workshop SDK package. Assert no callback exception, correct Ready
state, correct checkboxes and a truthful dependency explanation.

## UX-03 — Restoring the owned selection can still reverse its saved order

**Beta 10 status: implemented.** The recorded owned order is restored with its
selection. GUI regressions distinguish this from first adoption of native
order and verify the resulting merged bytes/preferences.

**Reproduction:** prepare and save `[a, b]`, externally set native `mods.xml`
to `[b, a]` in the owned fixture, and rescan as on reopening. The GUI restores
the owned mod IDs but rebuilds and saves order `[b, a]`. Only the generated
package remains active, so the activation safety check alone does not catch
this unwanted order change.

**Cause:** `gui.py:823`, `825–829`, `853–862`: remembered state replaces the
desired ID set, while the current native `_applied_order` takes precedence
over saved preferences. Ordered patch priority can therefore change without
a reorder action in ModLoader.

**Remediation:** restore the verified owned order together with its owned
selection; use native order only for first adoption when no owned state exists.

**Regression:** use overlapping ordered patches with distinguishable winning
bytes. Reverse native activation externally, reopen, and assert the saved
loader order, resulting bytes and persisted preference order are unchanged.

## UX-04 — Discovery failure has neither source identity nor useful details

**Beta 10 status: implemented.** The GUI uses explicit partial inventory with
named quarantine issues. Strict discovery remains the default for core callers.
Domain fixtures cover malformed/ambiguous/unsafe inputs and budgets; owned GUI
fixtures retain valid rows, export without a plan, and preserve an already
applied set when its selected source becomes invalid.

**Reproduction:** startup with one valid package and one unselected package
containing invalid `mod.xml`. Actual hidden Tk ended with status
`Invalid metadata XML`, no source name, no scan, and an empty mod list.
`problem_details` was empty and `problem_report` absent. Save report dispatched
to the details action instead of exporting; its empty-details fallback was
“No problems found.”

**Cause:** discovery errors such as `discovery.py:173`, `218`, `234`, `259`
omit the offending package. The nonselection scan error path in
`gui.py:589–611` sets status without a diagnostic report. Details and export
fall back at `gui.py:445`, `1270–1274`.

The same boundary exposes raw English structural/size errors in other UI
languages. A direct translator check left the actual
`Input file byte limit exceeded: …` message unchanged in RU, DE, FR and JA;
the 14-catalog key-completeness test does not cover these dynamic errors.

**Remediation:** retain stage/source identity and an exportable diagnostic
envelope even when no plan exists; show a localized plain-language notice
with the exact path/size/cause in details. Preserve the current fail-closed
path, metadata and native checks. Any per-package quarantine would need a
separate explicit design; silently ignoring unsafe inputs is not a fix.

**Regression:** malformed XML, duplicate IDs, unsafe links and resource-limit
errors at initial/passive scan. Assert named source, useful details/report,
no “No problems found” contradiction, 14-language summaries and preservation
of any previously verified applied output.

## UX-05 — Launch guards work, but their reason is discarded

**Beta 10 status: implemented.** Specific localized diagnoses and export survive
the GUI boundary, with no spawn and no Ready state until explicit revalidation.
The GUI fixture exercises the actual changed-game-hash guard with a mock process
port and keeps it refused through an unchanged passive inventory scan.

`game_launch.py:33–47` distinguishes changed activation, tampered output,
changed game/runtime and a running/unavailable game. `gui.py:1312–1314`
catches these conditions and shows only “Could not launch game.” Details may
be empty or still describe an unrelated earlier warning. Ready controls do
not request explicit revalidation of the failed condition.

This finding is based on direct control-flow review, not a fresh failed live
game launch. The guard still prevents spawning. Unchanged passive mod
fingerprints also return before checking external runtime/activation changes
(`gui.py:763–768`), so another passive scan need not explain the failure.

**Remediation/regression:** preserve the specific refusal and required next
action in the existing notice/details/report. For each owned launch-guard
failure, assert zero spawns, preserved unknown DLLs, meaningful localized
feedback and a readiness state that agrees with the required revalidation.

## UX-06 — Undo restores files but leaves a stale dependency explanation

**Beta 10 status: implemented.** Dependency notes follow the restored package's
recorded metadata. The GUI regression changes current source metadata before
Undo and verifies that disabled/current-source dependents are not shown.

**Reproduction:** B requires A; apply `[a, b]`. C also requires A; apply
`[a, c]`. Undo correctly restores `[a, b]` and unchecks C, but A still says
“Required by Dependent C”. This was reproduced through real hidden Tk and
owned apply/Undo transactions.

**Cause:** Undo rescans without applying (`gui.py:1243–1249`), while dependency
notes are built only at apply success (`1164–1173`) and reused in row rendering
(`482–487`).

**Remediation/regression:** derive notes from the verified active dependency
snapshot after restoration. Assert A names B after Undo and no restored row
names the now-disabled C. Do not rebuild new source versions merely to refresh
these labels.

## UX-07 — Screen ownership and aggregate-budget refusals need specific feedback

**Beta 10 status: implemented.** Managed-menu collisions identify exact owners
and a disable/update action. Screen refusals distinguish entry, descriptor and
source limits with actual/maximum values and contributors, including the owned
menu. Fixtures also retain ordinary Git merging and unrelated-DLL refusal.

For `managed_menu_collision`, `workflow.py:443–447` emits only a list of paths,
without owner IDs or a mapped user explanation. The presenter reproduction
showed the entire notice and row as `scripts/screen_menu_main.lua`, with that
path repeated twice in details. This is an unsupported ownership combination,
not an unknown DLL or proof that ordinary same-file edits cannot merge.

The combined screen limits at `workflow.py:449–458` also conflate entry count,
descriptor bytes and source bytes into one generic reason, without actual
values or participants. Collision/limit messages can therefore omit a usable
action or the contributing mods even though rejection itself is correct.

**Remediation/regression:** identify the owner and the managed-menu boundary;
give a supported disable/update action. Distinguish entry/descriptor/source
limits and record actual/maximum values plus contributing IDs. Cover named
owners, existing-set preservation and all 14 catalogs. Retain the already
fixed attribution for invalid descriptors and duplicate SDK screen owners.

## UX-08 — A Lua-only library is labeled “DLL plugin”

**Beta 10 status: implemented.** GUI fixtures distinguish a typed Lua/JSON screen
library from a library containing an actual DLL. Native review policy is
unchanged by this display correction.

**Reproduction:** discover an unselected library containing only
`cc2x/screen_extensions.json` and `cc2x/ui/helper.lua`. Actual hidden Tk showed
`Lua, DLL plugin`; the package contained zero `.dll` files.

**Cause:** `gui.py:953–957` uses `item.kind == 'native'` as a display label.
The classifier deliberately uses that safety category for every unhandled
`cc2x` path, including typed JSON/Lua data.

**Remediation/regression:** distinguish the safety classification from the
actual package capabilities shown to players. Assert a validated Lua-only
screen library does not claim to contain a DLL, while unhandled `cc2x`
resources keep their native safety checks.

## UX-09 — Inventory changes replace all existing checkbox widgets

**Beta 10 status: implemented.** Changed-inventory fixtures retain surviving
widgets, variables and selection on add/rename, plus scroll position in a hidden
list. This is source/Tk evidence, not general OS keyboard/accessibility acceptance.

**Reproduction:** keep the existing checkbox widget for A, add a new unchecked
package C, then passively rescan. Hidden Tk confirmed A's old widget was
destroyed and replaced with another widget, although A itself did not change.
Actual keyboard/OS focus acceptance was not performed; loss of focus on a
destroyed checkbox follows from the widget lifecycle.

This does **not** happen on every unchanged scan: the fingerprint shortcut at
`gui.py:763–768` returns early. The relevant rebuild is at `842–843`, with
destruction in `_display_items` at `939–947`.

**Remediation/regression:** reconcile rows by stable mod identity, or restore
equivalent keyboard focus and scroll position after an inventory change.
Verify checks, selection, notices and load-order interaction remain intact;
include an unchanged-scan control so the regression does not assert a false
every-three-seconds failure.

## UX-10 — Undo remains available without an available history record

**Beta 10 status: implemented.** The menu reflects checked history availability;
the action rechecks a stale record before confirmation or transaction. GUI
fixtures cover fresh history, consumed Undo and externally removed history.

The menu always offers Undo (`gui.py:200–202`); control refresh disables only
the whole menu during apply. A first run or consumed activation journal can
therefore offer an action whose missing file becomes a generic folder-access
error. This is a static menu/journal lifecycle finding, not a fresh Undo UI
failure reproduction.

**Remediation/regression:** track history availability separately and explain
“no previous selection” independently from actual I/O failure. Test fresh
startup, consumed Undo, ordinary available history and interrupted recovery.

## Scope beyond the ten original findings

- **Partial native Undo refusal:** an existing backend regression proves that
  resources may be restored before external-runtime rollback refuses. The
  pending journal prevents launching, but the GUI's error callback does not
  necessarily reconcile its displayed applied rows. This consequence is
  inferred from `workflow.py:767–781`, `gui.py:589–610` and
  `test_external_runtime_does_not_prevent_resource_rollback`; a new Tk recovery
  regression is required before calling the UI symptom freshly reproduced.
  Show recovery-required state and retain the unknown external loader.
- **Deferred changes and closing:** beta 10 now explicitly says ModLoader must
  remain open. The Disable-all GUI fixture defers writes while the game runs
  and cancels the requested automatic launch. A durable pending queue is a
  separate product decision: reopening restores the last applied owned set,
  while language-window recreation retains its existing in-process request.

## Disable all

The new main-window action clears mods and libraries, including required
libraries, in one ordinary empty-selection apply. It cancels the current
automatic launch request, respects running-game deferral and retains Undo.
It does not uninstall the SDK DLL, delete source packages/saves or launch an
unmodded game implicitly. `test_gui_controls_recovery.py` covers one apply,
dependent-library clearing, disabled states, deferred writes and restoration.

## Implementation coverage and remaining acceptance

The separate `codex/ux-state-recovery` follow-up implements UX-01 through UX-10
and Disable all for beta 10. The original beta 9 executable is not retroactively
changed. Contracts and acceptance boundaries are recorded in ADR-0034/0035.

The first four-finding intermediate source check had 497 passing tests and
23 environment/dependency skips; restoring bundled tools then covered 62
menu-delivery/screen cases. Those historical counts are not final beta 10
full-suite or frozen-binary results.

Current focused evidence consists of owned transaction/fault fixtures,
domain/presenter checks and hidden Tk controls. The diagnostic GUI suite covers
partial discovery and zero-plan export, selected-source failure with preserved
output, a real guard with zero mock spawns, and localized guard/OS-error exports.
The 14 offline catalogs have dedicated coverage for the added summaries and
controls. Record final aggregate checks and release-artifact verification
separately once performed.

No live-game action or new UI handoff was performed for this follow-up. The user
will perform real-game acceptance. Source closure of these ten findings does
not certify clean-machine behavior, general platform accessibility, full native
rollback dialog acceptance, gameplay, multiplayer or a packaged macOS app.

Final local beta 10 source validation: **603 passed, 10 skipped**. The skips
were unavailable Windows symlink operations, the optional full Lua interpreter
and the build-only bundle test. Ruff, formatting and strict mypy passed.
All 49 raw application/schema/profile/runtime/tool-manifest inputs embedded in
the frozen candidate matched this source tree exactly. Frozen GUI/tool and
public-download verification are recorded in the release evidence separately.
