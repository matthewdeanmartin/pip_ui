"""VirtualenvPanel — CommandForm wrapper with 'Activate in new terminal' button."""

# pylint: disable=consider-using-with

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any

from pip_ui.process_utils import resolve_executable, resolve_windows_shell
from pip_ui.ui.command_form import CommandForm


class VirtualenvPanel(ttk.Frame):
    """Middle panel for virtualenv. Embeds a CommandForm and adds an activate button."""

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
        self._last_venv_path: str | None = None
        self._last_exit_code: int | None = None

        self.command_form = CommandForm(
            self,
            on_run=self._on_run,
            on_form_change=on_form_change,
            global_values_provider=global_values_provider,
            on_open_global_options=on_open_global_options,
            global_requirements_provider=global_requirements_provider,
        )
        self.command_form.pack(fill=tk.BOTH, expand=True)

        self._outer_on_run = on_run

        self._activate_frame = ttk.Frame(self)
        self._activate_frame.pack(fill=tk.X, padx=4, pady=(2, 4))

        self._activate_btn = ttk.Button(
            self._activate_frame,
            text="Activate in new terminal",
            command=self._activate,
            state=tk.DISABLED,
        )
        self._activate_btn.pack(side=tk.LEFT, padx=4)
        self._activate_hint = ttk.Label(
            self._activate_frame,
            text="(available after a successful 'Create Env' run)",
            foreground="#666",
        )
        self._activate_hint.pack(side=tk.LEFT, padx=4)

    # ---- CommandForm delegation (MainWindow calls these) --------------------

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

    # ---- internal -----------------------------------------------------------

    def _on_run(self, pip_args: list[str], label: str) -> None:
        # Intercept run to capture the dest path for the activate button.
        self._outer_on_run(pip_args, label)

    def notify_run_done(self, exit_code: int, spec_name: str, argv: list[str]) -> None:
        """Called by MainWindow after a run completes."""
        self._last_exit_code = exit_code
        if spec_name == "create" and exit_code == 0:
            dest = self._extract_dest(argv)
            if dest:
                self._last_venv_path = dest
                self._activate_btn.config(state=tk.NORMAL)
                self._activate_hint.config(text=f"Activate: {dest}")
                return
        if exit_code != 0:
            self._activate_btn.config(state=tk.DISABLED)

    def _extract_dest(self, argv: list[str]) -> str | None:
        """Extract the positional dest argument from a virtualenv create argv."""
        skip_flags = {
            "--python",
            "--prompt",
            "--creator",
            "--seeder",
        }
        i = 0
        while i < len(argv):
            token = argv[i]
            if token.startswith("-"):
                if token in skip_flags:
                    i += 2
                else:
                    i += 1
            else:
                return token
        return None

    def _activate(self) -> None:
        path = self._last_venv_path
        if not path:
            return
        abs_path = os.path.abspath(path)
        try:
            if sys.platform == "win32":
                shell_exe = resolve_windows_shell()
                if shell_exe is None:
                    return
                activate = os.path.join(abs_path, "Scripts", "activate.bat")
                subprocess.Popen(  # nosec B603
                    [shell_exe, "/K", activate],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    shell=False,
                )  # nosec B607
            else:
                activate = os.path.join(abs_path, "bin", "activate")
                bash_exe = resolve_executable("bash")
                if bash_exe is None:
                    return
                for terminal in ("x-terminal-emulator", "gnome-terminal", "xterm"):
                    terminal_exe = resolve_executable(terminal)
                    if terminal_exe:
                        if terminal == "gnome-terminal":
                            subprocess.Popen(  # nosec B603
                                [terminal_exe, "--", bash_exe, "--init-file", activate],
                                shell=False,
                            )
                        else:
                            subprocess.Popen(  # nosec B603
                                [terminal_exe, "-e", bash_exe, "--init-file", activate],
                                shell=False,
                            )
                        return
                # Last resort
                subprocess.Popen([bash_exe, "--init-file", activate], shell=False)  # nosec B603
        except OSError:
            pass
