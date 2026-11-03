from dataclasses import replace
from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.workflow import analyze, apply_plan, resolve_selection, restore_previous
from tests.test_paths_discovery import make_mod
from tests.test_workflow import fixture


def versions(tmp_path: Path):
    for name, value in (
        ("3826940003", b"old"),
        ("local-next-version", b"new"),
        ("consumer", b"other"),
    ):
        make_mod(tmp_path, name, {"a.txt": value})
    scan = discover([tmp_path])
    return replace(
        scan,
        mods=tuple(
            replace(mod, package_id="3826940003") if mod.id != "consumer" else mod
            for mod in scan.mods
        ),
    )


@pytest.mark.parametrize("selected", ["3826940003", "local-next-version", "consumer"])
def test_unselected_versions_do_not_block_an_explicit_source(tmp_path, selected):
    scan = versions(tmp_path)
    assert [mod.id for mod in resolve_selection(scan, [selected])] == [selected]


def test_two_versions_cannot_be_applied_together(tmp_path):
    scan = versions(tmp_path)
    with pytest.raises(InputError, match="одну версию"):
        resolve_selection(scan, ["3826940003", "local-next-version"])


def test_dependency_uses_the_explicit_version_even_if_selected_later(tmp_path):
    scan = versions(tmp_path)
    scan = replace(
        scan,
        mods=tuple(
            replace(mod, dependencies=("3826940003",)) if mod.id == "consumer" else mod
            for mod in scan.mods
        ),
    )
    assert [mod.id for mod in resolve_selection(scan, ["consumer", "local-next-version"])] == [
        "local-next-version",
        "consumer",
    ]
    with pytest.raises(InputError, match="одну версию"):
        resolve_selection(scan, ["consumer"])


def test_identity_cannot_shadow_an_unrelated_source_id(tmp_path):
    scan = versions(tmp_path)
    scan = replace(
        scan,
        mods=tuple(
            replace(mod, package_id="another-identity") if mod.id == "3826940003" else mod
            for mod in scan.mods
        ),
    )
    with pytest.raises(InputError):
        resolve_selection(scan, ["local-next-version"])


def test_version_switch_replaces_the_fixed_output_and_undo_restores_old_source(tmp_path):
    installation, profile, user = fixture(tmp_path)
    scan = versions(tmp_path / "versions")
    old = analyze(installation, scan, ["3826940003"], profile=profile)
    output = apply_plan(old, user, game_running=lambda: False)
    assert (output / "content/a.txt").read_bytes() == b"old"
    new = analyze(installation, scan, ["local-next-version"], profile=profile)
    assert new.report["mod_order"] == ["local-next-version"]
    assert new.report["sources"][0]["package_id"] == "3826940003"
    assert apply_plan(new, user, game_running=lambda: False) == output
    assert (output / "content/a.txt").read_bytes() == b"new"
    restore_previous(user, game_running=lambda: False)
    assert (output / "content/a.txt").read_bytes() == b"old"
