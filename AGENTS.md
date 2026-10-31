# AGENTS.md — CC2-MCE coding agent guide

> The repository now has a **developer-only read-only discovery/dry-run CLI**, not a ready user application, mod loader or packager. GUI is mandatory for the first user release but not implemented yet. M0 game validation and Windows execution remain unverified. Source of truth: `README.md`, `docs/`, accepted ADRs and regression tests. Specifications are in Russian.

## Goal

Build an offline CC2 Mod Compatibility Engine that merges non-overlapping modifications to the same game files using a verified vanilla baseline and **existing Git three-way merge**, then produces a separate local merged mod. Core motto: «Конфликтуют не файлы, а несовместимые изменения».

## Non-negotiable constraints

1. Read `docs/01-PRODUCT-REQUIREMENTS.md`, `02-ARCHITECTURE.md`, `03-MERGE-SPEC.md`, `04-CC2-INTEGRATION.md` and ADRs before design/code edits.
2. Do not modify vanilla CC2, Mod SDK, subscribed Workshop folders, other authors' mods, `mods.xml`, `dinput8.dll` or executable.
3. No 'last mod wins'. On uncertain merge, missing baseline, native CC2X plugin, unknown binary type, invalid output — **fail closed**.
4. Treat all mod contents and filenames as untrusted input (path traversal/junction/XXE/DoS). Avoid running mod Lua/DLLs in development utilities.
5. Do not pretend CC2X provides a resource-merging hook; first prove it through tests if implementing later.
6. For Lua in MVP, use a real 3-way merge and syntax validation, not invented AST parsing or ad hoc regex merging.
7. For API/schema/behavior changes update specs, JSON contract, tests, relevant ADR, and CHANGELOG once code exists.
8. Do not introduce dependency with incompatible or unclear license. Preserve upstream notices for vendored code.
9. Write regression fixtures for conflicts, N-way, binary, DLL, no-base, path and encoding edge cases before implementation.
10. Every generated output must include source/base/engine hashes and reproducible mod order.
11. Windows and macOS are mandatory MVP host platforms for the complete desktop application, dependencies, validation and staging. Keep behavior consistent and test both; do not equate macOS app support with CC2X or unverified game runtime support. See [ADR-0005](docs/adr/0005-windows-macos-support.md).
12. User workflows MUST be GUI-only: no terminal/commands, manual Python/Git/Lua installs, PATH setup or editing technical configs/manifests. Ship verified tools with the app; keep CLI for development/CI only. Basic GUI is P0, not future polish. Follow [UX/UI](docs/13-UX-UI.md) and [ADR-0007](docs/adr/0007-gui-first-user-experience.md); never claim the current CLI prototype meets the user release gate.

## Suggested first steps

1. Perform the M0 validation against a **real installed game and legitimate sample mods**. If those are unavailable, use synthetic fixtures and mark assumptions unverified; don't fabricate gameplay test results.
2. Choose fork vs adapter on w3scriptmerge. Don't blindly copy Witcher-specific logic.
3. Implement CLI `doctor` and `scan` with strict path normalization.
4. Add baseline matching and `git merge-file -p` adapter with testable subprocess boundary.
5. Build JSON report before producing a game-loadable package.

## Coding conventions (proposed)

- Python 3.12+ if available on supported Windows and macOS versions/CPU architectures; confirm the runtime matrix in M0. Use type hints, pathlib, dataclasses/Pydantic if justified, pytest, Ruff, `subprocess.run(..., shell=False)`.
- Keep `domain/` pure; filesystem/Steam/Git interactions through ports.
- Prefer small deterministic functions and explicit status enums to magic strings.
- Every merge function returns a structured result and never silently discards an input.

## Local validation

- `uv sync --frozen --extra dev`, then `uv run pytest -q`, `uv run ruff check cc2_mce tests`, `uv run mypy cc2_mce`.
- `uv run cc2-mce --config examples/mce.synthetic.toml build --dry-run` is synthetic only; never report it as game acceptance.
- `build` without `--dry-run` and plan replay are deliberately blocked. See [ADR-0006](docs/adr/0006-read-only-first-slice.md).

## Definition of Done

Read `docs/06-TEST-STRATEGY.md`. Completing code without test fixture + report metadata + updated docs is not done.
