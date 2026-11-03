from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.workflow import analyze, apply_plan, recover_interrupted, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture

OLD = b"reviewed old runtime; never executed"
NEW = b"reviewed new runtime; never executed"


@pytest.fixture
def setup(tmp_path: Path):
    game, profile, user = fixture(tmp_path)
    (game.root / "dinput8.dll").write_bytes(OLD)
    library = game.libraries_dir / "new/content/dinput8.dll"
    library.parent.mkdir(parents=True)
    library.write_bytes(NEW)
    profile.update(
        runtime_sha256=digest(NEW),
        previous_runtime_sha256=[digest(OLD)],
        runtime_api=8,
    )
    source = tmp_path / "source"
    mod = make_mod(source, "app", {"a.txt": b"changed\n"})
    (mod / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="mod" sdk="cc2x" api="8">'
        '<requires id="cc2x.runtime"/></cc2mce></data>'
    )
    return game, profile, user, source


def plan(setup):
    game, profile, _, source = setup
    return analyze(game, discover([source]), ["app"], profile=profile)


def test_known_runtime_upgrade_and_undo_restore_original(setup):
    game, _, user, _ = setup
    prepared = plan(setup)
    assert not prepared.blockers
    assert [m.id for m in prepared.selected] == ["app"]
    apply_plan(prepared, user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == NEW
    restore_previous(user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == OLD


@pytest.mark.parametrize("failure", ["ordinary", "interruption"])
@pytest.mark.parametrize("existing", [True, False])
def test_runtime_rolls_back_after_failure_or_crash(setup, monkeypatch, failure, existing):
    import cc2_mce.workflow as workflow

    game, _, user, _ = setup
    target = game.root / "dinput8.dll"
    if not existing:
        target.unlink()
    before = (user / "mods.xml").read_bytes()
    real_replace = workflow._replace_checked

    def fail(path, *args):
        if path == user / "mods.xml":
            raise OSError("disk failure") if failure == "ordinary" else KeyboardInterrupt()
        return real_replace(path, *args)

    with monkeypatch.context() as patch:
        patch.setattr(workflow, "_replace_checked", fail)
        with pytest.raises(OSError if failure == "ordinary" else KeyboardInterrupt):
            apply_plan(plan(setup), user, game_running=lambda: False)
    if failure == "interruption":
        assert target.read_bytes() == NEW
        recover_interrupted(user, game_running=lambda: False)
    assert target.read_bytes() == OLD if existing else not target.exists()
    assert (user / "mods.xml").read_bytes() == before


def test_unknown_runtime_is_never_overwritten(setup):
    game, _, user, _ = setup
    target = game.root / "dinput8.dll"
    target.write_bytes(b"unknown user's loader")
    with pytest.raises(InputError):
        apply_plan(plan(setup), user, game_running=lambda: False)
    assert target.read_bytes() == b"unknown user's loader"
    assert not (user / "cc2-mce").exists()


def test_undo_preserves_external_runtime_and_recovery_journal(setup):
    game, _, user, _ = setup
    apply_plan(plan(setup), user, game_running=lambda: False)
    (game.root / "dinput8.dll").write_bytes(b"external replacement")
    with pytest.raises(InputError):
        restore_previous(user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == b"external replacement"
    assert (user / "cc2-mce/pending.json").exists()


def test_old_library_runtime_is_recorded_but_not_copied(setup):
    game, profile, user, source = setup
    wrapper = make_mod(source, "old-sdk", {"dinput8.dll": OLD})
    (wrapper / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="library" id="cc2x.runtime" sdk="cc2x" api="4"/></data>'
    )
    prepared = analyze(game, discover([source]), ["app"], profile=profile)
    assert not prepared.blockers
    assert prepared.report["runtime_inputs"] == {"old-sdk": digest(OLD)}
    apply_plan(prepared, user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == NEW
    assert (wrapper / "content/dinput8.dll").read_bytes() == OLD


def test_changed_game_blocks_runtime_restoration(setup):
    game, _, user, _ = setup
    apply_plan(plan(setup), user, game_running=lambda: False)
    game.executable.write_bytes(b"updated game executable")
    with pytest.raises(InputError):
        restore_previous(user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == NEW


def test_bundled_exact_runtime_satisfies_missing_workshop_dependency(setup, monkeypatch, tmp_path):
    import cc2_mce.workflow as workflow

    game, _, user, _ = setup
    (game.libraries_dir / "new/content/dinput8.dll").unlink()
    bundled = tmp_path / "application-runtime"
    candidate = bundled / digest(NEW) / "dinput8.dll"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(NEW)
    monkeypatch.setattr(workflow, "RUNTIME_DATA", bundled)
    apply_plan(plan(setup), user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == NEW


def test_corrupt_bundled_runtime_cannot_be_used(setup, monkeypatch, tmp_path):
    import cc2_mce.workflow as workflow

    game, _, user, _ = setup
    (game.libraries_dir / "new/content/dinput8.dll").unlink()
    bundled = tmp_path / "application-runtime"
    candidate = bundled / digest(NEW) / "dinput8.dll"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"corrupted")
    monkeypatch.setattr(workflow, "RUNTIME_DATA", bundled)
    with pytest.raises(InputError):
        apply_plan(plan(setup), user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == OLD


def test_no_new_runtime_does_not_satisfy_dependency(setup):
    game, _, _, _ = setup
    (game.libraries_dir / "new/content/dinput8.dll").unlink()
    with pytest.raises(InputError, match="cc2x.runtime"):
        plan(setup)


def test_same_bytes_external_replacement_is_preserved_on_undo(setup):
    import os

    game, _, user, _ = setup
    apply_plan(plan(setup), user, game_running=lambda: False)
    external = game.root / "external-runtime.dll"
    external.write_bytes(NEW)
    os.replace(external, game.root / "dinput8.dll")
    with pytest.raises(InputError):
        restore_previous(user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == NEW


def test_unlisted_old_library_runtime_stays_blocked(setup):
    game, profile, _, source = setup
    make_mod(source, "unreviewed", {"dinput8.dll": b"unreviewed source runtime"})
    prepared = analyze(game, discover([source]), ["app", "unreviewed"], profile=profile)
    assert any(b["code"] == "runtime_conflict" for b in prepared.blockers)
