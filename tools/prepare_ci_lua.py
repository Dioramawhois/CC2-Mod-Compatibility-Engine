"""Build official hash-pinned Lua for CI fixtures, never user mod scripts.

This is a CI dependency, independent of the pinned tools shipped to players.
Lua 5.3.6 uses the MIT license retained in its official source archive.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

URL = "https://www.lua.org/ftp/lua-5.3.6.tar.gz"
SHA256 = "fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    build = root / "build"
    build.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="ci-lua53-", dir=build))
    with urllib.request.urlopen(URL, timeout=45) as response:
        payload = response.read(303771)
    if len(payload) != 303770 or hashlib.sha256(payload).hexdigest() != SHA256:
        raise ValueError("Official Lua source size/checksum mismatch")
    # Read only bounded, flat regular source files; no archive extraction.
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive.getmembers():
            prefix = "lua-5.3.6/src/"
            if not member.name.startswith(prefix) or not member.isfile():
                continue
            name = member.name[len(prefix) :]
            if "/" in name or "\\" in name or Path(name).suffix not in {".c", ".h"}:
                continue
            if member.size > 262144:
                raise ValueError("Unexpected Lua source file size")
            stream = archive.extractfile(member)
            assert stream is not None
            (work / name).write_bytes(stream.read(262145))
        notice = archive.extractfile("lua-5.3.6/doc/readme.html")
        assert notice is not None
        (work / "Lua-README-license.html").write_bytes(notice.read(131072))
    compiler = shutil.which("clang") or shutil.which("gcc") or shutil.which("cc")
    if not compiler:
        raise ValueError("CI needs its preinstalled C compiler")
    common = [str(p) for p in sorted(work.glob("*.c")) if p.name not in {"lua.c", "luac.c"}]
    if len(common) != 33:
        raise ValueError("Unexpected official Lua source inventory")
    binary = work / "bin"
    binary.mkdir()
    suffix = ".exe" if sys.platform == "win32" else ""
    for name in ("lua", "luac"):
        command = [
            compiler,
            "-O2",
            "-I",
            str(work),
            *common,
            str(work / (name + ".c")),
            "-o",
            str(binary / (name + suffix)),
        ]
        if sys.platform != "win32":
            command.append("-lm")
        subprocess.run(command, check=True, timeout=120, shell=False)
        subprocess.run([str(binary / (name + suffix)), "-v"], check=True, timeout=10, shell=False)
    if path_file := os.environ.get("GITHUB_PATH"):
        with open(path_file, "a", encoding="utf-8") as stream:
            stream.write(str(binary) + "\n")
    print("Verified Lua 5.3.6 interpreter and validator: " + str(binary))


if __name__ == "__main__":
    main()
