"""Install the specifically requested local build, preserving the prior owned executable."""

import json
import os
import uuid
from pathlib import Path

from cc2_mce import APP_EXECUTABLE

from cc2_mce.filesystem import digest, input_root
from cc2_mce.installation import find_installations
from cc2_mce.reports import engine_hash
from cc2_mce.workflow import game_user_dir

root = Path(__file__).resolve().parents[1]
game = find_installations().games[0]
directory = input_root(game.root)
artifact = root / "dist" / APP_EXECUTABLE
payload = artifact.read_bytes()
report = json.loads(artifact.with_suffix(".build.json").read_text())
assert digest(payload) == report["artifact_sha256"]
assert engine_hash() == report["engine_sha256"]
backups = game_user_dir() / "cc2-mce/executable-backups"
backups.mkdir(parents=True, exist_ok=True)
input_root(backups)
legacy = directory / "CC2ModLoader-0.1.0.exe"
old_engine = directory / "CC2Engine.exe"
previous_path = root / "dist/CC2ModLoader-0.1.0.exe"
previous = previous_path.read_bytes() if previous_path.is_file() else None
base_hash = digest(previous) if previous is not None else None
owned_hashes = {digest(payload)}
if base_hash is not None:
    owned_hashes.add(base_hash)
ledger = backups.parent / "binary-deployment.json"
if ledger.exists():
    prior = json.loads(ledger.read_text(encoding="utf-8"))
    if prior.get("owner") == "cc2-mce":
        owned_hashes.add(prior["source_sha256"])
        if isinstance(prior.get("base_sha256"), str):
            owned_hashes.add(prior["base_sha256"])
            base_hash = base_hash or prior["base_sha256"]
if legacy.exists() and digest(legacy.read_bytes()) not in owned_hashes:
    raise RuntimeError("The legacy executable is not the previous owned build; preserve it")
if old_engine.exists() and digest(old_engine.read_bytes()) not in owned_hashes:
    raise RuntimeError("The old Engine executable is not an owned build; preserve it")
installed = []
for target in [directory / APP_EXECUTABLE, *([legacy] if legacy.exists() else [])]:
    if target.exists():
        old = target.read_bytes()
        if target.name == APP_EXECUTABLE and digest(old) not in owned_hashes:
            raise RuntimeError("A different ModLoader executable already exists; preserve it")
        backup = backups / (digest(old) + ".exe")
        if not backup.exists():
            with backup.open("xb") as stream:
                stream.write(old)
    temporary = directory / (".cc2-engine-" + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
        os.replace(temporary, target)
        assert digest(target.read_bytes()) == digest(payload)
        installed.append(str(target))
    finally:
        temporary.unlink(missing_ok=True)
if old_engine.exists():
    old = old_engine.read_bytes()
    if digest(old) not in owned_hashes:
        raise RuntimeError("The old Engine executable changed; preserve it")
    backup = backups / (digest(old) + ".exe")
    if not backup.exists():
        with backup.open("xb") as stream:
            stream.write(old)
    old_engine.unlink()
old_artifact = root / "dist/CC2Engine.exe"
if old_artifact.is_file() and digest(old_artifact.read_bytes()) in owned_hashes:
    input_root(old_artifact.parent)
    archive = root / "build/previous-builds"
    input_root(archive.parent)
    archive.mkdir(exist_ok=True)
    input_root(archive)
    archived = archive / ("CC2Engine-" + uuid.uuid4().hex)
    assert old_artifact.resolve().parent == (root / "dist").resolve()
    assert archived.parent.resolve() == archive.resolve()
    os.rename(old_artifact, archived.with_suffix(".exe"))
    old_report = old_artifact.with_suffix(".build.json")
    if old_report.exists():
        os.rename(old_report, archived.with_suffix(".build.json"))
(backups.parent / "binary-deployment.json").write_text(json.dumps({
    "owner": "cc2-mce", "source_sha256": digest(payload), "engine_sha256": engine_hash(),
    "base_sha256": base_hash, "mod_order": [], "installed": installed,
}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"installed": installed, "sha256": digest(payload)}))
