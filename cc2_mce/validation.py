from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True)
class TextFormat:
    bom: bool
    eol: str


def decode_text(data: bytes) -> tuple[str, TextFormat]:
    if b"\x00" in data:
        raise ValueError("NUL or unsupported UTF-16/binary text")
    text = data.decode("utf-8-sig")
    remainder = text.replace("\r\n", "")
    if "\r" in remainder or ("\r\n" in text and "\n" in remainder):
        raise ValueError("Mixed or unsupported EOL")
    return text, TextFormat(data.startswith(b"\xef\xbb\xbf"), "\r\n" if "\r\n" in text else "\n")


def has_conflict_markers(text: str) -> bool:
    opened = False
    separator = False
    for line in text.splitlines():
        if line.startswith("<<<<<<<"):
            opened = True
            separator = False
        elif opened and line == "=======":
            separator = True
        elif opened and separator and line.startswith(">>>>>>>"):
            return True
    return False


def validate_content(logical_path: str, data: bytes, *, luac: str | None = None) -> tuple[str, str]:
    try:
        text, _ = decode_text(data)
    except (UnicodeError, ValueError):
        return "encoding_conflict", "Only reversible UTF-8 LF/CRLF text is supported"
    if has_conflict_markers(text):
        return "validation_error", "Unresolved conflict marker block"
    suffix = Path(logical_path).suffix.casefold()
    if suffix == ".xml":
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.IGNORECASE):
            return "validation_error", "DTD/entities are forbidden"
        try:
            ElementTree.fromstring(text)
        except ElementTree.ParseError:
            return "validation_error", "XML is not well-formed"
    if suffix == ".lua":
        executable = (
            luac or shutil.which("luac5.3") or shutil.which("luac53") or shutil.which("luac")
        )
        if not executable:
            return "needs_review", "Lua 5.3 syntax validator is unavailable"
        try:
            result = subprocess.run(
                [executable, "-v"],
                capture_output=True,
                shell=False,
                timeout=5,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            version = (result.stdout + result.stderr).decode("utf-8", errors="replace")
            if result.returncode != 0 or not re.search(r"\bLua 5\.3(?:\.|\s|$)", version):
                return "needs_review", "Lua validator must be version 5.3"
            with tempfile.TemporaryDirectory(prefix="cc2-mce-lua-") as temporary:
                script = Path(temporary) / "input.lua"
                script.write_bytes(text.encode("utf-8"))
                result = subprocess.run(
                    [executable, "-p", str(script)],
                    capture_output=True,
                    shell=False,
                    timeout=5,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            if result.returncode != 0:
                return "validation_error", "Lua 5.3 syntax validation failed"
        except (OSError, subprocess.TimeoutExpired):
            return "tool_error", "Lua syntax validator failed or timed out"
    return "valid", ""
