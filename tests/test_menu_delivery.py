"""The front menu disables resource overlays: deliver policy through the SDK."""

import json
import shutil
from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.managed_menu import ADAPTER, MENU_PATH, SCREEN_DESCRIPTOR, SCREEN_SOURCE, screen_source
from cc2_mce.toolchain import Toolchain
from cc2_mce.workflow import analyze, apply_plan, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


def screen_fixture(tmp_path: Path):
    game, profile, user = fixture(tmp_path)
    runtime = b"owned runtime fixture, never executed"
    (game.root / "dinput8.dll").write_bytes(runtime)
    profile.update(runtime_sha256=digest(runtime), runtime_capabilities=["screen-extensions-v1"])
    luac = Path(
        shutil.which("luac5.3")
        or shutil.which("luac53")
        or shutil.which("luac")
        or str(Path(__file__).parents[1] / "cc2_mce/tools_data/lua/luac.exe")
    )
    if not luac.is_file():
        pytest.skip("Lua 5.3 validator unavailable")
    tools = Toolchain(Path(shutil.which("git") or "git"), luac, digest(b"owned tools fixture"))
    return game, profile, user, tools


def test_screen_delivery_does_not_depend_on_resource_overlay_or_stock_menu(tmp_path: Path):
    game, profile, user, tools = screen_fixture(tmp_path)
    plan = analyze(
        game, discover([tmp_path / "workshop"]), ["b", "a"], profile=profile, tools=tools
    )
    assert not plan.blockers
    assert MENU_PATH not in plan.payload
    descriptor = json.loads(plan.payload[SCREEN_DESCRIPTOR])
    assert descriptor == {
        "schema": 1,
        "extensions": [{"screen": MENU_PATH, "source": SCREEN_SOURCE}],
    }
    assert plan.payload[SCREEN_SOURCE] == screen_source(tuple(mod.name for mod in plan.selected))
    metadata = plan.report["managed_menu"]
    assert metadata["policy"] == "sdk-screen-extension-v4"
    assert metadata["adapter_sha256"] == digest(ADAPTER)
    assert metadata["output_sha256"] == digest(plan.payload[SCREEN_SOURCE])
    assert metadata["descriptor_sha256"] == digest(plan.payload[SCREEN_DESCRIPTOR])
    assert plan.report["runtime_sha256"] == profile["runtime_sha256"]
    package = apply_plan(plan, user, game_running=lambda: False)
    assert (package / "content" / SCREEN_SOURCE).read_bytes() == plan.payload[SCREEN_SOURCE]
    restore_previous(user, game_running=lambda: False)
    assert not package.exists()


def test_no_runtime_capability_does_not_claim_to_lock_the_front_menu(tmp_path: Path):
    game, profile, _ = fixture(tmp_path)
    menu = game.root / "rom_0" / MENU_PATH
    menu.parent.mkdir(parents=True)
    menu.write_bytes(b"function begin() end\nfunction update() end\n")
    plan = analyze(game, discover([tmp_path / "workshop"]), ["a"], profile=profile)
    assert not plan.blockers
    assert "managed_menu" not in plan.report
    assert MENU_PATH not in plan.payload
    assert SCREEN_DESCRIPTOR not in plan.payload


@pytest.mark.parametrize("eol", [b"\n", b"\r\n"])
def test_installed_stock_menu_stays_untouched(tmp_path: Path, eol: bytes):
    game, profile, user, tools = screen_fixture(tmp_path)
    original = game.root / "rom_0" / MENU_PATH
    original.parent.mkdir(parents=True)
    source = b"function begin() end\nfunction update() end\n".replace(b"\n", eol)
    original.write_bytes(source)
    plan = analyze(game, discover([tmp_path / "workshop"]), ["a"], profile=profile, tools=tools)
    assert not plan.blockers
    assert MENU_PATH not in plan.payload
    apply_plan(plan, user, game_running=lambda: False)
    assert original.read_bytes() == source
    restore_previous(user, game_running=lambda: False)
    assert original.read_bytes() == source


def test_empty_selection_has_no_screen_extension_or_forced_runtime(tmp_path: Path):
    game, profile, _, _ = screen_fixture(tmp_path)
    plan = analyze(game, discover([tmp_path / "workshop"]), [], profile=profile)
    assert not plan.blockers
    assert SCREEN_DESCRIPTOR not in plan.payload
    assert SCREEN_SOURCE not in plan.payload
    assert plan.report["runtime_sha256"] is None
    assert "managed_menu" not in plan.report


def test_user_cannot_supply_or_replace_owned_policy_paths(tmp_path: Path):
    game, profile, _, tools = screen_fixture(tmp_path)
    make_mod(tmp_path / "workshop", "injected", {SCREEN_SOURCE: b"print('untrusted')\n"})
    plan = analyze(
        game, discover([tmp_path / "workshop"]), ["injected"], profile=profile, tools=tools
    )
    assert any(item["code"] == "managed_menu_collision" for item in plan.blockers)
    assert "managed_menu" not in plan.report


def test_extension_inventory_cannot_be_changed_before_reapply(tmp_path: Path):
    game, profile, user, tools = screen_fixture(tmp_path)
    plan = analyze(game, discover([tmp_path / "workshop"]), ["a"], profile=profile, tools=tools)
    package = apply_plan(plan, user, game_running=lambda: False)
    (package / "content" / SCREEN_DESCRIPTOR).write_bytes(b'{"schema":1,"extensions":[]}\n')
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)
