"""Publish the verified Windows EXE and maintain the mutable latest-beta alias.

The numbered release and its tag are append-only: only a missing, byte-identical
EXE/checksum may be added. The separate, explicitly managed prerelease mirrors
every source asset. Its refs/tags/latest-beta ref may advance to the exact source
commit; main and versioned refs are never changed. This rolling download address
has changing contents and must not be made immutable. GitHub has no atomic asset
replacement, so interrupted channel updates are repaired by rerunning this tool.
Nothing is published merely by importing this module.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Any

REPOSITORY = "Dioramawhois/CC2-ModLoader"
CHANNEL_TAG = "latest-beta"
MANAGED_MARKER = "<!-- CC2ModLoader latest-beta: managed by tools/publish_latest_beta.py -->"
EXECUTABLE = "CC2ModLoader.exe"
CHECKSUM = EXECUTABLE + ".sha256"
MAX_ASSET_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ZIP_BYTES = 128 * 1024 * 1024
MAX_ZIP_MEMBERS = 4096
MAX_ZIP_TOTAL_BYTES = 512 * 1024 * 1024
MAX_ASSETS = 128
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def beta_version(tag: str) -> tuple[int, int, int, int]:
    """Accept only canonical numbered beta tags, and compare them numerically."""
    number = r"(0|[1-9][0-9]*)"
    if not isinstance(tag, str) or len(tag) > 100:
        raise ValueError("Expected a numbered beta tag such as v0.4.0b4")
    match = re.fullmatch(rf"v{number}\.{number}\.{number}b{number}", tag)
    if match is None:
        raise ValueError("Expected a numbered beta tag such as v0.4.0b4")
    major, minor, patch, beta = (int(value) for value in match.groups())
    return major, minor, patch, beta


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Invalid JSON metadata") from error
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def extract_executable(archive: bytes, tag: str, commit: str) -> bytes:
    """Read a bounded ZIP without extraction or execution, checking provenance."""
    beta_version(tag)
    if not COMMIT.fullmatch(commit) or len(archive) > MAX_ZIP_BYTES:
        raise ValueError("Invalid source commit or oversized Windows ZIP")
    # Bound the central directory before ZipFile allocates one object per member.
    end = archive.rfind(b"PK\x05\x06", max(0, len(archive) - 65557))
    if end < 0 or len(archive) < end + 22:
        raise ValueError("Missing ZIP end record")
    disk, directory_disk, disk_count, count, size, offset, comment = struct.unpack_from(
        "<4H2LH", archive, end + 4
    )
    if (
        disk
        or directory_disk
        or disk_count != count
        or count > MAX_ZIP_MEMBERS
        or offset + size != end
        or end + 22 + comment != len(archive)
    ):
        raise ValueError("Unsupported or oversized ZIP directory")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            entries = bundle.infolist()
            if (
                len(entries) != count
                or sum(item.file_size for item in entries) > MAX_ZIP_TOTAL_BYTES
            ):
                raise ValueError("Oversized Windows ZIP contents")
            seen: set[str] = set()
            for item in entries:
                # orig_filename retains NUL/backslashes normalized by ZipInfo on Windows.
                original = item.orig_filename
                name = original.rstrip("/")
                mode = stat.S_IFMT(item.external_attr >> 16)
                if (
                    original != item.filename
                    or not name
                    or any(character in original for character in ("\\", ":", "\x00"))
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or name.casefold() in seen
                    or mode not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or item.flag_bits & 1
                    or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or item.file_size > MAX_ASSET_BYTES
                ):
                    raise ValueError("Unsafe or unsupported Windows ZIP member")
                seen.add(name.casefold())
            report_info = bundle.getinfo("RELEASE.json")
            exe_info = bundle.getinfo(EXECUTABLE)
            if report_info.file_size > MAX_JSON_BYTES or not exe_info.file_size:
                raise ValueError("Invalid executable or release report size")
            report = _object(bundle.read(report_info))
            payload = bundle.read(exe_info)
    except (zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError) as error:
        raise ValueError("Invalid Windows ZIP") from error
    if (
        report.get("version") != tag[1:]
        or report.get("source_commit") != commit
        or report.get("artifact_sha256") != digest(payload)
    ):
        raise ValueError("Windows ZIP version, source commit or executable hash mismatch")
    return payload


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        # Authenticated API requests must never forward the token to another host.
        return None


def _read(response: Any, limit: int) -> bytes:
    length = response.headers.get("Content-Length")
    if length is not None and (not length.isdigit() or int(length) > limit):
        raise ValueError("Oversized HTTP response")
    data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Oversized HTTP response")
    return data


def _asset(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Invalid GitHub asset metadata")
    name, size, identifier = value.get("name"), value.get("size"), value.get("id")
    checksum = value.get("digest", "")
    if (
        not isinstance(name, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,199}", name) is None
        or type(size) is not int
        or not 0 <= size <= MAX_ASSET_BYTES
        or type(identifier) is not int
        or identifier <= 0
        or not isinstance(checksum, str)
        or not checksum.startswith("sha256:")
        or not SHA256.fullmatch(checksum[7:])
        or value.get("state") != "uploaded"
    ):
        raise ValueError("Invalid, unfinished or unverified GitHub asset")
    return value


def _asset_snapshot(assets: dict[str, dict[str, Any]]) -> dict[str, tuple[Any, ...]]:
    # Downloads change counters/timestamps, not an asset's verified identity.
    return {
        name: (item["id"], item["size"], item["digest"], item["state"])
        for name, item in assets.items()
    }


class GitHub:
    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        self.token = token
        self.opener = urllib.request.build_opener(_NoRedirect())

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        missing: bool = False,
        payload: bytes | None = None,
    ) -> Any:
        host = "uploads.github.com" if payload is not None else "api.github.com"
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CC2ModLoader-latest-beta",
        }
        if payload is not None:
            headers["Content-Type"] = "application/octet-stream"
        elif body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"https://{host}/repos/{REPOSITORY}/{path}",
            data=payload,
            headers=headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=60) as response:
                data = _read(response, MAX_JSON_BYTES)
        except urllib.error.HTTPError as error:
            if missing and error.code == 404:
                return None
            raise RuntimeError(f"GitHub {method} {path}: HTTP {error.code}") from None
        return json.loads(data) if data else None

    def release(self, tag: str) -> dict[str, Any] | None:
        return self.request("GET", "releases/tags/" + tag, missing=True)

    def assets(self, release: dict[str, Any]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()
        for page in range(1, 4):
            values = self.request(
                "GET", f"releases/{release['id']}/assets?per_page=100&page={page}"
            )
            if not isinstance(values, list):
                raise ValueError("Invalid asset listing")
            for value in values:
                item = _asset(value)
                if item["name"].casefold() in seen or len(result) >= MAX_ASSETS:
                    raise ValueError("Duplicate or excessive release assets")
                seen.add(item["name"].casefold())
                result[item["name"]] = item
            if len(values) < 100:
                return result
        raise ValueError("Excessive release assets")

    def download(self, item: dict[str, Any], tag: str) -> bytes:
        item = _asset(item)
        # Asset-ID downloads also work before a new channel draft is published.
        request = urllib.request.Request(
            f"https://api.github.com/repos/{REPOSITORY}/releases/assets/{item['id']}",
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/octet-stream",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "CC2ModLoader-latest-beta",
            },
        )
        for attempt in range(3):
            try:
                try:
                    response = self.opener.open(request, timeout=60)
                except urllib.error.HTTPError as redirect:
                    if redirect.code not in (301, 302, 303, 307, 308):
                        raise
                    location = redirect.headers.get("Location", "")
                    target = urllib.parse.urlsplit(location)
                    if (
                        target.scheme != "https"
                        or target.hostname != "release-assets.githubusercontent.com"
                        or target.username is not None
                        or target.password is not None
                        or target.port not in (None, 443)
                    ):
                        raise ValueError("Refusing an unexpected asset-download redirect") from None
                    # Never forward GitHub credentials to a redirected asset host.
                    response = urllib.request.urlopen(location, timeout=60)
                with response:
                    data = _read(response, item["size"])
                break
            except urllib.error.HTTPError as error:
                if attempt == 2 or error.code not in (404, 502, 503, 504):
                    raise RuntimeError(f"Download {item['name']}: HTTP {error.code}") from None
                time.sleep(attempt + 1)
        if len(data) != item["size"] or "sha256:" + digest(data) != item["digest"]:
            raise ValueError("Downloaded asset size/hash mismatch: " + item["name"])
        return data

    def put_asset(
        self,
        release: dict[str, Any],
        assets: dict[str, dict[str, Any]],
        name: str,
        payload: bytes,
        *,
        replace: bool,
    ) -> None:
        if len(payload) > MAX_ASSET_BYTES:
            raise ValueError("Oversized upload")
        previous = assets.get(name)
        if previous is not None:
            if previous["digest"] == "sha256:" + digest(payload) and previous["size"] == len(
                payload
            ):
                self.download(previous, release["tag_name"])
                return
            if not replace:
                raise ValueError("Refusing to overwrite a differing versioned asset: " + name)
            self.request("DELETE", f"releases/assets/{previous['id']}")
        elif release.get("immutable"):
            raise ValueError("Cannot add assets to an immutable versioned release")
        item = _asset(
            self.request(
                "POST",
                f"releases/{release['id']}/assets?name=" + urllib.parse.quote(name, safe=""),
                payload=payload,
            )
        )
        if item["name"] != name or item["digest"] != "sha256:" + digest(payload):
            raise ValueError("Uploaded asset metadata mismatch: " + name)
        self.download(item, release["tag_name"])
        assets[name] = item


def _managed(release: dict[str, Any]) -> None:
    if (
        release.get("tag_name") != CHANNEL_TAG
        or MANAGED_MARKER not in (release.get("body") or "")
        or release.get("prerelease") is not True
        or release.get("immutable") is not False
    ):
        raise ValueError("Refusing an unknown, non-beta or immutable latest-beta release")


def publish(github: GitHub, tag: str) -> None:
    version = beta_version(tag)
    source = github.release(tag)
    if (
        source is None
        or source.get("tag_name") != tag
        or source.get("draft") is not False
        or source.get("prerelease") is not True
    ):
        raise ValueError("The source must be a published numbered beta release")
    commit = github.request("GET", "commits/" + tag).get("sha", "")
    if not COMMIT.fullmatch(commit):
        raise ValueError("Invalid source commit")
    alias = github.release(CHANNEL_TAG)
    alias_assets: dict[str, dict[str, Any]] = {}
    previous_channel: bytes | None = None
    ref = github.request("GET", "git/ref/tags/" + CHANNEL_TAG, missing=True)
    if alias is not None:
        _managed(alias)
        alias_assets = github.assets(alias)
        metadata = alias_assets.get("CHANNEL.json", alias_assets.get("CHANNEL.previous.json"))
        if metadata is not None:
            previous_channel = github.download(metadata, CHANNEL_TAG)
            previous = _object(previous_channel)
            previous_version = beta_version(previous.get("source_tag", ""))
            if version < previous_version:
                print("Skipping an older beta; the rolling channel is already newer.")
                return
            if version == previous_version and previous.get("source_commit") != commit:
                raise ValueError("The versioned source commit changed")
        elif alias.get("draft") is not True:
            raise ValueError("Published managed channel has no downgrade-prevention metadata")
    elif ref is not None:
        raise ValueError("Refusing an existing latest-beta tag without a managed release")

    source_assets = github.assets(source)
    if source_assets.keys() & {"CHANNEL.json", "CHANNEL.previous.json"}:
        raise ValueError("Channel metadata names are reserved for the rolling alias")
    if sum(item["size"] for item in source_assets.values()) > MAX_TOTAL_BYTES:
        raise ValueError("Release assets exceed the total download limit")
    payloads = {name: github.download(item, tag) for name, item in source_assets.items()}
    windows = f"CC2ModLoader-{tag[1:]}-windows-x64.zip"
    if windows not in payloads or "SHA256SUMS.txt" not in payloads:
        raise ValueError("The Windows ZIP and original checksums are required")
    executable = extract_executable(payloads[windows], tag, commit)
    for line in payloads["SHA256SUMS.txt"].decode("ascii").splitlines():
        checksum, separator, name = line.partition("  ")
        if not separator or not SHA256.fullmatch(checksum) or name not in payloads:
            raise ValueError("Invalid original SHA256SUMS.txt entry")
        if digest(payloads[name]) != checksum:
            raise ValueError("Original release checksum mismatch: " + name)
    additions = {
        EXECUTABLE: executable,
        CHECKSUM: (digest(executable) + "  " + EXECUTABLE + "\n").encode("ascii"),
    }
    for name, payload in additions.items():
        if name in payloads and payloads[name] != payload:
            raise ValueError("Differing standalone versioned asset: " + name)
    # Refuse stale snapshots before the first mutation. Existing source bytes stay intact.
    if _asset_snapshot(github.assets(source)) != _asset_snapshot(source_assets):
        raise ValueError("Source release assets changed during verification")
    if github.request("GET", "commits/" + tag).get("sha") != commit:
        raise ValueError("Source tag changed during verification")
    for name, payload in additions.items():
        github.put_asset(source, source_assets, name, payload, replace=False)
        payloads[name] = payload
    if _asset_snapshot(github.assets(source)) != _asset_snapshot(source_assets):
        raise ValueError("Source release assets changed during standalone publication")

    body = (
        MANAGED_MARKER
        + "\n\nLatest Windows beta, currently **"
        + tag[1:]
        + "**. This mutable channel mirrors the verified [numbered release]("
        + source["html_url"]
        + ").\n\nExact source commit: `"
        + commit
        + "`. The beta's documented acceptance limits still apply.\n"
    )
    if alias is None:
        alias = github.request(
            "POST",
            "releases",
            {
                "tag_name": CHANNEL_TAG,
                "target_commitish": commit,
                "draft": True,
                "prerelease": True,
                "make_latest": "false",
                "body": body,
                "name": "Latest Windows beta — " + tag[1:],
            },
        )
        _managed(alias)
    for name, payload in payloads.items():
        github.put_asset(alias, alias_assets, name, payload, replace=True)
    if ref is None:
        # Draft creation may already have created the ref; never assume either behavior.
        ref = github.request("GET", "git/ref/tags/" + CHANNEL_TAG, missing=True)
    if ref is None:
        github.request("POST", "git/refs", {"ref": "refs/tags/" + CHANNEL_TAG, "sha": commit})
    elif ref.get("object", {}).get("sha") != commit:
        github.request("PATCH", "git/refs/tags/" + CHANNEL_TAG, {"sha": commit, "force": True})
    channel = {
        "schema_version": 1,
        "source_tag": tag,
        "source_release_url": source["html_url"],
        "source_commit": commit,
        "executable_sha256": digest(executable),
        "assets": {name: digest(payload) for name, payload in sorted(payloads.items())},
    }
    channel_payload = (json.dumps(channel, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if previous_channel is not None and previous_channel != channel_payload:
        # Retain downgrade metadata across GitHub's delete/upload replacement gap.
        github.put_asset(
            alias, alias_assets, "CHANNEL.previous.json", previous_channel, replace=True
        )
    github.put_asset(alias, alias_assets, "CHANNEL.json", channel_payload, replace=True)
    for name in alias_assets.keys() - payloads.keys() - {"CHANNEL.json"}:
        github.request("DELETE", f"releases/assets/{alias_assets[name]['id']}")
    github.request(
        "PATCH",
        f"releases/{alias['id']}",
        {
            "name": "Latest Windows beta — " + tag[1:],
            "body": body,
            "draft": False,
            "prerelease": True,
            "make_latest": "false",
        },
    )
    final = github.release(CHANNEL_TAG)
    if final is None:
        raise ValueError("Published channel is missing")
    _managed(final)
    if final.get("draft") is not False:
        raise ValueError("Managed channel is still a draft")
    expected = {**payloads, "CHANNEL.json": channel_payload}
    final_assets = github.assets(final)
    if final_assets.keys() != expected.keys():
        raise ValueError("Published channel asset set mismatch")
    for name, payload in expected.items():
        if github.download(final_assets[name], CHANNEL_TAG) != payload:
            raise ValueError("Published channel content mismatch: " + name)
    final_ref = github.request("GET", "git/ref/tags/" + CHANNEL_TAG)
    if final_ref.get("object", {}).get("sha") != commit:
        raise ValueError("Published channel tag does not match the source commit")
    print(
        f"Verified beta download: https://github.com/{REPOSITORY}/releases/download/"
        f"{CHANNEL_TAG}/{EXECUTABLE}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Published beta tag, for example v0.4.0b4")
    args = parser.parse_args()
    try:
        beta_version(args.tag)
        publish(GitHub(os.environ.get("GITHUB_TOKEN", "")), args.tag)
    except (ValueError, RuntimeError, urllib.error.URLError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
