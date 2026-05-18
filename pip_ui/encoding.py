"""UTF-8 defaults for console and subprocess I/O."""

from __future__ import annotations

import os
import sys
from collections.abc import MutableMapping
from typing import Any

UTF8_ENCODING = "utf-8"
UTF8_OUTPUT_ERRORS = "backslashreplace"
UTF8_SUBPROCESS_ERRORS = "replace"


def configure_utf8_stdio() -> None:
    """Prefer UTF-8 for CLI output streams when reconfiguration is available."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding=UTF8_ENCODING, errors=UTF8_OUTPUT_ERRORS)


# Variables that describe the *current* virtual environment. Passing these to a
# subprocess that runs a *different* Python (e.g. a pipx-managed interpreter or
# a global CLI tool) causes that Python to load the wrong stdlib, producing
# errors like "SRE module mismatch". Strip them when spawning global-CLI tools.
_VENV_ENV_VARS = ("VIRTUAL_ENV", "VIRTUAL_ENV_PROMPT", "PYTHONHOME", "PYTHONPATH")


def build_utf8_subprocess_env(
    base_env: MutableMapping[str, str] | None = None,
    strip_venv: bool = False,
) -> MutableMapping[str, str]:
    """Return a process environment that defaults Python child I/O to UTF-8.

    When *strip_venv* is True the venv-poisoning variables (VIRTUAL_ENV,
    PYTHONHOME, PYTHONPATH) are removed so that a subprocess running a
    different Python interpreter is not redirected to the wrong stdlib.
    """
    env = dict(os.environ if base_env is None else base_env)
    if strip_venv:
        for key in _VENV_ENV_VARS:
            env.pop(key, None)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", UTF8_ENCODING)
    return env


def utf8_subprocess_kwargs(strip_venv: bool = False) -> dict[str, Any]:
    """Return text-mode subprocess kwargs that decode output as UTF-8."""
    return {
        "text": True,
        "encoding": UTF8_ENCODING,
        "errors": UTF8_SUBPROCESS_ERRORS,
        "env": build_utf8_subprocess_env(strip_venv=strip_venv),
    }
