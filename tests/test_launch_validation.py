from pathlib import Path
from unittest.mock import Mock

import pytest

from cc2_mce.errors import InputError
from cc2_mce.game_launch import validate_launch
from tests.test_game_launch import prepared


def test_readonly_launch_validation_never_creates_a_process(tmp_path: Path, monkeypatch):
    game, user, package = prepared(tmp_path)
    spawned = Mock(side_effect=AssertionError("Read-only validation must never spawn"))
    monkeypatch.setattr("cc2_mce.game_launch.subprocess.Popen", spawned)
    monkeypatch.setattr("cc2_mce.game_launch.launch_game", spawned)
    assert validate_launch(game, user, package, game_running=lambda: False) is None
    spawned.assert_not_called()


@pytest.mark.parametrize("changed", ["game", "payload", "activation", "running"])
def test_readonly_validation_preserves_all_existing_refusals(tmp_path: Path, monkeypatch, changed):
    game, user, package = prepared(tmp_path)
    spawned = Mock(side_effect=AssertionError("A refused validation must never spawn"))
    monkeypatch.setattr("cc2_mce.game_launch.subprocess.Popen", spawned)
    if changed == "game":
        game.executable.write_bytes(b"Owned changed executable")
    elif changed == "payload":
        (package / "content/a.txt").write_bytes(b"Owned changed payload")
    elif changed == "activation":
        (user / "mods.xml").write_text("<data><active_mod_folders/></data>", encoding="utf-8")
    with pytest.raises(InputError):
        validate_launch(game, user, package, game_running=lambda: changed == "running")
    spawned.assert_not_called()


def test_readonly_validation_rejects_external_runtime_without_overwriting_it(tmp_path: Path):
    from cc2_mce.discovery import discover
    from cc2_mce.filesystem import digest
    from cc2_mce.workflow import analyze, apply_plan
    from tests.test_paths_discovery import make_mod
    from tests.test_workflow import fixture

    game, profile, user = fixture(tmp_path)
    runtime = b"Owned reviewed runtime fixture; never executed"
    target = game.root / "dinput8.dll"
    target.write_bytes(runtime)
    profile.update(runtime_sha256=digest(runtime), runtime_api=8)
    make_mod(tmp_path / "sdk-source", "sdk", {"dinput8.dll": runtime})
    plan = analyze(game, discover([tmp_path / "sdk-source"]), ["sdk"], profile=profile)
    package = apply_plan(plan, user, game_running=lambda: False)
    target.write_bytes(b"Owned external runtime replacement")

    with pytest.raises(InputError, match="Installed runtime changed"):
        validate_launch(game, user, package, game_running=lambda: False)
    assert target.read_bytes() == b"Owned external runtime replacement"
