from pathlib import Path

import pytest

from cc2_mce.discovery import discover
from cc2_mce.errors import InputError
from tests.test_paths_discovery import make_mod


def test_unmarked_workshop_package_remains_a_mod(tmp_path: Path) -> None:
    make_mod(tmp_path, "123", {"a.txt": b"x"})
    mod = discover([tmp_path]).mods[0]
    assert mod.package_kind == "mod"
    assert mod.dependencies == ()


def test_library_mark_in_mod_xml_not_its_location_controls_kind(tmp_path: Path) -> None:
    path = make_mod(tmp_path, "123", {"scripts/lib.lua": b"return 1"})
    (path / "mod.xml").write_text(
        '<data name="SDK"><cc2mce schema="1" type="library" id="example.sdk" '
        'sdk="cc2x" api="3"><requires id="other.library"/></cc2mce></data>',
        encoding="utf-8",
    )
    mod = discover([tmp_path]).mods[0]
    assert mod.package_kind == "library"
    assert mod.package_id == "example.sdk"
    assert mod.sdk == "cc2x" and mod.api == 3
    assert mod.dependencies == ("other.library",)
    assert mod.report()["package_kind"] == "library"


@pytest.mark.parametrize(
    "section",
    [
        '<cc2mce schema="2" type="library"/>',
        '<cc2mce schema="1" type="plugin"/>',
        '<cc2mce schema="1" type="library" api="oops"/>',
        '<cc2mce schema="1" type="library"><requires id="../outside"/></cc2mce>',
        '<cc2mce schema="1" type="library"/><cc2mce schema="1" type="mod"/>',
    ],
)
def test_invalid_declaration_does_not_fall_back_to_ordinary_mod(tmp_path: Path, section: str):
    path = make_mod(tmp_path, "123", {})
    (path / "mod.xml").write_text(f'<data name="SDK">{section}</data>', encoding="utf-8")
    with pytest.raises(InputError):
        discover([tmp_path])
