"""Help panel with tabbed overview/safety/examples/config."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

from pip_ui.encoding import utf8_subprocess_kwargs
from pip_ui.models import CommandSpec, InterpreterInfo, SafetyLevel
from pip_ui.runner import PipRunner
from pip_ui.safety import check_global_install, classify_command, collect_argv_warnings

SAFETY_LABELS = {
    SafetyLevel.READ_ONLY: "Read Only - safe to run",
    SafetyLevel.MODIFIES_ENV: "Modifies Environment - changes installed packages",
    SafetyLevel.DESTRUCTIVE: "Destructive - removes packages or data",
    SafetyLevel.RISKY_CONFIG: "Risky Config - modifies pip configuration",
}

EXAMPLES: dict[str, list[str]] = {
    "install": [
        "Install a package: requests",
        "Install with version pin: requests==2.28.0",
        "Install from requirements file: -r requirements.txt",
        "Install editable local project: -e .",
        "Upgrade an existing package: requests (with Upgrade checked)",
        "Install from internal index: -i https://internal.example.com/simple/",
        "Install offline from wheelhouse: --no-index -f ./wheelhouse",
    ],
    "uninstall": [
        "Uninstall a package: requests",
        "Uninstall multiple: requests flask",
        "Uninstall all from file: -r requirements.txt",
    ],
    "list": [
        "List all packages (default)",
        "List outdated packages (check Outdated Only)",
        "List in JSON format (select json in Format)",
    ],
    "show": [
        "Show info for one package: requests",
        "Show info including files: requests (check Show Files)",
    ],
    "freeze": [
        "Output all installed packages in requirements format",
        "Exclude editable: check Exclude Editable",
    ],
    "check": ["Verify dependency compatibility: no options needed"],
    "inspect": ["Inspect installed packages (JSON output)"],
    "index_versions": [
        "Show all versions of requests on PyPI",
        "Show pre-release versions: check Include Pre-releases",
    ],
    "download": [
        "Download a package and its deps into ./wheelhouse",
        "Restrict to a specific platform/python version for offline install",
    ],
    "wheel": ["Build wheels for the packages in requirements.txt into ./wheels"],
    "lock": ["Generate a lockfile (requires recent pip)"],
    "config_list": ["List active pip configuration values"],
    "config_debug": ["Show pip configuration sources and effective values"],
    "config_get": ["Read a config value: global.index-url"],
    "config_set": ["Set a user-scope value: global.index-url https://internal.example.com/simple/"],
    "config_unset": ["Remove a value: global.index-url"],
    "config_edit": ["Open the user pip config file in an external editor"],
    "cache_dir": ["Show the cache directory path"],
    "cache_info": ["Show cache statistics"],
    "cache_list": ["List cached wheels matching requests*"],
    "cache_remove": ["Remove cached entries matching requests*"],
    "cache_purge": ["Remove every cached pip artifact"],
}

TROUBLESHOOTING: dict[str, str] = {
    "install": (
        "Common errors:\n"
        "- Permission denied: use a virtual environment or --user.\n"
        "- No matching distribution found: check package name, Python version, or --index-url.\n"
        "- SSL error: check --cert/--client-cert or proxy.\n"
        "- Externally-managed environment: use a venv; do not use --break-system-packages on system Python."
    ),
    "uninstall": (
        "Common errors:\n"
        "- Package not found: package may not be installed.\n"
        "- Permission denied: you may not have write access to the environment."
    ),
    "list": (
        "Notes:\n"
        "- '--outdated' makes network requests to PyPI.\n"
        "- 'tree' format is not always available; use json for scripting."
    ),
    "config_set": (
        "Notes:\n"
        "- Scope 'global' writes a machine-wide file and may require admin rights.\n"
        "- 'user' is the safe default for personal use."
    ),
    "cache_purge": (
        "Cache purge cannot be undone. Wheels you previously installed offline will need to be re-downloaded."
    ),
}

# Maps a command spec name to the argv that ``pip help`` understands. Most pip
# subcommands accept their own help; for grouped ones (config, cache, index) we
# fall back to the parent command's help.
HELP_ARGV: dict[str, list[str]] = {
    "config_list": ["help", "config"],
    "config_debug": ["help", "config"],
    "config_get": ["help", "config"],
    "config_set": ["help", "config"],
    "config_unset": ["help", "config"],
    "config_edit": ["help", "config"],
    "cache_dir": ["help", "cache"],
    "cache_info": ["help", "cache"],
    "cache_list": ["help", "cache"],
    "cache_remove": ["help", "cache"],
    "cache_purge": ["help", "cache"],
    "index_versions": ["help", "index"],
    "version": ["--version"],
    "help": ["help"],
}


def help_argv_for(spec_name: str) -> list[str]:
    return list(HELP_ARGV.get(spec_name, ["help", spec_name]))


class HelpPanel(ttk.Frame):
    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.spec: CommandSpec | None = None
        self.interpreter_info: InterpreterInfo | None = None
        self.help_cache: dict[tuple[str, str], str] = {}
        self.build_ui()

    def build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.overview_text = self.make_text_tab("Overview")
        self.command_text = self.make_text_tab("Generated Command")
        self.command_help_text = self.make_text_tab("Command Help")
        self.config_text = self.make_text_tab("Active Config")
        self.safety_text = self.make_text_tab("Safety")
        self.examples_text = self.make_text_tab("Examples")
        self.troubleshooting_text = self.make_text_tab("Troubleshooting")

    def make_text_tab(self, label: str) -> tk.Text:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=label)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, state=tk.DISABLED, padx=6, pady=6)
        text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)
        return text

    def set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state=tk.DISABLED)

    def update_for_command(
        self,
        spec: CommandSpec,
        argv: list[str],
        interpreter_info: InterpreterInfo | None = None,
    ) -> None:
        self.spec = spec
        self.interpreter_info = interpreter_info

        self.set_text(
            self.overview_text,
            f"{spec.label}\n\n{spec.description}\n\n"
            f"Safety: {SAFETY_LABELS.get(spec.safety_level, str(spec.safety_level))}",
        )

        runner = PipRunner()
        python = interpreter_info.path if interpreter_info else "python"
        full_argv = runner.build_argv(python, argv)
        shell_cmd = runner.format_command(full_argv)
        redacted_argv = runner.redact_argv(full_argv)
        redacted_cmd = runner.format_command(redacted_argv)
        body = (
            f"Shell command:\n{shell_cmd}\n\n"
            f"Redacted (shown in logs):\n{redacted_cmd}\n\n"
            f"Argv JSON:\n{json.dumps(argv, indent=2)}"
        )
        self.set_text(self.command_text, body)

        # Command Help tab — show pip's own help for the current (sub)command.
        self.populate_command_help(spec, interpreter_info)

        # Active config snapshot.
        cfg_lines: list[str] = []
        if interpreter_info is None:
            cfg_lines.append("No interpreter selected.")
        else:
            cfg_lines.append(f"Interpreter: {interpreter_info.path}")
            cfg_lines.append(f"Python: {interpreter_info.version}")
            cfg_lines.append(f"Pip: {interpreter_info.pip_version}")
            cfg_lines.append(f"Env type: {interpreter_info.env_type}")
            cfg_lines.append(f"Virtual env: {'yes' if interpreter_info.is_venv else 'no'}")
            cfg_lines.append("")
            cfg_lines.append("Open View → Config Dashboard for full configuration details.")
        self.set_text(self.config_text, "\n".join(cfg_lines))

        safety_level = classify_command(spec.name)
        parts: list[str] = [SAFETY_LABELS.get(safety_level, str(safety_level))]
        if interpreter_info is not None and safety_level != SafetyLevel.READ_ONLY:
            warning = check_global_install(interpreter_info)
            if warning:
                parts.append("")
                parts.append(warning)
        argv_warnings = collect_argv_warnings(argv)
        if argv_warnings:
            parts.append("")
            parts.append("Argument warnings:")
            for w in argv_warnings:
                parts.append(f"- {w}")
        self.set_text(self.safety_text, "\n".join(parts))

        examples = EXAMPLES.get(spec.name, ["No examples available."])
        self.set_text(self.examples_text, "\n".join(f"- {ex}" for ex in examples))

        trouble = TROUBLESHOOTING.get(spec.name, "No known issues for this command.")
        self.set_text(self.troubleshooting_text, trouble)

    def populate_command_help(self, spec: CommandSpec, interpreter_info: InterpreterInfo | None) -> None:
        if interpreter_info is None:
            self.set_text(self.command_help_text, "Select a Python interpreter to load pip's help text.")
            return

        key = (interpreter_info.path, spec.name)
        cached = self.help_cache.get(key)
        if cached is not None:
            self.set_text(self.command_help_text, cached)
            return

        self.set_text(self.command_help_text, "Loading pip help...")

        argv = [interpreter_info.path, "-m", "pip", *help_argv_for(spec.name)]

        def worker() -> None:
            try:
                result = subprocess.run(
                    argv,
                    capture_output=True,
                    **utf8_subprocess_kwargs(),
                    check=False,
                    shell=False,
                    timeout=15,
                )  # nosec B603
                output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
                output = output.strip() or "(no output from pip help)"
            except (OSError, subprocess.SubprocessError) as exc:
                output = f"Error fetching pip help: {exc}"
            self.help_cache[key] = output
            self.after(0, lambda: self.render_command_help(key, output))

        threading.Thread(target=worker, daemon=True, name="pip-ui-help").start()

    def render_command_help(self, key: tuple[str, str], output: str) -> None:
        # Only render if the user is still looking at the same spec/interpreter.
        if self.spec is None or self.interpreter_info is None:
            return
        if (self.interpreter_info.path, self.spec.name) != key:
            return
        self.set_text(self.command_help_text, output)
