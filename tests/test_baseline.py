import json
from pathlib import Path

import pytest

from cc2_mce.baseline import load_baseline
from cc2_mce.errors import BaselineError, InputError
from cc2_mce.filesystem import digest


def baseline_fixture(root: Path, files: dict[str, bytes], *, kind: str = "synthetic") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for logical_path, content in files.items():
        target = root / "content" / logical_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        entries.append(
            {
                "logical_path": logical_path,
                "source_path": f"content/{logical_path}",
                "sha256": digest(content),
            }
        )
    manifest = {
        "schema_version": 1,
        "kind": kind,
        "complete": False,
        "game": {
            "version": "synthetic-v1" if kind == "synthetic" else "1.5.18",
            "executable_sha256": None,
        },
        "files": entries,
    }
    (root / "baseline-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_manifest_required_not_directory_guess(tmp_path: Path) -> None:
    with pytest.raises(BaselineError):
        load_baseline(tmp_path)


def test_hash_mapping_and_snapshot(tmp_path: Path) -> None:
    baseline_fixture(tmp_path, {"constants.txt": b"value=1\n"})
    base = load_baseline(tmp_path)
    assert base.kind == "synthetic"
    assert base.content_for("constants.txt") == b"value=1\n"
    assert base.unchanged()
    (tmp_path / "content/constants.txt").write_bytes(b"value=2\n")
    assert not base.unchanged()
    with pytest.raises(BaselineError, match="hash"):
        load_baseline(tmp_path)


def test_unmapped_resource_is_not_proven_absent(tmp_path: Path) -> None:
    baseline_fixture(tmp_path, {})
    assert not load_baseline(tmp_path).verified_for("missing.txt")


def test_game_manifest_requires_matching_executable(tmp_path: Path) -> None:
    baseline_fixture(tmp_path, {}, kind="game")
    with pytest.raises(BaselineError):
        load_baseline(tmp_path)
    executable = tmp_path / "game.exe"
    executable.write_bytes(b"synthetic executable, not run")
    manifest_path = tmp_path / "baseline-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["game"]["executable_sha256"] = digest(executable.read_bytes())
    manifest_path.write_text(json.dumps(manifest))
    assert load_baseline(tmp_path, game_executable=executable).kind == "game"
    executable.write_bytes(b"updated")
    with pytest.raises(BaselineError, match="fingerprint"):
        load_baseline(tmp_path, game_executable=executable)


def test_path_traversal_duplicate_json_and_collision(tmp_path: Path) -> None:
    baseline_fixture(tmp_path, {"constants.txt": b"value=1"})
    path = tmp_path / "baseline-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files"][0]["source_path"] = "../secret"
    path.write_text(json.dumps(manifest))
    with pytest.raises(InputError):
        load_baseline(tmp_path)
    path.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(InputError, match="Duplicate"):
        load_baseline(tmp_path)


def test_synthetic_cannot_claim_real_game(tmp_path: Path) -> None:
    baseline_fixture(tmp_path, {})
    path = tmp_path / "baseline-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["game"]["version"] = "1.5.18"
    path.write_text(json.dumps(manifest))
    with pytest.raises(BaselineError):
        load_baseline(tmp_path)
