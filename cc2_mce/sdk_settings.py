"""Create missing reviewed SDK settings; preserve user files across rollback."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cc2_mce.errors import InputError
from cc2_mce.filesystem import (
    Budget,
    Limits,
    digest,
    input_root,
    normalize_logical_path,
    read_regular,
)


def _name(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*\.ini", value):
        raise InputError("Invalid reviewed SDK setting filename")
    normalize_logical_path(value)
    return value


def reviewed_defaults(approval: object) -> dict[str, bytes]:
    if not isinstance(approval, dict):
        return {}
    value = approval.get("config_defaults", {})
    if not isinstance(value, dict) or len(value) > 8:
        raise InputError("Invalid reviewed SDK settings")
    result: dict[str, bytes] = {}
    for name, text in value.items():
        name = _name(name)
        if not isinstance(text, str) or "\x00" in text:
            raise InputError("Invalid reviewed SDK setting content")
        data = text.encode("utf-8")
        if len(data) > 16384:
            raise InputError("Reviewed SDK settings exceed size limit")
        result[name] = data
    return {name: result[name] for name in sorted(result)}


def missing(user: Path, defaults: dict[str, bytes]) -> list[str]:
    if not defaults:
        return []
    root = user / "cc2x"
    if root.exists() or root.is_symlink():
        input_root(root)
    result = []
    for name in sorted(defaults):
        path = root / _name(name)
        if path.exists() or path.is_symlink():
            # Only check the boundary; never replace or parse a user's preferences.
            read_regular(path, user, Budget(Limits()))
        else:
            result.append(name)
    return result


def stage(
    user: Path,
    state_dir: Path,
    defaults: dict[str, bytes],
    token: str,
    write_new: Callable[[Path, bytes], None],
) -> list[dict[str, Any]]:
    names = missing(user, defaults)
    if not names:
        return []
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise InputError("Invalid settings transaction identity")
    root = user / "cc2x"
    root.mkdir(exist_ok=True)
    input_root(root)
    records = []
    for index, name in enumerate(names):
        cache = f"config-{token}-{index}.ini"
        source = state_dir / cache
        write_new(source, defaults[name])
        info = source.stat()
        records.append(
            {
                "name": name,
                "cache": cache,
                "sha256": digest(defaults[name]),
                "device": info.st_dev,
                "inode": info.st_ino,
            }
        )
    return records


def install(user: Path, state_dir: Path, records: list[dict[str, Any]]) -> None:
    for record in records:
        source = _cache(state_dir, record["cache"])
        data = read_regular(source, state_dir, Budget(Limits()))
        info = source.stat()
        if digest(data) != record["sha256"] or (info.st_dev, info.st_ino) != (
            record["device"],
            record["inode"],
        ):
            raise InputError("Staged SDK settings changed")
        root = input_root(user / "cc2x")
        # Atomic, full-content, no-overwrite publication. The staged inode was
        # journaled first: a crash/race cannot make another writer's file ours.
        os.link(source, root / _name(record["name"]))


def _cache(state_dir: Path, value: str) -> Path:
    if not re.fullmatch(r"config-[0-9a-f]{32}-[0-9]+\.ini", value):
        raise InputError("Invalid settings cache identity")
    return state_dir / value


def cleanup(
    user: Path, state_dir: Path, records: list[dict[str, Any]], *, remove_targets: bool
) -> None:
    for record in records:
        name = _name(record["name"])
        if remove_targets:
            target = user / "cc2x" / name
            try:
                if target.exists() or target.is_symlink():
                    data = read_regular(target, user, Budget(Limits()))
                    info = target.stat()
                    if digest(data) == record["sha256"] and (info.st_dev, info.st_ino) == (
                        record["device"],
                        record["inode"],
                    ):
                        target.unlink()
            except (OSError, InputError):
                pass  # Preserve changed/inaccessible user files; rollback still proceeds.
        source = _cache(state_dir, record["cache"])
        if source.exists():
            source.unlink()  # Own cache link only; the user settings link survives commit.
