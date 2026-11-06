# ADR-0034: report committed activation and reconstruct owned GUI state

Status: accepted for the unreleased follow-up, 2026-11-04. Clarifies ADR-0010,
ADR-0011, ADR-0012 and ADR-0025 following the
[beta 9 state audit](../reviews/2026-11-04-ux-state-audit.md).

## Problem

The GUI must distinguish a rejected request from an already committed update.
Removing an owned settings-cache link happens after activation commits. An
`OSError` at that point previously reached the failure callback even though the
new package, settings, runtime and active paths were already installed.

A dependency supplied by the reviewed bundled SDK also need not have a selected
`ModRef` or library row. Treating every dependency identity as a selected package
could interrupt the GUI callback after a successful apply.

Reopening must retain the verified owned merge order if the game changes its
native active-path order. Undo must reconstruct dependency notes for the
restored package, whose recorded metadata can differ from current Workshop
sources.

## Decision

### Committed activation remains successful

Keep the existing transaction boundary: publish the owned package and activation
journal, install checked settings/runtime, recheck inputs, publish `mods.xml`,
and remove the pending recovery journal. Errors before that boundary retain the
existing rollback and refusal behavior.

After the boundary, an `OSError` from
`sdk_settings.cleanup(..., remove_targets=False)` does not turn the committed
apply into a rejection. The inaccessible owned cache link may remain; its
installed settings target remains intact. Return the committed package so the
GUI reflects the applied selection. Existing checked pruning of obsolete owned
packages remains optional housekeeping.

This narrow handling does not cover settings installation, runtime installation,
activation writes, source-integrity checks or native rollback. Unknown installed
loaders remain blocked and preserved. Recovery failures still retain the pending
journal when required; this change does not declare those transactions ready.

### Runtime-provided dependencies are not selectable packages

Build dependency-row notes from recorded applied source metadata. Resolve notes
only to real selected source IDs or package IDs. A dependency supplied by the
reviewed runtime has no synthetic `ModRef`, checkbox or library row, so the GUI
skips a row note for that provider and completes the ordinary success callback.
Runtime approval and provenance retain their existing separate fields.

### Verified owned order takes precedence on reopening

Use this order of authority: an explicit in-process resume request; the current
order during a passive scan; the verified remembered owned package order; then
the imported native active order or saved preferences as the existing fallback.
The owned activation/package journal supplies the remembered order. Reversed
native paths must not silently reverse patch priority in a previously owned set.

When there is no remembered owned selection, first adoption still imports the
game's native active order. Source revalidation and automatic rebuild continue;
remembering order does not approve changed files or skip merge checks.

### Undo notes describe the restored package

Refresh dependency notes after both successful apply and activation discovery,
including the rescan following Undo. For an owned active package, use its
recorded `sources` and dependencies rather than changed current mod metadata.
Clear stale row notes when a former dependent is no longer applied. Native
first-adoption rows may use current discovered metadata when no owned report
exists.

## Contracts and scope

Package/report schemas, owner identities, output paths, native profiles and SDK
capabilities retain their existing contracts. The checkbox remains the apply
action; closed-game deferral, integrity checks, the reversible runtime workflow
and all 14 offline catalogs remain in effect. This follow-up does not change the
published beta 9 executable or add a release version.

The broader audit findings about launch-error presentation, unavailable Undo,
partial-recovery display and deferred-close wording remain separate work.

## Regression evidence

`tests/test_post_commit_settings_cleanup.py` injects an owned cache-unlink
permission error after commit and checks successful return, the new active set,
settings/runtime bytes, guarded launch through a mock process and subsequent
Undo. Separate fixtures retain pre-commit activation-write rollback and unknown
installed-loader refusal. Fixture DLL bytes are never executed.

`tests/test_gui_state_recovery.py` covers a bundled SDK dependency without a
library row, restored owned priority despite reversed native paths, first
adoption of native order, and Undo notes reconstructed from historical source
metadata after the current source changes. These are owned filesystem/Tk
regressions. They do not establish new frozen-binary, clean-machine, real-game,
gameplay or multiplayer acceptance.
