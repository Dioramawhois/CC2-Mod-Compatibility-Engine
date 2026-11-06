import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import cc2_mce.screen_extensions as screens
import cc2_mce.workflow as workflow
from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.managed_menu import MENU_PATH, SCREEN_DESCRIPTOR, SCREEN_SOURCE, screen_source
from cc2_mce.ui_feedback import explain_rejection
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture

SOURCE = "cc2x/ui/helper.lua"
LUA = b"error('owned syntax fixture must never execute')\n"


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    game, profile, user = fixture(tmp_path)
    runtime = b"owned reviewed runtime fixture; never executed"
    (game.root / "dinput8.dll").write_bytes(runtime)
    profile.update(
        runtime_sha256=digest(runtime),
        runtime_capabilities=["screen-extensions-v1", "screen-source-edits-v1"],
    )
    # Contract tests isolate syntax-only validation, never executing helper Lua.
    monkeypatch.setattr(workflow, "validate_content", lambda *a, **kw: ("valid", ""))
    monkeypatch.setattr(screens, "validate_content", lambda *a, **kw: ("valid", ""))
    return game, profile, user


def addon(root: Path, name: str, targets: list[str], *, insertion: str | None = None) -> Path:
    entries = [{"screen": target, "source": SOURCE} for target in targets]
    if insertion is not None:
        for entry in entries:
            entry["profiles"] = [
                {"sha256": "a" * 64, "edits": [{"offset": 0, "remove": 0, "insert": insertion}]}
            ]
    mod = make_mod(
        root,
        name,
        {
            SCREEN_DESCRIPTOR: json.dumps(
                {"schema": 2 if insertion is not None else 1, "extensions": entries}
            ).encode(),
            **({SOURCE: LUA} if targets else {}),
        },
    )
    (mod / "mod.xml").write_text(f'<data name="Screen mod {name}"/>', encoding="utf-8")
    return mod


def assert_report_contract(plan) -> None:
    schema = json.loads(
        (Path(workflow.__file__).parent / "schemas/package.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(plan.report)
    assert plan.report["schema_version"] == 2
    assert not plan.report["installable"]


@pytest.mark.parametrize("collision", ["target", "owned_file"])
def test_managed_menu_collision_names_owner_and_offers_supported_action(
    tmp_path: Path, setup, collision: str
) -> None:
    game, profile, user = setup
    if collision == "target":
        addon(tmp_path / "workshop", "menu-mod", [MENU_PATH])
    else:
        mod = make_mod(tmp_path / "workshop", "menu-mod", {SCREEN_SOURCE: LUA})
        (mod / "mod.xml").write_text('<data name="Screen mod menu-mod"/>', encoding="utf-8")
    plan = workflow.analyze(game, discover([tmp_path / "workshop"]), ["menu-mod"], profile=profile)
    block = next(item for item in plan.blockers if item["code"] == "managed_menu_collision")
    assert block["participants"] == ["menu-mod"]
    assert block["file"] == (MENU_PATH if collision == "target" else SCREEN_SOURCE)
    assert not any(item["code"] == "native_plugin_review_required" for item in plan.blockers)
    feedback = explain_rejection(plan.report, {"menu-mod"}, {"menu-mod"})
    assert "Screen mod menu-mod" in feedback.message
    assert "ModLoader" in feedback.message
    assert "Отключите" in feedback.message
    assert set(feedback.rows) == {"menu-mod"}
    assert "managed_menu" not in plan.report
    assert_report_contract(plan)
    before = (user / "mods.xml").read_bytes()
    with pytest.raises(InputError):
        workflow.apply_plan(plan, user, game_running=lambda: False)
    assert (user / "mods.xml").read_bytes() == before


@pytest.mark.parametrize("source_count", [16, 17])
def test_entry_limit_reports_actual_count_and_exact_owners(
    tmp_path: Path, setup, source_count: int
) -> None:
    game, profile, _ = setup
    addon(tmp_path / "workshop", "first", [f"scripts/screen_{i}.lua" for i in range(8)])
    addon(
        tmp_path / "workshop",
        "second",
        [f"scripts/screen_{i}.lua" for i in range(8, source_count)],
    )
    plan = workflow.analyze(
        game, discover([tmp_path / "workshop"]), ["first", "second"], profile=profile
    )
    block = next(item for item in plan.blockers if item["code"] == "screen_extension_limits")
    assert block["limit_kind"] == "entries"
    assert block["actual"] == 17  # Either the owned menu or the 17th source entry exceeds 16.
    assert block["maximum"] == 16
    assert block["participants"] == ["first", "second"]
    feedback = explain_rejection(plan.report, {"first", "second"}, {"first", "second"})
    assert "17" in feedback.message and "16" in feedback.message
    assert "Отключите" in feedback.message
    assert set(feedback.rows) == {"first", "second"}
    assert_report_contract(plan)


def test_combined_descriptor_byte_limit_has_actual_size_and_owner_rows(tmp_path: Path, setup):
    game, profile, _ = setup
    insertion = "-- " + "x" * 33000 + "\n"
    addon(tmp_path / "workshop", "first", ["scripts/screen_holomap.lua"], insertion=insertion)
    addon(tmp_path / "workshop", "second", ["scripts/screen_propulsion.lua"], insertion=insertion)
    plan = workflow.analyze(
        game, discover([tmp_path / "workshop"]), ["second", "first"], profile=profile
    )
    block = next(item for item in plan.blockers if item["code"] == "screen_extension_limits")
    assert block["limit_kind"] == "descriptor_bytes"
    assert block["actual"] > 65536
    assert block["maximum"] == 65536
    assert block["participants"] == ["second", "first"]
    feedback = explain_rejection(plan.report, {"first", "second"}, {"first", "second"})
    assert str(block["actual"]) in feedback.message
    assert str(block["maximum"]) in feedback.message
    assert "байт" in feedback.message and "Отключите" in feedback.message
    assert set(feedback.rows) == {"first", "second"}
    assert_report_contract(plan)


@pytest.mark.parametrize("stage", ["source_adapter", "with_owned_menu"])
def test_source_byte_limit_is_actionable_at_each_composition_stage(
    tmp_path: Path, setup, monkeypatch: pytest.MonkeyPatch, stage: str
):
    game, profile, _ = setup
    addon(tmp_path / "workshop", "first", ["scripts/screen_holomap.lua"])
    addon(tmp_path / "workshop", "second", ["scripts/screen_propulsion.lua"])
    source_bytes = 2 * len(LUA)
    if stage == "source_adapter":
        maximum = source_bytes - 1
        monkeypatch.setattr(screens, "MAX_TOTAL_BYTES", maximum)
        expected = source_bytes
    else:
        expected = source_bytes + len(screen_source(("Screen mod first", "Screen mod second")))
        maximum = expected - 1
        monkeypatch.setattr(workflow, "MAX_TOTAL_BYTES", maximum)
    plan = workflow.analyze(
        game, discover([tmp_path / "workshop"]), ["first", "second"], profile=profile
    )
    block = next(item for item in plan.blockers if item["code"] == "screen_extension_limits")
    assert block["limit_kind"] == "source_bytes"
    assert block["actual"] == expected
    assert block["maximum"] == maximum
    assert block["participants"] == ["first", "second"]
    feedback = explain_rejection(plan.report, {"first", "second"}, {"first", "second"})
    assert str(expected) in feedback.message and str(maximum) in feedback.message
    assert set(feedback.rows) == {"first", "second"}
    assert_report_contract(plan)


def test_legacy_limit_report_still_offers_action_without_numeric_fields():
    report = {
        "sources": [{"id": "addon", "name": "Screen mod addon"}],
        "files": [],
        "blockers": [{"code": "screen_extension_limits", "participants": ["addon"]}],
    }
    feedback = explain_rejection(report, {"addon"}, {"addon"})
    assert "Screen mod addon" in feedback.message
    assert "Отключите" in feedback.message
    assert "{p0}" not in feedback.message


@pytest.mark.parametrize("limit", ["descriptor_bytes", "source_bytes", "entries"])
def test_individual_sdk_limits_report_actual_size_before_other_diagnostics(
    tmp_path: Path, setup, limit: str
):
    game, profile, _ = setup
    mod = addon(tmp_path / "workshop", "oversized", ["scripts/screen_holomap.lua"])
    if limit == "descriptor_bytes":
        maximum = screens.MAX_MANIFEST_BYTES
        (mod / "content" / SCREEN_DESCRIPTOR).write_bytes(b" " * (maximum + 1))
        actual = maximum + 1
    elif limit == "source_bytes":
        maximum = screens.MAX_SOURCE_BYTES
        (mod / "content" / SOURCE).write_bytes(b"--" + b" " * (maximum - 1))
        actual = maximum + 1
    else:
        maximum = screens.MAX_EXTENSIONS
        actual = maximum + 1
        value = {
            "schema": 1,
            "extensions": [
                {"screen": f"scripts/screen_{i}.lua", "source": SOURCE} for i in range(actual)
            ],
        }
        (mod / "content" / SCREEN_DESCRIPTOR).write_bytes(json.dumps(value).encode())
    plan = workflow.analyze(game, discover([tmp_path / "workshop"]), ["oversized"], profile=profile)
    first = plan.blockers[0]
    assert first["code"] == "screen_extension_limits"
    assert first["limit_kind"] == limit
    assert first["actual"] == actual
    assert first["maximum"] == maximum
    assert first["participants"] == ["oversized"]
    feedback = explain_rejection(plan.report, {"oversized"}, {"oversized"})
    assert "Screen mod oversized" in feedback.message
    assert str(actual) in feedback.message and str(maximum) in feedback.message
    assert "Отключите" in feedback.message
    assert_report_contract(plan)


def test_empty_descriptor_owner_is_not_blamed_for_an_aggregate_limit(tmp_path: Path, setup):
    game, profile, _ = setup
    addon(tmp_path / "workshop", "empty", [])
    addon(
        tmp_path / "workshop",
        "full",
        [f"scripts/screen_{i}.lua" for i in range(screens.MAX_EXTENSIONS)],
    )
    plan = workflow.analyze(
        game, discover([tmp_path / "workshop"]), ["empty", "full"], profile=profile
    )
    block = next(item for item in plan.blockers if item["code"] == "screen_extension_limits")
    assert block["participants"] == ["full"]
    feedback = explain_rejection(plan.report, {"empty", "full"}, {"empty", "full"})
    assert set(feedback.rows) == {"full"}


def test_owned_menu_refusal_does_not_approve_an_unrelated_dll(tmp_path: Path, setup):
    game, profile, _ = setup
    make_mod(
        tmp_path / "workshop", "unsafe", {SCREEN_SOURCE: LUA, "cc2x/unknown.dll": b"MZ unreviewed"}
    )
    plan = workflow.analyze(game, discover([tmp_path / "workshop"]), ["unsafe"], profile=profile)
    assert any(item["code"] == "managed_menu_collision" for item in plan.blockers)
    assert any(item["code"] == "native_plugin_review_required" for item in plan.blockers)
    assert "cc2x/unknown.dll" not in plan.payload
    assert SCREEN_SOURCE not in plan.payload
    assert_report_contract(plan)


def test_ordinary_menu_resource_changes_keep_the_normal_three_way_merge(
    tmp_path: Path, setup, monkeypatch: pytest.MonkeyPatch
):
    game, profile, _ = setup
    base = b"a=1\n\n\nb=1\n"
    original = game.root / "rom_0" / MENU_PATH
    original.parent.mkdir(parents=True)
    original.write_bytes(base)
    make_mod(tmp_path / "workshop", "first", {MENU_PATH: base.replace(b"a=1", b"a=2")})
    make_mod(tmp_path / "workshop", "second", {MENU_PATH: base.replace(b"b=1", b"b=2")})
    monkeypatch.setattr("cc2_mce.merge.validate_content", lambda *a, **kw: ("valid", ""))
    plan = workflow.analyze(
        game, discover([tmp_path / "workshop"]), ["first", "second"], profile=profile
    )
    assert not plan.blockers
    assert plan.payload[MENU_PATH] == b"a=2\n\n\nb=2\n"
    assert original.read_bytes() == base
    assert json.loads(plan.payload[SCREEN_DESCRIPTOR])["extensions"][-1]["screen"] == MENU_PATH
