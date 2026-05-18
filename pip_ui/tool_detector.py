"""Two-tier tool detection: global PATH + interpreter-local probes."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import threading
from collections.abc import Callable

from pip_ui.models import InterpreterInfo
from pip_ui.tools import ToolPlugin, get_registry


def _which_in_interpreter(interpreter: InterpreterInfo, exe_name: str) -> str | None:
    """Return the path to exe_name inside the interpreter's Scripts/bin dir, or None."""
    interp_dir = os.path.dirname(interpreter.path)
    candidates = [
        os.path.join(interp_dir, exe_name),
        os.path.join(interp_dir, exe_name + ".exe"),
        os.path.join(interp_dir, "..", "bin", exe_name),
    ]
    for c in candidates:
        normalized = os.path.normpath(c)
        if os.path.isfile(normalized) and os.access(normalized, os.X_OK):
            return normalized
    return None


def _probe_module(interpreter_path: str, module_name: str) -> bool:
    """Return True if the given module can be imported by interpreter_path."""
    try:
        result = subprocess.run(
            [interpreter_path, "-c", f"import {module_name}"],
            capture_output=True,
            timeout=5,
            check=False,
            shell=False,
        )  # nosec B603
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def is_available(plugin: ToolPlugin, interpreter: InterpreterInfo | None) -> bool:
    """Return True if the plugin's tool is usable in the current environment."""
    if plugin.name == "pip":
        return True

    if plugin.run_via == "python_module":
        if interpreter is not None and _probe_module(interpreter.path, plugin.module):
            return True
        # Fallback: try the system python
        system_python = shutil.which("python") or shutil.which("python3")
        return bool(system_python and _probe_module(system_python, plugin.module))

    # global_cli tools
    if interpreter is not None:
        local = _which_in_interpreter(interpreter, plugin.executable)
        if local:
            return True
    return bool(shutil.which(plugin.executable))


def detect_all_tools(
    interpreter: InterpreterInfo | None,
    on_result: Callable[[str, bool], None],
    on_done: Callable[[], None] | None = None,
) -> None:
    """Run availability probes for all plugins in a background thread.

    on_result(plugin_name, available) is called for each plugin as results
    arrive. on_done() is called after all probes complete.
    Use tk.after() inside on_result to safely update the UI.
    """

    def worker() -> None:
        for plugin in get_registry():
            available = is_available(plugin, interpreter)
            on_result(plugin.name, available)
        if on_done is not None:
            on_done()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
