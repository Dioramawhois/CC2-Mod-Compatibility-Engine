from pathlib import Path
from unittest.mock import Mock

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.game_launch import launch_game
from cc2_mce.workflow import analyze, apply_plan
from tests.test_workflow import fixture


def prepared(tmp_path: Path):
    game, profile, user = fixture(tmp_path)
    plan = analyze(game, discover([tmp_path / "workshop"]), ["a"], profile=profile)
    package = apply_plan(plan, user, game_running=lambda: False)
    return game, user, package


def test_launches_selected_executable_with_game_working_directory(tmp_path: Path):
    game, user, package = prepared(tmp_path)
    spawn = Mock()
    launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_called_once_with([str(game.executable)], cwd=str(game.root), shell=False)


def test_other_active_mods_cannot_be_launched_alongside_managed_set(tmp_path: Path):
    game, user, package = prepared(tmp_path)
    (user / "mods.xml").write_text(
        f'<data><active_mod_folders><path value="{package}"/>'
        f'<path value="{tmp_path / "workshop/a"}"/></active_mod_folders></data>'
    )
    spawn = Mock()
    with pytest.raises(InputError):
        launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_not_called()


@pytest.mark.parametrize("change", ["game", "payload", "running"])
def test_changed_or_running_game_is_not_started(tmp_path: Path, change: str):
    game, user, package = prepared(tmp_path)
    if change == "game":
        game.executable.write_bytes(b"replaced game")
    elif change == "payload":
        (package / "content/a.txt").write_bytes(b"replaced output")
    spawn = Mock()
    with pytest.raises(InputError):
        launch_game(game, user, package, spawn=spawn, game_running=lambda: change == "running")
    spawn.assert_not_called()
