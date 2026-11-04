# Compatibility and verification

CC2 ModLoader 0.4.0 beta 8 is a Windows x64 desktop beta. A successful file
merge is useful evidence about files; it does not establish gameplay compatibility.

Beta 8 changes bounded resource discovery/reading to fix large-collection
startup failures. See [resource limits](INSTALLATION.md#large-mods-and-resource-limits)
and [ADR-0031](adr/0031-streamed-resource-discovery-and-budgets.md). Its offline
regressions do not constitute new game-menu or gameplay acceptance. The beta 7
exact-binary menu checks below remain identified as beta 7 evidence.

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
| SDK 0.7.1 screen extensions | Final Windows EXE/runtime pair: heading visible, Mods blocked for mouse click and Enter, New Game navigation working. Exact hashes/captures are in [menu verification](verification/main-menu-v4.md). |
| SDK-only menu control | With the same runtime and no active extensions, the ordinary Mods screen opens and no ModLoader heading is shown. The previous managed selection was restored. |
| Historical SDK 0.6 | Combined native/Lua loading, custom aircraft registration/hangar creation and unchanged-catalog save/reload. These results do not certify the newer binary's full gameplay. |
| Screenshots | Actual application UI and private demonstration file operations. They are not gameplay or multiplayer acceptance. |

The pinned [SDK maintenance release](https://github.com/Dioramawhois/Carrier-Command-2-extender/releases/tag/0.7.1-client-beta.1)
and the ModLoader release's verification files identify exact tested binaries.
The SDK is a separate framework; aircraft, airfields and other gameplay content
belong to separately selected mods.
This is an exact ModLoader dependency, not a claim that 0.7.1 replaces the
parallel SDK 0.8 release or its latest-release channel.

## Still unverified

Remote multiplayer, dedicated-server profile/bootstrap, full custom-aircraft
flight/island landing, changed-catalog save migration, clean-machine acceptance,
a packaged macOS app and native macOS runtime are not certified by this beta.
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
