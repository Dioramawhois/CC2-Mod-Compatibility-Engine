import copy
import json
import shutil
from pathlib import Path

import pytest

from cc2_mce.discovery import FileRef, discover
from cc2_mce.filesystem import digest
from tests.test_paths_discovery import make_mod

DESCRIPTOR = "cc2x/screen_extensions.json"
SOURCE = "cc2x/ui/shared.lua"
LUA = b'error("syntax check must never execute this helper")\n'
CAPABILITIES = ["screen-extensions-v1", "screen-source-edits-v1"]


def descriptor(schema=1, entries=None):
    return {
        "schema": schema,
        "extensions": entries
        if entries is not None
        else [{"screen": "scripts/screen_holomap.lua", "source": SOURCE}],
    }


def module(tmp_path: Path, name: str, value, *, sources=None):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    make_mod(tmp_path, name, {DESCRIPTOR: raw, **({SOURCE: LUA} if sources is None else sources)})
    return next(item for item in discover([tmp_path]).mods if item.id == name)


def prepare(selected, *, capabilities=None, luac=None):
    from cc2_mce.screen_extensions import prepare_screen_extensions

    return prepare_screen_extensions(
        tuple(selected),
        {"runtime_capabilities": CAPABILITIES if capabilities is None else capabilities},
        luac=luac,
    )


@pytest.fixture
def syntax_only(monkeypatch):
    # Most contract tests isolate syntax validation; one test below runs real luac -p.
    monkeypatch.setattr(
        "cc2_mce.screen_extensions.validate_content", lambda *a, **kw: ("valid", "")
    )


def test_two_screens_share_one_byte_identical_namespaced_helper(tmp_path: Path, syntax_only):
    value = descriptor(
        entries=[
            {"screen": "scripts/screen_holomap.lua", "source": SOURCE},
            {"screen": "scripts/screen_vehicle_control.lua", "source": SOURCE},
        ]
    )
    mod = module(tmp_path, "islands", value)
    result = prepare([mod])
    assert not result.blockers
    assert result.schema == 1
    assert len(result.extensions) == 2
    renamed = f"cc2x/ui/m-{digest(mod.id.encode())[:16]}/shared.lua"
    assert result.payload == {renamed: LUA}
    assert {entry["source"] for entry in result.extensions} == {renamed}
    assert result.source_bytes == 2 * len(LUA)
    assert result.handled == {(mod.id, DESCRIPTOR), (mod.id, SOURCE)}
    assert result.descriptor_inputs == {mod.id: digest(json.dumps(value).encode())}
    assert len(result.files) == 1
    assert result.files[0]["source_sha256"] == {mod.id: digest(LUA)}
    assert result.files[0]["output_sha256"] == digest(LUA)
    assert DESCRIPTOR not in result.payload


def test_unique_targets_keep_mod_order_and_isolate_same_helper_names(tmp_path: Path, syntax_only):
    first = module(tmp_path, "first", descriptor())
    second = module(
        tmp_path,
        "second",
        descriptor(entries=[{"screen": "scripts/screen_propulsion.lua", "source": SOURCE}]),
    )
    result = prepare([second, first])
    assert not result.blockers
    assert [item["screen"] for item in result.extensions] == [
        "scripts/screen_propulsion.lua",
        "scripts/screen_holomap.lua",
    ]
    assert len(result.payload) == 2
    assert len({entry["source"] for entry in result.extensions}) == 2


def test_schema_two_preserves_profile_edits_exactly(tmp_path: Path, syntax_only):
    profiles = [
        {"sha256": "a" * 64, "edits": [{"offset": 12, "remove": 2, "insert": "-- café\n"}]},
        {"sha256": "b" * 64, "edits": [{"offset": 4, "remove": 0, "insert": ""}]},
    ]
    entry = {"screen": "scripts/screen_holomap.lua", "source": SOURCE, "profiles": profiles}
    original = copy.deepcopy(entry)
    result = prepare([module(tmp_path, "islands", descriptor(2, [entry]))])
    assert not result.blockers
    assert result.schema == 2
    assert result.extensions[0]["profiles"] == profiles
    assert result.extensions[0]["screen"] == entry["screen"]
    assert entry == original
    assert result.source_bytes == len(LUA) + len("-- café\n".encode())


@pytest.mark.parametrize("capabilities,schema", [([], 1), (["screen-extensions-v1"], 2)])
def test_missing_runtime_capability_is_actionable(
    tmp_path: Path, syntax_only, capabilities, schema
):
    mod = module(tmp_path, "islands", descriptor(schema))
    result = prepare([mod], capabilities=capabilities)
    assert result.blockers
    assert result.blockers[0]["code"] == "sdk_api"
    assert (mod.id, DESCRIPTOR) in result.handled
    assert (mod.id, SOURCE) in result.handled
    assert not result.payload


def test_same_screen_across_mods_blocks_with_both_participants(tmp_path: Path, syntax_only):
    first = module(tmp_path, "first", descriptor())
    second = module(tmp_path, "second", descriptor())
    result = prepare([first, second])
    conflict = next(item for item in result.blockers if item["code"] == "screen_extension_conflict")
    assert set(conflict["participants"]) == {"first", "second"}
    assert "screen_holomap.lua" in conflict["message"]


@pytest.mark.parametrize(
    "change",
    [
        "schema_boolean",
        "schema_float",
        "schema_unknown",
        "extra_root",
        "extra_entry",
        "duplicate_screen",
        "screen_case_collision",
        "schema_one_profiles",
        "missing_source",
        "traversal_source",
        "absolute_source",
        "backslash_source",
        "unicode_source",
        "wrong_source_root",
        "wrong_screen_root",
        "reserved_source",
        "source_case_alias",
        "profile_hash",
        "profile_hash_trailing_newline",
        "duplicate_profile",
        "empty_profiles",
        "too_many_profiles",
        "offset_boolean",
        "offset_negative",
        "offset_float",
        "remove_overflow",
        "same_offsets",
        "overlap",
        "descending",
        "insert_nul",
        "insert_surrogate",
        "extra_edit",
        "empty_edits",
        "too_many_edits",
        "insert_utf8_budget",
    ],
)
def test_invalid_descriptors_fail_closed(tmp_path: Path, syntax_only, change):
    entry = {
        "screen": "scripts/screen_holomap.lua",
        "source": SOURCE,
        "profiles": [{"sha256": "a" * 64, "edits": [{"offset": 1, "remove": 0, "insert": ""}]}],
    }
    value = descriptor(2, [entry])
    profile = entry["profiles"][0]
    edit = profile["edits"][0]
    if change == "schema_boolean":
        value["schema"] = True
    elif change == "schema_float":
        value["schema"] = 2.0
    elif change == "schema_unknown":
        value["schema"] = 3
    elif change == "extra_root":
        value["extra"] = 1
    elif change == "extra_entry":
        entry["extra"] = 1
    elif change == "duplicate_screen":
        value["extensions"].append(copy.deepcopy(entry))
    elif change == "screen_case_collision":
        duplicate = copy.deepcopy(entry)
        duplicate["screen"] = "scripts/SCREEN_HOLOMAP.lua"
        value["extensions"].append(duplicate)
    elif change == "schema_one_profiles":
        value["schema"] = 1
    elif change == "missing_source":
        entry["source"] = "cc2x/ui/missing.lua"
    elif change == "traversal_source":
        entry["source"] = "cc2x/ui/../shared.lua"
    elif change == "absolute_source":
        entry["source"] = "/cc2x/ui/shared.lua"
    elif change == "backslash_source":
        entry["source"] = "cc2x/ui\\shared.lua"
    elif change == "unicode_source":
        entry["source"] = "cc2x/ui/café.lua"
    elif change == "wrong_source_root":
        entry["source"] = "scripts/shared.lua"
    elif change == "wrong_screen_root":
        entry["screen"] = "cc2x/ui/screen.lua"
    elif change == "reserved_source":
        entry["source"] = "cc2x/ui/CON.lua"
    elif change == "source_case_alias":
        entry["source"] = "cc2x/ui/SHARED.lua"
    elif change == "profile_hash":
        profile["sha256"] = "A" * 64
    elif change == "profile_hash_trailing_newline":
        profile["sha256"] = "a" * 64 + "\n"
    elif change == "duplicate_profile":
        entry["profiles"].append(copy.deepcopy(profile))
    elif change == "empty_profiles":
        entry["profiles"] = []
    elif change == "too_many_profiles":
        entry["profiles"] = [copy.deepcopy(profile)] * 9
    elif change == "offset_boolean":
        edit["offset"] = True
    elif change == "offset_negative":
        edit["offset"] = -1
    elif change == "offset_float":
        edit["offset"] = 1.5
    elif change == "remove_overflow":
        edit.update(offset=2 * 1024 * 1024, remove=1)
    elif change == "same_offsets":
        profile["edits"].append(copy.deepcopy(edit))
    elif change == "overlap":
        edit["remove"] = 4
        profile["edits"].append({"offset": 2, "remove": 0, "insert": ""})
    elif change == "descending":
        edit["offset"] = 3
        profile["edits"].append({"offset": 2, "remove": 0, "insert": ""})
    elif change == "insert_nul":
        edit["insert"] = "\x00"
    elif change == "insert_surrogate":
        edit["insert"] = "\ud800"
    elif change == "extra_edit":
        edit["extra"] = 1
    elif change == "empty_edits":
        profile["edits"] = []
    elif change == "too_many_edits":
        profile["edits"] = [copy.deepcopy(edit)] * 65
    elif change == "insert_utf8_budget":
        edit["insert"] = "🛠" * (65536 + 1)
    result = prepare([module(tmp_path, "islands", value)])
    assert result.blockers
    assert not result.payload
    assert not result.extensions


@pytest.mark.parametrize(
    "raw", [b'{"schema":1,"schema":2,"extensions":[]}', b'{"schema":NaN}', b"\xff"]
)
def test_invalid_json_is_rejected(tmp_path: Path, syntax_only, raw):
    result = prepare([module(tmp_path, "islands", raw)])
    assert result.blockers
    assert not result.payload


def test_unreferenced_native_files_are_not_claimed(tmp_path: Path, syntax_only):
    mod = module(
        tmp_path, "islands", descriptor(), sources={SOURCE: LUA, "cc2x/unknown.dll": b"MZ"}
    )
    result = prepare([mod])
    assert not result.blockers
    assert (mod.id, "cc2x/unknown.dll") not in result.handled
    assert "cc2x/unknown.dll" not in result.payload


@pytest.mark.parametrize("large", ["descriptor", "helper"])
def test_sdk_size_limit_is_checked_before_lazy_content_read(
    tmp_path: Path, syntax_only, monkeypatch, large
):
    value = descriptor() if large == "helper" else b" " * (65536 + 1)
    sources = {SOURCE: b"--" + b" " * (256 * 1024)} if large == "helper" else None
    mod = module(tmp_path, "islands", value, sources=sources)
    original = FileRef.content.fget

    def guarded(item):
        forbidden = DESCRIPTOR if large == "descriptor" else SOURCE
        if item.key == forbidden:
            raise AssertionError("Check SDK file size before loading resource bytes")
        return original(item)

    monkeypatch.setattr(FileRef, "content", property(guarded))
    result = prepare([mod])
    assert result.blockers
    assert not result.payload
    assert not result.extensions


def test_changed_deferred_helper_is_not_copied(tmp_path: Path, syntax_only):
    mod = module(tmp_path, "islands", descriptor())
    (mod.root / "content" / SOURCE).write_bytes(b"-- changed after inventory\n")
    result = prepare([mod])
    assert result.blockers
    assert not result.payload


@pytest.mark.parametrize("preamble", [b"\xef\xbb\xbf", b"#!/usr/bin/lua\n"])
def test_file_preambles_not_supported_by_sdk_raw_chunk_loader_are_rejected(
    tmp_path: Path, syntax_only, preamble
):
    mod = module(tmp_path, "islands", descriptor(), sources={SOURCE: preamble + LUA})
    result = prepare([mod])
    assert result.blockers
    assert not result.payload


def test_insert_budget_counts_utf8_bytes_across_profiles(tmp_path: Path, syntax_only, monkeypatch):
    import cc2_mce.screen_extensions as screen

    monkeypatch.setattr(screen, "MAX_INSERT_BYTES", 4)
    entry = {
        "screen": "scripts/screen_holomap.lua",
        "source": SOURCE,
        "profiles": [
            {"sha256": "a" * 64, "edits": [{"offset": 1, "remove": 0, "insert": "é"}]},
            {"sha256": "b" * 64, "edits": [{"offset": 1, "remove": 0, "insert": "abc"}]},
        ],
    }
    result = prepare([module(tmp_path, "islands", descriptor(2, [entry]))])
    assert result.blockers
    assert not result.payload


@pytest.mark.parametrize("extra", [-1, 0])
def test_aggregate_sdk_budget_counts_repeated_helper_reads(
    tmp_path: Path, syntax_only, monkeypatch, extra
):
    import cc2_mce.screen_extensions as screen

    monkeypatch.setattr(screen, "MAX_TOTAL_BYTES", 2 * len(LUA) + extra)
    entries = [
        {"screen": "scripts/screen_holomap.lua", "source": SOURCE},
        {"screen": "scripts/screen_vehicle_control.lua", "source": SOURCE},
    ]
    result = prepare([module(tmp_path, "islands", descriptor(1, entries))])
    assert bool(result.blockers) == (extra < 0)
    if not result.blockers:
        assert result.source_bytes == 2 * len(LUA)
        assert len(result.payload) == 1


def test_extension_count_limit_matches_one_generated_sdk_package(tmp_path: Path, syntax_only):
    entries = [{"screen": f"scripts/screen_{i}.lua", "source": SOURCE} for i in range(16)]
    assert not prepare([module(tmp_path, "sixteen", descriptor(1, entries))]).blockers
    entries.append({"screen": "scripts/screen_seventeen.lua", "source": SOURCE})
    result = prepare([module(tmp_path, "seventeen", descriptor(1, entries))])
    assert result.blockers
    assert not result.payload


def test_real_luac_checks_syntax_without_running_helper(tmp_path: Path):
    luac = Path(
        shutil.which("luac5.3")
        or shutil.which("luac53")
        or shutil.which("luac")
        or str(Path(__file__).parents[1] / "cc2_mce/tools_data/lua/luac.exe")
    )
    if not luac.is_file():
        pytest.skip("Lua 5.3 validator unavailable")
    mod = module(tmp_path, "islands", descriptor())
    assert not prepare([mod], luac=str(luac)).blockers
    broken = module(tmp_path, "broken", descriptor(), sources={SOURCE: b"function(\n"})
    assert prepare([broken], luac=str(luac)).blockers
