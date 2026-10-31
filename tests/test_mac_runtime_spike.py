from __future__ import annotations

import hashlib
import os
import struct
from pathlib import Path

import pytest

from experiments.mac_runtime import launch


def test_launcher_refuses_unknown_game_before_spawning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = tmp_path / "build_mac"
    game.write_bytes(b"not the supported Carrier Command 2 build")
    runtime = tmp_path / "bridge.dylib"
    runtime.write_bytes(struct.pack("<II", launch.MACHO_64_MAGIC, launch.CPU_TYPE_X86_64))
    monkeypatch.setattr(launch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        launch.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("unsupported game must not launch"),
    )

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        launch.run(game, runtime, tmp_path / "probe.log", probe_seconds=1, self_test=True)
    assert not (tmp_path / "probe.log").exists()


def test_launcher_refuses_wrong_runtime_architecture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = tmp_path / "build_mac"
    game.write_bytes(b"fixture game executable")
    runtime = tmp_path / "bridge.dylib"
    runtime.write_bytes(struct.pack("<II", launch.MACHO_64_MAGIC, 0x0100000C))
    monkeypatch.setattr(launch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        launch, "SUPPORTED_GAME_SHA256", {hashlib.sha256(game.read_bytes()).hexdigest(): "fixture"}
    )

    with pytest.raises(ValueError, match="thin x86_64"):
        launch.verify_inputs(game, runtime)


def test_injection_environment_is_child_only_and_rejects_existing_injector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DYLD_INSERT_LIBRARIES", raising=False)
    runtime = tmp_path / "bridge.dylib"
    log = tmp_path / "bridge.log"
    child = launch.child_environment(runtime, log, self_test=True)

    assert child["DYLD_INSERT_LIBRARIES"] == str(runtime)
    assert child["CC2X_MAC_LOG_PATH"] == str(log)
    assert child["CC2X_MAC_SELFTEST"] == "1"
    assert "DYLD_INSERT_LIBRARIES" not in os.environ

    monkeypatch.setenv("DYLD_INSERT_LIBRARIES", "/another/injector.dylib")
    with pytest.raises(ValueError, match="stack injectors"):
        launch.child_environment(runtime, log, self_test=False)


def test_game_fingerprint_is_shared_by_python_and_native_bridge() -> None:
    source = (Path(__file__).parents[1] / "experiments/mac_runtime/mac_bridge.c").read_text()
    for sha256 in launch.SUPPORTED_GAME_SHA256:
        assert sha256 in source


def test_probe_requires_lua_success_for_every_registered_state(tmp_path: Path) -> None:
    log = tmp_path / "bridge.log"
    log.write_text(
        "Lua hook installed\n"
        "lua table registered before script compilation state=one\n"
        "lua selftest state=one result=PASS\n"
        "lua table registered before script compilation state=two\n"
    )
    assert not launch.probe_log_ok(log, self_test=True)

    with log.open("a") as output:
        output.write("lua selftest state=two result=PASS\n")
    assert launch.probe_log_ok(log, self_test=True)

    with log.open("a") as output:
        output.write("lua selftest state=three result=FAIL\n")
    assert not launch.probe_log_ok(log, self_test=True)
