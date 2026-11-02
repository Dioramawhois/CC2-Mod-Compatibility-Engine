import ast
from pathlib import Path

from cc2_mce.i18n import Translator, language_for_locale
from cc2_mce.translations import EN
from cc2_mce.ui_feedback import explain_rejection
from tests.test_ui_feedback import report


def test_system_locale_selection_and_fallback():
    assert language_for_locale("ru_RU.UTF-8") == "ru"
    assert language_for_locale("ru-RU") == "ru"
    assert language_for_locale("en_US") == "en"
    assert language_for_locale("de_DE") == "de"
    assert language_for_locale("pt_BR") == "pt"
    assert language_for_locale("zh_CN") == "zh"
    assert language_for_locale("zh_Hant_TW") == "zh-TW"
    assert language_for_locale("ja_JP") == "ja"
    assert language_for_locale("unknown") == "en"
    assert language_for_locale(None) == "en"


def test_english_messages_preserve_names_paths_and_values():
    tr = Translator("en")
    assert tr("Запустить игру") == "Launch game"
    assert tr("Готово. Замен по порядку: {p0}.", p0=3) == "Ready. Replacements by load order: 3."
    assert tr("Не найдена зависимость: автор.библиотека") == "Missing dependency: автор.библиотека"
    feedback = explain_rejection(report(), {"a"}, {"a", "b"}, translate=tr)
    assert "Could not enable" in feedback.title
    assert "Working Mod" in feedback.rows["b"]
    assert "File: scripts/common.lua" in feedback.details


def test_all_gui_message_ids_are_in_english_catalog():
    root = Path(__file__).resolve().parents[1] / "cc2_mce"
    messages = set()
    for filename in ("gui.py", "ui_feedback.py"):
        for node in ast.walk(ast.parse((root / filename).read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and node.args
                and (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "tr"
                    or isinstance(node.func, ast.Name)
                    and node.func.id == "tr"
                )
                and isinstance(node.args[0], ast.Constant)
            ):
                messages.add(node.args[0].value)
    assert messages <= set(EN)


def test_gui_uses_system_language_and_remembers_explicit_choice(tmp_path, monkeypatch):
    import gc
    import tkinter as tk

    import pytest

    from cc2_mce.gui import App
    from cc2_mce.preferences import Preferences

    monkeypatch.setattr("cc2_mce.i18n.system_language", lambda: "en")
    prefs = tmp_path / "prefs"
    try:
        app = App(discover_on_start=False, preferences_dir=prefs)
    except tk.TclError:
        pytest.skip("GUI display unavailable")
    app.withdraw()
    assert app.language_choice == "system"
    assert app.launch_button.cget("text") == "Launch game"
    app.language_var.set("ru")
    app.change_language()
    assert app.restart_requested
    assert Preferences.load(prefs).language == "ru"
    restored = App(discover_on_start=False, preferences_dir=prefs)
    restored.withdraw()
    assert restored.launch_button.cget("text") == "Запустить игру"
    restored.destroy()
    gc.collect()


def test_language_pack_has_complete_keys_and_preserves_placeholders():
    import re

    from cc2_mce.i18n import LANGUAGES
    from cc2_mce.language_packs import PACKS

    assert set(PACKS) == set(LANGUAGES) - {"ru", "en"}
    for language, catalog in PACKS.items():
        assert set(catalog) == set(EN), language
        for key, translated in catalog.items():
            assert translated.strip(), (language, key)
            assert set(re.findall(r"\{p\d+\}", translated)) == set(re.findall(r"\{p\d+\}", EN[key]))
        assert Translator(language)("Запустить игру") != EN["Запустить игру"]
