from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import Budget, Limits, input_root, walk_regular
from cc2_mce.merge import GitMergeAdapter, MergeInput, MergeOutcome, merge_file
from tests.test_paths_discovery import make_mod


def test_depth_and_entry_budgets(tmp_path: Path) -> None:
    make_mod(tmp_path, "a", {"a/b/c/d.txt": b"data"})
    with pytest.raises(InputError, match="depth"):
        discover([tmp_path], limits=Limits(max_depth=1))
    with pytest.raises(InputError, match="entry"):
        walk_regular(tmp_path, Budget(Limits(max_entries=1)))


def test_aggregate_byte_budget(tmp_path: Path) -> None:
    make_mod(tmp_path, "a", {"a.txt": b"a" * 20, "b.txt": b"b" * 20})
    with pytest.raises(InputError, match="byte limit"):
        discover([tmp_path], limits=Limits(max_total_bytes=60))


def test_root_ancestor_link_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "real/inside").mkdir(parents=True)
    try:
        (tmp_path / "linked").symlink_to(tmp_path / "real", target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(InputError, match="link"):
        input_root(tmp_path / "linked/inside")


def test_n_way_accumulator_conflict_stops_immediately() -> None:
    class Adapter(GitMergeAdapter):
        def __init__(self) -> None:
            self.calls = 0

        def merge(self, ours: bytes, base: bytes, theirs: bytes) -> MergeOutcome:
            self.calls += 1
            if self.calls <= 3:
                return MergeOutcome("clean", "text-3way", b"pairwise\n")
            return MergeOutcome("conflict", "text-3way")

    adapter = Adapter()
    result = merge_file(
        "a.txt",
        [MergeInput(str(i), f"value={i}\n".encode()) for i in range(3)],
        b"base\n",
        baseline_verified=True,
        git=adapter,
    )
    assert result.status == "conflict"
    assert result.content is None
    assert adapter.calls == 4


def test_source_markers_cannot_be_erased_into_false_success() -> None:
    conflict = b"<<<<<<< ours\none\n=======\ntwo\n>>>>>>> theirs\n"
    result = merge_file(
        "a.txt",
        [MergeInput("a", conflict), MergeInput("b", b"new\n")],
        conflict,
        baseline_verified=True,
    )
    assert result.status == "validation_error"
    assert result.content is None
