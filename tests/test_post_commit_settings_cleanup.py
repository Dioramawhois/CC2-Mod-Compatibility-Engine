import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.game_launch import launch_game
from cc2_mce.workflow import active_paths, analyze, apply_plan, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture

OLD_RUNTIME = b"MZ previous reviewed runtime fixture; never executed"
NEW_RUNTIME = b"MZ current reviewed runtime fixture; never executed"
PLUGIN = b"MZ reviewed native fixture; never executed"
DEFAULT = b"[demo]\nenabled=1\n"


def prepared_update(tmp_path: Path):
    game, profile, user = fixture(tmp_path)
    runtime = game.root / "dinput8.dll"
    runtime.write_bytes(OLD_RUNTIME)
    provider = game.libraries_dir / "current/content/dinput8.dll"
    provider.parent.mkdir(parents=True)
    provider.write_bytes(NEW_RUNTIME)
    profile.update(
        runtime_sha256=digest(NEW_RUNTIME),
        previous_runtime_sha256=[digest(OLD_RUNTIME)],
        runtime_api=8,
        native_plugins={digest(PLUGIN): {"config_defaults": {"demo.ini": DEFAULT.decode()}}},
    )
    source = make_mod(tmp_path / "workshop", "native", {"cc2x/plugin.dll": PLUGIN})
    scan = discover([tmp_path / "workshop"])
    previous = analyze(game, scan, ["a"], profile=profile)
    package = apply_plan(previous, user, game_running=lambda: False)
    old_manifest = (package / "mce-manifest.json").read_bytes()
    old_activation = (user / "mods.xml").read_bytes()
    updated = analyze(game, scan, ["a", "native"], profile=profile)
    assert not updated.blockers
    return game, user, package, updated, old_manifest, old_activation, source


def test_post_commit_cache_unlink_failure_reports_success_and_keeps_undo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, user, package, updated, old_manifest, old_activation, source = prepared_update(tmp_path)
    original_unlink = Path.unlink
    attempted: list[Path] = []

    def deny_own_cache_unlink(path: Path, *args, **kwargs):
        if path.parent == user / "cc2-mce" and path.name.startswith("config-"):
            # The fault is after the commit, never an activation or native-file write.
            assert not (user / "cc2-mce/pending.json").exists()
            assert json.loads((package / "mce-manifest.json").read_text())["mod_order"] == [
                "a",
                "native",
            ]
            assert (game.root / "dinput8.dll").read_bytes() == NEW_RUNTIME
            attempted.append(path)
            raise PermissionError("Owned cache unlink is temporarily denied")
        return original_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", deny_own_cache_unlink)
        assert apply_plan(updated, user, game_running=lambda: False) == package

    assert len(attempted) == 1
    assert attempted[0].read_bytes() == DEFAULT
    assert (user / "cc2x/demo.ini").read_bytes() == DEFAULT
    assert (package / "content/cc2x/plugin.dll").read_bytes() == PLUGIN
    assert (source / "content/cc2x/plugin.dll").read_bytes() == PLUGIN
    assert active_paths(user) == (package,)
    assert not (user / "cc2-mce/pending.json").exists()
    journal = json.loads((user / "cc2-mce/activation.json").read_text())
    assert journal["mod_order"] == ["a", "native"]
    assert journal["build_id"] == updated.report["build_id"]

    spawn = Mock()
    launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_called_once_with([str(game.executable)], cwd=str(game.root), shell=False)

    restore_previous(user, game_running=lambda: False)
    assert (package / "mce-manifest.json").read_bytes() == old_manifest
    assert (user / "mods.xml").read_bytes() == old_activation
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert not (user / "cc2x/demo.ini").exists()
    assert not attempted[0].exists()
    assert not (user / "cc2-mce/pending.json").exists()


def test_pre_commit_activation_failure_still_raises_and_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, user, package, updated, old_manifest, old_activation, source = prepared_update(tmp_path)
    original_replace = workflow._replace_checked

    def deny_activation_write(path: Path, *args):
        if path == user / "mods.xml":
            assert (user / "cc2-mce/pending.json").exists()
            raise PermissionError("Activation write denied before commit")
        return original_replace(path, *args)

    monkeypatch.setattr(workflow, "_replace_checked", deny_activation_write)
    with pytest.raises(PermissionError, match="before commit"):
        apply_plan(updated, user, game_running=lambda: False)

    assert (package / "mce-manifest.json").read_bytes() == old_manifest
    assert (user / "mods.xml").read_bytes() == old_activation
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert not (user / "cc2x/demo.ini").exists()
    assert not (user / "cc2-mce/pending.json").exists()
    assert (source / "content/cc2x/plugin.dll").read_bytes() == PLUGIN


def test_unknown_installed_loader_is_not_treated_as_optional_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, user, package, updated, old_manifest, old_activation, source = prepared_update(tmp_path)
    unknown = b"MZ external unreviewed loader; never executed"
    (game.root / "dinput8.dll").write_bytes(unknown)
    with pytest.raises(InputError):
        apply_plan(updated, user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == unknown
    assert (package / "mce-manifest.json").read_bytes() == old_manifest
    assert (user / "mods.xml").read_bytes() == old_activation
    assert not (user / "cc2x/demo.ini").exists()
    assert not (user / "cc2-mce/pending.json").exists()
    assert (source / "content/cc2x/plugin.dll").read_bytes() == PLUGIN
