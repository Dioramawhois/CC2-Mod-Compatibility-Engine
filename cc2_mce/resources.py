"""Bound selected payloads before loading any lazy resource content."""

from __future__ import annotations

from collections.abc import Iterable

from cc2_mce.discovery import ModRef
from cc2_mce.filesystem import RESOURCE_LIMITS, Budget, Limits


def validate_selection_resources(
    selected: Iterable[ModRef], *, limits: Limits = RESOURCE_LIMITS
) -> None:
    budget = Budget(limits)
    text_limits = Limits()
    for mod in selected:
        budget.consume(len(mod.metadata), label=mod.id + "/mod.xml")
        for item in (*mod.files, *mod.root_files):
            label = mod.id + "/" + item.logical_path
            budget.consume(item.size, label=label)
            if item.kind == "text" or item.logical_path.casefold().endswith(".json"):
                Budget(text_limits).consume(item.size, label=label)
