"""Bounded, local diagnostics for failures that do not produce a package plan."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from cc2_mce import __version__
from cc2_mce.errors import DiagnosticError
from cc2_mce.reports import engine_hash

_LAUNCH_GUARDS = {
    "Pending activation recovery; close the game before retrying": (
        "launch_recovery_pending",
        "Восстановление не завершено. Запуск игры заблокирован.",
    ),
    "Game is running or its executable is unavailable": (
        "launch_game_unavailable",
        "Игра уже запущена или её файл недоступен. Закройте игру и проверьте файлы игры.",
    ),
    "Game activation changed; rebuild the selected set": (
        "launch_activation_changed",
        "Набор модов в игре изменился. Обновите список, чтобы пересобрать его.",
    ),
    "Game executable changed since activation": (
        "launch_game_changed",
        "Файлы игры изменились. Обновите список, чтобы проверить набор заново.",
    ),
    "Installed runtime changed since activation": (
        "launch_runtime_changed",
        "Загрузчик SDK изменился. Обновите список, чтобы проверить набор заново.",
    ),
}
_LAUNCH_SUMMARIES = {code: message for code, message in _LAUNCH_GUARDS.values()}
_MAX_EXPORTED_DIAGNOSTICS = 200


@dataclass(frozen=True)
class Diagnostic:
    code: str
    stage: str
    cause: str
    source_id: str = ""
    source_name: str = ""
    source_path: str = ""
    resource_path: str = ""
    package_id: str = ""
    source_revision: str = ""

    def __post_init__(self) -> None:
        for field, maximum in (
            ("code", 96),
            ("stage", 32),
            ("cause", 4096),
            ("source_id", 256),
            ("source_name", 256),
            ("source_path", 2048),
            ("resource_path", 2048),
            ("package_id", 256),
            ("source_revision", 128),
        ):
            value = getattr(self, field)
            object.__setattr__(self, field, str(value)[:maximum])

    def summary(self, translate: Callable[..., str] | None = None) -> str:
        tr = translate or (lambda message, **values: message.format(**values))
        if self.code in _LAUNCH_SUMMARIES:
            return tr(_LAUNCH_SUMMARIES[self.code])
        if self.stage == "launch" or self.code == "launch_failed":
            return tr("Игра не запущена. Проверьте подробности проблемы.")
        if self.code in {"discovery_limit", "discovery_global_limit"}:
            message = tr(
                "Превышен предел чтения модов. Уменьшите набор папок и проверьте подробности."
            )
            name = self.source_name or self.source_id
            return f"«{name}»: {message}" if name else message
        if self.source_id or self.source_name:
            return tr(
                "Не удалось прочитать мод «{p0}». Проверьте его папку или обновите мод.",
                p0=self.source_name or self.source_id,
            )
        if self.code == "discovery_root" or self.stage == "discovery":
            return tr("Не удалось прочитать папку модов. Проверьте доступ к ней.")
        return tr("Операция прервалась. Повторите проверку или верните прежний набор.")

    def details(self, translate: Callable[..., str] | None = None) -> str:
        tr = translate or (lambda message, **values: message.format(**values))
        lines = [self.summary(translate)]
        if self.source_path:
            lines.append(tr("Источник: ") + self.source_path)
        if self.resource_path:
            lines.append(tr("Файл: ") + self.resource_path)
        lines.append(tr("Причина: ") + self.cause)
        return "\n".join(lines)

    def report(self) -> dict[str, str]:
        return {
            "code": self.code,
            "stage": self.stage,
            "cause": self.cause,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_path": self.source_path,
            "resource_path": self.resource_path,
            "package_id": self.package_id,
            "source_revision": self.source_revision,
        }


def error_diagnostic(
    exc: BaseException,
    *,
    stage: str,
    source_id: str = "",
    source_name: str = "",
    source_path: Path | str | None = None,
    resource_path: Path | str | None = None,
    package_id: str = "",
    source_revision: str = "",
    code: str | None = None,
) -> Diagnostic:
    if isinstance(exc, DiagnosticError):
        return replace(exc.diagnostic, stage=stage)
    message = str(exc)
    causes = [message]
    nested = exc.__cause__
    for _ in range(2):
        if nested is None:
            break
        detail = str(nested)
        if detail and detail not in causes:
            causes.append(detail)
        nested = nested.__cause__
    if code is None:
        if stage == "launch":
            code = _LAUNCH_GUARDS.get(message, ("launch_failed", ""))[0]
        elif "byte limit" in message or "entry limit" in message or "depth limit" in message:
            code = "discovery_limit"
        elif stage == "discovery":
            code = "discovery_package" if source_id or source_name else "discovery_root"
        else:
            code = "operation_failed"
    return Diagnostic(
        code,
        stage,
        "\n".join(causes),
        source_id,
        source_name,
        str(source_path) if source_path is not None else "",
        str(resource_path) if resource_path is not None else "",
        package_id,
        source_revision,
    )


def diagnostic_envelope(items: Iterable[Diagnostic], *, stage: str) -> dict[str, Any]:
    diagnostics: list[dict[str, str]] = []
    count = 0
    for item in items:
        count += 1
        if len(diagnostics) < _MAX_EXPORTED_DIAGNOSTICS:
            diagnostics.append(item.report())
    return {
        "schema_version": 1,
        "schema_kind": "diagnostics",
        "owner": "cc2-mce",
        "engine_version": __version__,
        "engine_sha256": engine_hash(),
        "stage": stage[:32],
        "installable": False,
        "diagnostic_count": count,
        "truncated": count > len(diagnostics),
        "diagnostics": diagnostics,
    }
