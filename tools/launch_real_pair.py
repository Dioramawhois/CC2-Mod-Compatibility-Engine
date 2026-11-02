"""Launch the actual game for the specifically authorized combined-mod test."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from cc2_mce.installation import find_installations
from cc2_mce.workflow import _running, game_user_dir

root = Path(__file__).resolve().parents[1]
evidence = Path((root / "build/auto-evidence-path.txt").read_text(encoding="utf-8"))
assert evidence.resolve().parent == (root / "build/evidence").resolve()
game = find_installations().games[0]
if _running():
    raise RuntimeError("The game is already running; do not launch a second instance")
saves = game_user_dir() / "saved_games"
backup = evidence / "saved_games.before"
if saves.exists() and not backup.exists():
    shutil.copytree(saves, backup)
output = (evidence / "game.stdout.log").open("wb")
process = subprocess.Popen(
    [str(game.executable)], cwd=game.root, stdout=output, stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW,
    env={**os.environ, "SteamAppId": "1489630", "SteamGameId": "1489630"},
)
(evidence / "game-pid.json").write_text(json.dumps({"pid": process.pid}) + "\n")
print(json.dumps({"pid": process.pid, "evidence": str(evidence)}))
