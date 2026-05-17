"""Help panel with tabbed overview/safety/examples."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from pip_ui.models import CommandSpec, InterpreterInfo, SafetyLevel
from pip_ui.safety import check_global_install, classify_command

SAFETY_LABELS = {
    SafetyLevel.READ_ONLY: "Read Only - safe to run",
    SafetyLevel.MODIFIES_ENV: "Modifies Environment - changes installed packages",
    SafetyLevel.DESTRUCTIVE: "Destructive - removes packages",
    SafetyLevel.RISKY_CONFIG: "Risky Config - modifies pip configuration",
}

SAFETY_COLORS = {
    SafetyLevel.READ_ONLY: "green",
    SafetyLevel.MODIFIES_ENV: "orange",
    SafetyLevel.DESTRUCTIVE: "red",
    SafetyLevel.RISKY_CONFIG: "red",
}

EXAMPLES: dict[str, list[str]] = {
    "install": [
        "Install a package: requests",
        "Install with version pin: requests==2.28.0",
        "Install from requirements file: -r requirements.txt",
        "Install editable local project: -e .",
        "Upgrade an existing package: requests (with Upgrade checked)",
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
    "check": [
        "Verify dependency compatibility: no options needed",
    ],
}

TROUBLESHOOTING: dict[str, str] = {
    "install": (
        "Common errors:\n"
        "- Permission denied: try user install or use a virtual environment\n"
        "- No matching distribution found: check package name or index URL\n"
        "- SSL error: check --trusted-host or network proxy settings"
    ),
    "uninstall": (
        "Common errors:\n"
        "- Package not found: package may not be installed\n"
        "- Permission denied: you may not have write access to the environment"
    ),
    "list": (
        "Common errors:\n"
        "- 'tree' format requires pip >= 23.0\n"
        "- '--outdated' makes network requests to PyPI"
    ),
}


class HelpPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.spec: Optional[CommandSpec] = None
        self.interpreter_info: Optional[InterpreterInfo] = None
        self.build_ui()

    def build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.overview_text = self.make_text_tab("Overview")
        self.command_text = self.make_text_tab("Generated Command")
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
        interpreter_info: Optional[InterpreterInfo] = None,
    ) -> None:
        self.spec = spec
        self.interpreter_info = interpreter_info

        self.set_text(self.overview_text, f"{spec.label}\n\n{spec.description}\n\nSafety: {SAFETY_LABELS.get(spec.safety_level, str(spec.safety_level))}")

        from pip_ui.runner import PipRunner
        runner = PipRunner()
        python = interpreter_info.path if interpreter_info else "python"
        full_argv = runner.build_argv(python, argv)
        shell_cmd = runner.format_command(full_argv)
        self.set_text(self.command_text, f"Shell command:\n{shell_cmd}\n\nArgv JSON:\n{json.dumps(argv, indent=2)}")

        safety_level = classify_command(spec.name)
        safety_text = SAFETY_LABELS.get(safety_level, str(safety_level)) + "\n"
        if interpreter_info is not None:
            warning = check_global_install(interpreter_info)
            if warning and safety_level != SafetyLevel.READ_ONLY:
                safety_text += f"\n{warning}"
        self.set_text(self.safety_text, safety_text)

        examples = EXAMPLES.get(spec.name, ["No examples available."])
        self.set_text(self.examples_text, "\n".join(f"- {ex}" for ex in examples))

        trouble = TROUBLESHOOTING.get(spec.name, "No known issues for this command.")
        self.set_text(self.troubleshooting_text, trouble)
