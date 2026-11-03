from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.workflow import analyze, apply_plan, recover_interrupted, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture

DEFAULT = b"[modes]\nenabled=1\n"


@pytest.fixture
def setup(tmp_path: Path):
    game, profile, user = fixture(tmp_path)
    runtime = b"synthetic reviewed runtime, never loaded"
    (game.root / "dinput8.dll").write_bytes(runtime)
    native = b"MZ synthetic reviewed plugin, never loaded"
    profile.update(
        runtime_sha256=digest(runtime),
        runtime_api=8,
        native_plugins={digest(native): {"config_defaults": {"modes.ini": DEFAULT.decode()}}},
    )
    source = tmp_path / "native-source"
    make_mod(source, "native", {"cc2x/plugin.dll": native})
    return game, profile, user, source


def plan(setup):
    game, profile, _, source = setup
    return analyze(game, discover([source]), ["native"], profile=profile)


def test_checkbox_apply_creates_reviewed_defaults_and_records_hashes(setup):
    _, _, user, _ = setup
    prepared = plan(setup)
    assert not prepared.blockers
    assert prepared.report["config_defaults"][0]["sha256"] == digest(DEFAULT)
    apply_plan(prepared, user, game_running=lambda: False)
    assert (user / "cc2x/modes.ini").read_bytes() == DEFAULT
    restore_previous(user, game_running=lambda: False)
    assert not (user / "cc2x/modes.ini").exists()


def test_existing_user_settings_are_preserved(setup):
    _, _, user, _ = setup
    (user / "cc2x").mkdir()
    existing = user / "cc2x/modes.ini"
    existing.write_bytes(b"[modes]\nenabled=0\n; personal settings\n")
    before = existing.read_bytes()
    apply_plan(plan(setup), user, game_running=lambda: False)
    assert existing.read_bytes() == before
    restore_previous(user, game_running=lambda: False)
    assert existing.read_bytes() == before


@pytest.mark.parametrize("failure", ["ordinary", "interruption"])
def test_failed_activation_rolls_back_created_settings(setup, monkeypatch, failure):
    import cc2_mce.workflow as workflow

    _, _, user, _ = setup
    before = (user / "mods.xml").read_bytes()
    real_replace = workflow._replace_checked

    def fail(path, *args):
        if path == user / "mods.xml":
            raise (
                OSError("simulated disk failure") if failure == "ordinary" else KeyboardInterrupt()
            )
        return real_replace(path, *args)

    with monkeypatch.context() as patch:
        patch.setattr(workflow, "_replace_checked", fail)
        with pytest.raises(OSError if failure == "ordinary" else KeyboardInterrupt):
            apply_plan(plan(setup), user, game_running=lambda: False)
    if failure == "interruption":
        assert (user / "cc2x/modes.ini").read_bytes() == DEFAULT
        recover_interrupted(user, game_running=lambda: False)
    assert not (user / "cc2x/modes.ini").exists()
    assert (user / "mods.xml").read_bytes() == before


def test_modified_created_settings_are_preserved_on_undo(setup):
    _, _, user, _ = setup
    apply_plan(plan(setup), user, game_running=lambda: False)
    target = user / "cc2x/modes.ini"
    target.write_bytes(b"[modes]\nenabled=1\neco_cap_light=0.7\n")
    changed = target.read_bytes()
    restore_previous(user, game_running=lambda: False)
    assert target.read_bytes() == changed


def test_missing_settings_are_repaired_even_when_package_is_unchanged(setup):
    _, _, user, _ = setup
    prepared = plan(setup)
    apply_plan(prepared, user, game_running=lambda: False)
    (user / "cc2x/modes.ini").unlink()
    apply_plan(plan(setup), user, game_running=lambda: False)
    assert (user / "cc2x/modes.ini").read_bytes() == DEFAULT


def test_same_bytes_created_by_another_writer_are_not_deleted(setup, monkeypatch):
    import cc2_mce.sdk_settings as settings

    _, _, user, _ = setup
    original = settings.os.link

    def external_writer(source, target, **kwargs):
        Path(target).write_bytes(DEFAULT)
        return original(source, target, **kwargs)

    monkeypatch.setattr(settings.os, "link", external_writer)
    with pytest.raises(OSError):
        apply_plan(plan(setup), user, game_running=lambda: False)
    assert (user / "cc2x/modes.ini").read_bytes() == DEFAULT


@pytest.mark.parametrize("filename", ["../escape.ini", "C:/escape.ini", "aux.ini", "x.dll"])
def test_profile_settings_cannot_escape_the_sdk_config_folder(setup, filename):
    _, profile, user, _ = setup
    approved = next(iter(profile["native_plugins"].values()))
    approved["config_defaults"] = {filename: "enabled=1\n"}
    with pytest.raises(InputError):
        apply_plan(plan(setup), user, game_running=lambda: False)
    assert not (user / "mods").exists()


def test_unreviewed_native_cannot_request_settings_by_metadata(setup):
    _, profile, user, _ = setup
    profile["native_plugins"] = {}
    prepared = plan(setup)
    assert prepared.blockers
    with pytest.raises(InputError):
        apply_plan(prepared, user, game_running=lambda: False)
    assert not (user / "cc2x").exists()


def test_deleted_runtime_is_reinstalled_even_when_payload_is_unchanged(setup):
    game, _, user, _ = setup
    prepared = plan(setup)
    original = (game.root / "dinput8.dll").read_bytes()
    library = game.libraries_dir / "runtime/content/dinput8.dll"
    library.parent.mkdir(parents=True)
    library.write_bytes(original)
    apply_plan(prepared, user, game_running=lambda: False)
    (game.root / "dinput8.dll").unlink()
    apply_plan(plan(setup), user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == original


def test_conflicting_reviewed_default_providers_block_the_set(setup):
    game, profile, _, source = setup
    other = b"MZ second synthetic native, never executed"
    make_mod(source, "other", {"cc2x/other.dll": other})
    profile["native_plugins"][digest(other)] = {
        "config_defaults": {"modes.ini": "[modes]\nenabled=0\n"}
    }
    prepared = analyze(game, discover([source]), ["native", "other"], profile=profile)
    assert any(b["code"] == "native_plugin_review_required" for b in prepared.blockers)
