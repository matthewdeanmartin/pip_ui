"""PypiServerPanel — live table of served packages + CommandForm."""

# pylint: disable=consider-using-with

from __future__ import annotations

import os
import queue
import re
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, ClassVar

from pip_ui.ui.command_form import CommandForm

_REFRESH_TRIGGERS = {"pypiserver_update"}

# Regex for parsing package filenames.
# Handles wheels: name-version(-tags).whl
# Handles sdists: name-version.tar.gz / name-version.zip
_WHEEL_RE = re.compile(r"^(?P<name>.+?)-(?P<version>\d[^-]*)-", re.IGNORECASE)
_SDIST_RE = re.compile(r"^(?P<name>.+?)-(?P<version>\d.*)\.(?:tar\.gz|zip)$", re.IGNORECASE)
_PKG_EXTENSIONS = (".whl", ".tar.gz", ".zip")


def _parse_package_filename(filename: str) -> tuple[str, str]:
    """Extract (name, version) from a package filename.

    Returns:
        Tuple of (name, version). Values are empty strings when parsing fails.
    """
    if filename.endswith(".whl"):
        m = _WHEEL_RE.match(filename)
        if m:
            return m.group("name").replace("_", "-"), m.group("version")
    else:
        m = _SDIST_RE.match(filename)
        if m:
            return m.group("name").replace("_", "-"), m.group("version")
    return filename, ""


class PypiServerPanel(ttk.Frame):
    """Top: live packages table. Bottom: CommandForm."""

    COLUMNS = ("name", "version", "filename")
    COL_LABELS: ClassVar[dict[str, str]] = {
        "name": "Package",
        "version": "Version",
        "filename": "Filename",
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
        self._packages_dir: str = "./packages"

        self._build_packages_table()

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
        self.refresh_packages()

    # ---- packages table -----------------------------------------------------

    def _build_packages_table(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Served Packages", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(header, text="Refresh", command=self.refresh_packages).pack(side=tk.RIGHT, padx=4, pady=2)

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

    # ---- public API (delegates to CommandForm) ------------------------------

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

    def set_preview_prefix(self, prefix: list[str]) -> None:
        self.command_form.set_preview_prefix(prefix)

    def notify_run_done(self, exit_code: int, spec_name: str, _argv: list[str]) -> None:
        if spec_name in _REFRESH_TRIGGERS and exit_code == 0:
            self.refresh_packages()

    # ---- packages directory scanning ----------------------------------------

    def set_packages_dir(self, path: str) -> None:
        """Update the packages directory used for scanning."""
        self._packages_dir = path

    def refresh_packages(self) -> None:
        """Scan the packages directory in a background thread."""
        packages_dir = self._packages_dir

        def worker() -> None:
            rows: list[dict[str, str]] = []
            try:
                if not os.path.isdir(packages_dir):
                    self._refresh_queue.put([])
                    return
                for filename in sorted(os.listdir(packages_dir)):
                    lower = filename.lower()
                    if not any(lower.endswith(ext) for ext in _PKG_EXTENSIONS):
                        continue
                    name, version = _parse_package_filename(filename)
                    rows.append({"name": name, "version": version, "filename": filename})
                self._refresh_queue.put(rows)
            except OSError:
                self._refresh_queue.put([])

        threading.Thread(target=worker, daemon=True, name="pypiserver-pkg-refresh").start()

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
                iid=row["filename"],
                values=(row["name"], row["version"], row["filename"]),
            )
