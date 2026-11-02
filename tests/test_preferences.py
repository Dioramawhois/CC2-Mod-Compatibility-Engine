from pathlib import Path

import pytest

from cc2_mce.errors import InputError
from cc2_mce.preferences import Preferences


def test_preferences_preserve_language_patch_mode_and_per_game_order(tmp_path: Path):
    prefs = Preferences.load(tmp_path / "settings")
    assert prefs.language == "system"
    assert prefs.patch_priority
    assert not prefs.launch_on_start
    assert not (tmp_path / "settings").exists()
    prefs.language = "en"
    prefs.set_order(tmp_path / "game", ["patch", "base"])
    prefs.patch_priority = False
    prefs.launch_on_start = True
    prefs.save()
    loaded = Preferences.load(tmp_path / "settings")
    assert loaded.language == "en"
    assert loaded.order(tmp_path / "game") == ["patch", "base"]
    assert not loaded.patch_priority
    assert loaded.launch_on_start
    assert list((tmp_path / "settings").iterdir()) == [tmp_path / "settings/preferences.json"]


def test_settings_do_not_overwrite_external_change(tmp_path: Path):
    prefs = Preferences.load(tmp_path / "settings")
    prefs.save()
    (tmp_path / "settings/preferences.json").write_bytes(b"user change")
    with pytest.raises(InputError):
        prefs.save()
    assert (tmp_path / "settings/preferences.json").read_bytes() == b"user change"


def test_old_preferences_default_to_no_automatic_launch_and_reject_wrong_type(tmp_path: Path):
    import json

    prefs = Preferences(tmp_path / "settings")
    prefs.save()
    path = prefs.root / "preferences.json"
    data = json.loads(path.read_text())
    data.pop("launch_on_start")
    path.write_text(json.dumps(data))
    assert not Preferences.load(prefs.root).launch_on_start
    data["launch_on_start"] = "false"
    path.write_text(json.dumps(data))
    with pytest.raises(InputError):
        Preferences.load(prefs.root)
