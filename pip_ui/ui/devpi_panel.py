"""DevpiPanel — live index table + status label + CommandForm for devpi."""

# pylint: disable=consider-using-with

from __future__ import annotations

import contextlib
import queue
import subprocess  # nosec B404
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, ClassVar

from pip_ui.encoding import utf8_subprocess_kwargs
from pip_ui.process_utils import resolve_executable
from pip_ui.ui.command_form import CommandForm

_REFRESH_TRIGGERS = {"devpi_index_create", "devpi_index_delete"}


class DevpiPanel(ttk.Frame):
    """Top: server status + live index table. Bottom: CommandForm."""

    COLUMNS = ("index", "type", "bases", "volatile")
    COL_LABELS: ClassVar[dict[str, str]] = {
        "index": "Index",
        "type": "Type",
        "bases": "Bases",
        "volatile": "Volatile",
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
        self._status_queue: queue.Queue[str] = queue.Queue()

        self._build_status_bar()
        self._build_index_table()

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
        self._refresh_status()
        self.refresh_indexes()

    # ---- status bar ---------------------------------------------------------

    def _build_status_bar(self) -> None:
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X)
        ttk.Label(status_frame, text="Server:", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=4, pady=2)
        self._status_var = tk.StringVar(value="(unknown)")
        ttk.Label(status_frame, textvariable=self._status_var).pack(side=tk.LEFT, padx=4, pady=2)

    # ---- index table --------------------------------------------------------

    def _build_index_table(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Indexes", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(header, text="Refresh", command=self.refresh_indexes).pack(side=tk.RIGHT, padx=4, pady=2)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=False)

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            height=5,
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )
        scrollbar.config(command=self._tree.yview)
        self._tree.pack(fill=tk.BOTH, expand=True)

        for col in self.COLUMNS:
            self._tree.heading(col, text=self.COL_LABELS[col])
            self._tree.column(col, width=150, anchor=tk.W)

        self._tree.bind("<<TreeviewSelect>>", self._on_index_select)
        self._tree.bind("<Button-3>", self._on_right_click)

        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="Use Index", command=self._ctx_use)
        self._ctx_menu.add_command(label="Delete Index", command=self._ctx_delete)

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

    def set_preview_prefix(self, prefix: list[str]) -> None:
        self.command_form.set_preview_prefix(prefix)

    def notify_run_done(self, exit_code: int, spec_name: str, _argv: list[str]) -> None:
        """Auto-refresh index table after mutating commands."""
        if spec_name in _REFRESH_TRIGGERS and exit_code == 0:
            self.refresh_indexes()
        if spec_name == "devpi_use" and exit_code == 0:
            self._refresh_status()

    def refresh_indexes(self) -> None:
        """Run devpi index -l in a background thread."""
        devpi_exe = resolve_executable("devpi")
        if devpi_exe is None:
            self._refresh_queue.put([])
            return

        def worker() -> None:
            try:
                result = subprocess.run(  # nosec B603
                    [devpi_exe, "index", "-l"],
                    capture_output=True,
                    timeout=15,
                    **utf8_subprocess_kwargs(strip_venv=True),
                    check=False,
                    shell=False,
                )
                rows: list[dict[str, str]] = []
                for line in (result.stdout or "").strip().splitlines():
                    line = line.strip()
                    if not line or line.startswith("current"):
                        continue
                    # Each line is typically "user/indexname" possibly with extra info
                    parts = line.split()
                    index_name = parts[0] if parts else line
                    rows.append(
                        {
                            "index": index_name,
                            "type": "",
                            "bases": "",
                            "volatile": "",
                        }
                    )
                self._refresh_queue.put(rows)
            except (OSError, subprocess.SubprocessError, ValueError):
                self._refresh_queue.put([])

        threading.Thread(target=worker, daemon=True, name="devpi-index-refresh").start()

    # ---- internal -----------------------------------------------------------

    def _refresh_status(self) -> None:
        """Run devpi use in a background thread to get the current server URL."""
        devpi_exe = resolve_executable("devpi")
        if devpi_exe is None:
            self._status_queue.put("(devpi not found)")
            return

        def worker() -> None:
            try:
                result = subprocess.run(  # nosec B603
                    [devpi_exe, "use"],
                    capture_output=True,
                    timeout=10,
                    **utf8_subprocess_kwargs(strip_venv=True),
                    check=False,
                    shell=False,
                )
                output = (result.stdout or "").strip()
                # First line typically shows the current URL
                first_line = output.splitlines()[0] if output else "(no server configured)"
                self._status_queue.put(first_line)
            except (OSError, subprocess.SubprocessError, ValueError, IndexError):
                self._status_queue.put("(error reading status)")

        threading.Thread(target=worker, daemon=True, name="devpi-status-refresh").start()

    def _poll(self) -> None:
        try:
            rows = self._refresh_queue.get_nowait()
            self._populate_tree(rows)
        except queue.Empty:
            pass
        try:
            status = self._status_queue.get_nowait()
            self._status_var.set(status)
        except queue.Empty:
            pass
        self.after(200, self._poll)

    def _populate_tree(self, rows: list[dict[str, str]]) -> None:
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            self._tree.insert(
                "",
                tk.END,
                iid=row["index"],
                values=(row["index"], row["type"], row["bases"], row["volatile"]),
            )

    def _current_index(self) -> str | None:
        sel = self._tree.selection()
        return sel[0] if sel else None

    def _on_index_select(self, _event: Any) -> None:
        index_name = self._current_index()
        if index_name:
            self._prefill_index_name(index_name)

    def _prefill_index_name(self, index_name: str) -> None:
        for fw in self.command_form.field_widgets:
            if fw.arg.name == "index_name":
                with contextlib.suppress(Exception):
                    fw.var.set(index_name)  # type: ignore[arg-type]
                self.command_form.update_preview()
                break

    def _on_right_click(self, event: Any) -> None:
        row_id = self._tree.identify_row(event.y)
        if row_id:
            self._tree.selection_set(row_id)
        self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_use(self) -> None:
        index_name = self._current_index()
        if index_name:
            self._prefill_index_name(index_name)

    def _ctx_delete(self) -> None:
        index_name = self._current_index()
        if index_name:
            self._prefill_index_name(index_name)
