import tracemalloc
from pathlib import Path

import pytest

from cc2_mce import discovery, filesystem
from cc2_mce.discovery import FileRef, discover, snapshot_unchanged
from cc2_mce.errors import InputError
from cc2_mce.filesystem import SCAN_LIMITS, Budget, Limits, digest
from tests.test_large_resource_workflow import sparse_file
from tests.test_paths_discovery import make_mod


def _sparse_resource(mod: Path, name: str, size: int) -> Path:
    path = mod / "content" / name
    sparse_file(path, size, b"TXTR")
    return path


def test_large_resource_is_streamed_without_loading_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = make_mod(tmp_path, "large", {})
    size = 16 * 1024 * 1024 + 1
    resource = _sparse_resource(mod, "textures/large.txtr", size)
    original_read = discovery.read_regular

    def metadata_only(path: Path, root: Path, budget: Budget) -> bytes:
        assert path != resource, "Discovery must not read a complete resource into memory"
        return original_read(path, root, budget)

    monkeypatch.setattr(discovery, "read_regular", metadata_only)
    tracemalloc.start()
    try:
        scan = discover([tmp_path])
        item = scan.mods[0].files[0]
        assert item.size == size
        assert item.report()["size"] == size
        assert item.kind == "binary"
        assert snapshot_unchanged(scan)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8 * 1024 * 1024
    assert scan.limits == SCAN_LIMITS
    assert len(item.content) == size
    assert digest(item.content) == item.sha256


def test_collection_over_old_aggregate_limit_uses_bounded_memory(tmp_path: Path) -> None:
    size = 129 * 1024 * 1024
    for name in ("one", "two"):
        mod = make_mod(tmp_path, name, {})
        _sparse_resource(mod, "textures/large.txtr", size)
    tracemalloc.start()
    try:
        scan = discover([tmp_path])
        assert sum(item.size for mod in scan.mods for item in mod.files) == 2 * size
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8 * 1024 * 1024


def test_lazy_content_rejects_same_size_source_change(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "changing", {"a.txt": b"original"})
    item = discover([tmp_path]).mods[0].files[0]
    (mod / "content/a.txt").write_bytes(b"modified")
    with pytest.raises(InputError, match="changed"):
        _ = item.content


def test_lazy_content_is_not_globally_cached(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "changing", {"a.txt": b"original"})
    item = discover([tmp_path]).mods[0].files[0]
    assert item.content == b"original"
    (mod / "content/a.txt").write_bytes(b"modified")
    with pytest.raises(InputError, match="changed"):
        _ = item.content


def test_file_ref_bytes_constructor_keeps_existing_contract() -> None:
    item = FileRef("a.txt", "a.txt", digest(b"value"), "text", b"value")
    assert item.content == b"value"
    assert item.size == 5
    assert item.report()["size"] == 5


def test_explicit_resource_limit_still_rejects_with_path_and_size(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "limited", {})
    _sparse_resource(mod, "textures/large.txtr", 129)
    with pytest.raises(InputError, match="file byte limit.*content/textures/large.txtr.*129.*128"):
        discover([tmp_path], limits=Limits(max_file_bytes=128))


def test_explicit_aggregate_limit_still_counts_metadata(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "limited", {"a.txt": b"a" * 20, "b.txt": b"b" * 20})
    total = len((mod / "mod.xml").read_bytes()) + 40
    with pytest.raises(InputError, match=f"total byte limit.*content/b.txt.*{total}.*{total - 1}"):
        discover([tmp_path], limits=Limits(max_total_bytes=total - 1))


def test_large_metadata_remains_rejected_without_loading(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "metadata", {})
    sparse_file(mod / "mod.xml", Limits().max_file_bytes + 1, b"<data/>")
    with pytest.raises(InputError, match="file byte limit.*mod.xml"):
        discover([tmp_path])


def test_resource_over_new_scan_bound_is_rejected_before_reading(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "oversized", {})
    _sparse_resource(mod, "textures/large.txtr", SCAN_LIMITS.max_file_bytes + 1)
    with pytest.raises(InputError, match="file byte limit.*content/textures/large.txtr"):
        discover([tmp_path])


def test_resource_changed_while_streaming_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    mod = make_mod(tmp_path, "changing", {"a.txt": b"original"})
    source = mod / "content/a.txt"
    inode = source.stat().st_ino
    original_fstat = filesystem.os.fstat
    changed = False

    def change_on_open(descriptor: int) -> os.stat_result:
        nonlocal changed
        info = original_fstat(descriptor)
        if info.st_ino == inode and not changed:
            changed = True
            source.write_bytes(b"modified")
            os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))
        return info

    monkeypatch.setattr(filesystem.os, "fstat", change_on_open)
    with pytest.raises(InputError, match="changed while reading"):
        discover([tmp_path])


@pytest.mark.parametrize("replacement", [b"", b"much longer replacement"])
def test_lazy_content_rejects_source_size_changes(tmp_path: Path, replacement: bytes) -> None:
    mod = make_mod(tmp_path, "changing", {"a.txt": b"original"})
    item = discover([tmp_path]).mods[0].files[0]
    (mod / "content/a.txt").write_bytes(replacement)
    with pytest.raises(InputError):
        _ = item.content


@pytest.mark.parametrize("link_ancestor", [False, True])
def test_lazy_content_rechecks_root_and_ancestor_links(tmp_path: Path, link_ancestor: bool) -> None:
    collection = tmp_path / "collection"
    mod = make_mod(collection, "changing", {"a.txt": b"original"})
    item = discover([collection]).mods[0].files[0]
    linked = collection if link_ancestor else mod
    original = tmp_path / "original"
    linked.rename(original)
    try:
        linked.symlink_to(original, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(InputError, match="link"):
        _ = item.content
