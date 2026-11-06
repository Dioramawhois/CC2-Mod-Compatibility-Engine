from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.filesystem import digest
from cc2_mce.installation import Installations
from cc2_mce.workflow import analyze, apply_plan, restore_previous
from tests.test_gui_discovery import auto_pair as auto_pair
from tests.test_gui_discovery import pump_until
from tests.test_gui_discovery import window as window
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


def test_bundled_sdk_dependency_finishes_gui_apply_without_a_library_row(
    window, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    game, profile, user = fixture(tmp_path)
    runtime = b"Owned reviewed provider fixture; never executed"
    runtime_hash = digest(runtime)
    bundled = tmp_path / "bundled-runtime"
    provider = bundled / runtime_hash / "dinput8.dll"
    provider.parent.mkdir(parents=True)
    provider.write_bytes(runtime)
    profile.update(runtime_sha256=runtime_hash, runtime_api=8)
    mod = make_mod(tmp_path / "workshop", "app", {"app.txt": b"owned data"})
    (mod / "mod.xml").write_text(
        '<data name="SDK Consumer"><cc2mce schema="1" type="mod" sdk="cc2x" api="8">'
        '<requires id="cc2x.runtime"/></cc2mce></data>',
        encoding="utf-8",
    )
    monkeypatch.setattr("cc2_mce.workflow.RUNTIME_DATA", bundled)
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: user)
    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(game, scan, selected, profile=profile),
    )
    monkeypatch.setattr(
        "cc2_mce.gui.apply_plan",
        lambda plan, user: apply_plan(plan, user, game_running=lambda: False),
    )
    errors = []
    monkeypatch.setattr(window, "report_callback_exception", lambda *args: errors.append(args))
    window.apply_installations(Installations((game,), (), ()))
    window.mod_roots = [tmp_path / "workshop"]
    window.display_scan(discover(window.mod_roots))

    window.checks["app"].invoke()
    pump_until(window, lambda: not window.selection_dirty and not window.busy)

    assert not errors, "A dependency supplied by the runtime must not crash the GUI callback"
    assert window._applied_ids == {"app"}
    assert window.vars["app"].get()
    assert not window.library_vars
    assert window._required_notes == {}
    assert "Готово" in window.status.get()
    assert window.launch_button.instate(["!disabled"])
    assert (game.root / "dinput8.dll").read_bytes() == runtime


def test_owned_merge_order_survives_reversed_native_activation(
    auto_pair, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    window, user = auto_pair
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=1\n")
    profile = {
        "game_sha256": digest(window.game.executable.read_bytes()),
        "baselines": {},
        "runtime_sha256": None,
        "native_plugins": {},
    }
    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(
            game, scan, selected, profile=profile, patch_priority=kwargs["patch_priority"]
        ),
    )
    window.patch_priority = True
    window.priority_var.set(True)
    window.vars["a"].set(True)
    window.vars["b"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty and not window.busy)
    output = user / "mods/CC2-MCE/content/a.txt"
    assert window._applied_order == ["a", "b"]
    assert output.read_bytes() == b"a=3\n\n\nb=1\n"

    (user / "mods.xml").write_text(
        f'<data><active_mod_folders><path value="{tmp_path / "workshop/b"}"/>'
        f'<path value="{tmp_path / "workshop/a"}"/></active_mod_folders></data>',
        encoding="utf-8",
    )
    window.scan_sources()
    pump_until(
        window,
        lambda: not window.selection_dirty and not window.busy and window._auto_timer is None,
    )

    assert window._applied_order == ["a", "b"]
    assert output.read_bytes() == b"a=3\n\n\nb=1\n"
    assert window.preferences.order(window.game.root) == ["a", "b"]


def test_first_adoption_retains_native_order_without_saved_owned_selection(
    auto_pair, tmp_path: Path
):
    window, user = auto_pair
    assert not (user / "cc2-mce/activation.json").exists()
    (user / "mods.xml").write_text(
        f'<data><active_mod_folders><path value="{tmp_path / "workshop/b"}"/>'
        f'<path value="{tmp_path / "workshop/a"}"/></active_mod_folders></data>',
        encoding="utf-8",
    )
    window.scan_sources()
    pump_until(
        window,
        lambda: not window.selection_dirty and not window.busy and window._auto_timer is None,
    )
    assert window._applied_order == ["b", "a"]
    assert window._applied_ids == {"a", "b"}


def test_undo_reconstructs_dependency_notes_from_restored_applied_sources(
    auto_pair, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    window, _ = auto_pair
    (tmp_path / "workshop/b/mod.xml").write_text(
        '<data name="Dependent B"><cc2mce schema="1" type="mod"><requires id="a"/></cc2mce></data>',
        encoding="utf-8",
    )
    other = make_mod(tmp_path / "workshop", "c", {"c.txt": b"owned data"})
    (other / "mod.xml").write_text(
        '<data name="Dependent C"><cc2mce schema="1" type="mod"><requires id="a"/></cc2mce></data>',
        encoding="utf-8",
    )
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: "c" in window.vars and not window.busy)
    window.checks["b"].invoke()
    pump_until(window, lambda: not window.selection_dirty and not window.busy)
    assert "Dependent B" in window.row_status["a"].get()

    window.vars["b"].set(False)
    window.vars["c"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty and not window.busy)
    assert "Dependent C" in window.row_status["a"].get()

    # The current source metadata may change after the recorded build was created.
    (tmp_path / "workshop/b/mod.xml").write_text(
        '<data name="Current source B"/>', encoding="utf-8"
    )
    monkeypatch.setattr("cc2_mce.gui.messagebox.askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "cc2_mce.gui.restore_previous",
        lambda user: restore_previous(user, game_running=lambda: False),
    )
    window.restore()
    pump_until(
        window,
        lambda: (
            not window.selection_dirty
            and not window.busy
            and not window.applying
            and window._applied_ids == {"a", "b"}
        ),
    )

    assert window.vars["b"].get() and not window.vars["c"].get()
    assert "Dependent B" in window.row_status["a"].get()
    assert "Dependent C" not in window.row_status["a"].get()
    assert "Current source B" not in window.row_status["a"].get()
