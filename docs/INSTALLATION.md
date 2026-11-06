# Install and use CC2 ModLoader

This guide covers the ready-to-use Windows application. If you want to compile
the application yourself, follow [Building from source](BUILDING.md), then
return here. Both routes produce the same graphical application.

## Requirements

- A 64-bit Windows PC and a legitimate Steam installation of Carrier Command 2.
- The game and the mods you want to use must already be downloaded.
- Write access to the selected game folder and your Carrier Command 2 user-data
  folder. The app does not require you to run a terminal or edit configuration.
- Close the game before changing the active mod set.

Native SDK/plugin support is limited to explicitly reviewed game and DLL
versions. Data-file merging and native-code compatibility are separate checks.
A packaged macOS application and native macOS SDK support are not certified by
this Windows release. See [compatibility and verification](COMPATIBILITY.md).

## 1. Download the application

Download [**CC2ModLoader.exe — latest Windows beta**](https://github.com/Dioramawhois/CC2-ModLoader/releases/download/latest-beta/CC2ModLoader.exe)
directly. This permanent link is updated when a newer beta is published.

Alternatively, open the [0.4.0 beta 11 release](https://github.com/Dioramawhois/CC2-ModLoader/releases/tag/v0.4.0b11)
and download **CC2ModLoader-0.4.0b11-windows-x64.zip** for the complete package with
its README, notices and metadata.

Choose the EXE or Windows ZIP for this route. GitHub's automatic **Source code** links
and the separate `-source.zip` are for developers; they are not the application.

If you downloaded the ZIP, extract it with Windows Explorer. Keep its README, license notices and
release metadata with your downloaded copy. The executable includes its Python
runtime, GUI, Git merge tool, Lua syntax checker and the reviewed SDK dependency;
you do not install Python, Git or Lua to use this build.

## 2. Put the executable beside the game

In Steam, right-click **Carrier Command 2**, then select **Manage > Browse local
files**. Copy **CC2ModLoader.exe** into the folder containing
**carrier_command.exe**:

```text
Carrier Command 2/
  carrier_command.exe
  CC2ModLoader.exe
```

The Steam library may be on any drive. Use Steam's Browse local files action
rather than assuming a particular `C:` path.

Open **CC2ModLoader.exe**. The Windows portable application expects to be beside
the game. If it reports the wrong location, move the executable to the correct
game folder and reopen it. For multiple detected installations, choose the
intended game in the application.

On first use, ModLoader prepares its local `mods` and `libraries` input folders
inside the selected game folder. Existing files and unsafe folder links are not
silently replaced.

## 3. Find your mods and libraries

Subscribed Workshop packages are discovered in the Steam libraries. ModLoader
reads them in place; you do not copy subscribed mods into a second folder.
Finish Steam downloads before selecting the packages.

On Windows, custom mods in the game's standard user-data folder are discovered
automatically:

```text
%APPDATA%\Carrier Command 2\mods\my-mod\
  mod.xml
  content\
    ...
```

Paste `%APPDATA%\Carrier Command 2\mods` into Windows Explorer's address bar to
open it. Keep each mod in its own folder with the layout above. No manual folder
selection is needed for this location. The next scan also detects it if you
create the `mods` folder after opening ModLoader. New mods appear unchecked;
select the ones you want to include.

On macOS the equivalent scanned user location is
`~/Library/Application Support/Carrier Command 2/mods`. This discovery support
does not certify a packaged macOS app or native SDK integration.

Game-folder packages remain supported with this layout:

```text
Carrier Command 2/
  mods/
    my-mod/
      mod.xml
      content/
        ...
  libraries/
    my-library/
      mod.xml
      content/
        ...
```

Use **Menu > Add mod folder...** to include another folder containing local
packages. **Menu > Refresh list** rescans the configured locations.

The **Mods** and **Libraries** tabs distinguish ordinary mods from packages with
a valid library declaration. A folder name alone does not turn a mod into a
library. Declared dependencies are included automatically when they can be
resolved.

The app includes the reviewed CC2X SDK **0.8.1-client-beta.1** runtime for its
supported native profile. A known older installed runtime can be upgraded
through the same automatic apply transaction, with backup and Undo. An older
reviewed SDK source package does not downgrade the chosen runtime. An unknown
installed loader is preserved and blocks activation.

If Steam updates an SDK package beyond the versions your loader supports,
update ModLoader before changing the selected set. The diagnostic names the
unsupported source library; it does not mean the installed game-folder loader
is unknown. Merely removing a gameplay mod still rebuilds and checks the
remaining libraries, so a pending SDK mismatch can affect that action too.

If Workshop and local versions of the same package are listed, select the
version you want. Switching the checkbox replaces the selected version; it does
not enable two versions together or overwrite the Workshop download.

## 4. Select mods and wait for the result

Select or clear the checkboxes. Each checkbox change authorizes the app to
validate, merge and activate that selection automatically. There is no separate
Check or Apply button.

Wait for **Ready** before selecting **Launch game**. If the game is running,
ModLoader waits for it to close before applying the pending change.

ModLoader maintains one generated local mod. Its name in the game includes
**CC2 ModLoader** and the selected mod names. The generated files are rebuilt as
a complete set, so files from removed mods are not left in the result.

**Disable all** clears both the mods and libraries, including automatically
required libraries, and applies the empty selection once. Keep ModLoader open
if it is waiting for the game to close. The action cancels a pending automatic
launch and does not delete downloaded packages, saves or the SDK DLL.
**Menu > Restore previous selection...** returns to the recorded previous set;
that command is unavailable when no usable history exists.

An unreadable package does not hide the valid mod list. The notice identifies
its folder; **Menu > Problem details...** and **Save report...** retain the exact
cause. A quarantined mod or unavailable dependency cannot enter a new build.
After repairing the package, refresh the list; its obsolete discovery notice
clears. Specific launch refusals remain visible until a successful check or
restoration establishes a usable set again.

The generated game mod is stored under your Carrier Command 2 user-data folder:

```text
Carrier Command 2 user data/
  mods/CC2-MCE/
    mod.xml
    content/...
    ...release and source metadata...
  cc2-mce/
    ...preferences, recovery and backup data...
```

On Windows this user-data folder is normally inside `%APPDATA%`. It is separate
from the game's installation folder. **Menu > File locations...** shows the
paths used by your installation; no manual configuration editing is needed.

## 5. Arrange patches and understand warnings

Each time you open ModLoader, it checks the saved selection and rebuilds it
from the currently installed mod files. Updates to selected Workshop mods are
included; newly discovered mods still need a checkbox. While ModLoader remains
open it also checks for changed sources periodically. If the game is running,
changes wait for it to close.

**Launch** starts `carrier_command.exe` directly from the selected installation.
Only the generated build is enabled. Use ModLoader to change your selection
with the game closed, then restart the game.

The loader uses its matching reviewed SDK to load a menu extension. The main menu
shows a **CC2 ModLoader** heading and compact selected-mod names; its **Mods**
entry is gray and disabled. Other menus retain their ordinary navigation.
The policy belongs to the generated package. An empty selection adds no
extension; removing it restores the ordinary menu on the next start.
See [beta 7 exact-build menu verification](verification/main-menu-v4.md) for that
binary's acceptance status and limits. Beta 9 changes the pinned runtime;
these historical checks do not establish fresh acceptance of that binary pair.

Beta 6's generated menu-file change did not reach the initial menu because the
game clears ordinary resource overlays there. Beta 7 uses the SDK boundary
described in [ADR-0030](adr/0030-sdk-screen-extension-delivery.md).

Open **Load order** to change the merge order. Drag a selected package, or use
**Alt+Up** and **Alt+Down**. Each change rebuilds the result automatically and
the order is remembered.

By default, **Menu > Later patches take priority** is enabled:

- Independent text changes are combined using Git three-way merging.
- When text changes overlap, the later patch has priority for the conflicting
  portions; unrelated earlier changes are retained where the merge permits it.
- If the original data file is unavailable, the app reports a whole-file
  replacement instead of pretending it performed a three-way merge.
- Supported binary-resource collisions use an explicit whole-file replacement,
  not a binary merge. DLLs are never merged.

An override warning identifies the affected files and mods. It means that some
changes have been replaced and the in-game result is unknown. Review **Menu >
Problem details...**, adjust the order or remove a conflicting package.

Disable **Later patches take priority** if you want strict conflict rejection.
Syntax errors, unsafe paths, unknown native plugins and unsupported game/runtime
combinations remain blockers in either mode.

A rejected change restores the previous working checkboxes and order. The
intact applied set can still be launched when no interrupted transaction needs
recovery. A clean merge proves file-level validation, not that every gameplay
feature of every mod combination works together.

## 6. Launch, language and automatic startup

Select **Launch game** after the selection is ready. The app starts the local
`carrier_command.exe` directly with the prepared set enabled.

The interface follows the system language by default. Use **Menu > Language**
to choose English or another included language; the choice is saved. The 14
catalogs are included locally, and mod names or file contents are not sent to
translation services.

For subsequent starts, **Menu > Launch game when opening ModLoader** prepares
the selected set and starts the game after a successful result. An unsuccessful
change cancels that automatic launch. Leave the option disabled if you prefer
to review the application before launching.

## Update, undo and remove

To update the application, close the game and ModLoader, retain a copy of the
previous executable, and replace `CC2ModLoader.exe` with the executable from the
new Windows release. Do not copy the developer source archive into the game.

To undo the last applied change, close the game and choose **Menu > Restore
previous selection...**. The app restores its recorded previous package and
activation state, including that build's menu behavior. A supported SDK
installation or upgrade participates in the recorded rollback; externally
changed files are preserved for review.

To disable all selected mods, clear their checkboxes and wait for completion.
To remove the application afterwards, close it and remove its executable.
Deleting the executable alone does not undo an active generated package. Keep
the application's recovery/backup data until you have restored or disabled the
set you no longer want.

## Large mods and resource limits

Beta 8 fixes `Input byte limit exceeded` during startup for resources above the
old 16 MiB limit or installed collections above the old 256 MiB limit. Update
the loader using the current EXE link above; you do not need to delete your
Workshop subscriptions or move your mods to work around those old limits.

The loader now hashes installed resources incrementally instead of keeping all
unchecked mod contents in memory. It keeps these bounded resource limits:

| Scope | Limit |
| --- | --- |
| One resource file for discovery or supported binary copying | 512 MiB |
| One text input processed for merging/validation | 16 MiB |
| Resource input scanned across installed packages | 16 GiB |
| Selected source input for one build, including package metadata | 1 GiB |
| Generated resource output | 1 GiB |

Metadata and configuration have separate, smaller bounds. Large binary-copy
capacity does not apply to text merging or Lua/XML/JSON processing. A large
text resource can appear in the list and still exceed the text-processing
limit when selected. A resource-limit message names the affected relative file
and shows its actual size and limit.
For a selected-set limit, reduce the selected set. If a single resource or the
installed collection exceeds the supported bounds, report the named resource,
size and loader version so the case can be reviewed. Keep the original files;
renaming an extension or editing a size declaration does not change support.

These limits concern file processing, not gameplay compatibility or native
plugin approval. A rejected build preserves the previously applied set.

## Troubleshooting

| Message or symptom | Action |
| --- | --- |
| Game not found or portable placement requested | Put the executable beside the intended `carrier_command.exe`; use **Menu > Choose game folder...** where available. |
| A subscribed mod is missing | Finish Steam downloads, check the selected game, then refresh the list. |
| `Input byte limit exceeded` immediately after opening an older loader | Update to beta 8 or later. The old scanner limited all installed mods to 256 MiB and each file to 16 MiB, including unchecked mods. |
| A file or aggregate resource limit is exceeded in beta 8 or later | Read the named file, actual size and limit. Reduce a selected set if its build exceeds 1 GiB; otherwise include those details in a bug report. See [resource limits](#large-mods-and-resource-limits). |
| A local package is missing | Check its `mod.xml` and `content` layout, or add its parent folder through the menu. |
| A library cannot be unchecked | A selected mod may require it. Disable the dependent mod first. |
| Unknown or incompatible DLL | Use a supported release of the mod/SDK; do not rename a DLL to bypass review. |
| A downloaded SDK library contains an unsupported runtime | Update ModLoader to the release supporting that SDK package. Beta 9 supports the reviewed 0.8.1 runtime. The message identifies the source library; the installed loader can still be correct. |
| An existing `dinput8.dll` blocks activation | Identify the installed loader. Preserve it and check compatibility instead of overwriting it blindly. |
| Update is waiting | Close the game and allow the pending change or recovery to finish. |
| A change is rejected | Read the named mod/file in the result and open problem details; the previous set is retained. |
| The game's Mods entry is gray | The active set is managed by ModLoader. Close the game to change it in the loader. |
| The game's Mods entry is still clickable | Check that you are using beta 7 or later and its matching reviewed SDK. Beta 6 had this defect. Include app/runtime versions and your exported report when reporting it. |
| Files were changed outside the app | Preserve the files and recovery data; report the issue before deleting or replacing them. |

For a bug report, include the application and game versions, selected mod names,
load order, exact reproduction steps and an exported report from **Menu > Save
report...**. Review the report before sharing it. Do not attach game files,
personal saves or private paths unless specifically needed and appropriate.
