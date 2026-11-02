from __future__ import annotations

import difflib
import itertools
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cc2_mce.filesystem import classify
from cc2_mce.textmerge import merge_lines
from cc2_mce.validation import decode_text, has_conflict_markers, validate_content


@dataclass(frozen=True)
class MergeInput:
    mod_id: str
    content: bytes


@dataclass(frozen=True)
class MergeOutcome:
    status: str
    strategy: str
    content: bytes | None = None
    diagnostics: tuple[str, ...] = ()
    conflicts: tuple[dict[str, object], ...] = ()


class BuiltinMergeAdapter:
    """Default three-way merge: pure Python, no external git, same result on every OS."""

    def merge(self, ours: bytes, base: bytes, theirs: bytes) -> MergeOutcome:
        result = merge_lines(ours, base, theirs)
        if result.status == "clean":
            return MergeOutcome("clean", "text-3way", result.content)
        return MergeOutcome("conflict", "text-3way")


class GitMergeAdapter:
    def __init__(self, executable: str | None = None, timeout: float = 10.0) -> None:
        self.executable = executable or shutil.which("git") or "git"
        self.timeout = timeout

    def merge(
        self, ours: bytes, base: bytes, theirs: bytes, *, favor_theirs: bool = False
    ) -> MergeOutcome:
        try:
            with tempfile.TemporaryDirectory(prefix="cc2-mce-merge-") as temporary:
                paths = [Path(temporary) / name for name in ("ours", "base", "theirs")]
                for path, content in zip(paths, (ours, base, theirs), strict=True):
                    path.write_bytes(content)
                command = [
                    self.executable,
                    "merge-file",
                    "-p",
                    "--diff3",
                    *(["--theirs"] if favor_theirs else []),
                    "-L",
                    "OURS",
                    "-L",
                    "BASE",
                    "-L",
                    "THEIRS",
                    *map(str, paths),
                ]
                result = subprocess.run(
                    command,
                    capture_output=True,
                    shell=False,
                    timeout=self.timeout,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            if result.returncode == 0:
                return MergeOutcome("clean", "text-3way", result.stdout)
            if 1 <= result.returncode <= 127:
                return MergeOutcome("conflict", "text-3way")
            return MergeOutcome("tool_error", "text-3way", diagnostics=("Git merge-file failed",))
        except (OSError, subprocess.TimeoutExpired):
            return MergeOutcome(
                "tool_error", "text-3way", diagnostics=("Git unavailable or timeout",)
            )


def _conflict_kind(base: bytes, left: bytes, right: bytes) -> str:
    original = base.decode("utf-8-sig").splitlines(keepends=True)
    if max(len(base), len(left), len(right)) > 256 * 1024 or len(original) > 2000:
        return "edit_edit_conflict"
    edits = []
    for data in (left, right):
        lines = data.decode("utf-8-sig").splitlines(keepends=True)
        edits.append(
            [
                op
                for op in difflib.SequenceMatcher(
                    None, original, lines, autojunk=True
                ).get_opcodes()
                if op[0] != "equal"
            ]
        )
    for a, b in itertools.product(*edits):
        if "delete" in (a[0], b[0]) and max(a[1], b[1]) < min(a[2], b[2]):
            return "delete_modify_conflict"
    return "edit_edit_conflict"


def merge_file(
    logical_path: str,
    variants: Sequence[MergeInput],
    base: bytes | None,
    *,
    baseline_verified: bool = False,
    git: GitMergeAdapter | None = None,
    luac: str | None = None,
    canonical_eol: bool = False,
    favor_later: bool = False,
) -> MergeOutcome:
    strategy = "text-3way"
    if not variants or len(variants) > 32:
        return MergeOutcome("input_error", "none", diagnostics=("Expected 1..32 variants",))
    kinds = {classify(logical_path, item.content) for item in variants}
    kind = classify(logical_path, variants[0].content)
    if "native" in kinds:
        return MergeOutcome("native_plugin_review_required", "blocked")
    if "unknown" in kinds:
        return MergeOutcome("needs_review", "unsupported", diagnostics=("Unknown resource type",))
    unique = []
    seen: set[bytes] = set()
    for item in reversed(variants) if favor_later else variants:
        if item.content not in seen:
            seen.add(item.content)
            unique.append(item)
    if favor_later:
        unique.reverse()
    if len(unique) == 1:
        content = unique[0].content
        status, strategy = (
            ("copied", "copy") if len(variants) == 1 else ("identical", "deduplicate")
        )
    elif favor_later and (kind == "binary" or not baseline_verified or base is None):
        content = variants[-1].content
        status = "overridden"
        strategy = (
            "ordered-binary-replacement" if kind == "binary" else "ordered-replacement-no-base"
        )
    elif kind == "binary":
        return MergeOutcome("unsupported_binary", "blocked")
    else:
        if not baseline_verified:
            return MergeOutcome("no_base", strategy)
        if base is None:
            conflict: dict[str, object] = {
                "kind": "add_add_conflict",
                "mods": [item.mod_id for item in variants],
                "resolution": "unresolved",
            }
            return MergeOutcome("conflict", strategy, conflicts=(conflict,))
        try:
            decoded = [decode_text(item.content) for item in unique]
            decoded.append(decode_text(base))
            formats = [item[1] for item in decoded]
            if len({fmt.bom for fmt in formats}) != 1 or (
                not canonical_eol and len(set(formats)) != 1
            ):
                raise ValueError("Encoding/EOL disagreement")
            for text, _ in decoded:
                if has_conflict_markers(text):
                    return MergeOutcome(
                        "validation_error",
                        strategy,
                        diagnostics=("Conflict markers in source/base",),
                    )
        except (UnicodeError, ValueError):
            return MergeOutcome("encoding_conflict", strategy)
        if canonical_eol:
            unique = [
                MergeInput(item.mod_id, item.content.replace(b"\r\n", b"\n")) for item in unique
            ]
            base = base.replace(b"\r\n", b"\n")
        adapter = git or GitMergeAdapter()
        resolved_conflicts = False
        for left, right in itertools.combinations(unique, 2):
            preflight = adapter.merge(left.content, base, right.content)
            if preflight.status == "conflict":
                if favor_later:
                    resolved_conflicts = True
                    continue
                conflict = {
                    "kind": _conflict_kind(base, left.content, right.content),
                    "mods": [left.mod_id, right.mod_id],
                    "resolution": "unresolved",
                }
                return MergeOutcome("conflict", strategy, conflicts=(conflict,))
            if preflight.status != "clean":
                return preflight
        content = unique[0].content
        for item in unique[1:]:
            merged = adapter.merge(content, base, item.content)
            if merged.status == "conflict" and favor_later:
                resolved_conflicts = True
                merged = adapter.merge(content, base, item.content, favor_theirs=True)
            if merged.status != "clean" or merged.content is None:
                if merged.status == "conflict":
                    conflict = {
                        "kind": "edit_edit_conflict",
                        "mods": [v.mod_id for v in unique],
                        "resolution": "unresolved",
                    }
                    return MergeOutcome("conflict", strategy, conflicts=(conflict,))
                return merged
            content = merged.content
        status = "overridden" if resolved_conflicts else "clean"
        if resolved_conflicts:
            strategy = "git-three-way-later-hunks"
    if kind == "text":
        validation_status, diagnostic = validate_content(logical_path, content, luac=luac)
        if validation_status != "valid":
            return MergeOutcome(validation_status, strategy, diagnostics=(diagnostic,))
    return MergeOutcome(status, strategy, content)
