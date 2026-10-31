from __future__ import annotations

import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator

from cc2_mce import __version__
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest


def envelope(command: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "engine_version": __version__,
        "command": command,
        "status": "ok",
        "installable": False,
        "dry_run": True,
        "engine_sha256": engine_hash(),
        "mod_order": [],
        "sources": [],
        "files": [],
        "conflicts": [],
        "blockers": [],
        "warnings": [],
    }


def engine_hash() -> str:
    root = Path(__file__).parent
    inputs = list(root.glob("*.py")) + list((root / "schemas").glob("*.json"))
    entries = [(p.relative_to(root).as_posix(), digest(p.read_bytes())) for p in sorted(inputs)]
    return digest(json.dumps(entries, separators=(",", ":")).encode())


def ensure_destination(path: Path, protected: list[Path]) -> Path:
    destination = path.absolute()
    if destination.is_symlink() or destination.exists():
        raise InputError("Report destination already exists; overwriting is forbidden")
    parent = destination.parent.resolve(strict=True)
    if not parent.is_dir():
        raise InputError("Report parent directory must exist")
    cursor = destination.parent
    while cursor != cursor.parent:
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            raise InputError("Report path must not contain links/junctions")
        cursor = cursor.parent
    resolved = parent / destination.name
    for root in protected:
        if resolved.is_relative_to(root.resolve()):
            raise InputError("Reports cannot be written inside input roots")
    # Never create reports in a recognizable mod/package or SDK subdirectory.
    for ancestor in (parent, *parent.parents):
        markers = ("mod.xml", "baseline-manifest.json", "carrier_command.exe", "carriercommand.app")
        if ancestor.name.casefold() in {"steamapps", "mod_dev_kit", "carriercommand.app"} or any(
            (ancestor / marker).exists() for marker in markers
        ):
            raise InputError("Reports cannot be written inside mod/game/Steam/baseline roots")
    if destination.name.casefold() in {"mods.xml", "dinput8.dll", "carrier_command.exe", "mod.xml"}:
        raise InputError("Protected report filename")
    return resolved


def write_report(report: dict[str, object], path: Path, protected: list[Path]) -> None:
    destination = ensure_destination(path, protected)
    payload = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    created = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = os.open(destination, flags, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        if created:
            destination.unlink(missing_ok=True)
        raise InputError("Report could not be written safely") from exc


def validate_report(value: object) -> dict[str, object]:
    schema_path = Path(__file__).parent / "schemas/report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not Draft202012Validator(schema).is_valid(value):
        raise InputError("Report does not match the non-installable schema v1 contract")
    return value
