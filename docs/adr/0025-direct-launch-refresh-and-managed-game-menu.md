# ADR-0025: direct game launch, startup rebuild and managed in-game selection

Status: accepted by the owner on 2026-11-03; supersedes the Steam-launch choice
in ADR-0016. The stable output, reversible activation and native review rules
from ADR-0009/0010 remain in effect.

## Owner request

Start the game's executable instead of opening a Steam URL. Rebuild selected
mods after updates and on each ModLoader startup. The game should start with
only the generated build active and show its own mod list as read-only.

## Implementation

The launcher uses the discovered local executable as an argument vector with
`shell=False` and the installation as its working directory. There is no Steam
URL, browser or shell fallback. Before spawning it checks the closed-game gate,
the executable path, the active folder list and the owned package's complete
inventory. The game/runtime hashes must still match the applied build.

Every initial scan reanalyzes and applies the saved selection, even when source
fingerprints are unchanged. New and changed files in selected mods are read
again; removing a file removes it from the replaced output. Periodic scans keep
the existing three-second update detection. Newly discovered mods are listed
but require a checkbox; they are not silently enabled. Identical results may
reuse the verified output without replacing the user's Undo history.

The last successful owned activation journal and verified package recover the
chosen set if the game changed `mods.xml`. Startup rebuild restores that set,
not every independently enabled mod. Launch after an external activation change
queues a rebuild first. The ordinary activation transaction clears all other
active folders and enables exactly the generated package. An empty selection
still disables all mods, as specified in ADR-0010.

When a selected set has a readable `scripts/screen_menu_main.lua`, its normal
resource merge runs first. An owned callback decorator is then appended and
the final Lua is syntax-validated. It disables row interaction and Disable All,
clears stale selection/confirmation state, and suppresses mod-enable calls in
that menu VM. The ordinary UI renders inactive gray rows while retaining the
actual enabled states and scrolling. Other screens and Workshop upload remain
usable. The list identifies CC2 ModLoader as its controller.

The decorator lives only in the generated package. It does not modify vanilla,
Workshop subscriptions, other authors' files or the SDK DLL. Removing/undoing
the generated package removes its menu behavior. It is a UI guard, not a
network protocol or an OS permission boundary. No synthetic vanilla menu is
invented for installations without readable menu resources; those builds do
not claim the menu guard. A rejected menu merge is never replaced with stock.

## Contract and verification

Package schema v2 adds optional `managed_menu` provenance: policy, logical
path, input hash, adapter hash and final output hash. The ordinary file inventory
contains the decorated result, so integrity, rollback and reproduction apply
to it as to every other output. Existing manifests remain valid.

Regression coverage includes direct spawning without Steam, activation/payload/
game changes rejected before spawning, forced startup analysis, Workshop file
addition/removal/update, remembered selection after external changes, syntax
validation and rollback. The owned Lua fixture executes the adapter against a
synthetic UI to check gray/read-only rows, real enabled flags, stale dialogs,
Disable All and unrelated screens. This does not execute user mod scripts.

Frozen Windows checks and real-menu observations are recorded separately from
fixtures. No multiplayer, dedicated-server or macOS runtime acceptance is
implied by the Windows work.
