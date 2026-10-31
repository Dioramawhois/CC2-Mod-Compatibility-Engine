from pathlib import Path

import pytest

from cc2_mce.discovery import discover, snapshot_unchanged
from cc2_mce.errors import InputError
from cc2_mce.filesystem import Limits, normalize_logical_path


@pytest.mark.parametrize(
    "value",
    [
        "../evil",
        "/absolute",
        "C:/evil",
        "C:evil",
        "//server/share",
        "a\\b",
        "a//b",
        "a/./b",
        "a/../b",
        "a\x00b",
        "CON.txt",
        "aux",
        "LPT1.lua",
        "name.",
        "a /b",
        "a:b",
        "a?b",
        "a*b",
        "a|b",
        "a<b",
        "a>b",
        'a"b',
        "",
    ],
)
def test_unsafe_logical_paths(value: str) -> None:
    with pytest.raises(InputError):
        normalize_logical_path(value)


def test_unicode_and_case_keys_are_host_independent() -> None:
    assert normalize_logical_path("Scripts/CAFÉ.lua")[1] == "scripts/café.lua"
    assert normalize_logical_path("scripts/cafe\u0301.lua")[1] == "scripts/café.lua"


def make_mod(root: Path, name: str, files: dict[str, bytes]) -> Path:
    mod = root / name
    (mod / "content").mkdir(parents=True)
    (mod / "mod.xml").write_bytes(b'<data name="Synthetic"/>')
    for path, data in files.items():
        target = mod / "content" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return mod


def test_scan_deterministic_metadata_not_game_resource(tmp_path: Path) -> None:
    make_mod(tmp_path, "b", {"scripts/a.lua": b"return 2\n"})
    make_mod(tmp_path, "a", {"scripts/a.lua": b"return 1\n"})
    scan = discover([tmp_path])
    assert [mod.id for mod in scan.mods] == ["a", "b"]
    assert [item.logical_path for item in scan.mods[0].files] == ["scripts/a.lua"]
    assert scan.mods[0].name == "Synthetic"
    assert discover([tmp_path]).fingerprint == scan.fingerprint
    assert snapshot_unchanged(scan)
    (tmp_path / "a/content/scripts/a.lua").write_bytes(b"return 3\n")
    assert not snapshot_unchanged(scan)


def test_case_alias_between_mods_rejected(tmp_path: Path) -> None:
    make_mod(tmp_path, "a", {"Scripts/a.lua": b"return 1"})
    make_mod(tmp_path, "b", {"scripts/a.lua": b"return 2"})
    with pytest.raises(InputError, match="collision"):
        discover([tmp_path])


def test_binary_and_native_detection(tmp_path: Path) -> None:
    make_mod(tmp_path, "a", {"cc2x/demo.dll": b"MZ", "pic.png": b"\x89PNG\r\n"})
    mod = discover([tmp_path]).mods[0]
    assert mod.files[0].kind == "native"
    assert mod.files[1].kind == "binary"


def test_xml_entities_not_read(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "a", {})
    (mod / "mod.xml").write_bytes(b'<!DOCTYPE data [<!ENTITY x SYSTEM "file:///secret">]><data/>')
    with pytest.raises(InputError, match="XML"):
        discover([tmp_path])


def test_observed_leading_whitespace_xml_header(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "a", {})
    (mod / "mod.xml").write_bytes(b'\r\n<?xml version="1.0"?><data name="Real layout"/>')
    assert discover([tmp_path]).mods[0].name == "Real layout"


def test_symlink_rejected(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "a", {})
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    try:
        (mod / "content/link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(InputError, match="link"):
        discover([tmp_path])


def test_file_limit(tmp_path: Path) -> None:
    make_mod(tmp_path, "a", {"a.txt": b"hello"})
    with pytest.raises(InputError, match="limit"):
        discover([tmp_path], limits=Limits(max_file_bytes=2))


def test_added_file_invalidates_snapshot(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "a", {"a.txt": b"hello"})
    scan = discover([tmp_path])
    (mod / "content/b.txt").write_bytes(b"new")
    assert not snapshot_unchanged(scan)


def test_single_mod_root_and_empty_collection(tmp_path: Path) -> None:
    mod = make_mod(tmp_path, "a", {})
    assert discover([mod]).mods[0].id == "a"
    assert discover([]).mods == ()


def test_duplicate_mod_ids_rejected(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    make_mod(left, "a", {})
    make_mod(right, "a", {})
    with pytest.raises(InputError, match="Duplicate"):
        discover([left, right])
