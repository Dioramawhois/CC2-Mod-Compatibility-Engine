"""Check curated runtime bytes/provenance without loading executable code."""

import json
import struct
from pathlib import Path

from cc2_mce.filesystem import digest
from tools.package_release import validate_runtime_provenance

ROOT = Path(__file__).parents[1] / "cc2_mce"


def test_client_candidate_runtime_matches_reviewed_profile_and_pe_architecture():
    profile = json.loads((ROOT / "profiles/windows-1.5.18-r2.json").read_text())
    assert profile["runtime_api"] == 8
    assert profile["runtime_lua_api"] == 2
    assert profile["runtime_framework_api"] == 1
    assert {"lua-mod-api-v2", "framework-c-api-v1"} <= set(profile["runtime_capabilities"])
    assert "ordered-module-bundles-v1" in profile["runtime_capabilities"]
    assert profile["runtime_review"]["stage"] == "client-candidate"
    assert not profile["runtime_review"]["multiplayer_verified"]
    folder = ROOT / "runtime_data" / profile["runtime_sha256"]
    # Carry one runtime: every bundled executable needs matching source/build inputs.
    assert {path.name for path in (ROOT / "runtime_data").iterdir() if path.is_dir()} == {
        profile["runtime_sha256"]
    }
    data = (folder / "dinput8.dll").read_bytes()
    assert digest(data) == profile["runtime_sha256"]
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[:2] == b"MZ" and data[pe : pe + 4] == b"PE\0\0"
    assert struct.unpack_from("<H", data, pe + 4)[0] == 0x14C
    assert struct.unpack_from("<H", data, pe + 22)[0] & 0x2000
    assert struct.unpack_from("<H", data, pe + 24)[0] == 0x10B
    provenance = json.loads((folder / "dinput8.build.json").read_text())
    assert provenance["artifact_sha256"] == profile["runtime_sha256"]
    assert provenance["api"] == 8
    assert (
        validate_runtime_provenance(folder, profile["runtime_review"], profile["runtime_sha256"])
        == provenance
    )
    snapshot = json.loads((folder / "SDK-RELEASE.json").read_text())
    assert snapshot["offline_verification"]["native_passed"] == 36
    assert snapshot["runtime_acceptance"]["game_runtime_tested"] is True
    assert snapshot["runtime_acceptance"]["candidate"] == "0.1.0-alpha.4 / alpha4-loop-01"
    lock = json.loads((ROOT.parent / "distribution/windows-runtime.json").read_text())
    assert lock["sha256"] == digest(data) and lock["bytes"] == len(data)
    assert "/" + profile["runtime_review"]["runtime_version"] + "/" in lock["url"]
    assert b"cc2x_query_framework_v1" in data
    assert "screen-extensions-v1" in profile["runtime_capabilities"]
    assert "screen-extensions-v1" in provenance["capabilities"]
    assert {"waypoint-origin-v1", "screen-source-edits-v1"} <= set(provenance["capabilities"])
    assert "screen-extension-offline-contract" in profile["runtime_review"]["verified_scope"]
    assert "full-gameplay" in profile["runtime_review"]["unverified_scope"]
    assert b"GNU GENERAL PUBLIC LICENSE" in (folder / "LICENSE").read_bytes()
    assert b"Lua" in (folder / "Lua-LICENSE.txt").read_bytes()
    assert (folder / "NOTICE.md").is_file()
    for library in ("libcxx", "libcxxabi", "libunwind"):
        assert b"LLVM" in (folder / (library + "-LICENSE.txt")).read_bytes()


def test_only_tested_native_bytes_receive_client_settings_defaults():
    profile = json.loads((ROOT / "profiles/windows-1.5.18-r2.json").read_text())
    expected = {
        "16666efca5b156b86fdeb4dede8fa3ed4c6989d1a67529b1a875dc4cd9a43de4": "modes.ini",
        "abda60ece8cdf595166ec63f9710719077168ae24b5790c4333059d0f6cd80f8": "frein.ini",
    }
    actual = {
        key: next(iter(value["config_defaults"]))
        for key, value in profile["native_plugins"].items()
        if value.get("config_defaults")
    }
    assert actual == expected
    assert profile["previous_runtime_sha256"] == [
        "2453ba5a368943812954902685211db497d30d3052939f91d826d0c4883280ba",
        "ce4fc1c883c70af6c40f5431003d17584e9b2becb502ac840d22f73be9d7a7f3",
        "ed27641315e3957e991bb5fb00de8481c4a5ba7432d48a2638dee1d939110ff0",
        "c741ed111cdb186463c01f6e9e189fb80ee15b43bc52e6bacdd92fe88ee95d12",
        "98ba9bfbc217767ecc5a30aaa3cd5de8d3d7de1f9e8a9164cd0e0e32a6bed085",
        "d83d509dbc0cc8b4f01db26c55bb428fc904186155a492d4f14411f09726f85e",
    ]
