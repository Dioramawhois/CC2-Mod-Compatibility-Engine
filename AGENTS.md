# AGENTS.md — CC2-MCE coding agent guide

> Version 0.2.0 has a Windows GUI, verified Git/Lua packaging and reversible activation for reviewed game/runtime/native profiles. AI Bridge + Island Airfields reached the game menu with a fresh plugin-load log; full gameplay, clean-machine and macOS release gates remain unverified. Do not disable the working GUI as if the historical read-only slice were current. Source of truth: README, docs, ADR-0009 and tests; specifications are in Russian.

## Goal

Brand/languages 0.3.1 (ADR-0013): user-facing product is CC2 ModLoader, canonical executable CC2ModLoader.exe. Generated game mod names include the selected mod names. Ship 14 complete offline catalogs (RU/EN/DE/FR/ES/PT-BR/IT/PL/TR/UK/zh-CN/zh-TW/JA/KO); default follows the system, explicit language is persisted. Core owner/folder/schema identities remain stable. Do not send user mod content or paths to translation services.

Owner update 0.3.0 (ADR-0012): GUI has an editable, persistent merge order and ordered patch priority enabled by default. Use installed originals without a preapproved per-file hash list; overlapping hunks favor the later patch explicitly, and missing-base data uses a reported whole-file replacement. This explicit owner request supersedes the older blanket no-base/no-priority constraints for data resources. Never invent a baseline or bypass native/path/syntax safety. Default UI language follows the system with RU/EN choices; selected tabs must be larger than inactive ones.

UX 0.2.2: a rejected checkbox change must restore the actual applied selection and allow launching the intact working set. Explain the rejected mod/participants inline; preserve the notice during passive scans. Prepare only the selected verified game's mods/libraries automatically; no preparation button. Keep the main screen to the list, result and Launch; secondary operations live in one menu. ADR-0011 supersedes the older explicit preparation and retained rejected-selection behavior.

Current user workflow (0.2.1): a checkbox is the authorized apply action, with automatic check/merge/activation, no extra confirmation or check/apply buttons. Maintain one fixed `mods/CC2-MCE` output with transactional folder/config rollback and closed-game deferral. This explicit owner request supersedes older confirmation/hash-output instructions; see ADR-0010. Preserve all source/native safety gates.

Build an offline CC2 Mod Compatibility Engine that merges non-overlapping modifications to the same game files using a verified vanilla baseline and **existing Git three-way merge**, then produces a separate local merged mod. Core motto: «Конфликтуют не файлы, а несовместимые изменения».

## Non-negotiable constraints

1. Read `docs/01-PRODUCT-REQUIREMENTS.md`, `02-ARCHITECTURE.md`, `03-MERGE-SPEC.md`, `04-CC2-INTEGRATION.md` and ADRs before design/code edits.
2. Do not modify vanilla CC2, Mod SDK, subscribed Workshop folders, other authors' mods or the game executable. Changes to mods.xml and installation of a hash-reviewed, user-provided dinput8.dll are permitted only through the explicitly confirmed reversible GUI workflow, or a real-game test expressly requested by the user (ADR-0009). Never overwrite an unknown installed loader.
3. No 'last mod wins'. On uncertain merge, missing baseline, unreviewed native CC2X plugin, unknown binary type, invalid output — **fail closed**. Reviewed plugins may be copied byte-identically for their approved game/runtime; DLLs are never merged.
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
- Legacy CLI/raw payload is a developer adapter, not the GUI package publisher. Plan replay remains unsupported. Schema v1 stays non-installable; GUI package/activation uses schema v2 and ADR-0009, which supersedes the historical read-only limitations of ADR-0006.

## Definition of Done

Read `docs/06-TEST-STRATEGY.md`. Completing code without test fixture + report metadata + updated docs is not done.
