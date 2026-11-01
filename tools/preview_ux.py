"""Developer-only synthetic conflict preview. Never touches the installed game/user config."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import cc2_mce.gui as gui
from cc2_mce.discovery import discover
from cc2_mce.installation import Installations
from cc2_mce.workflow import analyze, apply_plan
from tests.test_workflow import fixture

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="cc2-ux-preview-") as temporary:
    directory = Path(temporary)
    game, profile, user = fixture(directory)
    for key, name in [("a", "Навигация авианосца"), ("b", "Новый интерфейс")]:
        (directory / f"workshop/{key}/mod.xml").write_text(f'<data name="{name}"/>', encoding="utf-8")
    with patch.object(gui, "game_user_dir", lambda: user), patch.object(gui, "_running", lambda: False), \
         patch.object(gui, "analyze", lambda game, scan, chosen, **kwargs:
                      analyze(game, scan, chosen, profile=profile)), \
         patch.object(gui, "apply_plan", lambda plan, user:
                      apply_plan(plan, user, game_running=lambda: False)):
        app = gui.App(discover_on_start=False, patch_priority=False, language="ru")
        app.title("CC2 Engine — UX audit (synthetic)")
        app.apply_installations(Installations((game,), (), ()))
        app.mod_roots = [directory / "workshop"]
        app.display_scan(discover(app.mod_roots))
        app.checks["a"].invoke()

        def reject_new_mod():
            if app.selection_dirty:
                app.after(60, reject_new_mod)
                return
            (directory / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=1\n")
            app.checks["b"].invoke()
            app.after(60, record)

        def record():
            if not app.notice_title.get():
                app.after(60, record)
                return
            assert app.vars["a"].get() and not app.vars["b"].get()
            assert app.launch_button.instate(["!disabled"])
            (root / "build/ux-preview-ready.json").write_text(json.dumps({
                "scope": "synthetic source GUI; not game acceptance",
                "title": app.title(), "rejected_checkbox_off": True,
                "working_checkbox_on": True, "launch_available": True,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        app.after(60, reject_new_mod)
        app.after(60000, app.request_close)
        app.mainloop()
