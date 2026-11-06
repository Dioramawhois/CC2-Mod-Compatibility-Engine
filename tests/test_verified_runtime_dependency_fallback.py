from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import DiagnosticError
from cc2_mce.filesystem import Limits, digest
from cc2_mce.workflow import analyze, apply_plan
from tests.test_quarantined_runtime_dependencies import prepared
from tests.test_signed_runtime_provider import prepare
from tests.test_signed_runtime_provider import signed_sdk as signed_sdk


def test_verified_bundled_runtime_supplies_quarantined_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, profile, user, scan, candidate = prepared(tmp_path, monkeypatch, "known_identity")
    plan = analyze(game, scan, ["consumer"], profile=profile, user_dir=user)
    assert not plan.blockers
    assert [mod.id for mod in plan.selected] == ["consumer"]
    assert plan.runtime_source == candidate
    assert plan.report["runtime_sha256"] == digest(candidate.read_bytes())
    assert scan.issues[0].package_id == "cc2x.runtime"
    apply_plan(plan, user, game_running=lambda: False)
    assert (game.root / "dinput8.dll").read_bytes() == candidate.read_bytes()


@pytest.mark.parametrize(
    "selected",
    [
        ["workshop-sdk"],
        ["cc2x.runtime"],
        ["island-airfields", "workshop-sdk"],
        ["workshop-sdk", "island-airfields"],
    ],
)
def test_installed_signed_provider_does_not_hide_explicit_bad_sdk(
    signed_sdk, selected: list[str]
) -> None:
    game, profile, user, source, sdk, installed, update = signed_sdk
    data, _ = update()
    apply_plan(prepare(signed_sdk), user, game_running=lambda: False)
    (sdk / "content/broken.png").write_bytes(b"x" * 4096)
    scan = discover([source], collect_issues=True, limits=Limits(max_file_bytes=2048))
    assert any(issue.package_id == "cc2x.runtime" for issue in scan.issues)
    with pytest.raises(DiagnosticError) as refused:
        analyze(game, scan, selected, profile=profile, user_dir=user)
    assert refused.value.diagnostic.source_id == "workshop-sdk"
    assert installed.read_bytes() == data


def test_installed_signed_provider_supplies_quarantined_dependency(signed_sdk) -> None:
    game, profile, user, source, sdk, installed, update = signed_sdk
    data, _ = update()
    apply_plan(prepare(signed_sdk), user, game_running=lambda: False)
    (sdk / "content/broken.png").write_bytes(b"x" * 4096)
    scan = discover([source], collect_issues=True, limits=Limits(max_file_bytes=2048))
    plan = analyze(game, scan, ["island-airfields"], profile=profile, user_dir=user)
    assert not plan.blockers
    assert [mod.id for mod in plan.selected] == ["island-airfields"]
    assert plan.report["runtime_sha256"] == digest(data)
    assert plan.report["runtime_provider"]["payload"]["runtime_sha256"] == digest(data)
    apply_plan(plan, user, game_running=lambda: False)
    assert installed.read_bytes() == data


def test_unknown_installed_loader_cannot_bypass_quarantined_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, profile, user, scan, _ = prepared(tmp_path, monkeypatch, "known_identity")
    unknown = b"Owned unknown loader fixture; never execute"
    (game.root / "dinput8.dll").write_bytes(unknown)
    with pytest.raises(DiagnosticError):
        analyze(game, scan, ["consumer"], profile=profile, user_dir=user)
    assert (game.root / "dinput8.dll").read_bytes() == unknown
