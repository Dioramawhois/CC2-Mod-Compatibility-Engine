"""Release-channel integrity checks; fixture executable bytes are never run."""

import hashlib
import io
import json
import zipfile

import pytest

from tools.publish_latest_beta import beta_version, extract_executable, standalone_assets


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


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_published_standalone_checksum_preserves_existing_bytes(newline):
    payload = b"fixture executable, never executed"
    checksum = hashlib.sha256(payload).hexdigest().encode("ascii")
    existing = {
        "CC2ModLoader.exe": payload,
        "CC2ModLoader.exe.sha256": checksum + b"  CC2ModLoader.exe" + newline,
    }
    assert standalone_assets(payload, existing) == existing


@pytest.mark.parametrize("present", ["none", "exe", "checksum"])
def test_missing_standalone_assets_use_canonical_lf(present):
    payload = b"fixture executable, never executed"
    checksum = hashlib.sha256(payload).hexdigest().encode("ascii")
    expected = {
        "CC2ModLoader.exe": payload,
        "CC2ModLoader.exe.sha256": checksum + b"  CC2ModLoader.exe\n",
    }
    existing = {"unrelated-release-asset.txt": b"untouched"}
    if present != "none":
        name = "CC2ModLoader.exe" if present == "exe" else "CC2ModLoader.exe.sha256"
        existing[name] = expected[name]
    before = existing.copy()
    assert standalone_assets(payload, existing) == expected
    assert existing == before


@pytest.mark.parametrize(
    "change",
    ["executable", "hash", "filename", "extra-line", "blank-line", "trailing-space"],
)
def test_differing_or_malformed_versioned_standalone_assets_are_rejected(change):
    payload = b"fixture executable, never executed"
    checksum = hashlib.sha256(payload).hexdigest().encode("ascii")
    sidecar = checksum + b"  CC2ModLoader.exe\n"
    existing = {"CC2ModLoader.exe": payload, "CC2ModLoader.exe.sha256": sidecar}
    if change == "executable":
        existing["CC2ModLoader.exe"] = b"different executable"
    elif change == "hash":
        existing["CC2ModLoader.exe.sha256"] = b"0" * 64 + b"  CC2ModLoader.exe\n"
    elif change == "filename":
        existing["CC2ModLoader.exe.sha256"] = checksum + b"  Other.exe\n"
    elif change == "extra-line":
        existing["CC2ModLoader.exe.sha256"] = sidecar + sidecar
    elif change == "blank-line":
        existing["CC2ModLoader.exe.sha256"] = sidecar + b"\n"
    else:
        existing["CC2ModLoader.exe.sha256"] = sidecar.rstrip(b"\n") + b" \n"
    before = existing.copy()
    with pytest.raises(ValueError):
        standalone_assets(payload, existing)
    assert existing == before
