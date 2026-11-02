import pytest

from tools.package_release import public_build_report, validate_source_names


def test_public_build_report_does_not_publish_local_game_or_account_paths():
    report = public_build_report(
        {
            "version": "test",
            "artifact_sha256": "a" * 64,
            "engine_sha256": "b" * 64,
            "source_sha256": {"cc2_mce/gui.py": "c" * 64},
            "tested_mod_order": ["private-mod"],
            "local_acceptance": {"path": "C:/Users/private"},
            "evidence": "private-save",
            "regressions": {"passed": 1},
        }
    )
    assert "private" not in str(report)
    assert report["regressions"] == {"passed": 1}


@pytest.mark.parametrize(
    "name",
    [
        ".env",
        "build/secret.json",
        "research/game.c",
        "cc2_mce/tools_data/git/git.exe",
        "../outside",
        "C:/private",
        "game.exe",
    ],
)
def test_release_sources_refuse_private_or_compiled_artifacts(name):
    with pytest.raises(ValueError):
        validate_source_names(["LICENSE", "cc2_mce/gui.py", name])


def test_release_sources_require_a_license_and_keep_test_fixtures():
    with pytest.raises(ValueError):
        validate_source_names(["cc2_mce/gui.py"])
    validate_source_names(["LICENSE", "cc2_mce/gui.py", "tests/fixtures/mod/content/test.xml"])
