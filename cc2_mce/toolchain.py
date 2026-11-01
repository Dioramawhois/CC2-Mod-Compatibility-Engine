"""Hash-verified bundled tools; the player never supplies executables through PATH."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from cc2_mce.errors import InputError, ToolError
from cc2_mce.filesystem import (
    Budget,
    Limits,
    digest,
    input_root,
    normalize_logical_path,
    read_regular,
)


@dataclass(frozen=True)
class Toolchain:
    git: Path
    luac: Path
    manifest_sha256: str


def bundled_tools() -> Toolchain:
    try:
        root = input_root(Path(__file__).parent / "tools_data")
        budget = Budget(Limits(max_file_bytes=32 * 1024 * 1024))
        raw = read_regular(root / "manifest.json", root, budget)
        manifest = json.loads(raw)
        if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
            raise ToolError("Invalid bundled tool manifest")
        for name, expected in manifest["files"].items():
            logical, _ = normalize_logical_path(name)
            if digest(read_regular(root / logical, root, budget)) != expected:
                raise ToolError("Bundled tool integrity check failed")
        for key in ("git", "luac"):
            if manifest[key] not in manifest["files"]:
                raise ToolError("Bundled tool missing from integrity manifest")
        return Toolchain(root / manifest["git"], root / manifest["luac"], digest(raw))
    except (OSError, ValueError, KeyError, InputError) as exc:
        raise ToolError("Bundled Git/Lua tools are unavailable") from exc


def verify_bundle() -> dict[str, object]:
    """Developer/CI smoke inside the frozen executable; never executes mod Lua."""
    from cc2_mce.merge import GitMergeAdapter
    from cc2_mce.validation import validate_content

    tools = bundled_tools()
    git = subprocess.run(
        [str(tools.git), "--version"],
        capture_output=True,
        check=True,
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    result = GitMergeAdapter(str(tools.git)).merge(
        b"a=2\n\n\nb=1\n", b"a=1\n\n\nb=1\n", b"a=1\n\n\nb=2\n"
    )
    if result.content != b"a=2\n\n\nb=2\n":
        raise ToolError("Bundled Git merge smoke failed")
    valid = validate_content("test.lua", b'error("must not execute")\n', luac=str(tools.luac))
    invalid = validate_content("test.lua", b"function(\n", luac=str(tools.luac))
    if valid[0] != "valid" or invalid[0] != "validation_error":
        raise ToolError("Bundled Lua syntax-only smoke failed")
    return {
        "git": git.stdout.decode().strip(),
        "lua": "5.3.6",
        "manifest_sha256": tools.manifest_sha256,
        "merge": "clean",
        "syntax_only": True,
    }
