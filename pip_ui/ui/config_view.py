"""Configuration dashboard window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from pip_ui.config_inspector import ConfigInspector
from pip_ui.models import InterpreterInfo


class ConfigView(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        interpreter_info: Optional[InterpreterInfo] = None,
        show_secrets: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.title("pip-ui - Configuration Dashboard")
        self.geometry("900x650")
        self.interpreter_info = interpreter_info
        self.show_secrets = tk.BooleanVar(value=show_secrets)
        self.inspector: Optional[ConfigInspector] = None
        if interpreter_info:
            self.inspector = ConfigInspector(interpreter_info.path)
        self.build_ui()
        self.populate()

    def build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(toolbar, text="Refresh", command=self.populate).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Export Diagnostics...", command=self.export_diagnostics).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Checkbutton(
            toolbar,
            text="Show Sensitive Values",
            variable=self.show_secrets,
            command=self.populate,
        ).pack(side=tk.LEFT, padx=8)

        outer_frame = ttk.Frame(self)
        outer_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(outer_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(outer_frame, yscrollcommand=scrollbar.set, borderwidth=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas.yview)

        self.content_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor=tk.NW)
        self.content_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self.on_wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def on_wheel(self, event: Any) -> None:
        delta = -1 if getattr(event, "delta", 0) > 0 else 1
        self.canvas.yview_scroll(delta, "units")

    def add_section(self, title: str, content: str, warning: bool = False) -> None:
        section = ttk.LabelFrame(self.content_frame, text=title, padding=8)
        section.pack(fill=tk.X, padx=8, pady=4)
        height = max(2, min(20, content.count("\n") + 1))
        text = tk.Text(section, wrap=tk.WORD, height=height, state=tk.DISABLED)
        text.configure(state=tk.NORMAL)
        text.insert(tk.END, content)
        text.configure(state=tk.DISABLED)
        if warning:
            text.configure(foreground="#a00000")
        text.pack(fill=tk.X)

    def populate(self) -> None:
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if self.interpreter_info is None:
            self.add_section(
                "No Interpreter Selected",
                "Please select a Python interpreter to view configuration.",
            )
            return

        info = self.interpreter_info
        self.add_section(
            "Active Interpreter",
            (
                f"Path: {info.path}\nVersion: {info.version}\nType: {info.env_type}\n"
                f"Is venv: {info.is_venv}\nPrefix: {info.prefix}\nBase prefix: {info.base_prefix}"
            ),
        )

        if self.inspector is None:
            self.inspector = ConfigInspector(info.path)

        pip_version = self.inspector.get_pip_version()
        self.add_section("Pip Version", pip_version)

        try:
            config_files = self.inspector.discover_config_files()
            if config_files:
                lines = []
                for c in config_files:
                    lines.append(
                        f"[{c.scope}] {c.path}\n    exists={c.exists}  size={c.size}  modified={c.modified}"
                    )
                self.add_section("Config Files", "\n".join(lines))
            else:
                self.add_section("Config Files", "(none reported by pip config debug)")
        except Exception as exc:
            self.add_section("Config Files", f"Error: {exc}")

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
            index_info = self.inspector.detect_index_info()
            lines = [
                f"Main index URL: {index_info.main_index_url or '(default)'}",
                f"Extra index URLs: {index_info.extra_index_urls or '(none)'}",
                f"Find-links: {index_info.find_links or '(none)'}",
                f"Trusted hosts: {index_info.trusted_hosts or '(none)'}",
                f"No-index mode: {index_info.no_index}",
                f"Credentials embedded in URLs: {index_info.has_credentials}",
            ]
            self.add_section("Index and Repository Settings", "\n".join(lines))

            # Warnings.
            warnings: list[str] = []
            if index_info.has_credentials and not self.show_secrets.get():
                warnings.append(
                    "Credentials detected in an index URL. They are redacted above. Enable "
                    "'Show Sensitive Values' to view them."
                )
            if index_info.trusted_hosts:
                warnings.append(
                    "trusted-host disables TLS validation for the named host(s). Use only on trusted networks."
                )
            if index_info.main_index_url and index_info.main_index_url.startswith("http://"):
                warnings.append("Main index URL uses plain http://; prefer https://.")
            if index_info.extra_index_urls:
                warnings.append(
                    "Multiple package indexes are configured. Be aware of dependency-confusion risk if any "
                    "extra index hosts public-named packages."
                )
            if warnings:
                self.add_section("Index Warnings", "\n".join(f"- {w}" for w in warnings), warning=True)
        except Exception as exc:
            self.add_section("Index Settings", f"Error: {exc}")

        try:
            env_vars = self.inspector.get_env_vars(show_secrets=self.show_secrets.get())
            if env_vars:
                content = "\n".join(f"{k} = {v}" for k, v in env_vars.items())
            else:
                content = "(no relevant environment variables)"
            self.add_section("Environment Variables", content)
        except Exception as exc:
            self.add_section("Environment Variables", f"Error: {exc}")

        try:
            cache_dir = self.inspector.run_cache_dir()
            cache_info = self.inspector.run_cache_info()
            cache_text = f"Cache directory: {cache_dir or '(unknown)'}\n\n{cache_info or ''}"
            self.add_section("Cache", cache_text.strip())
        except Exception as exc:
            self.add_section("Cache", f"Error: {exc}")

        try:
            venv = self.inspector.virtual_env_status()
            lines = [f"{k} = {v or '(unset)'}" for k, v in venv.items()]
            lines.append(f"Detected as venv: {info.is_venv}")
            self.add_section("Virtual Environment", "\n".join(lines))
        except Exception as exc:
            self.add_section("Virtual Environment", f"Error: {exc}")

        try:
            config_debug = self.inspector.run_config_debug()
            self.add_section("Raw pip config debug Output", config_debug or "(no output)")
        except Exception as exc:
            self.add_section("Raw pip config debug Output", f"Error: {exc}")

    def export_diagnostics(self) -> None:
        if self.inspector is None:
            from pip_ui.ui.dialogs import error_dialog

            error_dialog(self, "No Inspector", "No interpreter selected.")
            return
        from pip_ui.ui.dialogs import info_dialog, save_file_dialog

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
        report = self.inspector.build_diagnostics_report(fmt, show_secrets=self.show_secrets.get())
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
        info_dialog(self, "Exported", f"Diagnostics saved to:\n{path}")
