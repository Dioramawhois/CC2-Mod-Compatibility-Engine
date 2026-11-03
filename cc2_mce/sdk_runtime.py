"""Journaled installation/upgrade of an exact reviewed runtime; never load it."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cc2_mce.errors import InputError
from cc2_mce.filesystem import Budget, Limits, digest, input_root, read_regular
from cc2_mce.installation import Installation


def _read(path: Path, root: Path) -> bytes:
    return read_regular(path, root, Budget(Limits()))


def stage(
    game: Installation,
    source: Path | None,
    profile: dict[str, Any],
    state_dir: Path,
    token: str,
    write_new: Callable[[Path, bytes], None],
) -> dict[str, Any] | None:
    if source is None:
        return None
    target = game.root / "dinput8.dll"
    old = _read(target, game.root) if target.exists() or target.is_symlink() else None
    expected = profile["runtime_sha256"]
    if old is not None and digest(old) == expected:
        return None
    if old is not None and digest(old) not in profile.get("previous_runtime_sha256", []):
        raise InputError("Unknown installed runtime; update refused")
    data = _read(source, input_root(source.parent))
    if digest(data) != expected:
        raise InputError("Reviewed runtime source changed")
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise InputError("Invalid runtime transaction identity")
    cache = "runtime-" + token + ".dll"
    if old is not None:
        write_new(state_dir / cache, old)
    # Same filesystem as target: publication is atomic. No active filename yet.
    temporary = game.root / (".cc2-mce-runtime-" + token + ".dll")
    write_new(temporary, data)
    info = temporary.stat()
    return {
        "game_root": str(game.root),
        "executable": game.executable.name,
        "game_sha256": profile["game_sha256"],
        "temporary": temporary.name,
        "backup": cache if old is not None else None,
        "old_sha256": digest(old) if old is not None else None,
        "new_sha256": expected,
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def _paths(record: dict[str, Any]) -> tuple[Path, Path, Path]:
    root = input_root(Path(record["game_root"]))
    executable = record["executable"]
    if executable != Path(executable).name or "/" in executable or "\\" in executable:
        raise InputError("Invalid runtime executable identity")
    if digest(_read(root / executable, root)) != record["game_sha256"]:
        raise InputError("Game changed; runtime restoration stopped")
    name = record["temporary"]
    if not re.fullmatch(r"\.cc2-mce-runtime-[0-9a-f]{32}\.dll", name):
        raise InputError("Invalid staged runtime identity")
    return root, root / "dinput8.dll", root / name


def install(record: dict[str, Any] | None) -> None:
    if record is None:
        return
    root, target, temporary = _paths(record)
    info = temporary.stat()
    if digest(_read(temporary, root)) != record["new_sha256"] or (
        info.st_dev,
        info.st_ino,
    ) != (record["device"], record["inode"]):
        raise InputError("Staged runtime changed")
    if record["old_sha256"] is None:
        os.link(temporary, target)  # Atomic create, never overwrite a racing writer.
        temporary.unlink()
    else:
        if digest(_read(target, root)) != record["old_sha256"]:
            raise InputError("Installed runtime changed; upgrade stopped")
        os.replace(temporary, target)


def rollback(
    record: dict[str, Any] | None,
    state_dir: Path,
    replace_checked: Callable[[Path, bytes, bytes], None],
) -> None:
    if record is None:
        return
    root, target, temporary = _paths(record)
    current = _read(target, root) if target.exists() or target.is_symlink() else None
    current_hash = digest(current) if current is not None else None
    if current_hash == record["old_sha256"]:
        pass  # Not installed yet, or a previous recovery already restored it.
    elif current_hash == record["new_sha256"]:
        info = target.stat()
        if (info.st_dev, info.st_ino) != (record["device"], record["inode"]):
            raise InputError("Runtime replaced externally; automatic restoration stopped")
        if record["backup"] is None:
            target.unlink()
        else:
            name = record["backup"]
            if not re.fullmatch(r"runtime-[0-9a-f]{32}\.dll", name):
                raise InputError("Invalid runtime backup identity")
            old = _read(state_dir / name, state_dir)
            if digest(old) != record["old_sha256"]:
                raise InputError("Runtime backup damaged")
            assert current is not None
            replace_checked(target, old, current)
    else:
        raise InputError("Runtime changed externally; automatic restoration stopped")
    if temporary.exists():
        info = temporary.stat()
        if digest(_read(temporary, root)) != record["new_sha256"] or (
            info.st_dev,
            info.st_ino,
        ) != (record["device"], record["inode"]):
            raise InputError("Staged runtime changed externally")
        temporary.unlink()
