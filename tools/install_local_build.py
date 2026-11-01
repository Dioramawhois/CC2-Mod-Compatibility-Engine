"""Install the specifically requested local build, preserving the prior owned executable."""

import json
import os
import uuid
from pathlib import Path

from cc2_mce.filesystem import digest, input_root
from cc2_mce.installation import find_installations
from cc2_mce.reports import engine_hash
from cc2_mce.workflow import game_user_dir

root = Path(__file__).resolve().parents[1]
game = find_installations().games[0]
directory = input_root(game.root)
payload = (root / "dist/CC2Engine.exe").read_bytes()
report = json.loads((root / "dist/CC2Engine.build.json").read_text())
assert digest(payload) == report["artifact_sha256"]
assert engine_hash() == report["engine_sha256"]
backups = game_user_dir() / "cc2-mce/executable-backups"
backups.mkdir(parents=True, exist_ok=True)
input_root(backups)
legacy = directory / "CC2ModLoader-0.1.0.exe"
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
installed = []
for target in [directory / "CC2Engine.exe", *([legacy] if legacy.exists() else [])]:
    if target.exists():
        old = target.read_bytes()
        if target.name == "CC2Engine.exe" and digest(old) not in owned_hashes:
            raise RuntimeError("A different CC2Engine.exe already exists; preserve it")
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
(backups.parent / "binary-deployment.json").write_text(json.dumps({
    "owner": "cc2-mce", "source_sha256": digest(payload), "engine_sha256": engine_hash(),
    "base_sha256": base_hash, "mod_order": [], "installed": installed,
}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"installed": installed, "sha256": digest(payload)}))
