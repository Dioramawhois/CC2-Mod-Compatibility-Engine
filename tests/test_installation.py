import platform
from pathlib import Path

import pytest

from cc2_mce.errors import InputError
from cc2_mce.installation import find_installations, inspect_game, parse_vdf, prepare_collections


def game(root: Path, host: str | None = None) -> Path:
    host = host or platform.system()
    executable = root / (
        "carriercommand.app/Contents/MacOS/build_mac" if host == "Darwin" else "carrier_command.exe"
    )
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(b"synthetic executable; never run")
    return root


def manifest(library: Path, name: str = "Carrier Command 2", appid: str = "1489630") -> None:
    path = library / "steamapps/appmanifest_1489630.acf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'"AppState" {{ "appid" "{appid}" "installdir" "{name}" }}', encoding="utf-8")


def libraries(steam: Path, entries: dict[str, object]) -> None:
    path = steam / "steamapps/libraryfolders.vdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = []
    for key, value in entries.items():
        escaped = str(value).replace("\\", "\\\\")
        body.append(f'"{key}" {{ "path" "{escaped}" }}')
    path.write_text('"libraryfolders" { ' + " ".join(body) + " }", encoding="utf-8")


def test_adjacent_executable_has_priority_and_creates_nothing(tmp_path: Path) -> None:
    adjacent = game(tmp_path / "portable", "Windows")
    steam = tmp_path / "steam"
    other = game(steam / "steamapps/common/Carrier Command 2", "Windows")
    manifest(steam)
    result = find_installations(app_dir=adjacent, steam_roots=[steam], host="Windows")
    assert [item.root for item in result.games] == [adjacent, other]
    assert result.games[0].plugins_dir == adjacent / "cc2x/plugins"
    assert result.games[0].local_mods_dir == adjacent / "mods"
    assert not (adjacent / "cc2x").exists()
    assert not (adjacent / "mods").exists()


def test_secondary_library_cyrillic_spaces_and_workshop_without_copy(tmp_path: Path) -> None:
    steam = tmp_path / "steam"
    extra = tmp_path / "Библиотека игр"
    installed = game(extra / "steamapps/common/CC2 custom")
    manifest(extra, "CC2 custom")
    libraries(steam, {"0": steam, "1": extra, "2": extra})
    workshop = extra / "steamapps/workshop/content/1489630"
    workshop.mkdir(parents=True)
    (workshop / "123456").mkdir()
    result = find_installations(app_dir=tmp_path / "elsewhere", steam_roots=[steam])
    assert [item.root for item in result.games] == [installed]
    assert result.workshop_roots == (workshop,)
    assert list(workshop.iterdir()) == [workshop / "123456"]


def test_legacy_libraryfolders_and_mac_executable(tmp_path: Path) -> None:
    steam = tmp_path / "steam"
    extra = tmp_path / "Mac Library"
    installed = game(extra / "steamapps/common/Carrier Command 2", "Darwin")
    manifest(extra)
    path = steam / "steamapps/libraryfolders.vdf"
    path.parent.mkdir(parents=True)
    escaped = str(extra).replace("\\", "\\\\")
    path.write_text(f'"LibraryFolders" {{ "1" "{escaped}" }}', encoding="utf-8")
    result = find_installations(steam_roots=[steam], host="Darwin")
    assert result.games[0].root == installed
    assert result.games[0].executable.name == "build_mac"


@pytest.mark.parametrize("name", ["../outside", "/outside", "C:/outside", "a/b", "CON", ""])
def test_manifest_install_directory_cannot_escape_library(tmp_path: Path, name: str) -> None:
    manifest(tmp_path, name)
    result = find_installations(steam_roots=[tmp_path])
    assert not result.games
    assert result.warnings


def test_wrong_appid_or_missing_executable_is_not_an_installation(tmp_path: Path) -> None:
    game(tmp_path / "steamapps/common/Carrier Command 2")
    manifest(tmp_path, appid="999")
    assert not find_installations(steam_roots=[tmp_path]).games
    assert inspect_game(tmp_path / "missing", host="Windows") is None


@pytest.mark.parametrize(
    "text",
    [
        '"a" {',
        '"a" "b" "a" "c"',
        '"a" "b" }',
        '"a"',
        '"a" "unterminated',
        '"a" "\x00"',
        '"x" {' * 18 + '"a" "b"' + "}" * 18,
        '"a" "' + "x" * (1024 * 1024) + '"',
    ],
    ids=["open", "duplicate", "extra-close", "no-value", "string", "nul", "depth", "size"],
)
def test_malformed_ambiguous_or_oversized_vdf_fails_closed(text: str) -> None:
    with pytest.raises(InputError):
        parse_vdf(text)


def test_vdf_comments_backslashes_and_escaped_quotes() -> None:
    assert parse_vdf('// comment\n"a" "C:\\\\Games" "b" "a\\"b"') == {"a": "C:\\Games", "b": 'a"b'}


def test_malformed_library_does_not_hide_valid_adjacent_game(tmp_path: Path) -> None:
    adjacent = game(tmp_path / "game")
    path = tmp_path / "steam/steamapps/libraryfolders.vdf"
    path.parent.mkdir(parents=True)
    path.write_text('"libraryfolders" {', encoding="utf-8")
    result = find_installations(app_dir=adjacent, steam_roots=[tmp_path / "steam"])
    assert result.games[0].root == adjacent
    assert result.warnings


def test_linked_game_is_rejected(tmp_path: Path) -> None:
    source = game(tmp_path / "source", "Windows")
    link = tmp_path / "linked"
    try:
        link.symlink_to(source, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    assert inspect_game(link, host="Windows") is None


@pytest.mark.parametrize("host", ["Windows", "Darwin"])
def test_synthetic_game_layout_matches_selected_host(tmp_path: Path, host: str) -> None:
    root = game(tmp_path / host, host)
    assert inspect_game(root, host=host) is not None
    other = "Darwin" if host == "Windows" else "Windows"
    assert inspect_game(root, host=other) is None


def test_adjacent_steam_library_found_without_registry(tmp_path: Path) -> None:
    adjacent = game(tmp_path / "steamapps/common/Carrier Command 2")
    workshop = tmp_path / "steamapps/workshop/content/1489630"
    workshop.mkdir(parents=True)
    result = find_installations(app_dir=adjacent, steam_roots=[])
    assert result.games[0].root == adjacent
    assert result.workshop_roots == (workshop,)


def test_explicit_prepare_creates_only_engine_collections(tmp_path: Path) -> None:
    root = game(tmp_path / "game")
    installed = inspect_game(root)
    assert installed is not None
    prepare_collections(installed)
    prepare_collections(installed)
    assert {path.name for path in root.iterdir()} == {"carrier_command.exe", "mods", "libraries"}
    assert not list((root / "mods").iterdir())
    assert not list((root / "libraries").iterdir())


def test_invalid_collection_prevents_creation_of_other_directory(tmp_path: Path) -> None:
    root = game(tmp_path / "game")
    installed = inspect_game(root)
    assert installed is not None
    (root / "libraries").write_bytes(b"protected existing file")
    with pytest.raises(InputError):
        prepare_collections(installed)
    assert not (root / "mods").exists()
    assert (root / "libraries").read_bytes() == b"protected existing file"
