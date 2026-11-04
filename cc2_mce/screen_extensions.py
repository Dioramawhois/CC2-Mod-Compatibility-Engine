"""Prepare declared SDK screen helpers as data; never execute mod Lua or DLLs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from cc2_mce.discovery import FileRef, ModRef
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest, normalize_logical_path
from cc2_mce.validation import validate_content

DESCRIPTOR = "cc2x/screen_extensions.json"
SOURCE_PREFIX = "cc2x/ui/"
CAPABILITY = "screen-extensions-v1"
EDIT_CAPABILITY = "screen-source-edits-v1"
MAX_MANIFEST_BYTES = 64 * 1024
MAX_EXTENSIONS = 16
MAX_SOURCE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
MAX_INSERT_BYTES = 256 * 1024
MAX_STOCK_BYTES = 2 * 1024 * 1024
_PATH = re.compile(r"[A-Za-z0-9_./-]+\Z", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


@dataclass
class ScreenExtensions:
    handled: set[tuple[str, str]] = field(default_factory=set)
    payload: dict[str, bytes] = field(default_factory=dict)
    files: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[dict[str, Any]] = field(default_factory=list)
    extensions: list[dict[str, Any]] = field(default_factory=list)
    schema: int = 1
    descriptor_inputs: dict[str, str] = field(default_factory=dict)
    source_bytes: int = 0


class _Rejected(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "screen_extension_invalid",
        path: str = DESCRIPTOR,
        participants: tuple[str, ...] = (),
    ):
        super().__init__(message)
        self.code = code
        self.path = path
        self.participants = participants


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(_value: str) -> None:
    raise ValueError("Nonfinite JSON number")


def _json(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_MANIFEST_BYTES:
        raise ValueError("Screen extension descriptor exceeds 64 KiB")
    value = json.loads(
        data.decode("utf-8-sig"), object_pairs_hook=_pairs, parse_constant=_nonfinite
    )
    if not isinstance(value, dict):
        raise ValueError("Screen extension descriptor must be an object")
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 32:
            raise ValueError("Screen extension JSON nesting exceeds limit")
        if isinstance(item, dict):
            for key, child in item.items():
                key.encode("utf-8")
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            item.encode("utf-8")
    return value


def _path(value: object, prefix: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 240
        or not value.startswith(prefix)
        or not value.endswith(".lua")
        or not _PATH.fullmatch(value)
    ):
        raise ValueError("Unsafe screen extension path")
    normalize_logical_path(value)
    return value


def _profile_bytes(entry: dict[str, Any]) -> int:
    profiles = entry.get("profiles", [])
    hashes: set[str] = set()
    inserted = 0
    for profile in profiles:
        if not _HASH.fullmatch(profile["sha256"]):
            raise ValueError("Screen source profile requires exactly 64 lowercase hash digits")
        if profile["sha256"] in hashes:
            raise ValueError("Duplicate screen source profile hash")
        hashes.add(profile["sha256"])
        previous_offset = -1
        previous_end = 0
        for edit in profile["edits"]:
            offset, remove = edit["offset"], edit["remove"]
            if (
                type(offset) is not int
                or type(remove) is not int
                or offset < 0
                or remove < 0
                or offset > MAX_STOCK_BYTES
                or remove > MAX_STOCK_BYTES - offset
                or offset <= previous_offset
                or offset < previous_end
            ):
                raise ValueError("Screen source edits have unsafe or overlapping byte ranges")
            text = edit["insert"]
            if "\x00" in text:
                raise ValueError("Screen source insertion contains NUL")
            inserted += len(text.encode("utf-8"))
            if inserted > MAX_INSERT_BYTES:
                raise ValueError("Screen source insertions exceed 256 KiB per extension")
            previous_offset, previous_end = offset, offset + remove
    return inserted


def _claim_references(result: ScreenExtensions, mod: ModRef, value: dict[str, Any]) -> None:
    """Keep referenced helpers out of the native gate even on descriptor refusal."""
    entries = value.get("extensions")
    if not isinstance(entries, list):
        return
    available = {item.key: item for item in mod.files}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            source = _path(entry.get("source"), SOURCE_PREFIX)
        except (ValueError, InputError):
            continue
        key = normalize_logical_path(source)[1]
        if key in available:
            result.handled.add((mod.id, key))


def prepare_screen_extensions(
    selected: tuple[ModRef, ...], profile: dict[str, Any], *, luac: str | None = None
) -> ScreenExtensions:
    result = ScreenExtensions()
    schema = json.loads(
        (Path(__file__).parent / "schemas/screen_extensions.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    targets: dict[str, ModRef] = {}
    output_keys: dict[str, str] = {}
    for mod in selected:
        available = {item.key: item for item in mod.files}
        descriptor = available.get(DESCRIPTOR)
        if descriptor is None:
            continue
        result.handled.add((mod.id, descriptor.key))
        result.descriptor_inputs[mod.id] = descriptor.sha256
        try:
            if descriptor.logical_path != DESCRIPTOR:
                raise ValueError("Screen descriptor path has noncanonical spelling")
            if descriptor.size > MAX_MANIFEST_BYTES:
                raise ValueError("Screen extension descriptor exceeds 64 KiB")
            raw = descriptor.content
            if digest(raw) != descriptor.sha256:
                raise InputError("Screen descriptor changed since scan")
            value = _json(raw)
            _claim_references(result, mod, value)
            if type(value.get("schema")) is not int or value["schema"] not in {1, 2}:
                raise ValueError("Unsupported screen extension schema")
            result.schema = max(result.schema, value["schema"])
            if not validator.is_valid(value):
                raise ValueError("Invalid screen extension descriptor structure")
            capabilities = profile.get("runtime_capabilities", [])
            if CAPABILITY not in capabilities:
                raise _Rejected(f"Requires SDK capability {CAPABILITY}", code="sdk_api")
            if value["schema"] == 2 and EDIT_CAPABILITY not in capabilities:
                raise _Rejected(f"Requires SDK capability {EDIT_CAPABILITY}", code="sdk_api")
            if len(result.extensions) + len(value["extensions"]) > MAX_EXTENSIONS:
                raise ValueError("Combined screen extensions exceed 16 entries")
            pending_extensions: list[dict[str, Any]] = []
            pending_sources: dict[str, tuple[FileRef, bytes]] = {}
            local_targets: set[str] = set()
            pending_bytes = 0
            for entry in value["extensions"]:
                screen = _path(entry["screen"], "scripts/")
                source = _path(entry["source"], SOURCE_PREFIX)
                screen_key = normalize_logical_path(screen)[1]
                source_key = normalize_logical_path(source)[1]
                if screen_key in local_targets:
                    raise ValueError("Duplicate or case-colliding screen target: " + screen)
                local_targets.add(screen_key)
                if screen_key in targets:
                    owner = targets[screen_key]
                    raise _Rejected(
                        f"{screen}: duplicate screen target in {owner.name} and {mod.name}",
                        code="screen_extension_conflict",
                        participants=(owner.id, mod.id),
                    )
                item = available.get(source_key)
                if item is None or item.logical_path != source:
                    raise ValueError("Missing or case-mismatched screen helper: " + source)
                if not 0 < item.size <= MAX_SOURCE_BYTES:
                    raise _Rejected(
                        "Screen helper must be nonempty and at most 256 KiB", path=source
                    )
                renamed = _path(
                    SOURCE_PREFIX
                    + "m-"
                    + digest(mod.id.encode("utf-8"))[:16]
                    + "/"
                    + source[len(SOURCE_PREFIX) :],
                    SOURCE_PREFIX,
                )
                if source not in pending_sources:
                    data = item.content
                    if digest(data) != item.sha256:
                        raise InputError("Screen helper changed since scan")
                    # luac's file loader strips these; the SDK loads the raw text chunk.
                    if data.startswith((b"\xef\xbb\xbf", b"#")):
                        raise _Rejected(
                            "Screen helper must be a UTF-8 Lua chunk without BOM or shebang",
                            path=source,
                        )
                    status, reason = validate_content(source, data, luac=luac)
                    if status != "valid":
                        raise _Rejected(reason, code=status, path=source)
                    pending_sources[source] = item, data
                pending_bytes += item.size + _profile_bytes(entry)
                if result.source_bytes + pending_bytes > MAX_TOTAL_BYTES:
                    raise ValueError("Combined screen source/read budget exceeds 4 MiB")
                pending_extensions.append({**entry, "source": renamed})
            for source, (item, data) in pending_sources.items():
                renamed = (
                    SOURCE_PREFIX
                    + "m-"
                    + digest(mod.id.encode("utf-8"))[:16]
                    + "/"
                    + source[len(SOURCE_PREFIX) :]
                )
                key = normalize_logical_path(renamed)[1]
                if key in output_keys:
                    raise ValueError("Generated screen helper path collision")
                output_keys[key] = renamed
                result.payload[renamed] = data
                result.files.append(
                    {
                        "logical_path": renamed,
                        "status": "copied",
                        "strategy": "screen-extension-source-copy",
                        "source_sha256": {mod.id: item.sha256},
                        "baseline_sha256": None,
                        "baseline_source": None,
                        "output_sha256": digest(data),
                        "diagnostics": ["Source: " + source],
                    }
                )
            result.extensions.extend(pending_extensions)
            result.source_bytes += pending_bytes
            for entry in pending_extensions:
                targets[normalize_logical_path(entry["screen"])[1]] = mod
        except _Rejected as exc:
            blocker: dict[str, Any] = {
                "code": exc.code,
                "file": exc.path,
                "message": mod.name + ": " + str(exc),
            }
            blocker["participants"] = list(exc.participants or (mod.id,))
            result.blockers.append(blocker)
        except (ValueError, UnicodeError, RecursionError, InputError) as exc:
            result.blockers.append(
                {
                    "code": "screen_extension_invalid",
                    "file": DESCRIPTOR,
                    "message": mod.name + ": " + str(exc),
                    "participants": [mod.id],
                }
            )
    return result
