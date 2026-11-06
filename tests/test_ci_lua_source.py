"""Offline download-boundary tests; owned placeholder bytes are never compiled."""

import hashlib
import io
import json
import stat
import warnings
import zipfile
from pathlib import Path
from urllib.error import URLError

import pytest

from tools import prepare_ci_lua

SOURCE_BYTES = 303770
MEMBER = "tools_data/notices/lua-5.3.6.tar.gz"
MIRROR = "https://example.invalid/pinned-tools.zip"


def _archive(
    source: bytes,
    *,
    name: str = MEMBER,
    duplicate: bool = False,
    attributes: int | None = None,
) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        entry = zipfile.ZipInfo(name)
        if attributes is not None:
            entry.external_attr = attributes
        archive.writestr(entry, source)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(name, source)
    return target.getvalue()


def _pin_archive(root: Path, payload: bytes) -> None:
    directory = root / "distribution"
    directory.mkdir(exist_ok=True)
    (directory / "windows-build-tools.json").write_text(
        json.dumps(
            {
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "url": MIRROR,
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def source(monkeypatch: pytest.MonkeyPatch) -> bytes:
    payload = b"Owned fetch-boundary fixture\n".ljust(SOURCE_BYTES, b".")
    monkeypatch.setattr(prepare_ci_lua, "SHA256", hashlib.sha256(payload).hexdigest())
    return payload


def _mirror_transport(
    monkeypatch: pytest.MonkeyPatch, payload: bytes, failure: OSError | None = None
) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []

    def fetch(url: str, *, timeout: int):
        calls.append((url, timeout))
        if url == prepare_ci_lua.URL:
            raise failure or URLError("Official source is unavailable")
        assert url == MIRROR
        return io.BytesIO(payload)

    monkeypatch.setattr(prepare_ci_lua.urllib.request, "urlopen", fetch)
    return calls


def test_production_source_pin_remains_the_official_lua_536_archive() -> None:
    assert prepare_ci_lua.SHA256 == (
        "fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60"
    )


def test_official_source_success_needs_no_fallback_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: bytes
) -> None:
    calls = []

    def fetch(url: str, *, timeout: int):
        calls.append((url, timeout))
        return io.BytesIO(source)

    monkeypatch.setattr(prepare_ci_lua.urllib.request, "urlopen", fetch)
    assert prepare_ci_lua.fetch_source(tmp_path) == source
    assert calls == [(prepare_ci_lua.URL, 45)]


@pytest.mark.parametrize(
    "failure", [URLError("offline"), TimeoutError("timeout"), OSError("reset")]
)
def test_transport_failure_uses_verified_source_from_pinned_tools_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: bytes, failure: OSError
) -> None:
    payload = _archive(source)
    _pin_archive(tmp_path, payload)
    calls = _mirror_transport(monkeypatch, payload, failure)
    assert prepare_ci_lua.fetch_source(tmp_path) == source
    assert calls == [(prepare_ci_lua.URL, 45), (MIRROR, 45)]


@pytest.mark.parametrize("corrupt", [False, True])
def test_official_integrity_failure_never_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: bytes, corrupt: bool
) -> None:
    payload = b"!" + source[1:] if corrupt else source + b"!"
    calls = []

    def fetch(url: str, *, timeout: int):
        calls.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr(prepare_ci_lua.urllib.request, "urlopen", fetch)
    with pytest.raises(ValueError, match="Lua source size/checksum"):
        prepare_ci_lua.fetch_source(tmp_path)
    assert calls == [prepare_ci_lua.URL]


@pytest.mark.parametrize("change", ["hash", "oversized", "truncated"])
def test_fallback_archive_is_verified_before_zip_is_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: bytes, change: str
) -> None:
    original = _archive(source)
    _pin_archive(tmp_path, original)
    payload = (
        b"!" + original[1:]
        if change == "hash"
        else original + b"!"
        if change == "oversized"
        else original[:-1]
    )
    _mirror_transport(monkeypatch, payload)
    monkeypatch.setattr(
        prepare_ci_lua.zipfile,
        "ZipFile",
        lambda *args, **kwargs: pytest.fail("Unverified ZIP must not be opened"),
    )
    with pytest.raises(ValueError, match="tool archive size/checksum"):
        prepare_ci_lua.fetch_source(tmp_path)


def test_correctly_pinned_non_zip_payload_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"Owned invalid archive fixture"
    _pin_archive(tmp_path, payload)
    _mirror_transport(monkeypatch, payload)
    with pytest.raises(zipfile.BadZipFile):
        prepare_ci_lua.fetch_source(tmp_path)


@pytest.mark.parametrize("problem", ["missing", "duplicate", "oversized"])
def test_fallback_requires_one_exact_bounded_source_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: bytes, problem: str
) -> None:
    payload = _archive(
        source + b"!" if problem == "oversized" else source,
        name="other/source.tar.gz" if problem == "missing" else MEMBER,
        duplicate=problem == "duplicate",
    )
    _pin_archive(tmp_path, payload)
    _mirror_transport(monkeypatch, payload)
    with pytest.raises(ValueError, match="Lua source member"):
        prepare_ci_lua.fetch_source(tmp_path)


@pytest.mark.parametrize(
    "attributes", [stat.S_IFLNK << 16, stat.S_IFDIR << 16, stat.S_IFIFO << 16, 16]
)
def test_fallback_rejects_nonregular_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: bytes, attributes: int
) -> None:
    payload = _archive(source, attributes=attributes)
    _pin_archive(tmp_path, payload)
    _mirror_transport(monkeypatch, payload)
    with pytest.raises(ValueError, match="Lua source member"):
        prepare_ci_lua.fetch_source(tmp_path)


def test_fallback_source_still_requires_the_exact_source_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: bytes
) -> None:
    payload = _archive(b"!" + source[1:])
    _pin_archive(tmp_path, payload)
    calls = _mirror_transport(monkeypatch, payload)
    with pytest.raises(ValueError, match="Lua source size/checksum"):
        prepare_ci_lua.fetch_source(tmp_path)
    assert len(calls) == 2
