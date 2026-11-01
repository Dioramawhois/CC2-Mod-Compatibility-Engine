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
        "needs_review": tr("Это изменение пока нельзя безопасно подключить."),
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
        else:
            reason = messages.get(
                blocker["code"], blocker.get("message", tr("Проверка не пройдена."))
            )
        if not first_message:
            first_message = reason
        details.append((tr("Файл: ") + logical + "\n" if logical else "") + reason)
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
