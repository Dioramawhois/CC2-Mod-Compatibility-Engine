# Documentation

Start with the English guides below. They describe the current graphical
application and its two distribution routes.

| I want to... | Read |
| --- | --- |
| Download the ready-to-use executable | [Main README](../README.md#start-here) |
| Install, select mods, set patch order and undo a change | [Installation and use](INSTALLATION.md) |
| Build the Windows executable from source | [Building from source](BUILDING.md) |
| Understand development checks and contribute changes | [Contributing](../CONTRIBUTING.md) |
| Report a security problem or understand repository policy | [Security](../SECURITY.md) |
| Read release changes | [Changelog](../CHANGELOG.md) |
| Check supported platforms and verification limits | [Compatibility and verification](COMPATIBILITY.md) |
| Check exact native-library source and compatibility | [CC2X SDK release](https://github.com/Dioramawhois/Carrier-Command-2-extender/releases/tag/0.7.0-client-beta.1) |
| Reuse screenshots or the English announcement | [Announcement kit](announcements/README.md) |

The application UI includes 14 offline languages. The language of a technical
document does not change the selected interface language or any mod contents.

## Release files

The release page separates the standalone EXE and ready Windows ZIP from application source,
native dependency source/runtime archives, third-party tool sources, build
metadata and checksums. Players can download the EXE directly; the full ZIP also
contains its README, component notices and verification metadata.
See [the build guide](BUILDING.md) before choosing a source archive.

## Design and implementation references

The numbered specifications and architecture decisions below are the original
engineering record, mostly written in Russian. Some early sections describe
historical prototypes or planned gates. Read their versioned updates and later
ADRs together; they are not an alternative set of player installation steps.

- [Product requirements](01-PRODUCT-REQUIREMENTS.md)
- [Architecture](02-ARCHITECTURE.md)
- [Merge specification](03-MERGE-SPEC.md)
- [CC2 integration](04-CC2-INTEGRATION.md)
- [Internal CLI and data contracts](05-CLI-AND-DATA-CONTRACTS.md)
- [Test strategy](06-TEST-STRATEGY.md)
- [UX/UI specification](13-UX-UI.md)
- [Library metadata contract](17-LIBRARY-SDK.md)
- [Steam distribution audit](19-STEAM-DISTRIBUTION-AUDIT.md)
- [Common SDK and separate gameplay mods](22-UNIFIED-SDK-AND-MOD-SPLIT.md)
- [Architecture decisions](adr/)

The current English README, installation/build guides and the release's own
metadata take precedence for public download and installation instructions.
Neither a historical test plan nor a successful synthetic test is a claim of
fresh gameplay, multiplayer, clean-machine or packaged macOS acceptance.
