import json
from pathlib import Path
from unittest.mock import patch

import jsonschema

from cc2_mce.cli import main
from tests.test_baseline import baseline_fixture
from tests.test_paths_discovery import make_mod

BASE = b"a=1\n\n\nb=1\n"


def read_stdout(capsys):
    return json.loads(capsys.readouterr().out)


def test_scan_schema_and_no_absolute_paths(tmp_path: Path, capsys) -> None:
    make_mod(tmp_path, "a", {"a.txt": b"hello"})
    assert main(["scan", "--mods-dir", str(tmp_path)]) == 0
    report = read_stdout(capsys)
    assert report["installable"] is False
    assert report["sources"][0]["id"] == "a"
    assert str(tmp_path) not in json.dumps(report)
    schema = json.loads(
        (Path(__file__).parents[1] / "cc2_mce/schemas/report.schema.json").read_text()
    )
    jsonschema.validate(report, schema)


def test_build_dry_run_merges_without_output(tmp_path: Path, capsys) -> None:
    mods = tmp_path / "mods"
    make_mod(mods, "a", {"constants.txt": BASE.replace(b"a=1", b"a=2")})
    make_mod(mods, "b", {"constants.txt": BASE.replace(b"b=1", b"b=2")})
    baseline = baseline_fixture(tmp_path / "base", {"constants.txt": BASE})
    output = tmp_path / "never-created"
    args = [
        "build",
        "--mods-dir",
        str(mods),
        "--mods",
        "a",
        "b",
        "--baseline",
        str(baseline),
        "--output",
        str(output),
        "--dry-run",
    ]
    assert main(args) == 0
    first = read_stdout(capsys)
    assert first["files"][0]["status"] == "clean"
    assert first["installable"] is False
    assert first["baseline"]["kind"] == "synthetic"
    assert first["baseline"]["verified"] is False
    assert not output.exists()
    assert main(args) == 0
    assert read_stdout(capsys) == first
    # Real build: a clean plan writes the merged file; the report stays schema-valid read-only.
    real = ["build", "--mods-dir", str(mods), "--mods", "a", "b", "--output", str(output),
            "--baseline", str(baseline)]
    assert main(real) == 0
    merged = (output / "constants.txt").read_bytes()
    assert b"a=2" in merged and b"b=2" in merged
    assert read_stdout(capsys)["installable"] is False


def test_conflict_native_binary_and_missing_base_exit(tmp_path: Path, capsys) -> None:
    mods = tmp_path / "mods"
    make_mod(mods, "a", {"a.txt": b"one"})
    make_mod(mods, "b", {"a.txt": b"two"})
    args = ["plan", "--mods-dir", str(mods), "--mods", "a", "b"]
    assert main(args) == 3
    assert read_stdout(capsys)["files"][0]["status"] == "no_base"
    base = baseline_fixture(tmp_path / "base", {"a.txt": b"base"})
    assert main([*args, "--baseline", str(base)]) == 2
    report = read_stdout(capsys)
    assert report["conflicts"][0]["resolution"] == "unresolved"
    assert report["files"][0]["output_sha256"] is None


def test_report_cannot_write_into_sources_or_overwrite(tmp_path: Path, capsys) -> None:
    make_mod(tmp_path / "mods", "a", {"a.txt": b"original"})
    protected = tmp_path / "mods/a/content/a.txt"
    assert main(["scan", "--mods-dir", str(tmp_path / "mods"), "--json", str(protected)]) == 4
    assert protected.read_bytes() == b"original"
    capsys.readouterr()
    report_path = tmp_path / "scan.json"
    args = ["scan", "--mods-dir", str(tmp_path / "mods"), "--json", str(report_path)]
    assert main(args) == 0
    capsys.readouterr()
    original = report_path.read_bytes()
    assert main(args) == 4
    assert report_path.read_bytes() == original


def test_report_roundtrip_rejects_installable_claim(tmp_path: Path, capsys) -> None:
    assert main(["scan", "--mods-dir", str(tmp_path)]) == 0
    report = read_stdout(capsys)
    path = tmp_path / "scan.json"
    path.write_text(json.dumps(report))
    assert main(["report", str(path)]) == 0
    assert read_stdout(capsys) == report
    report["installable"] = True
    path.write_text(json.dumps(report))
    assert main(["report", str(path)]) == 4


def test_workshop_change_aborts_plan(tmp_path: Path, capsys) -> None:
    mod = make_mod(tmp_path, "a", {"a.txt": b"one"})
    with patch("cc2_mce.planner.snapshot_unchanged", return_value=False):
        assert main(["plan", "--mods", str(mod)]) == 4
    assert read_stdout(capsys)["status"] == "blocked"


def test_toml_config_and_unknown_ids(tmp_path: Path, capsys) -> None:
    mods = tmp_path / "mods"
    make_mod(mods, "a", {"a.txt": b"one"})
    config = tmp_path / "mce.toml"
    config.write_text('schema_version = 1\nlocal_mods_dir = "mods"\nmod_order = ["a"]\n')
    assert main(["--config", str(config), "plan"]) == 0
    assert read_stdout(capsys)["mod_order"] == ["a"]
    assert main(["--config", str(config), "plan", "--mods", "missing"]) == 4


def test_doctor_real_tools_and_bad_lua(tmp_path: Path, capsys) -> None:
    assert main(["doctor", "--luac", str(tmp_path / "absent")]) == 5
    report = read_stdout(capsys)
    assert report["tools"]["git"]["available"] is True
    assert report["tools"]["lua"]["compatible"] is False


def test_build_plan_input_is_explicitly_deferred(capsys) -> None:
    assert main(["build", "--plan", "anything.json", "--dry-run"]) == 2
    assert "unsupported_plan_replay" in json.dumps(read_stdout(capsys))


def test_invalid_output_intersections_block_even_dry_run(tmp_path: Path, capsys) -> None:
    mod = make_mod(tmp_path, "a", {"a.txt": b"one"})
    assert main(["build", "--mods", str(mod), "--output", str(mod / "out"), "--dry-run"]) == 4
    assert not (mod / "out").exists()


def test_bad_arguments_still_structured(capsys) -> None:
    assert main(["plan", "--unknown"]) == 4
    assert read_stdout(capsys)["status"] == "blocked"


def test_config_relative_path_itself(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "settings"
    config_dir.mkdir()
    make_mod(config_dir / "mods", "a", {"a.txt": b"one"})
    (config_dir / "mce.toml").write_text(
        'schema_version = 1\nlocal_mods_dir = "mods"\nmod_order = ["a"]\n'
    )
    monkeypatch.chdir(tmp_path)
    assert main(["--config", "settings/mce.toml", "plan"]) == 0
    assert read_stdout(capsys)["mod_order"] == ["a"]


def test_report_rejects_invalid_file_status(tmp_path: Path, capsys) -> None:
    mod = make_mod(tmp_path / "mods", "a", {"a.txt": b"one"})
    assert main(["plan", "--mods", str(mod)]) == 0
    report = read_stdout(capsys)
    report["files"][0]["status"] = "invented-success"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(report))
    assert main(["report", str(path)]) == 4


def test_report_never_created_under_steam_root(tmp_path: Path, capsys) -> None:
    steam = tmp_path / "steamapps/common/example"
    steam.mkdir(parents=True)
    destination = steam / "scan.json"
    mods = tmp_path / "mods"
    mods.mkdir()
    assert main(["scan", "--mods-dir", str(mods), "--json", str(destination)]) == 4
    assert not destination.exists()
    assert read_stdout(capsys)["status"] == "blocked"


def test_non_strict_config_is_not_silently_accepted(tmp_path: Path, capsys) -> None:
    config = tmp_path / "mce.toml"
    config.write_text("schema_version = 1\nstrict_validation = false\n")
    assert main(["--config", str(config), "scan"]) == 4
    assert read_stdout(capsys)["status"] == "blocked"

def test_build_writes_merged_disjoint_edits(tmp_path: Path, capsys) -> None:
    mods = tmp_path / "mods"
    make_mod(mods, "a", {"constants.txt": BASE.replace(b"a=1", b"a=2")})
    make_mod(mods, "b", {"constants.txt": BASE.replace(b"b=1", b"b=2")})
    baseline = baseline_fixture(tmp_path / "base", {"constants.txt": BASE})
    output = tmp_path / "merged"
    assert main(["build", "--mods-dir", str(mods), "--mods", "a", "b",
                 "--baseline", str(baseline), "--output", str(output)]) == 0
    merged = (output / "constants.txt").read_bytes()
    assert b"a=2" in merged and b"b=2" in merged
    assert b"a=1" not in merged and b"b=1" not in merged

def test_build_conflict_writes_nothing(tmp_path: Path, capsys) -> None:
    mods = tmp_path / "mods"
    make_mod(mods, "a", {"constants.txt": BASE.replace(b"a=1", b"a=7")})
    make_mod(mods, "b", {"constants.txt": BASE.replace(b"a=1", b"a=9")})
    baseline = baseline_fixture(tmp_path / "base", {"constants.txt": BASE})
    output = tmp_path / "merged"
    assert main(["build", "--mods-dir", str(mods), "--mods", "a", "b",
                 "--baseline", str(baseline), "--output", str(output)]) == 2
    assert read_stdout(capsys)["conflicts"]
    assert not output.exists()
