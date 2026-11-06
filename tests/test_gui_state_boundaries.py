"""Cross-stage GUI recovery checks using owned files and no actual process creation."""

from pathlib import Path
from unittest.mock import Mock

from cc2_mce.game_launch import launch_game
from cc2_mce.workflow import restore_previous
from tests.test_gui_discovery import auto_pair as auto_pair
from tests.test_gui_discovery import pump_until
from tests.test_gui_discovery import window as window
from tests.test_paths_discovery import make_mod


def _settled(window):
    return not window.busy and not window.applying and not window.selection_dirty


def test_successful_undo_revalidates_and_clears_failed_launch_session_flag(auto_pair, monkeypatch):
    window, _ = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    window.checks["b"].invoke()
    pump_until(window, lambda: _settled(window))
    running = [True]
    spawn = Mock(name="owned_process_boundary")
    monkeypatch.setattr(
        "cc2_mce.gui.launch_game",
        lambda game, user, package: launch_game(
            game, user, package, spawn=spawn, game_running=lambda: running[0]
        ),
    )

    assert window.launch() is False
    assert window._launch_refused
    spawn.assert_not_called()
    running[0] = False
    monkeypatch.setattr("cc2_mce.gui.messagebox.askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "cc2_mce.gui.restore_previous",
        lambda user: restore_previous(user, game_running=lambda: False),
    )
    window.restore()
    pump_until(window, lambda: _settled(window) and window._applied_ids == {"a"})

    assert spawn.call_count == 0, "Undo must validate without creating even a mocked process"
    assert window._activation_known
    assert not window._launch_refused
    assert window.launch_button.instate(["!disabled"])
    assert window.launch() is True
    assert spawn.call_count == 1


def test_repaired_inventory_notice_disappears_without_reapplying(auto_pair, tmp_path: Path):
    window, _ = auto_pair
    metadata = tmp_path / "workshop/b/mod.xml"
    original = metadata.read_bytes()
    metadata.write_bytes(b"Owned invalid metadata")
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan.issue_count == 1)
    assert window.notice_title.get()
    assert "Invalid metadata XML" in window.problem_details
    assert window._diagnostic_report is not None

    metadata.write_bytes(original)
    window.scan_sources(preserve_selection=True, rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan.issue_count == 0)

    assert "b" in window.vars and window.checks["b"].instate(["!disabled"])
    assert not window.vars["b"].get()
    assert not window.notice_title.get()
    assert not window.problem_details
    assert window._diagnostic_report is None
    assert not window.selection_dirty and window._auto_timer is None


def test_inventory_repair_keeps_an_unrelated_rejected_selection_notice(auto_pair, tmp_path: Path):
    window, _ = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=1\n")
    window.checks["b"].invoke()
    pump_until(window, lambda: _settled(window) and bool(window.notice_title.get()))
    rejected_notice = window.notice_title.get(), window.notice_text.get()
    rejected_details = window.problem_details
    rejected_report = window.problem_report
    assert rejected_report is not None
    bad = make_mod(tmp_path / "workshop", "c", {"safe.txt": b"owned"})
    (bad / "mod.xml").write_bytes(b"Owned malformed third package")
    window.scan_sources(preserve_selection=True, rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan.issue_count == 1)
    assert (window.notice_title.get(), window.notice_text.get()) == rejected_notice
    assert "Invalid metadata XML" in window.problem_details

    (bad / "mod.xml").write_text('<data name="Healthy C"/>', encoding="utf-8")
    window.scan_sources(preserve_selection=True, rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy and window.scan.issue_count == 0)

    assert (window.notice_title.get(), window.notice_text.get()) == rejected_notice
    assert window.problem_details == rejected_details
    assert window.problem_report is rejected_report
    assert window.vars["a"].get() and not window.vars["b"].get() and not window.vars["c"].get()
    assert window.launch_button.instate(["!disabled"])
