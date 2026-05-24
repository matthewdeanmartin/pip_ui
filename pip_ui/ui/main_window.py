"""Main application window."""

# pylint: disable=too-many-lines

from __future__ import annotations

import contextlib
import os
import queue
import sys
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, ttk
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib

from pip_ui.__about__ import __version__
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
from pip_ui.tool_detector import detect_all_tools
from pip_ui.tools import ToolPlugin, get_plugin
from pip_ui.ui.audit_result_panel import AuditResultPanel
from pip_ui.ui.cert_tester import CertTesterDialog
from pip_ui.ui.command_form import CommandForm, default_global_values
from pip_ui.ui.command_tree import CommandTree
from pip_ui.ui.config_view import ConfigView
from pip_ui.ui.dialogs import confirm_dialog, error_dialog, info_dialog
from pip_ui.ui.global_options_dialog import GlobalOptionsDialog, summarize_globals
from pip_ui.ui.help_panel import HelpPanel
from pip_ui.ui.index_selector import IndexSelector
from pip_ui.ui.interpreter_picker import InterpreterPicker
from pip_ui.ui.output_panel import OutputPanel
from pip_ui.ui.pipx_python_picker import PipxPythonPicker
from pip_ui.ui.proxy_dialog import ProxyDialog
from pip_ui.ui.requirements_picker import RequirementsPicker
from pip_ui.ui.tool_switcher import ToolSwitcher


class MainWindow(tk.Tk):
    def __init__(self, no_history: bool = False, safe_mode: bool = False, dry_run: bool = False) -> None:
        super().__init__()
        self.no_history = no_history
        self.safe_mode = safe_mode
        self.dry_run = dry_run
        self.settings = AppSettings()
        self.settings.load()
        default_plugin = get_plugin("pip")
        assert default_plugin is not None
        self.active_plugin: ToolPlugin = default_plugin
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
            # pip
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
            # other tools
            "venv_version",
            "twine_version",
            "audit_version",
            "hatch_env_show",
            "hatch_version_show",
            "pipx_list",
            "pipx_environment",
        }

        # Globals are now stored centrally, not on each per-command form.
        stored_globals = self.settings.get("global_options", None) or default_global_values()
        merged_globals = default_global_values()
        merged_globals.update(stored_globals)
        self.global_options: dict[str, Any] = merged_globals

        self.global_requirements_file: str | None = None
        self.active_index_url: str | None = None
        self._active_help_url = "https://pip.pypa.io/en/stable/"
        self._pipx_picker_row: ttk.Frame | None = None
        self._pipx_picker: PipxPythonPicker | None = None
        self._pipx_python_path: str | None = None
        self.interpreter_row: ttk.Frame
        self.toolbar2: ttk.Frame
        self.dir_label: ttk.Label
        self.workdir_var: tk.StringVar
        self.requirements_picker: RequirementsPicker

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

        ToolSwitcher.configure_styles(self)
        self.build_menu()
        self.build_tool_switcher()
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
        # Kick off background tool detection; results update the tab row.
        self._start_tool_detection()
        # Restore the previously active tool (after detection so availability is set).
        saved_tool = self.settings.get("active_tool", "pip")
        if saved_tool and saved_tool != "pip":
            self.after(300, lambda: self.tool_switcher.select(str(saved_tool)))

    # -------------------------------------------------------- tool switcher

    def build_tool_switcher(self) -> None:
        self.tool_switcher = ToolSwitcher(self, on_switch=self.on_tool_switch)
        self.tool_switcher.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(2, 0))

    def on_tool_switch(self, plugin: ToolPlugin) -> None:
        self.active_plugin = plugin
        self.settings.set("active_tool", plugin.name)

        # Rebuild the command tree for this tool.
        self.command_tree.load_plugin(plugin.command_specs, plugin.command_groups)

        # Swap middle panel to the tool's panel_class (or plain CommandForm).
        self.swap_middle_panel(plugin)

        # Show/hide interpreter row and pipx Python picker.
        if plugin.hide_interpreter_picker:
            self.interpreter_row.pack_forget()
            self._show_pipx_picker()
        else:
            self._hide_pipx_picker()
            self.interpreter_row.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(0, 2), before=self.toolbar2)

        # Rename Dir label for project-scoped tools.
        label_text = "Project Dir:" if plugin.is_project_scoped else "Dir:"
        self.dir_label.config(text=label_text)

        # Update title bar.
        self.title(f"pip-ui v{__version__} — {plugin.label}")

        # Update Help menu doc link.
        self._active_help_url = plugin.help_url
        self._update_help_menu()
        if self.help_panel is not None:
            self.help_panel.set_base_url(plugin.help_url)
            self.help_panel.set_project_status(self._detect_project_status(plugin))
            self.help_panel.set_active_plugin(plugin)

        # Clear output cache (different tool = different outputs).
        self.output_cache.clear()
        self.output_panel.clear()

    def _start_tool_detection(self) -> None:
        def on_result(name: str, available: bool) -> None:
            self.after(0, lambda: self.tool_switcher.set_available(name, available))

        detect_all_tools(self.current_interpreter, on_result=on_result)

    def _show_pipx_picker(self) -> None:
        if self._pipx_picker_row is None:
            self._pipx_picker_row = ttk.Frame(self, relief=tk.GROOVE, borderwidth=1)
            self._pipx_picker = PipxPythonPicker(
                self._pipx_picker_row,
                on_change=self._on_pipx_python_change,
            )
            self._pipx_picker.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self._pipx_picker_row.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(0, 2), before=self.toolbar2)

    def _hide_pipx_picker(self) -> None:
        if self._pipx_picker_row is not None:
            self._pipx_picker_row.pack_forget()

    def _on_pipx_python_change(self, python_path: str | None) -> None:
        self._pipx_python_path = python_path

    def _detect_project_status(self, plugin: ToolPlugin) -> str:
        """Return a 'project: name version' string for project-scoped tools, or empty string."""
        if not plugin.is_project_scoped:
            return ""
        workdir = self.workdir_var.get() or os.getcwd()
        pyproject = os.path.join(workdir, "pyproject.toml")
        if not os.path.isfile(pyproject):
            return ""
        try:
            with open(pyproject, "rb") as fh:
                data = tomllib.load(fh)
            project = data.get("project", {})
            if not isinstance(project, dict):
                return ""
            name = str(project.get("name", ""))
            version = str(project.get("version", ""))
            if name:
                label = plugin.label
                return f"{label} project: {name} {version}".strip()
        except (OSError, tomllib.TOMLDecodeError):
            return ""
        return ""

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
        tools_menu.add_command(label="HTTPS Certificate Tester...", command=self.open_cert_tester)
        tools_menu.add_command(label="HTTP Proxy Configuration...", command=self.open_proxy_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Check for Updates", command=self.manual_check_updates)
        tools_menu.add_command(label="Upgrade pip-ui", command=self.self_upgrade)

        self.help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Documentation", command=self.open_tool_documentation)
        self.help_menu.add_command(label="pip Release Notes", command=self.open_pip_release_notes)
        self.help_menu.add_separator()
        self.help_menu.add_command(label="About", command=self.show_about)

    # --------------------------------------------------------------- toolbar

    def build_toolbar(self) -> None:
        self.interpreter_row = ttk.Frame(self, relief=tk.GROOVE, borderwidth=1)
        self.interpreter_row.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)

        self.interpreter_picker = InterpreterPicker(self.interpreter_row, on_change=self.on_interpreter_change)
        self.interpreter_picker.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.dir_label = ttk.Label(self.interpreter_row, text="Dir:")
        self.dir_label.pack(side=tk.LEFT, padx=(8, 2))
        self.workdir_var = tk.StringVar(value=self.settings.get("last_working_dir") or os.getcwd())
        workdir_entry = ttk.Entry(self.interpreter_row, textvariable=self.workdir_var, width=30)
        workdir_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(self.interpreter_row, text="Browse...", command=self.browse_workdir).pack(side=tk.LEFT, padx=2)

        # Second row: requirements picker + index selector + Global Options button.
        self.toolbar2 = ttk.Frame(self, relief=tk.GROOVE, borderwidth=1)
        toolbar2 = self.toolbar2
        toolbar2.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(0, 2))

        self.requirements_picker = RequirementsPicker(toolbar2, on_change=self.on_requirements_change)
        self.requirements_picker.pack(side=tk.LEFT, padx=4)

        self.index_selector = IndexSelector(
            toolbar2,
            settings=self.settings,
            on_change=self.on_index_change,
        )
        self.index_selector.pack(side=tk.LEFT, padx=4)

        ttk.Button(
            toolbar2,
            text="Global Options...",
            command=self.open_global_options_dialog,
        ).pack(side=tk.LEFT, padx=4)

        self.global_options_summary_var = tk.StringVar(value="(globals: defaults)")
        ttk.Label(toolbar2, textvariable=self.global_options_summary_var, foreground="#444").pack(side=tk.LEFT, padx=4)

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
            f"⚡ pip-ui {info.latest} is available (you have {info.current}). " "Use Tools → Upgrade pip-ui to install."
        )
        self.upgrade_banner.pack(side=tk.TOP, fill=tk.X)

    # ----------------------------------------------------------- main panels

    def build_main_panels(self) -> None:
        self.horizontal_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.horizontal_paned.pack(fill=tk.BOTH, expand=True)

        self.command_tree = CommandTree(self.horizontal_paned, on_select=self.on_command_select)
        self.horizontal_paned.add(self.command_tree, weight=0)

        self.middle_paned = ttk.PanedWindow(self.horizontal_paned, orient=tk.VERTICAL)
        self.horizontal_paned.add(self.middle_paned, weight=2)

        self.command_form = CommandForm(
            self.middle_paned,
            on_run=self.run_command,
            on_form_change=self.on_form_change,
            global_values_provider=lambda: dict(self.global_options),
            on_open_global_options=self.open_global_options_dialog,
            global_requirements_provider=lambda: self.global_requirements_file,
            show_global_options=True,
        )
        self.middle_paned.add(self.command_form, weight=1)

        self.output_panel = OutputPanel(self.middle_paned, on_cancel=self.on_cancel_running)
        self.middle_paned.add(self.output_panel, weight=1)

        self.help_panel = HelpPanel(self.horizontal_paned)
        self.horizontal_paned.add(self.help_panel, weight=0)

        # Position sashes after the window has been laid out (and maximized),
        # so winfo_width() reflects the real screen-sized geometry rather than
        # the requested 1100px.
        self.after(150, self.apply_initial_sash_positions)

        self.refresh_global_options_summary()

    def swap_middle_panel(self, plugin: ToolPlugin) -> None:
        """Replace the command form slot with the plugin's panel_class, or CommandForm."""
        # Destroy the old panel (not the output_panel).
        if self.command_form is not None:
            self.middle_paned.forget(self.command_form)
            self.command_form.destroy()
            self.command_form = None

        panel_class = plugin.panel_class
        show_globals = plugin.name == "pip"
        # kwargs shared between CommandForm and panel wrappers — must NOT include
        # show_global_options because panel classes forward **kwargs to ttk.Frame.
        form_kwargs: dict[str, Any] = {
            "on_run": self.run_command,
            "on_form_change": self.on_form_change,
            "global_values_provider": lambda: dict(self.global_options),
            "on_open_global_options": self.open_global_options_dialog,
            "global_requirements_provider": lambda: self.global_requirements_file,
        }

        if panel_class is None:
            new_panel: Any = CommandForm(self.middle_paned, show_global_options=show_globals, **form_kwargs)
        else:
            try:
                new_panel = panel_class(self.middle_paned, **form_kwargs)
            except (TypeError, tk.TclError):
                # Panel doesn't accept CommandForm kwargs — fall back to a plain form.
                new_panel = CommandForm(self.middle_paned, show_global_options=show_globals, **form_kwargs)

        # Insert before output_panel (index 0 in the paned window).
        self.middle_paned.insert(0, new_panel, weight=1)
        self.command_form = new_panel

        # Tell the form which executable prefix to show in the command preview.
        interp = self.current_interpreter.path if self.current_interpreter else "python"
        preview_prefix = self.runner.build_prefix(interp, plugin)
        if hasattr(self.command_form, "set_preview_prefix"):
            self.command_form.set_preview_prefix(preview_prefix)

        # Pass workdir to panels that support it (e.g. HatchEnvPanel).
        if hasattr(self.command_form, "set_workdir"):
            self.command_form.set_workdir(self.workdir_var.get() or os.getcwd())

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
            self.attributes("-zoomed", True)
            return
        except tk.TclError:
            pass
        # Last resort: size to the screen.
        with contextlib.suppress(tk.TclError):
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

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
        self.bind("<Control-r>", lambda e: self.command_form.do_run() if self.command_form else None)
        self.bind("<Control-l>", lambda e: self.command_tree.focus_search())
        self.bind("<Control-q>", lambda e: self.on_close())
        self.bind("<Control-Shift-C>", lambda e: self.copy_command())

    # ------------------------------------------------------------ callbacks

    def on_show_secrets_toggle(self) -> None:
        reveal = bool(self.show_secrets.get())
        self.settings.set("show_secrets", reveal)
        if self.command_form is not None:
            self.command_form.apply_show_secrets(reveal)

    def _update_preview_prefix(self) -> None:
        """Refresh the command-form preview prefix to match current interpreter + plugin."""
        if self.command_form is None or not hasattr(self, "runner") or not hasattr(self, "active_plugin"):
            return
        interp = self.current_interpreter.path if self.current_interpreter else "python"
        prefix = self.runner.build_prefix(interp, self.active_plugin)
        if hasattr(self.command_form, "set_preview_prefix"):
            self.command_form.set_preview_prefix(prefix)

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
                self._start_tool_detection()
            # If a command is already selected, refresh it.
            if hasattr(self, "_update_preview_prefix"):
                self._update_preview_prefix()
            if self.command_form is not None and self.command_form.spec is not None:
                self.after(0, self.refresh_current_command_output)

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
            if self.command_form is not None and hasattr(self.command_form, "set_workdir"):
                self.command_form.set_workdir(path)

    def on_command_select(self, command_name: str) -> None:
        spec = self.active_plugin.command_specs.get(command_name)
        if spec is None:
            return
        self.stderr_buffer = []
        if self.command_form and self.help_panel:
            self.command_form.set_command(spec)
            self.help_panel.update_for_command(spec, self.command_form.get_argv(), self.current_interpreter)
        self.show_output_for_command(command_name)

    def show_output_for_command(self, command_name: str) -> None:
        """Restore cached output for this command, or trigger a one-time auto-run."""
        if self.runner.is_running():
            # Don't disturb an in-flight command's output.
            return
        cache_key = self.cache_key_for(command_name)
        if cache_key in self.output_cache:
            self.output_panel.restore(self.output_cache[cache_key])
            return
        # No cache yet. For read-only commands that need nothing, run with defaults.
        # For pipx, auto-run even without a selected interpreter (global_cli tool).
        can_autorun = command_name in self.autorun_on_select and (
            self.current_interpreter is not None or self.active_plugin.name == "pipx"
        )
        if can_autorun:
            self.output_panel.clear()
            self.output_panel.append_combined(
                f"[auto] Running {command_name.replace('_', ' ')} with defaults...\n",
                tag="hint",
            )
            if self.command_form:
                self.command_form.do_run()
            return
        # Nothing to show; leave the panel empty so the user can fill the form.
        self.output_panel.clear()

    def refresh_current_command_output(self) -> None:
        if self.command_form is None or self.command_form.spec is None:
            return
        self.show_output_for_command(self.command_form.spec.name)

    def cache_key_for(self, command_name: str) -> tuple[str, str]:
        path = self.current_interpreter.path if self.current_interpreter is not None else self.active_plugin.name
        return (path, command_name)

    def on_form_change(self) -> None:
        if self.command_form and self.command_form.spec and self.help_panel:
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
        chips = summarize_globals(self.global_options)
        if not chips:
            self.global_options_summary_var.set("(globals: defaults)")
        else:
            shown = chips if len(chips) <= 3 else [*chips[:3], f"+{len(chips) - 3} more"]
            self.global_options_summary_var.set("globals: " + ", ".join(shown))

    # -------------------------------------------------------------- runners

    def run_command(self, pip_args: list[str], label: str) -> None:
        if self.current_interpreter is None and self.active_plugin.name != "pipx":
            error_dialog(self, "No Interpreter", "Please select a Python interpreter first.")
            return
        if self.runner.is_running():
            error_dialog(self, "Already Running", "A pip command is already in progress. Cancel it first.")
            return

        command_name = self.command_form.spec.name if self.command_form and self.command_form.spec else ""
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
        effective_pip_args = list(pip_args)
        if (
            self.active_index_url is not None
            and "--index-url" not in effective_pip_args
            and "-i" not in effective_pip_args
            and command_name in {"install", "download", "wheel", "index_versions"}
        ):
            effective_pip_args.extend(["--index-url", self.active_index_url])

        # For pipx, inject --python if the user picked a specific interpreter.
        pipx_python = getattr(self, "_pipx_python_path", None)
        if self.active_plugin.name == "pipx" and pipx_python is not None and "--python" not in effective_pip_args:
            effective_pip_args = ["--python", pipx_python, *effective_pip_args]

        # For pipx we have no interpreter row, so use the system python as a placeholder.
        interpreter_path = (
            self.current_interpreter.path
            if self.current_interpreter is not None
            else (self._pipx_python_path or "python")
        )
        full_argv = self.runner.build_argv(interpreter_path, effective_pip_args, plugin=self.active_plugin)

        self.output_panel.clear()
        self.stderr_buffer = []
        self.last_run_argv = list(pip_args)

        redacted_argv = PipRunner.redact_argv(full_argv, secret_flags=self.active_plugin.secret_flags)
        display_argv = full_argv if self.show_secrets.get() else redacted_argv

        interp = self.current_interpreter
        self.output_panel.set_command_info(
            {
                "Command": label,
                "Interpreter": interp.path if interp else interpreter_path,
                "Python Version": interp.version if interp else "",
                "Pip Version": interp.pip_version if interp else "",
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
        self.runner.run(
            full_argv,
            cwd,
            enqueue_stdout,
            enqueue_stderr,
            on_done,
            env=env,
            strip_venv=self.active_plugin.run_via == "global_cli",
            dry_run=self.dry_run,
        )

        self.run_pip_args = effective_pip_args
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
        finished_command = self.current_run_command
        if finished_command is not None:
            cache_path = (
                self.current_interpreter.path if self.current_interpreter is not None else self.active_plugin.name
            )
            key = (cache_path, finished_command)
            self.output_cache[key] = self.output_panel.snapshot()
        self.current_run_command = None

        # Notify custom panels about run completion.
        if (
            finished_command is not None
            and self.command_form is not None
            and hasattr(self.command_form, "notify_run_done")
        ):
            self.command_form.notify_run_done(exit_code, finished_command, list(self.last_run_argv))

        # Post-process pip-audit JSON output.
        if finished_command == "audit" and exit_code == 0 and "--output-format" in self.last_run_argv:
            fmt_idx = self.last_run_argv.index("--output-format")
            if fmt_idx + 1 < len(self.last_run_argv) and self.last_run_argv[fmt_idx + 1] == "json":
                self._try_show_audit_result()

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

    def _try_show_audit_result(self) -> None:
        """Parse pip-audit JSON from the output panel and show AuditResultPanel in a dialog."""
        raw = self.output_panel.get_stdout_text()
        if not raw:
            return

        top = tk.Toplevel(self)
        top.title("pip-audit Results")
        top.geometry("800x500")
        panel = AuditResultPanel(top)
        panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        if not panel.load_json(raw):
            top.title("pip-audit Results (raw — JSON parse failed)")

    # --------------------------------------------------------------- misc

    def on_index_change(self, url: str | None) -> None:
        self.active_index_url = url
        if self.command_form is not None:
            self.command_form.update_preview()

    def open_cert_tester(self) -> None:
        python_path = self.current_interpreter.path if self.current_interpreter else None
        CertTesterDialog(self, python_path=python_path)

    def open_proxy_dialog(self) -> None:
        python_path = self.current_interpreter.path if self.current_interpreter else None
        current_proxy = self.global_options.get("g_proxy") or None

        def apply_proxy(proxy: str | None) -> None:
            self.global_options["g_proxy"] = proxy
            self.settings.set("global_options", self.global_options)
            self.refresh_global_options_summary()
            if self.command_form is not None:
                self.command_form.refresh_globals_summary()
                self.command_form.update_preview()

        ProxyDialog(self, python_path=python_path, current_proxy=current_proxy, on_apply=apply_proxy)

    def show_config_view(self) -> None:
        ConfigView(self, interpreter_info=self.current_interpreter, show_secrets=bool(self.show_secrets.get()))

    def open_url(self, url: str) -> None:
        try:
            webbrowser.open(url, new=2)
        except webbrowser.Error as exc:
            error_dialog(self, "Open Link Failed", f"Could not open link:\n{url}\n\n{exc}")

    def open_tool_documentation(self) -> None:
        self.open_url(self._active_help_url)

    def _update_help_menu(self) -> None:
        label = f"{self.active_plugin.label} Documentation"
        self.help_menu.entryconfig(0, label=label)
        # Show/hide pip Release Notes depending on active tool.
        if self.active_plugin.name == "pip":
            self.help_menu.entryconfig(1, state=tk.NORMAL)
        else:
            self.help_menu.entryconfig(1, state=tk.DISABLED)

    def open_pip_documentation(self) -> None:
        self.open_url("https://pip.pypa.io/en/stable/")

    def open_pip_release_notes(self) -> None:
        self.open_url(self.pip_release_notes_url())

    def pip_release_notes_url(self) -> str:
        pip_version = self.current_interpreter.pip_version if self.current_interpreter is not None else ""
        anchor = pip_release_notes_anchor(pip_version)
        return f"https://pip.pypa.io/en/stable/news/#{anchor}" if anchor else "https://pip.pypa.io/en/stable/news/"

    def show_about(self) -> None:
        info_dialog(
            self,
            "About pip-ui",
            (
                f"pip-ui v{__version__}\n\n"
                "A Tkinter GUI for pip.\n"
                "Runs: python -m pip\n\n"
                "pip is a project of the Python Package Authority (PyPA).\n"
                "pip-ui-tkinter is an independent project and is not affiliated with or maintained by PyPA.\n\n"
                "No pip internals are used."
            ),
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
        if self.command_form and self.command_form.spec:
            self.command_form.copy_command()

    def on_close(self) -> None:
        self.settings.set("window_width", self.winfo_width())
        self.settings.set("window_height", self.winfo_height())
        self.destroy()


def pip_release_notes_anchor(pip_version: str) -> str | None:
    normalized = pip_version.strip().lstrip("v").replace(".", "-")
    if not normalized:
        return None
    if any(ch not in "0123456789-" for ch in normalized):
        return None
    return f"v{normalized}"
