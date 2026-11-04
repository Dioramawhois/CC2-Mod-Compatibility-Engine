import json
from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.ui_feedback import explain_rejection
from cc2_mce.workflow import active_paths, analyze, apply_plan, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture

OLD_RUNTIME = b"MZ owned reviewed previous SDK fixture; never execute"
NEW_RUNTIME = b"MZ owned reviewed current SDK fixture; never execute"
UNREVIEWED_RUNTIME = b"MZ owned unreviewed source fixture; never execute"


def providers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import cc2_mce.workflow as workflow

    game, profile, user = fixture(tmp_path)
    source = tmp_path / "providers"
    sdk = make_mod(source, "workshop-sdk", {"dinput8.dll": OLD_RUNTIME})
    (sdk / "mod.xml").write_text(
        '<data name="CC2X SDK"><cc2mce schema="1" type="library" '
        'id="cc2x.runtime" sdk="cc2x" api="8"/></data>',
        encoding="utf-8",
    )
    island = make_mod(source, "island-airfields", {"island.txt": b"owned gameplay fixture\n"})
    (island / "mod.xml").write_text(
        '<data name="Island Airfields"><cc2mce schema="1" type="mod" '
        'id="island-airfields" sdk="cc2x" api="8">'
        '<requires id="cc2x.runtime"/></cc2mce></data>',
        encoding="utf-8",
    )
    runtime = game.root / "dinput8.dll"
    runtime.write_bytes(OLD_RUNTIME)
    bundled = tmp_path / "bundled-runtime"
    candidate = bundled / digest(NEW_RUNTIME) / "dinput8.dll"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(NEW_RUNTIME)
    monkeypatch.setattr(workflow, "RUNTIME_DATA", bundled)
    profile.update(
        runtime_sha256=digest(NEW_RUNTIME),
        previous_runtime_sha256=[digest(OLD_RUNTIME)],
        runtime_api=8,
    )
    return game, profile, user, source, sdk, runtime


def test_workshop_sdk_update_can_remove_gameplay_and_upgrade_reversibly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, profile, user, source, sdk, runtime = providers(tmp_path, monkeypatch)
    old_profile = {**profile, "runtime_sha256": digest(OLD_RUNTIME), "previous_runtime_sha256": []}
    previous = analyze(game, discover([source]), ["island-airfields"], profile=old_profile)
    assert not previous.blockers
    package = apply_plan(previous, user, game_running=lambda: False)
    original_activation = (user / "mods.xml").read_bytes()
    original_manifest = (package / "mce-manifest.json").read_bytes()
    assert (package / "content/island.txt").is_file()

    # Steam updates the shared provider; the player's next action is removing a mod.
    (sdk / "content/dinput8.dll").write_bytes(NEW_RUNTIME)
    updated = analyze(game, discover([source]), ["workshop-sdk"], profile=profile)
    assert not updated.blockers
    assert updated.report["runtime_inputs"] == {"workshop-sdk": digest(NEW_RUNTIME)}
    assert updated.report["runtime_sha256"] == digest(NEW_RUNTIME)
    assert apply_plan(updated, user, game_running=lambda: False) == package
    assert runtime.read_bytes() == NEW_RUNTIME
    assert not (package / "content/island.txt").exists()
    assert active_paths(user) == (package,)

    restore_previous(user, game_running=lambda: False)
    assert runtime.read_bytes() == OLD_RUNTIME
    assert (user / "mods.xml").read_bytes() == original_activation
    assert (package / "mce-manifest.json").read_bytes() == original_manifest
    assert (package / "content/island.txt").read_bytes() == b"owned gameplay fixture\n"
    assert (sdk / "content/dinput8.dll").read_bytes() == NEW_RUNTIME


def test_unreviewed_workshop_runtime_names_source_not_installed_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, profile, user, source, sdk, runtime = providers(tmp_path, monkeypatch)
    runtime.write_bytes(NEW_RUNTIME)
    (sdk / "content/dinput8.dll").write_bytes(UNREVIEWED_RUNTIME)
    activation = (user / "mods.xml").read_bytes()

    prepared = analyze(game, discover([source]), ["workshop-sdk"], profile=profile)
    assert any(item["code"] == "runtime_source_conflict" for item in prepared.blockers)
    assert not any(item["code"] == "runtime_conflict" for item in prepared.blockers)
    record = next(
        item for item in prepared.report["files"] if item["logical_path"] == "dinput8.dll"
    )
    assert record["status"] == "runtime_source_conflict"
    assert record["strategy"] == "blocked"
    assert record["source_sha256"] == {"workshop-sdk": digest(UNREVIEWED_RUNTIME)}
    assert record["output_sha256"] is None
    feedback = explain_rejection(
        prepared.report, {"workshop-sdk", "island-airfields"}, {"workshop-sdk"}
    )
    assert "workshop-sdk" in feedback.rows
    with pytest.raises(InputError):
        apply_plan(prepared, user, game_running=lambda: False)
    assert runtime.read_bytes() == NEW_RUNTIME
    assert (sdk / "content/dinput8.dll").read_bytes() == UNREVIEWED_RUNTIME
    assert (user / "mods.xml").read_bytes() == activation
    assert not (user / "cc2-mce/activation.json").exists()
    assert not (user / "cc2-mce/pending.json").exists()
    assert not (user / "mods").exists()


def test_unknown_installed_loader_stays_blocked_despite_current_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, profile, user, source, sdk, runtime = providers(tmp_path, monkeypatch)
    unknown = b"MZ user's different installed loader; never execute"
    runtime.write_bytes(unknown)
    (sdk / "content/dinput8.dll").write_bytes(NEW_RUNTIME)
    activation = (user / "mods.xml").read_bytes()

    prepared = analyze(game, discover([source]), ["workshop-sdk"], profile=profile)
    assert any(item["code"] == "runtime_conflict" for item in prepared.blockers)
    assert not any(item["code"] == "runtime_source_conflict" for item in prepared.blockers)
    with pytest.raises(InputError):
        apply_plan(prepared, user, game_running=lambda: False)
    assert runtime.read_bytes() == unknown
    assert (user / "mods.xml").read_bytes() == activation
    assert (sdk / "content/dinput8.dll").read_bytes() == NEW_RUNTIME
    assert not (user / "cc2-mce/activation.json").exists()
    assert not (user / "cc2-mce/pending.json").exists()
    assert not (user / "mods").exists()


def test_previous_workshop_runtime_does_not_downgrade_current_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, profile, user, source, sdk, runtime = providers(tmp_path, monkeypatch)
    runtime.write_bytes(NEW_RUNTIME)
    prepared = analyze(game, discover([source]), ["workshop-sdk"], profile=profile)
    assert not prepared.blockers
    assert prepared.report["runtime_inputs"] == {"workshop-sdk": digest(OLD_RUNTIME)}
    package = apply_plan(prepared, user, game_running=lambda: False)

    assert runtime.read_bytes() == NEW_RUNTIME
    assert (sdk / "content/dinput8.dll").read_bytes() == OLD_RUNTIME
    assert not (package / "content/dinput8.dll").exists()
    activation = json.loads((user / "cc2-mce/activation.json").read_text())
    assert activation["runtime_change"] is None
    assert activation["runtime_sha256"] == digest(NEW_RUNTIME)
