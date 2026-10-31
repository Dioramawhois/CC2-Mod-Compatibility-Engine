"""Built-in three-way line merge: no external git, identical on every OS.

Both sides are compared to the base line by line. Non-overlapping edits combine;
an overlapping edit that both sides made differently is a conflict. Never picks a winner.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass(frozen=True)
class TextMergeResult:
    status: str  # "clean" or "conflict"
    content: bytes | None = None


def _changes(base: list[bytes], side: list[bytes]) -> list[tuple[int, int, list[bytes]]]:
    """Hunks as (base_start, base_end, replacement) against the base."""
    matcher = difflib.SequenceMatcher(a=base, b=side, autojunk=False)
    return [
        (i1, i2, side[j1:j2])
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    ]


def merge_lines(ours: bytes, base: bytes, theirs: bytes) -> TextMergeResult:
    base_lines = base.splitlines(keepends=True)
    our_lines = ours.splitlines(keepends=True)
    their_lines = theirs.splitlines(keepends=True)
    our_hunks = _changes(base_lines, our_lines)
    their_hunks = _changes(base_lines, their_lines)

    merged: list[bytes] = []
    cursor = 0
    oi = ti = 0
    while oi < len(our_hunks) or ti < len(their_hunks):
        o = our_hunks[oi] if oi < len(our_hunks) else None
        t = their_hunks[ti] if ti < len(their_hunks) else None
        if t is None:
            assert o is not None
            pick, side = o, "ours"
        elif o is None:
            pick, side = t, "theirs"
        elif o[1] <= t[0]:
            pick, side = o, "ours"
        elif t[1] <= o[0]:
            pick, side = t, "theirs"
        elif o == t:
            pick, side = o, "both"  # identical change on both sides: take once
        else:
            return TextMergeResult("conflict")
        start, end, repl = pick
        merged.extend(base_lines[cursor:start])
        merged.extend(repl)
        cursor = end
        if side in ("ours", "both"):
            oi += 1
        if side in ("theirs", "both"):
            ti += 1
    merged.extend(base_lines[cursor:])
    return TextMergeResult("clean", b"".join(merged))
