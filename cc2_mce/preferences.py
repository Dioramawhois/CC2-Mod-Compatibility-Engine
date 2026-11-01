"""Bounded, atomic GUI preferences; no player-edited configuration is required."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cc2_mce.errors import InputError
from cc2_mce.filesystem import Budget, Limits, input_root, read_regular


@dataclass
class Preferences:
    root: Path
    language: str = "system"
    patch_priority: bool = True
    orders: dict[str, list[str]] = field(default_factory=dict)
    extra_roots: list[str] = field(default_factory=list)
    _original: bytes | None = None

    @classmethod
    def load(cls, root: Path) -> Preferences:
        result = cls(root)
        path = root / "preferences.json"
        if not path.exists() and not path.is_symlink():
            return result
        raw = read_regular(path, input_root(root), Budget(Limits(max_file_bytes=65536)))
        try:
            value = json.loads(raw)
            if (
                value["owner"] != "cc2-mce"
                or value["schema_version"] != 1
                or value["language"] not in {"system", "ru", "en"}
                or type(value["patch_priority"]) is not bool
                or not isinstance(value["orders"], dict)
                or not isinstance(value["extra_roots"], list)
            ):
                raise ValueError()
            if len(value["orders"]) > 64 or len(value["extra_roots"]) > 64:
                raise ValueError()
            for key, order in value["orders"].items():
                if (
                    not isinstance(key, str)
                    or not isinstance(order, list)
                    or len(order) > 20000
                    or any(not isinstance(item, str) or len(item) > 256 for item in order)
                    or len(set(order)) != len(order)
                ):
                    raise ValueError()
            if any(not isinstance(item, str) for item in value["extra_roots"]):
                raise ValueError()
        except (ValueError, KeyError, TypeError) as exc:
            raise InputError("Не удалось прочитать настройки приложения.") from exc
        result.language = value["language"]
        result.patch_priority = value["patch_priority"]
        result.orders = value["orders"]
        result.extra_roots = value["extra_roots"]
        result._original = raw
        return result

    def order(self, game: Path) -> list[str]:
        return list(self.orders.get(str(game), []))

    def set_order(self, game: Path, order: list[str]) -> None:
        self.orders[str(game)] = list(dict.fromkeys(order))

    def save(self) -> None:
        input_root(self.root.parent)
        self.root.mkdir(exist_ok=True)
        root = input_root(self.root)
        path = root / "preferences.json"
        value: dict[str, Any] = {
            "owner": "cc2-mce",
            "schema_version": 1,
            "language": self.language,
            "patch_priority": self.patch_priority,
            "orders": self.orders,
            "extra_roots": self.extra_roots,
        }
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
        if len(raw) > 65536:
            raise InputError("Настройки приложения превышают допустимый размер.")
        current = (
            read_regular(path, root, Budget(Limits(max_file_bytes=65536)))
            if path.exists()
            else None
        )
        if current != self._original:
            raise InputError("Настройки изменены другой копией приложения.")
        temporary = root / (".preferences-" + uuid.uuid4().hex)
        try:
            with temporary.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            self._original = raw
        finally:
            temporary.unlink(missing_ok=True)
