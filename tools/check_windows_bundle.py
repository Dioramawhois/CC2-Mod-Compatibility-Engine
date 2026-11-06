"""Check the frozen GUI; optionally record read-only inventory, never execute mods or the game."""

import ctypes
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from xml.etree import ElementTree as ET
from ctypes import wintypes
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

from cc2_mce import APP_EXECUTABLE, APP_NAME, __version__
from cc2_mce.discovery import discover
from cc2_mce.filesystem import Budget, Limits, input_root, read_regular
from cc2_mce.installation import find_installations
from cc2_mce.reports import engine_hash

root = Path(__file__).resolve().parents[1]
exe = root / "dist" / APP_EXECUTABLE
archive = CArchiveReader(str(exe))
names = {name.replace("\\", "/"): name for name in archive.toc}
sources = [*sorted((root / "cc2_mce").glob("*.py"))]
sources += list((root / "cc2_mce/schemas").glob("*.json"))
sources += list((root / "cc2_mce/profiles").glob("*.json"))
sources += [p for p in (root / "cc2_mce/runtime_data").rglob("*") if p.is_file()]
sources += [root / "cc2_mce/tools_data/manifest.json"]
hashes = {}
for source in sources:
    relative = source.relative_to(root).as_posix()
    assert relative in names, relative
    payload = archive.extract(names[relative])
    assert payload == source.read_bytes(), relative
    hashes[relative] = hashlib.sha256(payload).hexdigest()

tool_manifest = json.loads(archive.extract(names["cc2_mce/tools_data/manifest.json"]))
for relative, expected in tool_manifest["files"].items():
    archived_name = "cc2_mce/tools_data/" + relative
    assert archived_name in names, archived_name
    assert hashlib.sha256(archive.extract(names[archived_name])).hexdigest() == expected

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def windows():
    found = []

    @callback_type
    def visit(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return True
        try:
            image = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(image))
            if kernel32.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
                if Path(image.value) == exe:
                    title = ctypes.create_unicode_buffer(1024)
                    user32.GetWindowTextW(hwnd, title, len(title))
                    found.append((hwnd, title.value))
        finally:
            kernel32.CloseHandle(handle)
        return True

    user32.EnumWindows(visit, 0)
    return found


before = {hwnd for hwnd, _ in windows()}
env = os.environ.copy()
windows_directory = ctypes.create_unicode_buffer(32768)
assert kernel32.GetWindowsDirectoryW(windows_directory, len(windows_directory))
env["SystemRoot"] = windows_directory.value
env["PATH"] = os.pathsep.join([str(Path(env["SystemRoot"]) / "System32"), env["SystemRoot"]])
for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
    env.pop(name, None)
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
with tempfile.TemporaryDirectory(prefix="cc2-exe-smoke-") as cwd:
    # A user's saved launch-on-start preference must never turn a packaging
    # smoke check into a game launch or an activation against real user data.
    for variable, folder in (("APPDATA", "Roaming"), ("LOCALAPPDATA", "Local")):
        isolated = Path(cwd) / folder
        isolated.mkdir()
        env[variable] = str(isolated)
    tool_result = Path(cwd) / "tools.json"
    tool_smoke = subprocess.run(
        [str(exe), "--verify-bundle", str(tool_result)],
        cwd=cwd,
        env=env,
        startupinfo=startup,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=30,
        check=True,
    )
    frozen_tools = json.loads(tool_result.read_text())
    assert frozen_tools["merge"] == "clean" and frozen_tools["syntax_only"] is True
    assert frozen_tools["sdk_signature_verified"] is True
    process = subprocess.Popen(
        [str(exe)],
        cwd=cwd,
        env=env,
        startupinfo=startup,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    opened = False
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            fresh = [(hwnd, title) for hwnd, title in windows() if hwnd not in before]
            matches = [hwnd for hwnd, title in fresh if title == APP_NAME]
            if matches:
                opened = True
                time.sleep(1)
                for hwnd in matches:
                    user32.PostMessageW(hwnd, 0x0010, 0, 0)
                break
            if process.poll() is not None:
                raise RuntimeError(
                    f"GUI exited before showing its main window: {process.returncode}"
                )
            time.sleep(0.2)
        assert opened, "The main window did not open within 30 seconds"
        assert process.wait(timeout=15) == 0
    finally:
        if process.poll() is None:
            subprocess.run(
                ["C:/Windows/System32/taskkill.exe", "/pid", str(process.pid), "/t", "/f"],
                capture_output=True,
                check=False,
            )

locations = find_installations(steam_roots=None if "--inventory" in sys.argv else [])
inventory = discover(list(locations.workshop_roots))
game_hashes = [
    hashlib.sha256(
        read_regular(
            item.executable,
            input_root(item.executable.parent),
            Budget(Limits(max_file_bytes=128 * 1024 * 1024, max_total_bytes=128 * 1024 * 1024)),
        )
    ).hexdigest()
    for item in locations.games
]
report = {
    "kind": "local-windows-build-smoke",
    "version": __version__,
    "artifact": exe.name,
    "artifact_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
    "artifact_bytes": exe.stat().st_size,
    "engine_sha256": engine_hash(),
    "build_input_sha256": {
        str(path): hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in [
            Path("build_windows.bat"),
            Path("CC2ModLoader-0.1.0.spec"),
            Path("uv.lock"),
            Path("tools/check_windows_bundle.py"),
        ]
    },
    "source_sha256": hashes,
    "base_sha256": None,
    "mod_order": [],
    "read_only_discovery": {
        "detected_installations": len(locations.games),
        "game_executable_sha256": game_hashes,
        "game_build_verified": False,
        "workshop_collections": len(locations.workshop_roots),
        "workshop_scan_sha256": inventory.fingerprint,
        "source_mods": [{"id": mod.id, "sha256": mod.sha256} for mod in inventory.mods],
        "game_executed": False,
    },
    "python": sys.version.split()[0],
    "pyinstaller": importlib.metadata.version("pyinstaller"),
    "host": platform.platform(),
    "checks": {
        "isolated_user_preferences": True,
        "packaged_schema_and_sources_match": True,
        "gui_opened_from_unrelated_directory_without_dev_tools_on_path": opened,
        "gui_closed_cleanly": True,
        "frozen_tools": frozen_tools,
    },
    "clean_machine_tested": False,
    "game_runtime_tested": False,
    "macos_tested": False,
    "git_and_lua_bundled": True,
    "installable_mod_verified": False,
}
test_report = root / "build/test-results.xml"
if test_report.exists():
    suites = ET.parse(test_report).getroot().iter("testsuite")
    counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    for suite in suites:
        for key in counts:
            counts[key] += int(suite.get(key, "0"))
    report["regressions"] = {**counts, "passed": counts["tests"] - counts["failures"]
                             - counts["errors"] - counts["skipped"]}
destination = exe.with_suffix(".build.json")
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "report": str(destination),
            "sha256": report["artifact_sha256"],
            "gui_opened_and_closed": opened,
            "bytes": report["artifact_bytes"],
        }
    )
)
