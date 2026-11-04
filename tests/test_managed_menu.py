import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cc2_mce.discovery import discover
from cc2_mce.filesystem import digest
from cc2_mce.managed_menu import ADAPTER, MENU_PATH, decorate, screen_source
from cc2_mce.workflow import analyze
from tests.test_workflow import fixture


@pytest.mark.parametrize("delivered_source", [False, True])
def test_real_lua_owned_menu_contract(tmp_path: Path, delivered_source: bool):
    adapter = tmp_path / "managed_menu.lua"
    # Run the exact generated extension too, including its installation wrapper.
    # The fixture provides an owned screen environment, never game/mod source.
    adapter.write_bytes(
        b"return function(env)\nlocal _G = env\n"
        + screen_source(("AI Bridge", "Island Airfields"))
        + b"\nend\n"
        if delivered_source
        else ADAPTER
    )
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


def test_empty_selection_does_not_lock_the_game_menu(tmp_path: Path):
    game, profile, _ = fixture(tmp_path)
    source = b"function begin() end\nfunction update() end\n"
    original = game.root / "rom_0" / MENU_PATH
    original.parent.mkdir(parents=True)
    original.write_bytes(source)
    plan = analyze(game, discover([tmp_path / "workshop"]), [], profile=profile)
    assert not plan.blockers
    assert MENU_PATH not in plan.payload
    assert "managed_menu" not in plan.report
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


@pytest.mark.parametrize(
    "policy", ["read-only-mod-list-v1", "locked-mods-menu-v2", "modloader-main-menu-v3"]
)
def test_menu_schema_accepts_existing_and_current_policy(policy: str):
    schema = json.loads(
        (Path(__file__).parents[1] / "cc2_mce/schemas/package.schema.json").read_text("utf-8")
    )
    validator = Draft202012Validator(
        {"$defs": schema["$defs"], **schema["properties"]["managed_menu"]}
    )
    metadata = {
        "policy": policy,
        "logical_path": MENU_PATH,
        "input_sha256": digest(b"input"),
        "adapter_sha256": digest(ADAPTER),
        "output_sha256": digest(b"output"),
    }
    validator.validate(metadata)
    metadata["policy"] = "unknown-policy"
    assert list(validator.iter_errors(metadata))


def test_menu_selection_label_keeps_order_unicode_and_normalizes_controls():
    from cc2_mce.managed_menu import selection_label

    assert selection_label(("  AI\nBridge\x00\t", "\u5c9b\u5c7f \u041c\u043e\u0434")) == (
        "AI Bridge + \u5c9b\u5c7f \u041c\u043e\u0434"
    )
    assert selection_label(()) == ""
    label = selection_label(("\u03a9" * 160, "Last"))
    assert len(label) == 140 and label.endswith("...")
    assert label[:-3] == "\u03a9" * 137


@pytest.mark.parametrize("eol", [b"\n", b"\r\n"])
def test_menu_name_is_lua_data_and_cannot_inject_code(eol: bytes):
    from cc2_mce.managed_menu import selection_label

    names = ('"]]; _G.fixture_should_not_run=true; --\\123\n\x00', "\u5c9b\u5c7f")
    source = b"function begin() end\nfunction update() end\n".replace(b"\n", eol)
    decorated = decorate(source, names)
    assert decorated.startswith(source)
    suffix = decorated[len(source) :]
    match = re.search(rb'install\(_G, "((?:\\[0-9]{3})*)"\)', suffix)
    assert match is not None
    encoded = match[1]
    decoded = bytes(int(encoded[index + 1 : index + 4]) for index in range(0, len(encoded), 4))
    assert decoded.decode("utf-8") == selection_label(names)
    assert b"_G.fixture_should_not_run" not in suffix
    if eol == b"\r\n":
        assert b"\n" not in suffix.replace(b"\r\n", b"")
