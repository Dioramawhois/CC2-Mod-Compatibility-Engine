"""Restore the pinned release toolchain on a developer machine; never runs mod code."""

from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path

from cc2_mce.errors import InputError
from cc2_mce.filesystem import input_root, normalize_logical_path


def unpack_verified(payload: bytes, expected: str, destination: Path) -> None:
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("Pinned Windows toolchain checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = []
        seen = set()
        total = 0
        if len(archive.infolist()) > 10000:
            raise ValueError("Tool archive file limit")
        for entry in archive.infolist():
            name = entry.orig_filename.removesuffix("/")
            if (
                not name.startswith("tools_data/")
                or (entry.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Unexpected tool archive root/link")
            try:
                relative, key = normalize_logical_path(name[len("tools_data/") :])
            except InputError as exc:
                raise ValueError("Unsafe tool archive name") from exc
            if key in seen or entry.file_size > 32 * 1024 * 1024:
                raise ValueError("Tool archive collision/size limit")
            seen.add(key)
            total += entry.file_size
            if total > 128 * 1024 * 1024:
                raise ValueError("Tool archive total size limit")
            if not entry.is_dir():
                entries.append((entry, relative))
        input_root(destination.parent)
        destination.mkdir(exist_ok=True)
        input_root(destination)
        for entry, relative in entries:
            path = destination / relative
            current = destination
            for part in Path(relative).parts[:-1]:
                current /= part
                current.mkdir(exist_ok=True)
                input_root(current)
            if path.is_symlink():
                raise ValueError("Tool output link forbidden")
            path.write_bytes(archive.read(entry))


def install_pinned_tools(root: Path, destination: Path) -> None:
    lock = json.loads((root / "distribution/windows-build-tools.json").read_text(encoding="utf-8"))
    cache = root / ".build-tools"
    cache.mkdir(exist_ok=True)
    source = Path(os.environ.get("CC2_MCE_TOOLS_ARCHIVE", str(cache / lock["file"])))
    if not source.exists():
        if "CC2_MCE_TOOLS_ARCHIVE" in os.environ:
            raise ValueError("Explicit Windows tool archive is missing")
        with urllib.request.urlopen(lock["url"], timeout=45) as response:
            payload = response.read(32 * 1024 * 1024 + 1)
        if len(payload) > 32 * 1024 * 1024:
            raise ValueError("Windows tool download exceeds limit")
        if hashlib.sha256(payload).hexdigest() != lock["sha256"]:
            raise ValueError("Windows tool download checksum mismatch")
        source.write_bytes(payload)
    unpack_verified(source.read_bytes(), lock["sha256"], destination)
    print("Restored the pinned Windows Git/Lua toolchain")
