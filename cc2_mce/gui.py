"""GUI discovery of the game, Workshop, local mods and Lua/native library packages."""

from __future__ import annotations

import os
import queue
import sys
import textwrap
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cc2_mce.baseline import Baseline
from cc2_mce.discovery import ModRef, Scan, discover
from cc2_mce.errors import InputError, MCEError
from cc2_mce.filesystem import Budget, Limits, input_root, read_regular
from cc2_mce.installation import (
    GAME_ID,
    Installation,
    Installations,
    find_installations,
    inspect_game,
    prepare_collections,
)
from cc2_mce.reports import write_report
from cc2_mce.toolchain import bundled_tools
from cc2_mce.ui_feedback import Rejection, explain_rejection
from cc2_mce.workflow import (
    PackagePlan,
    _running,
    active_paths,
    analyze,
    apply_plan,
    game_user_dir,
    recover_interrupted,
    restore_previous,
)


class App(tk.Tk):
    def __init__(self, *, discover_on_start: bool = True) -> None:
        super().__init__()
        self.title("CC2 Engine")
        self.geometry("860x700")
        self.minsize(720, 560)
        self.app_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else None
        self.portable_required = bool(self.app_dir is not None and sys.platform == "win32")
        self.game: Installation | None = None
        self.installations = Installations((), (), ())
        self.mod_roots: list[Path] = []
        self.extra_roots: list[Path] = []
        self.baseline: Baseline | None = None
        self.scan: Scan | None = None
        self.library_scan: Scan | None = None
        self.vars: dict[str, tk.BooleanVar] = {}
        self.library_vars: dict[str, tk.BooleanVar] = {}
        self.package_plan: PackagePlan | None = None
        self.active_package: Path | None = None
        self.selection_dirty = False
        self.applying = False
        self.busy = False
        self._auto_timer: str | None = None
        self._desired_ids: set[str] = set()
        self._applied_ids: set[str] = set()
        self._activation_known = False
        self.checks: dict[str, ttk.Checkbutton] = {}
        self.row_status: dict[str, tk.StringVar] = {}
        self.row_labels: dict[str, ttk.Label] = {}
        self._row_errors: dict[str, str] = {}
        self._required_notes: dict[str, str] = {}
        self.row_origins: dict[str, str] = {}
        self._scroll_canvases: dict[ttk.Frame, tk.Canvas] = {}
        self.problem_details = ""
        self.problem_report: PackagePlan | None = None
        self.auto_enabled = False
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self._generation = 0
        self.discover_on_start = discover_on_start

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f5f8")
        style.configure("TLabel", background="#f3f5f8", foreground="#17243a", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"))
        style.configure("Muted.TLabel", foreground="#526174")
        style.configure("List.TFrame", background="white")
        style.configure("List.TCheckbutton", background="white", font=("Segoe UI", 11), padding=4)
        style.map("List.TCheckbutton", background=[("active", "#edf3fc")])
        style.configure(
            "Row.TLabel", background="white", foreground="#526174", font=("Segoe UI", 9)
        )
        style.configure("Notice.TFrame", background="#fff3e8")
        style.configure("Notice.TLabel", background="#fff3e8", foreground="#863b12")
        style.configure(
            "NoticeTitle.TLabel",
            background="#fff3e8",
            foreground="#863b12",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Launch.TButton", background="#245bbc", foreground="white", padding=(22, 10)
        )
        style.map(
            "Launch.TButton",
            background=[("disabled", "#d5dce7"), ("active", "#194a9c")],
            foreground=[("disabled", "#526174")],
        )
        style.configure("TNotebook", background="#f3f5f8", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(18, 10),
            font=("Segoe UI", 10),
            background="#e5eaf2",
            foreground="#526174",
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "white")],
            foreground=[("selected", "#245bbc")],
        )
        style.configure(
            "TMenubutton",
            background="white",
            foreground="#17243a",
            font=("Segoe UI", 10),
            padding=(12, 8),
        )
        style.configure(
            "Vertical.TScrollbar",
            background="#dce3ed",
            troughcolor="white",
            bordercolor="white",
            arrowcolor="#526174",
            borderwidth=0,
        )
        style.configure(
            "Activity.Horizontal.TProgressbar",
            thickness=3,
            background="#245bbc",
            troughcolor="#e5eaf2",
            borderwidth=0,
        )
        self.configure(background="#f3f5f8")

        frame = ttk.Frame(self, padding=22)
        frame.pack(fill="both", expand=True)
        heading = ttk.Frame(frame)
        heading.pack(fill="x")
        ttk.Label(heading, text="Carrier Command 2", style="Title.TLabel").pack(side="left")
        self.menu_button = ttk.Menubutton(heading, text="Меню", takefocus=True)
        self.menu_button.pack(side="right")
        self.actions_menu = tk.Menu(self.menu_button, tearoff=False)
        self.menu_button.configure(menu=self.actions_menu)
        for title, action in [
            ("Обновить список", self.search),
            ("Выбрать папку игры…", self.pick_game),
            ("Добавить папку модов…", self.pick_mods),
            ("Расположение файлов…", self.show_locations),
        ]:
            self.actions_menu.add_command(label=title, command=action)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label="Вернуть предыдущий набор…", command=self.restore)
        self.actions_menu.add_command(label="Подробности проблемы…", command=self.show_problem)
        self.actions_menu.add_command(label="Сохранить отчёт…", command=self.export_report)
        self.game_path = tk.StringVar(value="Ищем установленную игру…")
        self.game_summary = tk.StringVar(value="Ищем игру…")
        ttk.Label(frame, textvariable=self.game_summary, style="Muted.TLabel").pack(
            anchor="w", pady=(6, 2)
        )
        self.activation_status = tk.StringVar(
            value="Отметьте моды — проверим и подключим автоматически."
        )
        ttk.Label(frame, textvariable=self.activation_status, wraplength=780).pack(
            anchor="w", pady=(0, 8)
        )
        row = ttk.Frame(frame)
        self.game_row = row
        self.game_choice = ttk.Combobox(row, state="readonly")
        self.game_choice.pack(side="left", fill="x", expand=True)
        self.game_choice.bind("<<ComboboxSelected>>", lambda _: self.select_game())

        self.mods_path = tk.StringVar(value="Моды: поиск Workshop и папки mods рядом с игрой")
        self.libraries_path = tk.StringVar(value="Библиотеки: папка libraries рядом с игрой")
        self.notice_title = tk.StringVar()
        self.notice_text = tk.StringVar()
        self.notice_frame = ttk.Frame(frame, style="Notice.TFrame", padding=12)
        ttk.Label(
            self.notice_frame,
            textvariable=self.notice_title,
            style="NoticeTitle.TLabel",
            wraplength=740,
        ).pack(anchor="w")
        ttk.Label(
            self.notice_frame, textvariable=self.notice_text, style="Notice.TLabel", wraplength=740
        ).pack(anchor="w", pady=(4, 0))

        self.tabs = ttk.Notebook(frame)
        self.tabs.pack(fill="both", expand=True, pady=(8, 12))
        mod_tab = ttk.Frame(self.tabs, padding=8, style="List.TFrame")
        library_tab = ttk.Frame(self.tabs, padding=8, style="List.TFrame")
        self.tabs.add(mod_tab, text="Моды")
        self.tabs.add(library_tab, text="Библиотеки")
        self.list_frame = self._scrolling_list(mod_tab)
        self.library_frame = self._scrolling_list(library_tab)
        ttk.Label(
            library_tab,
            text="Необходимые выбранным модам библиотеки подключаются автоматически.",
            style="Row.TLabel",
            wraplength=730,
        ).pack(anchor="w", pady=6)

        self.status = tk.StringVar(value="Ищем игру и подписки Steam. Файлы игры не меняются.")
        self.progress = ttk.Progressbar(
            frame, mode="indeterminate", maximum=100, style="Activity.Horizontal.TProgressbar"
        )
        bottom = ttk.Frame(frame)
        self.bottom = bottom
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status, wraplength=535).pack(
            side="left", fill="x", expand=True
        )
        self.launch_button = ttk.Button(
            bottom,
            text="Запустить игру",
            command=self.launch,
            style="Launch.TButton",
            state="disabled",
        )
        self.launch_button.pack(side="right", padx=(14, 0))
        if discover_on_start:
            self.after(0, self.search)
            self.after(3000, self._watch_sources)

    def _scrolling_list(self, parent: ttk.Frame) -> ttk.Frame:
        container = ttk.Frame(parent, style="List.TFrame")
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0, height=180, background="white")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        items = ttk.Frame(canvas, style="List.TFrame")
        self._scroll_canvases[items] = canvas
        anchor = canvas.create_window((0, 0), window=items, anchor="nw")
        items.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(anchor, width=event.width))
        return items

    def show_locations(self) -> None:
        messagebox.showinfo(
            "Расположение файлов",
            self.game_path.get()
            + "\n\n"
            + self.mods_path.get()
            + "\n\n"
            + self.libraries_path.get(),
        )

    def show_problem(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Подробности проблемы")
        dialog.geometry("720x440")
        dialog.minsize(440, 280)
        text = tk.Text(dialog, wrap="word", font=("Segoe UI", 10), padx=16, pady=16)
        scrollbar = ttk.Scrollbar(dialog, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.problem_details or "Проблем не обнаружено.")
        text.configure(state="disabled")
        text.focus_set()

    def _refresh_controls(self) -> None:
        pending = (game_user_dir() / "cc2-mce/pending.json").exists()
        ready = (
            self.game is not None
            and not self.needs_placement
            and self.scan is not None
            and self._activation_known
            and not self.selection_dirty
            and not self.applying
            and not pending
        )
        self.launch_button.state(["!disabled"] if ready else ["disabled"])
        self.menu_button.state(["disabled"] if self.applying else ["!disabled"])
        if self.selection_dirty or self.applying or (self.busy and self.scan is None):
            if not self.progress.winfo_manager():
                self.progress.pack(fill="x", before=self.bottom, pady=(0, 10))
            self.progress.start(18)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def _update_rows(self, pending_text: str = "Проверяем…") -> None:
        for key, value in self.row_status.items():
            if self.selection_dirty and (key in self._desired_ids) != (key in self._applied_ids):
                text = pending_text
            elif key in self._row_errors:
                text = self._row_errors[key]
            else:
                text = "Включён" if key in self._applied_ids else "Выключен"
            if (
                key in self._applied_ids
                and key not in self._row_errors
                and key in self._required_notes
            ):
                text += " · " + self._required_notes[key]
            value.set(self.row_origins.get(key, "") + " · " + text)
            self.row_labels[key].configure(
                foreground="#9a3412"
                if key in self._row_errors
                else "#166534"
                if key in self._applied_ids
                else "#526174"
            )

    def _clear_notice(self) -> None:
        self.notice_frame.pack_forget()
        self.notice_title.set("")
        self.notice_text.set("")
        self._row_errors.clear()
        self.problem_details = ""
        self.problem_report = None

    def _reject_change(self, rejection: Rejection) -> None:
        if self._auto_timer is not None:
            self.after_cancel(self._auto_timer)
            self._auto_timer = None
        self._desired_ids = set(self._applied_ids)
        self.selection_dirty = False
        for key, variable in {**self.vars, **self.library_vars}.items():
            variable.set(key in self._applied_ids)
        self._row_errors = rejection.rows
        self.problem_details = rejection.details
        self.notice_title.set(rejection.title)
        self.notice_text.set(rejection.message)
        self.notice_frame.pack(fill="x", before=self.tabs, pady=(4, 4))
        self._update_rows()
        self._refresh_controls()
        self.status.set(
            "Предыдущий набор сохранён. Можно играть."
            if self.launch_button.instate(["!disabled"])
            else "Изменение не применено. Проверьте подробности в меню."
        )

    @property
    def needs_placement(self) -> bool:
        return bool(
            self.portable_required
            and self.game is not None
            and (self.app_dir is None or self.app_dir.resolve() != self.game.root)
        )

    def _background[T](
        self,
        action: Callable[[], T],
        receive: Callable[[T], None],
        *,
        reject_selection: bool = False,
    ) -> None:
        self._generation += 1
        generation = self._generation
        results: queue.Queue[tuple[T | None, str | None]] = queue.Queue()
        self.busy = True
        self._refresh_controls()

        def worker() -> None:
            try:
                results.put((action(), None))
            except MCEError as exc:
                results.put((None, str(exc)))
            except (OSError, ValueError):
                results.put((None, "Не удалось безопасно прочитать или записать выбранные папки."))
            except Exception:
                results.put(
                    (None, "Операция прервалась. Повторите проверку или верните прежний набор.")
                )

        def poll() -> None:
            if generation != self._generation:
                return
            try:
                value, error = results.get_nowait()
            except queue.Empty:
                self.after(60, poll)
                return
            if error:
                self.busy = False
                self._set_applying(False)
                self.package_plan = None
                self.status.set(error)
                if self.selection_dirty and ("Игра запущена" in error or "Закройте игру" in error):
                    self.status.set("Закройте игру — выбранные моды применятся автоматически.")
                    self._queue_rebuild(1000)
                elif reject_selection:
                    added = self._desired_ids - self._applied_ids
                    self._reject_change(
                        Rejection(
                            "Изменение отменено",
                            error,
                            error,
                            {key: "Не включён: " + error for key in added},
                        )
                    )
                self._refresh_controls()
            elif value is not None:
                self.busy = False
                self._set_applying(False)
                receive(value)

        threading.Thread(target=worker, daemon=True).start()
        self.after(60, poll)

    def search(self) -> None:
        if self.applying:
            return
        self.status.set("Ищем игру и Workshop во всех библиотеках Steam…")
        self.game_path.set("Ищем установленную игру…")
        self._clear_sources()
        self.game = None
        self._background(lambda: find_installations(app_dir=self.app_dir), self.apply_installations)

    def _clear_sources(self) -> None:
        self._generation += 1
        if self._auto_timer is not None:
            self.after_cancel(self._auto_timer)
            self._auto_timer = None
        self.busy = False
        self.scan = None
        self.library_scan = None
        self.baseline = None
        self.package_plan = None
        self._desired_ids.clear()
        self._applied_ids.clear()
        self._activation_known = False
        self.active_package = None
        self.selection_dirty = False
        for frame in (self.list_frame, self.library_frame):
            for child in frame.winfo_children():
                child.destroy()
        self.vars.clear()
        self.library_vars.clear()
        self.checks.clear()
        self.row_status.clear()
        self.row_labels.clear()
        self.row_origins.clear()
        self._required_notes.clear()
        self._clear_notice()
        self._refresh_controls()

    def apply_installations(self, result: Installations) -> None:
        self._clear_sources()
        self.installations = result
        self.game_choice["values"] = [str(item.root) for item in result.games]
        if len(result.games) > 1:
            self.game_row.pack(fill="x", before=self.tabs, pady=4)
        else:
            self.game_row.pack_forget()
        adjacent = next(
            (
                item
                for item in result.games
                if self.app_dir is not None and self.app_dir.resolve() == item.root
            ),
            None,
        )
        if adjacent is not None:
            self.game_choice.current(result.games.index(adjacent))
        elif len(result.games) == 1:
            self.game_choice.current(0)
        else:
            self.game = None
            self.game_choice.set("")
            self.game_path.set("Игра не выбрана")
            self.game_summary.set(
                "Выберите установку игры в списке"
                if result.games
                else "Игра не найдена — укажите её папку через меню"
            )
            self.status.set(
                "Найдено несколько установок. Выберите нужную в списке."
                if result.games
                else "Игра не найдена. Укажите папку игры или перенесите приложение рядом с ней."
            )
            if result.warnings:
                self.status.set(self.status.get() + " " + " ".join(result.warnings))
            return
        self.select_game()

    def select_game(self) -> None:
        if self.applying:
            return
        index = self.game_choice.current()
        if index < 0:
            return
        self._clear_sources()
        self.game = self.installations.games[index]
        self.game_path.set(f"Игра: {self.game.root}")
        self.game_summary.set("Игра найдена · моды применяются автоматически")
        self.libraries_path.set(f"Библиотеки: {self.game.libraries_dir}")
        self.mod_roots = list(self.installations.workshop_roots)
        self.mod_roots += self.extra_roots
        self.mod_roots.append(self.game.local_mods_dir)
        self.mod_roots = list(dict.fromkeys(self.mod_roots))
        sources = " | ".join(str(root) for root in self.mod_roots) or "Workshop пока не найден"
        self.mods_path.set(f"Моды: {sources}\nЛокальные: {self.game.local_mods_dir}")
        if self.needs_placement:
            self.game_summary.set("Перенесите приложение в папку игры")
            self.status.set(
                f"Перенесите {Path(sys.executable).name} в {self.game.root}, "
                "рядом с carrier_command.exe, и запустите снова."
            )
            return
        self.status.set("Игра найдена. Читаем Workshop, локальные моды и библиотеки…")
        if self.discover_on_start:
            self.scan_sources()

    def scan_sources(
        self, *, preserve_selection: bool = False, rebuild_after_scan: bool = True
    ) -> None:
        if self.game is None or self.needs_placement:
            return
        roots = list(self.mod_roots)
        selected_game = self.game
        library_roots = [selected_game.libraries_dir]
        previous_scan = self.scan
        desired = set(self._desired_ids) if preserve_selection else set()

        def receive(combined: Scan) -> None:
            if (
                preserve_selection
                and previous_scan is not None
                and (combined.fingerprint == previous_scan.fingerprint)
            ):
                return
            self.scan = combined
            self.library_scan = combined
            mods = tuple(mod for mod in combined.mods if mod.package_kind == "mod")
            libraries = tuple(mod for mod in combined.mods if mod.package_kind == "library")
            self.active_package = None
            try:
                paths = active_paths(game_user_dir())
                applied: set[str] = set()
                names: list[str] = []
                for path in paths:
                    if (path.name == "CC2-MCE" or path.name.startswith("CC2-MCE-")) and (
                        path / "mce-manifest.json"
                    ).is_file():
                        self.active_package = path
                        self.auto_enabled = True
                        import json

                        package_root = input_root(path)
                        saved = json.loads(
                            read_regular(path / "mce-manifest.json", package_root, Budget(Limits()))
                        )
                        if not isinstance(saved, dict) or saved.get("owner") != "cc2-mce":
                            raise InputError("Неизвестный журнал активного пакета")
                        current_names = {mod.id: mod.name for mod in combined.mods}
                        names.extend(
                            current_names.get(mod_id, mod_id)
                            for mod_id in saved.get("mod_order", [])
                        )
                        applied.update(saved.get("mod_order", []))
                        if not preserve_selection:
                            desired.update(saved.get("mod_order", []))
                    else:
                        names += [mod.name for mod in combined.mods if mod.root == path]
                        applied.update(mod.id for mod in combined.mods if mod.root == path)
                        if not preserve_selection:
                            desired.update(mod.id for mod in combined.mods if mod.root == path)
                self.activation_status.set(
                    "В игре включены: "
                    + (
                        (
                            ", ".join(names[:3])
                            + (f" и ещё {len(names) - 3}" if len(names) > 3 else "")
                        )
                        if names
                        else "нет модов"
                    )
                )
                self._applied_ids = applied
                self._activation_known = True
            except (MCEError, OSError, ValueError):
                self._activation_known = False
                self.activation_status.set("Не удалось прочитать текущую активацию игры.")
            self._display_items(self.list_frame, self.vars, mods)
            self._display_items(self.library_frame, self.library_vars, libraries, library=True)
            self._desired_ids = desired
            old_sources = (
                {mod.id: mod.sha256 for mod in previous_scan.mods} if previous_scan else {}
            )
            new_sources = {mod.id: mod.sha256 for mod in combined.mods}
            selection_sources_changed = any(
                old_sources.get(key) != new_sources.get(key) for key in desired
            )
            current_ids = set(self.vars) | set(self.library_vars)
            previous_names = (
                {mod.id: mod.name for mod in previous_scan.mods} if previous_scan else {}
            )
            for missing in sorted(desired - current_ids):
                variable = tk.BooleanVar(value=True)
                self.vars[missing] = variable
                check = ttk.Checkbutton(
                    self.list_frame,
                    text=(
                        previous_names.get(missing, "Выбранный мод")
                        + " — не найден, снимите галочку"
                    ),
                    variable=variable,
                    command=self.selection_changed,
                    style="List.TCheckbutton",
                )
                check.pack(anchor="w", pady=3)
                self.checks[missing] = check
            for mod_id, variable in {**self.vars, **self.library_vars}.items():
                variable.set(mod_id in desired)
            if not preserve_selection:
                self.status.set(
                    f"Найдено модов: {len(mods)}, библиотек: {len(libraries)}. "
                    "Отметьте нужные."
                    + (
                        " " + " ".join(self.installations.warnings)
                        if self.installations.warnings
                        else ""
                    )
                )
            self.tabs.tab(0, text=f"Моды · {len(mods)}")  # type: ignore[no-untyped-call]
            self.tabs.tab(1, text=f"Библиотеки · {len(libraries)}")  # type: ignore[no-untyped-call]
            self._update_rows()
            if (
                self.auto_enabled
                and self._activation_known
                and rebuild_after_scan
                and (not preserve_selection or selection_sources_changed)
            ):
                self.selection_dirty = True
                self._queue_rebuild()
            self._refresh_controls()

        def scan() -> Scan:
            try:
                prepare_collections(selected_game)
            except (OSError, MCEError) as exc:
                raise InputError(
                    "Не удалось подготовить mods и libraries. Проверьте доступ к папке игры."
                ) from exc
            recover_interrupted(game_user_dir())
            return discover([*roots, *library_roots])

        self._background(scan, receive)

    def _display_items(
        self,
        frame: ttk.Frame,
        variables: dict[str, tk.BooleanVar],
        mods: tuple[ModRef, ...],
        *,
        library: bool = False,
    ) -> None:
        for child in frame.winfo_children():
            child.destroy()
        for key in variables:
            self.checks.pop(key, None)
            self.row_status.pop(key, None)
            self.row_labels.pop(key, None)
            self.row_origins.pop(key, None)
        variables.clear()
        for mod in sorted(
            mods, key=lambda item: (item.id not in self._applied_ids, item.name.casefold())
        ):
            variable = tk.BooleanVar(value=False)
            variables[mod.id] = variable
            if library:
                kinds = []
                if any(item.logical_path.casefold().endswith(".lua") for item in mod.files):
                    kinds.append("Lua")
                if any(item.kind == "native" for item in mod.files):
                    kinds.append("DLL-плагин")
                origin = ", ".join(kinds) or "ресурсы"
            else:
                origin = (
                    "Workshop"
                    if any(
                        mod.root.is_relative_to(root) for root in self.installations.workshop_roots
                    )
                    else "локальный"
                )
            row = ttk.Frame(frame, style="List.TFrame", padding=(6, 6))
            row.pack(fill="x")
            check = ttk.Checkbutton(
                row,
                text=textwrap.fill(mod.name, width=64),
                variable=variable,
                command=self.selection_changed,
                style="List.TCheckbutton",
            )
            check.pack(anchor="w", fill="x")
            self.checks[mod.id] = check
            self.row_origins[mod.id] = origin
            self.row_status[mod.id] = tk.StringVar(value=origin + " · Выключен")
            label = ttk.Label(
                row, textvariable=self.row_status[mod.id], style="Row.TLabel", wraplength=710
            )
            label.pack(anchor="w", padx=(25, 0))
            self.row_labels[mod.id] = label
            canvas = self._scroll_canvases[frame]

            def scroll(event: tk.Event, target: tk.Canvas = canvas) -> str:
                steps = (
                    (-1 if event.num == 4 else 1)
                    if event.num in (4, 5)
                    else (-int(event.delta / 120) if abs(event.delta) >= 120 else -event.delta)
                )
                target.yview_scroll(steps, "units")
                return "break"

            for widget in (row, check, label):
                for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                    widget.bind(sequence, scroll)
        if not mods:
            ttk.Label(
                frame,
                text="Библиотек пока нет."
                if library
                else "Моды пока не найдены. Подпишитесь в Workshop или добавьте папку через меню.",
                style="Row.TLabel",
                wraplength=700,
            ).pack(anchor="w", pady=6)

    def display_scan(self, scan: Scan) -> None:
        self.scan = scan
        self._display_items(self.list_frame, self.vars, scan.mods)

    def selection_changed(self) -> None:
        if self.applying:
            return
        self._generation += 1
        self.auto_enabled = True
        self._clear_notice()
        self._desired_ids = {
            key for key, value in {**self.vars, **self.library_vars}.items() if value.get()
        }
        self.status.set("Обновляем сборку…")
        self.package_plan = None
        self.selection_dirty = True
        self._queue_rebuild()
        self._update_rows()
        self._refresh_controls()

    def _queue_rebuild(self, delay: int = 250) -> None:
        if self._auto_timer is not None:
            self.after_cancel(self._auto_timer)
        self._auto_timer = self.after(delay, self._auto_rebuild)

    def _auto_rebuild(self) -> None:
        self._auto_timer = None
        if self.applying or self.game is None or self.needs_placement or not self.selection_dirty:
            return
        try:
            running = _running()
        except MCEError as exc:
            self._reject_change(Rejection("Изменение отменено", str(exc), str(exc), {}))
            return
        if running:
            self.status.set("Закройте игру — выбранные моды применятся автоматически.")
            self._update_rows("После закрытия игры")
            self._queue_rebuild(1000)
            return
        self.check_selected()

    def _watch_sources(self) -> None:
        if not self.busy and not self.applying and self._auto_timer is None and self.game:
            self.scan_sources(preserve_selection=True)
        self.after(3000, self._watch_sources)

    def pick_game(self) -> None:
        if self.applying:
            return
        folder = filedialog.askdirectory(title="Папка Carrier Command 2")
        if not folder:
            return
        installed = inspect_game(Path(folder))
        if installed is None:
            messagebox.showwarning(
                "Игра не найдена", "В выбранной папке нет исполняемого файла CC2."
            )
            return
        self.apply_installations(
            Installations(
                (installed,), self.installations.workshop_roots, self.installations.warnings
            )
        )

    def pick_mods(self) -> None:
        if self.applying:
            return
        folder = filedialog.askdirectory(title="Дополнительная папка модов")
        if folder:
            self.extra_roots.append(Path(folder))
            self.select_game()

    def check_selected(self) -> None:
        if self.applying:
            return
        if self.game is None or self.needs_placement:
            return
        selected = sorted(self._desired_ids)
        roots = list(self.mod_roots)
        if self.game.libraries_dir.exists():
            roots.append(self.game.libraries_dir)
        self.status.set("Проверяем выбранные моды и библиотеки…")
        selected_game = self.game

        def check() -> PackagePlan:
            scan = discover(roots)
            chosen = [mod for mod in scan.mods if mod.id in selected]
            if {mod.id for mod in chosen} != set(selected):
                raise InputError("Выбранный мод исчез из папки. Верните его или снимите галочку.")
            return analyze(selected_game, scan, [mod.id for mod in chosen], tools=bundled_tools())

        def receive(result: PackagePlan) -> None:
            self.package_plan = result
            if not result.blockers:
                self.apply_selected()
            else:
                self.problem_report = result
                self._reject_change(
                    explain_rejection(
                        result.report,
                        self._applied_ids,
                        self._desired_ids,
                        {mod.id: mod.name for mod in result.scan.mods},
                    )
                )

        self._background(check, receive, reject_selection=True)

    def apply_selected(self) -> None:
        if self.applying:
            return
        current = self.package_plan
        if current is None or current.blockers or self.needs_placement:
            self.status.set("Сначала проверьте выбранный набор.")
            return
        self.status.set("Обновляем общую папку модов…")
        requested = set(self._desired_ids)
        previously_applied = set(self._applied_ids)
        self._set_applying(True)

        def receive(path: Path) -> None:
            self.active_package = path
            self._activation_known = True
            self.selection_dirty = False
            self._applied_ids = {mod.id for mod in current.selected}
            by_id = {key: mod for mod in current.selected for key in {mod.id, mod.package_id}}
            required: dict[str, list[str]] = {}
            for mod in current.selected:
                for dependency in mod.dependencies:
                    target = by_id[dependency]
                    required.setdefault(target.id, []).append(mod.name)
            self._required_notes = {
                key: "Требуется для " + ", ".join(f"«{name}»" for name in names[:2])
                for key, names in required.items()
            }
            self.activation_status.set(
                "В игре включены: "
                + (
                    ", ".join(mod.name for mod in current.selected[:3])
                    + (f" и ещё {len(current.selected) - 3}" if len(current.selected) > 3 else "")
                    if current.selected
                    else "нет модов"
                )
            )
            self.status.set(
                "Готово. Можно запускать игру." if current.selected else "Все моды отключены."
            )
            for mod in current.selected:
                variable = self.vars.get(mod.id) or self.library_vars.get(mod.id)
                if variable is not None:
                    variable.set(True)
            self._desired_ids = {mod.id for mod in current.selected}
            if self._desired_ids - requested:
                self.status.set("Готово. Необходимые библиотеки подключены автоматически.")
                readded = (self._desired_ids - requested) & previously_applied
                if readded:
                    self.status.set("Зависимость остаётся включённой: она нужна выбранным модам.")
            self._clear_notice()
            self._update_rows()
            self._refresh_controls()

        self._background(
            lambda: apply_plan(current, game_user_dir()), receive, reject_selection=True
        )

    def restore(self) -> None:
        if self.applying:
            return
        if not messagebox.askyesno(
            "Вернуть прежние моды", "Восстановить набор до последнего применения?"
        ):
            return

        def action() -> bool:
            restore_previous(game_user_dir())
            return True

        def receive(_: bool) -> None:
            self.active_package = None
            self.selection_dirty = False
            self.package_plan = None
            self.activation_status.set("Прежний набор модов восстановлен.")
            self.status.set("Прежний набор восстановлен.")
            self.scan_sources(rebuild_after_scan=False)

        self._set_applying(True)
        self._background(action, receive)

    def _set_applying(self, value: bool) -> None:
        self.applying = value
        self.game_choice.configure(state="disabled" if value else "readonly")
        for check in self.checks.values():
            check.state(["disabled"] if value else ["!disabled"])
        self._update_rows("Сохраняем…" if value else "Проверяем…")
        self._refresh_controls()

    def request_close(self) -> None:
        if self.applying:
            self.status.set(
                "Завершаем запись и резервную копию. Окно можно закрыть после завершения."
            )
            return
        self.destroy()

    def export_report(self) -> None:
        plan = self.problem_report or self.package_plan
        if plan is None:
            self.show_problem()
            return
        name = filedialog.asksaveasfilename(title="Сохранить отчёт", defaultextension=".json")
        if name:
            try:
                write_report(plan.report, Path(name), list(plan.scan.roots))
            except (MCEError, OSError):
                self.status.set("Отчёт не сохранён: выберите новый файл вне исходников.")

    def launch(self) -> None:
        if self.applying:
            self.status.set("Дождитесь завершения применения модов.")
            return
        if self.game is None or self.needs_placement:
            self.status.set("Сначала выберите игру и разместите приложение рядом с ней.")
            return
        if (game_user_dir() / "cc2-mce/pending.json").exists():
            self.status.set("Сначала дождитесь восстановления незавершённой сборки.")
            return
        if self.selection_dirty:
            self.status.set(
                "Выбранный набор ещё не готов. Дождитесь сборки или устраните конфликт."
            )
            return
        try:
            input_root(self.game.root)
            url = f"steam://rungameid/{GAME_ID}"
            if sys.platform == "win32":
                os.startfile(url)
            else:
                webbrowser.open(url)
        except (OSError, MCEError):
            self.status.set("Не удалось открыть игру через Steam.")


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-bundle":
        import json

        from cc2_mce.reports import ensure_destination
        from cc2_mce.toolchain import verify_bundle

        destination = ensure_destination(Path(sys.argv[2]), [])
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(verify_bundle(), stream)
        return
    App().mainloop()


if __name__ == "__main__":
    main()
