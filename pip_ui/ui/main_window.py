"""Main application window."""

from __future__ import annotations

import os
import queue
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk
from typing import Any

from pip_ui.__about__ import __version__
from pip_ui.command_specs import COMMAND_SPECS
from pip_ui.history import CommandHistory
from pip_ui.models import HistoryEntry, InterpreterInfo
from pip_ui.runner import PipRunner
from pip_ui.safety import (
    check_global_install,
    classify_command,
    collect_argv_warnings,
    confirmation_message,
    explain_pip_error,
    needs_confirmation,
)
from pip_ui.self_update import UpgradeInfo, check_latest_version
from pip_ui.settings import AppSettings
from pip_ui.ui.command_form import CommandForm, default_global_values
from pip_ui.ui.command_tree import CommandTree
from pip_ui.ui.config_view import ConfigView
from pip_ui.ui.dialogs import confirm_dialog, error_dialog, info_dialog
from pip_ui.ui.global_options_dialog import GlobalOptionsDialog
from pip_ui.ui.help_panel import HelpPanel
from pip_ui.ui.interpreter_picker import InterpreterPicker
from pip_ui.ui.output_panel import OutputPanel
from pip_ui.ui.requirements_picker import RequirementsPicker


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
        self.upgrade_queue: queue.Queue[UpgradeInfo | None] = queue.Queue()
        self.current_interpreter: InterpreterInfo | None = None
        self.command_form: CommandForm | None = None
        self.help_panel: HelpPanel | None = None
        self.run_start_time: datetime | None = None
        self.last_run_argv: list[str] = []
        self.last_run_exit: int | None = None
        self.run_pip_args: list[str] = []
        self.run_label = ""
        self.run_redacted_argv: list[str] = []
        self.run_full_argv: list[str] = []
        self.stderr_buffer: list[str] = []
        self.manual_update_check_pending = False
        self.pending_self_upgrade = False

        # Per-command output cache: key = (interpreter_path, command_name).
        # Each value is the OutputPanel.snapshot() dict captured when that
        # command last finished running. Selecting a command in the tree
        # restores its snapshot so the user sees stale-but-real output
        # instead of a blank panel.
        self.output_cache: dict[tuple[str, str], dict[str, str]] = {}
        self.current_run_command: str | None = None
        # Commands we'll auto-run on first selection because they're read-only
        # and need no required args. Anything else stays blank until Run.
        self.autorun_on_select: set[str] = {
            "list",
            "freeze",
            "check",
            "inspect",
            "config_list",
            "config_debug",
            "cache_dir",
            "cache_info",
            "cache_list",
            "debug",
            "version",
        }

        # Globals are now stored centrally, not on each per-command form.
        stored_globals = self.settings.get("global_options", None) or default_global_values()
        merged_globals = default_global_values()
        merged_globals.update(stored_globals)
        self.global_options: dict[str, Any] = merged_globals

        self.global_requirements_file: str | None = None

        self.show_secrets = tk.BooleanVar(value=bool(self.settings.get("show_secrets", False)))
        self.status_interpreter_var = tk.StringVar(value="No interpreter selected")
        self.status_workdir_var = tk.StringVar(value=self.settings.get("last_working_dir") or os.getcwd())
        self.upgrade_banner_var = tk.StringVar(value="")

        self.title(f"pip-ui v{__version__} - Python Package Installer GUI")
        width = self.settings.get("window_width", 1100)
        height = self.settings.get("window_height", 700)
        self.geometry(f"{width}x{height}")
        self.maximize_on_startup()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_menu()
        self.build_toolbar()
        self.build_upgrade_banner()
        self.build_main_panels()
        self.build_status_bar()
        self.bind_shortcuts()

        # Push the initial working directory into the requirements picker.
        self.requirements_picker.set_directory(self.workdir_var.get() or os.getcwd())

        self.after(50, self.poll_queues)
        # Kick off the PyPI version check; the result lands on upgrade_queue.
        check_latest_version(__version__, self.upgrade_queue.put)

    # ------------------------------------------------------------------ menu

    def build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Quit", accelerator="Ctrl+Q", command=self.on_close)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self.copy_selection)
        edit_menu.add_command(label="Copy Command", accelerator="Ctrl+Shift+C", command=self.copy_command)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Config Dashboard", command=self.show_config_view)
        view_menu.add_command(label="Refresh Current Command", command=self.force_refresh_current)
        view_menu.add_checkbutton(
            label="Show Sensitive Values",
            variable=self.show_secrets,
            command=self.on_show_secrets_toggle,
        )

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Global Options...", command=self.open_global_options_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Check for Updates", command=self.manual_check_updates)
        tools_menu.add_command(label="Upgrade pip-ui", command=self.self_upgrade)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    # --------------------------------------------------------------- toolbar

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

        # Second row: requirements picker + Global Options button.
        toolbar2 = ttk.Frame(self, relief=tk.GROOVE, borderwidth=1)
        toolbar2.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(0, 2))

        self.requirements_picker = RequirementsPicker(
            toolbar2, on_change=self.on_requirements_change
        )
        self.requirements_picker.pack(side=tk.LEFT, padx=4)

        ttk.Button(
            toolbar2,
            text="Global Options...",
            command=self.open_global_options_dialog,
        ).pack(side=tk.LEFT, padx=4)

        self.global_options_summary_var = tk.StringVar(value="(globals: defaults)")
        ttk.Label(toolbar2, textvariable=self.global_options_summary_var, foreground="#444").pack(
            side=tk.LEFT, padx=4
        )

    def build_upgrade_banner(self) -> None:
        # Coloured strip; only visible when text is set.
        self.upgrade_banner = tk.Label(
            self,
            textvariable=self.upgrade_banner_var,
            background="#fff7c2",
            foreground="#5b4500",
            anchor=tk.W,
            padx=8,
            pady=4,
        )
        # Hidden by default; we pack it dynamically when there's something to show.

    def show_upgrade_banner(self, info: UpgradeInfo) -> None:
        self.upgrade_banner_var.set(
            f"⚡ pip-ui {info.latest} is available (you have {info.current}). "
            "Use Tools → Upgrade pip-ui to install."
        )
        self.upgrade_banner.pack(side=tk.TOP, fill=tk.X)

    # ----------------------------------------------------------- main panels

    def build_main_panels(self) -> None:
        self.horizontal_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.horizontal_paned.pack(fill=tk.BOTH, expand=True)

        self.command_tree = CommandTree(self.horizontal_paned, on_select=self.on_command_select)
        self.horizontal_paned.add(self.command_tree, weight=0)

        middle_paned = ttk.PanedWindow(self.horizontal_paned, orient=tk.VERTICAL)
        self.horizontal_paned.add(middle_paned, weight=2)

        self.command_form = CommandForm(
            middle_paned,
            on_run=self.run_command,
            on_form_change=self.on_form_change,
            global_values_provider=lambda: dict(self.global_options),
            on_open_global_options=self.open_global_options_dialog,
            global_requirements_provider=lambda: self.global_requirements_file,
        )
        middle_paned.add(self.command_form, weight=1)

        self.output_panel = OutputPanel(middle_paned, on_cancel=self.on_cancel_running)
        middle_paned.add(self.output_panel, weight=1)

        self.help_panel = HelpPanel(self.horizontal_paned)
        self.horizontal_paned.add(self.help_panel, weight=0)

        # Position sashes after the window has been laid out (and maximized),
        # so winfo_width() reflects the real screen-sized geometry rather than
        # the requested 1100px.
        self.after(150, self.apply_initial_sash_positions)

        self.refresh_global_options_summary()

    def maximize_on_startup(self) -> None:
        """Maximize the window on launch, with cross-platform fallbacks."""
        try:
            # Windows + most Linux WMs accept 'zoomed' on the root window state.
            self.state("zoomed")
            return
        except tk.TclError:
            pass
        try:
            # Generic Tk fallback (e.g. macOS).
            self.attributes("-zoomed", True)  # type: ignore[no-untyped-call]
            return
        except tk.TclError:
            pass
        # Last resort: size to the screen.
        try:
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        except tk.TclError:
            pass

    def apply_initial_sash_positions(self) -> None:
        self.update_idletasks()
        total = self.winfo_width()
        if total <= 1:
            # Window hasn't been mapped yet; retry shortly.
            self.after(100, self.apply_initial_sash_positions)
            return
        # Left tree pane: fixed 200px. Right help panel: 30% of total width.
        self.set_sash_position(0, 200)
        self.set_sash_position(1, int(total * 0.70))

    def build_status_bar(self) -> None:
        status_bar = ttk.Frame(self, relief=tk.SUNKEN, borderwidth=1)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status_bar, textvariable=self.status_interpreter_var).pack(side=tk.LEFT, padx=8)
        ttk.Separator(status_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Label(status_bar, textvariable=self.status_workdir_var).pack(side=tk.LEFT, padx=8)

    def bind_shortcuts(self) -> None:
        self.bind("<Control-r>", lambda e: self.command_form.do_run())
        self.bind("<Control-l>", lambda e: self.command_tree.focus_search())
        self.bind("<Control-q>", lambda e: self.on_close())
        self.bind("<Control-Shift-C>", lambda e: self.copy_command())

    # ------------------------------------------------------------ callbacks

    def on_show_secrets_toggle(self) -> None:
        self.settings.set("show_secrets", bool(self.show_secrets.get()))

    def on_interpreter_change(self, info: InterpreterInfo | None) -> None:
        prior = self.current_interpreter
        self.current_interpreter = info
        if info:
            self.status_interpreter_var.set(f"{info.path} ({info.version}, pip {info.pip_version})")
            self.settings.set("last_interpreter", info.path)
            if self.command_form is not None and self.help_panel is not None and self.command_form.spec is not None:
                self.help_panel.update_for_command(self.command_form.spec, self.command_form.get_argv(), info)
            # Switching interpreters invalidates everything we cached against
            # the old one. We *don't* eagerly re-run all info commands here —
            # that was the source of the "output panel keeps getting trampled"
            # problem. Instead we lazily run a command when the user clicks
            # it in the tree.
            if prior is not None and prior.path != info.path:
                self.output_cache.clear()
            # If a command is already selected, refresh it.
            if getattr(self, "command_form", None) is not None and self.command_form.spec is not None:
                self.after(0, lambda: self.refresh_current_command_output())

    def on_requirements_change(self, path: str | None) -> None:
        self.global_requirements_file = path
        if self.command_form is not None and path:
            self.command_form.apply_global_requirements(path)
        if self.command_form is not None:
            self.command_form.update_preview()

    def set_sash_position(self, index: int, position: int) -> None:
        self.horizontal_paned.sashpos(index, position)  # type: ignore[no-untyped-call]

    def browse_workdir(self) -> None:
        path = filedialog.askdirectory(title="Select Working Directory")
        if path:
            self.workdir_var.set(path)
            self.status_workdir_var.set(path)
            self.settings.set("last_working_dir", path)
            self.requirements_picker.set_directory(path)

    def on_command_select(self, command_name: str) -> None:
        spec = COMMAND_SPECS.get(command_name)
        if spec is None:
            return
        self.stderr_buffer = []
        self.command_form.set_command(spec)
        self.help_panel.update_for_command(spec, self.command_form.get_argv(), self.current_interpreter)
        self.show_output_for_command(command_name)

    def show_output_for_command(self, command_name: str) -> None:
        """Restore cached output for this command, or trigger a one-time auto-run."""
        if self.runner.is_running():
            # Don't disturb an in-flight command's output.
            return
        cache_key = self.cache_key_for(command_name)
        if cache_key is not None and cache_key in self.output_cache:
            self.output_panel.restore(self.output_cache[cache_key])
            return
        # No cache yet. For read-only commands that need nothing, run with defaults.
        if (
            cache_key is not None
            and command_name in self.autorun_on_select
            and self.current_interpreter is not None
        ):
            self.output_panel.clear()
            self.output_panel.append_combined(
                f"[auto] Running pip {command_name.replace('_', ' ')} with defaults...\n",
                tag="hint",
            )
            self.command_form.do_run()
            return
        # Nothing to show; leave the panel empty so the user can fill the form.
        self.output_panel.clear()

    def refresh_current_command_output(self) -> None:
        if self.command_form is None or self.command_form.spec is None:
            return
        self.show_output_for_command(self.command_form.spec.name)

    def cache_key_for(self, command_name: str) -> tuple[str, str] | None:
        if self.current_interpreter is None:
            return None
        return (self.current_interpreter.path, command_name)

    def on_form_change(self) -> None:
        if self.command_form.spec is None:
            return
        self.help_panel.update_for_command(
            self.command_form.spec, self.command_form.get_argv(), self.current_interpreter
        )

    # ------------------------------------------------------- global options

    def open_global_options_dialog(self) -> None:
        GlobalOptionsDialog(
            self,
            values=dict(self.global_options),
            on_apply=self.apply_global_options,
        )

    def apply_global_options(self, values: dict[str, Any]) -> None:
        self.global_options = values
        self.settings.set("global_options", values)
        self.refresh_global_options_summary()
        if self.command_form is not None:
            self.command_form.refresh_globals_summary()
            self.command_form.update_preview()

    def refresh_global_options_summary(self) -> None:
        from pip_ui.ui.global_options_dialog import summarize_globals

        chips = summarize_globals(self.global_options)
        if not chips:
            self.global_options_summary_var.set("(globals: defaults)")
        else:
            shown = chips if len(chips) <= 3 else chips[:3] + [f"+{len(chips) - 3} more"]
            self.global_options_summary_var.set("globals: " + ", ".join(shown))

    # -------------------------------------------------------------- runners

    def run_command(self, pip_args: list[str], label: str) -> None:
        if self.current_interpreter is None:
            error_dialog(self, "No Interpreter", "Please select a Python interpreter first.")
            return
        if self.runner.is_running():
            error_dialog(self, "Already Running", "A pip command is already in progress. Cancel it first.")
            return

        command_name = self.command_form.spec.name if self.command_form.spec else ""
        self.current_run_command = command_name
        safety_level = classify_command(command_name)

        warnings = collect_argv_warnings(pip_args)
        for w in warnings:
            self.output_panel.append_combined(f"[warning] {w}\n", tag="warning")

        if self.safe_mode and needs_confirmation(safety_level):
            confirmed = confirm_dialog(
                self,
                "Safe Mode - Confirm Action",
                f"Safe mode is active. This command ({label}) may modify your environment.\n\nProceed?",
            )
            if not confirmed:
                return
        elif needs_confirmation(safety_level):
            confirmed = confirm_dialog(self, "Confirm Action", confirmation_message(command_name))
            if not confirmed:
                return

        if command_name in {"install", "download", "wheel"} and self.current_interpreter is not None:
            warning = check_global_install(self.current_interpreter)
            if warning:
                confirmed = confirm_dialog(self, "Global Install Warning", warning + "\n\nContinue?")
                if not confirmed:
                    return

        cwd = self.workdir_var.get() or os.getcwd()
        env = self.runtime_env_for(command_name)
        full_argv = self.runner.build_argv(self.current_interpreter.path, pip_args)

        self.output_panel.clear()
        self.stderr_buffer = []
        self.last_run_argv = list(pip_args)

        redacted_argv = PipRunner.redact_argv(full_argv)
        display_argv = full_argv if self.show_secrets.get() else redacted_argv

        self.output_panel.set_command_info(
            {
                "Command": label,
                "Interpreter": self.current_interpreter.path,
                "Python Version": self.current_interpreter.version,
                "Pip Version": self.current_interpreter.pip_version,
                "Working Directory": cwd,
                "Argv": str(display_argv),
                "Started": datetime.now().isoformat(timespec="seconds"),
            }
        )

        self.run_start_time = datetime.now()

        def enqueue_stdout(line: str) -> None:
            self.output_queue.put(("stdout", line))

        def enqueue_stderr(line: str) -> None:
            self.output_queue.put(("stderr", line))

        def on_done(exit_code: int) -> None:
            self.done_queue.put(exit_code)

        self.output_panel.set_running(True)
        self.runner.run(full_argv, cwd, enqueue_stdout, enqueue_stderr, on_done, env=env)

        self.run_pip_args = pip_args
        self.run_label = label
        self.run_redacted_argv = redacted_argv
        self.run_full_argv = full_argv

    def runtime_env_for(self, command_name: str) -> dict[str, str] | None:
        """Build a process env override for the upcoming pip run.

        Currently used to default ``EDITOR`` to notepad.exe on Windows when
        ``config edit`` is invoked without a configured editor.
        """
        if command_name != "config_edit":
            return None
        if sys.platform != "win32":
            return None
        if any(os.environ.get(key) for key in ("VISUAL", "EDITOR", "GIT_EDITOR")):
            return None
        env = dict(os.environ)
        env["EDITOR"] = "notepad.exe"
        return env

    def on_cancel_running(self, force: bool) -> None:
        if not self.runner.is_running():
            return
        if force:
            confirmed = confirm_dialog(
                self,
                "Force Kill",
                "Graceful cancel did not stop the process. Force kill? This may leave files in a partial state.",
            )
            if not confirmed:
                return
            self.runner.cancel(force=True)
            self.output_panel.append_combined("\n[Force killed by user]\n", tag="warning")
        else:
            self.runner.cancel(force=False)
            self.output_panel.append_combined("\n[Cancel requested by user]\n", tag="warning")

    # ------------------------------------------------------------ refresh

    def force_refresh_current(self) -> None:
        """Drop the cached output for the current command and re-run it if eligible."""
        if self.command_form is None or self.command_form.spec is None:
            return
        key = self.cache_key_for(self.command_form.spec.name)
        if key is not None:
            self.output_cache.pop(key, None)
        self.show_output_for_command(self.command_form.spec.name)

    # ----------------------------------------------------------- self-upgrade

    def manual_check_updates(self) -> None:
        self.manual_update_check_pending = True
        self.status_interpreter_var.set("Checking PyPI for pip-ui updates...")
        check_latest_version(__version__, self.upgrade_queue.put)

    def self_upgrade(self) -> None:
        if self.current_interpreter is None:
            error_dialog(self, "No Interpreter", "Select a Python interpreter first.")
            return
        if self.runner.is_running():
            error_dialog(self, "Busy", "Cancel the running command first.")
            return
        confirmed = confirm_dialog(
            self,
            "Upgrade pip-ui",
            "This will run `pip install --upgrade pip_ui` using the selected interpreter.\n\n"
            "If pip-ui is installed in the *same* interpreter as the GUI you are running, "
            "you'll need to restart the application after the upgrade. Continue?",
        )
        if not confirmed:
            return
        self.pending_self_upgrade = True
        self.run_command(["install", "--upgrade", "pip_ui"], "Upgrade pip-ui")

    def handle_upgrade_result(self, info: UpgradeInfo | None) -> None:
        # Network failure path: always tell the user when they manually asked.
        if info is None:
            if getattr(self, "manual_update_check_pending", False):
                self.manual_update_check_pending = False
                self.restore_interpreter_status()
                error_dialog(
                    self,
                    "Update Check Failed",
                    "Could not reach PyPI to check for a newer version of pip-ui. "
                    "Check your network connection and try again.",
                )
            return

        if info.available:
            self.show_upgrade_banner(info)
            if getattr(self, "manual_update_check_pending", False):
                self.manual_update_check_pending = False
                self.restore_interpreter_status()
                if confirm_dialog(
                    self,
                    "Update Available",
                    f"pip-ui {info.latest} is available (you have {info.current}).\n\nUpgrade now?",
                ):
                    self.self_upgrade()
            return

        # Up to date.
        if getattr(self, "manual_update_check_pending", False):
            self.manual_update_check_pending = False
            self.restore_interpreter_status()
            info_dialog(
                self,
                "Up to Date",
                f"pip-ui is up to date (version {info.current}).",
            )

    def restore_interpreter_status(self) -> None:
        if self.current_interpreter is None:
            self.status_interpreter_var.set("No interpreter selected")
            return
        info = self.current_interpreter
        self.status_interpreter_var.set(f"{info.path} ({info.version}, pip {info.pip_version})")

    # ------------------------------------------------------------- polling

    def poll_queues(self) -> None:
        try:
            while True:
                kind, line = self.output_queue.get_nowait()
                if kind == "stdout":
                    self.output_panel.append_stdout(line)
                else:
                    self.output_panel.append_stderr(line)
                    self.stderr_buffer.append(line)
        except queue.Empty:
            pass

        try:
            exit_code = self.done_queue.get_nowait()
            self.on_run_done(exit_code)
        except queue.Empty:
            pass

        try:
            upgrade = self.upgrade_queue.get_nowait()
            self.handle_upgrade_result(upgrade)
        except queue.Empty:
            pass

        self.after(50, self.poll_queues)

    def on_run_done(self, exit_code: int) -> None:
        end_time = datetime.now()
        start_time = self.run_start_time or end_time
        duration = (end_time - start_time).total_seconds()
        self.last_run_exit = exit_code

        if exit_code == 0:
            self.output_panel.append_stdout(f"\n[Completed successfully in {duration:.2f}s]\n")
        elif exit_code == -1:
            self.output_panel.append_stderr(f"\n[Cancelled by user after {duration:.2f}s]\n")
        elif exit_code == -9:
            self.output_panel.append_stderr(f"\n[Force killed after {duration:.2f}s]\n")
        else:
            self.output_panel.append_stderr(f"\n[Exited with code {exit_code} in {duration:.2f}s]\n")

        stderr_blob = "".join(self.stderr_buffer)
        for hint in explain_pip_error(stderr_blob):
            self.output_panel.append_combined(f"[hint] {hint}\n", tag="hint")

        self.output_panel.append_command_info(
            {
                "Exit Code": exit_code,
                "Ended": end_time.isoformat(timespec="seconds"),
                "Duration (s)": f"{duration:.3f}",
            }
        )

        self.output_panel.set_running(False)

        # Cache the output for this command so re-selecting it shows what we
        # ran last time instead of a blank panel. Key uses the *current* run,
        # not whatever the form is showing now (the user may have already
        # clicked another command in the tree).
        if self.current_run_command is not None and self.current_interpreter is not None:
            key = (self.current_interpreter.path, self.current_run_command)
            self.output_cache[key] = self.output_panel.snapshot()
        self.current_run_command = None

        if self.history is not None and self.current_interpreter is not None:
            redacted = getattr(self, "run_redacted_argv", [])
            label = getattr(self, "run_label", "")
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

        if self.pending_self_upgrade:
            self.pending_self_upgrade = False
            if exit_code == 0:
                info_dialog(
                    self,
                    "Upgrade Complete",
                    "pip-ui upgrade finished successfully. Restart the application to use the new version.",
                )
                self.upgrade_banner_var.set("")
                self.upgrade_banner.pack_forget()
            elif exit_code in (-1, -9):
                error_dialog(self, "Upgrade Cancelled", "The pip-ui upgrade was cancelled before it completed.")
            else:
                error_dialog(
                    self,
                    "Upgrade Failed",
                    f"pip-ui upgrade exited with code {exit_code}. See the output panel for details.",
                )

    # --------------------------------------------------------------- misc

    def show_config_view(self) -> None:
        ConfigView(self, interpreter_info=self.current_interpreter, show_secrets=bool(self.show_secrets.get()))

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
                text = focused.selection_get()  # type: ignore[no-untyped-call]
                self.clipboard_clear()
                self.clipboard_append(text)
        except tk.TclError:
            self.bell()

    def copy_command(self) -> None:
        if self.command_form.spec is None:
            return
        self.command_form.copy_command()

    def on_close(self) -> None:
        self.settings.set("window_width", self.winfo_width())
        self.settings.set("window_height", self.winfo_height())
        self.destroy()
