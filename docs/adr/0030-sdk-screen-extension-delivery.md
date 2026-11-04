# ADR-0030: deliver managed-menu policy through SDK screen extensions

Status: accepted for beta 7, 2026-11-04. Supersedes the delivery
mechanism in ADR-0028/0029 while preserving their requested menu behavior.
The final Windows EXE/runtime pair passed the managed-menu click, Enter and
New Game checks. The SDK-only control retained the ordinary Mods menu with no
ModLoader heading. Exact identities, captures and acceptance scope are in
[menu verification](../verification/main-menu-v4.md).

## Problem

Beta 5/6 appended a Lua decorator to the generated
`content/scripts/screen_menu_main.lua`. The real game's main-menu world clears
ordinary mod-resource overlays before loading its screens. Enabling the
generated package in `mods.xml` therefore does not establish that its menu
resource executes. Owned callback fixtures validated the decorator in isolation
and did not detect this integration gap. The owner confirmed that Mods remains
clickable in beta 6.

## Decision

Use a generic, reviewed SDK screen-extension mechanism at the existing stock
screen-script loading boundary, after the screen source and before `begin()`.
Keep the SDK a framework: it loads declared extensions; the ModLoader package
supplies the menu policy. Do not add a second competing native hook, modify ROM
or the game executable, or install an unknown DLL.

The generated package contains this UTF-8 manifest:

`content/cc2x/screen_extensions.json`

```json
{
  "schema": 1,
  "extensions": [
    {
      "screen": "scripts/screen_menu_main.lua",
      "source": "cc2x/ui/modloader_menu.lua"
    }
  ]
}
```

`source` is relative to the same package's `content` directory. It identifies
the owned Lua extension, not an alternative copy of the game's menu source.
Screen matching is exact. The SDK must validate the declaration and paths,
load only extensions from active packages, preserve declaration order and fail
closed on malformed or unsupported declarations. Unloading the package removes
its extension on the next game start.

For nonempty selections, ModLoader stages the owned extension and declaration,
validates Lua syntax, and records their bytes in package integrity/provenance.
New `managed_menu.policy` is `sdk-screen-extension-v4`; historical policies
remain readable. The input/adapter hashes identify the owned policy bytes;
`output_sha256` identifies the generated extension. `source_path`,
`descriptor_path` and `descriptor_sha256` identify its SDK delivery files.
No stock baseline is invented for this owned code. Emit this policy only for
profiles whose exact reviewed runtime declares `screen-extensions-v1`; require
that runtime even for a data-only mod selection. Other profiles may still merge
data, but do not claim this menu integration. Ordinary resource merges retain their existing validation and
conflict rules. Source and Workshop files stay read-only. An empty selection
adds no extension. Transactional activation, closed-game deferral and Undo
remain mandatory.

The UI behavior remains the ADR-0028/0029 contract: a gray, disabled localized
Mods entry; blocked direct navigation and stale-state cleanup; a noninteractive
CC2 ModLoader heading and bounded, safely escaped selected-mod names. Other
screens retain their normal behavior. The app's 14 offline languages remain.

## Validation and release boundary

Retain the owned Lua behavior fixtures. Add package tests for declaration/source
paths, syntax, inventory hashes, policy compatibility, empty selection and Undo.
SDK tests must cover exact screen matching, bounded/path-safe declarations,
active-package scope, execution order and cleanup without executing user mods
in development utilities.

Before claiming the feature works, launch the exact candidate executable and
reviewed runtime with a generated package, record that the extension was loaded
for the real main-menu screen, confirm the visible heading, and attempt to open
Mods using the game UI. Also verify an ordinary menu and a launch without the
managed extension. Unit tests or a file present in the output alone are not
game acceptance. Multiplayer, dedicated-server, macOS runtime and clean-machine
gates remain separate.
