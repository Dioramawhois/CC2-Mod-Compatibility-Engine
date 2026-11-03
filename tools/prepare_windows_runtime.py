"""Restore the reviewed SDK build dependency; never install into or start the game."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from cc2_mce.filesystem import Budget, Limits, input_root, read_regular

MAX_RUNTIME_BYTES = 8 * 1024 * 1024


def install_pinned_runtime(root: Path, supplied_file: Path | None = None) -> None:
    """Hydrate export-ignored SDK bytes for a source build, preserving unknown files."""
    root = input_root(root)
    budget = Budget(Limits(max_file_bytes=65536, max_total_bytes=131072))
    lock = json.loads(read_regular(root / "distribution/windows-runtime.json", root, budget))
    profile = json.loads(
        read_regular(root / "cc2_mce/profiles/windows-1.5.18-r2.json", root, budget)
    )
    if (
        lock.get("schema_version") != 1
        or lock.get("file") != "dinput8.dll"
        or not isinstance(lock.get("sha256"), str)
        or not re.fullmatch("[a-f0-9]{64}", lock["sha256"])
        or profile.get("runtime_sha256") != lock["sha256"]
        or type(lock.get("bytes")) is not int
        or not 0 < lock["bytes"] <= MAX_RUNTIME_BYTES
    ):
        raise ValueError("Reviewed Windows runtime lock does not match the game profile")
    url = urllib.parse.urlparse(lock.get("url", ""))
    if (
        url.scheme != "https"
        or url.hostname != "github.com"
        or url.username is not None
        or url.password is not None
        or url.port not in (None, 443)
        or not url.path.startswith("/Dioramawhois/Carrier-Command-2-extender/releases/download/")
        or not url.path.endswith("/dinput8.dll")
        or url.query
        or url.fragment
    ):
        raise ValueError("Reviewed Windows runtime URL is not a pinned HTTPS release asset")
    folder = input_root(root / "cc2_mce/runtime_data" / lock["sha256"])
    destination = folder / "dinput8.dll"

    def verify(data: bytes, *, existing: bool = False) -> None:
        if len(data) != lock["bytes"] or hashlib.sha256(data).hexdigest() != lock["sha256"]:
            if existing:
                raise ValueError("Unknown existing SDK build dependency was preserved")
            raise ValueError("Reviewed Windows runtime size/checksum mismatch")

    def verify_existing() -> None:
        verify(
            read_regular(destination, folder, Budget(Limits(max_file_bytes=MAX_RUNTIME_BYTES))),
            existing=True,
        )

    if destination.exists() or destination.is_symlink():
        verify_existing()
        print("Verified the existing reviewed Windows SDK build dependency")
        return
    if supplied_file is not None:
        supplied_file = supplied_file.absolute()
        data = read_regular(
            supplied_file,
            input_root(supplied_file.parent),
            Budget(Limits(max_file_bytes=MAX_RUNTIME_BYTES)),
        )
    else:
        with urllib.request.urlopen(lock["url"], timeout=45) as response:
            data = response.read(lock["bytes"] + 1)
    verify(data)
    temporary = folder / (".dinput8-" + uuid.uuid4().hex + ".tmp")
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        input_root(folder)
        try:
            # A same-directory hard link publishes a complete regular file
            # atomically and refuses to replace a concurrently created file.
            os.link(temporary, destination)
        except FileExistsError:
            verify_existing()
    finally:
        if created:
            temporary.unlink(missing_ok=True)
    verify_existing()
    print("Restored the reviewed Windows SDK build dependency")


def main() -> None:
    supplied = os.environ.get("CC2_MCE_RUNTIME_FILE")
    install_pinned_runtime(
        Path(__file__).resolve().parents[1], Path(supplied) if supplied is not None else None
    )


if __name__ == "__main__":
    main()
