"""Minimal Windows window over the existing CLI core. No new merge logic lives here.

Pick mods, press "Merge". The window calls the same plan/build path the CLI uses and shows the
result: merged, conflicts, or blocked. Original mod folders are never written.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cc2_mce.cli import main as cli_main

GAME_ID = "1489630"
# Stock scripts live in the game folder; we only read them and copy into a temp baseline.
STEAM_GAME_CANDIDATES = [
    Path("C:/Program Files (x86)/Steam/steamapps/common/Carrier Command 2"),
    Path.home() / "Library/Application Support/Steam/steamapps/common/Carrier Command 2",
]
STOCK_SUBDIRS = [Path("."), Path("carriercommand.app/Contents/Resources/rom_0")]


def find_game_scripts() -> Path | None:
    """Return the stock scripts folder if the game is installed in a known Steam location."""
    for game in STEAM_GAME_CANDIDATES:
        for sub in STOCK_SUBDIRS:
            scripts = game / sub / "scripts"
            if scripts.is_dir():
                return scripts
    return None


def make_baseline(scripts: Path) -> Path:
    """Copy only the stock .lua files we compare against into a fresh temp baseline."""
    import tempfile

    from cc2_mce.baseline import Baseline  # noqa: F401  (ensures the module is importable)

    import hashlib
    import json

    # Resolve symlinks (macOS /var -> /private/var): the CLI rejects link-containing roots.
    root = Path(tempfile.mkdtemp(prefix="cc2-mce-baseline-")).resolve()
    entries = []
    for source in sorted(scripts.glob("*.lua")):
        data = source.read_bytes()
        logical = f"scripts/{source.name}"
        target = root / "content" / logical
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        entries.append({
            "logical_path": logical,
            "source_path": f"content/{logical}",
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    # Honest identity: stock scripts only, not verified against a real game executable.
    manifest = {
        "schema_version": 1,
        "kind": "synthetic",
        "complete": False,
        "game": {"version": "synthetic-stock-scripts", "executable_sha256": None},
        "files": entries,
    }
    (root / "baseline-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return root


def launch_game() -> str:
    """Start the game through Steam, the same way the Steam Play button does."""
    import os
    import sys
    import webbrowser

    url = f"steam://rungameid/{GAME_ID}"
    if sys.platform == "win32":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        webbrowser.open(url)
    return "Игра запущена через Steam."


def run_merge(mods_dir: Path, mod_ids: list[str], baseline: Path, output: Path) -> tuple[int, str]:
    """Runs the same code path as `cc2-mce build`. Returns (exit code, human message)."""
    argv = [
        "build",
        "--mods-dir", str(mods_dir),
        "--mods", *mod_ids,
        "--baseline", str(baseline),
        "--output", str(output),
    ]
    code = cli_main(argv, quiet=True)
    if code == 0:
        return code, f"Готово. Объединённый мод создан в:\n{output}"
    if code == 2:
        return code, "Есть конфликт или блокировка: правки пересекаются, ничего не записано."
    if code == 3:
        return code, "Не найдена база игры (baseline). Ничего не записано."
    return code, f"Сборка остановлена (код {code}). Ничего не записано."


class App(tk.Tk):
    def __init__(self, mods_dir: Path | None = None) -> None:
        super().__init__()
        self.title("CC2 Mod Loader")
        self.geometry("560x420")
        self.mods_dir = mods_dir
        self.baseline: Path | None = None
        self.output: Path | None = None
        self.vars: dict[str, tk.BooleanVar] = {}

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Моды для объединения", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.list_frame = ttk.Frame(frame)
        self.list_frame.pack(fill="x", pady=6)

        ttk.Button(frame, text="Выбрать папку модов…", command=self.pick_mods).pack(anchor="w")
        ttk.Button(frame, text="Выбрать базу игры…", command=self.pick_baseline).pack(anchor="w", pady=4)
        ttk.Button(frame, text="Куда сохранить…", command=self.pick_output).pack(anchor="w")

        self.status = tk.StringVar(value="Выберите папку модов, базу игры и место сохранения.")
        ttk.Label(frame, textvariable=self.status, wraplength=520, foreground="#333").pack(
            anchor="w", pady=10
        )
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e")
        ttk.Button(buttons, text="Запустить игру", command=self.launch).pack(side="left", padx=4)
        ttk.Button(buttons, text="Объединить", command=self.merge).pack(side="left", padx=4)

        found = find_game_scripts()
        if found is not None:
            self.baseline = make_baseline(found)
            self.status.set("База игры найдена автоматически. Отметьте моды.")
        if mods_dir:
            self.load_mods(mods_dir)

    def load_mods(self, folder: Path) -> None:
        self.mods_dir = folder
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.vars.clear()
        for item in sorted(p.name for p in folder.iterdir() if p.is_dir()):
            var = tk.BooleanVar(value=False)
            self.vars[item] = var
            ttk.Checkbutton(self.list_frame, text=item, variable=var).pack(anchor="w")
        self.status.set(f"Найдено папок: {len(self.vars)}. Отметьте моды.")

    def pick_mods(self) -> None:
        folder = filedialog.askdirectory(title="Папка с модами")
        if folder:
            self.load_mods(Path(folder))

    def pick_baseline(self) -> None:
        folder = filedialog.askdirectory(title="База игры (стоковые файлы)")
        if folder:
            self.baseline = Path(folder)
            self.status.set(f"База: {folder}")

    def pick_output(self) -> None:
        folder = filedialog.askdirectory(title="Куда сохранить объединённый мод")
        if folder:
            self.output = Path(folder)
            self.status.set(f"Сохранение в: {folder}")

    def launch(self) -> None:
        self.status.set(launch_game())

    def merge(self) -> None:
        chosen = [name for name, var in self.vars.items() if var.get()]
        if not self.mods_dir or not chosen or not self.baseline or not self.output:
            messagebox.showwarning("CC2 Mod Loader", "Выберите моды, базу и место сохранения.")
            return
        _, message = run_merge(self.mods_dir, chosen, self.baseline, self.output)
        self.status.set(message)
        messagebox.showinfo("CC2 Mod Loader", message)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
