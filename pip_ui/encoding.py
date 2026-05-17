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


def build_utf8_subprocess_env(
    base_env: MutableMapping[str, str] | None = None,
) -> MutableMapping[str, str]:
    """Return a process environment that defaults Python child I/O to UTF-8."""
    env = dict(os.environ if base_env is None else base_env)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", UTF8_ENCODING)
    return env


def utf8_subprocess_kwargs() -> dict[str, Any]:
    """Return text-mode subprocess kwargs that decode output as UTF-8."""
    return {
        "text": True,
        "encoding": UTF8_ENCODING,
        "errors": UTF8_SUBPROCESS_ERRORS,
        "env": build_utf8_subprocess_env(),
    }
