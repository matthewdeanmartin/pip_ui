"""PipxAppsPanel — live table of installed pipx apps + CommandForm."""

from __future__ import annotations

import contextlib
import json
import os
import queue
import subprocess  # nosec B404
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, ClassVar

from pip_ui.encoding import utf8_subprocess_kwargs
from pip_ui.ui.command_form import CommandForm

_REFRESH_TRIGGERS = {"pipx_install", "pipx_uninstall", "pipx_upgrade", "pipx_upgrade_all"}


class PipxAppsPanel(ttk.Frame):
    """Top: live pipx apps table. Bottom: CommandForm."""

    COLUMNS = ("app", "version", "python", "path")
    COL_LABELS: ClassVar[dict[str, str]] = {
        "app": "App",
        "version": "Version",
        "python": "Python",
        "path": "Install Path",
    }

    def __init__(
        self,
        parent: tk.Misc,
        on_run: Any,
        on_form_change: Any,
        global_values_provider: Any,
        on_open_global_options: Any,
        global_requirements_provider: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._outer_on_run = on_run
        self._refresh_queue: queue.Queue[list[dict[str, str]]] = queue.Queue()

        self._build_apps_table()

        sep = ttk.Separator(self, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=2)

        self.command_form = CommandForm(
            self,
            on_run=self._outer_on_run,
            on_form_change=on_form_change,
            global_values_provider=global_values_provider,
            on_open_global_options=on_open_global_options,
            global_requirements_provider=global_requirements_provider,
        )
        self.command_form.pack(fill=tk.BOTH, expand=True)

        self._poll()
        self.refresh_apps()

    # ---- apps table ---------------------------------------------------------

    def _build_apps_table(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Installed Apps", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(header, text="Refresh", command=self.refresh_apps).pack(side=tk.RIGHT, padx=4, pady=2)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=False)

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            height=6,
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )
        scrollbar.config(command=self._tree.yview)
        self._tree.pack(fill=tk.BOTH, expand=True)

        for col in self.COLUMNS:
            self._tree.heading(col, text=self.COL_LABELS[col])
            self._tree.column(col, width=160, anchor=tk.W)

        self._tree.bind("<<TreeviewSelect>>", self._on_app_select)
        self._tree.bind("<Button-3>", self._on_right_click)

        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="Upgrade", command=self._ctx_upgrade)
        self._ctx_menu.add_command(label="Uninstall", command=self._ctx_uninstall)
        self._ctx_menu.add_command(label="Open install path", command=self._ctx_open_path)

    # ---- public API ---------------------------------------------------------

    @property
    def spec(self) -> Any:
        return self.command_form.spec

    @spec.setter
    def spec(self, value: Any) -> None:
        self.command_form.spec = value

    @property
    def title_label(self) -> Any:
        return self.command_form.title_label

    @property
    def desc_label(self) -> Any:
        return self.command_form.desc_label

    @property
    def run_btn(self) -> Any:
        return self.command_form.run_btn

    @property
    def dry_run_btn(self) -> Any:
        return self.command_form.dry_run_btn

    def set_command(self, spec: Any) -> None:
        self.command_form.set_command(spec)

    def get_argv(self) -> list[str]:
        return self.command_form.get_argv()

    def do_run(self) -> None:
        self.command_form.do_run()

    def update_preview(self) -> None:
        self.command_form.update_preview()

    def apply_show_secrets(self, reveal: bool) -> None:
        self.command_form.apply_show_secrets(reveal)

    def apply_global_requirements(self, path: str) -> None:
        self.command_form.apply_global_requirements(path)

    def refresh_globals_summary(self) -> None:
        self.command_form.refresh_globals_summary()

    def copy_command(self) -> None:
        self.command_form.copy_command()

    def notify_run_done(self, exit_code: int, spec_name: str, _argv: list[str]) -> None:
        if spec_name in _REFRESH_TRIGGERS and exit_code == 0:
            self.refresh_apps()

    def refresh_apps(self) -> None:
        """Run pipx list --json in a background thread."""

        def worker() -> None:
            try:
                result = subprocess.run(  # nosec B603
                    ["pipx", "list", "--json"],
                    capture_output=True,
                    timeout=20,
                    **utf8_subprocess_kwargs(),
                )
                data = json.loads(result.stdout or "{}")
                rows: list[dict[str, str]] = []
                for app_name, venv_info in data.get("venvs", {}).items():
                    metadata = venv_info.get("metadata", {})
                    main_pkg = metadata.get("main_package", {})
                    python_path = metadata.get("python_path", "")
                    version = main_pkg.get("package_version", "")
                    install_path = venv_info.get("venv_location", "")
                    rows.append(
                        {
                            "app": app_name,
                            "version": version,
                            "python": python_path,
                            "path": install_path,
                        }
                    )
                self._refresh_queue.put(rows)
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
                self._refresh_queue.put([])

        threading.Thread(target=worker, daemon=True, name="pipx-apps-refresh").start()

    # ---- internal -----------------------------------------------------------

    def _poll(self) -> None:
        try:
            rows = self._refresh_queue.get_nowait()
            self._populate_tree(rows)
        except queue.Empty:
            pass
        self.after(200, self._poll)

    def _populate_tree(self, rows: list[dict[str, str]]) -> None:
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            self._tree.insert(
                "",
                tk.END,
                iid=row["app"],
                values=(row["app"], row["version"], row["python"], row["path"]),
            )

    def _current_app(self) -> str | None:
        sel = self._tree.selection()
        return sel[0] if sel else None

    def _on_app_select(self, _event: Any) -> None:
        app = self._current_app()
        if app:
            self._prefill_package(app)

    def _prefill_package(self, value: str) -> None:
        for fw in self.command_form.field_widgets:
            if fw.arg.name in ("package", "app"):
                with contextlib.suppress(Exception):
                    fw.var.set(value)  # type: ignore[arg-type]
                self.command_form.update_preview()
                break

    def _on_right_click(self, event: Any) -> None:
        row_id = self._tree.identify_row(event.y)
        if row_id:
            self._tree.selection_set(row_id)
        self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_upgrade(self) -> None:
        app = self._current_app()
        if app:
            self._prefill_package(app)

    def _ctx_uninstall(self) -> None:
        app = self._current_app()
        if app:
            self._prefill_package(app)

    def _ctx_open_path(self) -> None:
        app = self._current_app()
        if not app:
            return
        # Find path from tree values
        try:
            values = self._tree.item(app, "values")
            path = values[3] if len(values) > 3 else ""
        except Exception:
            path = ""
        if not path:
            return
        try:
            import sys

            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined,unused-ignore]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path], shell=False)  # nosec B603
            else:
                subprocess.Popen(["xdg-open", path], shell=False)  # nosec B603
        except OSError:
            pass
