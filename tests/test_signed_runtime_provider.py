import base64
import json
import shutil
import struct

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cc2_mce import runtime_providers
from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.workflow import analyze, apply_plan, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_runtime_provider_sync import providers


def pe_bytes(label: bytes) -> bytes:
    data = bytearray(512)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", data, 0x84, 0x14C)
    struct.pack_into("<H", data, 0x96, 0x2000)
    struct.pack_into("<H", data, 0x98, 0x10B)
    data[256 : 256 + len(label)] = label
    return bytes(data)


@pytest.fixture
def signed_sdk(tmp_path, monkeypatch):
    game, profile, user, source, sdk, installed = providers(tmp_path, monkeypatch)
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(
        runtime_providers, "trusted_keys", lambda: {"fixture": key.public_key().public_bytes_raw()}
    )

    def update(sequence=1, data=None, **changes):
        data = (
            data
            if data is not None
            else pe_bytes(b"owned SDK fixture; never load: " + str(sequence).encode())
        )
        payload = {
            "publisher": "cc2x",
            "package_id": "cc2x.runtime",
            "sequence": sequence,
            "version": "0.11.0-dev",
            "game_sha256": profile["game_sha256"],
            "runtime_sha256": digest(data),
            "runtime_bytes": len(data),
            "api": 8,
            "lua_api": 2,
            "framework_api": 1,
            "capabilities": ["independent-lua-v1", "lua-mod-api-v2", "framework-c-api-v1"],
            "previous_runtime_sha256": profile["previous_runtime_sha256"],
            "source_commit": "a" * 40,
        }
        payload.update(changes)
        signature = key.sign(
            runtime_providers.SIGNING_DOMAIN + runtime_providers.canonical(payload)
        )
        envelope = {
            "schema": 1,
            "key_id": "fixture",
            "payload": payload,
            "signature": base64.b64encode(signature).decode(),
        }
        target = sdk / "content" / runtime_providers.DESCRIPTOR
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(envelope), encoding="utf-8")
        (sdk / "content/dinput8.dll").write_bytes(data)
        return data, target

    return game, profile, user, source, sdk, installed, update


def prepare(fixture):
    game, profile, user, source, *_ = fixture
    return analyze(game, discover([source]), ["workshop-sdk"], profile=profile, user_dir=user)


def test_future_signed_sdk_releases_upgrade_without_changing_the_executable(signed_sdk):
    game, profile, user, source, sdk, installed, update = signed_sdk
    original = installed.read_bytes()
    first, _ = update()
    assert digest(first) not in {profile["runtime_sha256"], *profile["previous_runtime_sha256"]}
    plan = prepare(signed_sdk)
    assert not plan.blockers
    assert plan.report["runtime_sha256"] == digest(first)
    assert runtime_providers.DESCRIPTOR not in plan.payload
    apply_plan(plan, user, game_running=lambda: False)
    assert installed.read_bytes() == first
    second, _ = update(2)
    plan = prepare(signed_sdk)
    assert not plan.blockers
    apply_plan(plan, user, game_running=lambda: False)
    assert installed.read_bytes() == second
    restore_previous(user, game_running=lambda: False)
    assert installed.read_bytes() == first
    assert original != first


def test_signed_provider_proof_remains_usable_when_source_is_unavailable(signed_sdk):
    game, profile, user, source, sdk, installed, update = signed_sdk
    data, _ = update()
    apply_plan(prepare(signed_sdk), user, game_running=lambda: False)
    scan = discover([source])
    from dataclasses import replace

    scan = replace(scan, mods=tuple(mod for mod in scan.mods if mod.id != "workshop-sdk"))
    plan = analyze(game, scan, ["island-airfields"], profile=profile, user_dir=user)
    assert not plan.blockers
    assert plan.report["runtime_sha256"] == digest(data)


@pytest.mark.parametrize(
    "damage", ["signature", "game", "hash", "bytes", "architecture", "missing"]
)
def test_invalid_signed_source_never_installs(signed_sdk, damage):
    game, profile, user, source, sdk, installed, update = signed_sdk
    original = installed.read_bytes()
    if damage == "game":
        _, descriptor = update(game_sha256="0" * 64)
    elif damage == "hash":
        _, descriptor = update(runtime_sha256="0" * 64)
    elif damage == "bytes":
        _, descriptor = update(runtime_bytes=100)
    elif damage == "architecture":
        data = bytearray(pe_bytes(b"owned PE64 header fixture"))
        struct.pack_into("<H", data, 0x84, 0x8664)
        _, descriptor = update(data=bytes(data))
    else:
        _, descriptor = update()
    if damage == "signature":
        value = json.loads(descriptor.read_text())
        value["payload"]["runtime_sha256"] = "0" * 64
        descriptor.write_text(json.dumps(value))
    elif damage == "missing":
        descriptor.unlink()
    plan = prepare(signed_sdk)
    assert plan.blockers
    assert installed.read_bytes() == original


def test_signed_sdk_cannot_replace_an_unknown_installed_loader(signed_sdk):
    *_, installed, update = signed_sdk
    update()
    installed.write_bytes(b"unrelated user's loader")
    plan = prepare(signed_sdk)
    assert any(item["code"] == "runtime_conflict" for item in plan.blockers)
    assert installed.read_bytes() == b"unrelated user's loader"


def test_signed_older_source_does_not_downgrade_installed_provider(signed_sdk):
    game, profile, user, source, sdk, installed, update = signed_sdk
    newer, _ = update(2)
    apply_plan(prepare(signed_sdk), user, game_running=lambda: False)
    update(1)
    plan = prepare(signed_sdk)
    assert not plan.blockers
    assert plan.report["runtime_sha256"] == digest(newer)


@pytest.mark.parametrize(
    "damage", ["unknown-key", "duplicate-json", "oversized", "boolean-sequence"]
)
def test_untrusted_or_ambiguous_metadata_is_rejected_before_use(signed_sdk, damage):
    game, profile, user, source, sdk, installed, update = signed_sdk
    _, descriptor = update()
    data = descriptor.read_bytes()
    if damage == "unknown-key":
        value = json.loads(data)
        value["key_id"] = "package-controlled-key"
        data = json.dumps(value).encode()
    elif damage == "duplicate-json":
        data = data.replace(b'"schema": 1', b'"schema": 1, "schema": 1')
    elif damage == "oversized":
        data += b" " * runtime_providers.MAX_MANIFEST
    else:
        value = json.loads(data)
        value["payload"]["sequence"] = True
        data = json.dumps(value).encode()
    with pytest.raises(InputError):
        runtime_providers.verify(data, profile["game_sha256"])


def test_source_race_leaves_installed_dll_and_activation_intact(signed_sdk):
    game, profile, user, source, sdk, installed, update = signed_sdk
    _, descriptor = update()
    plan = prepare(signed_sdk)
    old_runtime, old_xml = installed.read_bytes(), (user / "mods.xml").read_bytes()
    descriptor.write_bytes(descriptor.read_bytes() + b" ")
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)
    assert installed.read_bytes() == old_runtime
    assert (user / "mods.xml").read_bytes() == old_xml


def test_cache_publication_failure_cannot_commit_partial_activation(signed_sdk, monkeypatch):
    game, profile, user, source, sdk, installed, update = signed_sdk
    update()
    plan = prepare(signed_sdk)
    old_runtime, old_xml = installed.read_bytes(), (user / "mods.xml").read_bytes()

    def denied(*args):
        raise PermissionError("owned cache publication fixture")

    monkeypatch.setattr(runtime_providers.os, "link", denied)
    with pytest.raises(PermissionError):
        apply_plan(plan, user, game_running=lambda: False)
    assert installed.read_bytes() == old_runtime
    assert (user / "mods.xml").read_bytes() == old_xml
    assert not list((user / "cc2-mce/runtime-providers").glob("*"))


def test_signed_sdk_does_not_approve_an_arbitrary_plugin(signed_sdk):
    game, profile, user, source, sdk, installed, update = signed_sdk
    update()
    make_mod(
        source, "unreviewed-plugin", {"cc2x/plugins/unreviewed.dll": pe_bytes(b"untrusted plugin")}
    )
    plan = analyze(
        game,
        discover([source]),
        ["workshop-sdk", "unreviewed-plugin"],
        profile=profile,
        user_dir=user,
    )
    assert any(item["code"] == "native_plugin_review_required" for item in plan.blockers)


def test_official_update_can_replace_backend_of_an_older_selected_library(signed_sdk):
    game, profile, user, source, sdk, installed, update = signed_sdk
    newer, descriptor = update()
    downloaded = source / "official-downloaded-sdk"
    shutil.copytree(sdk, downloaded)
    (downloaded / "content/unselected-gameplay.lua").write_text('error("never enabled")')
    descriptor.unlink()
    (sdk / "content/dinput8.dll").write_bytes(installed.read_bytes())
    plan = prepare(signed_sdk)
    assert not plan.blockers
    assert plan.report["runtime_sha256"] == digest(newer)
    assert plan.report["runtime_provider_source"]["id"] == downloaded.name
    assert "unselected-gameplay.lua" not in plan.payload
    assert [mod.id for mod in plan.selected] == ["workshop-sdk"]
