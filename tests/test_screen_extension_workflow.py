"""Screen sidecars survive the real package transaction without executing Lua."""

import json
from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.managed_menu import MENU_PATH, SCREEN_DESCRIPTOR, SCREEN_SOURCE
from cc2_mce.workflow import active_paths, analyze, apply_plan, restore_previous
from tests.test_menu_delivery import screen_fixture
from tests.test_paths_discovery import make_mod

COMMON = "cc2x/ui/shared.lua"
TRAFFIC = "cc2x/ui/traffic.lua"
COMMON_LUA = b"error('A packaging utility must never execute this helper')\n"
TRAFFIC_LUA = b"error('This second helper is also syntax-checked only')\n"
TARGETS = (
    "scripts/screen_holomap.lua",
    "scripts/screen_vehicle_control.lua",
    "scripts/screen_propulsion.lua",
)
STOCK = b"function update() return 1 end\n"


def addon(root: Path, name: str = "addon", *, entries=None, schema=2, extra=None):
    if entries is None:
        profiles = [
            {
                "sha256": digest(STOCK),
                "edits": [{"offset": 0, "remove": 0, "insert": "-- declared patch \u03b1\n"}],
            },
            {
                "sha256": digest(b"function update() return 2 end\n"),
                "edits": [{"offset": 0, "remove": 0, "insert": "-- other reviewed source\n"}],
            },
        ]
        entries = [
            {"screen": target, "source": COMMON if index < 2 else TRAFFIC, "profiles": profiles}
            for index, target in enumerate(TARGETS)
        ]
    value = {"schema": schema, "extensions": entries}
    raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
    files = {SCREEN_DESCRIPTOR: raw, COMMON: COMMON_LUA}
    if any(entry["source"] == TRAFFIC for entry in entries):
        files[TRAFFIC] = TRAFFIC_LUA
    files.update(extra or {})
    package = make_mod(root, name, files)
    return package, value, raw


def test_profiled_addon_and_menu_activate_with_complete_source_provenance(tmp_path: Path):
    game, profile, user, tools = screen_fixture(tmp_path)
    profile["runtime_capabilities"].append("screen-source-edits-v1")
    original, declared, raw = addon(tmp_path / "workshop")
    for target in TARGETS:
        stock = game.root / "rom_0" / target
        stock.parent.mkdir(parents=True, exist_ok=True)
        stock.write_bytes(STOCK)

    plan = analyze(
        game, discover([tmp_path / "workshop"]), ["a", "addon"], profile=profile, tools=tools
    )
    assert not plan.blockers
    assert plan.report["installable"]
    merged = json.loads(plan.payload[SCREEN_DESCRIPTOR])
    assert merged["schema"] == 2
    assert [entry["screen"] for entry in merged["extensions"]] == [*TARGETS, MENU_PATH]
    assert merged["extensions"][-1] == {"screen": MENU_PATH, "source": SCREEN_SOURCE}
    references = {}
    for source_entry, entry in zip(declared["extensions"], merged["extensions"], strict=False):
        assert entry["profiles"] == source_entry["profiles"]
        assert entry["source"] != source_entry["source"]
        assert entry["source"].startswith("cc2x/ui/")
        references[source_entry["source"]] = entry["source"]
    assert merged["extensions"][0]["source"] == merged["extensions"][1]["source"]
    assert len(references) == 2
    assert COMMON not in plan.payload and TRAFFIC not in plan.payload
    inventory = {entry["logical_path"]: entry for entry in plan.report["files"]}
    assert inventory[SCREEN_DESCRIPTOR]["source_sha256"] == {"addon": digest(raw)}
    assert inventory[SCREEN_DESCRIPTOR]["output_sha256"] == digest(plan.payload[SCREEN_DESCRIPTOR])
    for old, data in ((COMMON, COMMON_LUA), (TRAFFIC, TRAFFIC_LUA)):
        renamed = references[old]
        assert plan.payload[renamed] == data
        assert inventory[renamed]["source_sha256"] == {"addon": digest(data)}
        assert inventory[renamed]["output_sha256"] == digest(data)
    assert plan.report["managed_menu"]["descriptor_sha256"] == digest(
        plan.payload[SCREEN_DESCRIPTOR]
    )

    package = apply_plan(plan, user, game_running=lambda: False)
    assert active_paths(user) == (package,)
    assert json.loads((package / "content" / SCREEN_DESCRIPTOR).read_bytes()) == merged
    for old, data in ((COMMON, COMMON_LUA), (TRAFFIC, TRAFFIC_LUA)):
        assert (package / "content" / references[old]).read_bytes() == data
        assert (original / "content" / old).read_bytes() == data
    assert (original / "content" / SCREEN_DESCRIPTOR).read_bytes() == raw
    assert all((game.root / "rom_0" / target).read_bytes() == STOCK for target in TARGETS)


def test_disabling_addon_removes_helpers_and_profiles_and_undo_restores(tmp_path: Path):
    game, profile, user, tools = screen_fixture(tmp_path)
    profile["runtime_capabilities"].append("screen-source-edits-v1")
    original, _, raw = addon(tmp_path / "workshop")
    scan = discover([tmp_path / "workshop"])
    combined = analyze(game, scan, ["a", "addon"], profile=profile, tools=tools)
    assert not combined.blockers
    package = apply_plan(combined, user, game_running=lambda: False)
    before_manifest = (package / "mce-manifest.json").read_bytes()
    addon_helpers = {
        entry["source"]
        for entry in json.loads(combined.payload[SCREEN_DESCRIPTOR])["extensions"]
        if entry["screen"] != MENU_PATH
    }

    without = analyze(game, scan, ["a"], profile=profile, tools=tools)
    assert not without.blockers
    assert all(helper not in without.payload for helper in addon_helpers)
    assert json.loads(without.payload[SCREEN_DESCRIPTOR]) == {
        "schema": 1,
        "extensions": [{"screen": MENU_PATH, "source": SCREEN_SOURCE}],
    }
    apply_plan(without, user, game_running=lambda: False)
    assert all(not (package / "content" / helper).exists() for helper in addon_helpers)
    assert json.loads((package / "mce-manifest.json").read_bytes())["mod_order"] == ["a"]

    restore_previous(user, game_running=lambda: False)
    assert active_paths(user) == (package,)
    assert (package / "mce-manifest.json").read_bytes() == before_manifest
    assert (package / "content" / SCREEN_DESCRIPTOR).read_bytes() == combined.payload[
        SCREEN_DESCRIPTOR
    ]
    assert all(
        (package / "content" / helper).read_bytes() == combined.payload[helper]
        for helper in addon_helpers
    )
    assert (original / "content" / SCREEN_DESCRIPTOR).read_bytes() == raw


@pytest.mark.parametrize("addon_entries", [15, 16])
def test_owned_menu_counts_toward_sdk_sixteen_entry_limit(tmp_path: Path, addon_entries: int):
    game, profile, user, tools = screen_fixture(tmp_path)
    entries = [
        {"screen": f"scripts/screen_fixture_{index}.lua", "source": COMMON}
        for index in range(addon_entries)
    ]
    addon(tmp_path / "workshop", entries=entries, schema=1)
    activation_before = (user / "mods.xml").read_bytes()
    runtime_before = (game.root / "dinput8.dll").read_bytes()
    plan = analyze(game, discover([tmp_path / "workshop"]), ["addon"], profile=profile, tools=tools)
    if addon_entries == 15:
        assert not plan.blockers
        assert len(json.loads(plan.payload[SCREEN_DESCRIPTOR])["extensions"]) == 16
        assert apply_plan(plan, user, game_running=lambda: False).is_dir()
    else:
        assert any(item["code"] == "screen_extension_limits" for item in plan.blockers)
        assert not plan.report["installable"]
        with pytest.raises(InputError):
            apply_plan(plan, user, game_running=lambda: False)
        assert (user / "mods.xml").read_bytes() == activation_before
        assert not (user / "mods").exists()
        assert (game.root / "dinput8.dll").read_bytes() == runtime_before


def test_addon_main_menu_target_cannot_replace_the_managed_menu(tmp_path: Path):
    game, profile, user, tools = screen_fixture(tmp_path)
    addon(
        tmp_path / "workshop",
        entries=[{"screen": MENU_PATH, "source": COMMON}],
        schema=1,
    )
    activation_before = (user / "mods.xml").read_bytes()
    plan = analyze(game, discover([tmp_path / "workshop"]), ["addon"], profile=profile, tools=tools)
    assert any(item["code"] == "managed_menu_collision" for item in plan.blockers)
    assert "managed_menu" not in plan.report
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)
    assert (user / "mods.xml").read_bytes() == activation_before
    assert not (user / "mods").exists()


def test_declared_helpers_do_not_whitelist_an_unreferenced_native_dll(tmp_path: Path):
    game, profile, user, tools = screen_fixture(tmp_path)
    addon(
        tmp_path / "workshop",
        entries=[{"screen": TARGETS[0], "source": COMMON}],
        schema=1,
        extra={"cc2x/unreviewed.dll": b"MZ-owned-unreviewed-fixture-never-loaded"},
    )
    before = (user / "mods.xml").read_bytes()
    plan = analyze(game, discover([tmp_path / "workshop"]), ["addon"], profile=profile, tools=tools)
    assert any(
        item["code"] == "native_plugin_review_required" and item["file"] == "cc2x/unreviewed.dll"
        for item in plan.blockers
    )
    assert "cc2x/unreviewed.dll" not in plan.payload
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)
    assert (user / "mods.xml").read_bytes() == before
    assert not (user / "mods").exists()


def test_merge_order_keeps_different_owners_helpers_with_the_same_original_path(tmp_path: Path):
    game, profile, user, tools = screen_fixture(tmp_path)
    first, _, _ = addon(
        tmp_path / "workshop",
        "first",
        entries=[{"screen": TARGETS[0], "source": COMMON}],
        schema=1,
    )
    second, _, _ = addon(
        tmp_path / "workshop",
        "second",
        entries=[{"screen": TARGETS[1], "source": COMMON}],
        schema=1,
    )
    second_data = b"error('Second owner must not be merged into the first owner helper')\n"
    (second / "content" / COMMON).write_bytes(second_data)
    plan = analyze(
        game,
        discover([tmp_path / "workshop"]),
        ["second", "first"],
        profile=profile,
        tools=tools,
    )
    assert not plan.blockers
    entries = json.loads(plan.payload[SCREEN_DESCRIPTOR])["extensions"]
    assert [entry["screen"] for entry in entries] == [TARGETS[1], TARGETS[0], MENU_PATH]
    assert entries[0]["source"] != entries[1]["source"]
    assert plan.payload[entries[0]["source"]] == second_data
    assert plan.payload[entries[1]["source"]] == COMMON_LUA
    package = apply_plan(plan, user, game_running=lambda: False)
    assert (package / "content" / entries[0]["source"]).read_bytes() == second_data
    assert (package / "content" / entries[1]["source"]).read_bytes() == COMMON_LUA
    assert (first / "content" / COMMON).read_bytes() == COMMON_LUA
