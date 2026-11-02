"""Bounded, read-only Steam and adjacent-game discovery; no mod execution."""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from cc2_mce.errors import InputError
from cc2_mce.filesystem import (
    Budget,
    Limits,
    input_root,
    is_link,
    normalize_logical_path,
    read_regular,
)

GAME_ID = "1489630"
type VDFValue = str | dict[str, VDFValue]


@dataclass(frozen=True)
class Installation:
    root: Path
    executable: Path

    @property
    def plugins_dir(self) -> Path:
        return self.root / "cc2x/plugins"

    @property
    def local_mods_dir(self) -> Path:
        # An Engine input collection, not a claim that CC2 loads this directory.
        return self.root / "mods"

    @property
    def libraries_dir(self) -> Path:
        return self.root / "libraries"


@dataclass(frozen=True)
class Installations:
    games: tuple[Installation, ...]
    workshop_roots: tuple[Path, ...]
    warnings: tuple[str, ...]


def parse_vdf(text: str) -> dict[str, VDFValue]:
    """Steam's quoted KeyValues subset, with strict syntax and resource limits."""
    if len(text.encode("utf-8")) > 1024 * 1024 or "\0" in text:
        raise InputError("Steam metadata exceeds limits")
    tokens: list[tuple[str, str]] = []
    cursor = 0
    while cursor < len(text):
        char = text[cursor]
        if char.isspace():
            cursor += 1
            continue
        if text.startswith("//", cursor):
            end = text.find("\n", cursor)
            cursor = len(text) if end < 0 else end + 1
            continue
        if char in "{}":
            tokens.append((char, char))
            cursor += 1
        elif char == '"':
            cursor += 1
            value = []
            while cursor < len(text) and text[cursor] != '"':
                if text[cursor] == "\\" and cursor + 1 < len(text):
                    next_char = text[cursor + 1]
                    if next_char in ('"', "\\"):
                        value.append(next_char)
                        cursor += 2
                        continue
                value.append(text[cursor])
                cursor += 1
            if cursor == len(text):
                raise InputError("Unterminated Steam metadata string")
            tokens.append(("string", "".join(value)))
            cursor += 1
        else:
            raise InputError("Unsupported Steam metadata syntax")
        if len(tokens) > 8192:
            raise InputError("Steam metadata token limit exceeded")

    index = 0

    def object_value(depth: int) -> dict[str, VDFValue]:
        nonlocal index
        if depth > 16:
            raise InputError("Steam metadata depth limit exceeded")
        result: dict[str, VDFValue] = {}
        while index < len(tokens):
            kind, key = tokens[index]
            index += 1
            if kind == "}":
                if depth == 0:
                    raise InputError("Unexpected Steam metadata brace")
                return result
            if kind != "string" or index == len(tokens) or key.casefold() in result:
                raise InputError("Ambiguous Steam metadata key")
            kind, value = tokens[index]
            index += 1
            if kind == "{":
                result[key.casefold()] = object_value(depth + 1)
            elif kind == "string":
                result[key.casefold()] = value
            else:
                raise InputError("Invalid Steam metadata value")
        if depth:
            raise InputError("Unclosed Steam metadata object")
        return result

    return object_value(0)


def _metadata(path: Path) -> dict[str, VDFValue]:
    root = input_root(path.parent)
    data = read_regular(path, root, Budget(Limits(max_file_bytes=1024 * 1024)))
    try:
        return parse_vdf(data.decode("utf-8-sig"))
    except UnicodeError as exc:
        raise InputError("Steam metadata is not UTF-8") from exc


def _directory(path: Path) -> Path | None:
    try:
        # Automatic discovery never probes a network share.
        if str(path).startswith(("\\\\", "//")) or not path.is_absolute():
            return None
        return input_root(path)
    except (InputError, OSError, ValueError):
        return None


def inspect_game(root: Path, *, host: str | None = None) -> Installation | None:
    directory = _directory(root)
    if directory is None:
        return None
    relative = (
        "carriercommand.app/Contents/MacOS/build_mac"
        if (host or platform.system()) == "Darwin"
        else "carrier_command.exe"
    )
    executable = directory / relative
    try:
        input_root(executable.parent)
        if is_link(executable) or not executable.is_file():
            return None
    except (InputError, OSError):
        return None
    # Presence establishes location only, never a trusted game build or baseline.
    return Installation(directory, executable)


def prepare_collections(installation: Installation) -> None:
    """Idempotently prepare only Engine input directories for the selected verified game."""
    root = input_root(installation.root)
    targets = [root / "mods", root / "libraries"]
    for target in targets:
        if target.exists() or target.is_symlink():
            input_root(target)
    for target in targets:
        try:
            target.mkdir()
        except FileExistsError:
            input_root(target)
        input_root(target)


def default_steam_roots() -> list[Path]:
    if sys.platform == "darwin":
        return [Path.home() / "Library/Application Support/Steam"]
    if sys.platform != "win32":
        return [Path.home() / ".steam/steam", Path.home() / ".local/share/Steam"]
    import winreg

    roots = []
    for hive, key, field in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ):
        try:
            with winreg.OpenKey(hive, key) as handle:
                value, _ = winreg.QueryValueEx(handle, field)
                if isinstance(value, str):
                    roots.append(Path(value))
        except OSError:
            continue
    roots.extend(
        Path(os.environ[key]) / "Steam"
        for key in ("PROGRAMFILES(X86)", "PROGRAMFILES")
        if key in os.environ
    )
    return list(dict.fromkeys(roots))


def find_installations(
    *,
    app_dir: Path | None = None,
    steam_roots: list[Path] | None = None,
    host: str | None = None,
) -> Installations:
    libraries: list[Path] = []
    warnings: list[str] = []

    def add_library(path: Path) -> None:
        directory = _directory(path)
        if directory is not None and directory not in libraries:
            if len(libraries) >= 64:
                raise InputError("Steam library limit exceeded")
            libraries.append(directory)

    for root in (default_steam_roots() if steam_roots is None else steam_roots)[:64]:
        try:
            add_library(root)
            if _directory(root) is None:
                continue
            metadata = root / "steamapps/libraryfolders.vdf"
            if not metadata.exists() and not metadata.is_symlink():
                continue
            entries = _metadata(metadata).get("libraryfolders")
            if not isinstance(entries, dict):
                raise InputError("Invalid Steam library list")
            for key, entry in entries.items():
                if not key.isascii() or not key.isdigit():
                    continue
                value = entry.get("path") if isinstance(entry, dict) else entry
                if not isinstance(value, str):
                    raise InputError("Invalid Steam library path")
                add_library(Path(value))
        except (InputError, OSError, ValueError):
            warnings.append("Не удалось безопасно прочитать список библиотек Steam.")

    games: list[Installation] = []
    if app_dir is not None:
        adjacent = inspect_game(app_dir, host=host)
        if adjacent is not None:
            games.append(adjacent)
            if (
                adjacent.root.parent.name.casefold() == "common"
                and adjacent.root.parent.parent.name.casefold() == "steamapps"
            ):
                try:
                    add_library(adjacent.root.parent.parent.parent)
                except InputError:
                    warnings.append("Достигнут предел числа библиотек Steam.")
    workshop: list[Path] = []
    for library in libraries:
        collection = _directory(library / f"steamapps/workshop/content/{GAME_ID}")
        if collection is not None and collection not in workshop:
            workshop.append(collection)
        manifest = library / f"steamapps/appmanifest_{GAME_ID}.acf"
        if not manifest.exists() and not manifest.is_symlink():
            continue
        try:
            state = _metadata(manifest).get("appstate")
            if not isinstance(state, dict) or state.get("appid") != GAME_ID:
                raise InputError("Steam manifest appid mismatch")
            name = state.get("installdir")
            if not isinstance(name, str) or "/" in name:
                raise InputError("Unsafe Steam installation directory")
            normalize_logical_path(name)
            installed = inspect_game(library / "steamapps/common" / name, host=host)
            if installed is not None and installed not in games:
                games.append(installed)
        except (InputError, OSError, ValueError):
            warnings.append("Не удалось безопасно проверить расположение Carrier Command 2.")
    return Installations(tuple(games), tuple(workshop), tuple(dict.fromkeys(warnings)))
