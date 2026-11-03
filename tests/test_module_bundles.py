import json
from pathlib import Path

import pytest

from cc2_mce.discovery import discover, snapshot_unchanged
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.workflow import analyze, apply_plan, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


@pytest.fixture
def setup(tmp_path: Path, monkeypatch):
    installation, profile, user = fixture(tmp_path)
    runtime = b"synthetic reviewed runtime"
    (installation.root / "dinput8.dll").write_bytes(runtime)
    profile.update(
        runtime_sha256=digest(runtime),
        runtime_api=8,
        runtime_capabilities=["ordered-module-bundles-v1"],
    )
    # These tests exercise packaging/path/order boundaries, not a Lua interpreter.
    monkeypatch.setattr("cc2_mce.module_bundles.validate_content", lambda *a, **kw: ("valid", ""))
    root = tmp_path / "modules"
    for name in ("zeta", "alpha"):
        make_mod(
            root,
            name,
            {
                "bridge.json": json.dumps({"id": name, "scripts": ["bridge/main.lua"]}).encode(),
                "bridge/main.lua": f"return {{owner='{name}'}}\n".encode(),
                "bridge/helper.lua": f"return '{name}'\n".encode(),
            },
        )
    return installation, profile, user, root


def index(plan):
    return json.loads(plan.payload["cc2x-modules/index.json"])


def test_rules_entry_is_validated_and_kept_private(setup):
    game, profile, _, root = setup
    package = root / "zeta"
    (package / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="mod" id="zeta" sdk="cc2x" api="8" lua_api="2"/></data>',
        encoding="utf-8",
    )
    profile.update(runtime_lua_api=2)
    profile["runtime_capabilities"].append("lua-mod-api-v2")
    manifest = package / "content/bridge.json"
    (package / "content/bridge/rules.lua").write_bytes(b"return {}\n")
    value = {"id": "zeta", "scripts": ["bridge/main.lua"], "rules": "bridge/rules.lua"}
    manifest.write_text(json.dumps(value), encoding="utf-8")
    plan = analyze(game, discover([root]), ["zeta"], profile=profile)
    assert not plan.blockers
    key = index(plan)["packages"][0]
    assert plan.payload[f"cc2x-modules/{key}/content/bridge/rules.lua"] == b"return {}\n"
    for invalid in (
        "../outside.lua",
        "bridge/missing.lua",
        "scripts/screen.lua",
        ["bridge/rules.lua"],
    ):
        value["rules"] = invalid
        manifest.write_text(json.dumps(value), encoding="utf-8")
        plan = analyze(game, discover([root]), ["zeta"], profile=profile)
        assert plan.blockers, invalid


def test_identical_entry_names_keep_separate_code_and_owner_order(setup):
    game, profile, _, root = setup
    plan = analyze(game, discover([root]), ["zeta", "alpha"], profile=profile)
    assert not plan.blockers
    assert [m["owner_id"] for m in plan.report["modules"]] == ["zeta", "alpha"]
    keys = index(plan)["packages"]
    assert len(set(keys)) == 2
    for key, owner in zip(keys, ("zeta", "alpha"), strict=True):
        prefix = f"cc2x-modules/{key}/"
        assert (
            plan.payload[prefix + "content/bridge/main.lua"]
            == f"return {{owner='{owner}'}}\n".encode()
        )
        assert json.loads(plan.payload[prefix + "content/bridge.json"])["id"] == owner
        assert plan.payload[prefix + "mod.xml"] == (root / owner / "mod.xml").read_bytes()
    assert "bridge/main.lua" not in plan.payload and "bridge.json" not in plan.payload
    assert analyze(game, discover([root]), ["zeta", "alpha"], profile=profile).report == plan.report


def test_reorder_disable_apply_and_rollback_use_one_fixed_folder(setup):
    game, profile, user, root = setup
    first = analyze(game, discover([root]), ["zeta", "alpha"], profile=profile)
    output = apply_plan(first, user, game_running=lambda: False)
    second = analyze(game, discover([root]), ["alpha", "zeta"], profile=profile)
    assert index(second)["packages"] == list(reversed(index(first)["packages"]))
    assert apply_plan(second, user, game_running=lambda: False) == output
    third = analyze(game, discover([root]), ["alpha"], profile=profile)
    apply_plan(third, user, game_running=lambda: False)
    assert not (output / "content/cc2x-modules" / index(first)["packages"][0]).exists()
    restore_previous(user, game_running=lambda: False)
    assert json.loads((output / "content/cc2x-modules/index.json").read_bytes()) == index(second)


def test_runtime_capability_is_required_even_for_valid_module(setup):
    game, profile, user, root = setup
    profile.pop("runtime_capabilities")
    plan = analyze(game, discover([root]), ["zeta"], profile=profile)
    assert any(b["code"] == "sdk_api" for b in plan.blockers)
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)
    assert not (user / "mods").exists()


@pytest.mark.parametrize(
    "manifest",
    [
        b'{"id":"one","id":"two","scripts":["bridge/main.lua"]}',
        b'{"id":"../bad","scripts":["bridge/main.lua"]}',
        b'{"id":"zeta","scripts":["../outside.lua"]}',
        b'{"id":"zeta","scripts":["scripts/stock.lua"]}',
        b'{"id":"zeta","scripts":["bridge/missing.lua"]}',
        b'{"id":"zeta","scripts":["bridge/main.lua","BRIDGE/MAIN.LUA"]}',
        b'{"id":"zeta","scripts":["bridge/main.lua"],"ui":{"vehicles":{"jet":{"large":"../x.png"}}}}',
        b"{" + b" " * 65537 + b"}",
    ],
    ids=[
        "duplicate-key",
        "bad-id",
        "escape",
        "stock",
        "missing",
        "duplicate-script",
        "bad-ui",
        "oversize",
    ],
)
def test_invalid_metadata_refuses_whole_publication(setup, manifest):
    game, profile, user, root = setup
    (root / "zeta/content/bridge.json").write_bytes(manifest)
    plan = analyze(game, discover([root]), ["alpha", "zeta"], profile=profile, patch_priority=True)
    assert plan.blockers
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)
    assert not (user / "mods").exists()


def test_duplicate_owners_never_resolve_by_patch_priority(setup):
    game, profile, _, root = setup
    (root / "alpha/content/bridge.json").write_bytes(b'{"id":"ZETA","scripts":["bridge/main.lua"]}')
    plan = analyze(game, discover([root]), ["zeta", "alpha"], profile=profile, patch_priority=True)
    assert plan.blockers and not plan.report["installable"]


def test_private_lua_validation_cannot_be_bypassed_by_later_patch(setup, monkeypatch):
    game, profile, _, root = setup
    monkeypatch.setattr(
        "cc2_mce.module_bundles.validate_content",
        lambda *a, **kw: ("validation_error", "Lua 5.3 syntax validation failed"),
    )
    plan = analyze(game, discover([root]), ["zeta", "alpha"], profile=profile, patch_priority=True)
    assert any(b["code"] == "validation_error" for b in plan.blockers)


def test_unknown_native_stays_blocked_and_out_of_private_container(setup):
    game, profile, _, root = setup
    (root / "zeta/content/cc2x").mkdir()
    (root / "zeta/content/cc2x/unknown.dll").write_bytes(b"MZ unreviewed")
    plan = analyze(game, discover([root]), ["zeta"], profile=profile)
    assert any(b["code"] == "native_plugin_review_required" for b in plan.blockers)
    assert not any(key.endswith(".dll") and "cc2x-modules/" in key for key in plan.payload)


def test_untrusted_source_cannot_supply_generated_module_index(setup):
    game, profile, _, root = setup
    make_mod(root, "spoof", {"cc2x-modules/index.json": b'{"schema":1,"packages":[]}'})
    plan = analyze(game, discover([root]), ["spoof", "zeta"], profile=profile)
    assert plan.blockers


def test_source_update_and_unselected_modules_have_no_hidden_activation(setup):
    game, profile, _, root = setup
    scan = discover([root])
    one = analyze(game, scan, ["zeta"], profile=profile)
    assert [m["owner_id"] for m in one.report["modules"]] == ["zeta"]
    (root / "zeta/content/bridge/helper.lua").write_bytes(b"return 'updated'\n")
    assert not snapshot_unchanged(scan)
    two = analyze(game, discover([root]), ["zeta"], profile=profile)
    assert one.report["build_id"] != two.report["build_id"]
    assert index(one) == index(two)


def test_shared_game_data_still_uses_real_git_merge(setup):
    game, profile, _, root = setup
    (root / "zeta/content/a.txt").write_bytes(b"a=2\n\n\nb=1\n")
    (root / "alpha/content/a.txt").write_bytes(b"a=1\n\n\nb=2\n")
    plan = analyze(game, discover([root]), ["zeta", "alpha"], profile=profile)
    assert not plan.blockers
    assert plan.payload["a.txt"] == b"a=2\n\n\nb=2\n"
    assert (
        next(f for f in plan.report["files"] if f["logical_path"] == "a.txt")["status"] == "clean"
    )


@pytest.mark.parametrize("layout", ["root", "nested", "legacy-content"])
def test_legacy_layouts_preserve_relative_helpers_and_source_updates(setup, layout):
    game, profile, _, root = setup
    source = root / "zeta"
    legacy = {
        "schema": 1,
        "id": "original.owner",
        "name": "Original",
        "version": "1",
        "runtime": "bridge",
        "entry": "main.lua",
        "hooks": [],
    }
    (source / "content/bridge.json").unlink()
    for name in ("main.lua", "helper.lua"):
        (source / "content/bridge" / name).unlink()
    (source / "content/bridge").rmdir()
    if layout == "root":
        (source / "content").rmdir()
        code_root = source
        manifest = source / "bridge.json"
        relative = ""
    elif layout == "nested":
        code_root = source / "content/native_bridge"
        manifest = code_root / "bridge.json"
        relative = "content/native_bridge/"
    else:
        code_root = source / "content/bridge"
        legacy["entry"] = "content/bridge/main.lua"
        manifest = source / "content/bridge.json"
        relative = "content/bridge/"
    code_root.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(legacy))
    (code_root / "main.lua").write_bytes(b"return {}\n")
    (code_root / "helper.lua").write_bytes(b"return 'helper'\n")
    scan = discover([root])
    from cc2_mce.reports import envelope, validate_report

    inventory = envelope("scan")
    inventory["sources"] = [mod.report() for mod in scan.mods]
    validate_report(inventory)
    plan = analyze(game, scan, ["zeta"], profile=profile)
    assert not plan.blockers
    assert plan.report["modules"][0]["owner_id"] == "original.owner"
    key = index(plan)["packages"][0]
    assert plan.payload[f"cc2x-modules/{key}/{relative}helper.lua"] == b"return 'helper'\n"
    (code_root / "helper.lua").write_bytes(b"return 'changed'\n")
    assert not snapshot_unchanged(scan)


def test_dependency_order_precedes_user_order_for_module_execution(setup):
    game, profile, _, root = setup
    (root / "alpha/mod.xml").write_bytes(
        b'<data name="Alpha"><cc2mce schema="1" type="mod" id="alpha">'
        b'<requires id="zeta"/></cc2mce></data>'
    )
    plan = analyze(game, discover([root]), ["alpha"], profile=profile)
    assert not plan.blockers
    assert [m["source_id"] for m in plan.report["modules"]] == ["zeta", "alpha"]


def test_every_script_rejects_game_owned_entries_not_only_first(setup):
    game, profile, _, root = setup
    (root / "zeta/content/scripts").mkdir()
    (root / "zeta/content/scripts/stock.lua").write_bytes(b"return {}\n")
    (root / "zeta/content/bridge.json").write_bytes(
        b'{"id":"zeta","scripts":["bridge/main.lua","scripts/stock.lua"]}'
    )
    plan = analyze(game, discover([root]), ["zeta"], profile=profile)
    assert plan.blockers


@pytest.mark.parametrize("invalid", ["deep", "nonfinite", "surrogate", "hook-type"])
def test_metadata_matches_runtime_json_and_hook_limits(setup, invalid):
    game, profile, _, root = setup
    value = {"id": "zeta", "scripts": ["bridge/main.lua"]}
    if invalid == "deep":
        nested: object = "leaf"
        for _ in range(34):
            nested = [nested]
        value["future"] = nested
    elif invalid == "nonfinite":
        value["future"] = float("nan")
    elif invalid == "surrogate":
        value["future"] = "\ud800"
    else:
        value["hooks"] = [{"target": "bridge.update", "handler": "update", "mode": []}]
    (root / "zeta/content/bridge.json").write_bytes(json.dumps(value).encode())
    plan = analyze(game, discover([root]), ["zeta"], profile=profile)
    assert plan.blockers


def test_private_container_overhead_cannot_exceed_package_depth(setup):
    game, profile, _, root = setup
    extra = root / "zeta/content" / "/".join(["deep"] * 30) / "extra.txt"
    extra.parent.mkdir(parents=True)
    extra.write_bytes(b"bounded output")
    plan = analyze(game, discover([root]), ["zeta"], profile=profile)
    assert any(b["code"] == "input_error" for b in plan.blockers)
