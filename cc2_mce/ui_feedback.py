"""Plain-language feedback for a rejected checkbox change; no filesystem or mod execution."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Rejection:
    title: str
    message: str
    details: str
    rows: dict[str, str]


@dataclass(frozen=True)
class OverrideWarning:
    title: str
    message: str
    details: str
    rows: dict[str, str]


def explain_overrides(
    report: dict[str, Any], translate: Callable[..., str] | None = None
) -> OverrideWarning | None:
    """Describe reported overrides, never infer incompatibility from file overlap alone."""
    files = [item for item in report["files"] if item["status"] == "overridden"]
    tr = translate or (lambda message, **values: message.format(**values) if values else message)
    if not files:
        return None
    names = {source["id"]: source["name"] for source in report["sources"]}
    risk = tr(
        "Результат в игре неизвестен: часть изменений других модов заменена. "
        "Будьте осторожны. Подробности — в меню."
    )
    strategies = {
        "git-three-way-later-hunks": tr(
            "Спорные участки заменены по порядку; независимые изменения сохранены."
        ),
        "ordered-replacement-no-base": tr(
            "Оригинал не найден: файл заменён целиком последним модом в порядке."
        ),
        "ordered-binary-replacement": tr(
            "Двоичный файл заменён целиком последним модом в порядке."
        ),
    }
    details = [risk]
    rows: dict[str, str] = {}
    summary = ""
    for item in files:
        participants = [key for key in report["mod_order"] if key in item["source_sha256"]]
        ordered_names = " → ".join(f"«{names.get(key, key)[:64]}»" for key in participants)
        if not summary:
            short_names = " → ".join(f"«{names.get(key, key)[:64]}»" for key in participants[:3])
            if len(participants) > 3:
                short_names += tr(" и ещё {p0}", p0=len(participants) - 3)
            summary = item["logical_path"][:120] + ": " + short_names
        details.append(
            tr("Файл: ")
            + item["logical_path"]
            + "\n"
            + tr("Порядок: {p0}. Поздние моды имеют приоритет.", p0=ordered_names)
            + "\n"
            + strategies.get(item["strategy"], item["strategy"])
        )
        for key in participants:
            rows[key] = tr("Включён · есть перезапись изменений")
    if len(files) > 1:
        summary += "\n" + tr("Ещё файлов с перезаписью: {p0}.", p0=len(files) - 1)
    return OverrideWarning(
        tr("Внимание: моды перезаписывают изменения"),
        summary + "\n" + risk,
        "\n\n".join(details),
        rows,
    )


def explain_rejection(
    report: dict[str, Any],
    applied: set[str],
    requested: set[str],
    known_names: dict[str, str] | None = None,
    translate: Callable[..., str] | None = None,
) -> Rejection:
    tr = translate or (lambda message, **values: message.format(**values) if values else message)
    names = {
        **(known_names or {}),
        **{source["id"]: source["name"] for source in report["sources"]},
    }

    def display(keys: set[str]) -> str:
        ordered = sorted(keys)
        result = ", ".join(f"«{names.get(key, tr('мод'))[:80]}»" for key in ordered[:3])
        return result + (tr(" и ещё {p0}", p0=len(ordered) - 3) if len(ordered) > 3 else "")

    added, removed = (requested - applied, applied - requested)
    changed = added or removed
    action = tr("включить") if added else tr("отключить")
    title = (
        tr("Не удалось {p0} ", p0=action) + display(changed)
        if changed
        else tr("Обновление модов не применено")
    )
    messages = {
        "no_base": tr("Не найдены проверенные оригиналы для этой версии игры."),
        "native_plugin_review_required": tr("Эта версия DLL-плагина пока не поддерживается."),
        "validation_error": tr("Получившийся файл не прошёл проверку синтаксиса."),
        "tool_error": tr("Не удалось выполнить встроенную проверку файлов."),
        "unsupported_binary": tr("Эти двоичные ресурсы нельзя автоматически объединить."),
        "input_error": tr("Исходные файлы изменились или недоступны."),
        "encoding_conflict": tr("Файлы используют несовместимые кодировки."),
        "runtime_missing": tr("Не найден поддерживаемый загрузчик CC2X."),
        "runtime_conflict": tr("Установленный загрузчик CC2X не подходит этому набору."),
        "sdk_api": tr("Для этой библиотеки нужна другая версия SDK."),
    }
    details: list[str] = []
    rows: dict[str, str] = {}
    first_message = ""
    for blocker in report["blockers"][:20]:
        logical = blocker.get("file", "")
        participants = next(
            (
                set(item["source_sha256"])
                for item in report["files"]
                if item["logical_path"] == logical
            ),
            set(),
        )
        named = display(participants)
        if blocker["code"] == "conflict":
            reason = tr("Несовместимые изменения") + (": " + named if named else "") + "."
        elif blocker["code"] == "needs_review":
            diagnostic = blocker.get("message", "")
            reason = (
                tr("Приложение пока не поддерживает этот тип файла.")
                if diagnostic == "Unknown resource type"
                else tr("Не работает встроенный проверяющий Lua 5.3. Обновите ModLoader.")
                if diagnostic
                in {
                    "Lua 5.3 syntax validator is unavailable",
                    "Lua validator must be version 5.3",
                }
                else tr("Файл требует проверки: {p0}", p0=diagnostic)
            )
        else:
            reason = messages.get(
                blocker["code"], blocker.get("message", tr("Проверка не пройдена."))
            )
        if not first_message:
            first_message = (logical[:160] + ": " if logical else "") + reason
        details.append(
            (tr("Файл: ") + logical + "\n" if logical else "")
            + reason
            + ("\n" + blocker["message"] if blocker.get("message") else "")
        )
        for key in added or participants:
            other_names = display(participants - {key})
            rows[key] = (
                (
                    tr("Не включён: конфликт с ") + other_names
                    if key in added and key in participants and other_names
                    else tr("Не включён: выбранный набор несовместим")
                    if key in added
                    else tr("В игре сохранена предыдущая версия")
                )
                if blocker["code"] == "conflict"
                else reason
            )
    return Rejection(title, first_message, "\n\n".join(details), rows)
