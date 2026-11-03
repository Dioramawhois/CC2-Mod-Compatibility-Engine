import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.filesystem import digest
from cc2_mce.managed_menu import ADAPTER, MENU_PATH, decorate
from cc2_mce.toolchain import Toolchain
from cc2_mce.workflow import analyze, apply_plan, restore_previous
from tests.test_workflow import fixture


def test_real_lua_owned_menu_contract(tmp_path: Path):
    adapter = tmp_path / "managed_menu.lua"
    adapter.write_bytes(ADAPTER)
    contract = Path(__file__).parent / "fixtures/managed_menu_contract.lua"
    runner = os.environ.get("CC2_MCE_LUA_POLICY_RUNNER")
    if runner:
        command = [runner, str(adapter), str(contract)]
    elif interpreter := shutil.which("lua5.3") or shutil.which("lua53") or shutil.which("lua"):
        source = (
            "POLICY=assert(loadfile("
            + json.dumps(adapter.as_posix(), ensure_ascii=False)
            + "))();dofile("
            + json.dumps(contract.as_posix(), ensure_ascii=False)
            + ")"
        )
        command = [interpreter, "-e", source]
    else:
        pytest.skip("Lua interpreter unavailable; syntax and package checks run separately")
    result = subprocess.run(command, capture_output=True, timeout=10, check=False)
    assert result.returncode == 0, (result.stdout + result.stderr).decode(errors="replace")
    assert b"PASS managed menu" in result.stdout


@pytest.mark.parametrize("eol", [b"\n", b"\r\n"])
def test_owned_menu_adapter_is_hashed_validated_and_reversible(tmp_path: Path, eol: bytes):
    game, profile, user = fixture(tmp_path)
    source = b"function begin() end\nfunction update() end\n".replace(b"\n", eol)
    original = game.root / "rom_0" / MENU_PATH
    original.parent.mkdir(parents=True)
    original.write_bytes(source)
    luac = (
        shutil.which("luac5.3")
        or shutil.which("luac53")
        or shutil.which("luac")
        or str(Path(__file__).parents[1] / "cc2_mce/tools_data/lua/luac.exe")
    )
    if not Path(luac).is_file():
        pytest.skip("Lua 5.3 validator unavailable; CI builds the pinned interpreter and validator")
    tools = Toolchain(Path(shutil.which("git") or "git"), Path(luac), digest(b"fixture"))
    scan = discover([tmp_path / "workshop"])
    plan = analyze(game, scan, ["a"], profile=profile, tools=tools)
    assert not plan.blockers
    assert plan.payload[MENU_PATH] == decorate(source)
    assert plan.report["managed_menu"]["adapter_sha256"] == digest(ADAPTER)
    assert plan.report["managed_menu"]["input_sha256"] == digest(source)
    package = apply_plan(plan, user, game_running=lambda: False)
    assert (package / "content" / MENU_PATH).read_bytes() == decorate(source)
    assert original.read_bytes() == source
    restore_previous(user, game_running=lambda: False)
    assert original.read_bytes() == source


def test_unresolved_menu_conflict_is_not_replaced_by_stock_menu(tmp_path: Path):
    game, profile, _ = fixture(tmp_path)
    for name, value in (
        ("a", b"function update() return 1 end\n"),
        ("b", b"function update() return 2 end\n"),
    ):
        path = tmp_path / "workshop" / name / "content" / MENU_PATH
        path.parent.mkdir(parents=True)
        path.write_bytes(value)
    plan = analyze(game, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    assert plan.blockers
    assert MENU_PATH not in plan.payload
