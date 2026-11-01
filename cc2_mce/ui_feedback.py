"""Plain-language feedback for a rejected checkbox change; no filesystem or mod execution."""

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
) -> Rejection:
    names = {
        **(known_names or {}),
        **{source["id"]: source["name"] for source in report["sources"]},
    }

    def display(keys: set[str]) -> str:
        ordered = sorted(keys)
        result = ", ".join(f"«{names.get(key, 'мод')[:80]}»" for key in ordered[:3])
        return result + (f" и ещё {len(ordered) - 3}" if len(ordered) > 3 else "")

    added, removed = requested - applied, applied - requested
    changed = added or removed
    action = "включить" if added else "отключить"
    title = (
        f"Не удалось {action} " + display(changed) if changed else "Обновление модов не применено"
    )
    messages = {
        "no_base": "Не найдены проверенные оригиналы для этой версии игры.",
        "native_plugin_review_required": "Эта версия DLL-плагина пока не поддерживается.",
        "validation_error": "Получившийся файл не прошёл проверку синтаксиса.",
        "tool_error": "Не удалось выполнить встроенную проверку файлов.",
        "unsupported_binary": "Эти двоичные ресурсы нельзя автоматически объединить.",
        "input_error": "Исходные файлы изменились или недоступны.",
        "encoding_conflict": "Файлы используют несовместимые кодировки.",
        "needs_review": "Это изменение пока нельзя безопасно подключить.",
        "runtime_missing": "Не найден поддерживаемый загрузчик CC2X.",
        "runtime_conflict": "Установленный загрузчик CC2X не подходит этому набору.",
        "sdk_api": "Для этой библиотеки нужна другая версия SDK.",
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
            reason = "Несовместимые изменения" + (": " + named if named else "") + "."
        else:
            reason = messages.get(blocker["code"], blocker.get("message", "Проверка не пройдена."))
        if not first_message:
            first_message = reason
        details.append(("Файл: " + logical + "\n" if logical else "") + reason)
        for key in added or participants:
            other_names = display(participants - {key})
            rows[key] = (
                (
                    "Не включён: конфликт с " + other_names
                    if key in added and key in participants and other_names
                    else "Не включён: выбранный набор несовместим"
                    if key in added
                    else "В игре сохранена предыдущая версия"
                )
                if blocker["code"] == "conflict"
                else reason
            )
    return Rejection(title, first_message, "\n\n".join(details), rows)
