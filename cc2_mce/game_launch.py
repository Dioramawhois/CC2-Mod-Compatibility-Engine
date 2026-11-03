"""Start the verified local game executable with only the prepared activation."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cc2_mce.errors import InputError
from cc2_mce.filesystem import Budget, Limits, digest, input_root, is_link, read_regular
from cc2_mce.installation import Installation
from cc2_mce.workflow import _running, _verified_package, active_paths


def launch_game(
    game: Installation,
    user_dir: Path,
    package: Path | None,
    *,
    spawn: Callable[..., Any] = subprocess.Popen,
    game_running: Callable[[], bool] = _running,
) -> None:
    root = input_root(game.root)
    executable = game.executable
    if executable not in (
        root / "carrier_command.exe",
        root / "carriercommand.app/Contents/MacOS/build_mac",
    ):
        raise InputError("Unexpected game executable")
    input_root(executable.parent)
    if is_link(executable) or not executable.is_file() or game_running():
        raise InputError("Game is running or its executable is unavailable")
    expected = (package,) if package is not None else ()
    if active_paths(user_dir) != expected:
        raise InputError("Game activation changed; rebuild the selected set")
    if package is not None:
        if package != user_dir / "mods/CC2-MCE":
            raise InputError("Unexpected managed package path")
        report = _verified_package(package)
        if digest(read_regular(executable, root, Budget(Limits()))) != report["game_sha256"]:
            raise InputError("Game executable changed since activation")
        runtime_hash = report.get("runtime_sha256")
        if runtime_hash and digest(read_regular(root / "dinput8.dll", root, Budget(Limits()))) != (
            runtime_hash
        ):
            raise InputError("Installed runtime changed since activation")
    spawn([str(executable)], cwd=str(root), shell=False)
