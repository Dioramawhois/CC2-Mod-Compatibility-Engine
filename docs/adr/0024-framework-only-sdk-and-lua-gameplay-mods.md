# ADR-0024: framework SDK and separate Lua gameplay mods

Status: implementation in progress; supersedes the native-consumer migration
exception in docs/22 for the new mod releases. Date: 2026-11-03.

## Owner requirement

The SDK provides reusable engine capabilities and must introduce no gameplay
features by itself. Hold, Modes, Brake, Island Airfields and aircraft remain
individually selectable packages. Gameplay behavior, interfaces, configuration,
timers and conditions belong to their Lua/content packages. Mod authors must
not compile C or edit the SDK to build an ordinary gameplay mod.

Native code is permitted inside the framework for verified engine operations,
thread/session boundaries, lifecycle and transport. It must contain no selected
mod names, built-in feature activation or hard-coded gameplay policy. A Lua
enable switch around an entire native gameplay implementation is insufficient.

Owner clarification: C/C++ plugin development remains a supported SDK route.
Every shared engine capability must have public C and Lua access to the same
backend. The Lua-only packaging requirement above applies to the gameplay mods
we are migrating; it does not prohibit other authors from choosing native
plugins. Native policies remain outside the framework, with the existing hash
review and separate-DLL packaging rules. New Lua bindings must not consume
legacy native hook sites until explicitly requested by a consumer. Functional
parity requires paired C/Lua tests, not matching version numbers or two headers.

The candidate now implements the named C framework extension alongside Lua API
2. Paired synthetic-engine fixtures execute both frontends for world writes,
controls, button read aliases, input, messages, metadata, vehicle declarations,
native functions and next-tick tasks. The legacy C prefix remains unchanged.
The SDK capability contract inventories both routes and explicitly records the
remaining private Brake v15 operations and gameplay/remote/dedicated gates.
Passing fixtures does not certify those unimplemented migration features.

## Compatibility

The new Lua framework API has its own version, independent of the stable C API
prefix. A package declares `<cc2mce ... sdk="cc2x" api="8" lua_api="2">` and the
ordinary `cc2x.runtime` dependency. The scanner records the integer in its source
report. Analysis requires both `runtime_lua_api >= 2` and the exact reviewed
`lua-mod-api-v2` runtime capability. Existing packages without `lua_api` preserve
their previous behavior. Unknown native runtime hashes remain disallowed.

The older 0.6 SDK API 8 binary predates these Lua additions; a shared C API
number cannot establish support. The runtime facade additionally exposes
`cc2.lua_api_version`; a Lua mod checks it during its runtime initialization.
Older published releases, tags and native approval hashes are not rewritten.

SDK 0.7.0-client-beta.1 is now published from source commit
`8bafe71a9d43d8ed31e9eab1955d90d85f91b157`. The matching ModLoader beta 3
profile pins DLL SHA-256
`ed27641315e3957e991bb5fb00de8481c4a5ba7432d48a2638dee1d939110ff0`,
Lua API 2 and named C framework API 1. The exact previous 0.6 runtime is an
allowed reversible upgrade source. Unknown installed loaders remain blocked.
Its current real-game evidence covers bootstrap and consumer loading; historical
0.6 gameplay checks are not transferred to the new DLL. SDK version/test status
remains in technical metadata rather than the ModLoader interface.

The new named C interface has an independent `framework_api` requirement.
The scanner records this optional integer (0..10000), and analysis requires
both `runtime_framework_api` and `framework-c-api-vN`. This mirrors the Lua
version/capability check; an old C API 8 binary must not appear to satisfy the
new extension. Packages using both interfaces declare both requirements.
Legacy declarations preserve their report shape and behavior. DLL review and
path/syntax safety gates are unchanged.

## Implementation and acceptance

The candidate SDK exposes generic synchronous events, copied named-button
states and staged state-message transport, checked wing throttle operations,
and bounded per-module UI request/state mailboxes. Topics, button names,
aircraft policies and key bindings are chosen by each Lua mod. Mailboxes are
cleared on session change, reload, failed initialization and removal. Engine
writes require the verified game thread and supported native profile.

Hold and Modes have separate Lua policy candidates and syntax-checked player
packages with no private DLL or C payload. The Hold UI recipe now includes the
author's AC layout from upstream `a40d157`; Brake v15 source/research has been
preserved for its migration. This is ongoing work, not an announcement that all
mods have already reached gameplay parity or Steam publication acceptance.

Required evidence includes an empty SDK with no gameplay actions, independent
mod selection/removal, policy tests, native primitive/profile tests, source and
resource hashes, fresh in-game behavior checks, and normal installation through
the matching ModLoader. Single-player fixtures do not prove multiplayer. The
full Brake/Island migrations and fresh early-rules / Hold first-press acceptance
must be completed before advertising the new set as ready to publish.
The candidate now has separate read-only rules VMs and immediate checked button
read aliases; ordinary modules have no OS or native-library loading API. Offline
regressions cover these boundaries. Runtime acceptance remains a separate gate.
