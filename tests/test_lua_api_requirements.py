from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.workflow import analyze
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


def package(tmp_path: Path, value: str) -> Path:
    root = make_mod(tmp_path / "lua-packages", "lua-mod", {"example.txt": b"data"})
    (root / "mod.xml").write_text(
        '<data name="Lua mod"><cc2mce schema="1" type="mod" id="lua-mod" '
        f'sdk="cc2x" api="8" lua_api="{value}"/></data>',
        encoding="utf-8",
    )
    return root


def test_lua_requirement_is_reported_and_blocks_old_runtime(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    package(tmp_path, "2")
    scan = discover([tmp_path / "lua-packages"])
    assert scan.mods[0].lua_api == 2
    assert scan.mods[0].report()["lua_api"] == 2
    profile["runtime_api"] = 8
    plan = analyze(installation, scan, ["lua-mod"], profile=profile)
    assert any(b["code"] == "sdk_api" for b in plan.blockers)
    profile["runtime_capabilities"] = ["lua-mod-api-v2"]
    profile["runtime_lua_api"] = 2
    plan = analyze(installation, scan, ["lua-mod"], profile=profile)
    assert not any(b["code"] == "sdk_api" for b in plan.blockers)


@pytest.mark.parametrize("value", ["-1", "NaN", "2.0", "10001", "\u0662"])
def test_invalid_lua_api_is_rejected(tmp_path: Path, value: str) -> None:
    package(tmp_path, value)
    with pytest.raises(InputError):
        discover([tmp_path / "lua-packages"])
