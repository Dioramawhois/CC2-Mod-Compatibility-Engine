import hashlib
import io
import zipfile

import pytest

from tools.windows_tool_archive import unpack_verified


def archive(name, data=b"tool"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as stream:
        entry = zipfile.ZipInfo(name)
        entry.filename = name
        entry.orig_filename = name
        stream.writestr(entry, data)
    return output.getvalue()


def test_pinned_tools_reject_wrong_hash_before_writing(tmp_path):
    payload = archive("tools_data/git/git.exe")
    with pytest.raises(ValueError):
        unpack_verified(payload, "0" * 64, tmp_path / "tools")
    assert not (tmp_path / "tools").exists()


@pytest.mark.parametrize(
    "name", ["tools_data/../escape", "tools_data/C:/escape", "other/tool", "tools_data/a\\b"]
)
def test_pinned_tools_reject_traversal_and_foreign_roots(tmp_path, name):
    payload = archive(name)
    with pytest.raises(ValueError):
        unpack_verified(payload, hashlib.sha256(payload).hexdigest(), tmp_path / "tools")
    assert not (tmp_path / "escape").exists()


def test_pinned_tools_restore_exact_bytes_without_developer_git(tmp_path):
    payload = archive("tools_data/git/git.exe", b"pinned bytes")
    unpack_verified(payload, hashlib.sha256(payload).hexdigest(), tmp_path / "tools")
    assert (tmp_path / "tools/git/git.exe").read_bytes() == b"pinned bytes"
