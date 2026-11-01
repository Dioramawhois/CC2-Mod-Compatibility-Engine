"""OS-released exclusive lock for game activation transactions."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cc2_mce.errors import InputError
from cc2_mce.filesystem import input_root, is_link


@contextmanager
def activation_lock(user_dir: Path) -> Iterator[None]:
    user = input_root(user_dir)
    state = user / "cc2-mce"
    state.mkdir(exist_ok=True)
    input_root(state)
    path = state / "operation.lock"
    if (path.exists() or path.is_symlink()) and is_link(path):
        raise InputError("Небезопасный файл блокировки")
    with path.open("a+b") as stream:
        if path.stat().st_ino != os.fstat(stream.fileno()).st_ino:
            raise InputError("Файл блокировки изменился")
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise InputError("Другая копия приложения уже применяет моды") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
