"""Provider ordering and lifetime cache regressions; fixture DLLs are never loaded."""

import json
from pathlib import Path

import pytest

from cc2_mce import runtime_providers, workflow
from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.workflow import analyze, apply_plan, restore_previous
from tests.test_signed_runtime_provider import pe_bytes
from tests.test_signed_runtime_provider import signed_sdk as signed_sdk


def bundled_update(fixture, monkeypatch):
    game, profile, user, source, sdk, installed, update = fixture
    older, descriptor = update(1, version="0.10.0-dev")
    old_receipt = json.loads(descriptor.read_bytes())
    newer, _ = update(2, version="0.11.0-dev")
    receipt = json.loads(descriptor.read_bytes())
    payload = receipt["payload"]
    profile.update(
        runtime_sha256=digest(newer),
        runtime_api=payload["api"],
        runtime_lua_api=payload["lua_api"],
        runtime_framework_api=payload["framework_api"],
        runtime_capabilities=payload["capabilities"],
        previous_runtime_sha256=[*profile["previous_runtime_sha256"], digest(older)],
        runtime_review={
            "stage": "client-candidate",
            "runtime_version": payload["version"],
            "source_commit": payload["source_commit"],
            "verified_scope": ["owned-fixture"],
            "unverified_scope": ["gameplay"],
            "multiplayer_verified": False,
            "dedicated_verified": False,
        },
    )
    folder = workflow.RUNTIME_DATA / digest(newer)
    folder.mkdir()
    (folder / "dinput8.dll").write_bytes(newer)
    (folder / "runtime-update.json").write_bytes(runtime_providers.canonical(receipt))
    monkeypatch.setattr(runtime_providers, "RUNTIME_DATA", workflow.RUNTIME_DATA, raising=False)
    descriptor.write_bytes(runtime_providers.canonical(old_receipt))
    (sdk / "content/dinput8.dll").write_bytes(older)
    return older, newer, descriptor, old_receipt, receipt


@pytest.mark.parametrize("installed_older", [False, True])
def test_bundled_signed_sequence_prevents_older_source_or_cache_downgrade(
    signed_sdk, monkeypatch, installed_older
):
    game, profile, user, source, sdk, installed, _ = signed_sdk
    older, newer, descriptor, old_receipt, _ = bundled_update(signed_sdk, monkeypatch)
    installed.write_bytes(older if installed_older else newer)
    if installed_older:
        runtime_providers.remember(user, old_receipt, profile["game_sha256"])
        descriptor.unlink()
    plan = analyze(game, discover([source]), ["workshop-sdk"], profile=profile, user_dir=user)
    assert not plan.blockers
    assert plan.report["runtime_sha256"] == digest(newer)
    assert plan.report["runtime_review"] == profile["runtime_review"]
    apply_plan(plan, user, game_running=lambda: False)
    assert installed.read_bytes() == newer


def test_bundled_signed_identity_participates_in_sequence_ambiguity(signed_sdk, monkeypatch):
    game, profile, user, source, sdk, installed, update = signed_sdk
    older, newer, *_ = bundled_update(signed_sdk, monkeypatch)
    installed.write_bytes(newer)
    update(2, data=older, version="0.10.0-dev")
    with pytest.raises(InputError, match="Ambiguous signed SDK release sequence"):
        runtime_providers.select(game.root, discover([source]).mods, profile, user)
    assert installed.read_bytes() == newer


@pytest.mark.parametrize("damage", ["runtime-hash", "api", "capabilities"])
def test_bundled_receipt_must_agree_with_the_reviewed_profile(signed_sdk, monkeypatch, damage):
    game, profile, user, source, sdk, installed, _ = signed_sdk
    older, newer, _, old_receipt, _ = bundled_update(signed_sdk, monkeypatch)
    if damage == "runtime-hash":
        proof = workflow.RUNTIME_DATA / digest(newer) / "runtime-update.json"
        proof.write_bytes(runtime_providers.canonical(old_receipt))
    elif damage == "api":
        profile["runtime_api"] += 1
    else:
        profile["runtime_capabilities"] = []
    with pytest.raises(InputError, match="profile"):
        runtime_providers.select(game.root, (), profile, user)


def test_more_than_256_cached_releases_preserve_installed_and_undo_proofs(signed_sdk, monkeypatch):
    game, profile, user, source, sdk, installed, update = signed_sdk
    first = second = b""
    for sequence in range(1, 258):
        data, descriptor = update(sequence)
        runtime_providers.remember(
            user, json.loads(descriptor.read_bytes()), profile["game_sha256"]
        )
        if sequence == 1:
            first = data
        elif sequence == 257:
            second = data

    def no_enumeration(*args):
        raise AssertionError("Indexed runtime approval must not enumerate lifetime history")

    monkeypatch.setattr(runtime_providers, "bounded_children", no_enumeration)
    installed.write_bytes(first)
    plan = analyze(game, discover([source]), ["workshop-sdk"], profile=profile, user_dir=user)
    assert not plan.blockers
    apply_plan(plan, user, game_running=lambda: False)
    assert installed.read_bytes() == second
    restore_previous(user, game_running=lambda: False)
    assert installed.read_bytes() == first
    descriptor.unlink()
    (sdk / "content/dinput8.dll").write_bytes(first)
    restored = analyze(game, discover([source]), ["workshop-sdk"], profile=profile, user_dir=user)
    assert not restored.blockers
    assert restored.report["runtime_sha256"] == digest(first)


def test_legacy_cache_over_256_entries_finds_the_installed_receipt(signed_sdk):
    game, profile, user, source, sdk, installed, update = signed_sdk
    cache = user / "cc2-mce/runtime-providers"
    cache.mkdir(parents=True)
    expected = b""
    descriptor = Path()
    for sequence in range(1, 258):
        expected, descriptor = update(sequence)
        data = runtime_providers.canonical(json.loads(descriptor.read_bytes()))
        (cache / (digest(data) + ".json")).write_bytes(data)
    installed.write_bytes(expected)
    descriptor.unlink()
    (sdk / "content/dinput8.dll").write_bytes(expected)
    plan = analyze(game, discover([source]), ["workshop-sdk"], profile=profile, user_dir=user)
    assert not plan.blockers
    assert plan.report["runtime_sha256"] == digest(expected)


def test_unrelated_cache_entries_cannot_reject_an_empty_selection(signed_sdk):
    game, profile, user, source, sdk, installed, _ = signed_sdk
    cache = user / "cc2-mce/runtime-providers"
    cache.mkdir(parents=True)
    for number in range(257):
        (cache / f"unrelated-{number}.tmp").write_bytes(b"")
    plan = analyze(game, discover([source]), [], profile=profile, user_dir=user)
    assert not plan.blockers
    assert plan.report["runtime_sha256"] is None


@pytest.mark.parametrize("damage", ["runtime", "signature", "game"])
def test_runtime_index_cannot_substitute_a_different_or_unverified_receipt(signed_sdk, damage):
    game, profile, user, source, sdk, installed, update = signed_sdk
    first, descriptor = update()
    receipt = json.loads(descriptor.read_bytes())
    runtime_providers.remember(user, receipt, profile["game_sha256"])
    cache = user / "cc2-mce/runtime-providers"
    (cache / (digest(runtime_providers.canonical(receipt)) + ".json")).unlink()
    if damage == "runtime":
        update(2)
        invalid = json.loads(descriptor.read_bytes())
    elif damage == "game":
        update(2, data=first, game_sha256="0" * 64)
        invalid = json.loads(descriptor.read_bytes())
    else:
        invalid = receipt
        invalid["signature"] = "A" * 88
    index = cache / "by-runtime-v1" / profile["game_sha256"] / (digest(first) + ".json")
    index.write_bytes(runtime_providers.canonical(invalid))
    descriptor.unlink()
    (sdk / "content/dinput8.dll").write_bytes(first)
    installed.write_bytes(first)
    plan = analyze(game, discover([source]), ["workshop-sdk"], profile=profile, user_dir=user)
    assert any(item["code"] == "runtime_conflict" for item in plan.blockers)
    assert installed.read_bytes() == first


def test_sequence_index_rejects_a_cached_release_fork_without_scanning_history(
    signed_sdk, monkeypatch
):
    game, profile, user, source, sdk, installed, update = signed_sdk
    _, descriptor = update()
    receipt = json.loads(descriptor.read_bytes())
    runtime_providers.remember(user, receipt, profile["game_sha256"])
    update(1, data=pe_bytes(b"owned conflicting signed provider fixture"))

    def no_enumeration(*args):
        raise AssertionError("Sequence identity must be checked through its exact index")

    monkeypatch.setattr(runtime_providers, "bounded_children", no_enumeration)
    with pytest.raises(InputError, match="Ambiguous signed SDK release sequence"):
        runtime_providers.select(game.root, (), profile, user, available=discover([source]).mods)
