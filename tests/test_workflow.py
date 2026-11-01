from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from cc2_mce.filesystem import digest
from cc2_mce.installation import inspect_game
from cc2_mce.merge import GitMergeAdapter, MergeInput, merge_file
from cc2_mce.workflow import analyze, apply_plan, restore_previous
from tests.test_installation import game
from tests.test_paths_discovery import make_mod


def test_canonical_eol_uses_real_git_and_keeps_both_edits() -> None:
    base = b"a=1\r\n\r\n\r\nb=1\r\n"
    result = merge_file(
        "a.txt",
        [MergeInput("a", b"a=2\n\n\nb=1\n"), MergeInput("b", b"a=1\n\n\nb=2\n")],
        base,
        baseline_verified=True,
        git=GitMergeAdapter(),
        canonical_eol=True,
    )
    assert result.content == b"a=2\n\n\nb=2\n"


def fixture(tmp_path: Path):
    root = game(tmp_path / "game")
    installation = inspect_game(root)
    assert installation is not None
    make_mod(tmp_path / "workshop", "a", {"a.txt": b"a=2\n\n\nb=1\n"})
    make_mod(tmp_path / "workshop", "b", {"a.txt": b"a=1\n\n\nb=2\n"})
    for path in (root / "rom_0/a.txt", root / "mod_dev_kit/source/a.txt"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"a=1\r\n\r\n\r\nb=1\r\n")
    profile = {
        "game_sha256": digest(installation.executable.read_bytes()),
        "baselines": {"a.txt": digest(b"a=1\r\n\r\n\r\nb=1\r\n")},
        "runtime_sha256": None,
        "native_plugins": {},
    }
    user = tmp_path / "user"
    user.mkdir()
    (user / "mods.xml").write_bytes(b"<data><active_mod_folders/></data>")
    return installation, profile, user


def test_apply_creates_real_mod_activates_and_restores(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    before = (user / "mods.xml").read_bytes()
    plan = analyze(installation, scan, ["a", "b"], profile=profile)
    assert not plan.blockers
    package = apply_plan(plan, user, game_running=lambda: False)
    assert (package / "mod.xml").is_file()
    assert (package / "content/a.txt").read_bytes() == b"a=2\n\n\nb=2\n"
    assert str(package).encode() in (user / "mods.xml").read_bytes()
    assert (package / "mce-manifest.json").is_file()
    restore_previous(user, game_running=lambda: False)
    assert (user / "mods.xml").read_bytes() == before


def test_conflict_and_changed_sources_cannot_activate(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    plan = analyze(installation, scan, ["a", "b"], profile=profile)
    (tmp_path / "workshop/a/content/a.txt").write_bytes(b"changed")
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)
    assert not (user / "mods").exists()


def test_running_game_blocks_before_any_write(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: True)
    assert not (user / "mods").exists()


def test_unknown_native_plugin_is_not_enabled(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    make_mod(tmp_path / "workshop", "native", {"cc2x/foo.dll": b"MZ-unknown"})
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["native"], profile=profile)
    assert any(item["code"] == "native_plugin_review_required" for item in plan.blockers)


def test_reused_output_rejects_extra_executable(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    package = apply_plan(plan, user, game_running=lambda: False)
    evil = package / "content/cc2x/unreviewed.dll"
    evil.parent.mkdir()
    evil.write_bytes(b"must never load")
    with pytest.raises(InputError):
        apply_plan(plan, user, game_running=lambda: False)


def test_activation_write_failure_rolls_back(tmp_path: Path, monkeypatch) -> None:
    installation, profile, user = fixture(tmp_path)
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    before = (user / "mods.xml").read_bytes()
    monkeypatch.setattr(
        "cc2_mce.workflow.os.replace", lambda *args: (_ for _ in ()).throw(OSError())
    )
    with pytest.raises(OSError):
        apply_plan(plan, user, game_running=lambda: False)
    assert (user / "mods.xml").read_bytes() == before


def test_library_dependencies_are_added_and_cycles_block(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    for name, kind, dependency in [("app", "mod", "sdk"), ("sdk", "library", None)]:
        package = make_mod(tmp_path / "packages", name, {f"{name}.txt": b"data"})
        deps = f'<requires id="{dependency}"/>' if dependency else ""
        (package / "mod.xml").write_text(
            f'<data name="{name}"><cc2mce schema="1" type="{kind}" id="{name}">'
            f"{deps}</cc2mce></data>"
        )
    scan = discover([tmp_path / "packages"])
    plan = analyze(installation, scan, ["app"], profile=profile)
    assert [mod.id for mod in plan.selected] == ["sdk", "app"]
    assert not plan.blockers
    (tmp_path / "packages/sdk/mod.xml").write_text(
        '<data><cc2mce schema="1" type="library" id="sdk"><requires id="app"/></cc2mce></data>'
    )
    with pytest.raises(InputError, match="Циклическая"):
        analyze(installation, discover([tmp_path / "packages"]), ["app"], profile=profile)


def test_restore_does_not_overwrite_external_changes(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    apply_plan(plan, user, game_running=lambda: False)
    (user / "mods.xml").write_bytes(b"<data><active_mod_folders/> <!-- user change --></data>")
    with pytest.raises(InputError):
        restore_previous(user, game_running=lambda: False)


def test_restore_accepts_game_xml_reformatting(tmp_path: Path) -> None:
    from xml.etree import ElementTree

    installation, profile, user = fixture(tmp_path)
    original = (user / "mods.xml").read_bytes()
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    apply_plan(plan, user, game_running=lambda: False)
    xml = ElementTree.fromstring((user / "mods.xml").read_bytes())
    import copy

    active = xml.find("active_mod_folders")
    assert active is not None
    active.append(copy.deepcopy(active[0]))
    ElementTree.indent(xml, space="\t")
    (user / "mods.xml").write_bytes(ElementTree.tostring(xml, encoding="utf-8"))
    restore_previous(user, game_running=lambda: False)
    assert (user / "mods.xml").read_bytes() == original


def test_deep_dependency_graph_fails_before_python_recursion_limit(tmp_path: Path) -> None:
    from cc2_mce.discovery import ModRef, Scan
    from cc2_mce.filesystem import Limits
    from cc2_mce.workflow import resolve_selection

    mods = tuple(
        ModRef(
            str(i),
            "Library",
            tmp_path,
            digest(b""),
            (),
            "library",
            str(i),
            (str(i + 1),) if i < 1099 else (),
        )
        for i in range(1100)
    )
    scan = Scan((tmp_path,), mods, digest(b"snapshot"), Limits())
    with pytest.raises(InputError, match="32"):
        resolve_selection(scan, ["0"])


def test_one_folder_replaces_payload_and_undo_restores_previous_bytes(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    first = analyze(installation, scan, ["a", "b"], profile=profile)
    package = apply_plan(first, user, game_running=lambda: False)
    assert package.name == "CC2-MCE"
    before = {p.relative_to(package): p.read_bytes() for p in package.rglob("*") if p.is_file()}
    # A file removed from the selected set must not survive the replacement.
    (tmp_path / "workshop/a/content/only-a.txt").write_bytes(b"unique")
    second = analyze(installation, discover([tmp_path / "workshop"]), ["a"], profile=profile)
    assert apply_plan(second, user, game_running=lambda: False) == package
    assert (package / "content/only-a.txt").is_file()
    third = analyze(installation, discover([tmp_path / "workshop"]), ["b"], profile=profile)
    apply_plan(third, user, game_running=lambda: False)
    assert not (package / "content/only-a.txt").exists()
    assert list((user / "mods").iterdir()) == [package]
    restore_previous(user, game_running=lambda: False)
    assert (package / "content/only-a.txt").read_bytes() == b"unique"
    assert (package / "content/a.txt").read_bytes() == b"a=2\n\n\nb=1\n"
    assert before[Path("content/a.txt")] == first.payload["a.txt"]


def test_unchecking_last_mod_activates_empty_set(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    original = apply_plan(
        analyze(installation, scan, ["a"], profile=profile), user, game_running=lambda: False
    )
    plan = analyze(installation, scan, [], profile=profile)
    apply_plan(plan, user, game_running=lambda: False)
    from cc2_mce.workflow import active_paths

    assert active_paths(user) == ()
    assert not list((original / "content").iterdir())
    restore_previous(user, game_running=lambda: False)
    assert active_paths(user) == (original,)
    assert (original / "content/a.txt").is_file()


def test_failed_replacement_keeps_last_working_package(tmp_path: Path, monkeypatch) -> None:
    import cc2_mce.workflow as workflow

    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    package = apply_plan(
        analyze(installation, scan, ["a"], profile=profile), user, game_running=lambda: False
    )
    original = {p.relative_to(package): p.read_bytes() for p in package.rglob("*") if p.is_file()}
    config = (user / "mods.xml").read_bytes()
    replace = workflow._replace_checked

    def fail_config(path, content, expected):
        if path == user / "mods.xml":
            raise OSError("fixture config failure")
        return replace(path, content, expected)

    monkeypatch.setattr(workflow, "_replace_checked", fail_config)
    with pytest.raises(OSError):
        apply_plan(
            analyze(installation, scan, ["b"], profile=profile), user, game_running=lambda: False
        )
    assert (user / "mods.xml").read_bytes() == config
    assert original == {
        p.relative_to(package): p.read_bytes() for p in package.rglob("*") if p.is_file()
    }


def test_interrupted_folder_swap_recovers_on_next_apply(tmp_path: Path, monkeypatch) -> None:
    import cc2_mce.workflow as workflow

    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    first = analyze(installation, scan, ["a"], profile=profile)
    second = analyze(installation, scan, ["b"], profile=profile)
    package = apply_plan(first, user, game_running=lambda: False)
    rename = workflow.os.rename

    def interrupt(source, target):
        if Path(source).name.startswith("stage-"):
            raise KeyboardInterrupt("simulated process interruption")
        return rename(source, target)

    monkeypatch.setattr(workflow.os, "rename", interrupt)
    with pytest.raises(KeyboardInterrupt):
        apply_plan(second, user, game_running=lambda: False)
    assert (user / "cc2-mce/pending.json").is_file()
    monkeypatch.setattr(workflow.os, "rename", rename)
    apply_plan(second, user, game_running=lambda: False)
    assert (package / "content/a.txt").read_bytes() == second.payload["a.txt"]
    assert not (user / "cc2-mce/pending.json").exists()
    restore_previous(user, game_running=lambda: False)
    assert (package / "content/a.txt").read_bytes() == first.payload["a.txt"]


def test_idempotent_restart_preserves_undo_after_game_reformats_xml(tmp_path: Path) -> None:
    from xml.etree import ElementTree as ET

    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    first = analyze(installation, scan, ["a"], profile=profile)
    second = analyze(installation, scan, ["b"], profile=profile)
    package = apply_plan(first, user, game_running=lambda: False)
    apply_plan(second, user, game_running=lambda: False)
    journal = (user / "cc2-mce/activation.json").read_bytes()
    xml = ET.fromstring((user / "mods.xml").read_bytes())
    ET.indent(xml)
    (user / "mods.xml").write_bytes(ET.tostring(xml))
    apply_plan(second, user, game_running=lambda: False)
    assert (user / "cc2-mce/activation.json").read_bytes() == journal
    restore_previous(user, game_running=lambda: False)
    assert (package / "content/a.txt").read_bytes() == first.payload["a.txt"]


def test_generated_output_is_excluded_from_discovery(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a"], profile=profile)
    apply_plan(plan, user, game_running=lambda: False)
    assert discover([user / "mods"]).mods == ()


def test_unknown_existing_fixed_folder_is_never_overwritten(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    package = user / "mods/CC2-MCE"
    package.mkdir(parents=True)
    (package / "user.txt").write_bytes(b"preserve")
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a"], profile=profile)
    with pytest.raises((InputError, OSError)):
        apply_plan(plan, user, game_running=lambda: False)
    assert (package / "user.txt").read_bytes() == b"preserve"


def test_legacy_hash_output_is_archived_and_undo_returns_it(tmp_path: Path) -> None:
    import shutil
    from xml.etree import ElementTree as ET

    installation, profile, user = fixture(tmp_path)
    scan = discover([tmp_path / "workshop"])
    first = analyze(installation, scan, ["a"], profile=profile)
    stable = apply_plan(first, user, game_running=lambda: False)
    legacy = stable.with_name("CC2-MCE-" + first.report["build_id"][:16])
    stable.rename(legacy)
    inactive = stable.with_name("CC2-MCE-" + "1" * 16)
    shutil.copytree(legacy, inactive)
    xml = ET.Element("data")
    ET.SubElement(ET.SubElement(xml, "active_mod_folders"), "path", value=str(legacy))
    previous = ET.tostring(xml)
    (user / "mods.xml").write_bytes(previous)
    apply_plan(
        analyze(installation, scan, ["b"], profile=profile), user, game_running=lambda: False
    )
    assert list((user / "mods").iterdir()) == [stable]
    restore_previous(user, game_running=lambda: False)
    assert legacy.is_dir()
    assert inactive.is_dir()
    assert (legacy / "content/a.txt").read_bytes() == first.payload["a.txt"]
    assert (user / "mods.xml").read_bytes() == previous


def test_installed_original_is_used_without_preapproved_file_hash(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    profile["baselines"] = {}
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    assert not plan.blockers
    assert plan.payload["a.txt"] == b"a=2\n\n\nb=2\n"
    assert plan.report["files"][0]["baseline_sha256"] == digest(b"a=1\r\n\r\n\r\nb=1\r\n")


def test_later_patch_resolves_hunks_and_preserves_unrelated_changes(tmp_path: Path) -> None:
    installation, profile, user = fixture(tmp_path)
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=2\n")
    scan = discover([tmp_path / "workshop"])
    forward = analyze(installation, scan, ["a", "b"], profile=profile, patch_priority=True)
    reverse = analyze(installation, scan, ["b", "a"], profile=profile, patch_priority=True)
    assert forward.payload["a.txt"] == b"a=3\n\n\nb=2\n"
    assert reverse.payload["a.txt"] == b"a=2\n\n\nb=2\n"
    assert forward.report["files"][0]["status"] == "overridden"
    assert forward.report["mod_order"] == ["a", "b"]
    assert reverse.report["mod_order"] == ["b", "a"]
    package = apply_plan(forward, user, game_running=lambda: False)
    apply_plan(reverse, user, game_running=lambda: False)
    assert (package / "content/a.txt").read_bytes() == reverse.payload["a.txt"]


def test_no_original_uses_explicit_ordered_replacement(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    for path in (installation.root / "rom_0/a.txt", installation.root / "mod_dev_kit/source/a.txt"):
        path.unlink()
    scan = discover([tmp_path / "workshop"])
    plan = analyze(installation, scan, ["a", "b"], profile=profile, patch_priority=True)
    assert not plan.blockers
    assert plan.payload["a.txt"] == b"a=1\n\n\nb=2\n"
    result = plan.report["files"][0]
    assert result["baseline_sha256"] is None
    assert result["strategy"] == "ordered-replacement-no-base"
    strict = analyze(installation, scan, ["a", "b"], profile=profile)
    assert strict.blockers


def test_repeated_earlier_content_can_be_the_last_patch(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    (tmp_path / "workshop/b/content/a.txt").write_bytes(b"a=3\n\n\nb=2\n")
    make_mod(tmp_path / "workshop", "c", {"a.txt": b"a=2\n\n\nb=1\n"})
    plan = analyze(
        installation,
        discover([tmp_path / "workshop"]),
        ["a", "b", "c"],
        profile=profile,
        patch_priority=True,
    )
    assert not plan.blockers
    assert plan.payload["a.txt"] == b"a=2\n\n\nb=2\n"


def test_local_original_path_case_is_host_independent(tmp_path: Path) -> None:
    installation, profile, _ = fixture(tmp_path)
    original = installation.root / "rom_0/a.txt"
    original.rename(original.with_name("A.TXT"))
    plan = analyze(installation, discover([tmp_path / "workshop"]), ["a", "b"], profile=profile)
    assert not plan.blockers
    assert plan.payload["a.txt"] == b"a=2\n\n\nb=2\n"
