"""User-requested local test: preserve evidence, package AI Bridge + Island Airfields."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from cc2_mce.discovery import discover
from cc2_mce.installation import find_installations
from cc2_mce.toolchain import bundled_tools
from cc2_mce.workflow import analyze, apply_plan, game_user_dir

root = Path(__file__).resolve().parents[1]
evidence = root / "build/evidence" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
evidence.mkdir(parents=True)
locations = find_installations()
game = locations.games[0]
user = game_user_dir()
for path in [user / "mods.xml", user / "settings.xml", user / "persistent_data.xml",
             game.root / "cc2x.log"]:
    if path.is_file():
        shutil.copy2(path, evidence / (path.name + ".before"))
scan = discover([*locations.workshop_roots, game.libraries_dir])
selected = [mod.id for mod in scan.mods if mod.id in {"3828182483", "3826940003"}]
plan = analyze(game, scan, selected, tools=bundled_tools())
if plan.blockers:
    raise RuntimeError(json.dumps(plan.blockers))
package = apply_plan(plan, user)
(evidence / "package-report.json").write_text(json.dumps(plan.report, indent=2) + "\n")
(evidence / "locations.json").write_text(json.dumps({
    "package": str(package), "game": str(game.root), "user": str(user),
}, indent=2) + "\n")
print(json.dumps({"evidence": str(evidence), "package": str(package),
                  "files": len(plan.payload), "runtime_installed": (game.root / "dinput8.dll").is_file()}))
