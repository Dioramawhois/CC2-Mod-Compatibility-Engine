from cc2_mce.textmerge import merge_lines

BASE = b"1\n2\n3\n4\n5\n6\n"

def test_disjoint_edits_combine() -> None:
    r = merge_lines(b"ONE\n2\n3\n4\n5\n6\n", BASE, b"1\n2\n3\n4\n5\nSIX\n")
    assert r.status == "clean" and r.content == b"ONE\n2\n3\n4\n5\nSIX\n"

def test_identical_change_taken_once() -> None:
    same = b"1\nX\n3\n4\n5\n6\n"
    r = merge_lines(same, BASE, same)
    assert r.status == "clean" and r.content == same

def test_same_line_different_values_conflict() -> None:
    assert merge_lines(b"1\nA\n3\n4\n5\n6\n", BASE, b"1\nB\n3\n4\n5\n6\n").status == "conflict"

def test_adjacent_edits_combine() -> None:
    r = merge_lines(b"1\nX\n3\n4\n5\n6\n", BASE, b"1\n2\n3\nY\n5\n6\n")
    assert r.status == "clean" and r.content == b"1\nX\n3\nY\n5\n6\n"

def test_insert_at_top_and_end() -> None:
    r = merge_lines(b"0\n1\n2\n3\n4\n5\n6\n", BASE, b"1\n2\n3\n4\n5\n6\nEND\n")
    assert r.status == "clean" and r.content == b"0\n1\n2\n3\n4\n5\n6\nEND\n"

def test_delete_and_edit_on_different_lines_combine() -> None:
    r = merge_lines(b"1\n2\n4\n5\n6\n", BASE, b"1\nX\n3\n4\n5\n6\n")
    assert r.status == "clean" and r.content == b"1\nX\n4\n5\n6\n"

def test_delete_versus_edit_on_same_line_conflict() -> None:
    assert merge_lines(b"1\n4\n5\n6\n", BASE, b"1\nX\n3\n4\n5\n6\n").status == "conflict"

def test_unchanged_base_is_clean() -> None:
    assert merge_lines(BASE, BASE, BASE).content == BASE
