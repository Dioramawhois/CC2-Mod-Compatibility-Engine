"""GUI discovery of the game, Workshop, local mods and Lua/native library packages."""

from __future__ import annotations

import queue
import sys
import textwrap
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cc2_mce import APP_NAME
from cc2_mce.baseline import Baseline
from cc2_mce.discovery import ModRef, Scan, discover
from cc2_mce.errors import InputError, MCEError
from cc2_mce.filesystem import Budget, Limits, input_root, read_regular
from cc2_mce.game_launch import launch_game
from cc2_mce.i18n import LANGUAGES, Translator
from cc2_mce.installation import (
    Installation,
    Installations,
    find_installations,
    inspect_game,
    prepare_collections,
)
from cc2_mce.preferences import Preferences
from cc2_mce.reports import write_report
from cc2_mce.toolchain import bundled_tools
from cc2_mce.ui_feedback import OverrideWarning, Rejection, explain_overrides, explain_rejection
from cc2_mce.workflow import (
    PackagePlan,
    _running,
    active_paths,
    analyze,
    apply_plan,
    game_user_dir,
    recover_interrupted,
    remembered_package,
    restore_previous,
)


class App(tk.Tk):
    def __init__(
        self,
        *,
        discover_on_start: bool = True,
        patch_priority: bool | None = None,
        preferences_dir: Path | None = None,
        language: str | None = None,
        resume_request: tuple[Path, set[str], list[str]] | None = None,
        play_on_ready: bool | None = None,
    ) -> None:
        super().__init__()
        self.title(APP_NAME)
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
        self.mod_order: list[str] = []
        self._applied_order: list[str] = []
        self._order_drag: str | None = None
        self.restart_requested = False
        self._resume_request = resume_request
        self.restart_selection: tuple[Path, set[str], list[str]] | None = None
        self._language_restart_pending = False
        try:
            self.preferences = Preferences.load(preferences_dir or game_user_dir() / "cc2-mce")
        except (OSError, MCEError):
            self.preferences = Preferences(preferences_dir or game_user_dir() / "cc2-mce")
        self.patch_priority = (
            self.preferences.patch_priority if patch_priority is None else patch_priority
        )
        self._applied_patch_priority = self.patch_priority
        self._play_requested = (
            self.preferences.launch_on_start if play_on_ready is None else play_on_ready
        )
        self.language_choice = language or self.preferences.language
        self.translator = Translator(self.language_choice)
        self.extra_roots = [Path(value) for value in self.preferences.extra_roots]
        self._activation_known = False
        self.checks: dict[str, ttk.Checkbutton] = {}
        self.row_status: dict[str, tk.StringVar] = {}
        self.row_labels: dict[str, ttk.Label] = {}
        self._row_errors: dict[str, str] = {}
        self._applied_warning: OverrideWarning | None = None
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
            padding=[("selected", (20, 12)), ("!selected", (18, 8))],
            font=[("selected", ("Segoe UI", 10, "bold")), ("!selected", ("Segoe UI", 10))],
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
        ttk.Label(heading, text=APP_NAME, style="Title.TLabel").pack(side="left")
        self.menu_button = ttk.Menubutton(heading, text=self.tr("Меню"), takefocus=True)
        self.menu_button.pack(side="right")
        self.actions_menu = tk.Menu(self.menu_button, tearoff=False)
        self.menu_button.configure(menu=self.actions_menu)
        for title, action in [
            (self.tr("Обновить список"), self.search),
            (self.tr("Выбрать папку игры…"), self.pick_game),
            (self.tr("Добавить папку модов…"), self.pick_mods),
            (self.tr("Расположение файлов…"), self.show_locations),
        ]:
            self.actions_menu.add_command(label=title, command=action)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(
            label=self.tr("Вернуть предыдущий набор…"), command=self.restore
        )
        self.actions_menu.add_command(
            label=self.tr("Подробности проблемы…"), command=self.show_problem
        )
        self.actions_menu.add_command(label=self.tr("Сохранить отчёт…"), command=self.export_report)
        self.priority_var = tk.BooleanVar(value=self.patch_priority)
        self.auto_launch_var = tk.BooleanVar(value=self.preferences.launch_on_start)
        self.actions_menu.add_checkbutton(
            label=self.tr("Запускать игру при открытии"),
            variable=self.auto_launch_var,
            command=self.change_auto_launch,
        )
        self.actions_menu.add_checkbutton(
            label=self.tr("Приоритет поздних патчей"),
            variable=self.priority_var,
            command=self.change_patch_priority,
        )
        language_menu = tk.Menu(self.actions_menu, tearoff=False)
        self.language_var = tk.StringVar(value=self.language_choice)
        for choice, label in [("system", self.tr("Как в системе")), *LANGUAGES.items()]:
            language_menu.add_radiobutton(
                label=label, value=choice, variable=self.language_var, command=self.change_language
            )
        self.actions_menu.add_cascade(label=self.tr("Язык"), menu=language_menu)
        self.game_path = tk.StringVar(value=self.tr("Ищем установленную игру…"))
        self.game_summary = tk.StringVar(value=self.tr("Ищем игру…"))
        ttk.Label(frame, textvariable=self.game_summary, style="Muted.TLabel").pack(
            anchor="w", pady=(6, 2)
        )
        self.activation_status = tk.StringVar(
            value=self.tr("Отметьте моды — проверим и подключим автоматически.")
        )
        ttk.Label(frame, textvariable=self.activation_status, wraplength=780).pack(
            anchor="w", pady=(0, 8)
        )
        row = ttk.Frame(frame)
        self.game_row = row
        self.game_choice = ttk.Combobox(row, state="readonly")
        self.game_choice.pack(side="left", fill="x", expand=True)
        self.game_choice.bind("<<ComboboxSelected>>", lambda _: self.select_game())
        self.mods_path = tk.StringVar(
            value=self.tr("Моды: поиск Workshop и папки mods рядом с игрой")
        )
        self.libraries_path = tk.StringVar(
            value=self.tr("Библиотеки: папка libraries рядом с игрой")
        )
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
        self.tabs.add(mod_tab, text=self.tr("Моды"))
        self.tabs.add(library_tab, text=self.tr("Библиотеки"))
        order_tab = ttk.Frame(self.tabs, padding=8, style="List.TFrame")
        self.tabs.add(order_tab, text=self.tr("Порядок загрузки"))
        ttk.Label(
            order_tab,
            text=self.tr(
                "Перетащите моды мышью или используйте Alt+↑ / Alt+↓.\n"
                "Поздние патчи ниже. Изменение порядка сразу пересобирает файлы."
            ),
            style="Row.TLabel",
            wraplength=720,
        ).pack(anchor="w", pady=(0, 8))
        self.order_tree = ttk.Treeview(
            order_tab, columns=("position", "name"), show="headings", selectmode="browse", height=12
        )
        self.order_tree.heading("position", text="№")
        self.order_tree.heading("name", text=self.tr("Мод / библиотека"))
        self.order_tree.column("position", width=48, stretch=False)
        self.order_tree.column("name", width=620)
        self.order_tree.pack(fill="both", expand=True)
        self.order_tree.bind("<ButtonPress-1>", self._order_press)
        self.order_tree.bind("<ButtonRelease-1>", self._order_release)
        self.order_tree.bind("<Alt-Up>", lambda _: self._move_focused_order(-1))
        self.order_tree.bind("<Alt-Down>", lambda _: self._move_focused_order(1))
        self.list_frame = self._scrolling_list(mod_tab)
        self.library_frame = self._scrolling_list(library_tab)
        ttk.Label(
            library_tab,
            text=self.tr("Необходимые выбранным модам библиотеки подключаются автоматически."),
            style="Row.TLabel",
            wraplength=730,
        ).pack(anchor="w", pady=6)
        self.status = tk.StringVar(
            value=self.tr("Ищем игру и подписки Steam. Файлы игры не меняются.")
        )
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
            text=self.tr("Запустить игру"),
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
            self.tr("Расположение файлов"),
            self.game_path.get()
            + "\n\n"
            + self.mods_path.get()
            + "\n\n"
            + self.libraries_path.get(),
        )

    def tr(self, message: str, **values: object) -> str:
        return self.translator(message, **values)

    def change_language(self) -> None:
        choice = self.language_var.get()
        if choice == self.language_choice:
            return
        try:
            self.preferences.language = choice
            self.preferences.extra_roots = [str(path) for path in self.extra_roots]
            self.preferences.save()
        except (OSError, MCEError) as exc:
            self.status.set(self.tr(str(exc)))
            return
        self._language_restart_pending = True
        self._finish_language_restart()

    def _finish_language_restart(self) -> None:
        if self.busy or self.applying:
            self.after(120, self._finish_language_restart)
            return
        if self.selection_dirty and self.game is not None:
            self.restart_selection = (self.game.root, set(self._desired_ids), list(self.mod_order))
        self.restart_geometry = self.geometry()
        self.restart_requested = True
        self.request_close()

    def _ordered_selection(self) -> list[str]:
        return [key for key in self.mod_order if key in self._desired_ids] + sorted(
            self._desired_ids - set(self.mod_order)
        )

    def _render_order(self) -> None:
        selected = self.order_tree.selection()
        self.order_tree.delete(*self.order_tree.get_children())
        names = {mod.id: mod.name for mod in self.scan.mods} if self.scan else {}
        for index, key in enumerate(self._ordered_selection(), 1):
            self.order_tree.insert(
                "", "end", iid=key, values=(index, names.get(key, self.tr("Мод не найден")))
            )
        if selected and selected[0] in self.order_tree.get_children():
            self.order_tree.selection_set(selected[0])

    def _order_press(self, event: tk.Event) -> None:
        self._order_drag = self.order_tree.identify_row(event.y)

    def _order_release(self, event: tk.Event) -> None:
        target = self.order_tree.identify_row(event.y)
        order = self._ordered_selection()
        if self._order_drag in order and target in order:
            self.move_mod(self._order_drag, order.index(target))
        self._order_drag = None

    def _move_focused_order(self, direction: int) -> str:
        selected = self.order_tree.selection()
        if selected:
            order = self._ordered_selection()
            self.move_mod(selected[0], order.index(selected[0]) + direction)
        return "break"

    def move_mod(self, mod_id: str, index: int) -> None:
        if self.applying:
            return
        order = self._ordered_selection()
        if mod_id not in order or not 0 <= index < len(order):
            return
        if order.index(mod_id) == index:
            return
        order.remove(mod_id)
        order.insert(index, mod_id)
        self.mod_order = order + [key for key in self.mod_order if key not in order]
        self.selection_changed()

    def change_patch_priority(self) -> None:
        if self.applying:
            return
        self.patch_priority = self.priority_var.get()
        self.selection_changed()

    def change_auto_launch(self) -> None:
        previous = self.preferences.launch_on_start
        self.preferences.launch_on_start = self.auto_launch_var.get()
        try:
            self.preferences.save()
        except (OSError, MCEError):
            self.preferences.launch_on_start = previous
            self.auto_launch_var.set(previous)
            self.status.set(self.tr("Не удалось сохранить настройку запуска."))

    def show_problem(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(self.tr("Подробности проблемы"))
        dialog.geometry("720x440")
        dialog.minsize(440, 280)
        text = tk.Text(dialog, wrap="word", font=("Segoe UI", 10), padx=16, pady=16)
        scrollbar = ttk.Scrollbar(dialog, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.problem_details or self.tr("Проблем не обнаружено."))
        text.configure(state="disabled")
        text.focus_set()

    def _refresh_controls(self) -> None:
        pending = (game_user_dir() / "cc2-mce/pending.json").exists()
        ready = (
            self.game is not None
            and (not self.needs_placement)
            and (self.scan is not None)
            and self._activation_known
            and (not self.selection_dirty)
            and (not self.applying)
            and (not pending)
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

    def _update_rows(self, pending_text: str | None = None) -> None:
        pending_text = pending_text or self.tr("Проверяем…")
        for key, value in self.row_status.items():
            if self.selection_dirty and (
                (key in self._desired_ids) != (key in self._applied_ids)
                or (key in self._desired_ids and self._ordered_selection() != self._applied_order)
            ):
                text = pending_text
            elif key in self._row_errors:
                text = self._row_errors[key]
            else:
                text = self.tr("Включён") if key in self._applied_ids else self.tr("Выключен")
            if (
                key in self._applied_ids
                and key not in self._row_errors
                and (key in self._required_notes)
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
        self._show_applied_warning()

    def _show_applied_warning(self) -> None:
        if warning := self._applied_warning:
            self.notice_title.set(warning.title)
            self.notice_text.set(warning.message)
            self.problem_details = warning.details
            self._row_errors = dict(warning.rows)
            self.notice_frame.pack(fill="x", before=self.tabs, pady=(4, 4))

    def _reject_change(self, rejection: Rejection) -> None:
        self._play_requested = False
        if self._auto_timer is not None:
            self.after_cancel(self._auto_timer)
            self._auto_timer = None
        self._desired_ids = set(self._applied_ids)
        self.patch_priority = self._applied_patch_priority
        self.priority_var.set(self.patch_priority)
        self.mod_order = self._applied_order + [
            key for key in self.mod_order if key not in self._applied_ids
        ]
        self.selection_dirty = False
        for key, variable in {**self.vars, **self.library_vars}.items():
            variable.set(key in self._applied_ids)
        self._row_errors = rejection.rows
        self.problem_details = self.tr(rejection.details)
        self.notice_title.set(self.tr(rejection.title))
        self.notice_text.set(self.tr(rejection.message))
        self.notice_frame.pack(fill="x", before=self.tabs, pady=(4, 4))
        self._update_rows()
        self._render_order()
        self._refresh_controls()
        self.status.set(
            self.tr("Предыдущий набор сохранён. Можно играть.")
            if self.launch_button.instate(["!disabled"])
            else self.tr("Изменение не применено. Проверьте подробности в меню.")
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
                results.put(
                    (None, self.tr("Не удалось безопасно прочитать или записать выбранные папки."))
                )
            except Exception:
                results.put(
                    (
                        None,
                        self.tr(
                            "Операция прервалась. Повторите проверку или верните прежний набор."
                        ),
                    )
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
                self.status.set(self.tr(error))
                if self.selection_dirty and ("Игра запущена" in error or "Закройте игру" in error):
                    self.status.set(
                        self.tr("Закройте игру — выбранные моды применятся автоматически.")
                    )
                    self._queue_rebuild(1000)
                elif reject_selection:
                    added = self._desired_ids - self._applied_ids
                    self._reject_change(
                        Rejection(
                            self.tr("Изменение отменено"),
                            error,
                            error,
                            {key: self.tr("Не включён: ") + self.tr(error) for key in added},
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
        self.status.set(self.tr("Ищем игру и Workshop во всех библиотеках Steam…"))
        self.game_path.set(self.tr("Ищем установленную игру…"))
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
        self.mod_order.clear()
        self._applied_order.clear()
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
        self._applied_warning = None
        self._clear_notice()
        self._render_order()
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
            self.game_path.set(self.tr("Игра не выбрана"))
            self.game_summary.set(
                self.tr("Выберите установку игры в списке")
                if result.games
                else self.tr("Игра не найдена — укажите её папку через меню")
            )
            self.status.set(
                self.tr("Найдено несколько установок. Выберите нужную в списке.")
                if result.games
                else self.tr(
                    "Игра не найдена. Укажите папку игры или перенесите приложение рядом с ней."
                )
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
        self.game_path.set(self.tr("Игра: {p0}", p0=self.game.root))
        self.game_summary.set(self.tr("Игра найдена · моды применяются автоматически"))
        self.libraries_path.set(self.tr("Библиотеки: {p0}", p0=self.game.libraries_dir))
        self.mod_roots = list(self.installations.workshop_roots)
        self.mod_roots += self.extra_roots
        self.mod_roots.append(self.game.local_mods_dir)
        self._refresh_mod_roots()
        if self.needs_placement:
            self.game_summary.set(self.tr("Перенесите приложение в папку игры"))
            self.status.set(
                self.tr(
                    "Перенесите {p0} в {p1}, рядом с carrier_command.exe, и запустите снова.",
                    p0=Path(sys.executable).name,
                    p1=self.game.root,
                )
            )
            return
        self.status.set(self.tr("Игра найдена. Читаем Workshop, локальные моды и библиотеки…"))
        if self.discover_on_start:
            self.scan_sources()

    def _refresh_mod_roots(self) -> None:
        if self.game is None:
            return
        user_mods = game_user_dir() / "mods"
        roots = [root for root in self.mod_roots if root != user_mods]
        if user_mods.exists() or user_mods.is_symlink():
            roots.append(user_mods)
        self.mod_roots = list(dict.fromkeys(roots))
        sources = " | ".join(str(root) for root in self.mod_roots) or self.tr(
            "Workshop пока не найден"
        )
        self.mods_path.set(
            self.tr(
                "Моды: {p0}\nЛокальные: {p1}",
                p0=sources,
                p1=f"{user_mods} | {self.game.local_mods_dir}",
            )
        )

    def scan_sources(
        self, *, preserve_selection: bool = False, rebuild_after_scan: bool = True
    ) -> None:
        if self.game is None or self.needs_placement:
            return
        self._refresh_mod_roots()
        roots = list(self.mod_roots)
        selected_game = self.game
        library_roots = [selected_game.libraries_dir]
        previous_scan = self.scan
        desired = set(self._desired_ids) if preserve_selection else set()

        def receive(combined: Scan) -> None:
            nonlocal desired
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
                applied_order: list[str] = []
                names: list[str] = []
                active_report = None
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
                            raise InputError(self.tr("Неизвестный журнал активного пакета"))
                        active_report = saved
                        current_names = {mod.id: mod.name for mod in combined.mods}
                        names.extend(
                            current_names.get(mod_id, mod_id)
                            for mod_id in saved.get("mod_order", [])
                        )
                        applied.update(saved.get("mod_order", []))
                        applied_order.extend(saved.get("mod_order", []))
                        self._applied_patch_priority = (
                            saved.get("merge_policy") == "ordered-patches"
                        )
                        if not preserve_selection:
                            desired.update(saved.get("mod_order", []))
                    else:
                        names += [mod.name for mod in combined.mods if mod.root == path]
                        applied.update(mod.id for mod in combined.mods if mod.root == path)
                        applied_order.extend(mod.id for mod in combined.mods if mod.root == path)
                        if not preserve_selection:
                            desired.update(mod.id for mod in combined.mods if mod.root == path)
                self.activation_status.set(
                    self.tr("В игре включены: ")
                    + (
                        ", ".join(names[:3])
                        + (self.tr(" и ещё {p0}", p0=len(names) - 3) if len(names) > 3 else "")
                        if names
                        else self.tr("нет модов")
                    )
                )
                self._applied_ids = applied
                self._applied_order = list(dict.fromkeys(applied_order))
                self._activation_known = True
                if not preserve_selection:
                    remembered = remembered_package(selected_game, game_user_dir())
                    if remembered is not None:
                        desired = set(remembered["mod_order"])
                        self.auto_enabled = True
                showing_warning = (
                    self._applied_warning is not None
                    and self.notice_title.get() == self._applied_warning.title
                )
                self._applied_warning = (
                    explain_overrides(active_report, self.tr) if active_report else None
                )
                if not preserve_selection or not self.notice_title.get() or showing_warning:
                    self._clear_notice()
            except (MCEError, OSError, ValueError):
                self._activation_known = False
                self.activation_status.set(self.tr("Не удалось прочитать текущую активацию игры."))
            self._display_items(self.list_frame, self.vars, mods)
            self._display_items(self.library_frame, self.library_vars, libraries, library=True)
            resumed_order = None
            if not preserve_selection and self._resume_request is not None:
                resume_game, resume_ids, resume_order = self._resume_request
                if resume_game == selected_game.root:
                    desired = set(resume_ids)
                    resumed_order = list(resume_order)
                    self.auto_enabled = True
                    self._resume_request = None
            self._desired_ids = desired
            saved_order = (
                resumed_order
                if resumed_order is not None
                else (
                    self.mod_order
                    if preserve_selection
                    else self._applied_order or self.preferences.order(selected_game.root)
                )
            )
            self.mod_order = list(dict.fromkeys([*saved_order, *(mod.id for mod in combined.mods)]))
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
                    text=previous_names.get(missing, self.tr("Выбранный мод"))
                    + self.tr(" — не найден, снимите галочку"),
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
                    self.tr(
                        "Найдено модов: {p0}, библиотек: {p1}. Отметьте нужные.",
                        p0=len(mods),
                        p1=len(libraries),
                    )
                    + (
                        " " + " ".join(self.installations.warnings)
                        if self.installations.warnings
                        else ""
                    )
                )
            self.tabs.tab(0, text=self.tr("Моды · {p0}", p0=len(mods)))  # type: ignore[no-untyped-call]
            self.tabs.tab(1, text=self.tr("Библиотеки · {p0}", p0=len(libraries)))  # type: ignore[no-untyped-call]
            self._update_rows()
            self._render_order()
            if (
                self._activation_known
                and rebuild_after_scan
                and (not preserve_selection or selection_sources_changed)
            ):
                self.auto_enabled = True
                self.selection_dirty = True
                self._queue_rebuild()
            self._refresh_controls()
            self._maybe_play()

        def scan() -> Scan:
            try:
                prepare_collections(selected_game)
            except (OSError, MCEError) as exc:
                raise InputError(
                    self.tr(
                        "Не удалось подготовить mods и libraries. Проверьте доступ к папке игры."
                    )
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
                    kinds.append(self.tr("DLL-плагин"))
                origin = ", ".join(kinds) or self.tr("ресурсы")
            else:
                origin = (
                    "Workshop"
                    if any(
                        mod.root.is_relative_to(root) for root in self.installations.workshop_roots
                    )
                    else self.tr("локальный")
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
            self.row_status[mod.id] = tk.StringVar(value=origin + self.tr(" · Выключен"))
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
                    else -int(event.delta / 120)
                    if abs(event.delta) >= 120
                    else -event.delta
                )
                target.yview_scroll(steps, "units")
                return "break"

            for widget in (row, check, label):
                for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                    widget.bind(sequence, scroll)
        if not mods:
            ttk.Label(
                frame,
                text=self.tr("Библиотек пока нет.")
                if library
                else self.tr(
                    "Моды пока не найдены. Подпишитесь в Workshop или добавьте папку через меню."
                ),
                style="Row.TLabel",
                wraplength=700,
            ).pack(anchor="w", pady=6)

    def display_scan(self, scan: Scan) -> None:
        self.scan = scan
        self.mod_order = [mod.id for mod in scan.mods]
        self._display_items(self.list_frame, self.vars, scan.mods)

    def selection_changed(self) -> None:
        if self.applying:
            return
        self._generation += 1
        self.auto_enabled = True
        self._clear_notice()
        variables = {**self.vars, **self.library_vars}
        desired = {key for key, value in variables.items() if value.get()}
        added = desired - self._desired_ids
        if self.scan is not None and len(added) == 1:
            selected = next((mod for mod in self.scan.mods if mod.id in added), None)
            if selected is not None:
                identity = selected.package_id or selected.id
                for mod in self.scan.mods:
                    if mod.id != selected.id and (mod.package_id or mod.id) == identity:
                        desired.discard(mod.id)
                        if mod.id in variables:
                            variables[mod.id].set(False)
        self._desired_ids = desired
        self.status.set(self.tr("Обновляем сборку…"))
        self.package_plan = None
        self.selection_dirty = True
        self._queue_rebuild()
        self._update_rows()
        self._render_order()
        self._refresh_controls()

    def _queue_rebuild(self, delay: int = 250) -> None:
        if self._auto_timer is not None:
            self.after_cancel(self._auto_timer)
        self._auto_timer = self.after(delay, self._auto_rebuild)

    def _auto_rebuild(self) -> None:
        self._auto_timer = None
        if self.applying or self.game is None or self.needs_placement or (not self.selection_dirty):
            return
        try:
            running = _running()
        except MCEError as exc:
            self._reject_change(Rejection(self.tr("Изменение отменено"), str(exc), str(exc), {}))
            return
        if running:
            self.status.set(self.tr("Закройте игру — выбранные моды применятся автоматически."))
            self._update_rows(self.tr("После закрытия игры"))
            self._queue_rebuild(1000)
            return
        self.check_selected()

    def _watch_sources(self) -> None:
        if not self.busy and (not self.applying) and (self._auto_timer is None) and self.game:
            self.scan_sources(preserve_selection=True)
        self.after(3000, self._watch_sources)

    def pick_game(self) -> None:
        if self.applying:
            return
        folder = filedialog.askdirectory(title=self.tr("Папка Carrier Command 2"))
        if not folder:
            return
        installed = inspect_game(Path(folder))
        if installed is None:
            messagebox.showwarning(
                self.tr("Игра не найдена"), self.tr("В выбранной папке нет исполняемого файла CC2.")
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
        folder = filedialog.askdirectory(title=self.tr("Дополнительная папка модов"))
        if folder:
            self.extra_roots.append(Path(folder))
            self.select_game()

    def check_selected(self) -> None:
        if self.applying:
            return
        if self.game is None or self.needs_placement:
            return
        selected = self._ordered_selection()
        roots = list(self.mod_roots)
        if self.game.libraries_dir.exists():
            roots.append(self.game.libraries_dir)
        self.status.set(self.tr("Проверяем выбранные моды и библиотеки…"))
        selected_game = self.game

        def check() -> PackagePlan:
            scan = discover(roots)
            chosen = [mod for mod in scan.mods if mod.id in selected]
            if {mod.id for mod in chosen} != set(selected):
                raise InputError(
                    self.tr("Выбранный мод исчез из папки. Верните его или снимите галочку.")
                )
            return analyze(
                selected_game,
                scan,
                selected,
                tools=bundled_tools(),
                patch_priority=self.patch_priority,
            )

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
                        translate=self.tr,
                    )
                )

        self._background(check, receive, reject_selection=True)

    def apply_selected(self) -> None:
        if self.applying:
            return
        current = self.package_plan
        if current is None or current.blockers or self.needs_placement:
            self.status.set(self.tr("Сначала проверьте выбранный набор."))
            return
        self.status.set(self.tr("Обновляем общую папку модов…"))
        requested = set(self._desired_ids)
        previously_applied = set(self._applied_ids)
        self._set_applying(True)

        def receive(path: Path) -> None:
            self.active_package = path
            self._activation_known = True
            self.selection_dirty = False
            self._applied_ids = {mod.id for mod in current.selected}
            self._applied_patch_priority = current.report.get("merge_policy") == "ordered-patches"
            self._applied_order = [mod.id for mod in current.selected]
            self.mod_order = self._applied_order + [
                key for key in self.mod_order if key not in self._applied_ids
            ]
            by_id = {key: mod for mod in current.selected for key in {mod.id, mod.package_id}}
            required: dict[str, list[str]] = {}
            for mod in current.selected:
                for dependency in mod.dependencies:
                    target = by_id[dependency]
                    required.setdefault(target.id, []).append(mod.name)
            self._required_notes = {
                key: self.tr("Требуется для ") + ", ".join(f"«{name}»" for name in names[:2])
                for key, names in required.items()
            }
            self.activation_status.set(
                self.tr("В игре включены: ")
                + (
                    ", ".join(mod.name for mod in current.selected[:3])
                    + (
                        self.tr(" и ещё {p0}", p0=len(current.selected) - 3)
                        if len(current.selected) > 3
                        else ""
                    )
                    if current.selected
                    else self.tr("нет модов")
                )
            )
            self.status.set(
                self.tr("Готово. Можно запускать игру.")
                if current.selected
                else self.tr("Все моды отключены.")
            )
            for mod in current.selected:
                variable = self.vars.get(mod.id) or self.library_vars.get(mod.id)
                if variable is not None:
                    variable.set(True)
            self._desired_ids = {mod.id for mod in current.selected}
            if self._desired_ids - requested:
                self.status.set(self.tr("Готово. Необходимые библиотеки подключены автоматически."))
                readded = self._desired_ids - requested & previously_applied
                if readded:
                    self.status.set(
                        self.tr("Зависимость остаётся включённой: она нужна выбранным модам.")
                    )
            self._applied_warning = explain_overrides(current.report, self.tr)
            self._clear_notice()
            overridden = sum(item["status"] == "overridden" for item in current.report["files"])
            if overridden:
                self.status.set(self.tr("Готово. Замен по порядку: {p0}.", p0=overridden))
            try:
                self.preferences.set_order(current.game.root, self.mod_order)
                self.preferences.patch_priority = self.patch_priority
                self.preferences.extra_roots = [str(root) for root in self.extra_roots]
                self.preferences.save()
            except (OSError, MCEError):
                self.status.set(self.tr("Моды включены, но настройки не удалось сохранить."))
            self._update_rows()
            self._render_order()
            self._refresh_controls()
            self._maybe_play()

        self._background(
            lambda: apply_plan(current, game_user_dir()), receive, reject_selection=True
        )

    def _maybe_play(self) -> None:
        if self._play_requested and not self.busy and self.launch_button.instate(["!disabled"]):
            self._play_requested = False
            if self.launch() and self._applied_warning is None:
                self.request_close()

    def restore(self) -> None:
        if self.applying:
            return
        if not messagebox.askyesno(
            self.tr("Вернуть прежние моды"), self.tr("Восстановить набор до последнего применения?")
        ):
            return

        def action() -> bool:
            restore_previous(game_user_dir())
            return True

        def receive(_: bool) -> None:
            self.active_package = None
            self.selection_dirty = False
            self.package_plan = None
            self.activation_status.set(self.tr("Прежний набор модов восстановлен."))
            self.status.set(self.tr("Прежний набор восстановлен."))
            self.scan_sources(rebuild_after_scan=False)

        self._set_applying(True)
        self._background(action, receive)

    def _set_applying(self, value: bool) -> None:
        self.applying = value
        self.game_choice.configure(state="disabled" if value else "readonly")
        for check in self.checks.values():
            check.state(["disabled"] if value else ["!disabled"])
        self._update_rows(self.tr("Сохраняем…") if value else self.tr("Проверяем…"))
        self._refresh_controls()

    def request_close(self) -> None:
        if self.applying:
            self.status.set(
                self.tr("Завершаем запись и резервную копию. Окно можно закрыть после завершения.")
            )
            return
        self.destroy()

    def export_report(self) -> None:
        plan = self.problem_report or self.package_plan
        if plan is None:
            self.show_problem()
            return
        name = filedialog.asksaveasfilename(
            title=self.tr("Сохранить отчёт"), defaultextension=".json"
        )
        if name:
            try:
                write_report(plan.report, Path(name), list(plan.scan.roots))
            except (MCEError, OSError):
                self.status.set(self.tr("Отчёт не сохранён: выберите новый файл вне исходников."))

    def launch(self) -> bool:
        if self.applying:
            self.status.set(self.tr("Дождитесь завершения применения модов."))
            return False
        if self.game is None or self.needs_placement:
            self.status.set(self.tr("Сначала выберите игру и разместите приложение рядом с ней."))
            return False
        if (game_user_dir() / "cc2-mce/pending.json").exists():
            self.status.set(self.tr("Сначала дождитесь восстановления незавершённой сборки."))
            return False
        if self.selection_dirty:
            self.status.set(
                self.tr("Выбранный набор ещё не готов. Дождитесь сборки или устраните конфликт.")
            )
            return False
        try:
            expected = (self.active_package,) if self._applied_ids else ()
            if active_paths(game_user_dir()) != expected:
                self._play_requested = True
                self.selection_dirty = True
                self.status.set(self.tr("Обновляем сборку…"))
                self._queue_rebuild()
                self._refresh_controls()
                return False
            launch_game(
                self.game, game_user_dir(), self.active_package if self._applied_ids else None
            )
            return True
        except (OSError, MCEError):
            self.status.set(self.tr("Не удалось запустить игру."))
            return False


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-bundle":
        import json

        from cc2_mce.reports import ensure_destination
        from cc2_mce.toolchain import verify_bundle

        destination = ensure_destination(Path(sys.argv[2]), [])
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(verify_bundle(), stream)
        return
    geometry = None
    resume_request = None
    play_on_ready = True if "--play" in sys.argv[1:] else None
    while True:
        app = App(resume_request=resume_request, play_on_ready=play_on_ready)
        if geometry:
            app.geometry(geometry)
        app.mainloop()
        if not app.restart_requested:
            break
        geometry = app.restart_geometry
        resume_request = app.restart_selection
        play_on_ready = app._play_requested


if __name__ == "__main__":
    main()
