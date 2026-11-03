"""Release-channel integrity checks; fixture executable bytes are never run."""

import hashlib
import io
import json
import zipfile

import pytest

from tools.publish_latest_beta import beta_version, extract_executable


def release_zip(*, version="0.4.0b4", commit="a" * 40, digest=None):
    payload = b"fixture executable, never executed"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("CC2ModLoader.exe", payload)
        archive.writestr(
            "RELEASE.json",
            json.dumps(
                {
                    "version": version,
                    "source_commit": commit,
                    "artifact_sha256": digest or hashlib.sha256(payload).hexdigest(),
                }
            ),
        )
    return stream.getvalue(), payload


def test_beta_order_is_numeric():
    assert beta_version("v0.4.0b10") > beta_version("v0.4.0b4")
    assert beta_version("v0.5.0b1") > beta_version("v0.4.0b99")


@pytest.mark.parametrize("tag", ["main", "latest-beta", "v0.4.0", "../v0.4.0b4", "v0.4.0b4/other"])
def test_channel_cannot_target_a_branch_or_unreviewed_tag(tag):
    with pytest.raises(ValueError):
        beta_version(tag)


def test_standalone_executable_is_exactly_the_versioned_payload():
    archive, payload = release_zip()
    assert extract_executable(archive, "v0.4.0b4", "a" * 40) == payload


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "0.4.0b3"},
        {"commit": "b" * 40},
        {"digest": "0" * 64},
    ],
)
def test_wrong_version_source_or_payload_is_never_published(changes):
    archive, _ = release_zip(**changes)
    with pytest.raises(ValueError):
        extract_executable(archive, "v0.4.0b4", "a" * 40)
