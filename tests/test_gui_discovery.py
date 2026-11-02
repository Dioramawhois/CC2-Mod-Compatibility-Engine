import gc
import shutil
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import pytest

from cc2_mce.gui import App
from cc2_mce.installation import Installations, inspect_game
from tests.test_installation import game
from tests.test_paths_discovery import make_mod


@pytest.fixture
def window(monkeypatch, tmp_path: Path):
    from cc2_mce.filesystem import digest
    from cc2_mce.toolchain import Toolchain

    # GUI/service tests use the toolchain port; the real frozen bundle has its own smoke.
    # CI checkouts deliberately do not contain ignored, machine-built Windows executables.
    tools = Toolchain(
        Path(shutil.which("git") or "git"), tmp_path / "absent-luac", digest(b"fixture")
    )
    monkeypatch.setattr("cc2_mce.gui.bundled_tools", lambda: tools)
    monkeypatch.setattr("cc2_mce.gui._running", lambda: False)
    isolated_user = tmp_path / "gui-user"
    isolated_user.mkdir()
    (isolated_user / "mods.xml").write_text("<data><active_mod_folders/></data>")
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: isolated_user)
    try:
        app = App(discover_on_start=False, patch_priority=False, language="ru")
    except tk.TclError:
        pytest.skip("GUI display unavailable; not a GUI acceptance pass")
    app.withdraw()
    yield app
    app.destroy()
    app.vars.clear()
    app.library_vars.clear()
    gc.collect()  # Collect destroyed Tk cycles on their owning thread, never in a merge worker.


def test_detected_game_shows_paths_without_inventing_baseline(window, tmp_path: Path) -> None:
    root = game(tmp_path / "CC2")
    installation = inspect_game(root)
    assert installation is not None
    window.apply_installations(Installations((installation,), (), ()))
    assert str(root) in window.game_path.get()
    assert str(root / "libraries") in window.libraries_path.get()
    assert window.baseline is None
    assert window.package_plan is None
    assert not (root / "mods").exists()
    assert not (root / "cc2x").exists()
    assert not (root / "libraries").exists()


def test_workshop_and_local_mod_names_show_without_moving_inputs(window, tmp_path: Path) -> None:
    root = game(tmp_path / "CC2")
    workshop = tmp_path / "workshop/1489630"
    make_mod(workshop, "12345", {"a.txt": b"workshop"})
    make_mod(root / "mods", "local", {"b.txt": b"local"})
    installation = inspect_game(root)
    assert installation is not None
    window.apply_installations(Installations((installation,), (workshop,), ()))
    # Exercise the same service used by the background scan, then its real widgets.
    from cc2_mce.discovery import discover

    window.display_scan(discover(window.mod_roots))
    assert set(window.vars) == {"12345", "local"}
    labels = [str(child.cget("text")) for child in window.checks.values()]
    assert any("Synthetic" in label for label in labels)
    assert any("Workshop" in value.get() for value in window.row_status.values())
    assert (workshop / "12345/content/a.txt").read_bytes() == b"workshop"


def test_windows_portable_requires_exe_beside_game(window, tmp_path: Path) -> None:
    root = game(tmp_path / "CC2")
    window.portable_required = True
    window.app_dir = tmp_path / "downloads"
    installation = inspect_game(root)
    assert installation is not None
    window.apply_installations(Installations((installation,), (), ()))
    assert "Перенесите" in window.status.get()
    assert window.needs_placement
    window.app_dir = root
    window.select_game()
    assert not window.needs_placement


def test_ambiguous_games_require_selection(window, tmp_path: Path) -> None:
    one = inspect_game(game(tmp_path / "one"))
    two = inspect_game(game(tmp_path / "two"))
    assert one is not None and two is not None
    window.apply_installations(Installations((one, two), (), ()))
    assert window.game is None
    assert "несколько" in window.status.get()


def test_lua_and_native_library_inventory_and_safe_refusal(window, tmp_path: Path, monkeypatch):
    root = game(tmp_path / "CC2")
    library = make_mod(
        root / "libraries",
        "lib",
        {"scripts/library.lua": b"return 1\n", "cc2x/demo.dll": b"MZ-not-an-executable"},
    )
    (library / "mod.xml").write_text(
        '<data name="Synthetic"><cc2mce schema="1" type="library"/></data>', encoding="utf-8"
    )
    installation = inspect_game(root)
    assert installation is not None
    monkeypatch.setattr(window, "_background", lambda action, receive, **kwargs: receive(action()))
    from cc2_mce.filesystem import digest
    from cc2_mce.workflow import analyze

    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(
            game,
            scan,
            selected,
            tools=kwargs["tools"],
            profile={
                "game_sha256": digest(game.executable.read_bytes()),
                "baselines": {},
                "native_plugins": {},
                "runtime_sha256": None,
            },
        ),
    )
    window.apply_installations(Installations((installation,), (), ()))
    window.scan_sources()
    assert set(window.library_vars) == {"lib"}
    labels = [window.row_status[key].get() for key in window.library_vars]
    assert any("Lua" in label and "DLL" in label for label in labels)
    window.library_vars["lib"].set(True)
    window.selection_changed()
    window.check_selected()
    assert "DLL-плагина" in window.notice_text.get()
    assert not window.library_vars["lib"].get()
    assert window.active_package is None
    assert (library / "content/cc2x/demo.dll").read_bytes() == b"MZ-not-an-executable"
    assert not (root / "dinput8.dll").exists()


def test_changing_selection_invalidates_pending_result(window):
    before = window._generation
    window.selection_changed()
    assert window._generation > before
    assert window.selection_dirty


def test_background_scan_updates_widgets_without_running_library(window, tmp_path: Path):
    root = game(tmp_path / "game")
    make_mod(root / "mods", "mod", {"a.txt": b"mod data"})
    library = make_mod(root / "libraries", "lib", {"cc2x/fake.dll": b"never execute"})
    (library / "mod.xml").write_text(
        '<data name="Synthetic"><cc2mce schema="1" type="library"/></data>', encoding="utf-8"
    )
    installed = inspect_game(root)
    assert installed is not None
    window.discover_on_start = True
    window.apply_installations(Installations((installed,), (), ()))
    deadline = time.monotonic() + 5
    while window.library_scan is None and time.monotonic() < deadline:
        window.update()
        time.sleep(0.01)
    assert set(window.vars) == {"mod"}
    assert set(window.library_vars) == {"lib"}
    assert "Найдено модов: 1, библиотек: 1" in window.status.get()
    assert window.package_plan is None
    assert window.active_package is None


def test_gui_checkbox_automatically_changes_game_activation(window, tmp_path: Path, monkeypatch):
    from cc2_mce.discovery import discover
    from cc2_mce.workflow import analyze, apply_plan
    from tests.test_workflow import fixture

    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    window.apply_installations(Installations((installation,), (), ()))
    window.mod_roots = list(scan.roots)
    window.display_scan(scan)
    for variable in window.vars.values():
        variable.set(True)
    window.selection_changed()

    def synchronous(action, receive, **kwargs):
        value = action()
        window._set_applying(False)
        receive(value)

    monkeypatch.setattr(window, "_background", synchronous)
    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(game, scan, selected, profile=profile),
    )
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: user)
    monkeypatch.setattr(
        "cc2_mce.gui.apply_plan",
        lambda plan, user: apply_plan(plan, user, game_running=lambda: False),
    )
    monkeypatch.setattr(
        "cc2_mce.gui.messagebox.askyesno",
        lambda *args, **kwargs: pytest.fail("No confirmation"),
    )
    deadline = time.monotonic() + 5
    while window.selection_dirty and time.monotonic() < deadline:
        window.update()
        time.sleep(0.01)
    assert window.active_package is not None
    assert str(window.active_package).encode() in (user / "mods.xml").read_bytes()
    assert not window.selection_dirty
    window.selection_changed()
    assert window.selection_dirty


@pytest.fixture
def auto_pair(window, tmp_path: Path, monkeypatch):
    from cc2_mce.discovery import discover
    from cc2_mce.workflow import analyze, apply_plan
    from tests.test_workflow import fixture

    installation, profile, user = fixture(tmp_path)
    window.apply_installations(Installations((installation,), (), ()))
    window.mod_roots = [tmp_path / "workshop"]
    window.display_scan(discover(window.mod_roots))
    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(game, scan, selected, profile=profile),
    )
    monkeypatch.setattr("cc2_mce.gui.game_user_dir", lambda: user)
    monkeypatch.setattr(
        "cc2_mce.gui.apply_plan",
        lambda plan, user: apply_plan(plan, user, game_running=lambda: False),
    )
    return window, user


def pump_until(window, condition):
    deadline = time.monotonic() + 8
    while not condition() and time.monotonic() < deadline:
        window.update()
        time.sleep(0.01)
    assert condition(), window.status.get()


def test_rapid_clicks_publish_only_latest_selection_and_last_uncheck_disables(auto_pair):
    window, user = auto_pair
    window.vars["a"].set(True)
    window.selection_changed()
    window.vars["b"].set(True)
    window.selection_changed()
    window.vars["a"].set(False)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    package = user / "mods/CC2-MCE"
    assert (package / "content/a.txt").read_bytes() == b"a=1\n\n\nb=2\n"
    window.vars["b"].set(False)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    from cc2_mce.workflow import active_paths

    assert active_paths(user) == ()
    assert "отключены" in window.status.get()


def test_conflicting_checkbox_keeps_working_package(auto_pair, tmp_path):
    window, user = auto_pair
    window.vars["a"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    package = user / "mods/CC2-MCE"
    old = (package / "mce-manifest.json").read_bytes()
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=1\n")
    window.vars["b"].set(True)
    window.selection_changed()
    pump_until(window, lambda: "Предыдущий набор сохранён" in window.status.get())
    assert not window.vars["b"].get(), "Rejected mod must return to unchecked"
    assert window.vars["a"].get()
    assert not window.selection_dirty, "The working set can still be launched"
    assert (package / "mce-manifest.json").read_bytes() == old
    assert (package / "content/a.txt").read_bytes() == b"a=2\n\n\nb=1\n"


def test_first_run_prepares_folders_without_button(window, tmp_path):
    root = game(tmp_path / "CC2")
    installed = inspect_game(root)
    assert installed is not None
    window.discover_on_start = True
    window.apply_installations(Installations((installed,), (), ()))
    pump_until(window, lambda: window.scan is not None)
    assert (root / "mods").is_dir()
    assert (root / "libraries").is_dir()
    assert not (root / "cc2x").exists()


def test_apply_failure_reverts_checkbox_and_keeps_launch_available(auto_pair, monkeypatch):
    from cc2_mce.errors import InputError

    window, _ = auto_pair
    window.vars["a"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)

    def fail(*args, **kwargs):
        raise InputError("Не удалось записать сборку")

    monkeypatch.setattr("cc2_mce.gui.apply_plan", fail)
    window.vars["b"].set(True)
    window.selection_changed()
    pump_until(window, lambda: "записать" in window.notice_text.get())
    assert window.vars["a"].get()
    assert not window.vars["b"].get()
    assert not window.selection_dirty
    assert window.launch_button.instate(["!disabled"])


def test_rejection_names_mods_and_allows_launching_working_set(auto_pair, tmp_path, monkeypatch):
    import cc2_mce.gui as gui

    window, user = auto_pair
    (tmp_path / "workshop/a/mod.xml").write_text('<data name="Working Mod"/>')
    (tmp_path / "workshop/b/mod.xml").write_text('<data name="New Mod"/>')
    window.checks["a"].invoke()
    pump_until(window, lambda: not window.selection_dirty)
    before = (user / "mods/CC2-MCE/mce-manifest.json").read_bytes()
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=1\n")
    window.checks["b"].invoke()
    assert window.launch_button.instate(["disabled"])
    pump_until(window, lambda: "New Mod" in window.notice_title.get())
    assert "Working Mod" in window.row_status["b"].get()
    assert "a.txt" in window.problem_details
    assert not window.vars["b"].get()
    assert window.launch_button.instate(["!disabled"])
    opened = []
    monkeypatch.setattr(gui.os, "startfile", opened.append, raising=False)
    monkeypatch.setattr(gui.webbrowser, "open", opened.append)
    window.launch_button.invoke()
    assert opened == ["steam://rungameid/1489630"]
    assert (user / "mods/CC2-MCE/mce-manifest.json").read_bytes() == before


def test_passive_scan_does_not_erase_rejection_or_retry_unchecked_mod(auto_pair, tmp_path):
    window, _ = auto_pair
    window.checks["a"].invoke()
    pump_until(window, lambda: not window.selection_dirty)
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=1\n")
    window.checks["b"].invoke()
    pump_until(window, lambda: bool(window.notice_title.get()))
    notice = window.notice_title.get(), window.notice_text.get()
    make_mod(tmp_path / "workshop", "c", {"c.txt": b"new unchecked mod"})
    window.scan_sources(preserve_selection=True)
    pump_until(window, lambda: "c" in window.vars and not window.busy)
    assert (window.notice_title.get(), window.notice_text.get()) == notice
    assert not window.vars["b"].get()
    assert not window.vars["c"].get()
    assert window._auto_timer is None


def test_required_dependency_explains_why_it_cannot_be_unchecked(auto_pair, tmp_path):
    window, _ = auto_pair
    (tmp_path / "workshop/b/mod.xml").write_text(
        '<data name="Dependent Mod"><cc2mce schema="1" type="mod">'
        '<requires id="a"/></cc2mce></data>'
    )
    window.checks["b"].invoke()
    pump_until(window, lambda: not window.selection_dirty)
    assert window.vars["a"].get()
    window.checks["a"].invoke()
    pump_until(window, lambda: not window.selection_dirty)
    assert window.vars["a"].get()
    assert "Dependent Mod" in window.row_status["a"].get()
    assert "нужна" in window.status.get()


def test_main_screen_has_only_launch_action_and_one_menu(window):
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    buttons = [child.cget("text") for child in descendants(window) if isinstance(child, ttk.Button)]
    assert buttons == ["Запустить игру"]
    labels = [
        window.actions_menu.entrycget(index, "label")
        for index in range(window.actions_menu.index("end") + 1)
        if window.actions_menu.type(index) == "command"
    ]
    assert "Сохранить отчёт…" in labels
    assert "Расположение файлов…" in labels
    assert not any("Подготов" in label for label in labels)


def test_first_run_refuses_file_in_place_of_collection(window, tmp_path):
    root = game(tmp_path / "CC2")
    (root / "libraries").write_bytes(b"user file must survive")
    installed = inspect_game(root)
    assert installed is not None
    window.discover_on_start = True
    window.apply_installations(Installations((installed,), (), ()))
    pump_until(window, lambda: "доступ" in window.status.get())
    assert (root / "libraries").read_bytes() == b"user file must survive"
    assert not (root / "mods").exists()
    assert window.scan is None
    assert window.launch_button.instate(["disabled"])


def test_order_change_rebuilds_automatically_and_is_persisted(auto_pair, tmp_path, monkeypatch):
    from cc2_mce.workflow import analyze

    window, user = auto_pair
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=2\n")
    installation = window.game
    assert installation is not None
    from cc2_mce.filesystem import digest

    profile = {
        "game_sha256": digest(installation.executable.read_bytes()),
        "native_plugins": {},
        "runtime_sha256": None,
        "baselines": {},
    }
    monkeypatch.setattr(
        "cc2_mce.gui.analyze",
        lambda game, scan, selected, **kwargs: analyze(
            game, scan, selected, profile=profile, patch_priority=True
        ),
    )
    window.checks["a"].invoke()
    window.checks["b"].invoke()
    pump_until(window, lambda: not window.selection_dirty)
    package = user / "mods/CC2-MCE"
    assert (package / "content/a.txt").read_bytes() == b"a=3\n\n\nb=2\n"
    assert "перезаписывают" in window.notice_title.get()
    assert "a.txt" in window.notice_text.get()
    assert "неизвестен" in window.notice_text.get()
    assert "Включён" in window.row_status["a"].get()
    assert window.launch_button.instate(["!disabled"])
    before_notice = window.notice_text.get()
    window.scan_sources(preserve_selection=True, rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy)
    assert window.notice_text.get() == before_notice
    # A newly opened window must also recover the active warning without rebuilding.
    window._applied_warning = None
    window._clear_notice()
    window.scan_sources(preserve_selection=False, rebuild_after_scan=False)
    pump_until(window, lambda: not window.busy)
    assert window.notice_text.get() == before_notice
    window.move_mod("b", 0)
    pump_until(window, lambda: not window.selection_dirty)
    assert window._applied_order == ["b", "a"]
    assert list(window.order_tree.get_children()) == ["b", "a"]
    assert (package / "content/a.txt").read_bytes() == b"a=2\n\n\nb=2\n"
    assert "a.txt" in window.notice_text.get()
    from cc2_mce.preferences import Preferences

    assert Preferences.load(window.preferences.root).order(installation.root)[:2] == ["b", "a"]
    window.checks["b"].invoke()
    pump_until(window, lambda: not window.selection_dirty)
    assert not window.notice_title.get(), "Removing the overlap must clear the warning"


def test_selected_tab_has_larger_padding(window):
    style = ttk.Style(window)
    selected = tuple(
        map(int, window.tk.splitlist(style.lookup("TNotebook.Tab", "padding", ("selected",))))
    )
    idle = tuple(
        map(int, window.tk.splitlist(style.lookup("TNotebook.Tab", "padding", ("!selected",))))
    )
    assert selected[1] > idle[1]


def test_running_game_defers_checkbox_until_game_closes(auto_pair, monkeypatch):
    window, user = auto_pair
    running = [True]
    monkeypatch.setattr("cc2_mce.gui._running", lambda: running[0])
    window.vars["a"].set(True)
    window.selection_changed()
    pump_until(window, lambda: "Закройте игру" in window.status.get())
    assert not (user / "mods").exists()
    running[0] = False
    pump_until(window, lambda: not window.selection_dirty)
    assert (user / "mods/CC2-MCE/content/a.txt").is_file()


def test_changed_source_rebuilds_without_losing_selection(auto_pair, tmp_path):
    window, user = auto_pair
    window.vars["a"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    (tmp_path / "workshop/a/content/a.txt").write_bytes(b"a=4\n\n\nb=1\n")
    window.scan_sources(preserve_selection=True)
    pump_until(
        window,
        lambda: (
            (user / "mods/CC2-MCE/content/a.txt").read_bytes() == b"a=4\n\n\nb=1\n"
            if not window.applying
            else False
        ),
    )
    assert window.vars["a"].get()
    assert not window.vars["b"].get()


def test_disappeared_selected_mod_can_be_unchecked(auto_pair, tmp_path):
    window, user = auto_pair
    window.vars["a"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    (tmp_path / "workshop/a").rename(tmp_path / "removed-a")
    window.scan_sources(preserve_selection=True)
    pump_until(
        window,
        lambda: (
            "a" in window.vars
            and any("не найден" in str(child.cget("text")) for child in window.checks.values())
        ),
    )
    assert window.vars["a"].get()
    window.vars["a"].set(False)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    from cc2_mce.workflow import active_paths

    assert active_paths(user) == ()


def test_late_analysis_cannot_publish_obsolete_selection(auto_pair, monkeypatch):
    import cc2_mce.gui as gui

    window, user = auto_pair
    original_analyze = gui.analyze
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def delayed(game, scan, selected, **kwargs):
        if selected == ["a"]:
            started.set()
            assert release.wait(8)
            value = original_analyze(game, scan, selected, **kwargs)
            finished.set()
            return value
        return original_analyze(game, scan, selected, **kwargs)

    monkeypatch.setattr(gui, "analyze", delayed)
    window.vars["a"].set(True)
    window.selection_changed()
    try:
        pump_until(window, started.is_set)
        window.vars["a"].set(False)
        window.vars["b"].set(True)
        window.selection_changed()
        pump_until(window, lambda: not window.selection_dirty)
        release.set()
        pump_until(window, finished.is_set)
        assert (user / "mods/CC2-MCE/content/a.txt").read_bytes() == b"a=1\n\n\nb=2\n"
    finally:
        release.set()


def test_undo_refreshes_checkboxes_without_reapplying(auto_pair, monkeypatch):
    from cc2_mce.workflow import restore_previous

    window, user = auto_pair
    monkeypatch.setattr("cc2_mce.gui.messagebox.askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "cc2_mce.gui.restore_previous",
        lambda user: restore_previous(user, game_running=lambda: False),
    )
    window.vars["a"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    window.vars["a"].set(False)
    window.vars["b"].set(True)
    window.selection_changed()
    pump_until(window, lambda: not window.selection_dirty)
    window.restore()
    pump_until(window, lambda: not window.busy and window.vars["a"].get())
    assert not window.vars["b"].get()
    assert window._auto_timer is None
    assert not (user / "cc2-mce/activation.json").exists()
    assert (user / "mods/CC2-MCE/content/a.txt").read_bytes() == b"a=2\n\n\nb=1\n"
