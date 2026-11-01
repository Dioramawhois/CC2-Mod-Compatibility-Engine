"""Record before/after evidence of the installed GUI's automatic output migration.

Read-only toward the game and sources; writes evidence only in this checkout's build tree.
"""

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from cc2_mce.filesystem import digest
from cc2_mce.installation import find_installations
from cc2_mce.reports import engine_hash
from cc2_mce.workflow import _verified_package, active_paths, game_user_dir

root = Path(__file__).resolve().parents[1]
user = game_user_dir()
game = find_installations().games[0]
if sys.argv[1:] == ["before"]:
    evidence = root / "build/evidence" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence.mkdir(parents=True)
    paths = active_paths(user)
    assert len(paths) == 1
    report = _verified_package(paths[0])
    shutil.copy2(user / "mods.xml", evidence / "mods.xml.before")
    shutil.copy2(game.root / "cc2x.log", evidence / "cc2x.log.before")
    (evidence / "before.json").write_text(json.dumps({
        "package": str(paths[0]), "report": report,
        "binary_sha256": digest((game.root / "CC2Engine.exe").read_bytes())
                         if (game.root / "CC2Engine.exe").is_file() else None,
    }, indent=2) + "\n", encoding="utf-8")
    (root / "build/auto-evidence-path.txt").write_text(str(evidence), encoding="utf-8")
    print(json.dumps({"evidence": str(evidence), "selected": report["mod_order"]}))
elif sys.argv[1:] in (["after"], ["current"]):
    strict = sys.argv[1:] == ["after"]
    evidence = Path((root / "build/auto-evidence-path.txt").read_text(encoding="utf-8"))
    before = json.loads((evidence / "before.json").read_text(encoding="utf-8"))
    package = user / "mods/CC2-MCE"
    assert active_paths(user) == (package,)
    report = _verified_package(package)
    same_selection = report["mod_order"] == before["report"]["mod_order"]
    if strict:
        assert same_selection
    assert report["engine_sha256"] == engine_hash()
    same_payload = {f["logical_path"]: f["output_sha256"] for f in report["files"]} == {
        f["logical_path"]: f["output_sha256"] for f in before["report"]["files"]
    }
    if strict:
        assert same_payload
    legacy_output = Path(before["package"]) != package
    if legacy_output:
        assert not Path(before["package"]).exists(), "Legacy output was not archived"
    assert [p.name for p in (user / "mods").glob("CC2-MCE*") if p.is_dir()] == ["CC2-MCE"]
    (evidence / "package-report.json").write_text(json.dumps(report, indent=2) + "\n")
    (evidence / "locations.json").write_text(json.dumps({
        "package": str(package), "game": str(game.root), "user": str(user),
    }, indent=2) + "\n")
    (evidence / "auto-apply.json").write_text(json.dumps({
        "scope": "read-only validation of installed frozen GUI's current applied selection",
        "matches_pre_update_selection": same_selection,
        "matches_pre_update_payload": same_payload,
        "pre_update_mod_order": before["report"]["mod_order"],
        "single_fixed_output": True, "legacy_output_archived": legacy_output,
        "engine_sha256": report["engine_sha256"],
        "mod_order": report["mod_order"],
    }, indent=2) + "\n")
    print(json.dumps({"package": str(package), "mod_order": report["mod_order"],
                      "payload_files": len(report["files"])}))
else:
    raise SystemExit("Expected before, after or current")
