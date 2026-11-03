# CC2 ModLoader

Choose the Carrier Command 2 mods you want to play. ModLoader combines their
files into one local mod, merges changes where possible, and starts the game
with that build selected.

**Windows x64 beta · 0.4.0 beta 4**

[**Download CC2ModLoader.exe — latest Windows beta**](https://github.com/Dioramawhois/CC2-ModLoader/releases/download/latest-beta/CC2ModLoader.exe)

[Complete download package](https://github.com/Dioramawhois/CC2-ModLoader/releases/tag/v0.4.0b4)
· [Build from source](docs/BUILDING.md) · [Detailed help](docs/INSTALLATION.md)

## Start here

1. Download **CC2ModLoader.exe** using the link above.
2. In Steam, right-click **Carrier Command 2 → Manage → Browse local files**.
   Put the downloaded EXE beside **carrier_command.exe**.
3. Close the game, then open **CC2ModLoader.exe**.
4. Tick the mods you want. Wait for **Ready** and read any warning.
5. Click **Launch game**. Your combined mod is already enabled.

Your game folder should look like this:

```text
Carrier Command 2/
  carrier_command.exe
  CC2ModLoader.exe
```

### 1. Choose your mods

Ticking a box checks, combines and applies that selection automatically.
Unticking a box rebuilds the result without that mod.

![Choose mods with checkboxes, wait for Ready, then select Launch game.](docs/images/01-choose-mods.png)

*Example workspace: two Workshop mods selected; two local demonstration mods left off.*

### 2. Put patches in the right order

Open **Load order** and drag a mod, or use **Alt+Up / Alt+Down**.
Changing the order rebuilds the combined files automatically.

By default, patches lower in the list take priority where changes overlap.
For example, put a compatibility patch after the mods it is meant to change.

![The Load order tab lists the selected SDK, AI Bridge and Island Airfields.](docs/images/02-load-order.png)

### 3. Manage shared libraries

Some mods use a shared library such as **CC2X SDK**. The **Libraries** tab lists
these packages. Declared dependencies are included automatically when available;
you can also select a library here. The SDK supplies tools for mods; gameplay
features come from the separate mods you choose.

![The Libraries tab shows the selected CC2X shared runtime.](docs/images/03-libraries.png)

### 4. Read warnings before launching

Two mods can edit the same file without changing the same parts. ModLoader tries
to keep those edits together. If a later patch replaces another mod's changes,
an orange warning names the mods and the file.

**Ready means the files are prepared. It does not guarantee that the mods work
together in the game.** Review **Menu → Problem details…**, change the order or
untick a mod if needed. **Menu → Later patches take priority** controls this policy.

![An orange warning identifies the two example patches with overlapping changes.](docs/images/04-overlap-warning.png)

*Conflict demonstration: the two “Example:” patches deliberately overlap.*

## Everyday use

- **Workshop and local mods:** subscribed Workshop items are found automatically.
  Windows custom mods are also read from `%APPDATA%\Carrier Command 2\mods` and
  the game's `mods` folder. New discoveries appear unchecked.
- **Mod updates:** selected mods are checked again when you open ModLoader and
  while it stays open. Changes wait until the game is closed before applying.
- **One result:** ModLoader maintains one generated `mods/CC2-MCE` package.
  Source mod files stay in place. The previous applied set is kept if a change
  is rejected; **Menu → Restore previous selection…** offers the recorded undo.
- **Your language:** the UI follows the system language. Choose another in
  **Menu → Language**; 14 offline languages are included.

## Before you start

This is a **Windows beta**. Some mod combinations are incompatible. Native
SDK/plugins require supported game/runtime versions; multiplayer, dedicated
servers and a packaged macOS app are not certified by this release.
[Compatibility and test scope](docs/COMPATIBILITY.md) explains the limits.

The screenshots show the actual application in an isolated demonstration
workspace, not gameplay acceptance. [Screenshot details](docs/SCREENSHOTS.md).

## Help, source and license

- [Installation, local folders, updates and undo](docs/INSTALLATION.md)
- [Build the same graphical app from source](docs/BUILDING.md)
- [Report a bug](https://github.com/Dioramawhois/CC2-ModLoader/issues): include
  your app/game versions, selected mods, load order and an exported GUI report.
- [Contribute](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

Open source under [GPL-3.0-or-later](LICENSE). Keep the complete package's
[component notices](NOTICE.md) and corresponding source materials when redistributing.
