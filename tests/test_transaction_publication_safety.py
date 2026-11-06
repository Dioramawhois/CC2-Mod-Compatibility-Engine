"""Fault injection against owned fixtures; DLL bytes and game processes stay inert."""

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.game_launch import launch_game
from cc2_mce.locking import activation_lock
from cc2_mce.workflow import analyze, apply_plan, recover_interrupted, restore_previous
from tests.test_post_commit_settings_cleanup import NEW_RUNTIME, OLD_RUNTIME, prepared_update
from tests.test_workflow import fixture


def _prepared(tmp_path: Path):
    game, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    package = apply_plan(
        analyze(game, scan, ["a"], profile=profile), user, game_running=lambda: False
    )
    return game, profile, user, scan, package


class _PartialWrite:
    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def write(self, content):
        self.stream.write(content[:32])
        self.stream.flush()
        raise OSError("Owned fixture: journal write interrupted")


@pytest.mark.parametrize("operation", ["apply", "undo"])
def test_partial_journal_write_preserves_working_set_and_leaves_no_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    game, profile, user, scan, package = _prepared(tmp_path)
    before_xml = (user / "mods.xml").read_bytes()
    before_manifest = (package / "mce-manifest.json").read_bytes()
    before_state = (user / "cc2-mce/activation.json").read_bytes()
    original_open = Path.open

    def fail_journal(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        if mode == "xb" and (path.name == "pending.json" or path.name.startswith(".pending.json.")):
            return _PartialWrite(stream)
        return stream

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", fail_journal)
        with pytest.raises(OSError, match="journal write interrupted"):
            if operation == "apply":
                apply_plan(
                    analyze(game, scan, ["b"], profile=profile),
                    user,
                    game_running=lambda: False,
                )
            else:
                restore_previous(user, game_running=lambda: False)

    assert (user / "mods.xml").read_bytes() == before_xml
    assert (package / "mce-manifest.json").read_bytes() == before_manifest
    assert (user / "cc2-mce/activation.json").read_bytes() == before_state
    assert not (user / "cc2-mce/pending.json").exists()
    assert not list((user / "cc2-mce").glob(".pending.json.*"))
    recover_interrupted(user, game_running=lambda: False)
    spawn = Mock()
    launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_called_once()


def test_pending_publication_failure_cleans_all_unpublished_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, user, package, plan, manifest, activation, _ = prepared_update(tmp_path)
    before = set((user / "cc2-mce").iterdir())
    original_link = workflow.os.link

    def denied(source, target):
        if Path(target).name == "pending.json":
            raise PermissionError("Owned fixture: pending publication denied")
        return original_link(source, target)

    monkeypatch.setattr(workflow.os, "link", denied)
    with pytest.raises(PermissionError, match="publication denied"):
        apply_plan(plan, user, game_running=lambda: False)
    assert (package / "mce-manifest.json").read_bytes() == manifest
    assert (user / "mods.xml").read_bytes() == activation
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert not list(game.root.glob(".cc2-mce-runtime-*.dll"))
    assert set((user / "cc2-mce").iterdir()) == before
    assert not (user / "cc2x/demo.ini").exists()


def test_prejournal_backup_failure_cleans_runtime_settings_and_package_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, user, package, plan, manifest, activation, _ = prepared_update(tmp_path)
    before = set((user / "cc2-mce").iterdir())
    original_write = workflow._write_new

    def denied(path, data):
        if path.parent == user / "cc2-mce" and path.name.startswith("mods-"):
            raise PermissionError("Owned fixture: activation backup denied")
        return original_write(path, data)

    monkeypatch.setattr(workflow, "_write_new", denied)
    with pytest.raises(PermissionError, match="backup denied"):
        apply_plan(plan, user, game_running=lambda: False)
    assert (package / "mce-manifest.json").read_bytes() == manifest
    assert (user / "mods.xml").read_bytes() == activation
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert not list(game.root.glob(".cc2-mce-runtime-*.dll"))
    assert set((user / "cc2-mce").iterdir()) == before
    assert not (user / "cc2x/demo.ini").exists()


def test_detected_game_start_defers_native_rollback_until_game_is_closed(
    tmp_path: Path,
) -> None:
    game, user, package, plan, manifest, activation, _ = prepared_update(tmp_path)
    runtime = game.root / "dinput8.dll"
    running_detected = False

    def running():
        nonlocal running_detected
        if runtime.read_bytes() == NEW_RUNTIME:
            running_detected = True
        return running_detected

    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=running)
    assert running_detected
    assert runtime.read_bytes() == NEW_RUNTIME
    assert (user / "cc2-mce/pending.json").exists()
    interrupted_manifest = (package / "mce-manifest.json").read_bytes()
    with pytest.raises(InputError):
        recover_interrupted(user, game_running=lambda: True)
    assert runtime.read_bytes() == NEW_RUNTIME
    assert (package / "mce-manifest.json").read_bytes() == interrupted_manifest
    recover_interrupted(user, game_running=lambda: False)
    assert runtime.read_bytes() == OLD_RUNTIME
    assert (package / "mce-manifest.json").read_bytes() == manifest
    assert (user / "mods.xml").read_bytes() == activation
    assert not (user / "cc2-mce/pending.json").exists()


def test_game_start_between_settings_and_runtime_install_defers_remaining_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, user, package, plan, manifest, _, _ = prepared_update(tmp_path)
    running = False
    install_settings = workflow.sdk_settings.install

    def started_after_settings(*args, **kwargs):
        nonlocal running
        install_settings(*args, **kwargs)
        running = True

    monkeypatch.setattr(workflow.sdk_settings, "install", started_after_settings)
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: running)
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert (user / "cc2x/demo.ini").exists()
    assert (user / "cc2-mce/pending.json").exists()
    recover_interrupted(user, game_running=lambda: False)
    assert (package / "mce-manifest.json").read_bytes() == manifest
    assert not (user / "cc2x/demo.ini").exists()


def test_partial_runtime_stage_write_cleans_every_unpublished_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, user, _, plan, _, _, _ = prepared_update(tmp_path)
    before = set((user / "cc2-mce").iterdir())
    original_open = Path.open

    def fail_runtime(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        if mode == "xb" and path.name.startswith(".cc2-mce-runtime-"):
            return _PartialWrite(stream)
        return stream

    monkeypatch.setattr(Path, "open", fail_runtime)
    with pytest.raises(OSError, match="write interrupted"):
        apply_plan(plan, user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert not list(game.root.glob(".cc2-mce-runtime-*.dll"))
    assert set((user / "cc2-mce").iterdir()) == before


def test_prejournal_cleanup_preserves_external_replacement_of_staged_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, user, _, plan, _, _, _ = prepared_update(tmp_path)
    original_write = workflow._write_new
    external = b"Owned different writer's staged file; never execute"
    replaced = []

    def replaced_before_return(path, data):
        if path.parent == user / "cc2-mce" and path.name.startswith("mods-"):
            raise PermissionError("Owned fixture: activation backup denied")
        identity = original_write(path, data)
        if path.name.startswith(".cc2-mce-runtime-"):
            replacement = game.root / "other-writer.tmp"
            replacement.write_bytes(external)
            workflow.os.replace(replacement, path)
            replaced.append(path)
        return identity

    monkeypatch.setattr(workflow, "_write_new", replaced_before_return)
    with pytest.raises(PermissionError, match="backup denied"):
        apply_plan(plan, user, game_running=lambda: False)
    assert len(replaced) == 1 and replaced[0].read_bytes() == external
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert not (user / "cc2-mce/pending.json").exists()


def test_interruption_immediately_after_journal_publication_preserves_recovery_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, user, package, plan, manifest, activation, _ = prepared_update(tmp_path)
    original_link = workflow.os.link

    def interrupted(source, target):
        original_link(source, target)
        if Path(target).name == "pending.json":
            raise KeyboardInterrupt("Owned interruption immediately after journal publication")

    with monkeypatch.context() as patch:
        patch.setattr(workflow.os, "link", interrupted)
        with pytest.raises(KeyboardInterrupt):
            apply_plan(plan, user, game_running=lambda: False)
    journal = json.loads((user / "cc2-mce/pending.json").read_bytes())
    assert (user / "cc2-mce" / journal["previous_state"]).exists()
    assert (game.root / journal["runtime_change"]["temporary"]).exists()
    recover_interrupted(user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == OLD_RUNTIME
    assert (package / "mce-manifest.json").read_bytes() == manifest
    assert (user / "mods.xml").read_bytes() == activation
    assert not (user / "cc2-mce/pending.json").exists()


def test_recovery_rechecks_closed_game_after_acquiring_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cc2_mce.workflow as workflow

    game, user, package, plan, _, _, _ = prepared_update(tmp_path)
    original_replace = workflow._replace_checked

    def interrupt(path, *args):
        if path == user / "mods.xml":
            raise KeyboardInterrupt("Owned interrupted transaction")
        return original_replace(path, *args)

    with monkeypatch.context() as patch:
        patch.setattr(workflow, "_replace_checked", interrupt)
        with pytest.raises(KeyboardInterrupt):
            apply_plan(plan, user, game_running=lambda: False)
    before = (package / "mce-manifest.json").read_bytes()
    running = False

    @contextmanager
    def started_before_lock_was_acquired(_user):
        nonlocal running
        running = True
        yield

    monkeypatch.setattr(workflow, "activation_lock", started_before_lock_was_acquired)
    with pytest.raises(InputError):
        recover_interrupted(user, game_running=lambda: running)
    assert (game.root / "dinput8.dll").read_bytes() == NEW_RUNTIME
    assert (package / "mce-manifest.json").read_bytes() == before
    assert (user / "cc2-mce/pending.json").exists()


def test_launch_refuses_pending_transaction_before_mock_spawn(tmp_path: Path) -> None:
    game, _, user, _, package = _prepared(tmp_path)
    (user / "cc2-mce/pending.json").write_text(json.dumps({"owner": "cc2-mce"}))
    spawn = Mock()
    with pytest.raises(InputError):
        launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_not_called()


def test_launch_shares_the_apply_lock_and_holds_it_through_spawn(tmp_path: Path) -> None:
    game, _, user, _, package = _prepared(tmp_path)
    spawn = Mock()
    with activation_lock(user), pytest.raises(InputError):
        launch_game(game, user, package, spawn=spawn, game_running=lambda: False)
    spawn.assert_not_called()

    def checked_spawn(*args, **kwargs):
        with pytest.raises(InputError):
            with activation_lock(user):
                pytest.fail("Launch must retain the transaction lock through spawning")

    launch_game(game, user, package, spawn=checked_spawn, game_running=lambda: False)
    with activation_lock(user):
        pass  # The shared lock is released after spawning.
