# Compatibility and verification

CC2 ModLoader 0.4.0 beta 6 is a Windows x64 desktop beta. A successful file
merge is useful evidence about files; it does not establish gameplay compatibility.

## What the application checks

- Text changes use real Git three-way merging when installed originals are available.
- Later patches take priority by default. Overwritten changes are reported.
  Missing originals can produce an explicitly reported whole-file replacement.
- Turning off **Later patches take priority** rejects unresolved conflicts.
- Applicable syntax/format checks, input path validation and transactional
  activation still apply. Original mod resources are read in place.
- Reviewed native DLLs remain separate byte-identical copies. DLLs are never
  merged, and unknown installed loaders or plugin bytes are not trusted by name.
- The application manages its generated package, activation configuration and,
  where required, the exact reviewed runtime/settings with backup/recovery data.

The default user-mod location is `%APPDATA%\Carrier Command 2\mods` on Windows.
The equivalent discovery path on macOS is
`~/Library/Application Support/Carrier Command 2/mods`.

## Current evidence

| Area | Scope |
| --- | --- |
| Ready desktop download | Windows x64 GUI with bundled merge and validation tools. |
| Shared code | Windows/macOS CI on Python 3.12 and 3.13; actual Git fixtures and owned Lua tests. |
| Native integration | Exact reviewed Windows CC2 1.5.18-r2 game/runtime/plugin profiles. Data-only merging can have a different scope. |
| SDK 0.7 | Real-game bootstrap alone and with the existing native set and public C/C++ consumers. Shared Lua API 2 / C framework API 1 have paired offline fixtures. |
| Historical SDK 0.6 | Combined native/Lua loading, custom aircraft registration/hangar creation and unchanged-catalog save/reload. These results do not certify the newer binary's full gameplay. |
| Screenshots | Actual application UI and private demonstration file operations. They are not gameplay or multiplayer acceptance. |

The current [SDK release](https://github.com/Dioramawhois/Carrier-Command-2-extender/releases/tag/0.7.0-client-beta.1)
and the ModLoader release's verification files identify exact tested binaries.
The SDK is a separate framework; aircraft, airfields and other gameplay content
belong to separately selected mods.

## Still unverified

Remote multiplayer, dedicated-server profile/bootstrap, full custom-aircraft
flight/island landing, changed-catalog save migration, clean-machine acceptance,
a packaged macOS app and native macOS runtime are not certified by this beta.
The generated main menu shows **CC2 ModLoader** and a compact selected-mod line
while the owned set is active. The **Mods** entry remains disabled, including
access to its Workshop uploader. Other menus and gameplay remain available.
Undo restores the prior build's menu behavior; disabling the generated set
removes its menu changes. An empty selection adds no label or guard. The menu
decorator has owned synthetic Lua coverage and real Lua syntax checks; the
beta 6 label and disabled entry have no fresh in-game visual acceptance.
Historical beta 4 GUI screenshots do not verify this game-menu behavior.

Mod authors can create gameplay conflicts even when file merging succeeds.
Use the warning details and test your own selected set. Keep save backups when
changing gameplay mods, following those mods' own instructions.

## Source and redistribution

The release includes a standalone EXE/checksum, complete Windows ZIP,
application source, exact SDK runtime/source, compiler-library source, pinned
Git/Lua tools and corresponding dependency sources, notices, SBOM and checksums.
`latest-beta` mirrors the complete numbered release; `CHANNEL.json` identifies
the exact version and hashes. Numbered release tags and original archives stay fixed.

For redistribution, retain the complete ZIP's notices and corresponding source
materials. See [NOTICE.md](../NOTICE.md), [Building from source](BUILDING.md),
[Contributing](../CONTRIBUTING.md) and [Security](../SECURITY.md).
