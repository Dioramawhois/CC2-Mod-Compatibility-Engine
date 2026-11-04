# ADR-0029: identify the managed set on the game's main menu

Status: accepted following the owner's request, 2026-11-04. Extends ADR-0028's
disabled Mods entry and navigation guard. Direct launch, refresh, reversible
activation and native/source safety rules remain in effect.

Delivery superseded by [ADR-0030](0030-sdk-screen-extension-delivery.md): the
real main menu clears ordinary mod overlays, so the generated resource alone
does not display this label there. The requested UI behavior below is retained.

## Problem

The disabled Mods entry does not itself tell the player that CC2 ModLoader
manages the active set. The game main menu needs a visible indication of its
controller and selected mods.

## Decision

Extend the owned decorator appended to the successfully merged
`content/scripts/screen_menu_main.lua`. On the main menu, before its first
ordinary header, render a noninteractive **CC2 ModLoader** header followed by a
compact line of selected source names in the recorded merge order. Render this
pair once per frame, including when the UI object is recreated. Other screens
retain their ordinary headers and callbacks.

Treat names as untrusted text. Normalize control characters to spaces, bound
the compact line to at most 140 Unicode characters, and safely escape the
result as a Lua string literal. Quotes, backslashes and non-ASCII names must not
alter the generated script. Only the product brand and author-provided names
appear in this label, so no language-catalog additions are needed. Preserve
the game's localized Mods label and all 14 offline application catalogs.

Retain ADR-0028's gray, disabled Mods entry, forced-click suppression, rejected
Mods navigation and stale-state cleanup. Its Workshop uploader stays unavailable
through that entry. The label is informational; changing the set remains a
ModLoader action with the game closed. Other menus and gameplay retain their
existing behavior.

The decorator changes only the generated merged resource. Do not edit vanilla,
Workshop, SDK, author files or the game executable, and do not invent a stock
replacement when merging fails or menu resources are unreadable. Require final
Lua syntax validation and retain the complete merged input bytes. Development
utilities execute only owned synthetic fixtures, never user mod Lua or DLLs.

Undo restores the recorded prior package and its menu behavior, which can
include an earlier menu decorator. Unloading the generated set removes that
set's menu changes. An empty selection adds no decorator or label. Existing
closed-game deferral, transactional activation, rollback and integrity checks
continue to apply.

## Contract and validation

New schema-v2 `managed_menu` provenance uses `modloader-main-menu-v3`. The
optional object's logical path, input SHA-256, adapter SHA-256 and final output
SHA-256 retain their existing structure. The schema accepts this policy plus
historical `read-only-mod-list-v1` and `locked-mods-menu-v2` packages. The normal
package inventory covers the final decorated resource.

Owned fixtures cover placement before the first main-menu header, one label
per frame, recreated UI objects, unrelated screens, noninteractive behavior,
source order, long Unicode names, control characters, quotes and backslashes.
Keep the Mods entry/navigation regressions. Workflow/schema checks cover real
Lua syntax validation, hashes, all three policies, empty selection and restoration
of prior package behavior.

These offline checks do not establish fresh game visual or gameplay acceptance.
The existing beta 4 GUI screenshots retain their original provenance and scope;
none is relabeled as a beta 6 game-menu capture. Multiplayer, dedicated-server,
clean-machine and packaged macOS gates remain separate.
