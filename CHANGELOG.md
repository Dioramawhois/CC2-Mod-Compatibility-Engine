# Changelog

This file records project history. Historical validation and limitations describe
that entry's date; use the [README](README.md) and [current guides](docs/README.md)
for installation, self-build and support information.

## 0.4.0b8 - Windows beta 8 (2026-11-04)

- Fix startup failure `Input byte limit exceeded` for large installed mods and
  subscription collections. Discovery hashes resources incrementally rather
  than retaining all unchecked content in memory.
- Separate bounded resource discovery from selected-build input/output:
  512 MiB per resource, 16 GiB per discovery and 1 GiB each for materialized
  selected input and generated output. Text-processing inputs retain 16 MiB
  per-file limits; metadata/configuration keep separate tighter bounds.
  Explicit smaller developer limits remain effective.
- Revalidate deferred resource contents against their recorded size/hash.
  Preserve path/link/native checks, source provenance, merge rules and
  transactional activation. Byte-limit diagnostics identify the resource and
  applicable per-file or aggregate limit. See ADR-0031.
- Add offline regression coverage for large resources/collections, bounded
  discovery, changed sources and package verification. This hotfix does not
  claim fresh gameplay or beta 8 exact-binary menu acceptance; beta 7's menu
  evidence remains separately identified.

## 0.4.0b7 - Windows beta 7 (2026-11-04)

- Correct the main-menu integration boundary: the game's menu world clears
  ordinary resource overlays, so beta 5/6's generated menu-file decorator did
  not lock the real Mods entry. Retain this finding in the historical record.
- Deliver the owned policy through the SDK screen-extension declaration at
  `content/cc2x/screen_extensions.json` and `cc2x/ui/modloader_menu.lua`, using
  `sdk-screen-extension-v4` provenance. Preserve the requested badge/lock
  behavior, ordinary merge rules and reversible activation. See ADR-0030.
- Pin CC2X SDK **0.7.1-client-beta.1**, a maintenance release providing the
  generic screen-extension boundary. The SDK remains a framework; the menu
  policy is supplied by ModLoader's generated package. This exact pin does not
  replace the parallel SDK 0.8 release or its latest-release channel.
- The final Windows EXE/runtime pair passed real menu checks: the heading was
  visible, Mods stayed closed after a mouse click and Enter, and New Game
  opened normally. Exact hashes and captures are recorded in
  [menu verification](docs/verification/main-menu-v4.md);
  full gameplay and multiplayer are not certified by those menu checks.
- A separate run with the same SDK and no enabled extensions retained the
  ordinary Mods screen and showed no ModLoader heading. The original managed
  selection was restored after this control test.

## 0.4.0b6 - Windows beta 6 (2026-11-04)

- Identify the active generated set on the game's main menu with a
  noninteractive **CC2 ModLoader** header and compact selected-mod line above
  the first ordinary header, once per frame. Names follow source order, with
  control-character normalization, a 140-Unicode-character limit and safe Lua
  escaping. Other screens keep their ordinary headers.
- Retain the gray, disabled **Mods** entry and navigation guard. The decorator
  lives only in the generated merged menu resource; source mods, vanilla and
  the SDK remain untouched. Undo restores the prior build's menu behavior;
  an empty selection adds no label or guard. The 14 offline catalogs are unchanged.
- Record `modloader-main-menu-v3` in new package provenance while accepting both
  earlier policies. Retain final Lua validation and input/adapter/output hashes.
  See [ADR-0029](docs/adr/0029-main-menu-modloader-badge.md).
- Add owned synthetic Lua and package regressions. No fresh in-game visual or
  gameplay acceptance is claimed; existing beta 4 screenshot provenance is unchanged.

## 0.4.0b5 - Windows beta 5 (2026-11-04)

- Distribution addendum: accept verified LF/CRLF standalone checksums without
  rewriting published assets, and generate future checksums with LF on both
  Windows and macOS. This repairs the rolling beta link; the beta 5 executable
  and numbered release remain unchanged.

- Disable and gray the main-menu **Mods** entry while the generated ModLoader
  set is active, replacing the earlier guard that only disabled list rows.
  Reject direct navigation to that screen and return stale screen state to
  the main menu. The Workshop uploader behind the entry is also unavailable;
  other menus and gameplay remain available.
- Keep the decorator inside the generated merged menu resource, with final
  Lua syntax validation and adapter/input/output hashes. Removing or undoing
  the generated set restores the ordinary menu; an empty selection adds no guard.
- Record `locked-mods-menu-v2` in new package provenance and retain schema
  compatibility with `read-only-mod-list-v1`. See ADR-0028.
- Cover the entry, navigation, stale state and unrelated UI with owned synthetic
  Lua fixtures. No fresh in-game visual or gameplay acceptance is claimed.

## 0.4.0b4 - Windows beta 4 (2026-11-04)

- Documentation addendum: beginner-first English README with four actual GUI
  screenshots, separate compatibility/provenance pages, and an English announcement
  kit. Screenshots use an isolated demo workspace and do not claim gameplay acceptance.

- Distribution addendum: publish the byte-identical standalone executable and
  checksum, plus a permanent `latest-beta` EXE download that follows published
  beta releases. Complete sources/notices and numbered archives remain available.

- Automatically discover custom mods in the standard game user-data mods
  folder, including `%APPDATA%\Carrier Command 2\mods` on Windows.
- Refresh the user-mod root on every scan, so creating it after startup
  needs no manual folder selection. Keep new mods unchecked, preserve the
  current selection and exclude owned generated output.
- Document both local locations and retain existing path/native validation,
  Workshop discovery and package/report schemas. See ADR-0026.

## 0.4.0b3 - Windows beta 3 (2026-11-03)

- Pin the published CC2X SDK 0.7.0-client-beta.1 runtime, Lua API 2 and
  named C framework API 1. Upgrade the exact reviewed 0.6 runtime reversibly;
  preserve unknown installed loaders. Exact-source and compiler-library
  notices remain separate release assets. Current native acceptance covers
  bootstrap and consumer loading; full gameplay and multiplayer remain open.

- Start the local game executable directly with the game working directory.
  Recheck the applied activation and package before launching.
- Refresh and rebuild the saved mod set on every ModLoader startup, including
  added/removed Workshop files. Recover the last owned selection if the game
  changed its active mods, then activate only the generated build.
- Add an owned, syntax-checked menu decorator to generated packages: the game
  mod list is gray and read-only while ModLoader manages the selected set.
  Vanilla and Workshop files remain untouched; see ADR-0025.

- Keep native C/C++ plugin support alongside Lua. Recognize a separate
  `framework_api` package requirement and require the matching reviewed C
  extension capability, preventing an older API 8 binary from silently
  accepting a consumer of the new named interface.

- Record a separate `lua_api` requirement in package metadata and source reports.
  Require a matching reviewed runtime capability as well as its Lua API version;
  the published C API 8 runtime cannot silently satisfy newer Lua-only mods.
- Adopt the framework-only SDK boundary: new gameplay releases own their Lua
  policy and content and contain no private native plugin. Migration and fresh
  game acceptance remain in progress; see ADR-0024.

## 0.4.0b2 - Windows beta 2 (2026-11-03)

- Publish two documented distribution routes: the ready-to-use Windows executable
  and a clean application-source archive that can build the same GUI. English
  installation, build, contribution, troubleshooting and security guides replace
  the previous mixed-language public entry points.
- Restore a missing SDK dependency during a source-archive build from an exact,
  pinned release, checking its size and SHA-256. Existing unknown files and links
  remain protected; developers can supply a verified local file for offline use.
- Release packaging checks the actual archived application source against the
  frozen build inputs. Export-ignored native binaries and pinned Git/Lua tools
  have explicit, verified restoration paths rather than private sibling paths.
- Workshop and local versions of the same package can coexist in the list.
  Selecting a version replaces the selected version of that identity in one
  transaction; rejection restores the previous selection. Dependencies follow the
  explicit choice, while ambiguous or duplicate selections are rejected.
- Bundle the exact reviewed CC2X API 8 runtime, clean-build provenance and component
  notices. Reviewed native profiles cover Hold, Modes, Brake and Island Airfields
  v46; the previous v45 profile remains available. Unknown DLLs remain blocked.
- Install or upgrade a known SDK runtime transactionally with backup, recovery and
  Undo. The built-in reviewed dependency can satisfy cc2x.runtime without requiring
  a separate manual SDK installation. Unknown installed loaders are preserved.
- Create missing INI defaults only for exact reviewed native hashes. Existing user
  settings survive; ordinary failures and interrupted writes are recoverable.
- Keep independent Bridge Lua owners/code roots inside one generated CC2-MCE mod.
  Ordered module bundles preserve dependencies and private code contexts. Shared
  resources still use Git merging. Duplicate owners, stock-script entries, unsafe
  manifests and unreviewed native code remain blocked.
- Remove SDK test-build notices from the ModLoader interface and all 14 offline
  catalogs. Runtime review metadata stays in reports; warnings about actual mod
  overwrites continue to show participants, resources, order and uncertainty.
- Count each original-resource directory once per analysis, avoiding false scan
  budget failures. Recovery preserves complete relative executable paths,
  including macOS application layouts.
- Recorded Windows single-player checks with the combined SDK/mod set covered
  F-16/F-15 registration and hangar creation, a new temporary save, reloading the
  same catalog with unchanged IDs, and creation after reload. Previous user game
  state, runtime, activation/Undo and saves were restored after testing.
- Publish separate application, SDK and tool source assets, including generated
  native inputs, compiler-library sources, licenses, SBOM and SHA-256 checksums.
  Remote multiplayer, dedicated servers, full flight/island landing, changed-catalog
  saves, clean-machine and packaged macOS acceptance remain incomplete or unverified.

## Native Bridge and cc2mods integration audit (2026-11-02)

- Defined a common SDK with separate gameplay-mod projects, private Lua namespaces,
  preserved identities/catalogs and explicit networking boundaries. Extractors use
  SHA-locked sources without copying the SDK into every mod.
- The project owner confirmed the team's integration/publication permissions.
  Original GPL/MIT notices and provenance were retained. F-16/F-15 content was
  separated with its original IDs and 57 source files.
- Found an API-layout collision between the session prototype and Native Bridge.
  A checked named session extension preserves the existing C API prefix.
- Corrected waypoint update publication in the companion Island Airfields project
  using the existing explicit replication model. Offline regressions were added;
  this audit did not establish multiplayer acceptance.

## 0.4.0b1 - Open-source Windows beta and prepared launch (2026-11-02)

- Adopted the owner's GPL-3.0-or-later license, LICENSE/NOTICE and project metadata.
- Added the persistent Menu > Launch game when opening ModLoader option. Startup
  prepares and activates the selected set before opening Steam. Rejected changes
  cancel automatic launch; overwrite warnings remain available.
- A clean developer checkout downloads SHA-pinned Git/Lua tools. Bounded archive
  validation rejects unsafe, corrupt or unexpected payloads before writing files.
- Added a release packager with provenance/JUnit checks, privacy-filtered build
  reports, Windows/source/tool-source assets, component notices, SBOM and checksums.
- Updated the existing ModLoader rather than creating another Workshop mod.
  In-game UI, multiplayer, clean-machine and packaged macOS certification were
  not completed by this beta.

## 0.3.3 - Game resource formats and actionable errors (2026-11-02)

- Support .glsl text merging and TXTR-magic .txtr copy/ordered replacement using
  real installed resource examples. Invalid headers and unknown types remain
  blockers; DLL checks are unchanged.
- Show the unsupported file or unavailable Lua-validator reason directly in the
  notice, with detailed diagnostics and translations in all 14 languages.
- Corrected a Windows-only synthetic-layout fixture exposed by macOS CI; added
  explicit Windows/Darwin layout coverage without weakening production discovery.

## 0.3.2 - Persistent overwrite warnings and Steam audit (2026-11-02)

- Ordered-patch application retains a warning naming the affected mods, merge
  order and resource. Details distinguish conflicting hunks from whole-file
  replacements and explain that the in-game result is unknown.
- Warnings survive reopening/passive scans, update on reorder and disappear when
  the overwrite disappears. Clean or identical overlap is not called incompatible.
- Audited Workshop Required Items, real CC2X discovery, first-run bootstrap,
  Player Tools/SteamPipe options and licenses. Prepared author templates without
  inventing Workshop IDs or claiming that subscription installs the native loader.

## 0.3.1 - CC2 ModLoader branding and 14 languages (2026-11-02)

- Restored CC2 ModLoader branding and CC2ModLoader.exe. Generated game-mod names
  include selected author-supplied names; known previous executables are backed up.
- Added 12 offline catalogs to Russian/English, locale mapping and native language
  names. Catalog keys/placeholders are checked; some secondary text is machine
  assisted. Runtime translation requires no network requests.
- Moved CI from the retired macos-14 runner to macos-15.

## 0.3.0 - Merge order and system language (2026-11-02)

- Added persistent drag/drop and Alt+Up/Down load order with automatic rebuilding.
  Later patches take conflicting hunks while independent edits are preserved.
  Missing-base data replacement is explicit and reported; strict mode is optional.
- Use installed rom_0/SDK originals without a per-file hash allowlist, retaining
  hashes and provenance. Native, path and syntax gates remain mandatory.
- Follow the system language by default and preserve explicit choices/pending
  selection across language changes. Selected tabs are larger than inactive tabs.
- Save preferences atomically; record baseline source, policy and JUnit counts.

## 0.2.2 - Clear checkbox state and simpler UI (2026-11-02)

- Rejected changes restore the actual working selection and keep it launchable.
  Inline errors name the rejected mod, participants and resource, and survive scans.
- Explain dependencies that remain selected because another selected mod needs them.
- Prepare local mods/libraries folders automatically. Keep primary actions to the
  list, result and Launch; move secondary operations into one menu.

## 0.2.1 - One output and automatic checkbox application (2026-11-02)

- Each checkbox change authorizes validation, merging and activation without
  additional Check/Apply buttons. Maintain one transactional mods/CC2-MCE output.
- Replace the complete generated folder, preserving backup/config rollback and
  source hashes. Defer application while the game runs; preserve author inputs.

## 0.2.0 - Game activation and SDK libraries (2026-11-01)

- Added the Windows GUI packaging/activation pipeline, real Git merging with
  explicit LF policy, bundled Lua 5.3 checking, backup/journal rollback, process
  locks, source-integrity checks and refusal of foreign output files.
- Recognize a provided reviewed dinput8.dll and keep native plugins as separate
  byte-identical copies. No DLL merging or trust by filename/location.
- Added opt-in cc2mce mod.xml library/dependency metadata and package schema v2.
- AI Bridge + Island Airfields reached the menu with a fresh combined-plugin log.
  At that stage full gameplay and macOS/clean-machine acceptance remained open.
  The earlier application executable was named CC2Engine.exe.

## Earlier engineering milestones (2026-10-26 to 2026-10-31)

- Read-only Steam discovery added secondary libraries, adjacent-game checks,
  bounded metadata parsing and traversal/link protection. The early GUI used an
  explicit preparation button, later replaced by automatic setup in 0.2.2.
- Initial Windows freezing included JSON schemas and Python source for engine
  hashes; the batch script handled Python discovery, external working folders,
  a reusable virtual environment and --no-pause error propagation. PyInstaller
  was pinned to 6.22.3. Early builds did not yet bundle Git/Lua.
- The developer CLI gained clean merged-file output with real Git; schema v1
  remained non-installable, and conflicts/absent output paths wrote nothing.
- Native installation required explicit reviewed version/architecture/hash gates.
  A manifest alone did not authorize runtime injection or unknown plugin code.
- A separate macOS runtime spike exercised limited Lua initialization on two
  inspected builds. It did not establish Windows CC2X ABI compatibility, a player
  installer, a full gameplay session, third-party mods, saves or native plugins.
- GUI-only player workflows became a release requirement. CLI commands moved to
  contributor documentation; synthetic checks did not become game acceptance.

## 0.1.0.dev1 - Read-only prototype (2026-10-26)

### Added

- Developer doctor, scan, plan, build --dry-run and report commands with strict TOML.
- Bounded discovery, content-relative paths, case/Unicode collision checks,
  link rejection and SHA-256 input snapshot rechecks.
- Explicit baseline mapping, source provenance and game executable fingerprints.
- Real Git three-way merging with pairwise N-way preflight, copy/deduplication,
  fail-closed binary/native/encoding policies, Lua 5.3 syntax and safe XML parsing.
- Schema v1 reports containing source/base/engine/output hashes, order, tool
  versions and policy metadata; reports are written outside input sources.
- A synthetic golden corpus, regression tests, dependency lock, lint/type checks
  and a Windows/macOS CI definition.

### Historical limitations

- The prototype was not a complete MVP or a game-loadable publisher: installable
  was always false, with no atomic package activation/rollback or game smoke.
- Real Workshop content was only inventoried. Current game/SDK mapping, Windows
  CI and real Lua validation were not established by that first slice.
- The project license had not yet been selected at the time; GPL-3.0-or-later was
  adopted later in 0.4.0b1.
