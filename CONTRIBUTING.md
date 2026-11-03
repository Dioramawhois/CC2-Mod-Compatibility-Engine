# Contributing to CC2 ModLoader

Players installing the application should start with
[Installation and use](docs/INSTALLATION.md). This document is for contributors;
[Building from source](docs/BUILDING.md) gives the complete self-build route.

## Before making a change

Read [AGENTS.md](AGENTS.md), the applicable specifications and later architecture
decisions. The numbered documents are the original engineering record, mostly
in Russian. Later accepted decisions and explicit owner requirements supersede
older prototype limitations; do not treat a historical read-only design as the
current application.

Keep the user workflow graphical: a player using the ready executable must not
need commands, hand-edited manifests, developer tools or PATH setup. Commands
in this contributor guide are development/CI tools, not player instructions.

## Branches and pull requests

Use a fork or a topic branch, for example:

- `feat/<topic>` for a feature;
- `fix/<topic>` for a bug fix;
- `docs/<topic>` for documentation;
- `spike/<topic>` for an explicitly experimental investigation.

Submit a pull request to `main`. Follow the enforced branch rules and required
checks; do not use direct or force pushes to work around the review workflow.
When only the owner has write access, a PR may be merged by that owner after
checks pass without a second approval. Do not confuse this with independent
review. See [Security policy](SECURITY.md) for the access-control limits.

Describe the concrete problem, resulting behavior, validation and material
limitations. Link the relevant requirement or decision when it explains a
tradeoff. For a public contract change, update the schema/API documentation,
regressions, applicable ADR and changelog together. Keep the PR focused.

## Prepare a development environment

Use Python 3.12 or 3.13 and Git. Install `uv` on the developer machine, then run
from the repository root:

```text
uv sync --frozen --extra dev
uv run --frozen cc2-mce --version
uv run --frozen pytest -q
uv run --frozen ruff check cc2_mce tests
uv run --frozen ruff format --check cc2_mce tests
uv run --frozen mypy cc2_mce
```

`uv.lock` fixes the development dependency set. The standard Windows batch
builder uses its own `.build-venv` and pip; see the build guide for that route,
its bundled native dependencies and the difference between a clone and a source
export.

For a synthetic merge smoke check:

```text
uv run --frozen cc2-mce --config examples/mce.synthetic.toml build --dry-run
```

This command uses synthetic fixtures and does not activate a game mod. A
passing CLI/golden result is not gameplay acceptance.

## Tests and evidence

Write a meaningful regression fixture before fixing a behavioral defect. Use
small synthetic Lua/XML/data inputs rather than proprietary game files. Preserve
fixture bytes and test path, encoding, no-base, native/binary and failure cases
when the change affects those boundaries.

Use real Git three-way merging for integration fixtures. A mocked subprocess
can test its boundary, but it is not evidence that the actual bundled tool or
game integration works. Lua validation checks syntax; it does not prove gameplay
logic, engine API compatibility or networking.

GUI fixtures use actual Tk widgets where a display is available. A display-based
skip must remain visible in the results. Core tests on macOS do not certify a
packaged macOS GUI or native CC2X runtime.

Run the required checks once after the relevant changes and record their
results. Broaden verification when a new failure or unresolved concern warrants
it. Distinguish local unit/integration checks, frozen binary smoke checks,
clean-machine usability and fresh in-game acceptance.

## Source and native safety

- Treat mod paths, filenames, metadata and contents as untrusted input.
- Do not modify vanilla game resources, the game executable, Workshop downloads
  or other authors' source mods.
- Do not execute mod Lua or load mod DLLs in discovery/development utilities.
- Keep native review keyed to exact game/runtime/plugin bytes. A name, folder,
  library declaration or team origin is not a trust decision.
- Do not bypass syntax, path, native or transaction checks for convenience.
- Keep source/base/engine/output hashes and deterministic mod order in generated
  reports and manifests.
- Preserve the previous working set on rejection or failed publication; retain
  recovery data when a third party changes a managed file.
- Retain upstream licenses/notices and verify dependency license compatibility.

User-authorized later-patch priority is explicit and reported, not silent data
loss. It does not permit binary DLL merging or unreviewed native installation.

## Real-game and installation tests

The normal build and CI must not modify the user's actual game configuration,
activate a test set or launch the game. Real-installation harnesses and
`tools/install_local_build.py` are maintainer tools for a specifically authorized
local task, not commands to add to the default contributor checks.

For an authorized game test, preserve the original activation, runtime, managed
output, recovery data and saves; use a disposable test session and record exact
versions and hashes. Restore user state afterwards. A menu startup, a single
feature test and a multiplayer test are different acceptance levels.

## Preparing an official release

Use a clean reviewed commit and the matching verified executable. The release
publisher rejects mismatched binary/source hashes, failing regression metadata,
unsafe/private archive paths and incomplete corresponding dependency sources.
It prepares a new release directory; it must not silently replace an existing
release.

For the current native dependency, `tools/package_release.py` additionally
requires the exact SDK source checkout and compiler provider needed to export
its corresponding sources. These are maintainer release inputs, not requirements
for a normal ModLoader self-build. Preserve the source/runtime separation and
all redistribution notices. Never include game executables, personal saves,
research dumps, credentials or private user paths in public release assets.

Do not label unverified multiplayer, dedicated-server, flight/landing,
clean-machine or packaged macOS behavior as complete. The release must name its
actual validation level and link its matching sources.

## Security reports

Follow [SECURITY.md](SECURITY.md). Do not publish a dangerous executable fixture,
exploit details or private data in an ordinary public issue.
