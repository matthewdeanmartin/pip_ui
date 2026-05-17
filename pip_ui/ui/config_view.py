"""Configuration dashboard window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from pip_ui.config_inspector import ConfigInspector
from pip_ui.models import InterpreterInfo


class ConfigView(tk.Toplevel):
    def __init__(self, parent: tk.Widget, interpreter_info: Optional[InterpreterInfo] = None, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.title("pip-ui - Configuration Dashboard")
        self.geometry("800x600")
        self.interpreter_info = interpreter_info
        self.show_secrets = tk.BooleanVar(value=False)
        self.inspector: Optional[ConfigInspector] = None
        if interpreter_info:
            self.inspector = ConfigInspector(interpreter_info.path)
        self.build_ui()
        self.populate()

    def build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(toolbar, text="Refresh", command=self.populate).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Export Diagnostics...", command=self.export_diagnostics).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(toolbar, text="Show Secrets", variable=self.show_secrets, command=self.populate).pack(side=tk.LEFT, padx=8)

        outer_frame = ttk.Frame(self)
        outer_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(outer_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(outer_frame, yscrollcommand=scrollbar.set, borderwidth=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas.yview)

        self.content_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor=tk.NW)
        self.content_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

    def add_section(self, title: str, content: str) -> None:
        section = ttk.LabelFrame(self.content_frame, text=title, padding=8)
        section.pack(fill=tk.X, padx=8, pady=4)
        text = tk.Text(section, wrap=tk.WORD, height=max(2, content.count("\n") + 1), state=tk.DISABLED)
        text.configure(state=tk.NORMAL)
        text.insert(tk.END, content)
        text.configure(state=tk.DISABLED)
        text.pack(fill=tk.X)

    def populate(self) -> None:
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if self.interpreter_info is None:
            self.add_section("No Interpreter Selected", "Please select a Python interpreter to view configuration.")
            return

        info = self.interpreter_info
        self.add_section(
            "Active Interpreter",
            f"Path: {info.path}\nVersion: {info.version}\nType: {info.env_type}\nIs venv: {info.is_venv}\nPrefix: {info.prefix}",
        )

        if self.inspector is None:
            self.inspector = ConfigInspector(info.path)

        pip_version = self.inspector.get_pip_version()
        self.add_section("Pip Version", pip_version)

        try:
            config_values = self.inspector.run_config_list()
            if config_values:
                content = "\n".join(f"{k} = {v}" for k, v in config_values.items())
            else:
                content = "(no configuration values)"
            self.add_section("Active Config Values", content)
        except Exception as exc:
            self.add_section("Active Config Values", f"Error: {exc}")

        try:
            env_vars = self.inspector.get_env_vars()
            if env_vars:
                content = "\n".join(f"{k} = {v}" for k, v in env_vars.items())
            else:
                content = "(no relevant environment variables)"
            self.add_section("Environment Variables", content)
        except Exception as exc:
            self.add_section("Environment Variables", f"Error: {exc}")

        try:
            config_debug = self.inspector.run_config_debug()
            self.add_section("Config Debug Output", config_debug or "(no output)")
        except Exception as exc:
            self.add_section("Config Debug Output", f"Error: {exc}")

    def export_diagnostics(self) -> None:
        if self.inspector is None:
            from pip_ui.ui.dialogs import error_dialog
            error_dialog(self, "No Inspector", "No interpreter selected.")
            return
        from pip_ui.ui.dialogs import save_file_dialog
        path = save_file_dialog(
            self,
            title="Export Diagnostics",
            default_name="pip_diagnostics.md",
            filetypes=[("Markdown", "*.md"), ("JSON", "*.json"), ("Text", "*.txt"), ("All", "*.*")],
        )
        if not path:
            return
        fmt = "markdown"
        if path.endswith(".json"):
            fmt = "json"
        elif path.endswith(".txt"):
            fmt = "text"
        report = self.inspector.build_diagnostics_report(fmt)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
        from pip_ui.ui.dialogs import info_dialog
        info_dialog(self, "Exported", f"Diagnostics saved to:\n{path}")
