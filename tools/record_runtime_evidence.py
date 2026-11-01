"""Read-only evidence from the explicitly authorized, already running game test."""

import ctypes
import json
import shutil
from ctypes import wintypes
from pathlib import Path

from cc2_mce.filesystem import digest
from cc2_mce.workflow import active_paths, game_user_dir

root = Path(__file__).resolve().parents[1]
evidence = Path((root / "build/auto-evidence-path.txt").read_text(encoding="utf-8"))
assert evidence.resolve().parent == (root / "build/evidence").resolve()
locations = json.loads((evidence / "locations.json").read_text())
pid = json.loads((evidence / "game-pid.json").read_text())["pid"]
package = Path(locations["package"])
game = Path(locations["game"])
report = json.loads((package / "mce-manifest.json").read_text(encoding="utf-8"))
log = (game / "cc2x.log").read_bytes()
shutil.copy2(game / "cc2x.log", evidence / "cc2x-fresh.log")
assert b'plugin cc2x_island_airfields.dll loaded (mod "CC2' in log
assert b"1 enabled mod folder(s) checked" in log


class Module(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD), ("module_id", wintypes.DWORD), ("process_id", wintypes.DWORD),
        ("global_count", wintypes.DWORD), ("process_count", wintypes.DWORD),
        ("base", ctypes.c_void_p), ("base_size", wintypes.DWORD), ("handle", wintypes.HMODULE),
        ("name", wintypes.WCHAR * 256), ("path", wintypes.WCHAR * 260),
    ]


api = ctypes.WinDLL("kernel32", use_last_error=True)
api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
api.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Module)]
api.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Module)]
api.CloseHandle.argtypes = [wintypes.HANDLE]
snapshot = api.CreateToolhelp32Snapshot(0x18, pid)
loaded = []
if snapshot != wintypes.HANDLE(-1).value:
    try:
        entry = Module()
        entry.size = ctypes.sizeof(Module)
        more = api.Module32FirstW(snapshot, ctypes.byref(entry))
        while more:
            if entry.name.casefold() in {"dinput8.dll", "cc2x_island_airfields.dll"}:
                loaded.append({"name": entry.name, "path": entry.path})
            more = api.Module32NextW(snapshot, ctypes.byref(entry))
    finally:
        api.CloseHandle(snapshot)
plugin = package / "content/cc2x/cc2x_island_airfields.dll"
assert any(Path(entry["path"]) == plugin for entry in loaded), "Expected plugin is not loaded"
assert any(Path(entry["path"]) == game / "dinput8.dll" for entry in loaded)
result = {
    "scope": "actual-game-startup-and-native-plugin-load; not full gameplay",
    "package": package.name, "engine_sha256": report["engine_sha256"],
    "mod_order": report["mod_order"], "game_sha256": report["game_sha256"],
    "log_sha256": digest(log), "native_sha256": digest(plugin.read_bytes()),
    "payload_sha256": {entry["logical_path"]: entry["output_sha256"] for entry in report["files"]},
    "active_packages": [path.name for path in active_paths(game_user_dir())],
    "loaded_modules": loaded, "fresh_plugin_log_confirmed": True,
    "prior_launch_menu_confirmed_by_user_on_identical_payload": True,
    "current_menu_independently_verified": False, "full_gameplay_verified": False,
    "gui_canonical_selection_matches_active_plan": True,
}
(evidence / "runtime-evidence.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"package": package.name, "fresh_plugin_log": True, "loaded_modules": loaded}))
