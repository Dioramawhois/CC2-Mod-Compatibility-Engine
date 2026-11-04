import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from cc2_mce.discovery import FileRef, discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.game_launch import launch_game
from cc2_mce.workflow import _verified_package, analyze, apply_plan
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture

MIB = 1024 * 1024


def sparse_file(path: Path, size: int, header: bytes) -> None:
    """Create large owned fixtures without allocating their holes on Windows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        if os.name == "nt":
            import ctypes
            import msvcrt

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            returned = ctypes.c_ulong()
            if not kernel.DeviceIoControl(
                ctypes.c_void_p(msvcrt.get_osfhandle(stream.fileno())),
                0x900C4,  # FSCTL_SET_SPARSE
                None,
                0,
                None,
                0,
                ctypes.byref(returned),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            stream.write(header)
            stream.flush()
            handle = ctypes.c_void_p(msvcrt.get_osfhandle(stream.fileno()))
            if not kernel.SetFilePointerEx(handle, ctypes.c_longlong(size), None, 0):
                raise ctypes.WinError(ctypes.get_last_error())
            if not kernel.SetEndOfFile(handle):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            stream.write(header)
            stream.truncate(size)


def sparse_png(path: Path, size: int) -> None:
    """Owned binary-copy fixture; not a game asset or PNG decoder acceptance."""
    sparse_file(path, size, b"\x89PNG\r\n\x1a\n")


def test_large_binary_survives_activation_reuse_and_direct_launch_guard(tmp_path: Path) -> None:
    game, profile, user = fixture(tmp_path)
    mod = make_mod(tmp_path / "workshop", "large", {})
    resource = mod / "content/textures/large.png"
    sparse_png(resource, 16 * MIB + 123)
    sparse_png(game.root / "rom_0/textures/large.png", resource.stat().st_size)

    scan = discover([tmp_path / "workshop"])
    plan = analyze(game, scan, ["large"], profile=profile)
    assert not plan.blockers
    assert plan.payload["textures/large.png"] == resource.read_bytes()
    package = apply_plan(plan, user, game_running=lambda: False)
    assert _verified_package(package)["build_id"] == plan.report["build_id"]
    assert (package / "content/textures/large.png").read_bytes() == resource.read_bytes()
    assert apply_plan(plan, user, game_running=lambda: False) == package

    spawn = Mock()
    launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_called_once_with([str(game.executable)], cwd=str(game.root), shell=False)

    # A larger read allowance must not let changed payload bytes reach the game.
    with (package / "content/textures/large.png").open("r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"!")
    spawn.reset_mock()
    with pytest.raises(InputError):
        launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_not_called()


def test_selected_binary_payload_can_exceed_the_old_aggregate_limit(tmp_path: Path) -> None:
    game, profile, _ = fixture(tmp_path)
    mod = make_mod(tmp_path / "workshop", "large", {})
    for name in ("first", "second"):
        sparse_png(mod / f"content/textures/{name}.png", 128 * MIB + 1)

    plan = analyze(game, discover([tmp_path / "workshop"]), ["large"], profile=profile)
    assert not plan.blockers
    assert sum(map(len, plan.payload.values())) == 256 * MIB + 2
    assert all(
        item["output_sha256"] == digest(plan.payload[item["logical_path"]])
        for item in plan.report["files"]
    )


def test_selection_budget_refuses_before_reading_and_preserves_working_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, profile, user = fixture(tmp_path)
    working = analyze(game, discover([tmp_path / "workshop"]), ["a"], profile=profile)
    package = apply_plan(working, user, game_running=lambda: False)
    original_config = (user / "mods.xml").read_bytes()
    original_payload = (package / "content/a.txt").read_bytes()
    original_manifest = (package / "mce-manifest.json").read_bytes()
    mod = make_mod(tmp_path / "workshop", "large", {})
    sparse_png(mod / "content/textures/large.png", 200)
    scan = discover([tmp_path / "workshop"])

    monkeypatch.setattr(
        workflow,
        "RESOURCE_LIMITS",
        replace(workflow.RESOURCE_LIMITS, max_file_bytes=1024, max_total_bytes=128),
    )

    def unexpected_resource_read(_file: FileRef) -> bytes:
        raise AssertionError("Selection budget must be checked before loading resources")

    monkeypatch.setattr(FileRef, "content", property(unexpected_resource_read))
    with pytest.raises(InputError, match="byte limit"):
        analyze(game, scan, ["large"], profile=profile)

    assert (user / "mods.xml").read_bytes() == original_config
    assert (package / "content/a.txt").read_bytes() == original_payload
    assert (package / "mce-manifest.json").read_bytes() == original_manifest


@pytest.mark.parametrize("oversized", ["source", "baseline"])
def test_large_binary_allowance_does_not_expand_text_parser_budget(
    tmp_path: Path, oversized: str
) -> None:
    game, profile, _ = fixture(tmp_path)
    mod = make_mod(tmp_path / "workshop", "large", {"settings/constants.txt": b"value=2\n"})
    target = (
        mod / "content/settings/constants.txt"
        if oversized == "source"
        else game.root / "rom_0/settings/constants.txt"
    )
    sparse_file(target, 16 * MIB + 1, b"value=1\n")

    # Inventory can list the mod; selecting it must preserve the text/merge bound.
    scan = discover([tmp_path / "workshop"])
    with pytest.raises(InputError, match="byte limit"):
        analyze(game, scan, ["large"], profile=profile)
