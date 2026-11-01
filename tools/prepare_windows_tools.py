"""Developer-only bundling of existing Git and an official Lua 5.3 syntax checker."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path
from urllib.error import URLError

import pefile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "cc2_mce/tools_data"
BUILD = ROOT / ".build-tools"
LUA_SHA256 = "fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    git_cmd = shutil.which("git")
    if git_cmd is None:
        raise RuntimeError("Developer build needs Git for Windows")
    prefix = Path(subprocess.check_output([git_cmd, "--exec-path"], text=True).strip()).parents[1]
    source = prefix / "bin/git.exe"
    if not source.is_file():
        raise RuntimeError("Unsupported developer Git layout")
    git_dir = DEST / "git"
    git_dir.mkdir(exist_ok=True)
    available = {path.name.casefold(): path for path in source.parent.glob("*.dll")}
    pending, copied = [source], set()
    while pending:
        path = pending.pop()
        if path.name.casefold() in copied:
            continue
        copied.add(path.name.casefold())
        shutil.copy2(path, git_dir / path.name)
        image = pefile.PE(str(path))
        for entry in getattr(image, "DIRECTORY_ENTRY_IMPORT", []):
            dependency = available.get(entry.dll.decode("ascii").casefold())
            if dependency is not None:
                pending.append(dependency)
        image.close()
    notices = DEST / "notices"
    notices.mkdir(exist_ok=True)
    shutil.copy2(prefix.parent / "LICENSE.txt", notices / "Git-LICENSE.txt")
    shutil.copytree(prefix / "share/licenses", notices / "Git-dependencies", dirs_exist_ok=True)

    archive = BUILD / "lua-5.3.6.tar.gz"
    if not archive.exists():
        try:
            with urllib.request.urlopen(
                "https://www.lua.org/ftp/lua-5.3.6.tar.gz", timeout=30
            ) as response:
                payload = response.read(1024 * 1024)
        except URLError:
            # Pinned official SHA-256 remains mandatory before any extraction/compilation.
            with urllib.request.urlopen(
                "http://www.lua.org/ftp/lua-5.3.6.tar.gz", timeout=30
            ) as response:
                payload = response.read(1024 * 1024)
        archive.write_bytes(payload)
    if sha(archive) != LUA_SHA256:
        raise RuntimeError("Official Lua archive hash mismatch")
    with tarfile.open(archive) as stream:
        stream.extractall(BUILD, filter="data")
    lua = BUILD / "lua-5.3.6"
    compiler = Path(
        os.environ.get(
            "CC2_MCE_ZIG",
            str(Path.home() / "Documents/CC2 Modding/cc2x/.deps/zig-x86_64-windows-0.15.2/zig.exe"),
        )
    )
    if not compiler.is_file():
        raise RuntimeError("Set CC2_MCE_ZIG to a developer Zig C compiler")
    checker = DEST / "lua/luac.exe"
    checker.parent.mkdir(exist_ok=True)
    sources = sorted(path for path in (lua / "src").glob("*.c") if path.name != "lua.c")
    subprocess.run(
        [
            str(compiler),
            "cc",
            "-target",
            "x86_64-windows-gnu",
            "-O2",
            *map(str, sources),
            "-o",
            str(checker),
        ],
        cwd=BUILD,
        check=True,
        timeout=240,
        env={**os.environ, "ZIG_GLOBAL_CACHE_DIR": str(BUILD / "zig-cache")},
    )
    shutil.copy2(lua / "doc/readme.html", notices / "Lua-5.3.6-readme-license.html")
    shutil.copy2(archive, notices / archive.name)
    for path in checker.parent.glob("*.pdb"):
        path.unlink()
    binaries = [*git_dir.iterdir(), checker]
    manifest = {
        "schema_version": 1,
        "git": "git/git.exe",
        "luac": "lua/luac.exe",
        "git_version": subprocess.check_output(
            [str(git_dir / "git.exe"), "--version"], text=True
        ).strip(),
        "lua_version": "5.3.6",
        "lua_source_sha256": LUA_SHA256,
        "git_source": "https://github.com/git-for-windows/git/tree/v2.56.0.windows.2",
        "files": {path.relative_to(DEST).as_posix(): sha(path) for path in sorted(binaries)},
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"git": manifest["git_version"], "lua": "5.3.6", "files": len(binaries)}))


if __name__ == "__main__":
    main()
