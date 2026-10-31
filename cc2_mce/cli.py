from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any, NoReturn

from cc2_mce import __version__
from cc2_mce.baseline import load_baseline, parse_json
from cc2_mce.discovery import ModRef, discover
from cc2_mce.doctor import diagnose, steam_workshop_candidates
from cc2_mce.errors import InputError, MCEError
from cc2_mce.filesystem import Budget, Limits, input_root, read_regular
from cc2_mce.planner import plan
from cc2_mce.reports import envelope, validate_report, write_report


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise InputError(message)


def parser() -> Parser:
    result = Parser(
        prog="cc2-mce", description="Read-only CC2 mod analysis; no package installation"
    )
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument("--config", type=Path)
    sub = result.add_subparsers(dest="command", required=True, parser_class=Parser)
    for command in ("doctor", "scan", "plan", "build", "report"):
        child = sub.add_parser(command)
        if command == "report":
            child.add_argument("report_json", type=Path)
            continue
        child.add_argument("--json", "--report", dest="report_path", type=Path)
        if command in ("doctor", "plan", "build"):
            child.add_argument("--baseline", type=Path)
            child.add_argument("--game-executable", type=Path)
            child.add_argument("--luac")
            child.add_argument("--git")
        if command == "doctor":
            child.add_argument("--game", type=Path)
        else:
            child.add_argument("--mods-dir", action="append", type=Path, default=[])
            child.add_argument("--workshop-dir", action="append", type=Path, default=[])
            if command in ("plan", "build"):
                child.add_argument("--mods", nargs="+")
                child.add_argument("--output", type=Path)
        if command == "build":
            child.add_argument("--dry-run", action="store_true")
            child.add_argument("--plan", type=Path)
    return result


def _configuration(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    root = input_root(path.parent)
    raw = read_regular(path.absolute(), root, Budget(Limits()))
    try:
        config = tomllib.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise InputError("Invalid TOML configuration") from exc
    allowed = {
        "schema_version",
        "profile",
        "game_dir",
        "baseline_dir",
        "local_mods_dir",
        "workshop_dirs",
        "output_dir",
        "mod_order",
        "strict_validation",
        "native_plugin_policy",
        "binary_conflict_policy",
    }
    if (
        set(config) - allowed
        or type(config.get("schema_version")) is not int
        or config["schema_version"] != 1
    ):
        raise InputError("Unsupported configuration fields/schema version")
    if config.get("strict_validation", True) is not True or any(
        config.get(key, "block") != "block"
        for key in ("native_plugin_policy", "binary_conflict_policy")
    ):
        raise InputError("Only strict validation and block policies are implemented")
    for key in ("workshop_dirs", "mod_order"):
        if key in config and (
            not isinstance(config[key], list) or not all(isinstance(v, str) for v in config[key])
        ):
            raise InputError("Config arrays must contain strings")
    for key in ("game_dir", "baseline_dir", "local_mods_dir", "output_dir"):
        if key in config:
            if not isinstance(config[key], str):
                raise InputError("Config paths must be strings")
            value = Path(config[key]).expanduser()
            config[key] = value if value.is_absolute() else root / value
    if "workshop_dirs" in config:
        config["workshop_dirs"] = [
            Path(v).expanduser() if Path(v).expanduser().is_absolute() else root / v
            for v in config["workshop_dirs"]
        ]
    return config


def _select(mods: tuple[ModRef, ...], selectors: list[str]) -> list[ModRef]:
    selected: list[ModRef] = []
    for value in selectors:
        matches = [
            mod for mod in mods if mod.id == value or str(mod.root) == str(Path(value).resolve())
        ]
        if len(matches) != 1 or matches[0] in selected:
            raise InputError("Unknown, ambiguous or duplicate selected mod")
        selected.append(matches[0])
    return selected


def _output_check(output: Path | None, protected: list[Path]) -> None:
    if output is None:
        return
    resolved = output.resolve()
    for root in protected:
        root = root.resolve()
        if resolved.is_relative_to(root) or root.is_relative_to(resolved):
            raise InputError("Output and input roots must not intersect")


def execute(
    args: argparse.Namespace, config: dict[str, Any]
) -> tuple[dict[str, object], int, list[Path]]:
    command = args.command
    protected: list[Path] = []
    baseline_path = getattr(args, "baseline", None) or config.get("baseline_dir")
    game = getattr(args, "game", None) or config.get("game_dir")
    for path in (baseline_path, game, getattr(args, "game_executable", None)):
        if path:
            protected.append(path if path.is_dir() else path.parent)
    if command == "report":
        root = input_root(args.report_json.parent)
        data = read_regular(args.report_json.absolute(), root, Budget(Limits()))
        loaded_report = validate_report(parse_json(data))
        return loaded_report, 2 if loaded_report["status"] == "blocked" else 0, protected
    if command == "doctor":
        report, code = diagnose(
            game=game,
            baseline=baseline_path,
            game_executable=args.game_executable,
            luac=args.luac,
            git=args.git,
        )
        return report, code, protected
    if command == "build" and args.plan is not None:
        report = envelope("build")
        report.update(
            status="blocked",
            blockers=[
                {
                    "code": "unsupported_plan_replay",
                    "message": "Replaying a saved plan is not implemented yet",
                }
            ],
        )
        return report, 2, protected
    roots = list(args.mods_dir) + list(args.workshop_dir)
    if config.get("local_mods_dir"):
        roots.append(config["local_mods_dir"])
    roots.extend(config.get("workshop_dirs", []))
    selectors = getattr(args, "mods", None) or config.get("mod_order") or []
    for value in selectors:
        if Path(value).is_dir():
            roots.append(Path(value))
    if not roots:
        roots = steam_workshop_candidates()
    if not roots:
        raise InputError("No mod roots found; specify --mods-dir/--workshop-dir or --config")
    protected.extend(roots)
    output = getattr(args, "output", None) or config.get("output_dir")
    _output_check(output, protected)
    scan = discover(roots)
    if command == "scan":
        report = envelope("scan")
        report["sources"] = [mod.report() for mod in scan.mods]
        report["scan_sha256"] = scan.fingerprint
        report["warnings"] = ["Read-only inventory; not a gameplay or merge compatibility verdict"]
        return report, 0, protected
    selected = _select(scan.mods, selectors)
    baseline = (
        load_baseline(baseline_path, game_executable=args.game_executable)
        if baseline_path
        else None
    )
    report, code, outputs = plan(
        scan, selected, baseline, command=command, luac=args.luac, git_executable=args.git
    )
    if command == "build" and not args.dry_run:
        if output is None:
            blockers: list[dict[str, object]] = [
                {"code": "output_required", "message": "build without --dry-run needs --output"}
            ]
            report["blockers"] = blockers
            report["status"] = "blocked"
            return report, 2, protected
        if report["status"] == "ok":
            # The report stays the read-only v1 schema (installable is const false).
            _write_outputs(Path(output), outputs)
    return report, code, protected

def _write_outputs(root: Path, outputs: dict[str, bytes]) -> None:
    # Only reached after a clean plan. Each logical path is written beneath root.
    root.mkdir(parents=True, exist_ok=True)
    for logical_path, content in sorted(outputs.items()):
        target = (root / logical_path).resolve()
        if root.resolve() not in target.parents:
            raise InputError(f"Refusing to write outside output: {logical_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def main(argv: list[str] | None = None, *, quiet: bool = False) -> int:
    args: argparse.Namespace | None = None
    try:
        args = parser().parse_args(argv)
        config = _configuration(args.config)
        report, code, protected = execute(args, config)
        validate_report(report)
        destination = getattr(args, "report_path", None)
        if destination:
            write_report(report, destination, protected)
    except SystemExit as exc:
        return int(exc.code or 0)
    except (MCEError, OSError, ValueError) as exc:
        report = envelope(getattr(args, "command", "error"))
        # OSError messages contain personal paths; export only a generic diagnostic.
        message = str(exc) if isinstance(exc, MCEError) else "Filesystem or input operation failed"
        error_kind = {3: "no_base", 5: "tool_error"}.get(
            exc.exit_code if isinstance(exc, MCEError) else 4, "input_error"
        )
        report.update(status="blocked", blockers=[{"code": error_kind, "message": message}])
        code = exc.exit_code if isinstance(exc, MCEError) else 4
    if not quiet:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return code
