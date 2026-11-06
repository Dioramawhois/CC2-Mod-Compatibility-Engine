"""Real Tk regressions for the beta-12 audit; only owned files and mock spawns."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from cc2_mce.discovery import discover
from cc2_mce.installation import Installations
from cc2_mce.workflow import analyze, apply_plan, recover_interrupted, restore_previous
from tests.test_gui_discovery import pump_until
from tests.test_gui_discovery import window as window
from tests.test_paths_discovery import make_mod
from tests.test_runtime_upgrade import NEW, OLD
from tests.test_runtime_upgrade import plan as runtime_plan
from tests.test_runtime_upgrade import setup as setup
from tests.test_signed_runtime_provider import prepare as signed_plan
from tests.test_signed_runtime_provider import signed_sdk as signed_sdk
from tests.test_workflow import fixture


@pytest.mark.parametrize("initial_kind", ["library", "mod"])
def test_package_kind_change_moves_checkbox_without_losing_other_rows(
    window, tmp_path: Path, monkeypatch, initial_kind
):
    game, _, user = fixture(tmp_path)
    source = tmp_path / "changing-kind"
    package = make_mod(source, "moving", {"safe.txt": b"owned data"})
    make_mod(source, "stable", {"other.txt": b"unrelated owned data"})
    metadata = package / "mod.xml"

    def change_kind(kind):
        metadata.write_text(
            '<data name="Moving Package"><cc2mce schema="1" type="' + kind + '"/></data>',
            encoding="utf-8",
        )

    change_kind(initial_kind)
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: user)
    window.apply_installations(Installations((game,), (source,), ()))
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan is not None)
    old = window.checks["moving"]
    stable = window.checks["stable"]
    target_kind = "mod" if initial_kind == "library" else "library"

    change_kind(target_kind)
    window.scan_sources(preserve_selection=True, rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy)

    assert not old.winfo_exists()
    assert window.checks["stable"] is stable
    assert stable.winfo_exists()
    moved = window.checks["moving"]
    assert moved.winfo_exists()
    target_vars = window.vars if target_kind == "mod" else window.library_vars
    other_vars = window.library_vars if target_kind == "mod" else window.vars
    target_frame = window.list_frame if target_kind == "mod" else window.library_frame
    assert "moving" in target_vars and "moving" not in other_vars
    assert window._row_frames["moving"].master is target_frame

    window.scan_sources(preserve_selection=True, rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy)
    assert window.checks["moving"] is moved
    monkeypatch.setattr(window, "_queue_rebuild", lambda *args: None)
    moved.invoke()
    assert target_vars["moving"].get()
    assert window._desired_ids == {"moving"}


@pytest.mark.parametrize("damaged_package", [False, True])
def test_partial_native_undo_reports_recovery_and_only_verified_resource_state(
    window, setup, monkeypatch, damaged_package
):
    game, profile, user, source = setup
    previous = analyze(game, discover([source.parent / "workshop"]), ["a", "b"], profile=profile)
    package = apply_plan(previous, user, game_running=lambda: False)
    apply_plan(runtime_plan(setup), user, game_running=lambda: False)
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: user)
    monkeypatch.setattr(
        "cc2_mce.gui.restore_previous",
        lambda directory: restore_previous(directory, game_running=lambda: False),
    )
    monkeypatch.setattr("cc2_mce.gui.messagebox.askyesno", lambda *args, **kwargs: True)
    window.apply_installations(Installations((game,), (source, source.parent / "workshop"), ()))
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan is not None)
    assert window._applied_ids == {"app"}
    external_loader = b"owned unknown external runtime; never load"
    (game.root / "dinput8.dll").write_bytes(external_loader)
    if damaged_package:
        (package / "content/a.txt").write_bytes(b"owned external content change")
    spawn = Mock(name="forbidden_game_spawn")
    monkeypatch.setattr("cc2_mce.gui.launch_game", spawn)

    window.restore()
    pump_until(window, lambda: not window.busy and not window.applying)

    assert (user / "cc2-mce/pending.json").is_file()
    assert (game.root / "dinput8.dll").read_bytes() == external_loader
    assert window.notice_title.get() == "Восстановление не завершено. Запуск игры заблокирован."
    assert "обновите список" in window.notice_text.get()
    assert window._diagnostic_report is not None
    assert not window.selection_dirty and not window._play_requested
    assert window.launch_button.instate(["disabled"])
    assert window.disable_all_button.instate(["disabled"])
    assert window.actions_menu.entrycget(window._undo_index, "state") == "disabled"
    assert all(check.instate(["disabled"]) for check in window.checks.values())
    assert not window.launch()
    spawn.assert_not_called()
    if damaged_package:
        assert not window._activation_known
        assert window._applied_ids == set()
        assert not any(variable.get() for variable in window.vars.values())
        assert "не подтверждён" in window.activation_status.get()
        assert all("не подтверждено" in row.get() for row in window.row_status.values())
    else:
        assert json.loads((package / "mce-manifest.json").read_text())["mod_order"] == ["a", "b"]
        assert window._activation_known
        assert window._applied_ids == {"a", "b"}
        assert window._desired_ids == {"a", "b"}
        assert window._applied_order == ["a", "b"]
        assert window.vars["a"].get() and window.vars["b"].get()
        assert not window.vars["app"].get()
        assert "Проверенные файлы набора:" in window.activation_status.get()
        assert "Runtime changed externally" in window.problem_details


@pytest.mark.parametrize("preserve_selection", [False, True])
def test_completed_recovery_refresh_clears_refusal_with_unchanged_inventory(
    window, setup, monkeypatch, preserve_selection
):
    game, profile, user, source = setup
    previous = analyze(game, discover([source.parent / "workshop"]), ["a", "b"], profile=profile)
    apply_plan(previous, user, game_running=lambda: False)
    apply_plan(runtime_plan(setup), user, game_running=lambda: False)
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: user)
    monkeypatch.setattr(
        "cc2_mce.gui.restore_previous",
        lambda directory: restore_previous(directory, game_running=lambda: False),
    )
    monkeypatch.setattr(
        "cc2_mce.gui.recover_interrupted",
        lambda directory: recover_interrupted(directory, game_running=lambda: False),
    )
    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(game, scan, selected, profile=profile),
    )
    monkeypatch.setattr(
        "cc2_mce.gui.apply_plan",
        lambda plan, directory: apply_plan(plan, directory, game_running=lambda: False),
    )
    monkeypatch.setattr("cc2_mce.gui.messagebox.askyesno", lambda *args, **kwargs: True)
    spawn = Mock(name="forbidden_game_spawn")
    monkeypatch.setattr("cc2_mce.gui.launch_game", spawn)
    window.apply_installations(Installations((game,), (source, source.parent / "workshop"), ()))
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan is not None)
    fingerprint = window.scan.fingerprint
    runtime = game.root / "dinput8.dll"
    runtime.write_bytes(b"owned unknown external replacement; never load")
    window._play_requested = True
    window.restore()
    pump_until(window, lambda: not window.busy and not window.applying)
    assert (user / "cc2-mce/pending.json").is_file()
    assert not window._play_requested
    runtime.write_bytes(NEW)

    window.scan_sources(preserve_selection=preserve_selection)
    pump_until(
        window,
        lambda: not window.busy and not window.applying and not window.selection_dirty,
    )

    assert window.scan.fingerprint == fingerprint
    assert not (user / "cc2-mce/pending.json").exists()
    assert runtime.read_bytes() == OLD
    assert not window._launch_refused
    assert window._activation_known
    assert window._applied_ids == window._desired_ids == {"a", "b"}
    assert window.vars["a"].get() and window.vars["b"].get()
    assert not window.vars["app"].get()
    assert not window.notice_title.get()
    assert window.launch_button.instate(["!disabled"])
    assert window.disable_all_button.instate(["!disabled"])
    assert all(check.instate(["!disabled"]) for check in window.checks.values())
    assert not window._play_requested
    spawn.assert_not_called()


def test_gui_uses_installed_signed_sdk_when_unselected_source_is_quarantined(
    window, signed_sdk, monkeypatch
):
    game, profile, user, source, sdk, installed, update = signed_sdk
    runtime, _ = update()
    apply_plan(signed_plan(signed_sdk), user, game_running=lambda: False)
    empty = analyze(game, discover([source]), [], profile=profile, user_dir=user)
    apply_plan(empty, user, game_running=lambda: False)
    nested = sdk / "content" / "/".join(["nested"] * 34) / "too-deep.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("owned invalid unselected data", encoding="utf-8")
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: user)
    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(
            game, scan, selected, profile=profile, user_dir=user
        ),
    )
    monkeypatch.setattr(
        "cc2_mce.gui.apply_plan",
        lambda plan, directory: apply_plan(plan, directory, game_running=lambda: False),
    )
    spawn = Mock(name="forbidden_game_spawn")
    monkeypatch.setattr("cc2_mce.gui.launch_game", spawn)
    window.apply_installations(Installations((game,), (source,), ()))
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan is not None)
    assert not window._applied_ids
    assert "workshop-sdk" not in window.library_vars

    window.checks["island-airfields"].invoke()
    pump_until(
        window,
        lambda: not window.busy and not window.selection_dirty and window._auto_timer is None,
    )

    assert window.vars["island-airfields"].get(), window.problem_details
    assert window._applied_ids == {"island-airfields"}
    assert window.launch_button.instate(["!disabled"])
    assert installed.read_bytes() == runtime
    assert "CC2X SDK" in window.problem_details
    assert "Scan depth limit exceeded" in window.problem_details
    spawn.assert_not_called()
