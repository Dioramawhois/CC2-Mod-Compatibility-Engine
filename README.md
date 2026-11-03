# CC2 ModLoader

Combine selected Carrier Command 2 mods into one local game mod, using a desktop
interface and real Git three-way merging. Choose mods with checkboxes, arrange
patches in **Load order**, and launch the prepared set from the same window.

**Current release: 0.4.0 beta 4 for Windows x64.**
[Download the release](https://github.com/Dioramawhois/CC2-Mod-Compatibility-Engine/releases/tag/v0.4.0b4)
| [Installation and use](docs/INSTALLATION.md)
| [Build from source](docs/BUILDING.md)
| [Documentation](docs/README.md)

A successful file merge does not guarantee that arbitrary gameplay mods work
together. The application reports overwritten changes and refuses unsupported
native code, invalid syntax and unsafe paths.

## Choose your installation route

| Route | What to download | What you need |
| --- | --- | --- |
| **1. Use the ready executable** - recommended for players | [CC2ModLoader-0.4.0b4-windows-x64.zip](https://github.com/Dioramawhois/CC2-Mod-Compatibility-Engine/releases/download/v0.4.0b4/CC2ModLoader-0.4.0b4-windows-x64.zip) | Windows x64 and an installed copy of Carrier Command 2. No Python, Git, Lua or terminal setup. |
| **2. Build the application yourself** | [CC2ModLoader-0.4.0b4-source.zip](https://github.com/Dioramawhois/CC2-Mod-Compatibility-Engine/releases/download/v0.4.0b4/CC2ModLoader-0.4.0b4-source.zip), or clone tag `v0.4.0b4` | A Windows developer environment with Python 3.12+ and Git. The build prepares its pinned dependencies. Follow the [complete build guide](docs/BUILDING.md). |

Both routes produce **CC2ModLoader.exe** and lead to the same GUI workflow.
GitHub's automatic Source code ZIP is not the ready application. Application
source, SDK source and third-party tool source are separate release assets;
choose the application source ZIP when building ModLoader.

## Quick start with the executable

1. Download and extract the Windows ZIP from the release page.
2. In Steam, right-click **Carrier Command 2 > Manage > Browse local files**.
3. Put **CC2ModLoader.exe** beside **carrier_command.exe** and open it.
4. Select your mods and libraries. The app checks, merges and activates the
   selection automatically; there are no separate Check or Apply buttons.
5. Wait for **Ready**, review any override warning, then select **Launch game**.

The game must be closed while the active set changes. If it is running, the
application waits and applies the pending selection after it closes.

For local mod layouts, Steam discovery, multiple game installations, updates,
undo and troubleshooting, read [Installation and use](docs/INSTALLATION.md).

## What ModLoader does

- Discovers Workshop subscriptions across Steam libraries and reads them in
  place, alongside custom mods in `%APPDATA%\Carrier Command 2\mods` on Windows
  and the game's local `mods` and `libraries` folders. Newly created user-mod
  folders are picked up by the next scan without manual folder selection.
- Rebuilds one fixed generated mod after checkbox or load-order changes and
  refreshes the saved selection on every startup, including Workshop updates.
- Starts the local game executable with the generated build already enabled.
  The generated menu makes the game mod list gray and read-only; change your
  selection in ModLoader before starting the game.
- Uses installed originals as the common base for real Git three-way text
  merging, followed by the applicable syntax/format checks.
- Preserves independent Lua modules when supported by the reviewed runtime,
  instead of concatenating unrelated scripts into one Lua context.
- Resolves declared dependencies and lets you select one Workshop/local version
  of the same package without rewriting the subscribed copy.
- Installs or upgrades the exact supported shared runtime when a selected mod
  needs it, using recorded backups and recovery. Unknown loaders are preserved.
- Keeps the previous applied set when a new selection is rejected and restores
  the actual working checkboxes/order.
- Offers **Menu > Restore previous selection...** for the recorded previous set.

The result is a separate local mod named **CC2 ModLoader: <selected mod names>**.
Source mods, Workshop downloads, vanilla game resources and the game executable
are not rewritten. ModLoader manages its own generated output, activation
configuration and supported runtime/settings through its recorded workflow.

## Load order and conflicts

**Load order** is the merge/patch order. Drag selected packages, or use
**Alt+Up/Down**; every change rebuilds automatically and is remembered.

**Menu > Later patches take priority** is enabled by default:

- Independent text edits are merged when possible.
- Overlapping text portions favor the later patch. Earlier unrelated edits are
  retained where the merge permits it.
- If an original data file is unavailable, the later file replaces the previous
  one as a reported whole-file replacement; no baseline is invented.
- Supported binary-resource collisions use explicit whole-file replacement.
  DLLs are never merged.

An orange override notice names the participants and affected file and states
that the in-game result is unknown. It remains available after reopening the
app. Read **Menu > Problem details...** before relying on the result.

Turn off **Later patches take priority** to reject unresolved conflicts instead.
Native compatibility, path, syntax and transaction checks apply in both modes.

## Folders and local packages

```text
Carrier Command 2 installation/
  carrier_command.exe
  CC2ModLoader.exe
  mods/<mod-package>/mod.xml
  mods/<mod-package>/content/...
  libraries/<library-package>/mod.xml
  libraries/<library-package>/content/...

Carrier Command 2 user data/
  mods/CC2-MCE/               # the one generated game mod
  cc2-mce/                   # app preferences, backups and recovery data
```

The app prepares its `mods` and `libraries` input folders automatically for the
selected game. Use **Menu > Add mod folder...** for another collection and
**Menu > File locations...** to inspect the actual paths.

A valid library declaration in `mod.xml` distinguishes a library from an
ordinary mod; the folder name alone does not. An unmarked package remains an
ordinary mod. Shared native plugins remain separate DLLs loaded by one reviewed
runtime, not binary code merged into an injector.

## Language and startup

The interface follows the system language by default. **Menu > Language**
provides English, Russian, German, French, Spanish, Brazilian Portuguese,
Italian, Polish, Turkish, Ukrainian, Simplified Chinese, Traditional Chinese,
Japanese and Korean. All 14 catalogs are included offline; an explicit choice
is saved. Mod names, paths and contents are not sent to translation services.

**Menu > Launch game when opening ModLoader** optionally prepares the selected
set and starts the game on later launches. A rejected change cancels automatic
launch. The normal GUI remains available when that option is disabled.

## Support and validation

| Area | Current scope |
| --- | --- |
| Ready desktop download | Windows x64 graphical executable with bundled merge/validation tools. |
| Shared code | Windows/macOS CI on Python 3.12 and 3.13, including real Git fixtures and the synthetic golden corpus. |
| Native game integration | Exact reviewed Windows CC2 1.5.18-r2 game/runtime/plugin profiles; unreviewed binaries stay blocked. |
| Current SDK integration | Exact 0.7 framework runtime: real-game bootstrap alone and with the existing native mod set and public C/C++ consumers. Independent Lua API 2 and named C API 1 have paired offline fixtures. |
| Historical single-player checks | The earlier 0.6 runtime covered combined native/Lua loading, custom aircraft registration/hangar creation and unchanged-catalog save/reload. Those results do not certify the new binary's full gameplay. |
| Remaining gates | Remote multiplayer, dedicated-server profile/bootstrap, full custom flight/island landing, changed-catalog save migration, clean-machine acceptance, packaged macOS app and native macOS runtime. |

These are distinct validation levels. Shared-core CI and a successful synthetic
merge do not prove game compatibility or a certified macOS application. See the
release notes and attached build metadata for the evidence for a particular
binary. The SDK's own source and distribution are maintained in the separate
[CC2X SDK project](https://github.com/Dioramawhois/Carrier-Command-2-extender/releases/tag/0.7.0-client-beta.1).

## Release contents and source transparency

The release page separates:

- the ready Windows application ZIP;
- the exact ModLoader application source ZIP;
- matching SDK runtime, SDK source and linked compiler-library sources;
- the pinned Git/Lua build-tools archive and corresponding dependency sources;
- release/build metadata, component notices, SBOM and SHA-256 checksums.

The Windows ZIP includes its player README and notices. The build guide explains
which additional archives are useful for an offline source build. Normal use of
the completed app does not download development dependencies.

## Contribute and report problems

Read [CONTRIBUTING.md](CONTRIBUTING.md) before making a change and
[SECURITY.md](SECURITY.md) for vulnerability reporting and repository policy.
Work in a topic branch or fork and submit a pull request; `main` is not the
contribution branch for direct pushes.

For ordinary bugs, include the app/game versions, selected mods and load order,
steps to reproduce the problem, and a report exported through the GUI. Review
that report before sharing it and use synthetic examples where possible.

The [documentation index](docs/README.md) links the current English guides and
the original, mostly Russian engineering specifications and ADR history. Those
historical records are not alternate player installation instructions.

## License

CC2 ModLoader is **GPL-3.0-or-later**; see [LICENSE](LICENSE). Third-party
components retain their own licenses and notices in [NOTICE.md](NOTICE.md) and
the release's `LICENSES` directory. Carrier Command 2 and other authors' mods
retain their respective ownership and licenses.
