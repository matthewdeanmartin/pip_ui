"""Tests for data models."""

from __future__ import annotations

from pip_ui.models import InterpreterInfo


def test_interpreter_info_display_label_system() -> None:
    info = InterpreterInfo(
        path="/usr/bin/python3",
        version="3.12.0",
        pip_version="23.3",
        is_venv=False,
        prefix="/usr",
        base_prefix="/usr",
        env_type="system",
    )
    assert info.display_label() == "/usr/bin/python3 (3.12.0, pip 23.3)"


def test_interpreter_info_display_label_venv() -> None:
    info = InterpreterInfo(
        path="/home/user/project/.venv/bin/python",
        version="3.12.0",
        pip_version="23.3",
        is_venv=True,
        prefix="/home/user/project/.venv",
        base_prefix="/usr",
        env_type="venv",
    )
    assert info.display_label() == "/home/user/project/.venv/bin/python (3.12.0, pip 23.3) [venv]"
