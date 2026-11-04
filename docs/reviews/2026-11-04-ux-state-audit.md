# ModLoader UX and state audit — 2026-11-04

Scope: the staged **0.4.0 beta 9** sources at
`dabb60e649245e0f54e41a5f80b717c390ea8960`. This is a read-only engineering
audit after packaging, covering selection truthfulness, recovery, dependency
messages, discovery, runtime errors and the 14 offline languages. It does not
certify publication status, game-menu behavior, gameplay or multiplayer.

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

These fixes do not close the remaining findings below.

## Priorities

| ID | Priority | Remaining issue | Evidence |
| --- | --- | --- | --- |
| UX-01 | P1 | A committed update can be displayed as rejected after cache cleanup fails | Hidden Tk + real owned transaction + mock launch |
| UX-02 | P1 | Built-in SDK dependency crashes the successful-apply callback | Valid service plan + actual callback through a controlled port |
| UX-03 | P1 | External native activation silently replaces saved merge order | Hidden Tk + real owned transactions |
| UX-04 | P1 | A broken discovered package hides the list and produces empty diagnostics | Hidden Tk + owned malformed metadata |
| UX-05 | P2 | Launch refusals discard their actionable cause | Static GUI/guard control flow |
| UX-06 | P2 | Undo leaves dependency explanations from the discarded set | Hidden Tk + real owned Undo |
| UX-07 | P2 | Some screen-extension refusals remain technical or unattributed | Presenter reproduction + workflow review |
| UX-08 | P2 | Lua-only screen libraries are labeled as DLL plugins | Hidden Tk + owned Lua/JSON library |
| UX-09 | P2 | Changed inventory destroys existing checkbox widgets | Hidden Tk widget lifecycle; focus consequence inferred |
| UX-10 | P2 | Undo is offered without an available history record | Static menu/journal lifecycle |

P1 means an ordinary state boundary can misrepresent the applied set, change
patch priority unexpectedly, or prevent a usable recovery/support workflow.
P2 means the safety boundary remains effective but feedback or control state
is misleading. These priorities are engineering follow-up, not a claim that
every user encounters every trigger.

## UX-01 — A housekeeping failure reverses the displayed result after commit

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

The menu always offers Undo (`gui.py:200–202`); control refresh disables only
the whole menu during apply. A first run or consumed activation journal can
therefore offer an action whose missing file becomes a generic folder-access
error. This is a static menu/journal lifecycle finding, not a fresh Undo UI
failure reproduction.

**Remediation/regression:** track history availability separately and explain
“no previous selection” independently from actual I/O failure. Test fresh
startup, consumed Undo, ordinary available history and interrupted recovery.

## Recovery and wording checks requiring follow-up evidence

- **Partial native Undo refusal:** an existing backend regression proves that
  resources may be restored before external-runtime rollback refuses. The
  pending journal prevents launching, but the GUI's error callback does not
  necessarily reconcile its displayed applied rows. This consequence is
  inferred from `workflow.py:767–781`, `gui.py:589–610` and
  `test_external_runtime_does_not_prevent_resource_rollback`; a new Tk recovery
  regression is required before calling the UI symptom freshly reproduced.
  Show recovery-required state and retain the unknown external loader.
- **Deferred changes and closing:** the wait text says changes apply after
  the game closes, but should say ModLoader must remain open. This is a P3
  expectation gap, **not** a proven pending-selection persistence defect.
  ADR-0025 restores the last applied selection on reopening; ADR-0012's pending
  preservation is specific to language-window recreation. A durable pending
  queue would be a separate product decision.

## Proposed follow-up sequence

1. Fix and regress the state-truthfulness boundaries first: post-commit
   housekeeping, built-in dependency success, and saved merge-order recovery.
2. Make every discovery/launch/recovery refusal identify the real cause and
   retain an exportable diagnostic; close the 14-language dynamic-error gap.
3. Reconcile restored dependency labels, screen-limit/ownership messages,
   library labels, changed-inventory focus and Undo availability.

Keep these changes in a separate reviewed UX PR. The audit itself changes no
application behavior. The user will perform game acceptance; synthetic GUI,
fault-injection and source-archive checks do not replace that acceptance.

## Isolated source follow-up

The separate `codex/ux-state-recovery` branch implements UX-01, UX-02, UX-03
and UX-06. The staged/published beta 9 binary does not include this follow-up;
the installed EXE remains available for the user's independent test.

Seven new regressions cover post-commit cache cleanup, real pre-commit failure,
unknown loader preservation, runtime-provided dependencies, owned merge order,
first adoption of native order and historical dependency notes after Undo.
The complete source suite passed with 497 tests and 23 environment/dependency
skips. After restoring the pinned bundled tools, all 62 menu-delivery and
screen-extension cases passed, including the 14 previously skipped validator
checks. Ruff, formatting and strict mypy passed. No new binary, game or
multiplayer acceptance is claimed for this branch.

The other six findings and the explicitly labeled recovery/wording follow-ups
remain open; this report does not present the UX audit as a completed redesign.
