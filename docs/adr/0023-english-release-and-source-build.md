# ADR-0023: English release documentation and a complete self-build route

Status: accepted, 2026-11-03, following the owner's release-preparation request.

## Decision

Publish CC2 ModLoader separately from the SDK, with two clearly named routes:

1. The Windows ZIP contains the ready graphical executable and redistribution
   notices. Players need no Python, Git, Lua, terminal or manual manifest editing.
2. The application source ZIP or exact Git tag supports a documented Windows
   developer build that produces the same GUI. Python/Git/build commands are
   explicitly authorized for people choosing this route, not player prerequisites.

README, installation/build guides, contributor/security policies, changelog,
player instructions and GitHub issue/PR entry points are in English. Original
numbered specifications are labelled historical engineering references. The
application keeps its existing 14 offline language catalogs and system default.

## Source and dependency integrity

The source ZIP excludes the compiled SDK DLL through export-ignore. A normal
Git clone includes that reviewed dependency. The build now handles both inputs:
it verifies an existing SDK file or restores the exact pinned release asset,
checking size and SHA-256 before publishing a complete file. A verified local
file supports offline preparation. Unknown existing files, links and competing
writers are preserved. Hydration never installs into or launches the game.

Release packaging validates bytes actually placed in the application source ZIP
against the frozen source/build report. Only certified LF/CRLF restoration and
explicit hash-verified deferred SDK/Git/Lua inputs are permitted. Missing build
helpers, changed hashes, unsafe paths and links reject packaging. The package
schema and native trust profiles do not change.

Each release includes the application ZIP, complete application source, exact
corresponding dependency sources/notices, provenance, SBOM and checksums. A clean
source-archive build and frozen GUI/tool verification are recorded independently
of earlier game acceptance. Windows/macOS core CI does not certify a packaged
macOS application, native macOS SDK or multiplayer support.

## Main-branch protection

Changes to main go through a PR with an up-to-date branch, four required GitHub
Actions checks for Windows/macOS with Python 3.12/3.13, and resolved review
conversations. Rules apply to administrators; force-push and deletion are
disabled. Actions checks are bound to the expected GitHub Actions application.

The repository currently has one owner with write access. Mandatory independent
approvals remain zero to avoid an impossible self-review requirement. CI is
required; it is not human review. Adding a trusted second reviewer can support
an independent-approval policy later. Administrators with permission to edit
repository rules can still change those rules; no absolute immutability claim
is made. GitHub settings are verified separately from this documentation.

## Validation

Regressions cover missing/export-ignored inputs, corrupted downloads, unknown
existing files, links, concurrent writers, atomic publication and archived-source
hash mismatches. Actual release validation builds from a clean archive, checks
bundled sources/tools and GUI startup with isolated preferences, then verifies
published downloads and server-side branch protection.
