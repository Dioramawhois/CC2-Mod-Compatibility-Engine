from __future__ import annotations

import hashlib
import os
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from cc2_mce.errors import InputError


@dataclass(frozen=True)
class Limits:
    max_file_bytes: int = 16 * 1024 * 1024
    max_total_bytes: int = 256 * 1024 * 1024
    max_entries: int = 20000
    max_depth: int = 32
    max_variants: int = 32


@dataclass
class Budget:
    limits: Limits
    entries: int = 0
    total_bytes: int = 0

    def entry(self) -> None:
        self.entries += 1
        if self.entries > self.limits.max_entries:
            raise InputError("Scan entry limit exceeded")

    def consume(self, size: int) -> None:
        self.total_bytes += size
        if size > self.limits.max_file_bytes or self.total_bytes > self.limits.max_total_bytes:
            raise InputError("Input byte limit exceeded")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_logical_path(value: str) -> tuple[str, str]:
    forbidden = set('\\:\x00<>"|?*')
    if not value or value.startswith("/") or any(c in forbidden or ord(c) < 32 for c in value):
        raise InputError("Unsafe logical path")
    parts = value.split("/")
    reserved = {"con", "prn", "aux", "nul", "conin$", "conout$"}
    reserved |= {f"{prefix}{number}" for prefix in ("com", "lpt") for number in "123456789¹²³"}
    for part in parts:
        if part in ("", ".", "..") or part.endswith((" ", ".")):
            raise InputError("Unsafe logical path component")
        if part.split(".")[0].casefold() in reserved:
            raise InputError("Reserved Windows logical path")
    return value, unicodedata.normalize("NFC", value).casefold()


def is_link(path: Path) -> bool:
    info = path.lstat()
    junction = bool(getattr(info, "st_file_attributes", 0) & 0x400)
    return stat.S_ISLNK(info.st_mode) or junction


def input_root(path: Path) -> Path:
    try:
        absolute = path.absolute()
        for component in (absolute, *absolute.parents):
            if is_link(component):
                raise InputError("Input root contains a link/junction")
        if is_link(path) or not path.is_dir():
            raise InputError("Input root is not a regular directory (link/junction forbidden)")
        return path.resolve(strict=True)
    except OSError as exc:
        raise InputError("Input directory is not accessible") from exc


def read_regular(path: Path, root: Path, budget: Budget) -> bytes:
    try:
        relative = path.relative_to(root)
        cursor = root
        for part in relative.parts:
            cursor /= part
            if is_link(cursor):
                raise InputError("Input link/junction forbidden")
        if not path.resolve(strict=True).is_relative_to(root):
            raise InputError("Input escapes its root")
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise InputError("Input is not a regular file")
        budget.consume(before.st_size)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise InputError("Input changed while opening")
            data = stream.read(budget.limits.max_file_bytes + 1)
            after = os.fstat(stream.fileno())

        def identity(info: os.stat_result) -> tuple[int, int, int, int]:
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns

        if len(data) != before.st_size or identity(before) != identity(after):
            raise InputError("Input changed while reading")
        if is_link(path) or identity(path.lstat()) != identity(after):
            raise InputError("Input changed after reading")
        return data
    except (OSError, ValueError) as exc:
        raise InputError("Input file is inaccessible or outside its root") from exc


def bounded_children(directory: Path, budget: Budget) -> list[Path]:
    children = []
    for child in directory.iterdir():
        budget.entry()
        children.append(child)
    return sorted(children, key=lambda p: p.name)


def walk_regular(root: Path, budget: Budget) -> list[Path]:
    files: list[Path] = []

    def visit(directory: Path, depth: int) -> None:
        if depth > budget.limits.max_depth:
            raise InputError("Scan depth limit exceeded")
        try:
            for child in bounded_children(directory, budget):
                if is_link(child):
                    raise InputError("Input link/junction forbidden")
                if child.is_dir():
                    visit(child, depth + 1)
                elif child.is_file():
                    if child.name != ".DS_Store":
                        files.append(child)
                else:
                    raise InputError("Special input file forbidden")
        except OSError as exc:
            raise InputError("Input directory cannot be scanned") from exc

    visit(root, 0)
    return files


def classify(logical_path: str, data: bytes) -> str:
    path = PurePosixPath(logical_path.casefold())
    if path.suffix == ".dll" or path.parts[0] == "cc2x":
        return "native"
    if path.suffix in {".png", ".jpg", ".jpeg", ".dds", ".fbx", ".wav", ".ogg", ".mesh"}:
        return "binary"
    if path.suffix == ".txtr":
        return "binary" if data.startswith(b"TXTR") else "unknown"
    if path.suffix in {".lua", ".txt", ".xml", ".glsl"}:
        return "text"
    return "unknown"
