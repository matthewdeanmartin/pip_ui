"""Main application window."""

from __future__ import annotations

import os
import queue
import sys
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any, Optional

from pip_ui.__about__ import __version__
from pip_ui.command_specs import COMMAND_SPECS
from pip_ui.history import CommandHistory
from pip_ui.models import HistoryEntry, InterpreterInfo, RunResult
from pip_ui.runner import PipRunner
from pip_ui.safety import check_global_install, classify_command, needs_confirmation
from pip_ui.settings import AppSettings
from pip_ui.ui.command_form import CommandForm
from pip_ui.ui.command_tree import CommandTree
from pip_ui.ui.dialogs import confirm_dialog, error_dialog, info_dialog
from pip_ui.ui.help_panel import HelpPanel
from pip_ui.ui.interpreter_picker import InterpreterPicker
from pip_ui.ui.output_panel import OutputPanel


class MainWindow(tk.Tk):
    def __init__(self, no_history: bool = False, safe_mode: bool = False) -> None:
        super().__init__()
        self.no_history = no_history
        self.safe_mode = safe_mode
        self.settings = AppSettings()
        self.settings.load()
        self.history = CommandHistory() if not no_history else None
        self.runner = PipRunner()
        self.output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.done_queue: queue.Queue[int] = queue.Queue()
        self.current_interpreter: Optional[InterpreterInfo] = None
        self.run_start_time: Optional[datetime] = None

        self.title("pip-ui - Python Package Installer GUI")
        width = self.settings.get("window_width", 1100)
        height = self.settings.get("window_height", 700)
        self.geometry(f"{width}x{height}")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_menu()
        self.build_toolbar()
        self.build_main_panels()
        self.build_status_bar()
        self.bind_shortcuts()
        self.after(50, self.poll_queues)

    def build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Quit", accelerator="Ctrl+Q", command=self.on_close)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self.copy_selection)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Config Dashboard", command=self.show_config_view)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def build_toolbar(self) -> None:
        toolbar = ttk.Frame(self, relief=tk.GROOVE, borderwidth=1)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)

        self.interpreter_picker = InterpreterPicker(toolbar, on_change=self.on_interpreter_change)
        self.interpreter_picker.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        ttk.Label(toolbar, text="Dir:").pack(side=tk.LEFT, padx=(8, 2))
        self.workdir_var = tk.StringVar(value=self.settings.get("last_working_dir") or os.getcwd())
        workdir_entry = ttk.Entry(toolbar, textvariable=self.workdir_var, width=30)
        workdir_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Browse...", command=self.browse_workdir).pack(side=tk.LEFT, padx=2)

    def build_main_panels(self) -> None:
        self.horizontal_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.horizontal_paned.pack(fill=tk.BOTH, expand=True)

        self.command_tree = CommandTree(self.horizontal_paned, on_select=self.on_command_select)
        self.horizontal_paned.add(self.command_tree, weight=0)

        middle_paned = ttk.PanedWindow(self.horizontal_paned, orient=tk.VERTICAL)
        self.horizontal_paned.add(middle_paned, weight=2)

        self.command_form = CommandForm(middle_paned, on_run=self.run_command)
        middle_paned.add(self.command_form, weight=1)

        self.output_panel = OutputPanel(middle_paned)
        middle_paned.add(self.output_panel, weight=1)

        self.help_panel = HelpPanel(self.horizontal_paned)
        self.horizontal_paned.add(self.help_panel, weight=0)

        self.after(100, lambda: self.horizontal_paned.sashpos(0, 200))
        self.after(100, lambda: self.horizontal_paned.sashpos(1, self.winfo_width() - 250))

    def build_status_bar(self) -> None:
        status_bar = ttk.Frame(self, relief=tk.SUNKEN, borderwidth=1)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_interpreter_var = tk.StringVar(value="No interpreter selected")
        self.status_workdir_var = tk.StringVar(value=os.getcwd())
        ttk.Label(status_bar, textvariable=self.status_interpreter_var).pack(side=tk.LEFT, padx=8)
        ttk.Separator(status_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Label(status_bar, textvariable=self.status_workdir_var).pack(side=tk.LEFT, padx=8)

    def bind_shortcuts(self) -> None:
        self.bind("<Control-r>", lambda e: self.command_form.do_run())
        self.bind("<Control-l>", lambda e: self.command_tree.focus_search())
        self.bind("<Control-q>", lambda e: self.on_close())

    def on_interpreter_change(self, info: Optional[InterpreterInfo]) -> None:
        self.current_interpreter = info
        if info:
            self.status_interpreter_var.set(f"{info.path} ({info.version}, pip {info.pip_version})")
            self.settings.set("last_interpreter", info.path)

    def browse_workdir(self) -> None:
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select Working Directory")
        if path:
            self.workdir_var.set(path)
            self.status_workdir_var.set(path)
            self.settings.set("last_working_dir", path)

    def on_command_select(self, command_name: str) -> None:
        spec = COMMAND_SPECS.get(command_name)
        if spec is None:
            return
        self.command_form.set_command(spec)
        self.help_panel.update_for_command(spec, [], self.current_interpreter)

    def run_command(self, pip_args: list[str], label: str) -> None:
        if self.current_interpreter is None:
            error_dialog(self, "No Interpreter", "Please select a Python interpreter first.")
            return

        command_name = pip_args[0] if pip_args else ""
        safety_level = classify_command(command_name)

        if self.safe_mode and needs_confirmation(safety_level):
            confirmed = confirm_dialog(
                self,
                "Safe Mode - Confirm Action",
                f"Safe mode is active. This command ({label}) may modify your environment.\n\nProceed?",
            )
            if not confirmed:
                return
        elif needs_confirmation(safety_level):
            from pip_ui.safety import confirmation_message
            confirmed = confirm_dialog(self, "Confirm Action", confirmation_message(command_name))
            if not confirmed:
                return

        if command_name == "install" and self.current_interpreter is not None:
            warning = check_global_install(self.current_interpreter)
            if warning:
                confirmed = confirm_dialog(self, "Global Install Warning", warning + "\n\nContinue?")
                if not confirmed:
                    return

        full_argv = self.runner.build_argv(self.current_interpreter.path, pip_args)
        cwd = self.workdir_var.get() or os.getcwd()

        self.output_panel.clear()
        self.output_panel.set_command_info({
            "Command": label,
            "Interpreter": self.current_interpreter.path,
            "Working Directory": cwd,
            "Arguments": str(pip_args),
        })

        self.run_start_time = datetime.now()

        redacted_argv = PipRunner.redact_argv(full_argv)

        def enqueue_stdout(line: str) -> None:
            self.output_queue.put(("stdout", line))

        def enqueue_stderr(line: str) -> None:
            self.output_queue.put(("stderr", line))

        def on_done(exit_code: int) -> None:
            self.done_queue.put(exit_code)

        self.runner.run(full_argv, cwd, enqueue_stdout, enqueue_stderr, on_done)

        self.run_pip_args = pip_args
        self.run_label = label
        self.run_redacted_argv = redacted_argv

    def poll_queues(self) -> None:
        try:
            while True:
                kind, line = self.output_queue.get_nowait()
                if kind == "stdout":
                    self.output_panel.append_stdout(line)
                else:
                    self.output_panel.append_stderr(line)
        except queue.Empty:
            pass

        try:
            exit_code = self.done_queue.get_nowait()
            self.on_run_done(exit_code)
        except queue.Empty:
            pass

        self.after(50, self.poll_queues)

    def on_run_done(self, exit_code: int) -> None:
        end_time = datetime.now()
        start_time = self.run_start_time or end_time
        duration = (end_time - start_time).total_seconds()

        if exit_code == 0:
            self.output_panel.append_stdout(f"\n[Completed successfully in {duration:.2f}s]\n")
        else:
            self.output_panel.append_stderr(f"\n[Exited with code {exit_code} in {duration:.2f}s]\n")

        if self.history is not None and self.current_interpreter is not None:
            redacted = getattr(self, "run_redacted_argv", [])
            label = getattr(self, "run_label", "")
            from pip_ui.runner import PipRunner
            runner = PipRunner()
            entry = HistoryEntry(
                timestamp=start_time,
                command_label=label,
                argv_redacted=redacted,
                command_redacted=runner.format_command(redacted),
                exit_code=exit_code,
                duration=duration,
                interpreter_path=self.current_interpreter.path,
                working_directory=self.workdir_var.get() or os.getcwd(),
            )
            self.history.add(entry)

    def show_config_view(self) -> None:
        from pip_ui.ui.config_view import ConfigView
        ConfigView(self, interpreter_info=self.current_interpreter)

    def show_about(self) -> None:
        info_dialog(
            self,
            "About pip-ui",
            f"pip-ui v{__version__}\n\nA Tkinter GUI for pip.\nRuns: python -m pip\n\nNo pip internals are used.",
        )

    def copy_selection(self) -> None:
        try:
            focused = self.focus_get()
            if focused and hasattr(focused, "selection_get"):
                text = focused.selection_get()
                self.clipboard_clear()
                self.clipboard_append(text)
        except Exception:
            pass

    def on_close(self) -> None:
        self.settings.set("window_width", self.winfo_width())
        self.settings.set("window_height", self.winfo_height())
        self.destroy()
