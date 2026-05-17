"""Inspect pip and environment configuration."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Optional

from pip_ui.safety import redact_url

ENV_VARS_OF_INTEREST = [
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "PYTHONPATH",
    "PYTHONHOME",
]


class ConfigInspector:
    def __init__(self, python_path: str) -> None:
        self.python_path = python_path

    def run_pip_command(self, args: list[str]) -> tuple[str, str, int]:
        argv = [self.python_path, "-m", "pip"] + args
        try:
            result = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as exc:
            return "", str(exc), -1

    def run_config_debug(self) -> str:
        stdout, stderr, _ = self.run_pip_command(["config", "debug"])
        return stdout + stderr

    def run_config_list(self) -> dict[str, str]:
        stdout, _, _ = self.run_pip_command(["config", "list"])
        result: dict[str, str] = {}
        for line in stdout.splitlines():
            line = line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
        return result

    def run_pip_debug(self) -> str:
        stdout, stderr, _ = self.run_pip_command(["debug"])
        return stdout + stderr

    def get_pip_version(self) -> str:
        stdout, _, _ = self.run_pip_command(["--version"])
        return stdout.strip()

    def get_env_vars(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith("PIP_") or key in ENV_VARS_OF_INTEREST:
                result[key] = redact_url(value)
        return result

    def build_diagnostics_report(self, format: str = "markdown") -> str:
        pip_version = self.get_pip_version()
        config_values = self.run_config_list()
        env_vars = self.get_env_vars()
        pip_debug = self.run_pip_debug()

        if format == "json":
            data = {
                "pip_version": pip_version,
                "config_values": config_values,
                "env_vars": env_vars,
                "pip_debug": pip_debug,
            }
            return json.dumps(data, indent=2)

        if format == "markdown":
            lines = [
                "# pip-ui Diagnostics Report",
                "",
                "## Pip Version",
                "",
                pip_version,
                "",
                "## Active Configuration",
                "",
            ]
            if config_values:
                for k, v in config_values.items():
                    lines.append(f"- `{k}` = `{v}`")
            else:
                lines.append("_No configuration values found._")
            lines += [
                "",
                "## Environment Variables",
                "",
            ]
            if env_vars:
                for k, v in env_vars.items():
                    lines.append(f"- `{k}` = `{v}`")
            else:
                lines.append("_No relevant environment variables found._")
            lines += [
                "",
                "## pip debug output",
                "",
                "```",
                pip_debug,
                "```",
            ]
            return "\n".join(lines)

        lines = [
            "pip-ui Diagnostics Report",
            "=" * 40,
            "",
            "Pip Version:",
            pip_version,
            "",
            "Active Configuration:",
        ]
        for k, v in config_values.items():
            lines.append(f"  {k} = {v}")
        lines += ["", "Environment Variables:"]
        for k, v in env_vars.items():
            lines.append(f"  {k} = {v}")
        lines += ["", "pip debug:", pip_debug]
        return "\n".join(lines)
