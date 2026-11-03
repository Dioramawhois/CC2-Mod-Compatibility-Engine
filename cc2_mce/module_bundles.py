"""Preserve independent SDK modules as data; never execute their Lua or DLLs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from cc2_mce.discovery import FileRef, ModRef
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest, normalize_logical_path
from cc2_mce.validation import validate_content

PREFIX = "cc2x-modules/"
CAPABILITY = "ordered-module-bundles-v1"
MANIFESTS = {"bridge.json", "native_bridge/bridge.json"}
ID = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\Z", re.ASCII)


@dataclass
class ModuleBundle:
    payload: dict[str, bytes] = field(default_factory=dict)
    files: list[dict[str, Any]] = field(default_factory=list)
    modules: list[dict[str, Any]] = field(default_factory=list)
    handled: set[tuple[str, str]] = field(default_factory=set)
    blockers: list[dict[str, str]] = field(default_factory=list)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _json(data: bytes) -> dict[str, Any]:
    if len(data) > 65536:
        raise ValueError("Module manifest exceeds 64 KiB")

    def nonfinite(value: str) -> None:
        raise ValueError("Nonfinite JSON value: " + value)

    value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=_pairs, parse_constant=nonfinite)
    if not isinstance(value, dict):
        raise ValueError("Module manifest must be an object")
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 32:
            raise ValueError("Module JSON nesting exceeds runtime limit")
        if isinstance(item, dict):
            for key, child in item.items():
                key.encode("utf-8")  # Reject isolated escaped UTF-16 surrogates.
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            item.encode("utf-8")
    return value


def _identifier(value: object, maximum: int = 64) -> str:
    if not isinstance(value, str) or len(value) > maximum or not ID.fullmatch(value):
        raise ValueError("Invalid module identity")
    return value


def _relative(value: object) -> str:
    if not isinstance(value, str) or len(value) > 240:
        raise ValueError("Invalid module path")
    logical, _ = normalize_logical_path(value)
    if logical != value:
        raise ValueError("Noncanonical module path")
    return logical


def _manifest(
    data: bytes, available: dict[str, FileRef], manifest_root: str, *, lua_api: int = 0
) -> str:
    value = _json(data)
    owner = _identifier(value.get("id")).lower()
    schema = value.get("schema", 2)
    if type(schema) is not int or schema not in {1, 2}:
        raise ValueError("Unsupported module schema")
    if schema == 1 and not {"name", "version", "runtime", "entry", "hooks"} <= value.keys():
        raise ValueError("Incomplete legacy module manifest")
    for name, maximum in (("name", 128), ("version", 64)):
        if name in value and (
            not isinstance(value[name], str)
            or not 0 < len(value[name].encode("utf-16-le")) // 2 <= maximum
            or any(ord(c) < 32 for c in value[name])
        ):
            raise ValueError("Invalid module name/version")
    if "runtime" in value and value["runtime"] != "bridge":
        raise ValueError("Unsupported Lua runtime")
    scripts = value.get("scripts", [])
    if not isinstance(scripts, list) or len(scripts) > 256:
        raise ValueError("Invalid module script list")
    scripts = ([value["entry"]] if "entry" in value else []) + scripts
    if not scripts:
        raise ValueError("Module has no declared scripts")
    if "rules" in value:
        if schema != 2 or lua_api < 2 or not isinstance(value["rules"], str):
            raise ValueError("A separate rules entry requires SDK Lua API 2")
        scripts = scripts + [value["rules"]]
    # Legacy content/bridge.json sometimes keeps a package-relative entry.
    script_root = (
        ""
        if schema == 1
        and manifest_root == "content/"
        and isinstance(value.get("entry"), str)
        and value["entry"].startswith("content/")
        else manifest_root
    )
    seen: set[str] = set()
    for script in scripts:
        relative = _relative(script)
        full = script_root + relative
        key = normalize_logical_path(full)[1]
        if not relative.endswith(".lua") or key.startswith("content/scripts/") or key in seen:
            raise ValueError("Duplicate or stock-game module script")
        if key not in available:
            raise ValueError("Declared module script is missing")
        seen.add(key)
    hooks = value.get("hooks", [])
    if not isinstance(hooks, list) or len(hooks) > 256:
        raise ValueError("Invalid module hooks")
    hook_keys = set()
    replacements = 0
    for hook in hooks:
        if not isinstance(hook, dict):
            raise ValueError("Invalid module hook")
        target = hook.get("target", hook.get("event"))
        mode = hook.get("mode", "after")
        handler = _identifier(hook.get("handler"), 160)
        if (
            not isinstance(mode, str)
            or target != "bridge.update"
            or mode not in {"before", "after", "replace", "around"}
        ):
            raise ValueError("Unsupported module hook")
        key_hook = (target, mode, handler)
        replacements += mode == "replace"
        if key_hook in hook_keys or replacements > 1:
            raise ValueError("Duplicate module hook")
        hook_keys.add(key_hook)
    ui = value.get("ui", {})
    if not isinstance(ui, dict) or ui.keys() - {"vehicles", "weapons"}:
        raise ValueError("Invalid module UI")
    for category, images in ui.items():
        if not isinstance(images, dict):
            raise ValueError("Invalid module image category")
        for identity, descriptor in images.items():
            _identifier(identity)
            allowed = (
                {"small", "large", "loadout"}
                if category == "vehicles"
                else {"small", "large", "type"}
            )
            if (
                not isinstance(descriptor, dict)
                or descriptor.keys() - allowed
                or "large" not in descriptor
            ):
                raise ValueError("Invalid module image descriptor")
            if category == "weapons" and not _identifier(descriptor.get("type")).lower().startswith(
                "attachment_"
            ):
                raise ValueError("Invalid attachment image type")
            for kind, image in descriptor.items():
                if kind == "type":
                    continue
                relative = _relative(image)
                key = normalize_logical_path(manifest_root + relative)[1]
                if not relative.lower().endswith(".png") or key not in available:
                    raise ValueError("Missing or unsafe module image")
    return owner


def _record(
    bundle: ModuleBundle, path: str, data: bytes, sources: dict[str, str], strategy: str
) -> None:
    normalize_logical_path(path)
    if path in bundle.payload:
        raise ValueError("Duplicate generated module path")
    bundle.payload[path] = data
    bundle.files.append(
        {
            "logical_path": path,
            "status": "copied",
            "strategy": strategy,
            "source_sha256": sources,
            "baseline_sha256": None,
            "baseline_source": None,
            "output_sha256": digest(data),
            "diagnostics": [],
        }
    )


def prepare_modules(
    selected: tuple[ModRef, ...], profile: dict[str, Any], *, luac: str | None = None
) -> ModuleBundle:
    result = ModuleBundle()
    owners: set[str] = set()
    for mod in selected:
        content = {item.key: item for item in mod.files}
        for item in mod.files:
            if item.key.startswith(PREFIX):
                result.handled.add((mod.id, item.key))
                result.blockers.append(
                    {
                        "code": "input_error",
                        "file": item.logical_path,
                        "message": "Reserved module output namespace in source: " + mod.name,
                    }
                )
        chosen = next(
            (
                content[name]
                for name in ("bridge.json", "native_bridge/bridge.json")
                if name in content
            ),
            None,
        )
        roots = {item.key: item for item in mod.root_files}
        root_manifest = chosen is None and "bridge.json" in roots
        if chosen is None and not root_manifest:
            continue
        chosen = chosen if chosen is not None else roots["bridge.json"]
        manifest_path = chosen.logical_path if root_manifest else "content/" + chosen.logical_path
        manifest_root = manifest_path.rpartition("/")[0]
        manifest_root = manifest_root + "/" if manifest_root else ""
        for item in mod.files:
            if (
                item.key in MANIFESTS
                or (
                    item.logical_path.lower().endswith(".lua")
                    and not item.key.startswith("scripts/")
                )
                or item.key.startswith("native_bridge/")
            ):
                result.handled.add((mod.id, item.key))
        if (
            CAPABILITY not in profile.get("runtime_capabilities", [])
            or profile.get("runtime_api", 0) < 8
        ):
            result.blockers.append(
                {
                    "code": "sdk_api",
                    "file": chosen.logical_path,
                    "message": f"{mod.name}: {CAPABILITY}",
                }
            )
        available = {"content/" + item.key: item for item in mod.files}
        available.update(roots)
        try:
            owner = _manifest(chosen.content, available, manifest_root, lua_api=mod.lua_api)
            if owner in owners:
                raise ValueError("Duplicate active module owner: " + owner)
            owners.add(owner)
            if not mod.metadata:
                raise ValueError("Module mod.xml is missing")
            status, reason = validate_content("mod.xml", mod.metadata, luac=luac)
            if status != "valid":
                raise ValueError(reason)
            container = "m-" + digest(mod.id.encode("utf-8"))[:32]
            prefix = PREFIX + container + "/"
            pending: list[tuple[str, FileRef]] = []
            for path, item in [
                *(("content/" + f.logical_path, f) for f in mod.files),
                *((f.logical_path, f) for f in mod.root_files),
            ]:
                if item.kind == "native":
                    if not path.startswith("content/"):
                        result.blockers.append(
                            {
                                "code": "native_plugin_review_required",
                                "file": path,
                                "message": "Legacy native files require content/cc2x",
                            }
                        )
                    continue
                if item.key in MANIFESTS or (path == "bridge.json" and root_manifest):
                    # Preserve shadowed manifests too; never merge author metadata.
                    _json(item.content)
                elif item.kind == "unknown":
                    result.blockers.append(
                        {"code": "needs_review", "file": path, "message": "Unknown resource type"}
                    )
                    continue
                elif item.kind == "text":
                    status, reason = validate_content(path, item.content, luac=luac)
                    if status != "valid":
                        result.blockers.append({"code": status, "file": path, "message": reason})
                        continue
                pending.append((prefix + path, item))
            _record(
                result,
                prefix + "mod.xml",
                mod.metadata,
                {mod.id: digest(mod.metadata)},
                "module-metadata-copy",
            )
            for path, item in pending:
                _record(result, path, item.content, {mod.id: item.sha256}, "module-private-copy")
            result.modules.append(
                {
                    "source_id": mod.id,
                    "owner_id": owner,
                    "container": container,
                    "source_sha256": mod.sha256,
                    "manifest_sha256": chosen.sha256,
                }
            )
        except (ValueError, UnicodeError, RecursionError, InputError) as exc:
            result.blockers.append(
                {
                    "code": "validation_error",
                    "file": chosen.logical_path,
                    "message": mod.name + ": " + str(exc),
                }
            )
    if result.modules:
        index = (
            json.dumps(
                {"schema": 1, "packages": [m["container"] for m in result.modules]},
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )
        _record(
            result,
            PREFIX + "index.json",
            index,
            {m["source_id"]: m["source_sha256"] for m in result.modules},
            "module-index",
        )
    return result
