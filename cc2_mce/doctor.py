from __future__ import annotations

import platform
import re
import shutil
import subprocess
from pathlib import Path

from cc2_mce.baseline import load_baseline
from cc2_mce.errors import MCEError
from cc2_mce.filesystem import input_root
from cc2_mce.installation import find_installations
from cc2_mce.reports import envelope


def tool_version(executable: str | None, flag: str) -> tuple[str | None, bool]:
    if not executable:
        return None, False
    try:
        result = subprocess.run(
            [executable, flag], capture_output=True, shell=False, timeout=5, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        text = (result.stdout + result.stderr).decode("utf-8", errors="replace").strip()
        return text[:300], result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return None, False


def steam_workshop_candidates() -> list[Path]:
    return list(find_installations().workshop_roots)


def diagnose(
    *,
    game: Path | None,
    baseline: Path | None,
    game_executable: Path | None,
    luac: str | None,
    git: str | None,
) -> tuple[dict[str, object], int]:
    report = envelope("doctor")
    git_version, git_ok = tool_version(git or shutil.which("git"), "--version")
    lua_path = luac or shutil.which("luac5.3") or shutil.which("luac53") or shutil.which("luac")
    lua_version, lua_available = tool_version(lua_path, "-v")
    lua_ok = lua_available and bool(re.search(r"\bLua 5\.3(?:\.|\s|$)", lua_version or ""))
    report["host"] = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "validation": "local-only",
    }
    report["tools"] = {
        "git": {"available": git_ok, "version": git_version},
        "lua": {
            "available": lua_available,
            "compatible": lua_ok,
            "version": lua_version,
            "required": "5.3",
        },
    }
    blockers: list[dict[str, object]] = []
    exit_code = 0
    if not git_ok or not lua_ok:
        blockers.append({"code": "tool_error", "message": "Git and Lua 5.3 validator are required"})
        exit_code = 5
    if game is not None:
        input_root(game)
        report["game"] = {
            "directory_accessible": True,
            "version": None,
            "warning": "Directory presence is not gameplay/build verification",
        }
    if baseline is not None:
        try:
            loaded = load_baseline(baseline, game_executable=game_executable)
            report["baseline"] = loaded.report()
            report["game"] = loaded.game
        except MCEError as exc:
            blockers.append({"code": "no_base", "message": str(exc)})
            exit_code = max(exit_code, exc.exit_code)
    report.update(blockers=blockers, status="blocked" if blockers else "ok")
    report["warnings"] = [
        "Local diagnostics do not establish Windows/macOS release certification",
        "Game runtime, SDK mapping and packaging still require M0 validation",
    ]
    return report, exit_code
