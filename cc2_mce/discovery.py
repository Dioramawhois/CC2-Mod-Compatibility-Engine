from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from xml.etree import ElementTree

from cc2_mce.diagnostics import Diagnostic, error_diagnostic
from cc2_mce.errors import DiagnosticError, InputError
from cc2_mce.filesystem import (
    SCAN_LIMITS,
    Budget,
    FileSnapshot,
    Limits,
    bounded_children,
    classify,
    digest,
    input_root,
    is_link,
    normalize_logical_path,
    read_regular,
    snapshot_regular,
    walk_regular,
)


@dataclass(frozen=True)
class FileRef:
    logical_path: str
    key: str
    sha256: str
    kind: str
    _payload: bytes | FileSnapshot

    @property
    def content(self) -> bytes:
        return self._payload if isinstance(self._payload, bytes) else self._payload.read()

    @property
    def size(self) -> int:
        return len(self._payload) if isinstance(self._payload, bytes) else self._payload.size

    def report(self) -> dict[str, object]:
        return {
            "logical_path": self.logical_path,
            "sha256": self.sha256,
            "kind": self.kind,
            "size": self.size,
        }


@dataclass(frozen=True)
class ModRef:
    id: str
    name: str
    root: Path
    sha256: str
    files: tuple[FileRef, ...]
    package_kind: str = "mod"
    package_id: str = ""
    dependencies: tuple[str, ...] = ()
    sdk: str | None = None
    api: int = 0
    metadata: bytes = b""
    root_files: tuple[FileRef, ...] = ()
    lua_api: int = 0
    framework_api: int = 0

    def report(self) -> dict[str, object]:
        value: dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "sha256": self.sha256,
            "files": [item.report() for item in self.files],
            "package_kind": self.package_kind,
            "package_id": self.package_id or self.id,
            "dependencies": list(self.dependencies),
            "sdk": self.sdk,
            "api": self.api,
        }
        if self.root_files:
            value["root_files"] = [item.report() for item in self.root_files]
        if self.lua_api:
            value["lua_api"] = self.lua_api
        if self.framework_api:
            value["framework_api"] = self.framework_api
        return value


@dataclass(frozen=True)
class Scan:
    roots: tuple[Path, ...]
    mods: tuple[ModRef, ...]
    fingerprint: str
    limits: Limits
    issues: tuple[Diagnostic, ...] = ()
    collect_issues: bool = False
    requested_roots: tuple[Path, ...] = ()

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def require_available(
        self, selected: Iterable[str], *, provided_dependencies: frozenset[str] = frozenset()
    ) -> None:
        pending = [(key, False) for key in selected]
        checked: set[tuple[str, bool]] = set()
        while pending:
            key, dependency = pending.pop()
            if (key, dependency) in checked:
                continue
            checked.add((key, dependency))
            exact = [mod for mod in self.mods if mod.id == key]
            available = exact or [mod for mod in self.mods if (mod.package_id or mod.id) == key]
            if available:
                if len(available) == 1:
                    pending.extend((required, True) for required in available[0].dependencies)
                continue  # The normal resolver handles ambiguous versions and runtime provision.
            if dependency and key in provided_dependencies:
                # Verified infrastructure supplies a dependency, never an explicit source.
                continue
            issue = next(
                (item for item in self.issues if key in {item.source_id, item.package_id}), None
            )
            if issue is None:
                issue = next(
                    (item for item in self.issues if item.code == "discovery_global_limit"), None
                )
            if issue is not None:
                raise DiagnosticError(issue)


def fingerprint(value: object) -> str:
    return digest(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _metadata(
    data: bytes, fallback: str
) -> tuple[str, str, str, tuple[str, ...], str | None, int, int, int]:
    try:
        text = data.decode("utf-8-sig").lstrip()
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.IGNORECASE):
            raise InputError("Unsafe metadata XML declarations")
        root = ElementTree.fromstring(text)
        name = root.attrib.get("name", fallback)
        if root.tag != "data" or len(name) > 256 or any(ord(char) < 32 for char in name):
            raise InputError("Invalid mod metadata root/name")
        sections = root.findall("cc2mce")
        if not sections:
            return root.attrib.get("name", fallback), "mod", fallback, (), None, 0, 0, 0
        if len(sections) != 1:
            raise InputError("Duplicate CC2-MCE package declaration")
        section = sections[0]
        if (
            section.get("schema") != "1"
            or section.get("type") not in {"mod", "library"}
            or set(section.attrib)
            - {"schema", "type", "id", "sdk", "api", "lua_api", "framework_api"}
        ):
            raise InputError("Unsupported CC2-MCE package declaration")
        package_id = section.get("id", fallback)
        normalize_logical_path(package_id)
        if "/" in package_id:
            raise InputError("Package id must be a single component")
        api_value = section.get("api", "0")
        if not api_value.isascii() or not api_value.isdigit() or not 0 <= int(api_value) <= 10000:
            raise InputError("Invalid SDK API version")
        lua_api_value = section.get("lua_api", "0")
        if (
            not lua_api_value.isascii()
            or not lua_api_value.isdigit()
            or not 0 <= int(lua_api_value) <= 10000
        ):
            raise InputError("Invalid SDK Lua API version")
        framework_api_value = section.get("framework_api", "0")
        if (
            not framework_api_value.isascii()
            or not framework_api_value.isdigit()
            or len(framework_api_value) > 5
            or not 0 <= int(framework_api_value) <= 10000
        ):
            raise InputError("Invalid SDK framework API version")
        sdk = section.get("sdk")
        if sdk not in {None, "cc2x"}:
            raise InputError("Unknown SDK declaration")
        dependencies = []
        for child in section:
            value = child.get("id", "")
            if child.tag != "requires" or set(child.attrib) != {"id"} or len(child):
                raise InputError("Unsupported package dependency")
            normalize_logical_path(value)
            if "/" in value or value == package_id or value in dependencies:
                raise InputError("Invalid/duplicate package dependency")
            dependencies.append(value)
        return (
            root.attrib.get("name", fallback),
            section.attrib["type"],
            package_id,
            tuple(dependencies),
            sdk,
            int(api_value),
            int(lua_api_value),
            int(framework_api_value),
        )
    except (UnicodeError, ElementTree.ParseError) as exc:
        raise InputError("Invalid metadata XML") from exc


def _read_mod(root: Path, budget: Budget, metadata_budget: Budget) -> ModRef | None:
    source_id, name, package_id = root.name, root.name, ""
    resource = ""
    metadata = b""
    files: list[FileRef] = []
    root_files: list[FileRef] = []
    observed: dict[str, tuple[int, int, int, int]] = {}

    def observe(path: Path) -> None:
        info = path.lstat()
        observed[path.relative_to(root).as_posix()] = (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
        )

    try:
        root = input_root(root)
        if re.fullmatch(r"CC2-MCE(?:-[0-9a-f]{16})?", root.name):
            manifest = root / "mce-manifest.json"
            if manifest.exists():
                resource = "mce-manifest.json"
                observe(manifest)
                try:
                    generated = json.loads(read_regular(manifest, root, metadata_budget))
                except (ValueError, UnicodeError, RecursionError) as exc:
                    raise InputError("Invalid generated package manifest") from exc
                if isinstance(generated, dict) and generated.get("owner") == "cc2-mce":
                    return None  # Managed output is never a source for its own rebuild.
        mod_id, _ = normalize_logical_path(root.name)
        source_id = mod_id
        content = root / "content"
        resource = "content"
        if content.exists() or content.is_symlink():
            input_root(content)
            observe(content)
        if (root / "mod.xml").exists() or (root / "mod.xml").is_symlink():
            resource = "mod.xml"
            observe(root / "mod.xml")
            metadata = read_regular(root / "mod.xml", root, metadata_budget)
        name, package_kind, package_id, dependencies, sdk, api, lua_api, framework_api = (
            _metadata(metadata, mod_id) if metadata else (mod_id, "mod", mod_id, (), None, 0, 0, 0)
        )
        local_keys: set[str] = set()
        resource = "content"
        for path in walk_regular(content, budget) if content.exists() else []:
            resource = path.relative_to(root).as_posix()
            logical, key = normalize_logical_path(path.relative_to(content).as_posix())
            if key in local_keys:
                raise InputError("Logical path case/Unicode collision")
            local_keys.add(key)
            observe(path)
            snapshot = snapshot_regular(path, root, budget)
            files.append(
                FileRef(logical, key, snapshot.sha256, classify(logical, snapshot.header), snapshot)
            )
        files.sort(key=lambda item: item.key)
        if (root / "bridge.json").exists() or (root / "bridge.json").is_symlink():
            resource = "bridge.json"
            for child in bounded_children(root, budget):
                if child.name in {"content", ".git", "mod.xml"}:
                    continue
                if is_link(child):
                    resource = child.relative_to(root).as_posix()
                    raise InputError("Input link/junction forbidden")
                resource = child.relative_to(root).as_posix()
                entries = walk_regular(input_root(child), budget) if child.is_dir() else [child]
                for path in entries:
                    resource = path.relative_to(root).as_posix()
                    logical, key = normalize_logical_path(path.relative_to(root).as_posix())
                    if (
                        path.suffix.casefold()
                        not in {".lua", ".xml", ".png", ".mesh", ".txtr", ".txt", ".glsl", ".dll"}
                        and key != "bridge.json"
                    ):
                        continue
                    if any(item.key == key for item in root_files):
                        raise InputError("Logical path case/Unicode collision")
                    observe(path)
                    snapshot = snapshot_regular(path, root, budget)
                    root_files.append(
                        FileRef(
                            logical,
                            key,
                            snapshot.sha256,
                            classify(logical, snapshot.header),
                            snapshot,
                        )
                    )
            root_files.sort(key=lambda item: item.key)
        source_hash = fingerprint(
            {
                "metadata": digest(metadata),
                "files": [item.report() for item in files],
                **({"root_files": [item.report() for item in root_files]} if root_files else {}),
            }
        )
        return ModRef(
            mod_id,
            name,
            root,
            source_hash,
            tuple(files),
            package_kind,
            package_id,
            dependencies,
            sdk,
            api,
            metadata,
            tuple(root_files),
            lua_api,
            framework_api,
        )
    except (InputError, OSError, ValueError, RecursionError) as exc:
        revision = fingerprint(
            {
                "metadata": digest(metadata),
                "files": [item.report() for item in (*files, *root_files)],
                "observed": observed,
            }
        )
        raise DiagnosticError(
            error_diagnostic(
                exc,
                stage="discovery",
                source_id=source_id,
                source_name=name,
                source_path=root,
                resource_path=resource,
                package_id=package_id,
                source_revision=revision,
            )
        ) from exc


def _global_limit(exc: BaseException) -> bool:
    return str(exc).startswith(("Scan entry limit exceeded", "Input total byte limit exceeded"))


def discover(
    roots: list[Path], *, limits: Limits | None = None, collect_issues: bool = False
) -> Scan:
    limits = limits or SCAN_LIMITS
    budget = Budget(limits)

    class MetadataBudget(Budget):
        def consume(self, size: int, *, label: str | None = None) -> None:
            budget.consume(size, label=label)
            super().consume(size, label=label)

    metadata_budget = MetadataBudget(Limits())
    requested_roots = tuple(dict.fromkeys(root.absolute() for root in roots))
    canonical: list[Path] = []
    candidates: list[Path] = []
    issues: list[Diagnostic] = []
    exhausted = False
    for requested in requested_roots:
        try:
            root = input_root(requested)
            if root in canonical:
                continue
            canonical.append(root)
            if (root / "content").exists() or (root / "bridge.json").exists():
                candidates.append(root)
                continue
            for child in bounded_children(root, budget):
                if is_link(child):
                    if not collect_issues:
                        raise InputError("Input link/junction forbidden")
                    candidates.append(child)  # The package reader rejects it without following it.
                elif child.is_dir() and (
                    (child / "content").exists() or (child / "bridge.json").exists()
                ):
                    candidates.append(child)
        except (InputError, OSError) as exc:
            if not collect_issues:
                if isinstance(exc, OSError):
                    raise InputError("Mod collection cannot be read") from exc
                raise
            issues.append(error_diagnostic(exc, stage="discovery", source_path=requested))
            if _global_limit(exc):
                issues[-1] = replace(issues[-1], code="discovery_global_limit")
                exhausted = True
                break

    ordered = sorted(set(candidates), key=lambda path: (path.name, str(path)))
    owners: dict[str, list[Path]] = {}
    eligible: list[Path] = []
    for root in ordered:
        try:
            _, identity = normalize_logical_path(root.name)
        except InputError as exc:
            if not collect_issues:
                raise
            issues.append(
                error_diagnostic(exc, stage="discovery", source_name=root.name, source_path=root)
            )
            continue
        owners.setdefault(identity, []).append(root)
        eligible.append(root)

    mods: list[ModRef] = []
    for root in eligible if not exhausted else []:
        try:
            mod = _read_mod(root, budget, metadata_budget)
            if mod is None:
                owners[normalize_logical_path(root.name)[1]].remove(root)
            else:
                mods.append(mod)
        except DiagnosticError as exc:
            if not collect_issues:
                raise
            issue = exc.diagnostic
            if _global_limit(exc):
                issue = replace(issue, code="discovery_global_limit")
            issues.append(issue)
            if _global_limit(exc):
                break  # No additional resource reads after exhausting the shared budget.

    duplicates = {identity for identity, paths in owners.items() if len(paths) > 1}
    if duplicates and not collect_issues:
        raise InputError("Duplicate mod id")
    by_root = {mod.root: mod for mod in mods}
    earlier_issues = {item.source_path: item for item in issues}
    for identity in sorted(duplicates):
        cause = "Duplicate mod id: " + ", ".join(str(path) for path in owners[identity])
        for root in owners[identity]:
            known = by_root.get(root)
            earlier = earlier_issues.get(str(root))
            issues.append(
                error_diagnostic(
                    InputError(cause),
                    stage="discovery",
                    code="duplicate_mod_id",
                    source_id=root.name,
                    source_name=known.name
                    if known
                    else earlier.source_name
                    if earlier
                    else root.name,
                    source_path=root,
                    package_id=known.package_id if known else earlier.package_id if earlier else "",
                    source_revision=(
                        known.sha256 if known else earlier.source_revision if earlier else ""
                    ),
                )
            )
    mods = [mod for mod in mods if normalize_logical_path(mod.id)[1] not in duplicates]

    spellings: dict[str, dict[str, set[str]]] = {}
    for mod in mods:
        for item in mod.files:
            spellings.setdefault(item.key, {}).setdefault(item.logical_path, set()).add(mod.id)
    collisions = {key: values for key, values in spellings.items() if len(values) > 1}
    if collisions and not collect_issues:
        raise InputError("Logical path case/Unicode collision")
    rejected: set[str] = set()
    by_id = {mod.id: mod for mod in mods}
    for key, variants in sorted(collisions.items()):
        participants = set().union(*variants.values())
        for source_id in sorted(participants):
            mod = by_id[source_id]
            rejected.add(mod.id)
            issues.append(
                error_diagnostic(
                    InputError("Logical path case/Unicode collision: " + ", ".join(variants)),
                    stage="discovery",
                    code="logical_path_collision",
                    source_id=mod.id,
                    source_name=mod.name,
                    source_path=mod.root,
                    resource_path=key,
                    package_id=mod.package_id,
                    source_revision=mod.sha256,
                )
            )
    mods = [mod for mod in mods if mod.id not in rejected]
    reports = [mod.report() for mod in mods]
    identity = fingerprint(
        {"mods": reports, "issues": [item.report() for item in issues]} if issues else reports
    )
    return Scan(
        tuple(canonical),
        tuple(mods),
        identity,
        limits,
        tuple(issues),
        collect_issues,
        requested_roots,
    )


def snapshot_unchanged(scan: Scan) -> bool:
    try:
        current = discover(
            list(scan.requested_roots or scan.roots),
            limits=scan.limits,
            collect_issues=scan.collect_issues,
        )
        return current.fingerprint == scan.fingerprint
    except InputError:
        return False
