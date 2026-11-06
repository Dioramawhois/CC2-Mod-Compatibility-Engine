"""Offline publisher-authenticated SDK updates. Never load native code."""

from __future__ import annotations

import base64
import binascii
import copy
import json
import os
import re
import struct
import uuid
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator

from cc2_mce.discovery import ModRef
from cc2_mce.errors import InputError
from cc2_mce.filesystem import Budget, Limits, bounded_children, digest, input_root, read_regular

DESCRIPTOR = "cc2x/runtime_update.json"
SIGNING_DOMAIN = b"CC2X runtime provider v1\n"
MAX_MANIFEST = 65536
MAX_RUNTIME = 8 * 1024 * 1024
SCHEMAS = Path(__file__).parent / "schemas"


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def trusted_keys() -> dict[str, bytes]:
    data = json.loads((Path(__file__).parent / "profiles/sdk-publishers.json").read_text())
    return {name: base64.b64decode(key, validate=True) for name, key in data["keys"].items()}


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate signed metadata key")
        result[key] = value
    return result


def verify(data: bytes, game_sha256: str) -> dict[str, Any]:
    try:
        if len(data) > MAX_MANIFEST:
            raise ValueError("Signed metadata exceeds its bound")
        value = json.loads(data, object_pairs_hook=_unique)
        schema = json.loads((SCHEMAS / "runtime-provider.schema.json").read_text())
        if not Draft202012Validator(schema).is_valid(value):
            raise ValueError("Invalid signed provider contract")
        key = trusted_keys().get(value["key_id"])
        if key is None:
            raise ValueError("Unknown SDK publisher key")
        signature = base64.b64decode(value["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(key).verify(
            signature, SIGNING_DOMAIN + canonical(value["payload"])
        )
        if value["payload"]["game_sha256"] != game_sha256:
            raise ValueError("SDK release targets a different game executable")
        return value  # type: ignore[no-any-return]
    except (
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
        InvalidSignature,
        binascii.Error,
    ) as exc:
        raise InputError("SDK publisher verification failed: " + str(exc)) from exc


def validate_binary(data: bytes, payload: dict[str, Any]) -> None:
    if len(data) != payload["runtime_bytes"] or digest(data) != payload["runtime_sha256"]:
        raise InputError("SDK DLL does not match its signed release")
    try:
        offset = struct.unpack_from("<I", data, 0x3C)[0]
        if (
            data[:2] != b"MZ"
            or data[offset : offset + 4] != b"PE\0\0"
            or struct.unpack_from("<H", data, offset + 4)[0] != 0x14C
            or not struct.unpack_from("<H", data, offset + 22)[0] & 0x2000
            or struct.unpack_from("<H", data, offset + 24)[0] != 0x10B
        ):
            raise ValueError("Not a Windows PE32 DLL")
    except (ValueError, struct.error) as exc:
        raise InputError("Invalid signed SDK DLL architecture") from exc


def _cache(user: Path) -> Path:
    return user / "cc2-mce/runtime-providers"


def cached(user: Path, game_sha256: str) -> list[dict[str, Any]]:
    folder = _cache(user)
    if not folder.exists() and not folder.is_symlink():
        return []
    root = input_root(folder)
    budget = Budget(
        Limits(max_entries=256, max_file_bytes=MAX_MANIFEST, max_total_bytes=256 * MAX_MANIFEST)
    )
    result = []
    for path in bounded_children(root, budget):
        if re.fullmatch(r"[0-9a-f]{64}\.json", path.name) is None:
            continue
        try:
            data = read_regular(path, root, budget)
            if digest(data) == path.stem:
                result.append(verify(data, game_sha256))
        except (InputError, OSError):
            # An invalid unrelated cache entry grants no approval. A selected
            # source is verified strictly, and unknown installed bytes still fail.
            continue
    return result


def select(
    game_root: Path,
    chosen: tuple[ModRef, ...],
    base: dict[str, Any],
    user: Path,
    available: tuple[ModRef, ...] = (),
) -> tuple[dict[str, Any], Path | None]:
    profile = copy.deepcopy(base)
    profile.pop("runtime_provider_source", None)
    game_hash = profile["game_sha256"]
    receipts = cached(user, game_hash)
    sources: dict[str, Path] = {}
    source_records: dict[str, dict[str, str]] = {}
    required = {mod.id for mod in chosen}
    candidates = {mod.id: mod for mod in (*available, *chosen)}
    for mod in candidates.values():
        descriptors = [item for item in mod.files if item.key == DESCRIPTOR]
        if not descriptors:
            continue
        try:
            if (
                mod.package_kind != "library"
                or mod.package_id != "cc2x.runtime"
                or mod.sdk != "cc2x"
            ):
                raise InputError("SDK release metadata belongs to a different package")
            if descriptors[0].size > MAX_MANIFEST:
                raise InputError("Signed SDK manifest exceeds its bound")
            envelope = verify(descriptors[0].content, game_hash)
            binary = next((item for item in mod.files if item.key == "dinput8.dll"), None)
            if binary is None or binary.size > MAX_RUNTIME:
                raise InputError("Signed SDK package has no bounded runtime DLL")
            validate_binary(binary.content, envelope["payload"])
        except InputError:
            if mod.id in required:
                raise
            continue  # An unselected invalid download cannot reject a working set.
        receipts.append(envelope)
        sources[envelope["payload"]["runtime_sha256"]] = mod.root / "content" / binary.logical_path
        source_records[envelope["payload"]["runtime_sha256"]] = {
            "id": mod.id,
            "sha256": mod.sha256,
            "runtime_sha256": binary.sha256,
        }
    installed = game_root / "dinput8.dll"
    installed_hash = None
    if receipts and (installed.exists() or installed.is_symlink()):
        try:
            installed_hash = digest(
                read_regular(installed, input_root(game_root), Budget(Limits()))
            )
        except (InputError, OSError):
            pass  # The normal runtime guard reports this only when an SDK is required.
    eligible = [
        value
        for value in receipts
        if value["payload"]["runtime_sha256"] in sources
        or value["payload"]["runtime_sha256"] == installed_hash
    ]
    identities: dict[int, str] = {}
    allowed = {profile.get("runtime_sha256"), *profile.get("previous_runtime_sha256", [])}
    for envelope in receipts:
        payload = envelope["payload"]
        sequence, runtime_hash = payload["sequence"], payload["runtime_sha256"]
        identity = digest(canonical(payload))
        if sequence in identities and identities[sequence] != identity:
            raise InputError("Ambiguous signed SDK release sequence")
        identities[sequence] = identity
        allowed.update([runtime_hash, *payload["previous_runtime_sha256"]])
    sequence = profile.get("runtime_provider", {}).get("payload", {}).get("sequence", 0)
    if eligible:
        envelope = max(eligible, key=lambda value: value["payload"]["sequence"])
        payload = envelope["payload"]
        if payload["sequence"] >= sequence:
            profile.update(
                runtime_sha256=payload["runtime_sha256"],
                runtime_api=payload["api"],
                runtime_lua_api=payload["lua_api"],
                runtime_framework_api=payload["framework_api"],
                runtime_capabilities=payload["capabilities"],
                runtime_provider=envelope,
            )
            profile["runtime_review"] = {
                "stage": "publisher-signed",
                "runtime_version": payload["version"],
                "source_commit": payload["source_commit"],
                "publisher_key": envelope["key_id"],
                "verified_scope": ["publisher-signature", "exact-game-and-runtime-hashes"],
                "unverified_scope": ["full-gameplay", "remote-multiplayer", "dedicated-server"],
                "multiplayer_verified": False,
                "dedicated_verified": False,
            }
    profile["previous_runtime_sha256"] = sorted(
        value for value in allowed if value and value != profile.get("runtime_sha256")
    )
    provider_hash = profile.get("runtime_sha256", "")
    if provider_hash in source_records:
        profile["runtime_provider_source"] = source_records[provider_hash]
    return profile, sources.get(provider_hash)


def remember(user: Path, envelope: dict[str, Any], game_sha256: str) -> None:
    data = canonical(envelope)
    verify(data, game_sha256)
    state = user / "cc2-mce"
    state.mkdir(exist_ok=True)
    input_root(state)
    folder = _cache(user)
    folder.mkdir(exist_ok=True)
    input_root(folder)
    target = folder / (digest(data) + ".json")
    if target.exists() or target.is_symlink():
        if read_regular(target, folder, Budget(Limits())) != data:
            raise InputError("Signed SDK receipt cache changed")
        return
    # Immutable approval evidence, separate from activation preference. It never
    # selects an absent/uninstalled runtime, including after Undo.
    temporary = folder / ("." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if read_regular(target, folder, Budget(Limits())) != data:
                raise InputError("Signed SDK receipt cache changed") from None
    finally:
        temporary.unlink(missing_ok=True)
