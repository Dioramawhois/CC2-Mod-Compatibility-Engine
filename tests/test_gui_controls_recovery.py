"""Owned hidden-window regressions; these do not launch CC2 or run mod code."""

import json
from pathlib import Path

import pytest

from cc2_mce.installation import Installations, inspect_game
from cc2_mce.workflow import active_paths, restore_previous
from tests.test_gui_discovery import auto_pair as auto_pair
from tests.test_gui_discovery import pump_until
from tests.test_gui_discovery import window as window
from tests.test_installation import game
from tests.test_paths_discovery import make_mod


def _settled(window):
    return not window.busy and not window.applying and not window.selection_dirty


def _disk_snapshot(root: Path):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.fixture
def library_pair(auto_pair, tmp_path: Path):
    window, user = auto_pair
    (tmp_path / "workshop/a/mod.xml").write_text(
        '<data name="Shared tools"><cc2mce schema="1" type="library"/></data>',
        encoding="utf-8",
    )
    (tmp_path / "workshop/b/mod.xml").write_text(
        '<data name="Gameplay"><cc2mce schema="1" type="mod"><requires id="a"/></cc2mce></data>',
        encoding="utf-8",
    )
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: "a" in window.library_vars and not window.busy)
    window.checks["b"].invoke()
    pump_until(window, lambda: _settled(window))
    assert window._applied_ids == {"a", "b"}
    assert window.library_vars["a"].get() and window.vars["b"].get()
    return window, user


def test_disable_all_applies_once_including_required_library_and_undo_restores(
    library_pair, monkeypatch
):
    import cc2_mce.gui as gui

    window, user = library_pair
    package = user / "mods/CC2-MCE"
    previous = (package / "content/a.txt").read_bytes()
    original_apply = gui.apply_plan
    applied = []

    def record_apply(plan, directory):
        applied.append(list(plan.report["mod_order"]))
        return original_apply(plan, directory)

    monkeypatch.setattr(gui, "apply_plan", record_apply)
    monkeypatch.setattr(
        gui.messagebox, "askyesno", lambda *args, **kwargs: pytest.fail("No apply confirmation")
    )
    assert window.disable_all_button.instate(["!disabled"])
    window.disable_all_button.invoke()
    pump_until(window, lambda: _settled(window))

    assert applied == [[]]
    assert active_paths(user) == ()
    assert window._applied_ids == window._desired_ids == set()
    assert not any(var.get() for var in [*window.vars.values(), *window.library_vars.values()])
    assert window.disable_all_button.instate(["disabled"])
    assert window.launch_button.instate(["!disabled"])

    monkeypatch.setattr(gui.messagebox, "askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        gui,
        "restore_previous",
        lambda directory: restore_previous(directory, game_running=lambda: False),
    )
    window.restore()
    pump_until(window, lambda: _settled(window) and window._applied_ids == {"a", "b"})
    assert active_paths(user) == (package,)
    assert (package / "content/a.txt").read_bytes() == previous
    assert window.library_vars["a"].get() and window.vars["b"].get()
    assert applied == [[]], "Undo must restore the recorded set without an automatic reapply"


def test_disable_all_defers_while_running_and_cancels_requested_launch(auto_pair, monkeypatch):
    window, user = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    before = _disk_snapshot(user)
    running = [True]
    monkeypatch.setattr("cc2_mce.gui._running", lambda: running[0])
    monkeypatch.setattr(
        "cc2_mce.gui.launch_game", lambda *args: pytest.fail("Disable all must not launch vanilla")
    )
    window._play_requested = True
    window.disable_all_button.invoke()
    pump_until(window, lambda: window.selection_dirty and "Закройте игру" in window.status.get())

    assert not window._play_requested
    assert window._desired_ids == set()
    assert window._applied_ids == {"a"}
    assert _disk_snapshot(user) == before
    assert window.launch_button.instate(["disabled"])

    running[0] = False
    pump_until(window, lambda: _settled(window))
    assert active_paths(user) == ()
    assert not window._play_requested
    assert window.disable_all_button.instate(["disabled"])


def test_disable_all_is_disabled_for_empty_selection_and_during_apply(auto_pair):
    window, _ = auto_pair
    window._refresh_controls()
    assert window.disable_all_button.instate(["disabled"])
    generation = window._generation
    window.disable_all()
    assert window._generation == generation
    assert not window.selection_dirty

    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    assert window.disable_all_button.instate(["!disabled"])
    window._set_applying(True)
    try:
        generation = window._generation
        window.disable_all_button.invoke()
        window.disable_all()
        assert window.disable_all_button.instate(["disabled"])
        assert window._generation == generation
        assert window._desired_ids == {"a"}
        assert window.vars["a"].get()
    finally:
        window._set_applying(False)
    assert window.disable_all_button.instate(["!disabled"])


def test_screen_lua_library_is_not_labeled_dll_but_real_dll_is(window, tmp_path: Path):
    root = game(tmp_path / "game")
    descriptor = {
        "schema": 1,
        "extensions": [{"screen": "scripts/screen_holomap.lua", "source": "cc2x/ui/panel.lua"}],
    }
    libraries = {
        "screen": {
            "cc2x/screen_extensions.json": json.dumps(descriptor).encode(),
            "cc2x/ui/panel.lua": b"-- owned syntax-only fixture; never executed\n",
        },
        "dll": {"cc2x/plugins/example.dll": b"MZ-owned-invalid-fixture-never-loaded"},
        "opaque": {"cc2x/opaque.dat": b"owned unreviewed data"},
    }
    for name, files in libraries.items():
        library = make_mod(root / "libraries", name, files)
        (library / "mod.xml").write_text(
            f'<data name="{name}"><cc2mce schema="1" type="library"/></data>',
            encoding="utf-8",
        )
    installation = inspect_game(root)
    assert installation is not None
    window.apply_installations(Installations((installation,), (), ()))
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: set(window.library_vars) == set(libraries) and not window.busy)

    screen_label = window.row_status["screen"].get()
    assert "Lua" in screen_label and "SDK-расширения экранов" in screen_label
    assert "DLL" not in screen_label and "Нативные файлы" not in screen_label
    assert "DLL-плагин" in window.row_status["dll"].get()
    assert "Нативные файлы" in window.row_status["opaque"].get()
    assert "DLL" not in window.row_status["opaque"].get()
    assert not (root / "dinput8.dll").exists()
    assert window.active_package is None


def test_passive_add_and_rename_preserve_existing_widgets_variables_and_selection(
    library_pair, tmp_path: Path
):
    window, _ = library_pair
    checks = {key: window.checks[key] for key in ("a", "b")}
    variables = {"a": window.library_vars["a"], "b": window.vars["b"]}
    for key, name in (("a", "Renamed shared tools"), ("b", "Renamed gameplay")):
        path = tmp_path / "workshop" / key / "mod.xml"
        text = path.read_text(encoding="utf-8")
        text = text.replace('name="Shared tools"', f'name="{name}"')
        text = text.replace('name="Gameplay"', f'name="{name}"')
        path.write_text(text, encoding="utf-8")
    make_mod(tmp_path / "workshop", "c", {"c.txt": b"new unchecked gameplay"})
    new_library = make_mod(tmp_path / "workshop", "d", {"d.txt": b"new unchecked library"})
    (new_library / "mod.xml").write_text(
        '<data name="New library"><cc2mce schema="1" type="library"/></data>',
        encoding="utf-8",
    )

    window.scan_sources(preserve_selection=True)
    pump_until(
        window, lambda: "c" in window.vars and "d" in window.library_vars and _settled(window)
    )

    assert window.checks["a"] is checks["a"] and window.checks["b"] is checks["b"]
    assert window.library_vars["a"] is variables["a"] and window.vars["b"] is variables["b"]
    assert variables["a"].get() and variables["b"].get()
    assert "Renamed shared tools" in window.checks["a"].cget("text")
    assert "Renamed gameplay" in window.checks["b"].cget("text")
    assert not window.vars["c"].get() and not window.library_vars["d"].get()
    assert window._desired_ids == window._applied_ids == {"a", "b"}


def test_passive_inventory_preserves_hidden_list_scroll_position(window, tmp_path: Path):
    root = game(tmp_path / "game")
    for number in range(40):
        make_mod(root / "mods", f"mod-{number:02}", {f"{number}.txt": b"owned text"})
    installation = inspect_game(root)
    assert installation is not None
    window.apply_installations(Installations((installation,), (), ()))
    window.scan_sources(rebuild_after_scan=False)
    pump_until(window, lambda: len(window.vars) == 40 and not window.busy)
    window.update_idletasks()
    canvas = window._scroll_canvases[window.list_frame]
    canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.yview_moveto(0.45)
    before = canvas.yview()[0]
    if before == 0:
        pytest.skip("Withdrawn Tk canvas cannot scroll on this host")
    first = window.checks["mod-00"]
    make_mod(root / "mods", "new-mod", {"new.txt": b"owned new text"})

    window.scan_sources(preserve_selection=True, rebuild_after_scan=False)
    pump_until(window, lambda: "new-mod" in window.vars and not window.busy)
    window.update_idletasks()

    assert window.checks["mod-00"] is first
    assert canvas.yview()[0] == pytest.approx(before, abs=0.015)


def test_undo_menu_disabled_without_history_and_after_consumed_restore(auto_pair, monkeypatch):
    window, user = auto_pair
    window._refresh_controls()
    assert window.actions_menu.entrycget(window._undo_index, "state") == "disabled"
    monkeypatch.setattr(
        "cc2_mce.gui.messagebox.askyesno",
        lambda *args, **kwargs: pytest.fail("No confirmation without an Undo journal"),
    )
    window.restore()
    assert "Нет предыдущего набора" in window.status.get()

    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    assert window.actions_menu.entrycget(window._undo_index, "state") == "normal"
    monkeypatch.setattr("cc2_mce.gui.messagebox.askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "cc2_mce.gui.restore_previous",
        lambda directory: restore_previous(directory, game_running=lambda: False),
    )
    window.restore()
    pump_until(window, lambda: _settled(window) and not (user / "cc2-mce/activation.json").exists())
    assert window.actions_menu.entrycget(window._undo_index, "state") == "disabled"
    assert active_paths(user) == ()
    monkeypatch.setattr(
        "cc2_mce.gui.messagebox.askyesno",
        lambda *args, **kwargs: pytest.fail("Consumed history must not prompt again"),
    )
    window.restore()
    assert "Нет предыдущего набора" in window.status.get()


def test_direct_undo_rechecks_history_removed_since_menu_was_enabled(auto_pair, monkeypatch):
    window, user = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: _settled(window))
    assert window.actions_menu.entrycget(window._undo_index, "state") == "normal"
    (user / "cc2-mce/activation.json").unlink()
    before = _disk_snapshot(user)
    monkeypatch.setattr(
        "cc2_mce.gui.messagebox.askyesno",
        lambda *args, **kwargs: pytest.fail("Stale Undo must recheck before confirming"),
    )

    window.restore()

    assert "Нет предыдущего набора" in window.status.get()
    assert window.actions_menu.entrycget(window._undo_index, "state") == "disabled"
    assert _disk_snapshot(user) == before
