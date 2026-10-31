from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from cc2_mce.errors import InputError
from cc2_mce.filesystem import (
    Budget,
    Limits,
    bounded_children,
    classify,
    digest,
    input_root,
    is_link,
    normalize_logical_path,
    read_regular,
    walk_regular,
)


@dataclass(frozen=True)
class FileRef:
    logical_path: str
    key: str
    sha256: str
    kind: str
    content: bytes

    def report(self) -> dict[str, object]:
        return {
            "logical_path": self.logical_path,
            "sha256": self.sha256,
            "kind": self.kind,
            "size": len(self.content),
        }


@dataclass(frozen=True)
class ModRef:
    id: str
    name: str
    root: Path
    sha256: str
    files: tuple[FileRef, ...]

    def report(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "sha256": self.sha256,
            "files": [item.report() for item in self.files],
        }


@dataclass(frozen=True)
class Scan:
    roots: tuple[Path, ...]
    mods: tuple[ModRef, ...]
    fingerprint: str
    limits: Limits


def fingerprint(value: object) -> str:
    return digest(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _metadata_name(data: bytes, fallback: str) -> str:
    try:
        text = data.decode("utf-8-sig").lstrip()
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.IGNORECASE):
            raise InputError("Unsafe metadata XML declarations")
        root = ElementTree.fromstring(text)
        return root.attrib.get("name", fallback)
    except (UnicodeError, ElementTree.ParseError) as exc:
        raise InputError("Invalid metadata XML") from exc


def discover(roots: list[Path], *, limits: Limits | None = None) -> Scan:
    limits = limits or Limits()
    budget = Budget(limits)
    canonical_roots = tuple(dict.fromkeys(input_root(root) for root in roots))
    candidates: list[Path] = []
    for root in canonical_roots:
        if (root / "content").exists():
            candidates.append(root)
            continue
        try:
            for child in bounded_children(root, budget):
                if is_link(child):
                    raise InputError("Input link/junction forbidden")
                if child.is_dir() and (child / "content").exists():
                    candidates.append(child)
        except OSError as exc:
            raise InputError("Mod collection cannot be read") from exc
    mods: list[ModRef] = []
    ids: set[str] = set()
    spellings: dict[str, str] = {}
    for root in sorted(set(candidates), key=lambda p: p.name):
        mod_id, id_key = normalize_logical_path(root.name)
        if id_key in ids:
            raise InputError("Duplicate mod id")
        ids.add(id_key)
        content = root / "content"
        input_root(content)
        metadata = b""
        if (root / "mod.xml").exists() or (root / "mod.xml").is_symlink():
            metadata = read_regular(root / "mod.xml", root, budget)
        name = _metadata_name(metadata, mod_id) if metadata else mod_id
        files: list[FileRef] = []
        local_keys: set[str] = set()
        for path in walk_regular(content, budget):
            logical, key = normalize_logical_path(path.relative_to(content).as_posix())
            if key in local_keys or (key in spellings and spellings[key] != logical):
                raise InputError("Logical path case/Unicode collision")
            local_keys.add(key)
            spellings[key] = logical
            data = read_regular(path, root, budget)
            files.append(FileRef(logical, key, digest(data), classify(logical, data), data))
        files.sort(key=lambda item: item.key)
        source_hash = fingerprint(
            {"metadata": digest(metadata), "files": [item.report() for item in files]}
        )
        mods.append(ModRef(mod_id, name, root, source_hash, tuple(files)))
    return Scan(canonical_roots, tuple(mods), fingerprint([mod.report() for mod in mods]), limits)


def snapshot_unchanged(scan: Scan) -> bool:
    try:
        return discover(list(scan.roots), limits=scan.limits).fingerprint == scan.fingerprint
    except InputError:
        return False
