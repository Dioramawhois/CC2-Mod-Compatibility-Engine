"""Build reviewable Windows beta/source assets. Does not publish or read player mods."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import tkinter
import uuid
import zipfile
from pathlib import Path

from cc2_mce import APP_EXECUTABLE, __version__
from cc2_mce.errors import InputError
from cc2_mce.filesystem import normalize_logical_path
from cc2_mce.reports import engine_hash


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def public_build_report(report: dict) -> dict:
    fields = {
        "version",
        "artifact",
        "artifact_sha256",
        "artifact_bytes",
        "engine_sha256",
        "source_sha256",
        "build_input_sha256",
        "regressions",
        "git_and_lua_bundled",
        "gui_opened_and_closed",
        "clean_machine_tested",
        "macos_tested",
    }
    public = {key: value for key, value in report.items() if key in fields}
    for field in ("source_sha256", "build_input_sha256"):
        for filename, digest in public.get(field, {}).items():
            try:
                normalize_logical_path(filename.replace("\\", "/"))
            except InputError as exc:
                raise ValueError("Private/unsafe build path") from exc
            if not re.fullmatch("[a-f0-9]{64}", digest):
                raise ValueError("Invalid build checksum")
    return public


def validate_source_names(names: list[str]) -> None:
    if "LICENSE" not in names:
        raise ValueError("A source release needs LICENSE")
    blocked = {"build", "dist", "research", ".git", ".deps", ".cache", "tools_data"}
    for name in names:
        try:
            logical, _ = normalize_logical_path(name)
        except InputError as exc:
            raise ValueError("Unsafe source path") from exc
        path = Path(logical)
        if (
            blocked.intersection(path.parts)
            or path.name == ".env"
            or path.suffix.lower() in {".exe", ".dll", ".pdb"}
        ):
            raise ValueError("Private or compiled file in source release: " + name)


def write_zip(path: Path, contents: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(contents.items()):
            normalize_logical_path(name)
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def runtime_notices(root: Path) -> tuple[dict[str, bytes], list[dict]]:
    files = {}
    components = []
    for name in (
        "jsonschema",
        "jsonschema-specifications",
        "attrs",
        "referencing",
        "rpds-py",
        "pyinstaller",
    ):
        package = importlib.metadata.distribution(name)
        found = 0
        for item in package.files or ():
            if not any(word in item.name.lower() for word in ("license", "copying", "notice")):
                continue
            if ".." in item.parts:
                continue
            data = package.locate_file(item).read_bytes()
            files["LICENSES/" + name + "/" + item.as_posix()] = data
            found += 1
        if not found:
            raise ValueError("Missing component notices: " + name)
        components.append({"type": "library", "name": name, "version": package.version})
    python = Path(sys.base_prefix)
    files["LICENSES/CPython/LICENSE.txt"] = (python / "LICENSE.txt").read_bytes()
    for name in ("tcl8.6", "tk8.6"):
        license_file = python / "tcl" / name / "license.terms"
        # Official Windows CPython includes Tcl's notice in LICENSE.txt even
        # when the standalone Tcl license.terms is absent. Keep that file whole.
        data = (
            license_file.read_bytes()
            if license_file.exists()
            else (python / "LICENSE.txt").read_bytes()
        )
        if b"Scriptics Corporation" not in data:
            raise ValueError("Missing Tcl/Tk redistribution notice")
        files["LICENSES/" + name + "/license.terms"] = data
        if name.startswith("tcl"):
            version = tkinter.Tcl().eval("info patchlevel")
        else:
            script = (python / "tcl" / name / "tk.tcl").read_text(encoding="utf-8")
            match = re.search(r"package require -exact Tk\s+([0-9.]+)", script)
            if match is None:
                raise ValueError("Missing exact Tk version")
            version = match.group(1)
        components.append({"type": "framework", "name": name, "version": version})
    components.append({"type": "framework", "name": "CPython", "version": sys.version.split()[0]})
    for file in sorted((root / "cc2_mce/tools_data/notices").rglob("*")):
        if file.is_file():
            files[
                "LICENSES/tools/" + file.relative_to(root / "cc2_mce/tools_data/notices").as_posix()
            ] = file.read_bytes()
    return files, components


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip():
        raise ValueError("Commit the reviewed release sources before packaging")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    executable = root / "dist" / APP_EXECUTABLE
    report = json.loads(executable.with_suffix(".build.json").read_text(encoding="utf-8"))
    payload = executable.read_bytes()
    if (
        report["version"] != __version__
        or report["artifact_sha256"] != sha(payload)
        or report["engine_sha256"] != engine_hash()
    ):
        raise ValueError("Frozen artifact does not match this source tree")
    counts = report.get("regressions", {})
    if not counts.get("passed") or counts.get("errors") or counts.get("failures"):
        raise ValueError("A passing regression report is required")
    for relative, expected in report["source_sha256"].items():
        if sha((root / relative).read_bytes()) != expected:
            raise ValueError("Packaged source changed: " + relative)
    destination = root / "dist" / ("release-" + __version__)
    if destination.exists():
        raise ValueError("A previous release is never overwritten")
    output = root / "dist" / (".release-" + uuid.uuid4().hex)
    output.mkdir()
    prefix = "CC2ModLoader-" + __version__
    public = public_build_report(report)
    public.update(
        {
            "source_commit": revision,
            "channel": "windows-beta",
            "project_license": "GPL-3.0-or-later",
            "game_runtime_tested": False,
            "packaged_macos_certified": False,
        }
    )
    notices, components = runtime_notices(root)
    manifest = json.loads((root / "cc2_mce/tools_data/manifest.json").read_text())
    components += [
        {"type": "application", "name": "Git for Windows", "version": manifest["git_version"]},
        {"type": "application", "name": "Lua syntax validator", "version": manifest["lua_version"]},
    ]
    lock = json.loads((root / "distribution/windows-source-lock.json").read_text())
    versions = {item["component"]: item["version"] for item in lock["sources"]}
    for filename, digest in manifest["files"].items():
        components.append(
            {
                "type": "file",
                "name": filename,
                "hashes": [{"alg": "SHA-256", "content": digest}],
            }
        )
    for name in ("libiconv", "gettext", "pcre2", "zlib"):
        components.append({"type": "library", "name": name, "version": versions[name]})
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "CC2 ModLoader",
                "version": __version__,
                "licenses": [{"license": {"id": "GPL-3.0-or-later"}}],
            }
        },
        "components": components,
    }
    contents = {
        APP_EXECUTABLE: payload,
        "LICENSE": (root / "LICENSE").read_bytes(),
        "NOTICE.md": (root / "NOTICE.md").read_bytes(),
        "README.txt": (root / "distribution/PLAYER_README.txt").read_bytes(),
        "RELEASE.json": (json.dumps(public, indent=2) + "\n").encode(),
        "SBOM.cdx.json": (json.dumps(sbom, indent=2) + "\n").encode(),
        **notices,
    }
    write_zip(output / (prefix + "-windows-x64.zip"), contents)
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")[:-1]
    validate_source_names(names)
    with (output / (prefix + "-source.zip")).open("xb") as stream:
        subprocess.run(
            ["git", "archive", "--format=zip", "--prefix=" + prefix + "-source/", revision],
            cwd=root,
            stdout=stream,
            check=True,
        )
    lock = json.loads((root / "distribution/windows-source-lock.json").read_text())
    cache = root / "build/release-sources"
    sources = {"SOURCE-MANIFEST.json": (json.dumps(lock, indent=2) + "\n").encode()}
    for item in lock["sources"]:
        data = (cache / item["file"]).read_bytes()
        if sha(data) != item["sha256"]:
            raise ValueError("Corresponding source checksum mismatch: " + item["component"])
        sources[item["file"]] = data
    for relative, expected in lock["recipe_files"].items():
        data = (cache / relative).read_bytes()
        if sha(data) != expected:
            raise ValueError("Build recipe checksum mismatch")
        sources[relative] = data
    lua = root / "cc2_mce/tools_data/notices/lua-5.3.6.tar.gz"
    if sha(lua.read_bytes()) != manifest["lua_source_sha256"]:
        raise ValueError("Lua source checksum mismatch")
    sources[lua.name] = lua.read_bytes()
    write_zip(output / (prefix + "-tool-sources.zip"), sources)
    tools = json.loads((root / "distribution/windows-build-tools.json").read_text())
    archive = root / "build" / tools["file"]
    if sha(archive.read_bytes()) != tools["sha256"]:
        raise ValueError("Build toolchain checksum mismatch")
    shutil.copy2(archive, output / archive.name)
    (output / "SHA256SUMS.txt").write_text(
        "".join(
            sha(p.read_bytes()) + "  " + p.name + "\n"
            for p in sorted(output.iterdir())
            if p.is_file()
        ),
        encoding="ascii",
    )
    output.rename(destination)
    print(
        json.dumps(
            {
                "version": __version__,
                "source_commit": revision,
                "output": str(destination),
                "assets": [p.name for p in destination.iterdir()],
            }
        )
    )


if __name__ == "__main__":
    main()
