"""Tkinter GUI for MatrixTag Studio."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import AppConfig, load_app_config, save_app_config
from .core import (
    DEFAULT_DPI,
    allocate_batch_output_dir,
    check_runtime_dependencies,
    generate_batch_job,
    preview_batch_range,
    validate_batch_job,
)
from .errors import DMLabelError

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception as exc:  # pragma: no cover - runtime/platform dependent
    raise RuntimeError("Tkinter is required for GUI mode.") from exc


APP_NAME = "MatrixTag Studio"


class SettingsDialog(tk.Toplevel):
    """Modal settings dialog."""

    def __init__(self, master: "DMLabelGUI", config: AppConfig):
        super().__init__(master)
        self.title("Settings")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.output_var = tk.StringVar(value=config.output_root)
        self.font_var = tk.StringVar(value=config.font_path)
        self.result: Optional[AppConfig] = None

        container = tk.Frame(self, padx=16, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Output Root").grid(row=0, column=0, sticky="w")
        tk.Entry(container, textvariable=self.output_var, width=46).grid(
            row=1, column=0, sticky="we", pady=(4, 8)
        )
        tk.Button(container, text="Browse", command=self.pick_output_dir).grid(
            row=1, column=1, padx=(8, 0)
        )

        tk.Label(container, text="Font Path (Optional)").grid(row=2, column=0, sticky="w")
        tk.Entry(container, textvariable=self.font_var, width=46).grid(
            row=3, column=0, sticky="we", pady=(4, 8)
        )

        font_row = tk.Frame(container)
        font_row.grid(row=3, column=1, padx=(8, 0))
        tk.Button(font_row, text="Browse", command=self.pick_font).pack(fill="x")
        tk.Button(font_row, text="Clear", command=lambda: self.font_var.set("")).pack(
            fill="x", pady=(4, 0)
        )

        action_row = tk.Frame(container)
        action_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(8, 0))
        tk.Button(action_row, text="Cancel", width=10, command=self.destroy).pack(side="left")
        tk.Button(action_row, text="Save", width=10, command=self.save).pack(side="left", padx=(8, 0))

        container.grid_columnconfigure(0, weight=1)

    def pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(
            parent=self,
            title="Select output root",
            initialdir=self.output_var.get() or str(Path.cwd()),
        )
        if selected:
            self.output_var.set(selected)

    def pick_font(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self,
            title="Select font",
            filetypes=[("Font", "*.ttf *.otf *.ttc"), ("All files", "*.*")],
        )
        if selected:
            self.font_var.set(selected)

    def save(self) -> None:
        output_root = self.output_var.get().strip()
        font_path = self.font_var.get().strip()
        if not output_root:
            messagebox.showerror(APP_NAME, "Output root cannot be empty.", parent=self)
            return
        if font_path and not Path(font_path).exists():
            messagebox.showerror(APP_NAME, "Font file does not exist.", parent=self)
            return
        self.result = AppConfig(output_root=output_root, font_path=font_path)
        self.destroy()


class DMLabelGUI(tk.Tk):
    """Main GUI window."""

    def __init__(self, project_root: Path):
        super().__init__()
        self.title(APP_NAME)
        self.resizable(False, False)

        self.project_root = project_root
        self.config_state = load_app_config(project_root)

        self.prefix_var = tk.StringVar(value="LD")
        self.middle_code_var = tk.StringVar(value="4000")
        self.start_serial_var = tk.StringVar(value="0035")
        self.quantity_var = tk.StringVar(value="1000")
        self.preview_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready.")

        self._build_ui()
        self._bind_events()
        self.refresh_preview()

    def _build_ui(self) -> None:
        root = tk.Frame(self, padx=18, pady=18)
        root.pack(fill="both", expand=True)

        tk.Label(root, text="Line 1 Prefix").grid(row=0, column=0, sticky="w")
        tk.Entry(root, textvariable=self.prefix_var, width=16).grid(row=1, column=0, sticky="we", pady=(4, 10))

        tk.Label(root, text="Line 2 Middle Code").grid(row=2, column=0, sticky="w")
        tk.Entry(root, textvariable=self.middle_code_var, width=16).grid(
            row=3, column=0, sticky="we", pady=(4, 10)
        )

        tk.Label(root, text="Line 3 Start Serial").grid(row=4, column=0, sticky="w")
        tk.Entry(root, textvariable=self.start_serial_var, width=16).grid(
            row=5, column=0, sticky="we", pady=(4, 10)
        )

        tk.Label(root, text="Quantity").grid(row=6, column=0, sticky="w")
        tk.Entry(root, textvariable=self.quantity_var, width=16).grid(row=7, column=0, sticky="we", pady=(4, 14))

        row = tk.Frame(root)
        row.grid(row=8, column=0, sticky="we")
        tk.Button(row, text="Generate", width=14, command=self.generate).pack(side="left")
        tk.Button(row, text="Settings", width=10, command=self.open_settings).pack(side="left", padx=(8, 0))

        tk.Label(root, text="Preview").grid(row=9, column=0, sticky="w", pady=(14, 0))
        tk.Label(root, textvariable=self.preview_var, width=44, anchor="w", justify="left", wraplength=380).grid(
            row=10, column=0, sticky="we", pady=(4, 0)
        )

        tk.Label(root, text="Status").grid(row=11, column=0, sticky="w", pady=(14, 0))
        tk.Label(root, textvariable=self.status_var, width=44, anchor="w", justify="left", wraplength=380).grid(
            row=12, column=0, sticky="we", pady=(4, 0)
        )

        root.grid_columnconfigure(0, weight=1)

    def _bind_events(self) -> None:
        for var in [self.prefix_var, self.middle_code_var, self.start_serial_var, self.quantity_var]:
            var.trace_add("write", lambda *_: self.refresh_preview())

    def _output_root(self) -> Path:
        return Path(self.config_state.output_root)

    def _font_path(self) -> Optional[str]:
        return self.config_state.font_path or None

    def refresh_preview(self) -> None:
        try:
            job = validate_batch_job(
                prefix=self.prefix_var.get(),
                middle_code=self.middle_code_var.get(),
                start_serial_text=self.start_serial_var.get(),
                quantity_text=self.quantity_var.get(),
                output_root=self._output_root(),
            )
            output_dir = allocate_batch_output_dir(job.prefix, job.output_root)
            start_code, end_code = preview_batch_range(job)
            self.preview_var.set(
                f"Folder: {output_dir}\nRange: {start_code} -> {end_code}\nQuantity: {job.quantity}"
            )
            self.status_var.set("Input valid.")
        except Exception as exc:
            self.preview_var.set("Fix input values and try again.")
            self.status_var.set(str(exc))

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.config_state)
        self.wait_window(dialog)
        if dialog.result is not None:
            self.config_state = dialog.result
            save_app_config(self.config_state)
            self.refresh_preview()

    def generate(self) -> None:
        try:
            job = validate_batch_job(
                prefix=self.prefix_var.get(),
                middle_code=self.middle_code_var.get(),
                start_serial_text=self.start_serial_var.get(),
                quantity_text=self.quantity_var.get(),
                output_root=self._output_root(),
            )
            batch_dir, files, start_code, end_code = generate_batch_job(
                job=job, dpi=DEFAULT_DPI, font_path=self._font_path()
            )
            self.status_var.set(
                f"Done: {len(files)} labels\nFolder: {batch_dir}\nRange: {start_code} -> {end_code}"
            )
            messagebox.showinfo(
                APP_NAME,
                f"Generated {len(files)} labels.\n\nFolder: {batch_dir}\nRange: {start_code} -> {end_code}",
                parent=self,
            )
            self.refresh_preview()
        except Exception as exc:
            self.status_var.set(f"Failed: {exc}")
            messagebox.showerror(APP_NAME, str(exc), parent=self)


def launch_gui(project_root: Path) -> None:
    """Launch GUI app with friendly dependency errors."""
    try:
        check_runtime_dependencies()
    except DMLabelError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, str(exc))
        root.destroy()
        raise
    app = DMLabelGUI(project_root=project_root)
    app.mainloop()
