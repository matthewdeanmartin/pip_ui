"""Tests for simple dialog wrapper helpers."""

from __future__ import annotations

import sys
from typing import cast

import pytest

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    from pip_ui.ui import dialogs
except ModuleNotFoundError:
    pytest.skip("tkinter not installed", allow_module_level=True)


def test_confirm_dialog_passes_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """confirm_dialog should forward title, message, and parent."""
    seen: dict[str, object] = {}

    def fake_askyesno(title: str, message: str, *, parent: object) -> bool:
        seen["title"] = title
        seen["message"] = message
        seen["parent"] = parent
        return True

    monkeypatch.setattr(messagebox, "askyesno", fake_askyesno)

    parent = cast(tk.Misc, object())
    assert dialogs.confirm_dialog(parent, "Confirm", "Proceed?") is True
    assert seen == {"title": "Confirm", "message": "Proceed?", "parent": parent}


def test_error_and_info_dialogs_forward_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """error_dialog and info_dialog should call the expected messagebox helpers."""
    calls: list[tuple[str, str, str, object]] = []

    def fake_showerror(title: str, message: str, *, parent: object) -> None:
        calls.append(("error", title, message, parent))

    def fake_showinfo(title: str, message: str, *, parent: object) -> None:
        calls.append(("info", title, message, parent))

    monkeypatch.setattr(messagebox, "showerror", fake_showerror)
    monkeypatch.setattr(messagebox, "showinfo", fake_showinfo)

    parent = cast(tk.Misc, object())
    dialogs.error_dialog(parent, "Oops", "Bad news")
    dialogs.info_dialog(parent, "Heads up", "Good news")

    assert calls == [
        ("error", "Oops", "Bad news", parent),
        ("info", "Heads up", "Good news", parent),
    ]


def test_save_file_dialog_returns_selected_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """save_file_dialog should return the selected path and default extension."""
    seen: dict[str, object] = {}

    def fake_asksaveasfilename(**kwargs: object) -> str:
        seen.update(kwargs)
        return "C:\\tmp\\report.txt"

    monkeypatch.setattr(filedialog, "asksaveasfilename", fake_asksaveasfilename)

    parent = cast(tk.Misc, object())
    filetypes = [("Text", ".txt"), ("All files", "*")]
    result = dialogs.save_file_dialog(parent, "Save Report", "report.txt", filetypes)

    assert result == "C:\\tmp\\report.txt"
    assert seen["parent"] is parent
    assert seen["title"] == "Save Report"
    assert seen["initialfile"] == "report.txt"
    assert seen["filetypes"] == filetypes
    assert seen["defaultextension"] == ".txt"


def test_save_file_dialog_returns_none_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cancelling save_file_dialog should return None."""
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kwargs: "")

    parent = cast(tk.Misc, object())
    assert dialogs.save_file_dialog(parent, "Save", "report.txt", [("Text", ".txt")]) is None


def test_browse_interpreter_dialog_uses_windows_filetypes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows interpreter browsing should prefer python.exe."""
    seen: dict[str, object] = {}

    def fake_askopenfilename(**kwargs: object) -> str:
        seen.update(kwargs)
        return "C:\\Python313\\python.exe"

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(filedialog, "askopenfilename", fake_askopenfilename)

    parent = cast(tk.Misc, object())
    result = dialogs.browse_interpreter_dialog(parent)

    assert result == "C:\\Python313\\python.exe"
    assert seen["parent"] is parent
    assert seen["title"] == "Select Python Interpreter"
    assert seen["filetypes"] == [("Python Executable", "python.exe"), ("All files", "*")]


def test_browse_interpreter_dialog_returns_none_when_cancelled_on_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-Windows interpreter browsing should use python* and return None on cancel."""
    seen: dict[str, object] = {}

    def fake_askopenfilename(**kwargs: object) -> str:
        seen.update(kwargs)
        return ""

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(filedialog, "askopenfilename", fake_askopenfilename)

    parent = cast(tk.Misc, object())
    assert dialogs.browse_interpreter_dialog(parent) is None
    assert seen["filetypes"] == [("Python Executable", "python*"), ("All files", "*")]
