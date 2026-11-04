from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import DiagnosticError
from cc2_mce.filesystem import Limits, digest
from cc2_mce.workflow import analyze
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, broken: str):
    import cc2_mce.workflow as workflow

    game, profile, user = fixture(tmp_path)
    source = tmp_path / "sources"
    consumer = make_mod(source, "consumer", {"a.txt": b"owned resource\n"})
    (consumer / "mod.xml").write_text(
        '<data name="Consumer"><cc2mce schema="1" type="mod" sdk="cc2x" api="8">'
        '<requires id="cc2x.runtime"/></cc2mce></data>',
        encoding="utf-8",
    )
    if broken != "absent":
        library = make_mod(source, "broken-sdk", {"too-big.png": b"x" * 513})
        (library / "mod.xml").write_text(
            '<data name="Shared SDK"><cc2mce schema="1" type="library" '
            'id="cc2x.runtime" sdk="cc2x" api="8"/></data>'
            if broken == "known_identity"
            else "<data",
            encoding="utf-8",
        )
    runtime = b"MZ exact reviewed builtin runtime fixture; never execute"
    bundled = tmp_path / "application-runtime"
    candidate = bundled / digest(runtime) / "dinput8.dll"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(runtime)
    monkeypatch.setattr(workflow, "RUNTIME_DATA", bundled)
    profile.update(runtime_sha256=digest(runtime), runtime_api=8)
    scan = discover([source], collect_issues=True, limits=Limits(max_file_bytes=512))
    return game, profile, user, scan, candidate


@pytest.mark.parametrize("selected", [["consumer"], ["broken-sdk"], ["cc2x.runtime"]])
def test_core_rejects_known_quarantined_runtime_before_builtin_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: list[str]
) -> None:
    game, profile, user, scan, _ = prepared(tmp_path, monkeypatch, "known_identity")
    before = (user / "mods.xml").read_bytes()
    with pytest.raises(DiagnosticError) as refused:
        analyze(game, scan, selected, profile=profile)
    assert refused.value.diagnostic.source_id == "broken-sdk"
    assert refused.value.diagnostic.package_id == "cc2x.runtime"
    assert refused.value.diagnostic.source_name == "Shared SDK"
    assert (user / "mods.xml").read_bytes() == before
    assert not (game.root / "dinput8.dll").exists()


@pytest.mark.parametrize("broken", ["absent", "unknown_identity"])
def test_builtin_still_supplies_genuinely_missing_or_unknown_unselected_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, broken: str
) -> None:
    game, profile, _, scan, candidate = prepared(tmp_path, monkeypatch, broken)
    plan = analyze(game, scan, ["consumer"], profile=profile)
    assert not plan.blockers
    assert [mod.id for mod in plan.selected] == ["consumer"]
    assert plan.runtime_source == candidate
    assert plan.report["runtime_sha256"] == digest(candidate.read_bytes())
    assert not (game.root / "dinput8.dll").exists()


def test_explicit_unparseable_quarantined_source_still_refuses_with_named_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, profile, _, scan, _ = prepared(tmp_path, monkeypatch, "unknown_identity")
    with pytest.raises(DiagnosticError) as refused:
        analyze(game, scan, ["broken-sdk"], profile=profile)
    assert refused.value.diagnostic.source_id == "broken-sdk"
    assert refused.value.diagnostic.package_id == ""
