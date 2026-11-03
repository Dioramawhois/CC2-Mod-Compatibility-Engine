import pytest

from cc2_mce.i18n import LANGUAGES, Translator
from cc2_mce.ui_feedback import explain_overrides


def report():
    return {
        "files": [],
        "sources": [],
        "mod_order": [],
        "runtime_review": {"stage": "client-candidate"},
    }


@pytest.mark.parametrize("language", LANGUAGES)
def test_runtime_review_does_not_create_a_gui_warning(language):
    value = report()
    assert explain_overrides(value, Translator(language)) is None
    assert value["runtime_review"] == {"stage": "client-candidate"}


@pytest.mark.parametrize("language", LANGUAGES)
def test_runtime_review_does_not_change_existing_override_feedback(language):
    value = report()
    value.update(
        sources=[{"id": "a", "name": "First"}, {"id": "b", "name": "Patch"}],
        mod_order=["a", "b"],
        files=[
            {
                "logical_path": "screen.lua",
                "status": "overridden",
                "strategy": "git-three-way-later-hunks",
                "source_sha256": {"a": "a" * 64, "b": "b" * 64},
            }
        ],
    )
    warning = explain_overrides(value, Translator(language))
    assert warning is not None
    assert "First" in warning.message and "Patch" in warning.message
    assert set(warning.rows) == {"a", "b"}
    without_review = {key: item for key, item in value.items() if key != "runtime_review"}
    assert warning == explain_overrides(without_review, Translator(language))


def test_data_only_sets_do_not_receive_a_native_candidate_notice():
    value = report()
    del value["runtime_review"]
    assert explain_overrides(value) is None
