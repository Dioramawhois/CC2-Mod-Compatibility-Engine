"""Check bundle data when the developer's PyInstaller environment is available."""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from cc2_mce import reports


def test_windows_spec_preserves_schema_and_engine_hash(tmp_path, monkeypatch) -> None:
    pytest.importorskip("PyInstaller", reason="Windows packaging tool is build-only")
    root = Path(__file__).parents[1]
    captured = {}

    def analysis(scripts, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(pure=[], scripts=scripts, binaries=[], datas=kwargs["datas"])

    runpy.run_path(
        str(root / "CC2ModLoader-0.1.0.spec"),
        init_globals={
            "SPECPATH": str(root),
            "Analysis": analysis,
            "PYZ": lambda *args, **kwargs: None,
            "EXE": lambda *args, **kwargs: None,
        },
    )
    bundled = {
        (Path(destination) / Path(source).name).as_posix(): Path(source)
        for source, destination in captured["datas"]
    }
    expected = [*sorted((root / "cc2_mce").glob("*.py"))]
    expected += list((root / "cc2_mce/schemas").glob("*.json"))
    expected += list((root / "cc2_mce/profiles").glob("*.json"))
    if (root / "cc2_mce/tools_data/manifest.json").is_file():
        expected.append(root / "cc2_mce/tools_data/manifest.json")
    for source in expected:
        relative = source.relative_to(root)
        assert relative.as_posix() in bundled, f"Missing bundle input: {relative}"
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bundled[relative.as_posix()].read_bytes())

    original = reports.envelope("scan")
    monkeypatch.setattr(reports, "__file__", str(tmp_path / "cc2_mce/reports.py"))
    assert reports.engine_hash() == original["engine_sha256"]
    assert reports.validate_report(original) == original
