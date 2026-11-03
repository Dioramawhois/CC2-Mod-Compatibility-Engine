CC2 ModLoader 0.4.0 beta 4 - Windows x64
======================================

INSTALL THE READY APPLICATION

1. Download CC2ModLoader.exe directly, or extract the complete Windows ZIP:
   https://github.com/Dioramawhois/CC2-ModLoader/releases/download/latest-beta/CC2ModLoader.exe
2. In Steam, right-click Carrier Command 2 > Manage > Browse local files.
3. Put CC2ModLoader.exe beside carrier_command.exe and open it.
4. Select your mods and libraries. Each checkbox change checks, merges and
   activates the selection automatically. There are no separate Check/Apply
   buttons. Wait for Ready, read any warning, then select Launch game.

You do not install Python, Git, Lua or developer tools for this route. The
executable contains the required runtime and verified merge/validation tools.
The build creates no new Workshop subscription or separate gameplay mod release.

BUILD IT YOURSELF INSTEAD

Application source is a separate asset: CC2ModLoader-0.4.0b4-source.zip.
You can also clone release tag v0.4.0b4. The complete Windows source-build guide,
prerequisites, dependency downloads and offline options are here:
https://github.com/Dioramawhois/CC2-ModLoader/blob/v0.4.0b4/docs/BUILDING.md

Both routes produce the same graphical application. The source archive itself
is not the executable. SDK and third-party tool source archives are separate
corresponding-source materials, not the ModLoader application project.

USING MODS

- Steam Workshop downloads are discovered and read in place. Let Steam finish
  downloading the selected packages first.
- Local packages belong under mods/<package>/mod.xml + content/... or
  libraries/<package>/mod.xml + content/... next to the game. These input
  folders are prepared automatically. Add other collections through the menu.
- A package with valid library metadata appears as a library. The folder name
  alone does not change its type. Declared dependencies are resolved when possible.
- Choose one version when local and Workshop editions of the same package are
  listed. Selecting another version switches the source without rewriting Steam.
- Load order is patch/merge order. Drag packages or use Alt+Up/Down to change it;
  the application rebuilds automatically and remembers the order.
- Later patches take priority is enabled by default. Overlapping text changes
  can be replaced by a later patch; independent changes are retained when the
  merge permits it. Missing-base data and supported binary collisions use a
  reported whole-file replacement. DLLs are never merged.
- An override warning means the in-game result is unknown. Read Menu > Problem
  details, adjust the order or remove a conflicting package. Disable Later
  patches take priority in the menu if you want strict conflict rejection.
- Rejected changes restore the previous working checkboxes/order. Unknown native
  code, invalid syntax and unsafe paths remain blocked in either mode.

The result is one generated local mod under the game's user-data mods/CC2-MCE
folder; its name includes CC2 ModLoader and the selected mod names. Workshop,
vanilla resources, source mods and the game executable are preserved. The app
manages its own generated output, activation and supported runtime/settings.

Close the game before changing the active set. If it is running, the app waits
and applies the pending change after it closes. Do not force-close the app
while it reports that it is finishing an update/backup.

Menu > Restore previous selection restores the recorded previous package and
activation state. Supported runtime upgrades have their own recorded recovery;
unknown or externally replaced files are preserved for review. Do not delete
recovery files to work around an error.

LANGUAGE AND STARTUP

The UI follows your system language. Menu > Language offers 14 included offline
catalogs and remembers an explicit choice. Mod names and contents are not sent
to translation services.

Menu > Launch game when opening ModLoader optionally prepares your set and
starts Steam after successful validation. A rejected change cancels that launch.

UPDATING OR REMOVING THE APP

Close the game and ModLoader before replacing the executable. Keep a backup
of your earlier executable. To stop using a generated set, first disable all
checkboxes or restore the previous selection and wait for completion. Deleting
the application executable by itself does not undo an active game package.

SUPPORT AND SOURCES

This is a Windows beta. Shared-code Windows/macOS CI does not certify a packaged
macOS application. Native support is limited to reviewed game/runtime/plugin
versions. Arbitrary gameplay compatibility, remote multiplayer, dedicated
servers, full custom flight/island landing, changed-catalog saves and clean-
machine acceptance are not certified by this release.

Documentation and issues:
https://github.com/Dioramawhois/CC2-ModLoader
Installation guide:
https://github.com/Dioramawhois/CC2-ModLoader/blob/v0.4.0b4/docs/INSTALLATION.md

When reporting a problem include app/game versions, selected mods, load order,
reproduction steps and an exported GUI report. Review reports before sharing.
Do not attach credentials, personal saves or proprietary game files publicly.

License: GPL-3.0-or-later (LICENSE). Third parties retain their own notices in
NOTICE.md and LICENSES/. The release includes provenance/SBOM/checksums;
application, SDK and third-party corresponding sources are separate assets.
