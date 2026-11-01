from cc2_mce.ui_feedback import explain_rejection


def report():
    return {
        "sources": [{"id": "a", "name": "Working Mod"}, {"id": "b", "name": "New Mod"}],
        "files": [
            {"logical_path": "scripts/common.lua", "source_sha256": {"a": "hash", "b": "hash"}}
        ],
        "blockers": [{"code": "conflict", "file": "scripts/common.lua"}],
    }


def test_rejection_identifies_new_mod_incumbent_and_file():
    feedback = explain_rejection(report(), {"a"}, {"a", "b"})
    assert "New Mod" in feedback.title
    assert "Working Mod" in feedback.rows["b"]
    assert "scripts/common.lua" in feedback.details
    assert "a" not in feedback.rows  # Never label the incumbent as disabled.


def test_failed_removal_uses_name_even_when_absent_from_requested_report():
    feedback = explain_rejection(report(), {"a", "b", "c"}, {"a", "b"}, {"c": "Removed Mod"})
    assert "отключить «Removed Mod»" in feedback.title


def test_source_update_failure_says_previous_version_is_still_active():
    feedback = explain_rejection(report(), {"a", "b"}, {"a", "b"})
    assert "Обновление" in feedback.title
    assert all("предыдущая версия" in text for text in feedback.rows.values())


def test_long_names_cannot_expand_main_notice_without_bound():
    value = report()
    value["sources"] = [{"id": str(i), "name": "X" * 256} for i in range(32)]
    feedback = explain_rejection(value, set(), {str(i) for i in range(32)})
    assert len(feedback.title) < 300
    assert "ещё 29" in feedback.title
