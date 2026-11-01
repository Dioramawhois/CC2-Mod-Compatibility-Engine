"""Attach fresh, scope-limited local acceptance evidence to the build sidecar."""

import json
import sys
from pathlib import Path

from cc2_mce.filesystem import digest
from cc2_mce.reports import engine_hash

root = Path(__file__).resolve().parents[1]
evidence = Path((root / "build/auto-evidence-path.txt").read_text(encoding="utf-8"))
assert evidence.resolve().parent == (root / "build/evidence").resolve()
auto = json.loads((evidence / "auto-apply.json").read_text())
ui_only = "--ui-only" in sys.argv
runtime = {} if ui_only else json.loads((evidence / "runtime-evidence.json").read_text())
package = json.loads((evidence / "package-report.json").read_text())
sidecar = root / "dist/CC2Engine.build.json"
report = json.loads(sidecar.read_text(encoding="utf-8"))
assert engine_hash() == report["engine_sha256"] == auto["engine_sha256"]
if not ui_only:
    assert runtime["engine_sha256"] == report["engine_sha256"]
assert digest((root / "dist/CC2Engine.exe").read_bytes()) == report["artifact_sha256"]
if not ui_only:
    assert runtime["fresh_plugin_log_confirmed"] is True
    assert runtime["full_gameplay_verified"] is False
report.update({
    "installable_mod_verified": True,
    "game_runtime_tested": not ui_only,
    "full_gameplay_verified": False,
    "tested_mod_order": package["mod_order"],
    "game_sha256": package["game_sha256"],
    "base_sha256": {entry["logical_path"]: entry["baseline_sha256"]
                    for entry in package["files"]},
    "auto_apply_evidence": str((evidence / "auto-apply.json").relative_to(root)),
    "verified_scope": "installed GUI's current applied selection; checkbox rejection UI regression tests"
                      if ui_only else "automatic GUI rebuild and fresh native plugin load; not gameplay",
})
if not ui_only:
    report["runtime_evidence"] = str((evidence / "runtime-evidence.json").relative_to(root))
    report["runtime_evidence_sha256"] = digest((evidence / "runtime-evidence.json").read_bytes())
sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"version": report["version"], "package": "CC2-MCE",
                  "auto_apply_verified": True, "native_load_verified": not ui_only,
                  "full_gameplay_verified": False}))
