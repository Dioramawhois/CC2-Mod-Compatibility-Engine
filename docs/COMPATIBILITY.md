# Compatibility and verification

CC2 ModLoader 0.4.0 beta 9 is a Windows x64 desktop beta. A successful file
merge is useful evidence about files; it does not establish gameplay compatibility.

Beta 8 changes bounded resource discovery/reading to fix large-collection
startup failures. See [resource limits](INSTALLATION.md#large-mods-and-resource-limits)
and [ADR-0031](adr/0031-streamed-resource-discovery-and-budgets.md). Its offline
regressions do not constitute new game-menu or gameplay acceptance. The beta 7
exact-binary menu checks below remain identified as beta 7 evidence.

Beta 9 synchronizes the bundled provider and reviewed profile with CC2X SDK
0.8.1-client-beta.1. It distinguishes an unsupported runtime in a downloaded
library (`runtime_source_conflict`) from an incompatible installed loader
(`runtime_conflict`). See [ADR-0032](adr/0032-reviewed-sdk-provider-synchronization.md).

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
| Historical beta 7 / SDK 0.7.1 screen extensions | That Windows EXE/runtime pair showed the heading, blocked Mods for mouse click and Enter, and retained New Game navigation. Exact hashes/captures are in [menu verification](verification/main-menu-v4.md). |
| Historical beta 7 SDK-only menu control | With that runtime and no active extensions, the ordinary Mods screen opened and no ModLoader heading was shown. The previous managed selection was restored. |
| Beta 9 provider synchronization | Synthetic fixtures cover a Workshop source update while removing a gameplay mod, reversible old-to-current upgrade, no downgrade from an older reviewed source, and separate source/installed-runtime refusal. These are offline transaction and UI-report checks. |
| Historical SDK 0.6 | Combined native/Lua loading, custom aircraft registration/hangar creation and unchanged-catalog save/reload. These results do not certify the newer binary's full gameplay. |
| Screenshots | Actual application UI and private demonstration file operations. They are not gameplay or multiplayer acceptance. |

## Current native dependency

The pinned [SDK release](https://github.com/Dioramawhois/Carrier-Command-2-extender/releases/tag/0.8.1-client-beta.1)
and the ModLoader release metadata identify the current dependency:

| Identity | Value |
| --- | --- |
| Runtime version | `0.8.1-client-beta.1` |
| DLL SHA-256 | `98ba9bfbc217767ecc5a30aaa3cd5de8d3d7de1f9e8a9164cd0e0e32a6bed085` |
| Source revision | `f322938094bf7ea9e30f3be841b3c744687385b8` |
| Added reviewed capabilities | `waypoint-origin-v1`, `screen-source-edits-v1` |

The reviewed 0.7.1 runtime (`c741ed11…`) remains a previous version eligible for
the journaled upgrade. It is not the new provider, and recognizing it does not
authorize an unreviewed future Workshop DLL. Source/runtime/profile locks move
together; an SDK update requires a matching reviewed ModLoader release.

The SDK is a separate framework; aircraft, airfields and other gameplay content
belong to separately selected mods.

## Still unverified

Remote multiplayer, dedicated-server profile/bootstrap, full custom-aircraft
flight/island landing, changed-catalog save migration, clean-machine acceptance,
a packaged macOS app and native macOS runtime are not certified by this beta.
The beta 9 provider pin is not a fresh exact-binary game-menu or gameplay
acceptance claim. Static review, upstream SDK fixtures and the synthetic
transaction checks above have separate scope from real-game validation.
The owner reported a beta 6 defect: the real **Mods** entry remained
clickable and the planned ModLoader heading was absent. The initial menu clears
ordinary resource overlays, so the generated menu file is not sufficient.
Beta 7 uses a reviewed SDK screen-extension mechanism. Its final packaged-pair
label, Mods lock and New Game navigation passed the scoped test recorded in
[menu verification](verification/main-menu-v4.md).
Owned Lua fixtures and syntax checks alone do not establish that acceptance.
See [ADR-0030](adr/0030-sdk-screen-extension-delivery.md).
Historical beta 4 GUI screenshots do not verify this game-menu behavior.
The newer game captures in that verification record cover menu behavior only.

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
