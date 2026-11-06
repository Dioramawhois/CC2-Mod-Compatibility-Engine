from cc2_mce.ui_feedback import explain_overrides, explain_rejection


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


def test_unsupported_resource_names_file_and_real_reason():
    value = report()
    value["blockers"] = [
        {"code": "needs_review", "file": "textures/test.xyz", "message": "Unknown resource type"}
    ]
    feedback = explain_rejection(value, {"a"}, {"a", "b"})
    assert "textures/test.xyz" in feedback.message
    assert "не поддерживает" in feedback.message
    assert "безопасно" not in feedback.message
    assert "Unknown resource type" in feedback.details


def test_missing_lua_validator_is_not_called_an_incompatible_mod():
    value = report()
    value["blockers"] = [
        {
            "code": "needs_review",
            "file": "scripts/test.lua",
            "message": "Lua 5.3 syntax validator is unavailable",
        }
    ]
    feedback = explain_rejection(value, {"a"}, {"a", "b"})
    assert "Lua 5.3" in feedback.message
    assert "встроенный" in feedback.message
    assert "scripts/test.lua" in feedback.message


def test_long_names_cannot_expand_main_notice_without_bound():
    value = report()
    value["sources"] = [{"id": str(i), "name": "X" * 256} for i in range(32)]
    feedback = explain_rejection(value, set(), {str(i) for i in range(32)})
    assert len(feedback.title) < 300
    assert "ещё 29" in feedback.title


def override_report():
    value = report()
    value["mod_order"] = ["b", "a"]
    value["files"][0].update(status="overridden", strategy="git-three-way-later-hunks")
    return value


def test_override_warning_names_sources_file_and_uncertain_game_result():
    warning = explain_overrides(override_report())
    assert warning is not None
    assert "scripts/common.lua" in warning.message
    assert warning.message.index("New Mod") < warning.message.index("Working Mod")
    assert "неизвестен" in warning.message
    assert set(warning.rows) == {"a", "b"}
    assert all("Включён" in text for text in warning.rows.values())
    assert "участки" in warning.details


def test_clean_merge_and_identical_files_have_no_override_warning():
    for status in ("clean", "identical", "unique"):
        value = override_report()
        value["files"][0]["status"] = status
        assert explain_overrides(value) is None


def test_whole_file_override_is_not_described_as_hunk_merge():
    for strategy in ("ordered-replacement-no-base", "ordered-binary-replacement"):
        value = override_report()
        value["files"][0]["strategy"] = strategy
        warning = explain_overrides(value)
        assert warning is not None
        assert "целиком" in warning.details
        assert "участки" not in warning.details


def test_override_banner_is_bounded_but_details_keep_all_paths():
    value = override_report()
    value["sources"][0]["name"] = "A" * 256
    value["files"] = [
        {**value["files"][0], "logical_path": f"scripts/{i}-" + "x" * 200 + ".lua"}
        for i in range(100)
    ]
    warning = explain_overrides(value)
    assert warning is not None
    assert len(warning.message) < 550
    assert "99" in warning.message
    assert all(item["logical_path"] in warning.details for item in value["files"])


def runtime_source_report():
    return {
        "sources": [{"id": "sdk", "name": "CC2X SDK 0.8.1"}],
        "files": [
            {
                "logical_path": "dinput8.dll",
                "status": "runtime_source_conflict",
                "strategy": "blocked",
                "source_sha256": {"sdk": "unsupported-sdk-hash"},
            }
        ],
        "blockers": [
            {
                "code": "runtime_source_conflict",
                "file": "dinput8.dll",
                "message": "CC2X SDK 0.8.1: unsupported-sdk-hash",
            }
        ],
    }


def test_sdk_source_conflict_names_provider_when_unrelated_mod_is_removed():
    from cc2_mce.i18n import Translator

    feedback = explain_rejection(
        runtime_source_report(),
        {"sdk", "islands"},
        {"sdk"},
        {"islands": "Island Airfields"},
        Translator("en"),
    )
    assert "disable «Island Airfields»" in feedback.title
    assert "CC2X SDK 0.8.1" in feedback.message
    assert "Download the library again." in feedback.message
    assert "Update ModLoader." not in feedback.message
    assert "installed" not in feedback.message.lower()
    assert "Island Airfields" not in feedback.message
    assert set(feedback.rows) == {"sdk"}
    assert "CC2X SDK 0.8.1" in feedback.rows["sdk"]
    assert "unsupported-sdk-hash" in feedback.details


def test_unknown_installed_runtime_retains_distinct_existing_diagnostic():
    from cc2_mce.i18n import Translator

    value = runtime_source_report()
    value["blockers"] = [{"code": "runtime_conflict", "message": "Unknown installed DLL"}]
    feedback = explain_rejection(value, set(), {"sdk"}, translate=Translator("en"))
    assert feedback.message == "The installed CC2X loader does not support this selection."
    assert "Update ModLoader." not in feedback.message
    assert "Unknown installed DLL" in feedback.details


def test_sdk_source_conflict_message_is_complete_in_all_offline_languages():
    from cc2_mce.i18n import LANGUAGES, Translator
    from cc2_mce.language_packs import PACKS
    from cc2_mce.translations import EN

    key = "Не удалось проверить DLL библиотеки SDK. Повторите загрузку библиотеки."
    assert key in EN
    assert set(LANGUAGES) == {"ru", "en", *PACKS}
    for language in LANGUAGES:
        if language not in {"ru", "en"}:
            assert key in PACKS[language], language
            assert set(PACKS[language]) == set(EN), language
        feedback = explain_rejection(
            runtime_source_report(), {"sdk"}, {"sdk"}, translate=Translator(language)
        )
        assert "CC2X SDK 0.8.1" in feedback.message
        assert "ModLoader" not in feedback.message
        assert "CC2X SDK 0.8.1" in feedback.rows["sdk"]
        assert Translator(language)(key) in feedback.message


def screen_extension_report(code="screen_extension_conflict"):
    return {
        "sources": [
            {"id": "sdk", "name": "CC2X SDK"},
            {"id": "map", "name": "Tactical Map"},
        ],
        "files": [],
        "blockers": [
            {
                "code": code,
                "file": "cc2x/screen_extensions.json",
                "participants": ["sdk", "map"],
                "message": "Duplicate SDK extensions for scripts/screen_holomap.lua",
            }
        ],
    }


def test_duplicate_sdk_screen_extensions_name_owners_when_other_mod_is_removed():
    from cc2_mce.i18n import Translator

    feedback = explain_rejection(
        screen_extension_report(),
        {"sdk", "map", "islands"},
        {"sdk", "map"},
        {"islands": "Island Airfields"},
        Translator("en"),
    )
    assert "disable «Island Airfields»" in feedback.title
    assert "CC2X SDK" in feedback.message
    assert "Tactical Map" in feedback.message
    assert "Island Airfields" not in feedback.message
    assert "SDK extensions" in feedback.message
    assert "not supported" in feedback.message
    assert "DLL" not in feedback.message and "installed" not in feedback.message.lower()
    assert set(feedback.rows) == {"sdk", "map"}
    assert "scripts/screen_holomap.lua" in feedback.details


def test_explicit_extension_owners_take_priority_over_merged_descriptor_sources():
    value = screen_extension_report()
    value["sources"].append({"id": "other", "name": "Unrelated Screens"})
    value["files"] = [
        {
            "logical_path": "cc2x/screen_extensions.json",
            "source_sha256": {"sdk": "a", "map": "b", "other": "c"},
        }
    ]
    feedback = explain_rejection(value, {"sdk", "map", "other"}, {"sdk", "map", "other"})
    assert "Unrelated Screens" not in feedback.message
    assert set(feedback.rows) == {"sdk", "map"}


def test_invalid_screen_extension_names_provider_and_preserves_technical_details():
    from cc2_mce.i18n import Translator

    value = screen_extension_report("screen_extension_invalid")
    value["blockers"][0].update(participants=["map"], message="Unsafe screen helper path")
    feedback = explain_rejection(value, {"sdk", "map"}, {"sdk", "map"}, translate=Translator("en"))
    assert "Tactical Map" in feedback.message
    assert "validation" in feedback.message
    assert "DLL" not in feedback.message
    assert "Unsafe screen helper path" in feedback.details
    assert set(feedback.rows) == {"map"}


def test_screen_extension_messages_are_complete_in_all_offline_languages():
    from cc2_mce.i18n import LANGUAGES, Translator
    from cc2_mce.language_packs import PACKS
    from cc2_mce.translations import EN

    keys = {
        "screen_extension_invalid": (
            "Изменения игрового экрана в этом моде не прошли проверку. Подробности — в меню."
        ),
        "screen_extension_conflict": (
            "В сборке несколько SDK-расширений одного экрана. "
            "Такое сочетание пока не поддерживается. Отключите один из модов."
        ),
    }
    for code, key in keys.items():
        assert key in EN
        for language in LANGUAGES:
            if language not in {"ru", "en"}:
                assert key in PACKS[language], (code, language)
                assert set(PACKS[language]) == set(EN), language
            feedback = explain_rejection(
                screen_extension_report(code),
                {"sdk", "map"},
                {"sdk", "map"},
                translate=Translator(language),
            )
            assert Translator(language)(key) in feedback.message
            assert "CC2X SDK" in feedback.message and "Tactical Map" in feedback.message
