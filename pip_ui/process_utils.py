"""Helpers for launching trusted executables with resolved paths."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def resolve_executable(name: str) -> str | None:
    """Resolve an executable from PATH to an absolute path."""
    path = shutil.which(name)
    if path is None:
        return None
    return str(Path(path).resolve())


def resolve_windows_shell() -> str | None:
    """Return the platform shell executable path on Windows."""
    comspec = os.environ.get("COMSPEC")
    if comspec and os.path.isabs(comspec):
        return comspec
    return resolve_executable("cmd.exe") or resolve_executable("cmd")
