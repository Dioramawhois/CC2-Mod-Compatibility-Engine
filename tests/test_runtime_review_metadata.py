import json
from pathlib import Path

from cc2_mce.discovery import discover
from cc2_mce.workflow import analyze
from tests.test_runtime_provider_sync import providers


def test_bundled_runtime_review_metadata_is_a_valid_package_contract(tmp_path, monkeypatch):
    game, profile, user, source, sdk, runtime = providers(tmp_path, monkeypatch)
    bundled = Path(__file__).parents[1] / "cc2_mce/profiles/windows-1.5.18-r2.json"
    profile["runtime_review"] = json.loads(bundled.read_text())["runtime_review"]
    plan = analyze(game, discover([source]), ["workshop-sdk"], profile=profile, user_dir=user)
    assert not plan.blockers
    assert plan.report["runtime_review"] == profile["runtime_review"]
