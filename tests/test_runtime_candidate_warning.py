from cc2_mce.i18n import Translator
from cc2_mce.ui_feedback import explain_overrides


def report():
    return {
        "files": [],
        "sources": [],
        "mod_order": [],
        "runtime_review": {"stage": "client-candidate"},
    }


def test_runtime_candidate_notice_is_visible_without_a_resource_collision():
    warning = explain_overrides(report(), Translator("en"))
    assert warning is not None
    assert "single-player" in warning.message
    assert "dedicated" in warning.details
    assert warning.rows == {}


def test_native_scope_notice_preserves_the_existing_override_participants():
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
    warning = explain_overrides(value, Translator("en"))
    assert warning is not None
    assert "First" in warning.message and "Patch" in warning.message
    assert "single-player" in warning.message
    assert set(warning.rows) == {"a", "b"}


def test_data_only_sets_do_not_receive_a_native_candidate_notice():
    value = report()
    del value["runtime_review"]
    assert explain_overrides(value) is None
