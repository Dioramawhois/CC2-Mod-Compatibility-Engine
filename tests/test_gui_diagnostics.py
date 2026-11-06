"""Production GUI diagnostic callbacks with owned data and no process creation."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from cc2_mce.errors import InputError
from cc2_mce.game_launch import launch_game
from cc2_mce.i18n import Translator
from cc2_mce.workflow import active_paths
from tests.test_gui_discovery import auto_pair as auto_pair
from tests.test_gui_discovery import pump_until
from tests.test_gui_discovery import window as window


def _settled(window):
    return not window.busy and not window.applying and not window.selection_dirty


def _snapshot(root: Path):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _export(window, path: Path, monkeypatch):
    monkeypatch.setattr("cc2_mce.gui.filedialog.asksaveasfilename", lambda **kwargs: str(path))
    monkeypatch.setattr(
        window, "show_problem", lambda: pytest.fail("Structured diagnostics must export directly")
    )
    window.export_report()
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["owner"] == "cc2-mce"
    assert report["schema_kind"] == "diagnostics"
    assert report["schema_version"] == 1
    assert report["installable"] is False
    assert report["diagnostic_count"] >= 1
    assert report["truncated"] is False
    return report


def test_partial_scan_keeps_valid_mod_usable_and_exports_without_plan(
    auto_pair, tmp_path: Path, monkeypatch
):
    window, user = auto_pair
    bad = tmp_path / "workshop/b/mod.xml"
    bad.write_bytes(b"owned invalid XML fixture")

    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: window.scan is not None and not window.busy)

    assert set(window.vars) == {"a"}
    assert window.checks["a"].instate(["!disabled"])
    assert window.package_plan is None and window.problem_report is None
    assert "b" in window.notice_text.get()
    assert str(bad.parent) in window.problem_details
    assert "Invalid metadata XML" in window.problem_details
    exported = _export(window, tmp_path / "inventory-diagnostics.json", monkeypatch)
    issue = exported["diagnostics"][0]
    assert issue["source_id"] == "b"
    assert issue["source_path"] == str(bad.parent.resolve())
    assert issue["resource_path"] == "mod.xml"
    assert "Invalid metadata XML" in issue["cause"]
    assert active_paths(user) == ()

    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))

    assert window._applied_ids == {"a"}
    assert window.vars["a"].get()
    assert [source["id"] for source in window.package_plan.report["sources"]] == ["a"]
    assert active_paths(user) == (user / "mods/CC2-MCE",)
    assert window.launch_button.instate(["!disabled"])
    assert bad.read_bytes() == b"owned invalid XML fixture"


def test_invalid_metadata_of_selected_mod_preserves_applied_output_and_exports_cause(
    auto_pair, tmp_path: Path, monkeypatch
):
    window, user = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    before = _snapshot(user / "mods/CC2-MCE")
    activation = (user / "mods.xml").read_bytes()
    bad = tmp_path / "workshop/a/mod.xml"
    bad.write_bytes(b"owned newly invalid metadata")

    window.scan_sources(preserve_selection=True)
    pump_until(
        window, lambda: _settled(window) and "Invalid metadata XML" in window.problem_details
    )

    assert _snapshot(user / "mods/CC2-MCE") == before
    assert (user / "mods.xml").read_bytes() == activation
    assert window.vars["a"].get() and not window.vars["b"].get()
    assert window._desired_ids == window._applied_ids == {"a"}
    assert window.launch_button.instate(["!disabled"])
    assert str(bad.parent) in window.problem_details
    assert "a" in window.notice_text.get()
    exported = _export(window, tmp_path / "selected-source-diagnostics.json", monkeypatch)
    assert any(
        issue["source_id"] == "a"
        and issue["resource_path"] == "mod.xml"
        and "Invalid metadata XML" in issue["cause"]
        for issue in exported["diagnostics"]
    )


def test_real_launch_guard_stays_refused_until_explicit_rebuild_after_game_change(
    auto_pair, tmp_path: Path, monkeypatch
):
    window, user = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    window.translator = Translator("en")
    executable = window.game.executable
    original = executable.read_bytes()
    package_before = _snapshot(user / "mods/CC2-MCE")
    spawn = Mock(name="owned_process_boundary")
    monkeypatch.setattr(
        "cc2_mce.gui.launch_game",
        lambda game, directory, package: launch_game(
            game, directory, package, spawn=spawn, game_running=lambda: False
        ),
    )
    executable.write_bytes(original + b"owned executable change")

    assert window.launch() is False

    spawn.assert_not_called()
    assert window.status.get() == (
        "The game files changed. Refresh the list to check the selection again."
    )
    assert "Game executable changed since activation" in window.problem_details
    assert str(executable) in window.problem_details
    assert window._launch_refused
    assert window.launch_button.instate(["disabled"])
    assert not window._play_requested
    exported = _export(window, tmp_path / "game-changed-diagnostics.json", monkeypatch)
    assert exported["stage"] == "launch"
    assert exported["diagnostics"][0]["code"] == "launch_game_changed"
    assert exported["diagnostics"][0]["resource_path"] == str(executable)
    original_notice = window.notice_title.get(), window.problem_details, window.status.get()

    window.scan_sources(preserve_selection=True)
    pump_until(window, lambda: not window.busy)

    assert window._launch_refused
    assert window.launch_button.instate(["disabled"])
    assert (
        window.notice_title.get(),
        window.problem_details,
        window.status.get(),
    ) == original_notice
    assert _snapshot(user / "mods/CC2-MCE") == package_before
    spawn.assert_not_called()

    executable.write_bytes(original)
    window.scan_sources()
    pump_until(window, lambda: _settled(window) and not window._launch_refused)

    assert window.launch_button.instate(["!disabled"])
    assert window._applied_ids == {"a"}
    assert window.vars["a"].get()
    spawn.assert_not_called()


@pytest.mark.parametrize(
    ("error", "code", "summary"),
    [
        (
            InputError("Pending activation recovery; close the game before retrying"),
            "launch_recovery_pending",
            "Recovery is incomplete. Game launch is blocked.",
        ),
        (
            InputError("Game is running or its executable is unavailable"),
            "launch_game_unavailable",
            "The game is already running or its executable is unavailable. "
            "Close the game and check its files.",
        ),
        (
            InputError("Game activation changed; rebuild the selected set"),
            "launch_activation_changed",
            "The game's mod selection changed. Refresh the list to rebuild it.",
        ),
        (
            InputError("Game executable changed since activation"),
            "launch_game_changed",
            "The game files changed. Refresh the list to check the selection again.",
        ),
        (
            InputError("Installed runtime changed since activation"),
            "launch_runtime_changed",
            "The SDK loader changed. Refresh the list to check the selection again.",
        ),
        (
            OSError("owned process creation denied"),
            "launch_failed",
            "The game was not launched. Check the problem details.",
        ),
    ],
)
def test_gui_maps_domain_refusals_to_localized_exportable_diagnostics(
    auto_pair, tmp_path: Path, monkeypatch, error, code, summary
):
    """Mocked guard mapping complements the actual domain guard regression above."""
    window, user = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    before = _snapshot(user)
    window.translator = Translator("en")
    refusal = Mock(side_effect=error)
    monkeypatch.setattr("cc2_mce.gui.launch_game", refusal)
    window._play_requested = True

    assert window.launch() is False

    refusal.assert_called_once_with(window.game, user, user / "mods/CC2-MCE")
    assert window.status.get() == summary
    assert str(error) in window.problem_details
    assert window.launch_button.instate(["disabled"])
    assert not window._play_requested
    assert window._launch_refused
    exported = _export(window, tmp_path / "launch-diagnostics.json", monkeypatch)
    issue = exported["diagnostics"][0]
    assert issue["code"] == code and issue["stage"] == "launch"
    assert str(error) in issue["cause"]
    expected_resource = (
        window.game.root / "dinput8.dll"
        if code == "launch_runtime_changed"
        else window.game.executable
    )
    assert issue["resource_path"] == str(expected_resource)
    assert _snapshot(user) == before
