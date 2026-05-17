"""Common dialog utilities."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox


def confirm_dialog(parent: tk.Misc, title: str, message: str) -> bool:
    return messagebox.askyesno(title, message, parent=parent)


def error_dialog(parent: tk.Misc, title: str, message: str) -> None:
    messagebox.showerror(title, message, parent=parent)


def info_dialog(parent: tk.Misc, title: str, message: str) -> None:
    messagebox.showinfo(title, message, parent=parent)


def save_file_dialog(
    parent: tk.Misc,
    title: str,
    default_name: str,
    filetypes: list[tuple[str, str]],
) -> str | None:
    path = filedialog.asksaveasfilename(
        parent=parent,
        title=title,
        initialfile=default_name,
        filetypes=filetypes,
        defaultextension=filetypes[0][1] if filetypes else "",
    )
    return path if path else None


def browse_interpreter_dialog(parent: tk.Misc) -> str | None:
    if sys.platform == "win32":
        filetypes = [("Python Executable", "python.exe"), ("All files", "*")]
    else:
        filetypes = [("Python Executable", "python*"), ("All files", "*")]
    path = filedialog.askopenfilename(
        parent=parent,
        title="Select Python Interpreter",
        filetypes=filetypes,
    )
    return path if path else None
