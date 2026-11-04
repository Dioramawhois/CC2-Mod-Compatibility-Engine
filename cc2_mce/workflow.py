"""Verified three-way packaging, game activation and reversible runtime installation."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import unicodedata
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from jsonschema import Draft202012Validator

from cc2_mce import APP_NAME, sdk_runtime, sdk_settings
from cc2_mce.discovery import ModRef, Scan, fingerprint, snapshot_unchanged
from cc2_mce.errors import InputError
from cc2_mce.filesystem import (
    Budget,
    Limits,
    bounded_children,
    digest,
    input_root,
    normalize_logical_path,
    read_regular,
    walk_regular,
)
from cc2_mce.installation import Installation
from cc2_mce.locking import activation_lock
from cc2_mce.managed_menu import (
    ADAPTER,
    MENU_PATH,
    POLICY,
    SCREEN_DESCRIPTOR,
    SCREEN_SOURCE,
    screen_source,
)
from cc2_mce.merge import GitMergeAdapter, MergeInput, merge_file
from cc2_mce.module_bundles import prepare_modules
from cc2_mce.reports import engine_hash
from cc2_mce.toolchain import Toolchain
from cc2_mce.validation import validate_content

OUTPUT_FOLDER = "CC2-MCE"
RUNTIME_DATA = Path(__file__).parent / "runtime_data"


@dataclass(frozen=True)
class PackagePlan:
    game: Installation
    scan: Scan
    selected: tuple[ModRef, ...]
    profile: dict[str, Any]
    tools: Toolchain | None
    payload: dict[str, bytes]
    report: dict[str, Any]
    runtime_source: Path | None
    config_defaults: dict[str, bytes] = field(default_factory=dict)

    @property
    def blockers(self) -> list[dict[str, str]]:
        return self.report["blockers"]  # type: ignore[no-any-return]


def game_user_dir() -> Path:
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "Carrier Command 2"
    return Path.home() / "Library/Application Support/Carrier Command 2"


def _read(path: Path, root: Path) -> bytes:
    return read_regular(path, root, Budget(Limits()))


def review_profile(game: Installation) -> dict[str, Any]:
    executable_hash = digest(_read(game.executable, input_root(game.executable.parent)))
    for path in sorted((Path(__file__).parent / "profiles").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("game_sha256") == executable_hash:
            return value  # type: ignore[no-any-return]
    # Unprofiled game builds can merge data using their installed originals. Native approval
    # remains absent: no executable code is trusted just because data merging is allowed.
    return {
        "game_sha256": executable_hash,
        "baselines": {},
        "native_plugins": {},
        "runtime_sha256": None,
        "runtime_api": 0,
    }


def resolve_selection(
    scan: Scan, selected: list[str], *, provided_dependencies: frozenset[str] = frozenset()
) -> tuple[ModRef, ...]:
    by_id: dict[str, ModRef] = {}
    versions: dict[str, list[ModRef]] = {}
    ambiguous = "Выберите одну версию мода: Workshop или локальную."
    for mod in scan.mods:
        if mod.id in by_id:
            raise InputError("Неоднозначный идентификатор мода или библиотеки")
        by_id[mod.id] = mod
        versions.setdefault(mod.package_id or mod.id, []).append(mod)
    for identity in versions:
        source = by_id.get(identity)
        if source is not None and (source.package_id or source.id) != identity:
            raise InputError("Неоднозначный идентификатор мода или библиотеки")
    preferred: dict[str, ModRef] = {}
    explicit: dict[str, ModRef] = {}
    for key in selected:
        requested = by_id.get(key)
        candidates = versions.get(key, [])
        if requested is None and candidates:
            if len(candidates) != 1:
                raise InputError(ambiguous)
            requested = candidates[0]
        if requested is not None:
            identity = requested.package_id or requested.id
            if identity in preferred and preferred[identity] != requested:
                raise InputError(ambiguous)
            preferred[identity] = requested
            explicit[key] = requested
    result: list[ModRef] = []
    visiting: set[str] = set()

    def visit(key: str, *, dependency: bool = False) -> None:
        mod = explicit.get(key) if not dependency else preferred.get(key)
        if dependency and mod is None:
            candidates = versions.get(key, [])
            if len(candidates) > 1:
                raise InputError(ambiguous)
            mod = candidates[0] if candidates else by_id.get(key)
        if mod is None:
            if dependency and key in provided_dependencies:
                return
            raise InputError(f"Не найдена зависимость: {key}")
        identity = mod.package_id or mod.id
        if identity in preferred and preferred[identity] != mod:
            raise InputError(ambiguous)
        preferred[identity] = mod
        if mod.id in visiting:
            raise InputError("Циклическая зависимость библиотек")
        if mod in result:
            return
        if len(visiting) + len(result) >= 32:
            raise InputError("Набор с зависимостями превышает 32 пакета")
        visiting.add(mod.id)
        for required in mod.dependencies:
            visit(required, dependency=True)
        visiting.remove(mod.id)
        result.append(mod)

    for key in selected:
        visit(key)
    if len(result) > 32:
        raise InputError("Выберите не более 32 пакетов")
    return tuple(result)


def _runtime(game: Installation, expected: str, previous: list[str] | None = None) -> Path | None:
    installed = game.root / "dinput8.dll"
    if installed.exists() or installed.is_symlink():
        installed_hash = digest(_read(installed, game.root))
        if installed_hash == expected:
            return installed
        if installed_hash not in (previous or []):
            raise InputError("В игре другой dinput8.dll. Он не будет перезаписан.")
    bundled = RUNTIME_DATA / expected / "dinput8.dll"
    if bundled.exists():
        if digest(_read(bundled, input_root(bundled.parent))) != expected:
            raise InputError("Bundled SDK runtime failed integrity verification")
        return bundled
    libraries = game.libraries_dir
    if not libraries.exists():
        return None
    root = input_root(libraries)
    for path in walk_regular(root, Budget(Limits())):
        if path.name.casefold() == "dinput8.dll" and digest(_read(path, root)) == expected:
            return path
    return None


def _package_metadata(selected: tuple[ModRef, ...]) -> bytes:
    root = ET.Element(
        "data",
        name=(
            (APP_NAME + ": " + " + ".join(mod.name for mod in selected))[:240]
            if selected
            else APP_NAME
        ),
        author="CC2 Mod Compatibility Engine",
        description=(" + ".join(mod.name for mod in selected) or "No mods enabled")[:512],
    )
    ET.SubElement(root, "cc2mce", schema="1", type="mod")
    return bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


def _original_path(
    root: Path,
    folder: str,
    logical: str,
    budget: Budget,
    directory_cache: dict[Path, tuple[Path, ...]],
) -> Path | None:
    directory = root / folder
    if not directory.exists() and not directory.is_symlink():
        return None
    input_root(directory)
    direct = directory / logical
    if direct.exists() or direct.is_symlink():
        return direct
    # CC2 logical paths use the same case/Unicode identity on all host filesystems.
    cursor = directory
    for component in logical.split("/"):
        key = unicodedata.normalize("NFC", component).casefold()
        cursor = input_root(cursor)
        if cursor not in directory_cache:
            directory_cache[cursor] = tuple(bounded_children(cursor, budget))
        matches = [
            path
            for path in directory_cache[cursor]
            if unicodedata.normalize("NFC", path.name).casefold() == key
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise InputError("Original path case/Unicode collision")
        cursor = matches[0]
    return cursor


def analyze(
    game: Installation,
    scan: Scan,
    selected: list[str],
    *,
    profile: dict[str, Any] | None = None,
    tools: Toolchain | None = None,
    patch_priority: bool = False,
) -> PackagePlan:
    profile = profile if profile is not None else review_profile(game)
    actual_game_hash = digest(_read(game.executable, input_root(game.executable.parent)))
    if actual_game_hash != profile["game_sha256"]:
        raise InputError("Сборка игры изменилась")
    provided: frozenset[str] = frozenset()
    if profile.get("runtime_sha256") and any("cc2x.runtime" in m.dependencies for m in scan.mods):
        try:
            if _runtime(game, profile["runtime_sha256"], profile.get("previous_runtime_sha256")):
                provided = frozenset({"cc2x.runtime"})
        except InputError:
            pass  # Never satisfy a missing dependency using an unknown installed DLL.
    chosen = resolve_selection(scan, selected, provided_dependencies=provided)
    groups: dict[str, list[tuple[ModRef, Any]]] = defaultdict(list)
    bundle = prepare_modules(chosen, profile, luac=str(tools.luac) if tools else None)
    blockers: list[dict[str, str]] = list(bundle.blockers)
    files: list[dict[str, Any]] = list(bundle.files)
    payload: dict[str, bytes] = dict(bundle.payload)
    needs_runtime = bool(bundle.modules) or any(mod.sdk == "cc2x" for mod in chosen)
    for mod in chosen:
        if mod.api > profile.get("runtime_api", 0):
            blockers.append({"code": "sdk_api", "message": f"{mod.name}: нужна новая версия SDK"})
        if mod.lua_api and (
            mod.lua_api > profile.get("runtime_lua_api", 0)
            or f"lua-mod-api-v{mod.lua_api}" not in profile.get("runtime_capabilities", [])
        ):
            blockers.append({"code": "sdk_api", "message": f"{mod.name}: нужна новая версия SDK"})
        if mod.framework_api and (
            mod.framework_api > profile.get("runtime_framework_api", 0)
            or f"framework-c-api-v{mod.framework_api}"
            not in profile.get("runtime_capabilities", [])
        ):
            blockers.append({"code": "sdk_api", "message": f"{mod.name}: нужна новая версия SDK"})
        for item in mod.files:
            if (mod.id, item.key) in bundle.handled:
                continue
            groups[item.key].append((mod, item))
    native_names: dict[str, str] = {}
    config_defaults: dict[str, bytes] = {}
    config_providers: dict[str, set[str]] = defaultdict(set)
    runtime_inputs: dict[str, str] = {}
    baseline_budget = Budget(Limits())
    baseline_directories: dict[Path, tuple[Path, ...]] = {}
    for key, variants in sorted(groups.items()):
        logical = variants[0][1].logical_path
        source_hashes = {mod.id: item.sha256 for mod, item in variants}
        if logical.casefold() == "dinput8.dll":
            needs_runtime = True
            runtime_inputs.update(source_hashes)
            allowed = {profile.get("runtime_sha256"), *profile.get("previous_runtime_sha256", [])}
            if not set(source_hashes.values()).issubset(allowed):
                blockers.append(
                    {
                        "code": "runtime_conflict",
                        "file": logical,
                        "message": "Неизвестная версия загрузчика dinput8.dll",
                    }
                )
            continue
        base: bytes | None = None
        baseline_source = None
        for folder in ("rom_0", "mod_dev_kit/source"):
            candidate = _original_path(
                game.root, folder, logical, baseline_budget, baseline_directories
            )
            if candidate is not None:
                base = read_regular(candidate, game.root, baseline_budget)
                baseline_source = folder + "/" + logical
                break
        if variants[0][1].kind == "native":
            needs_runtime = True
            hashes = set(source_hashes.values())
            approved = profile.get("native_plugins", {})
            name = Path(logical).name.casefold()
            if (
                not logical.casefold().startswith("cc2x/")
                or len(hashes) != 1
                or next(iter(hashes)) not in approved
                or (name in native_names and native_names[name] != key)
            ):
                status, strategy, content = "native_plugin_review_required", "blocked", None
            else:
                status, strategy, content = "copied", "reviewed-native-copy", variants[0][1].content
                native_names[name] = key
                native_hash = next(iter(hashes))
                for filename, data in sdk_settings.reviewed_defaults(approved[native_hash]).items():
                    if filename in config_defaults and config_defaults[filename] != data:
                        blockers.append(
                            {
                                "code": "native_plugin_review_required",
                                "file": logical,
                                "message": "Conflicting reviewed SDK defaults: " + filename,
                            }
                        )
                    else:
                        config_defaults[filename] = data
                    config_providers[filename].add(native_hash)
            diagnostics: list[str] = []
        else:
            outcome = merge_file(
                logical,
                [MergeInput(mod.id, item.content) for mod, item in variants],
                base,
                baseline_verified=base is not None,
                git=GitMergeAdapter(str(tools.git)) if tools else GitMergeAdapter(),
                luac=str(tools.luac) if tools else None,
                canonical_eol=True,
                favor_later=patch_priority,
            )
            status, strategy, content = outcome.status, outcome.strategy, outcome.content
            diagnostics = list(outcome.diagnostics)
        files.append(
            {
                "logical_path": logical,
                "status": status,
                "strategy": strategy,
                "source_sha256": source_hashes,
                "baseline_sha256": digest(base) if base is not None else None,
                "baseline_source": baseline_source,
                "output_sha256": digest(content) if content is not None else None,
                "diagnostics": diagnostics,
            }
        )
        if content is not None and status in {"clean", "copied", "identical", "overridden"}:
            payload[logical] = content
        else:
            blockers.append(
                {
                    "code": status,
                    "file": logical,
                    "message": "; ".join(diagnostics) or f"{logical}: {status}",
                }
            )
    managed_menu = None
    if chosen and "screen-extensions-v1" in profile.get("runtime_capabilities", []):
        # CC2 deliberately disables ordinary mod resource roots in the front menu.
        # Only a reviewed SDK screen extension can run the owned policy there.
        needs_runtime = True
        owned_menu = screen_source(tuple(mod.name for mod in chosen))
        descriptor = (
            json.dumps(
                {"schema": 1, "extensions": [{"screen": MENU_PATH, "source": SCREEN_SOURCE}]},
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
        collisions = [
            name
            for name in (SCREEN_DESCRIPTOR, SCREEN_SOURCE)
            if name.casefold() in groups or name in payload
        ]
        status, diagnostic = validate_content(
            SCREEN_SOURCE, owned_menu, luac=str(tools.luac) if tools else None
        )
        if collisions:
            blockers.append({"code": "managed_menu_collision", "message": ", ".join(collisions)})
        elif status != "valid":
            blockers.append({"code": status, "file": SCREEN_SOURCE, "message": diagnostic})
        else:
            for logical, content in ((SCREEN_SOURCE, owned_menu), (SCREEN_DESCRIPTOR, descriptor)):
                payload[logical] = content
                files.append(
                    {
                        "logical_path": logical,
                        "status": "copied",
                        "strategy": "managed-menu",
                        "source_sha256": {},
                        "baseline_sha256": None,
                        "output_sha256": digest(content),
                        "diagnostics": [],
                    }
                )
            managed_menu = {
                "policy": POLICY,
                "logical_path": MENU_PATH,
                "input_sha256": digest(ADAPTER),
                "adapter_sha256": digest(ADAPTER),
                "output_sha256": digest(owned_menu),
                "source_path": SCREEN_SOURCE,
                "descriptor_path": SCREEN_DESCRIPTOR,
                "descriptor_sha256": digest(descriptor),
            }
    runtime = None
    if needs_runtime:
        expected = profile.get("runtime_sha256")
        if expected:
            try:
                runtime = _runtime(game, expected, profile.get("previous_runtime_sha256"))
            except InputError as exc:
                blockers.append({"code": "runtime_conflict", "message": str(exc)})
        if runtime is None:
            blockers.append(
                {
                    "code": "runtime_missing",
                    "message": "Проверенный dinput8.dll не найден в игре или libraries.",
                }
            )
    output_budget = Budget(Limits())
    try:
        output_paths = {"mod.xml", "mce-manifest.json", "content"}
        for logical, data in payload.items():
            parts = logical.split("/")
            if len(parts) > output_budget.limits.max_depth:
                raise InputError("Output depth limit exceeded")
            for index in range(1, len(parts) + 1):
                output_paths.add("content/" + "/".join(parts[:index]))
            output_budget.consume(len(data))
        for _ in output_paths:
            output_budget.entry()
    except InputError as exc:
        blockers.append({"code": "input_error", "message": str(exc)})
    report: dict[str, Any] = {
        "schema_version": 2,
        "owner": "cc2-mce",
        "output_folder": OUTPUT_FOLDER,
        "merge_policy": "ordered-patches" if patch_priority else "strict",
        "engine_sha256": engine_hash(),
        "game_sha256": actual_game_hash,
        "mod_order": [mod.id for mod in chosen],
        "sources": [mod.report() for mod in chosen],
        "files": files,
        "blockers": blockers,
        "eol_policy": "canonical-lf-for-three-way; unique-files-preserved",
        "toolchain_sha256": tools.manifest_sha256 if tools else None,
        "runtime_sha256": profile.get("runtime_sha256") if needs_runtime else None,
        "installable": not blockers,
        "gameplay_verified": False,
        "package_metadata_sha256": digest(_package_metadata(chosen)),
    }
    if bundle.modules:
        report["modules"] = bundle.modules
    if managed_menu is not None:
        report["managed_menu"] = managed_menu
    if runtime_inputs:
        report["runtime_inputs"] = runtime_inputs
    if needs_runtime and profile.get("runtime_review"):
        report["runtime_review"] = profile["runtime_review"]
    if config_defaults:
        report["config_defaults"] = [
            {
                "filename": name,
                "sha256": digest(data),
                "providers": sorted(config_providers[name]),
                "policy": "create-missing-preserve-user",
            }
            for name, data in sorted(config_defaults.items())
        ]
    report["build_id"] = fingerprint(report)
    schema = json.loads((Path(__file__).parent / "schemas/package.schema.json").read_text())
    if not Draft202012Validator(schema).is_valid(report):
        raise InputError("Internal package report contract violation")
    return PackagePlan(
        game, scan, chosen, profile, tools, payload, report, runtime, config_defaults
    )


def _parse_activation(raw: bytes) -> ET.Element:
    if (
        len(raw) > 1024 * 1024
        or b"\x00" in raw
        or re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", raw, re.I)
    ):
        raise InputError("Unsafe game activation XML")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise InputError("Не удалось прочитать mods.xml") from exc
    nodes = root.findall("active_mod_folders")
    if root.tag != "data" or len(nodes) != 1:
        raise InputError("Неизвестный формат mods.xml")
    for child in nodes[0]:
        value = child.get("value", "")
        if (
            child.tag != "path"
            or set(child.attrib) != {"value"}
            or len(child)
            or not Path(value).is_absolute()
            or value.startswith(("\\\\", "//"))
        ):
            raise InputError("Неизвестный или небезопасный путь в mods.xml")
    return root


def active_paths(user_dir: Path) -> tuple[Path, ...]:
    root = input_root(user_dir)
    raw = _read(root / "mods.xml", root)
    xml = _parse_activation(raw)
    return tuple(
        dict.fromkeys(Path(node.attrib["value"]) for node in xml.findall("active_mod_folders/path"))
    )


def _write_new(path: Path, content: bytes) -> None:
    input_root(path.parent)
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _replace_checked(path: Path, content: bytes, expected: bytes) -> None:
    parent = input_root(path.parent)
    temporary = parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        _write_new(temporary, content)
        if _read(path, parent) != expected:
            raise InputError("Настройки игры изменились. Повторите проверку.")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _running() -> bool:
    if sys.platform != "win32":
        raise InputError("Game activation is currently verified on Windows only")
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("pid", wintypes.DWORD),
            ("heap", ctypes.c_size_t),
            ("module", wintypes.DWORD),
            ("threads", wintypes.DWORD),
            ("parent", wintypes.DWORD),
            ("priority", wintypes.LONG),
            ("flags", wintypes.DWORD),
            ("exe", wintypes.WCHAR * 260),
        ]

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    api.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    api.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = api.CreateToolhelp32Snapshot(2, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        raise InputError("Не удалось проверить, закрыта ли игра")
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(Entry)
        more = api.Process32FirstW(snapshot, ctypes.byref(entry))
        if not more:
            raise InputError("Не удалось прочитать список процессов")
        while more:
            if entry.exe.casefold() in {"carrier_command.exe", "carrier_command_vr.exe"}:
                return True
            more = api.Process32NextW(snapshot, ctypes.byref(entry))
        return False
    finally:
        api.CloseHandle(snapshot)


def _verified_package(path: Path) -> dict[str, Any]:
    """Recognize only complete, unchanged Engine outputs before moving/replacing them."""
    root = input_root(path)
    report = json.loads(_read(root / "mce-manifest.json", root))
    schema = json.loads((Path(__file__).parent / "schemas/package.schema.json").read_text())
    if not Draft202012Validator(schema).is_valid(report) or not report["installable"]:
        raise InputError("Папка сборки не принадлежит Engine или повреждена")
    expected = {"mod.xml", "mce-manifest.json"}
    for item in report["files"]:
        logical, _ = normalize_logical_path(item["logical_path"])
        expected.add("content/" + logical)
        if digest(_read(root / "content" / logical, root)) != item["output_sha256"]:
            raise InputError("Выходной пакет изменён извне")
    if digest(_read(root / "mod.xml", root)) != report["package_metadata_sha256"]:
        raise InputError("Метаданные выходного пакета изменены извне")
    actual = {p.relative_to(root).as_posix() for p in walk_regular(root, Budget(Limits()))}
    if actual != expected:
        raise InputError("В выходной пакет добавлены или изменены файлы")
    return report  # type: ignore[no-any-return]


def remembered_package(game: Installation, user_dir: Path) -> dict[str, Any] | None:
    """Recover the last owned selection even when the game changed mods.xml."""
    state_dir = user_dir / "cc2-mce"
    state_file = state_dir / "activation.json"
    if not state_file.exists() and not state_file.is_symlink():
        return None
    state = json.loads(_read(state_file, input_root(state_dir)))
    if not isinstance(state, dict) or state.get("owner") != "cc2-mce":
        raise InputError("Unknown activation journal")
    package = user_dir / "mods" / OUTPUT_FOLDER
    if state.get("package") != str(package):
        raise InputError("Unexpected saved package path")
    report = _verified_package(package)
    if (
        report["build_id"] != state.get("build_id")
        or report["mod_order"] != state.get("mod_order")
        or digest(_read(package / "mce-manifest.json", package)) != state.get("new_manifest_sha256")
    ):
        raise InputError("Saved activation and package do not match")
    # The same user-data directory may be used with another installed game.
    if digest(_read(game.executable, game.root)) != report["game_sha256"]:
        return None
    return report


def _cache_path(state_dir: Path, name: str) -> Path:
    normalized, _ = normalize_logical_path(name)
    if "/" in normalized:
        raise InputError("Неверный путь журнала восстановления")
    return state_dir / normalized


def _recover_pending(user: Path) -> None:
    """Roll back an interrupted folder/config transaction before the next operation."""
    state_dir = input_root(user / "cc2-mce")
    pending = state_dir / "pending.json"
    if not pending.exists():
        return
    journal = json.loads(_read(pending, state_dir))
    if journal.get("owner") != "cc2-mce":
        raise InputError("Неизвестный журнал незавершённой записи")
    destination = user / "mods" / OUTPUT_FOLDER
    backup = _cache_path(state_dir, journal["package_backup"])
    old = _read(_cache_path(state_dir, journal["backup"]), state_dir)
    current = _read(user / "mods.xml", user)
    if digest(old) != journal["backup_sha256"] or digest(current) not in {
        journal["backup_sha256"],
        journal["applied_sha256"],
    }:
        raise InputError(
            "Настройки изменились после сбоя; автоматическое восстановление остановлено"
        )
    if destination.exists():
        _verified_package(destination)
        current_hash = digest(_read(destination / "mce-manifest.json", destination))
        if current_hash == journal["new_manifest_sha256"] and (
            backup.exists() or not journal["had_destination"]
        ):
            # Cache the complete failed candidate, never delete an unverified directory.
            os.rename(destination, state_dir / ("discarded-" + uuid.uuid4().hex))
        elif current_hash != journal["old_manifest_sha256"] or backup.exists():
            raise InputError("Папка сборки изменена после сбоя")
    if backup.exists():
        _verified_package(backup)
        if digest(_read(backup / "mce-manifest.json", backup)) != journal["old_manifest_sha256"]:
            raise InputError("Резервная сборка повреждена")
        os.rename(backup, destination)
    elif journal["had_destination"] and not destination.exists():
        raise InputError("Не найдена предыдущая рабочая сборка")
    for move in journal.get("legacy_moves", []):
        source = _cache_path(user / "mods", move["name"])
        archived = _cache_path(state_dir, move["cache"])
        if archived.exists():
            _verified_package(archived)
            if source.exists():
                raise InputError("Прежняя папка модов занята")
            os.rename(archived, source)
    if current != old:
        _replace_checked(user / "mods.xml", old, current)
    state_file = state_dir / "activation.json"
    if journal["previous_state"]:
        previous = _read(_cache_path(state_dir, journal["previous_state"]), state_dir)
        if state_file.exists():
            _replace_checked(state_file, previous, _read(state_file, state_dir))
        else:
            _write_new(state_file, previous)
    elif state_file.exists():
        state_file.unlink()
    sdk_settings.cleanup(user, state_dir, journal.get("config_created", []), remove_targets=True)
    # Restore our resources/settings even if a separate writer replaced the DLL.
    # Preserve the pending journal and runtime backup if native rollback refuses.
    sdk_runtime.rollback(journal.get("runtime_change"), state_dir, _replace_checked)
    pending.unlink()


def _apply_plan_locked(
    plan: PackagePlan,
    user_dir: Path,
    *,
    game_running: Callable[[], bool] = _running,
) -> Path:
    if plan.blockers:
        raise InputError("Есть неразрешённые блокировки; активация запрещена")
    if game_running():
        raise InputError("Закройте игру перед применением модов")
    user = input_root(user_dir)
    state_dir = user / "cc2-mce"
    state_dir.mkdir(exist_ok=True)
    input_root(state_dir)
    _recover_pending(user)
    if not snapshot_unchanged(plan.scan):
        raise InputError("Исходные моды изменились. Повторите проверку.")
    fresh = analyze(
        plan.game,
        plan.scan,
        [mod.id for mod in plan.selected],
        profile=plan.profile,
        tools=plan.tools,
        patch_priority=plan.report.get("merge_policy") == "ordered-patches",
    )
    if fresh.blockers or fresh.report != plan.report or fresh.payload != plan.payload:
        raise InputError("База, инструменты или игра изменились")
    old = _read(user / "mods.xml", user)
    xml = _parse_activation(old)
    mods = user / "mods"
    mods.mkdir(exist_ok=True)
    input_root(mods)
    destination = mods / OUTPUT_FOLDER
    token = uuid.uuid4().hex
    stage = state_dir / ("stage-" + token)
    old_manifest_hash = None
    if destination.exists():
        _verified_package(destination)
        old_manifest_hash = digest(_read(destination / "mce-manifest.json", destination))
    stage.mkdir()
    try:
        (stage / "content").mkdir()
        for logical, content in sorted(plan.payload.items()):
            normalize_logical_path(logical)
            path = stage / "content" / logical
            path.parent.mkdir(parents=True, exist_ok=True)
            _write_new(path, content)
        _write_new(stage / "mod.xml", _package_metadata(plan.selected))
        _write_new(
            stage / "mce-manifest.json",
            (json.dumps(plan.report, ensure_ascii=False, indent=2) + "\n").encode(),
        )
        _verified_package(stage)
    except (OSError, InputError):
        # This exact directory was created above and cannot contain source files.
        input_root(stage)
        shutil.rmtree(stage)
        raise
    if game_running() or not snapshot_unchanged(plan.scan):
        raise InputError("Игра запущена или входы изменились; пакет не активирован")
    runtime_target = plan.game.root / "dinput8.dll"
    active = xml.find("active_mod_folders")
    assert active is not None
    active.clear()
    if plan.selected:
        ET.SubElement(active, "path", value=str(destination))
    new = ET.tostring(xml, encoding="utf-8", xml_declaration=True)
    state_file = state_dir / "activation.json"
    state: dict[str, Any] = {}
    previous_state: bytes | None = None
    if state_file.exists():
        previous_state = _read(state_file, state_dir)
        state = json.loads(previous_state)
        if not isinstance(state, dict) or state.get("owner") != "cc2-mce":
            raise InputError("Неверный журнал активации")
    legacy_moves = []
    for previous in bounded_children(mods, Budget(Limits())):
        if not re.fullmatch(r"CC2-MCE-[0-9a-f]{16}", previous.name):
            continue
        manifest = previous / "mce-manifest.json"
        if not manifest.exists():
            continue
        previous_root = input_root(previous)
        metadata = json.loads(_read(manifest, previous_root))
        if not isinstance(metadata, dict) or metadata.get("owner") != "cc2-mce":
            continue
        _verified_package(previous_root)
        legacy_moves.append({"name": previous.name, "cache": "legacy-" + uuid.uuid4().hex})
    same_activation = old == new
    if state.get("owner") == "cc2-mce" and not same_activation:
        saved_root = _parse_activation(_read(_cache_path(state_dir, state["backup"]), state_dir))
        same_activation = (
            len(xml) == len(saved_root) == 1
            and xml.attrib == saved_root.attrib
            and active_paths(user) == ((destination,) if plan.selected else ())
            and all(
                not (node.text or "").strip() and not (node.tail or "").strip()
                for node in xml.iter()
            )
        )
    if (
        same_activation
        and state.get("build_id") == plan.report["build_id"]
        and old_manifest_hash == digest(_read(stage / "mce-manifest.json", stage))
        and not legacy_moves
        and not sdk_settings.missing(user, plan.config_defaults)
        and (
            plan.runtime_source is None
            or (
                runtime_target.exists()
                and digest(_read(runtime_target, plan.game.root)) == plan.report["runtime_sha256"]
            )
        )
    ):
        shutil.rmtree(input_root(stage))
        return destination
    backup_name = f"mods-{uuid.uuid4().hex}.xml"
    config_created = sdk_settings.stage(user, state_dir, plan.config_defaults, token, _write_new)
    runtime_change = sdk_runtime.stage(
        plan.game, plan.runtime_source, plan.profile, state_dir, token, _write_new
    )
    _write_new(state_dir / backup_name, old)
    updated = {
        "owner": "cc2-mce",
        "backup": backup_name,
        "backup_sha256": digest(old),
        "applied_sha256": digest(new),
        "package": str(destination),
        "runtime_created": runtime_change is not None and runtime_change["backup"] is None,
        "runtime_change": runtime_change,
        "runtime_target": str(runtime_target),
        "runtime_sha256": plan.report["runtime_sha256"],
        "engine_sha256": plan.report["engine_sha256"],
        "mod_order": plan.report["mod_order"],
        "build_id": plan.report["build_id"],
        "package_backup": "package-" + token,
        "old_manifest_sha256": old_manifest_hash,
        "new_manifest_sha256": digest(_read(stage / "mce-manifest.json", stage)),
        "legacy_moves": legacy_moves,
        "config_created": config_created,
    }
    prior_name = "previous-state-" + token + ".json" if previous_state else None
    if previous_state is not None:
        assert prior_name is not None
        _write_new(state_dir / prior_name, previous_state)
    pending = state_dir / "pending.json"
    journal = {**updated, "had_destination": destination.exists(), "previous_state": prior_name}
    _write_new(pending, (json.dumps(journal, indent=2) + "\n").encode())
    try:
        if game_running():
            raise InputError("Игра запущена; применение остановлено")
        if destination.exists():
            _verified_package(destination)
            os.rename(destination, state_dir / updated["package_backup"])
        os.rename(stage, destination)
        for move in updated["legacy_moves"]:
            os.rename(mods / move["name"], state_dir / move["cache"])
        # Commit the recovery journal before changing runtime/configuration.
        encoded = (json.dumps(updated, indent=2) + "\n").encode()
        if previous_state is not None:
            _replace_checked(state_file, encoded, previous_state)
        else:
            _write_new(state_file, encoded)
        sdk_settings.install(user, state_dir, config_created)
        sdk_runtime.install(runtime_change)
        if plan.runtime_source is not None and (
            digest(_read(runtime_target, plan.game.root)) != plan.report["runtime_sha256"]
        ):
            raise InputError("Установленный загрузчик изменился")
        if game_running():
            raise InputError("Игра запущена; применение остановлено")
        if (
            not snapshot_unchanged(plan.scan)
            or digest(_read(plan.game.executable, plan.game.executable.parent))
            != plan.report["game_sha256"]
        ):
            raise InputError("Игра или моды обновились во время применения")
        _replace_checked(user / "mods.xml", new, old)
        pending.unlink()
    except (OSError, InputError):
        _recover_pending(user)
        raise
    sdk_settings.cleanup(user, state_dir, config_created, remove_targets=False)
    # Keep only the current undo payload; never prune source or unrecognized directories.
    obsolete = [state.get("package_backup", "")]
    obsolete += [move["cache"] for move in state.get("legacy_moves", [])]
    for name in obsolete:
        if not re.fullmatch(r"(?:package|legacy)-[0-9a-f]{32}", name):
            continue
        cached = _cache_path(state_dir, name)
        if cached.exists():
            try:
                root = input_root(cached)
                if root.parent != state_dir:
                    raise InputError("Неверный каталог старой резервной сборки")
                _verified_package(root)
                shutil.rmtree(root)
            except (OSError, InputError):
                pass  # Optional cache pruning must not turn a committed update into failure.
    return destination


def _restore_previous_locked(
    user_dir: Path, *, game_running: Callable[[], bool] = _running
) -> None:
    if game_running():
        raise InputError("Закройте игру перед восстановлением")
    user = input_root(user_dir)
    state_dir = input_root(user / "cc2-mce")
    _recover_pending(user)
    state_path = state_dir / "activation.json"
    state = json.loads(_read(state_path, state_dir))
    name = state["backup"]
    normalize_logical_path(name)
    if "/" in name or state.get("owner") != "cc2-mce":
        raise InputError("Неверный журнал восстановления")
    backup = _read(state_dir / name, state_dir)
    current = _read(user / "mods.xml", user)
    if (
        current == backup
        and digest(backup) == state["backup_sha256"]
        and "package_backup" not in state
    ):
        state_path.unlink()
        return
    current_matches = digest(current) == state["applied_sha256"]
    if not current_matches:
        # CC2 rewrites indentation/quotes on exit. Accept only the proven one-node grammar,
        # identical root attributes and exactly the package this journal activated.
        now_root = _parse_activation(current)
        old_root = _parse_activation(backup)
        current_matches = (
            len(now_root) == len(old_root) == 1
            and now_root.attrib == old_root.attrib
            and active_paths(user) == ((Path(state["package"]),) if state["mod_order"] else ())
            and all(
                not (node.text or "").strip() and not (node.tail or "").strip()
                for node in now_root.iter()
            )
        )
    if digest(backup) != state["backup_sha256"] or not current_matches:
        raise InputError("Настройки изменены вне программы. Автоматический откат остановлен.")
    _parse_activation(backup)
    if "package_backup" in state:
        journal = {
            **state,
            "applied_sha256": digest(current),
            "had_destination": state["old_manifest_sha256"] is not None,
            "previous_state": None,
        }
        _write_new(state_dir / "pending.json", (json.dumps(journal, indent=2) + "\n").encode())
        _recover_pending(user)
        return
    _replace_checked(user / "mods.xml", backup, current)
    state_path.unlink()


def apply_plan(
    plan: PackagePlan,
    user_dir: Path,
    *,
    game_running: Callable[[], bool] = _running,
) -> Path:
    if game_running():
        raise InputError("Закройте игру перед применением модов")
    user = input_root(user_dir)
    for protected in (*plan.scan.roots, plan.game.root):
        if user.is_relative_to(protected):
            raise InputError("Настройки/выход не могут находиться внутри исходников")
    destination = user / "mods" / OUTPUT_FOLDER
    for protected in (mod.root for mod in plan.scan.mods):
        if destination.is_relative_to(protected) or protected.is_relative_to(destination):
            raise InputError("Выходной пакет пересекается с исходниками")
    with activation_lock(user):
        return _apply_plan_locked(plan, user, game_running=game_running)


def restore_previous(user_dir: Path, *, game_running: Callable[[], bool] = _running) -> None:
    if game_running():
        raise InputError("Закройте игру перед восстановлением")
    with activation_lock(user_dir):
        _restore_previous_locked(user_dir, game_running=game_running)


def recover_interrupted(user_dir: Path, *, game_running: Callable[[], bool] = _running) -> None:
    """Repair our pending transaction on startup; ordinary discovery remains read-only."""
    if not (user_dir / "cc2-mce/pending.json").exists():
        return
    if game_running():
        raise InputError("Закройте игру — восстановим незавершённую сборку автоматически.")
    with activation_lock(user_dir):
        _recover_pending(input_root(user_dir))
