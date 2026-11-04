from __future__ import annotations

import shutil
from collections import defaultdict

from cc2_mce.baseline import Baseline
from cc2_mce.discovery import FileRef, ModRef, Scan, fingerprint, snapshot_unchanged
from cc2_mce.doctor import tool_version
from cc2_mce.errors import InputError
from cc2_mce.filesystem import RESOURCE_LIMITS, digest
from cc2_mce.merge import GitMergeAdapter, MergeInput, merge_file
from cc2_mce.reports import envelope
from cc2_mce.resources import validate_selection_resources


def plan(
    scan: Scan,
    selected: list[ModRef],
    baseline: Baseline | None,
    *,
    command: str,
    luac: str | None = None,
    git_executable: str | None = None,
) -> tuple[dict[str, object], int, dict[str, bytes]]:
    if not selected or len(selected) > scan.limits.max_variants:
        raise InputError("Select 1..32 mods explicitly")
    validate_selection_resources(selected, limits=RESOURCE_LIMITS)
    report = envelope(command)
    report["mod_order"] = [mod.id for mod in selected]
    report["sources"] = [mod.report() for mod in selected]
    report["game"] = baseline.game if baseline else None
    report["baseline"] = baseline.report() if baseline else None
    # Use the existing Git three-way implementation; no alternative merge fallback.
    git_version, _ = tool_version(GitMergeAdapter(git_executable).executable, "--version")
    lua_path = luac or shutil.which("luac5.3") or shutil.which("luac53") or shutil.which("luac")
    lua_version, _ = tool_version(lua_path, "-v")
    report["tools"] = {"git": {"version": git_version}, "lua": {"version": lua_version}}
    report["policies"] = {
        "strict_validation": True,
        "native_plugin_policy": "block",
        "binary_conflict_policy": "block",
        "text_encoding": "utf-8",
    }
    groups: dict[str, list[tuple[ModRef, FileRef]]] = defaultdict(list)
    for mod in selected:
        for item in mod.files:
            groups[item.key].append((mod, item))
    files: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    blockers: list[dict[str, object]] = []
    outputs: dict[str, bytes] = {}
    exit_code = 0
    for key in sorted(groups):
        participants = groups[key]
        logical_path = participants[0][1].logical_path
        base = baseline.content_for(logical_path) if baseline else None
        outcome = merge_file(
            logical_path,
            [MergeInput(mod.id, item.content) for mod, item in participants],
            base,
            baseline_verified=bool(baseline and baseline.verified_for(logical_path)),
            git=GitMergeAdapter(git_executable),
            luac=luac,
        )
        conflict_ids = []
        for conflict in outcome.conflicts:
            conflict_id = f"c-{len(conflicts) + 1:04d}"
            conflict_ids.append(conflict_id)
            conflicts.append({**conflict, "id": conflict_id, "file": logical_path})
        files.append(
            {
                "logical_path": logical_path,
                "strategy": outcome.strategy,
                "status": outcome.status,
                "sources": [mod.id for mod, _ in participants],
                "source_sha256": {mod.id: item.sha256 for mod, item in participants},
                "baseline_sha256": digest(base) if base is not None else None,
                "output_sha256": digest(outcome.content) if outcome.content is not None else None,
                "conflict_ids": conflict_ids,
                "diagnostics": list(outcome.diagnostics),
            }
        )
        if outcome.status in {"clean", "copied", "identical"} and outcome.content is not None:
            outputs[logical_path] = outcome.content
        if outcome.status not in {"clean", "copied", "identical"}:
            code = {"no_base": 3, "input_error": 4, "tool_error": 5}.get(outcome.status, 2)
            exit_code = max(exit_code, code)
            blockers.append({"code": outcome.status, "file": logical_path})
    if not snapshot_unchanged(scan) or (baseline and not baseline.unchanged()):
        blockers.append({"code": "input_error", "message": "Inputs changed during analysis"})
        exit_code = max(exit_code, 4)
    report.update(
        files=files, conflicts=conflicts, blockers=blockers, status="blocked" if blockers else "ok"
    )
    # Written only when the whole plan is clean; never persisted into the report.
    report_outputs = outputs if not blockers else {}
    report["build_id"] = fingerprint(
        {
            "engine": report["engine_sha256"],
            "sources": [(m.id, m.sha256) for m in selected],
            "baseline": baseline.fingerprint if baseline else None,
            "files": files,
            "tools": report["tools"],
            "policies": report["policies"],
        }
    )
    warnings = [
        "Analysis only: no installable package was created",
        "Clean text merge does not prove gameplay compatibility",
    ]
    if baseline and baseline.kind == "synthetic":
        warnings.append("Synthetic baseline: game compatibility is unverified")
    report["warnings"] = warnings
    return report, exit_code, report_outputs
