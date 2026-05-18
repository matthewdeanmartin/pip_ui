"""HatchEnvPanel — live env table + CommandForm for hatch."""

# pylint: disable=consider-using-with

from __future__ import annotations

import contextlib
import json
import queue
import subprocess  # nosec B404
import sys
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, ClassVar

from pip_ui.encoding import utf8_subprocess_kwargs
from pip_ui.process_utils import resolve_executable, resolve_windows_shell
from pip_ui.ui.command_form import CommandForm


class HatchEnvPanel(ttk.Frame):
    """Top: live hatch env table. Bottom: CommandForm."""

    COLUMNS = ("name", "type", "python", "path")
    COL_LABELS: ClassVar[dict[str, str]] = {"name": "Name", "type": "Type", "python": "Python", "path": "Path"}

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
        self._workdir: str = "."
        self._refresh_queue: queue.Queue[list[dict[str, str]]] = queue.Queue()

        self._build_env_table()

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

    # ---- env table ----------------------------------------------------------

    def _build_env_table(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Environments", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(header, text="Refresh", command=self.refresh_envs).pack(side=tk.RIGHT, padx=4, pady=2)

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

        self._tree.bind("<<TreeviewSelect>>", self._on_env_select)
        self._tree.bind("<Button-3>", self._on_right_click)

        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="Create Env", command=self._ctx_create)
        self._ctx_menu.add_command(label="Remove Env", command=self._ctx_remove)
        self._ctx_menu.add_command(label="Shell", command=self._ctx_shell)

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

    def set_workdir(self, path: str) -> None:
        self._workdir = path

    def notify_run_done(self, exit_code: int, spec_name: str, _argv: list[str]) -> None:
        """Auto-refresh env table after mutating commands."""
        if spec_name in ("hatch_env_create", "hatch_env_remove", "hatch_env_prune") and exit_code == 0:
            self.refresh_envs()

    def refresh_envs(self) -> None:
        """Run hatch env show --json in a background thread."""
        hatch_exe = resolve_executable("hatch")
        if hatch_exe is None:
            self._refresh_queue.put([])
            return

        def worker() -> None:
            try:
                result = subprocess.run(  # nosec B603
                    [hatch_exe, "env", "show", "--json"],
                    capture_output=True,
                    cwd=self._workdir,
                    timeout=15,
                    **utf8_subprocess_kwargs(strip_venv=True),
                    check=False,
                    shell=False,
                )
                data = json.loads(result.stdout or "{}")
                rows: list[dict[str, str]] = []
                for env_name, info in data.items():
                    rows.append(
                        {
                            "name": env_name,
                            "type": info.get("type", ""),
                            "python": info.get("python", ""),
                            "path": info.get("path", ""),
                        }
                    )
                self._refresh_queue.put(rows)
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
                self._refresh_queue.put([])

        threading.Thread(target=worker, daemon=True, name="hatch-env-refresh").start()

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
                iid=row["name"],
                values=(row["name"], row["type"], row["python"], row["path"]),
            )

    def _on_env_select(self, _event: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        env_name = sel[0]
        self._prefill_env_name(env_name)

    def _prefill_env_name(self, env_name: str) -> None:
        for fw in self.command_form.field_widgets:
            if fw.arg.name == "env_name":
                with contextlib.suppress(Exception):
                    fw.var.set(env_name)  # type: ignore[arg-type]
                self.command_form.update_preview()
                break

    def _on_right_click(self, event: Any) -> None:
        row_id = self._tree.identify_row(event.y)
        if row_id:
            self._tree.selection_set(row_id)
        self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_create(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        self._prefill_env_name(sel[0])

    def _ctx_remove(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        self._prefill_env_name(sel[0])

    def _ctx_shell(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        env_name = sel[0]
        hatch_exe = resolve_executable("hatch")
        if hatch_exe:
            try:
                if sys.platform == "win32":
                    shell_exe = resolve_windows_shell()
                    if shell_exe is None:
                        return
                    subprocess.Popen(  # nosec B603
                        [shell_exe, "/K", hatch_exe, "shell", env_name],
                        cwd=self._workdir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        shell=False,
                    )  # nosec B607
                else:
                    for term in ("x-terminal-emulator", "gnome-terminal", "xterm"):
                        terminal_exe = resolve_executable(term)
                        if terminal_exe:
                            subprocess.Popen(  # nosec B603
                                (
                                    [terminal_exe, "--", hatch_exe, "shell", env_name]
                                    if term == "gnome-terminal"
                                    else [terminal_exe, "-e", hatch_exe, "shell", env_name]
                                ),
                                cwd=self._workdir,
                                shell=False,
                            )
                            break
            except OSError:
                pass
