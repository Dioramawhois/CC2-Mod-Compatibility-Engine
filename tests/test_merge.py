import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from cc2_mce.merge import GitMergeAdapter, MergeInput, merge_file

BASE = b"alpha=1\n\n\nbeta=1\n\n\ngamma=1\n"
A = BASE.replace(b"alpha=1", b"alpha=2")
B = BASE.replace(b"beta=1", b"beta=2")
C = BASE.replace(b"gamma=1", b"gamma=2")


def merge(
    *data: bytes, base: bytes | None = BASE, verified: bool = True, path: str = "constants.txt"
):
    return merge_file(
        path,
        [MergeInput(str(i), value) for i, value in enumerate(data)],
        base,
        baseline_verified=verified,
    )


def test_real_git_clean_three_way() -> None:
    result = merge(A, B)
    assert result.status == "clean"
    assert result.content == A.replace(b"beta=1", b"beta=2")


def test_same_edit_and_dedup() -> None:
    assert merge(A, A).status == "identical"
    assert merge(A).status == "copied"


def test_conflict_not_last_mod_wins() -> None:
    result = merge(A, BASE.replace(b"alpha=1", b"alpha=3"))
    assert result.status == "conflict"
    assert result.content is None
    assert result.conflicts[0]["kind"] == "edit_edit_conflict"


def test_n_way_uses_common_base_and_preflights_all_pairs() -> None:
    assert merge(A, B, C).content == A.replace(b"beta=1", b"beta=2").replace(b"gamma=1", b"gamma=2")
    conflicting = BASE.replace(b"alpha=1", b"alpha=3")
    for variants in [(A, B, conflicting), (B, A, conflicting), (conflicting, B, A)]:
        assert merge(*variants).status == "conflict"


def test_delete_modify_conflict() -> None:
    assert (
        merge(BASE.replace(b"alpha=1\n", b""), A).conflicts[0]["kind"] == "delete_modify_conflict"
    )


def test_no_baseline_and_proven_absence() -> None:
    assert merge(A, B, base=None, verified=False).status == "no_base"
    assert merge(A, B, verified=False).status == "no_base"
    assert merge(A, B, base=None).conflicts[0]["kind"] == "add_add_conflict"
    assert merge(A, A, base=None, verified=False).status == "identical"


@pytest.mark.parametrize("path", ["cc2x/example.dll", "elsewhere/PLUGIN.DLL", "cc2x/config.txt"])
def test_native_block_even_unique(path: str) -> None:
    assert merge(b"MZ", path=path).status == "native_plugin_review_required"


def test_binary_and_unknown() -> None:
    assert merge(b"a", b"b", path="icon.png").status == "unsupported_binary"
    assert merge(b"a", path="icon.png").status == "copied"
    assert merge(b"a", b"a", path="icon.png").status == "identical"
    assert merge(b"a", path="payload.xyz").status == "needs_review"
    assert merge(b"\x00", b"\x01", path="fake.txt").status == "encoding_conflict"


def test_cc2_shader_uses_real_three_way_and_preserves_independent_edits() -> None:
    result = merge(A, B, path="shaders/screen_crt.glsl")
    assert result.status == "clean"
    assert result.content == A.replace(b"beta=1", b"beta=2")
    assert merge(b"\xff", path="shaders/bad.glsl").status == "encoding_conflict"


def test_cc2_texture_is_copied_or_replaced_whole_and_unknown_header_stays_blocked() -> None:
    left, right = b"TXTR\x02\x00left", b"TXTR\x02\x00right"
    assert merge(left, path="textures/a.txtr").content == left
    assert merge(left, right, path="textures/a.txtr").status == "unsupported_binary"
    result = merge_file(
        "textures/a.txtr",
        [MergeInput("a", left), MergeInput("b", right)],
        None,
        favor_later=True,
    )
    assert result.content == right
    assert result.status == "overridden"
    assert result.strategy == "ordered-binary-replacement"
    assert merge(b"unknown", path="textures/a.txtr").status == "needs_review"
    assert merge(left, b"MZ-not-a-texture", path="textures/a.txtr").status == "needs_review"
    for contents in ((left, b"invalid"), (b"invalid", right)):
        for priority in (False, True):
            invalid = merge_file(
                "textures/a.txtr",
                [MergeInput(str(i), content) for i, content in enumerate(contents)],
                None,
                favor_later=priority,
            )
            assert invalid.status == "needs_review"


def test_eol_and_bom_roundtrip() -> None:
    variants = [
        MergeInput("a", b"\xef\xbb\xbf" + A.replace(b"\n", b"\r\n")),
        MergeInput("b", b"\xef\xbb\xbf" + B.replace(b"\n", b"\r\n")),
    ]
    result = merge_file(
        "constants.txt",
        variants,
        b"\xef\xbb\xbf" + BASE.replace(b"\n", b"\r\n"),
        baseline_verified=True,
    )
    assert result.content == b"\xef\xbb\xbf" + A.replace(b"beta=1", b"beta=2").replace(
        b"\n", b"\r\n"
    )
    assert merge(A, B.replace(b"\n", b"\r\n")).status == "encoding_conflict"
    assert merge(b"\xff\xfea\x00").status == "encoding_conflict"


def test_literal_markers_not_conflicts() -> None:
    assert merge(b'value="<<<<<<<"\n').status == "copied"
    assert (
        merge(b"<<<<<<< ours\nhello\n=======\nworld\n>>>>>>> theirs\n").status == "validation_error"
    )


def test_xml_validation_and_entities() -> None:
    assert merge(b"<root><a/></root>", path="data.xml").status == "copied"
    assert merge(b"<root>", path="data.xml").status == "validation_error"
    assert (
        merge(
            b'<!DOCTYPE root [<!ENTITY x SYSTEM "file:///secret">]><root/>', path="data.xml"
        ).status
        == "validation_error"
    )


def test_lua_requires_53_and_never_executes() -> None:
    with patch("cc2_mce.validation.shutil.which", return_value=None):
        assert merge(b"return 1\n", path="script.lua").status == "needs_review"

    def runner(args, **kwargs):
        assert kwargs["shell"] is False
        assert "-p" in args or "-v" in args
        return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"Lua 5.5.0")

    with patch("cc2_mce.validation.subprocess.run", side_effect=runner):
        assert (
            merge_file(
                "script.lua", [MergeInput("a", b"return 1")], None, luac="/trusted/luac"
            ).status
            == "needs_review"
        )


def test_lua_invalid_and_valid_with_53_mock() -> None:
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        if "-v" in args:
            return subprocess.CompletedProcess(args, 0, stdout=b"Lua 5.3.6", stderr=b"")
        assert "-p" in args
        assert Path(args[-1]).read_bytes() == b"return 1\n"
        return subprocess.CompletedProcess(args, 1, stdout=b"", stderr=b"syntax error")

    with patch("cc2_mce.validation.subprocess.run", side_effect=runner):
        assert (
            merge_file(
                "script.lua", [MergeInput("a", b"return 1\n")], None, luac="/trusted/luac"
            ).status
            == "validation_error"
        )
    assert len(calls) == 2


@pytest.mark.parametrize(
    "code,status",
    [
        (1, "conflict"),
        (127, "conflict"),
        (128, "tool_error"),
        (255, "tool_error"),
        (-9, "tool_error"),
    ],
)
def test_git_return_codes(code: int, status: str) -> None:
    with patch(
        "cc2_mce.merge.subprocess.run",
        return_value=subprocess.CompletedProcess([], code, stdout=b"", stderr=b""),
    ):
        assert GitMergeAdapter("git").merge(A, BASE, B).status == status


def test_git_failure_and_timeout() -> None:
    for failure in [OSError("missing"), subprocess.TimeoutExpired("git", 1)]:
        with patch("cc2_mce.merge.subprocess.run", side_effect=failure):
            assert GitMergeAdapter("git").merge(A, BASE, B).status == "tool_error"


def test_git_no_original_writes(tmp_path: Path) -> None:
    original = tmp_path / "a.txt"
    original.write_bytes(A)
    assert merge(A, B).status == "clean"
    assert original.read_bytes() == A
