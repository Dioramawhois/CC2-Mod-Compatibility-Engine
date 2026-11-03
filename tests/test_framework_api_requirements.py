from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.workflow import analyze
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


def package(tmp_path: Path, value: str) -> None:
    root = make_mod(tmp_path / "native-packages", "native-mod", {"example.txt": b"data"})
    (root / "mod.xml").write_text(
        '<data name="Native mod"><cc2mce schema="1" type="mod" id="native-mod" '
        f'sdk="cc2x" api="8" framework_api="{value}"/></data>',
        encoding="utf-8",
    )


def test_named_c_requirement_needs_reviewed_version_and_capability(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    package(tmp_path, "1")
    scan = discover([tmp_path / "native-packages"])
    assert scan.mods[0].framework_api == 1
    assert scan.mods[0].report()["framework_api"] == 1
    profile["runtime_api"] = 8
    for version, capabilities in ((0, []), (1, []), (0, ["framework-c-api-v1"])):
        profile["runtime_framework_api"] = version
        profile["runtime_capabilities"] = capabilities
        plan = analyze(installation, scan, ["native-mod"], profile=profile)
        assert any(blocker["code"] == "sdk_api" for blocker in plan.blockers)
    profile["runtime_framework_api"] = 1
    profile["runtime_capabilities"] = ["framework-c-api-v1"]
    plan = analyze(installation, scan, ["native-mod"], profile=profile)
    assert not any(blocker["code"] == "sdk_api" for blocker in plan.blockers)


@pytest.mark.parametrize("value", ["-1", "NaN", "1.0", "10001", "\u0661"])
def test_invalid_framework_api_is_rejected(tmp_path: Path, value: str) -> None:
    package(tmp_path, value)
    with pytest.raises(InputError):
        discover([tmp_path / "native-packages"])
