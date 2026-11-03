from pathlib import Path

from cc2_mce.discovery import discover
from cc2_mce.workflow import analyze
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


def test_missing_resource_lookup_counts_each_original_directory_once(tmp_path: Path):
    game, profile, _ = fixture(tmp_path)
    for index in range(350):
        (game.root / "rom_0" / f"original-{index}.txt").write_bytes(b"original\n")
    make_mod(
        tmp_path / "source",
        "new-resources",
        {f"added-{index}.txt": b"new resource\n" for index in range(80)},
    )
    plan = analyze(game, discover([tmp_path / "source"]), ["new-resources"], profile=profile)
    assert not plan.blockers
    assert len(plan.payload) == 80
