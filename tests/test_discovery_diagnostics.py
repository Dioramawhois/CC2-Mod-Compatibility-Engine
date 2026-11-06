import json
from pathlib import Path

import pytest

from cc2_mce.diagnostics import diagnostic_envelope, error_diagnostic
from cc2_mce.discovery import discover, snapshot_unchanged
from cc2_mce.errors import DiagnosticError, InputError
from cc2_mce.filesystem import Limits
from tests.test_paths_discovery import make_mod


def test_partial_inventory_names_bad_metadata_and_keeps_good_mod(tmp_path: Path):
    make_mod(tmp_path, "good", {"a.txt": b"good"})
    bad = make_mod(tmp_path, "broken", {})
    (bad / "mod.xml").write_bytes(b"Owned invalid metadata")
    with pytest.raises(InputError, match="XML"):
        discover([tmp_path])

    scan = discover([tmp_path], collect_issues=True)
    assert [mod.id for mod in scan.mods] == ["good"]
    assert scan.issue_count == 1
    issue = scan.issues[0]
    assert issue.source_id == "broken"
    assert issue.source_path == str(bad.resolve())
    assert issue.resource_path == "mod.xml"
    assert "Invalid metadata XML" in issue.cause
    assert "broken" in issue.summary()
    assert "mod.xml" in issue.details()
    scan.require_available(["good"])
    with pytest.raises(DiagnosticError) as rejected:
        scan.require_available(["broken"])
    assert rejected.value.diagnostic.source_id == "broken"
    envelope = diagnostic_envelope(scan.issues, stage="discovery")
    assert not envelope["installable"]
    assert envelope["schema_kind"] == "diagnostics"
    assert "broken" in json.dumps(envelope)


def test_issue_fingerprint_detects_metadata_tamper_and_repair(tmp_path: Path):
    bad = make_mod(tmp_path, "broken", {})
    metadata = bad / "mod.xml"
    metadata.write_bytes(b"invalid one")
    scan = discover([tmp_path], collect_issues=True)
    assert snapshot_unchanged(scan)
    metadata.write_bytes(b"invalid two")
    assert not snapshot_unchanged(scan)
    metadata.write_bytes(b'<data name="Repaired"/>')
    fixed = discover([tmp_path], collect_issues=True)
    assert not fixed.issues
    assert [mod.name for mod in fixed.mods] == ["Repaired"]
    assert fixed.fingerprint != scan.fingerprint


def test_duplicate_mod_ids_quarantine_all_owners_without_choosing_a_winner(tmp_path: Path):
    left, right = tmp_path / "left", tmp_path / "right"
    make_mod(left, "same", {"a.txt": b"left"})
    make_mod(right, "same", {"a.txt": b"right"})
    make_mod(left, "good", {"good.txt": b"safe"})
    scan = discover([left, right], collect_issues=True)
    assert [mod.id for mod in scan.mods] == ["good"]
    assert len(scan.issues) == 2
    assert {issue.source_path for issue in scan.issues} == {
        str((left / "same").resolve()),
        str((right / "same").resolve()),
    }
    with pytest.raises(DiagnosticError):
        scan.require_available(["same"])
    (left / "same/content/a.txt").write_bytes(b"changed duplicate")
    assert not snapshot_unchanged(scan)


def test_root_issue_is_retried_after_missing_root_is_created(tmp_path: Path):
    valid, missing = tmp_path / "valid", tmp_path / "missing"
    make_mod(valid, "good", {"a.txt": b"safe"})
    scan = discover([valid, missing], collect_issues=True)
    assert [mod.id for mod in scan.mods] == ["good"]
    assert len(scan.issues) == 1
    assert snapshot_unchanged(scan)
    make_mod(missing, "new", {"new.txt": b"new"})
    assert not snapshot_unchanged(scan)


def test_rejected_candidate_does_not_poison_later_path_spellings(tmp_path: Path):
    make_mod(tmp_path, "a-bad", {"Scripts/a.lua": b"-- fixture", "zzz.png": b"x" * 129})
    make_mod(tmp_path, "b-good", {"scripts/a.lua": b"-- fixture"})
    scan = discover([tmp_path], collect_issues=True, limits=Limits(max_file_bytes=128))
    assert [mod.id for mod in scan.mods] == ["b-good"]
    assert len(scan.issues) == 1
    assert scan.issues[0].source_id == "a-bad"
    assert "129" in scan.issues[0].cause and "128" in scan.issues[0].cause


def test_unavailable_library_dependency_has_named_diagnostic(tmp_path: Path):
    app = make_mod(tmp_path, "consumer", {"a.txt": b"safe"})
    (app / "mod.xml").write_text(
        '<data name="Consumer"><cc2mce schema="1" type="mod">'
        '<requires id="shared.library"/></cc2mce></data>',
        encoding="utf-8",
    )
    library = make_mod(tmp_path, "library", {"too-big.png": b"x" * 513})
    (library / "mod.xml").write_text(
        '<data name="Shared Library"><cc2mce schema="1" type="library" '
        'id="shared.library"/></data>',
        encoding="utf-8",
    )
    scan = discover([tmp_path], collect_issues=True, limits=Limits(max_file_bytes=512))
    with pytest.raises(DiagnosticError) as rejected:
        scan.require_available(["consumer"])
    assert rejected.value.diagnostic.source_name == "Shared Library"
    assert rejected.value.diagnostic.package_id == "shared.library"


def test_global_budget_stops_further_resource_reads(tmp_path: Path, monkeypatch):
    from cc2_mce import discovery

    for name in ("a", "b", "c"):
        make_mod(tmp_path, name, {"a.txt": b"x" * 20})
    original = discovery.snapshot_regular
    reads = []

    def tracked(path, root, budget):
        reads.append(root.name)
        return original(path, root, budget)

    monkeypatch.setattr(discovery, "snapshot_regular", tracked)
    scan = discover([tmp_path], collect_issues=True, limits=Limits(max_total_bytes=60))
    assert [mod.id for mod in scan.mods] == ["a"]
    assert reads == ["a"]
    assert any("byte limit" in issue.cause for issue in scan.issues)
    with pytest.raises(DiagnosticError):
        scan.require_available(["c"])


def test_unknown_missing_dependency_retains_existing_resolver_behavior(tmp_path: Path):
    mod = make_mod(tmp_path, "app", {})
    (mod / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="mod"><requires id="cc2x.runtime"/></cc2mce></data>',
        encoding="utf-8",
    )
    scan = discover([tmp_path], collect_issues=True)
    scan.require_available(["app"])


def test_diagnostic_fields_are_bounded_and_wrapping_preserves_source_context(tmp_path: Path):
    item = error_diagnostic(
        InputError("x" * 10000),
        stage="discovery",
        source_id="broken",
        source_path=tmp_path / "broken",
        resource_path="mod.xml",
    )
    assert len(item.cause) <= 4096
    wrapped = error_diagnostic(DiagnosticError(item), stage="selection")
    assert wrapped.source_id == "broken" and wrapped.resource_path == "mod.xml"
    assert wrapped.stage == "selection"
    assert json.loads(json.dumps(wrapped.report()))["cause"] == item.cause


@pytest.mark.parametrize(
    "cause, expected",
    [
        ("Game is running or its executable is unavailable", "закройте"),
        ("Game activation changed; rebuild the selected set", "набор"),
        ("Game executable changed since activation", "файлы"),
        ("Installed runtime changed since activation", "sdk"),
    ],
)
def test_launch_guards_have_actionable_summaries_and_exact_details(cause, expected):
    item = error_diagnostic(InputError(cause), stage="launch")
    assert expected in item.summary().lower()
    assert cause in item.details()


def test_spawn_oserror_has_an_exportable_launch_diagnostic():
    item = error_diagnostic(PermissionError("Owned denied executable fixture"), stage="launch")
    assert item.stage == "launch"
    assert "Owned denied executable fixture" in item.details()
    assert diagnostic_envelope([item], stage="launch")["installable"] is False


def test_cross_mod_case_collision_quarantines_all_participants(tmp_path: Path):
    make_mod(tmp_path, "one", {"Scripts/a.lua": b"-- owned"})
    make_mod(tmp_path, "two", {"scripts/a.lua": b"-- owned"})
    make_mod(tmp_path, "good", {"safe.txt": b"safe"})
    scan = discover([tmp_path], collect_issues=True)
    assert [mod.id for mod in scan.mods] == ["good"]
    assert {issue.source_id for issue in scan.issues} == {"one", "two"}
    with pytest.raises(DiagnosticError):
        scan.require_available(["one"])
    with pytest.raises(DiagnosticError):
        scan.require_available(["two"])


def test_unsafe_link_candidate_is_not_followed_and_other_mods_remain_available(tmp_path: Path):
    collection = tmp_path / "mods"
    make_mod(collection, "good", {"safe.txt": b"safe"})
    outside = make_mod(tmp_path / "outside", "untrusted", {"secret.txt": b"outside"})
    linked = collection / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    scan = discover([collection], collect_issues=True)
    assert [mod.id for mod in scan.mods] == ["good"]
    assert len(scan.issues) == 1
    assert scan.issues[0].source_path == str(linked)
    assert "link" in scan.issues[0].cause.lower()
    with pytest.raises(DiagnosticError):
        scan.require_available(["linked"])


def test_large_invalid_sdk_api_is_a_package_issue_instead_of_aborting_inventory(tmp_path: Path):
    bad = make_mod(tmp_path, "bad", {})
    make_mod(tmp_path, "good", {"safe.txt": b"safe"})
    (bad / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="mod" api="' + "9" * 10000 + '"/></data>',
        encoding="utf-8",
    )
    scan = discover([tmp_path], collect_issues=True)
    assert [mod.id for mod in scan.mods] == ["good"]
    assert scan.issues[0].source_id == "bad"


def test_good_partial_inventory_build_preserves_revalidation_and_native_gates(tmp_path: Path):
    from cc2_mce.workflow import analyze, apply_plan
    from tests.test_workflow import fixture

    game, profile, user = fixture(tmp_path)
    bad = make_mod(tmp_path / "workshop", "broken", {})
    (bad / "mod.xml").write_bytes(b"Owned invalid metadata fixture")
    make_mod(tmp_path / "workshop", "native", {"cc2x/unreviewed.dll": b"MZ never executed"})
    scan = discover([tmp_path / "workshop"], collect_issues=True)
    scan.require_available(["a"])
    prepared = analyze(game, scan, ["a"], profile=profile)
    assert not prepared.blockers
    output = apply_plan(prepared, user, game_running=lambda: False)
    original = (output / "mce-manifest.json").read_bytes()
    with pytest.raises(DiagnosticError):
        scan.require_available(["broken"])
    assert (output / "mce-manifest.json").read_bytes() == original

    unreviewed = analyze(game, scan, ["native"], profile=profile)
    assert any(item["code"] == "native_plugin_review_required" for item in unreviewed.blockers)
    with pytest.raises(InputError):
        apply_plan(unreviewed, user, game_running=lambda: False)
    assert (output / "mce-manifest.json").read_bytes() == original


def test_issue_export_is_bounded_without_losing_the_total_count():
    issues = [
        error_diagnostic(InputError(f"owned error {i}"), stage="discovery") for i in range(205)
    ]
    report = diagnostic_envelope(issues, stage="discovery")
    assert report["diagnostic_count"] == 205
    assert report["truncated"] is True
    assert len(report["diagnostics"]) == 200


def test_valid_alternative_library_version_is_not_blocked_by_an_unselected_bad_copy(tmp_path: Path):
    good = make_mod(tmp_path, "good", {"safe.txt": b"safe"})
    (good / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="library" id="shared.library"/></data>', encoding="utf-8"
    )
    bad = make_mod(tmp_path, "bad", {"too-big.png": b"x" * 513})
    (bad / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="library" id="shared.library"/></data>', encoding="utf-8"
    )
    scan = discover([tmp_path], collect_issues=True, limits=Limits(max_file_bytes=512))
    scan.require_available(["good", "shared.library"])
    with pytest.raises(DiagnosticError):
        scan.require_available(["bad"])


def test_diagnostic_summaries_and_labels_are_available_in_all_offline_languages():
    from cc2_mce.i18n import LANGUAGES, Translator
    from cc2_mce.language_packs import PACKS
    from cc2_mce.translations import EN

    keys = {
        "Не удалось прочитать мод «{p0}». Проверьте его папку или обновите мод.",
        "Не удалось прочитать папку модов. Проверьте доступ к ней.",
        "Превышен предел чтения модов. Уменьшите набор папок и проверьте подробности.",
        "Причина: ",
        "Источник: ",
        "Игра уже запущена или её файл недоступен. Закройте игру и проверьте файлы игры.",
        "Набор модов в игре изменился. Обновите список, чтобы пересобрать его.",
        "Файлы игры изменились. Обновите список, чтобы проверить набор заново.",
        "Загрузчик SDK изменился. Обновите список, чтобы проверить набор заново.",
        "Игра не запущена. Проверьте подробности проблемы.",
    }
    assert keys <= set(EN)
    for language in LANGUAGES:
        if language not in {"ru", "en"}:
            assert keys <= set(PACKS[language]), language
        item = error_diagnostic(
            InputError("Owned exact parser cause"),
            stage="discovery",
            source_name="Owned Mod Name",
            source_path="owned-source-folder",
            resource_path="mod.xml",
        )
        assert "Owned Mod Name" in item.summary(Translator(language))
        assert "owned-source-folder" in item.details(Translator(language))
        assert "Owned exact parser cause" in item.details(Translator(language))


def test_diagnostic_report_carries_current_engine_provenance_and_validates_its_schema():
    from jsonschema import Draft202012Validator

    from cc2_mce import __version__
    from cc2_mce.reports import engine_hash

    schema = json.loads(
        (Path(__file__).parents[1] / "cc2_mce/schemas/diagnostics.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)
    report = diagnostic_envelope(
        [error_diagnostic(InputError("Owned failure"), stage="discovery", source_id="broken")],
        stage="discovery",
    )
    assert report["engine_version"] == __version__
    assert report["engine_sha256"] == engine_hash()
    validator.validate(report)
    validator.validate(diagnostic_envelope([], stage="discovery"))
    validator.validate(
        diagnostic_envelope(
            (error_diagnostic(InputError(f"Owned {i}"), stage="discovery") for i in range(205)),
            stage="discovery",
        )
    )


@pytest.mark.parametrize(
    "change",
    ["installable", "hash", "cause", "path", "extra", "row_extra", "count", "truncated"],
)
def test_diagnostic_contract_rejects_unsafe_or_inconsistent_report_fields(change):
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (Path(__file__).parents[1] / "cc2_mce/schemas/diagnostics.schema.json").read_text(
            encoding="utf-8"
        )
    )
    report = diagnostic_envelope(
        [error_diagnostic(InputError("Owned"), stage="launch")], stage="launch"
    )
    if change == "installable":
        report["installable"] = True
    elif change == "hash":
        report["engine_sha256"] = "unverified"
    elif change == "cause":
        report["diagnostics"][0]["cause"] = "x" * 4097
    elif change == "path":
        report["diagnostics"][0]["source_path"] = "x" * 2049
    elif change == "extra":
        report["unexpected"] = "Not part of the export contract"
    elif change == "row_extra":
        report["diagnostics"][0]["unexpected"] = "Not part of the export contract"
    elif change == "count":
        report["diagnostic_count"] = 201
    else:
        report.update(truncated=True, diagnostic_count=201)
    assert not Draft202012Validator(schema).is_valid(report)


def test_global_read_limit_uses_the_localized_budget_summary():
    from cc2_mce.diagnostics import Diagnostic
    from cc2_mce.i18n import Translator

    item = Diagnostic(
        "discovery_global_limit",
        "discovery",
        "Input total byte limit exceeded (61 bytes; limit 60 bytes)",
        source_name="Owned Mod",
    )
    for language in ("ru", "en", "de", "ja"):
        summary = item.summary(Translator(language))
        assert "Owned Mod" in summary
        assert (
            Translator(language)(
                "Превышен предел чтения модов. Уменьшите набор папок и проверьте подробности."
            )
            in summary
        )
    assert "Use fewer source folders" in item.summary(Translator("en"))
    assert "61" in item.details(Translator("en"))
    assert "60" in item.details(Translator("en"))


@pytest.mark.parametrize("selected", [["consumer"], ["bad-sdk"]])
def test_quarantined_named_sdk_does_not_fall_back_to_a_reviewed_provider(tmp_path: Path, selected):
    from cc2_mce.filesystem import digest
    from tests.test_workflow import fixture

    game, profile, _ = fixture(tmp_path)
    runtime = b"Owned reviewed runtime; never executed"
    (game.root / "dinput8.dll").write_bytes(runtime)
    profile.update(runtime_sha256=digest(runtime), runtime_api=8)
    consumer = make_mod(tmp_path / "workshop", "consumer", {"safe.txt": b"safe"})
    (consumer / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="mod" sdk="cc2x" api="8">'
        '<requires id="cc2x.runtime"/></cc2mce></data>',
        encoding="utf-8",
    )
    library = make_mod(tmp_path / "workshop", "bad-sdk", {"too-large.png": b"x" * 513})
    (library / "mod.xml").write_text(
        '<data name="Broken SDK"><cc2mce schema="1" type="library" id="cc2x.runtime"/></data>',
        encoding="utf-8",
    )
    scan = discover([tmp_path / "workshop"], collect_issues=True, limits=Limits(max_file_bytes=512))
    assert any(mod.id == "consumer" for mod in scan.mods)
    with pytest.raises(DiagnosticError) as rejected:
        scan.require_available(selected)
    assert rejected.value.diagnostic.source_id == "bad-sdk"


def test_valid_metadata_unknown_sdk_dll_is_not_hidden_by_partial_discovery(tmp_path: Path):
    from cc2_mce.filesystem import digest
    from cc2_mce.workflow import analyze
    from tests.test_workflow import fixture

    game, profile, _ = fixture(tmp_path)
    runtime = b"Owned reviewed runtime; never executed"
    (game.root / "dinput8.dll").write_bytes(runtime)
    profile.update(runtime_sha256=digest(runtime), runtime_api=8)
    library = make_mod(tmp_path / "workshop", "sdk", {"dinput8.dll": b"MZ unreviewed bytes"})
    (library / "mod.xml").write_text(
        '<data><cc2mce schema="1" type="library" id="cc2x.runtime" sdk="cc2x" api="8"/></data>',
        encoding="utf-8",
    )
    scan = discover([tmp_path / "workshop"], collect_issues=True)
    scan.require_available(["sdk"])
    prepared = analyze(game, scan, ["sdk"], profile=profile)
    assert any(item["code"] == "runtime_source_conflict" for item in prepared.blockers)
    assert (game.root / "dinput8.dll").read_bytes() == runtime
