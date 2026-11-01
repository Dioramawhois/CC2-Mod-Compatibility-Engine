import json
import subprocess
import sys
from pathlib import Path

from cc2_mce.cli import main


def test_committed_golden_matches_on_every_host(capsys) -> None:
    root = Path(__file__).parents[1]
    assert main(["--config", str(root / "examples/mce.synthetic.toml"), "build", "--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)
    expected = json.loads((root / "tests/fixtures/golden/expected.json").read_text())
    assert {key: report["files"][0][key] for key in expected} == expected
    assert report["installable"] is False


def test_module_entrypoint_from_another_directory(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "cc2_mce", "--version"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    from cc2_mce import __version__

    assert result.stdout.strip() == __version__
