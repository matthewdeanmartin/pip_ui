"""Shared helpers for localhost-only local-server integration tests."""

from __future__ import annotations

import importlib.util
import queue
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest

from pip_ui.encoding import utf8_subprocess_kwargs
from pip_ui.forms import build_argv_for_spec, parse_raw_extra, render_global_args
from pip_ui.runner import PipRunner
from pip_ui.tools import get_plugin

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Do NOT resolve() — on Linux the venv python is a symlink to the system python,
# and resolving it loses the venv context so installed extras like 'build' vanish.
REPO_PYTHON = Path(sys.executable)


@dataclass(frozen=True)
class CommandResult:
    """Captured result of a subprocess launched through the same runner path as the UI."""

    exit_code: int
    stdout: str
    stderr: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class LocalPypiServer:
    """Running pypiserver instance used by the integration tests."""

    url: str
    simple_url: str
    port: int
    packages_dir: Path
    argv: tuple[str, ...]
    log_path: Path


@dataclass(frozen=True)
class LocalDevpiServer:
    """Running devpi-server instance used by the integration tests."""

    url: str
    port: int
    server_dir: Path
    argv: tuple[str, ...]
    log_path: Path


def require_modules(*module_names: str) -> None:
    """Skip when the optional Python modules required by these tests are unavailable."""
    missing = [name for name in module_names if importlib.util.find_spec(name) is None]
    if missing:
        pytest.skip(f"Missing optional modules for localhost server tests: {', '.join(missing)}")


def resolve_interpreter_local_executable(name: str, python_path: Path = REPO_PYTHON) -> Path | None:
    """Resolve a CLI next to the selected interpreter, matching the GUI runner preference."""
    interp_dir = python_path.parent
    candidates = (
        interp_dir / name,
        interp_dir / f"{name}.exe",
        (interp_dir / ".." / "bin" / name).resolve(),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    found = shutil.which(name)
    return Path(found).resolve() if found is not None else None


def require_executables(*names: str) -> None:
    """Skip when optional CLI tools required by these tests are unavailable."""
    missing = [name for name in names if resolve_interpreter_local_executable(name) is None]
    if missing:
        pytest.skip(f"Missing optional executables for localhost server tests: {', '.join(missing)}")


def find_free_port() -> int:
    """Reserve and return a currently free localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def wait_for_url(url: str, timeout: float = 30.0) -> None:
    """Wait until *url* returns a successful HTTP response."""
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:  # nosec B310
                if 200 <= response.status < 500:
                    return
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise AssertionError(f"Timed out waiting for {url}: {last_error}")


def terminate_process(process: subprocess.Popen[str]) -> None:
    """Terminate a long-running child process with a kill fallback."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def default_values(plugin_name: str, spec_name: str) -> dict[str, object]:
    """Return the default field values for the requested plugin command."""
    plugin = get_plugin(plugin_name)
    assert plugin is not None, f"Plugin '{plugin_name}' is not registered"
    spec = plugin.command_specs[spec_name]
    values: dict[str, object] = {}
    for arg in spec.args:
        values[arg.name] = bool(arg.default) if arg.field_type == "checkbox" else arg.default
    return values


def build_gui_argv(
    plugin_name: str,
    spec_name: str,
    values: dict[str, object],
    *,
    python_path: Path = REPO_PYTHON,
    global_values: dict[str, object] | None = None,
    raw_extra: str = "",
) -> list[str]:
    """Build the full argv the same way the command form and main window do."""
    plugin = get_plugin(plugin_name)
    assert plugin is not None, f"Plugin '{plugin_name}' is not registered"
    spec = plugin.command_specs[spec_name]
    tool_argv = build_argv_for_spec(spec, values)
    if plugin_name == "pip" and global_values:
        tool_argv += render_global_args(global_values)
    if raw_extra:
        tool_argv += parse_raw_extra(raw_extra)
    return PipRunner().build_argv(str(python_path), tool_argv, plugin)


def run_gui_command(
    plugin_name: str,
    spec_name: str,
    values: dict[str, object],
    *,
    cwd: Path,
    python_path: Path = REPO_PYTHON,
    global_values: dict[str, object] | None = None,
    raw_extra: str = "",
    timeout: int = 180,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a UI-built command through PipRunner and capture its output."""
    plugin = get_plugin(plugin_name)
    assert plugin is not None, f"Plugin '{plugin_name}' is not registered"
    argv = build_gui_argv(
        plugin_name,
        spec_name,
        values,
        python_path=python_path,
        global_values=global_values,
        raw_extra=raw_extra,
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    done: queue.Queue[int] = queue.Queue()

    runner = PipRunner()
    runner.run(
        argv,
        cwd=str(cwd),
        on_stdout=stdout_lines.append,
        on_stderr=stderr_lines.append,
        on_done=done.put,
        env=env,
        strip_venv=plugin.run_via == "global_cli",
    )
    try:
        exit_code = done.get(timeout=timeout)
    except queue.Empty as exc:
        runner.cancel(force=True)
        raise AssertionError(f"Timed out after {timeout}s: {argv}") from exc

    return CommandResult(
        exit_code=exit_code,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
        argv=tuple(argv),
    )


def run_subprocess(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
    strip_venv: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a direct subprocess with the same UTF-8 defaults used by the app."""
    return subprocess.run(  # nosec B603
        argv,
        cwd=str(cwd),
        capture_output=True,
        timeout=timeout,
        check=False,
        shell=False,
        **utf8_subprocess_kwargs(strip_venv=strip_venv),
    )


def venv_python_path(venv_dir: Path) -> Path:
    """Return the interpreter path for a virtualenv (cross-platform)."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"
