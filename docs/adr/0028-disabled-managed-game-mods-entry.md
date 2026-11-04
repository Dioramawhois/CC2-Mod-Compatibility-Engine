# ADR-0028: disable the in-game Mods entry while ModLoader controls the set

Status: accepted following the owner's correction, 2026-11-04. Supersedes
ADR-0025's reachable read-only mod-list behavior. Direct launch, refresh,
reversible activation and native/source safety rules remain in effect.

Delivery superseded by [ADR-0030](0030-sdk-screen-extension-delivery.md): the
real main menu clears ordinary mod overlays, so the generated resource alone
does not apply this policy there. The requested UI behavior below is retained.

## Problem

The earlier decorator disabled mod-list rows only after the player opened Mods.
The main-menu entry remained clickable, which did not match the requested gray,
disabled entry while ModLoader controls the active generated set.

## Decision

Keep the existing owned decorator in the generated
`content/scripts/screen_menu_main.lua`, after the ordinary resource merge.
Wrap `ui:list_item` only for the main menu's localized `upp_mods` label, passing
`false` as the third argument, which is the enabled flag. Preserve the label,
icon, remaining arguments and unrelated list items. Suppress activation even
if a synthetic or stale UI reports a click for the disabled entry.

Reject `nav_set_screen(g_screens.mods)` and return stale Mods-screen state to
the main menu before updating. Clear stale mod selection/confirmation state
and retain the menu VM's defense against enabling mods. Other menus and gameplay
remain available. The Workshop uploader behind Mods is inaccessible while this
set is active; this deliberately supersedes ADR-0025's promise of uploader access.

The decorator changes only the generated merged resource. Vanilla, Workshop,
SDK, author mods and the game executable remain untouched. Do not run user mod
Lua or DLLs in development checks. Require final Lua syntax validation, retain
the complete source bytes, and never replace a rejected menu merge with stock.
An installation without readable menu resources cannot claim the guard.

Undo or unloading the generated set restores the ordinary menu. An empty
selection adds no decorator. The existing closed-game transaction and deferral
apply; the guard is a UI behavior, not an OS or networking permission boundary.
The game's localized label and ModLoader's 14 offline catalogs remain intact.

## Contract and validation

New `managed_menu` provenance uses policy `locked-mods-menu-v2` and retains its
logical path, input SHA-256, adapter SHA-256 and final output SHA-256. The final
file is covered by the normal package inventory and rollback. Package schema
v2 accepts both this policy and historical `read-only-mod-list-v1` manifests.

Owned synthetic Lua fixtures cover the third enabled argument, localized label,
forced-click suppression, direct navigation, stale Mods state, unrelated menus,
callback arguments and recreated UI objects. Workflow/schema fixtures cover
syntax, hashes, policy compatibility and no-guard empty selection. They execute
owned fixtures only and do not establish fresh visual or gameplay acceptance.

No fresh in-game visual acceptance accompanies this correction. Existing beta 4
GUI screenshots and historical game captures retain their original scope and
provenance; none is relabeled as a beta 5 game-menu capture. Multiplayer,
dedicated-server, clean-machine and packaged macOS gates remain separate.
