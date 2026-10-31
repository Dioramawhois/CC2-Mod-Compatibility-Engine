from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cc2_mce.discovery import fingerprint
from cc2_mce.errors import BaselineError, InputError
from cc2_mce.filesystem import (
    Budget,
    Limits,
    digest,
    input_root,
    normalize_logical_path,
    read_regular,
)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError("Duplicate JSON key")
        result[key] = value
    return result


def parse_json(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(InputError("Invalid JSON")),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InputError("Invalid JSON document") from exc


@dataclass(frozen=True)
class Baseline:
    root: Path
    kind: str
    game: dict[str, object]
    files: dict[str, bytes]
    fingerprint: str
    game_executable: Path | None

    def content_for(self, logical_path: str) -> bytes | None:
        return self.files.get(normalize_logical_path(logical_path)[1])

    def verified_for(self, logical_path: str) -> bool:
        return normalize_logical_path(logical_path)[1] in self.files

    def unchanged(self) -> bool:
        try:
            return (
                load_baseline(self.root, game_executable=self.game_executable).fingerprint
                == self.fingerprint
            )
        except (InputError, BaselineError):
            return False

    def report(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "path_hint": "baseline",
            "fingerprint": self.fingerprint,
            "verified": self.kind == "game",
            "verification": "explicit-hash-mapping",
        }


def load_baseline(root: Path, *, game_executable: Path | None = None) -> Baseline:
    root = input_root(root)
    budget = Budget(Limits())
    manifest_path = root / "baseline-manifest.json"
    if not manifest_path.exists():
        raise BaselineError("baseline-manifest.json is required; SDK mapping is never guessed")
    raw = read_regular(manifest_path, root, budget)
    manifest = parse_json(raw)
    if not isinstance(manifest, dict):
        raise BaselineError("Baseline manifest must be an object")
    required = {"schema_version", "kind", "complete", "game", "files"}
    if (
        set(manifest) != required
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
    ):
        raise BaselineError("Unsupported baseline manifest fields/version")
    kind = manifest["kind"]
    if kind not in ("synthetic", "game") or manifest["complete"] is not False:
        raise BaselineError("Only explicit incomplete baseline mappings are supported")
    game = manifest["game"]
    if not isinstance(game, dict) or set(game) != {"version", "executable_sha256"}:
        raise BaselineError("Invalid baseline game identity")
    version = game["version"]
    if not isinstance(version, str) or not version:
        raise BaselineError("Baseline game version is required")
    if kind == "synthetic":
        if not version.startswith("synthetic-") or game["executable_sha256"] is not None:
            raise BaselineError("Synthetic baseline cannot assert real game identity")
    else:
        if game_executable is None:
            raise BaselineError("Game baseline requires --game-executable fingerprint check")
        executable_root = input_root(game_executable.parent)
        executable_data = read_regular(game_executable, executable_root, budget)
        if digest(executable_data) != game["executable_sha256"]:
            raise BaselineError("Game executable fingerprint mismatch")
    entries = manifest["files"]
    if not isinstance(entries, list) or len(entries) > budget.limits.max_entries:
        raise BaselineError("Invalid baseline file list")
    files: dict[str, bytes] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"logical_path", "source_path", "sha256"}:
            raise BaselineError("Invalid baseline file mapping")
        if not all(isinstance(entry[key], str) for key in entry):
            raise BaselineError("Baseline mapping fields must be strings")
        _, key = normalize_logical_path(entry["logical_path"])
        source, _ = normalize_logical_path(entry["source_path"])
        if key in files:
            raise InputError("Baseline logical path collision")
        data = read_regular(root / source, root, budget)
        if digest(data) != entry["sha256"]:
            raise BaselineError("Baseline file hash mismatch")
        files[key] = data
    return Baseline(
        root,
        kind,
        game,
        files,
        fingerprint({"manifest": digest(raw), "files": {k: digest(v) for k, v in files.items()}}),
        game_executable,
    )
