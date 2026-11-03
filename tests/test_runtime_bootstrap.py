import hashlib
import io
import json
import os
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from cc2_mce.errors import InputError
from tools.prepare_windows_runtime import install_pinned_runtime


@pytest.fixture
def runtime_source(tmp_path):
    payload = b"reviewed SDK dependency fixture, never executed"
    digest = hashlib.sha256(payload).hexdigest()
    (tmp_path / "distribution").mkdir()
    (tmp_path / "distribution/windows-runtime.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "file": "dinput8.dll",
                "url": "https://github.com/Dioramawhois/Carrier-Command-2-extender/releases/download/0.6.0-client-beta.1/dinput8.dll",
                "sha256": digest,
                "bytes": len(payload),
            }
        )
    )
    profile = tmp_path / "cc2_mce/profiles/windows-1.5.18-r2.json"
    profile.parent.mkdir(parents=True)
    profile.write_text(json.dumps({"runtime_sha256": digest}))
    folder = tmp_path / "cc2_mce/runtime_data" / digest
    folder.mkdir(parents=True)
    supplied = tmp_path / "downloaded-runtime.dll"
    supplied.write_bytes(payload)
    return tmp_path, supplied, folder / "dinput8.dll", payload


def test_source_build_restores_only_the_pinned_runtime_without_an_sdk_checkout(runtime_source):
    root, supplied, destination, payload = runtime_source
    install_pinned_runtime(root, supplied)
    assert destination.read_bytes() == payload
    assert supplied.read_bytes() == payload


def test_default_source_build_downloads_the_pinned_runtime(runtime_source, monkeypatch):
    root, _, destination, payload = runtime_source
    calls = []

    def download(url, **kwargs):
        calls.append((url, kwargs))
        return nullcontext(io.BytesIO(payload))

    monkeypatch.setattr("urllib.request.urlopen", download)
    install_pinned_runtime(root)
    assert destination.read_bytes() == payload
    assert calls[0][0].endswith("/0.6.0-client-beta.1/dinput8.dll")
    assert calls[0][1]["timeout"] <= 60


def test_existing_reviewed_runtime_needs_no_network(runtime_source, monkeypatch):
    root, _, destination, payload = runtime_source
    destination.write_bytes(payload)
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: pytest.fail("network"))
    install_pinned_runtime(root)
    assert destination.read_bytes() == payload


@pytest.mark.parametrize("existing", [b"unknown installed bytes", b""])
def test_source_build_preserves_unknown_existing_dependency(runtime_source, monkeypatch, existing):
    root, supplied, destination, _ = runtime_source
    destination.write_bytes(existing)
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: pytest.fail("network"))
    with pytest.raises(ValueError, match="existing"):
        install_pinned_runtime(root, supplied)
    assert destination.read_bytes() == existing


@pytest.mark.parametrize("corruption", ["checksum", "size", "profile"])
def test_source_build_rejects_changed_dependency_before_publishing(runtime_source, corruption):
    root, supplied, destination, payload = runtime_source
    if corruption == "checksum":
        supplied.write_bytes(b"x" * len(payload))
    elif corruption == "size":
        supplied.write_bytes(payload + b"extra")
    else:
        profile = root / "cc2_mce/profiles/windows-1.5.18-r2.json"
        profile.write_text(json.dumps({"runtime_sha256": "0" * 64}))
    with pytest.raises(ValueError):
        install_pinned_runtime(root, supplied)
    assert not destination.exists()
    assert not list(destination.parent.glob("*.tmp"))


def test_source_build_cleans_temporary_dependency_if_atomic_publication_fails(
    runtime_source, monkeypatch
):
    root, supplied, destination, _ = runtime_source

    def fail(*args, **kwargs):
        raise OSError("simulated publication failure")

    monkeypatch.setattr(os, "link", fail)
    with pytest.raises(OSError, match="publication"):
        install_pinned_runtime(root, supplied)
    assert not destination.exists()
    assert not list(destination.parent.glob("*.tmp"))


def test_source_build_preserves_a_file_created_by_another_writer(runtime_source, monkeypatch):
    root, supplied, destination, _ = runtime_source
    link = os.link

    def raced(source, target):
        destination.write_bytes(b"another writer")
        link(source, target)

    monkeypatch.setattr(os, "link", raced)
    with pytest.raises(ValueError, match="existing"):
        install_pinned_runtime(root, supplied)
    assert destination.read_bytes() == b"another writer"


def test_source_build_refuses_a_dependency_link(runtime_source):
    root, supplied, destination, payload = runtime_source
    try:
        destination.symlink_to(supplied)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(InputError, match="link"):
        install_pinned_runtime(root, supplied)
    assert destination.is_symlink() and supplied.read_bytes() == payload


def test_source_build_preserves_an_existing_temporary_path(runtime_source, monkeypatch):
    root, supplied, destination, _ = runtime_source
    temporary = destination.parent / ".dinput8-existing.tmp"
    temporary.write_bytes(b"existing temporary file")
    monkeypatch.setattr("uuid.uuid4", lambda: SimpleNamespace(hex="existing"))
    with pytest.raises(FileExistsError):
        install_pinned_runtime(root, supplied)
    assert temporary.read_bytes() == b"existing temporary file"
    assert not destination.exists()
