# ADR-0035: partial inventory, persistent diagnostics and truthful controls

Status: accepted for beta 10, 2026-11-04. Extends ADR-0010, ADR-0011,
ADR-0033 and ADR-0034. Implements the remaining six original findings in the
[UX/state audit](../reviews/2026-11-04-ux-state-audit.md), plus the requested
**Disable all** action. The ten-item source audit closure is separate from
frozen-binary and user game acceptance.

## Problem

A damaged unselected package could hide the entire inventory and leave no
useful details or export. Launch guards prevented unsafe starts but discarded
their specific cause. Some screen errors showed only paths or omitted owners
and limits. Library labels confused a safety category with actual DLL content,
changed inventories replaced checkbox widgets, and Undo was offered without
usable history. Clearing a set with required libraries also needed one explicit
GUI action rather than repeated dependency rechecking.

## Decision

### Partial inventory is explicit and never approves a failed package

The GUI calls discovery with `collect_issues=True`. Valid complete packages
remain visible alongside diagnostics for failed roots or packages. A failed
package contributes no selectable `ModRef` and no approved payload. Its source
identity, available package identity, resource, revision and cause are retained
as an issue. The default developer/core `discover()` behavior remains strict:
the same invalid input raises rather than silently returning a partial list.

Quarantine all owners of a duplicate mod ID or a cross-package case/Unicode
path collision; do not choose a winner. Preserve path containment, regular-file,
link/junction, syntax, source-hash and native review gates. Stop additional
resource reads when a shared entry/byte budget is exhausted and retain a global
limit issue. A checked unavailable source or required unavailable dependency
blocks analysis through `Scan.require_available`; it cannot disappear silently
from the requested build. A valid explicitly selected alternative version
continues through the normal dependency resolver.

Requested roots are retained for retry and snapshot comparison, including
currently inaccessible roots. Issues participate in the inventory fingerprint.
Repairing or changing a failed package can therefore trigger a new scan result.
Successful selected builds still revalidate their source snapshot and lazy
resource hashes before transactional publication. Partial inventory neither
relaxes native approval nor permits partial installation of an invalid set.

### Diagnostics exist even without a package plan

Use bounded local `Diagnostic` values for discovery, operation, restoration and
launch failures. Preserve the stage and cause, with source/resource context when
known. The main notice is localized; paths and exact technical causes belong in
the existing details view. The same menu can export a diagnostic even when no
merge plan was created. Nothing is sent automatically.

The diagnostic export has `schema_kind = "diagnostics"`, `schema_version = 1`,
`owner = "cc2-mce"`, `engine_version`, `engine_sha256`, `stage`, `installable = false`,
`diagnostic_count`, `truncated`, and `diagnostics`. Each item contains the string
fields `code`, `stage`, `cause`, `source_id`, `source_name`, `source_path`,
`resource_path`, `package_id`, and `source_revision`. Fields are bounded; at most
200 items are exported while the full issue count and truncation flag remain.
The owned [diagnostic schema](../../cc2_mce/schemas/diagnostics.schema.json)
defines this envelope. It is not an installable package or a replay plan. Existing package/report
contracts remain unchanged, including package schema 2.

Preserve specific launch-guard diagnoses for changed game/runtime, changed
activation and running/unavailable game. A refused launch starts no process,
cancels that automatic launch request and disables readiness until an explicit
refresh/revalidation. Unknown installed loaders remain untouched. Recovery
journals continue to block launch while recovery is incomplete.

### Refusal messages name the cause and a supported action

Managed-menu collisions identify their source owners and explain that the
loader owns that menu policy; offer disabling or updating the source mod. Do
not present a reserved Lua policy-file collision as an unreviewed DLL. Ordinary
same-file game-resource changes retain their normal Git merge behavior, and
unrelated unreviewed DLLs remain blocked.

Screen-extension budget refusals identify `limit_kind` (`entries`,
`descriptor_bytes` or `source_bytes`), integer `actual` and `maximum` values and
contributing source IDs in `participants`. Keep `code` and `message` strings and
schema 2. Cover individual source bounds, combined source packages and the final
descriptor/source budget including the loader's own menu. Known older reports
without these fields still get a supported action. The 14 offline catalogs
contain the corresponding summaries and controls.

### Controls reflect available data and preserve navigation

Reconcile existing mod/library rows by source ID when inventory changes.
Preserve surviving checkbox widgets, variables and scroll position; refresh
their text/state without replacing every row. An unchanged-fingerprint scan
keeps its existing early-return behavior. Required-dependency notes and owned
merge order continue to follow ADR-0034.

Label a library as containing a DLL only when it actually contains a `.dll`
resource; typed Lua/JSON screen data do not justify that label. This display
rule grants no native approval.

Enable Undo only when its owned activation record and checked backup are
available. Recheck before invoking it, distinguish absent history from a real
read/verification failure, and retain the normal confirmation for restoration.
This UI availability check does not replace transaction or rollback checks.

### Disable all applies one empty selection

The main window has **Launch game** and **Disable all**. The latter clears both
mod and library checkboxes, including required libraries, then submits one
ordinary selection change. It adds no second apply/confirmation step. Cancel
the current requested automatic launch; do not start an unmodded game as a
side effect and do not change the persistent automatic-start preference.

With the game closed, successful application activates an empty mod set through
the existing managed-folder/activation transaction. Undo can restore the prior
recorded set. While the game runs, keep the actual applied state and queue the
empty desired set; disable launch and say to close the game while leaving
ModLoader open. The button is disabled during apply and when no selection can
be cleared. Clearing a set does not implicitly uninstall or replace an SDK DLL,
delete Workshop/local source packages, or remove saves.

Pending requests are in-process state. Closing ModLoader does not promise a
durable deferred queue; a later start restores the last applied owned set.
During an atomic write, retain the existing close deferral until it completes.

## Evidence and limits

ADR-0034 covers committed outcomes, supplied runtime dependencies, owned order
and Undo labels. The remaining contracts have focused fixtures in
`test_discovery_diagnostics.py`, `test_gui_diagnostics.py`,
`test_screen_extension_refusals.py` and `test_gui_controls_recovery.py`;
existing path/native/transaction regressions
remain required. They use owned temporary inputs and syntax-only Lua checks or
mock process creation. No mod Lua/DLL or real game is run for this source work.

The audit records implementation and the level of each supporting fixture.
It does not declare a new full-suite/frozen build, clean-machine run, general
OS accessibility acceptance or gameplay/multiplayer acceptance. The user owns
the subsequent real-game test; this change adds no UI handoff or game action.
Partial native rollback remains guarded by its pending journal; a complete
recovery-dialog acceptance and durable pending-queue product design are outside
the ten original findings.
