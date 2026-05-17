"""Inspect pip and environment configuration."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from pip_ui.safety import redact_url

PYTHON_ENV_VARS = [
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "PYTHONPATH",
    "PYTHONHOME",
]

# Explicit list per spec §10.4.
PIP_ENV_VARS = [
    "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL",
    "PIP_NO_INDEX",
    "PIP_FIND_LINKS",
    "PIP_TRUSTED_HOST",
    "PIP_REQUIRE_VIRTUALENV",
    "PIP_REQUIRE_HASHES",
    "PIP_CERT",
    "PIP_CLIENT_CERT",
    "PIP_CACHE_DIR",
    "PIP_NO_CACHE_DIR",
    "PIP_CONFIG_FILE",
    "PIP_DISABLE_PIP_VERSION_CHECK",
    "PIP_DEFAULT_TIMEOUT",
    "PIP_RETRIES",
    "PIP_PROXY",
]


@dataclass
class ConfigFileInfo:
    path: str
    scope: str
    exists: bool
    size: Optional[int]
    modified: Optional[str]


@dataclass
class IndexInfo:
    main_index_url: Optional[str]
    extra_index_urls: list[str]
    no_index: bool
    find_links: list[str]
    trusted_hosts: list[str]
    has_credentials: bool


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
        return parse_config_list(stdout)

    def run_pip_debug(self) -> str:
        stdout, stderr, _ = self.run_pip_command(["debug"])
        return stdout + stderr

    def run_cache_info(self) -> str:
        stdout, stderr, _ = self.run_pip_command(["cache", "info"])
        return stdout + stderr

    def run_cache_dir(self) -> str:
        stdout, _, _ = self.run_pip_command(["cache", "dir"])
        return stdout.strip()

    def get_pip_version(self) -> str:
        stdout, _, _ = self.run_pip_command(["--version"])
        return stdout.strip()

    def get_env_vars(self, show_secrets: bool = False) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith("PIP_") or key in PYTHON_ENV_VARS:
                result[key] = value if show_secrets else redact_url(value)
        return result

    def discover_config_files(self) -> list[ConfigFileInfo]:
        """Extract candidate config file paths from `pip config debug` output."""
        debug = self.run_config_debug()
        return parse_config_files(debug)

    def detect_index_info(self) -> IndexInfo:
        config = self.run_config_list()
        env = self.get_env_vars(show_secrets=True)

        main_index = (
            config.get("global.index-url")
            or env.get("PIP_INDEX_URL")
            or None
        )
        extra_raw = config.get("global.extra-index-url") or env.get("PIP_EXTRA_INDEX_URL") or ""
        extras = [x.strip() for x in re.split(r"[\s,]+", extra_raw) if x.strip()]

        find_raw = config.get("global.find-links") or env.get("PIP_FIND_LINKS") or ""
        find_links = [x.strip() for x in re.split(r"[\s,]+", find_raw) if x.strip()]

        trusted_raw = config.get("global.trusted-host") or env.get("PIP_TRUSTED_HOST") or ""
        trusted = [x.strip() for x in re.split(r"[\s,]+", trusted_raw) if x.strip()]

        no_index_str = (config.get("global.no-index") or env.get("PIP_NO_INDEX") or "").lower()
        no_index = no_index_str in {"1", "true", "yes", "on"}

        all_urls = [main_index or ""] + extras
        has_creds = any(re.search(r"://[^:@/\s]+:[^@/\s]+@", u) for u in all_urls)

        return IndexInfo(
            main_index_url=main_index,
            extra_index_urls=extras,
            no_index=no_index,
            find_links=find_links,
            trusted_hosts=trusted,
            has_credentials=has_creds,
        )

    def virtual_env_status(self) -> dict[str, str]:
        return {
            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
            "CONDA_PREFIX": os.environ.get("CONDA_PREFIX", ""),
            "sys.executable": self.python_path,
        }

    def build_diagnostics_report(
        self,
        format: str = "markdown",
        last_command: Optional[str] = None,
        last_exit_code: Optional[int] = None,
        working_directory: Optional[str] = None,
        show_secrets: bool = False,
    ) -> str:
        pip_version = self.get_pip_version()
        config_values = self.run_config_list()
        env_vars = self.get_env_vars(show_secrets=show_secrets)
        pip_debug = self.run_pip_debug()
        cache_info = self.run_cache_info()
        config_files = self.discover_config_files()
        index_info = self.detect_index_info()
        venv_status = self.virtual_env_status()
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        wd = working_directory or os.getcwd()

        if format == "json":
            data = {
                "os": os_info,
                "python_executable": self.python_path,
                "python_version": sys.version,
                "pip_version": pip_version,
                "working_directory": wd,
                "virtual_env": venv_status,
                "config_files": [c.__dict__ for c in config_files],
                "config_values": config_values,
                "env_vars": env_vars,
                "index": index_info.__dict__,
                "cache_info": cache_info,
                "pip_debug": pip_debug,
                "last_command": last_command,
                "last_exit_code": last_exit_code,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
            return json.dumps(data, indent=2)

        if format == "markdown":
            lines = [
                "# pip-ui Diagnostics Report",
                "",
                f"Generated: {datetime.now().isoformat(timespec='seconds')}",
                "",
                "## Environment",
                "",
                f"- OS: `{os_info}`",
                f"- Python executable: `{self.python_path}`",
                f"- Python version: `{sys.version.splitlines()[0]}`",
                f"- Pip version: `{pip_version}`",
                f"- Working directory: `{wd}`",
                f"- VIRTUAL_ENV: `{venv_status['VIRTUAL_ENV']}`",
                f"- CONDA_PREFIX: `{venv_status['CONDA_PREFIX']}`",
                "",
                "## Config Files",
                "",
            ]
            if config_files:
                for c in config_files:
                    mod = c.modified or "-"
                    size = c.size if c.size is not None else "-"
                    lines.append(
                        f"- `{c.path}` ({c.scope}) - exists: {c.exists}, size: {size}, modified: {mod}"
                    )
            else:
                lines.append("_No config files reported._")
            lines += ["", "## Active Config Values", ""]
            if config_values:
                for k, v in config_values.items():
                    lines.append(f"- `{k}` = `{v}`")
            else:
                lines.append("_No configuration values found._")
            lines += ["", "## Index and Repository", ""]
            lines.append(f"- Main index: `{index_info.main_index_url or '(default)'}`")
            lines.append(f"- Extra indexes: {index_info.extra_index_urls or '(none)'}")
            lines.append(f"- No-index mode: {index_info.no_index}")
            lines.append(f"- Find-links: {index_info.find_links or '(none)'}")
            lines.append(f"- Trusted hosts: {index_info.trusted_hosts or '(none)'}")
            lines.append(f"- Credentials embedded in URLs: {index_info.has_credentials}")
            lines += ["", "## Environment Variables", ""]
            if env_vars:
                for k, v in env_vars.items():
                    lines.append(f"- `{k}` = `{v}`")
            else:
                lines.append("_No relevant environment variables found._")
            lines += ["", "## Last Command", ""]
            if last_command is not None:
                lines.append(f"- Command: `{last_command}`")
                lines.append(f"- Exit code: `{last_exit_code}`")
            else:
                lines.append("_No command has been run in this session._")
            lines += [
                "",
                "## Cache Info",
                "",
                "```",
                cache_info or "(no output)",
                "```",
                "",
                "## pip debug output",
                "",
                "```",
                pip_debug or "(no output)",
                "```",
            ]
            return "\n".join(lines)

        lines = [
            "pip-ui Diagnostics Report",
            "=" * 40,
            "",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            f"OS: {os_info}",
            f"Python executable: {self.python_path}",
            f"Python version: {sys.version.splitlines()[0]}",
            f"Pip version: {pip_version}",
            f"Working directory: {wd}",
            "",
            "Config files:",
        ]
        for c in config_files:
            lines.append(f"  {c.scope}: {c.path} exists={c.exists} size={c.size} modified={c.modified}")
        lines += ["", "Active configuration:"]
        for k, v in config_values.items():
            lines.append(f"  {k} = {v}")
        lines += ["", "Environment variables:"]
        for k, v in env_vars.items():
            lines.append(f"  {k} = {v}")
        lines += [
            "",
            "Index:",
            f"  main_index_url = {index_info.main_index_url}",
            f"  extra_index_urls = {index_info.extra_index_urls}",
            f"  trusted_hosts = {index_info.trusted_hosts}",
            f"  has_credentials = {index_info.has_credentials}",
        ]
        lines += ["", "Last command:", str(last_command), f"Exit: {last_exit_code}"]
        lines += ["", "pip debug:", pip_debug]
        return "\n".join(lines)


CONFIG_FILE_LINE_RE = re.compile(r"^\s*(global|user|site|env|virtualenv):\s*(.+)$", re.IGNORECASE)


def parse_config_list(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in stdout.splitlines():
        line = raw.strip()
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def parse_config_files(debug_output: str) -> list[ConfigFileInfo]:
    """Parse `pip config debug` output looking for file paths.

    pip config debug emits sections like:
      env_var:
         PIP_*
      env:
         <none>
      global:
         /etc/pip.conf, exists: False
      user:
         /home/u/.pip/pip.conf, exists: True
      site:
         /home/u/.venv/pip.conf, exists: False
    """
    files: list[ConfigFileInfo] = []
    current_scope: Optional[str] = None
    for raw in debug_output.splitlines():
        stripped = raw.rstrip()
        if not stripped:
            continue
        # Detect scope headers like "global:" at column 0.
        if not stripped.startswith(" ") and stripped.endswith(":"):
            current_scope = stripped[:-1].strip().lower()
            continue
        if current_scope is None or current_scope.startswith("env"):
            continue
        # The body lines often start with whitespace and contain a path.
        body = stripped.strip()
        # Lines like "/etc/pip.conf, exists: False"
        m = re.match(r"^(?P<path>.+?)(?:,\s*exists:\s*(?P<exists>True|False))?\s*$", body)
        if m and ("/" in m.group("path") or "\\" in m.group("path")):
            path = m.group("path").strip()
            exists_field = m.group("exists")
            file_exists = (exists_field == "True") if exists_field is not None else Path(path).exists()
            size: Optional[int] = None
            modified: Optional[str] = None
            try:
                if file_exists:
                    st = Path(path).stat()
                    size = st.st_size
                    modified = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
            except OSError:
                pass
            files.append(
                ConfigFileInfo(
                    path=path,
                    scope=current_scope,
                    exists=file_exists,
                    size=size,
                    modified=modified,
                )
            )
    return files
