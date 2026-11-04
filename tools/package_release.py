"""Build reviewable Windows beta/source assets. Does not publish or read player mods."""

from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import re
import shutil
import subprocess
import sys
import time
import tkinter
import uuid
import zipfile
from pathlib import Path

from cc2_mce import APP_EXECUTABLE, __version__
from cc2_mce.errors import InputError
from cc2_mce.filesystem import normalize_logical_path
from cc2_mce.reports import engine_hash

ZIG_SOURCE_ARCHIVE_SHA256 = "3a0ed1e8799a2f8ce2a6e6290a9ff22e6906f8227865911fb7ddedc3cc14cb0c"


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


def project_source_files(
    payload: bytes, prefix: str, report: dict, deferred: dict[str, bytes]
) -> dict[str, bytes]:
    """Match actual archived inputs, allowing only explicit hash-verified build dependencies."""
    normalize_logical_path(prefix.removesuffix("/"))
    files = {}
    seen = set()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for entry in archive.infolist():
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Source archive link forbidden")
            if not entry.filename.startswith(prefix):
                raise ValueError("Unexpected source archive root")
            name = entry.filename[len(prefix) :].removesuffix("/")
            if not name and entry.is_dir():
                continue
            _, key = normalize_logical_path(name)
            if key in seen:
                raise ValueError("Source archive path collision")
            seen.add(key)
            if not entry.is_dir():
                files[name] = archive.read(entry)
    validate_source_names([name for name in files if name not in deferred])
    required = {
        "build_windows.bat",
        "pyproject.toml",
        "uv.lock",
        "CC2ModLoader-0.1.0.spec",
        "tools/check_windows_bundle.py",
        "tools/prepare_windows_tools.py",
        "tools/windows_tool_archive.py",
        "tools/prepare_windows_runtime.py",
        "distribution/windows-runtime.json",
        "distribution/windows-build-tools.json",
    }
    if not required <= files.keys():
        raise ValueError("Source archive omits a required self-build input")
    expected: dict[str, str] = {}
    for field in ("source_sha256", "build_input_sha256"):
        for name, digest in report[field].items():
            name = name.replace("\\", "/")
            normalize_logical_path(name)
            if name in expected and expected[name] != digest:
                raise ValueError("Inconsistent source build provenance: " + name)
            expected[name] = digest
    for name, digest in expected.items():
        data = files.get(name, deferred.get(name))
        if data is None:
            raise ValueError("Source archive omits a recorded build input: " + name)
        if sha(data) != digest:
            # Git archives normalize tracked EOL. Restore only a reversible
            # line-ending representation whose hash is already certified.
            if name not in files:
                raise ValueError("Deferred build dependency checksum mismatch: " + name)
            lf = data.replace(b"\r\n", b"\n")
            data = next(
                (
                    candidate
                    for candidate in (lf, lf.replace(b"\n", b"\r\n"))
                    if sha(candidate) == digest
                ),
                None,
            )
            if data is None:
                raise ValueError("Archived source does not match the frozen build: " + name)
            files[name] = data
    return {prefix + name: data for name, data in files.items()}


def write_zip(path: Path, contents: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(contents.items()):
            normalize_logical_path(name)
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def native_runtime_assets(
    root: Path, sdk: Path | None
) -> tuple[dict[str, bytes], list[dict], bytes | None]:
    """Package the reviewed dependency separately from source; never execute it."""
    profile = json.loads((root / "cc2_mce/profiles/windows-1.5.18-r2.json").read_text())
    review = profile.get("runtime_review")
    if not review:
        return {}, [], None
    expected = profile["runtime_sha256"]
    relative = "cc2_mce/runtime_data/" + expected
    folder = root / relative
    runtime = (folder / "dinput8.dll").read_bytes()
    if sha(runtime) != expected:
        raise ValueError("Reviewed runtime checksum mismatch")
    provenance = json.loads((folder / "dinput8.build.json").read_text())
    if provenance["source_dirty"] or provenance["source_commit"] != review["source_commit"]:
        raise ValueError("Runtime provenance mismatch")
    if sdk is None:
        raise ValueError("The reviewed SDK source checkout is required: --sdk PATH")
    sdk = sdk.resolve(strict=True)
    source = subprocess.check_output(
        ["git", "archive", "--format=zip", "--prefix=CC2X-source/", review["source_commit"]],
        cwd=sdk,
    )
    with zipfile.ZipFile(io.BytesIO(source)) as archive:
        source_files = {
            item.filename: archive.read(item) for item in archive.infolist() if not item.is_dir()
        }
        generated = {
            "build/unified/generated/sdk_data.h",
            "build/unified/generated/ui_library_shim_source.h",
            "build/unified/generated/waypoint_origin_profile.h",
            "build/unified/generated/world_constants.inc",
        }
        for name, digest in provenance["source_sha256"].items():
            normalize_logical_path(name)
            key = "CC2X-source/" + name
            if name in generated:
                data = (sdk / name).read_bytes()
            else:
                data = source_files[key]
                if sha(data) != digest:
                    # Git may normalize tracked source EOL while the certified
                    # Windows build used CRLF. Only that reversible conversion
                    # is allowed; never substitute arbitrary working-tree code.
                    data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            if sha(data) != digest:
                raise ValueError("Corresponding SDK source mismatch: " + name)
            source_files[key] = data
    encoded = io.BytesIO()
    with zipfile.ZipFile(encoded, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(source_files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    source = encoded.getvalue()
    contents = {relative + "/" + p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}
    components = [
        {
            "type": "library",
            "name": "CC2X",
            "version": review["runtime_version"],
            "licenses": [{"license": {"id": "GPL-3.0-or-later"}}],
            "hashes": [{"alg": "SHA-256", "content": expected}],
            "externalReferences": [{"type": "vcs", "url": review["source_url"]}],
            "properties": [{"name": "review-stage", "value": review["stage"]}],
        },
        {
            "type": "library",
            "name": "Lua (CC2X runtime)",
            "version": "5.3.6",
            "licenses": [{"license": {"id": "MIT"}}],
        },
    ]
    for name in ("libcxx", "libcxxabi", "libunwind"):
        if not (folder / (name + "-LICENSE.txt")).is_file():
            raise ValueError("Missing native runtime notice: " + name)
        components.append(
            {
                "type": "library",
                "name": name,
                "version": "20.1.0 (Zig 0.15.2)",
                "licenses": [{"expression": "Apache-2.0 WITH LLVM-exception"}],
            }
        )
    return contents, components, source


def native_toolchain_sources(root: Path, zig: Path | None) -> dict[str, bytes]:
    """Keep linked compiler runtime/standard library sources with the candidate."""
    profile = json.loads((root / "cc2_mce/profiles/windows-1.5.18-r2.json").read_text())
    if "runtime_review" not in profile:
        return {}
    if zig is None:
        raise ValueError("The matching SDK toolchain is required: --zig PATH")
    folder = root / "cc2_mce/runtime_data" / profile["runtime_sha256"]
    report = json.loads((folder / "dinput8.build.json").read_text())
    zig = zig.resolve(strict=True)
    if sha(zig.read_bytes()) != report["compiler_sha256"]:
        raise ValueError("Native toolchain checksum mismatch")
    provider = zig.parent
    contents = {}
    for path in sorted((provider / "lib").rglob("*")):
        if path.is_file():
            name = path.relative_to(provider).as_posix()
            normalize_logical_path(name)
            contents["Zig-0.15.2/" + name] = path.read_bytes()
    if not contents:
        raise ValueError("Missing compiler runtime sources")
    contents["Zig-0.15.2/LICENSE"] = (provider / "LICENSE").read_bytes()
    contents["SOURCE-MANIFEST.json"] = (
        json.dumps(
            {
                "provider": "Zig 0.15.2",
                "compiler_sha256": report["compiler_sha256"],
                "source": "https://ziglang.org/download/0.15.2/zig-x86_64-windows-0.15.2.zip",
                "archive_sha256": ZIG_SOURCE_ARCHIVE_SHA256,
                "files": {name: sha(data) for name, data in sorted(contents.items())},
            },
            indent=2,
        )
        + "\n"
    ).encode()
    return contents


def finalize_release(staging: Path, destination: Path) -> None:
    for attempt in range(40):
        if destination.exists():
            raise ValueError("A previous release is never overwritten")
        try:
            staging.rename(destination)
            return
        except PermissionError:
            # Windows scanners can briefly retain a newly written asset handle.
            # Keep the complete staging directory and preserve atomic promotion.
            if attempt == 39:
                raise
            time.sleep(0.5)


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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sdk", type=Path, help="matching CC2X source checkout for corresponding sources"
    )
    parser.add_argument("--zig", type=Path, help="matching SDK compiler for linked runtime sources")
    args = parser.parse_args()
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
    native_files, native_components, sdk_source = native_runtime_assets(root, args.sdk)
    components += native_components
    for name, data in native_files.items():
        if not name.endswith("/dinput8.dll"):
            notices["LICENSES/CC2X/" + Path(name).name] = data
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
    (output / APP_EXECUTABLE).write_bytes(payload)
    (output / (APP_EXECUTABLE + ".sha256")).write_text(
        sha(payload) + "  " + APP_EXECUTABLE + "\n", encoding="ascii", newline="\n"
    )
    if native_files:
        write_zip(output / (prefix + "-sdk-runtime.zip"), native_files)
        assert sdk_source is not None
        (output / (prefix + "-sdk-source.zip")).write_bytes(sdk_source)
        write_zip(
            output / (prefix + "-sdk-toolchain-sources.zip"),
            native_toolchain_sources(root, args.zig),
        )
    tools = json.loads((root / "distribution/windows-build-tools.json").read_text())
    tool_archive = root / "build" / tools["file"]
    tool_payload = tool_archive.read_bytes()
    if sha(tool_payload) != tools["sha256"]:
        raise ValueError("Build toolchain checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(tool_payload)) as archive:
        deferred = {"cc2_mce/tools_data/manifest.json": archive.read("tools_data/manifest.json")}
    deferred.update(
        {name: data for name, data in native_files.items() if name.endswith("/dinput8.dll")}
    )
    source_prefix = prefix + "-source/"
    source_archive = subprocess.check_output(
        ["git", "archive", "--format=zip", "--prefix=" + source_prefix, revision], cwd=root
    )
    write_zip(
        output / (prefix + "-source.zip"),
        project_source_files(source_archive, source_prefix, report, deferred),
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
    shutil.copy2(tool_archive, output / tool_archive.name)
    (output / "SHA256SUMS.txt").write_text(
        "".join(
            sha(p.read_bytes()) + "  " + p.name + "\n"
            for p in sorted(output.iterdir())
            if p.is_file()
        ),
        encoding="ascii",
        newline="\n",
    )
    finalize_release(output, destination)
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
