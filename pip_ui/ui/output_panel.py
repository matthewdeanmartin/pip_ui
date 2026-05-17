"""Output panel with tabbed stdout/stderr/combined view."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any, cast

from pip_ui.ui.dialogs import save_file_dialog

MONO_FONT = ("Consolas", 10)


class OutputPanel(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_cancel: Callable[[bool], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.on_cancel = on_cancel
        self.running = False
        self.build_ui()

    def build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        ttk.Button(toolbar, text="Copy All", command=self.copy_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save...", command=self.save_output).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=2)

        self.cancel_btn = ttk.Button(toolbar, text="Cancel", command=self.request_cancel, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=2)
        self.kill_btn = ttk.Button(toolbar, text="Force Kill", command=self.request_kill, state=tk.DISABLED)
        self.kill_btn.pack(side=tk.LEFT, padx=2)

        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=(8, 2))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=2)
        search_entry.bind("<Return>", lambda e: self.search_output())
        ttk.Button(toolbar, text="Find", command=self.search_output).pack(side=tk.LEFT, padx=2)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        self.combined_text = self.make_text_tab("Combined")
        self.stdout_text = self.make_text_tab("stdout")
        self.stderr_text = self.make_text_tab("stderr")
        self.info_text = self.make_text_tab("Command Info")

        for widget in (self.combined_text, self.stderr_text):
            widget.tag_configure("stderr", foreground="red")
            widget.tag_configure("warning", foreground="#b06000")
            widget.tag_configure("hint", foreground="#0a5a0a")

    def make_text_tab(self, label: str) -> tk.Text:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=label)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text = tk.Text(
            frame,
            wrap=tk.WORD,
            font=MONO_FONT,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED,
        )
        text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)
        return text

    def append_to(self, widget: tk.Text, text: str, tag: str | None = None) -> None:
        widget.configure(state=tk.NORMAL)
        if tag:
            widget.insert(tk.END, text, tag)
        else:
            widget.insert(tk.END, text)
        widget.see(tk.END)
        widget.configure(state=tk.DISABLED)

    def append_stdout(self, text: str) -> None:
        self.append_to(self.stdout_text, text)
        self.append_to(self.combined_text, text)

    def append_stderr(self, text: str) -> None:
        self.append_to(self.stderr_text, text, "stderr")
        self.append_to(self.combined_text, text, "stderr")

    def append_combined(self, text: str, tag: str | None = None) -> None:
        self.append_to(self.combined_text, text, tag)

    def set_command_info(self, info_dict: dict[str, Any]) -> None:
        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        for key, value in info_dict.items():
            self.info_text.insert(tk.END, f"{key}: {value}\n")
        self.info_text.configure(state=tk.DISABLED)

    def append_command_info(self, info_dict: dict[str, Any]) -> None:
        self.info_text.configure(state=tk.NORMAL)
        for key, value in info_dict.items():
            self.info_text.insert(tk.END, f"{key}: {value}\n")
        self.info_text.configure(state=tk.DISABLED)

    def set_running(self, running: bool) -> None:
        self.running = running
        if running:
            self.cancel_btn.config(state=tk.NORMAL)
            self.kill_btn.config(state=tk.NORMAL)
        else:
            self.cancel_btn.config(state=tk.DISABLED)
            self.kill_btn.config(state=tk.DISABLED)

    def request_cancel(self) -> None:
        if self.on_cancel is not None:
            self.on_cancel(False)

    def request_kill(self) -> None:
        if self.on_cancel is not None:
            self.on_cancel(True)

    def clear(self) -> None:
        for widget in (self.combined_text, self.stdout_text, self.stderr_text, self.info_text):
            widget.configure(state=tk.NORMAL)
            widget.delete("1.0", tk.END)
            widget.configure(state=tk.DISABLED)

    def snapshot(self) -> dict[str, str]:
        """Return the current text in every tab so a caller can restore it later."""
        return {
            "combined": self.combined_text.get("1.0", tk.END),
            "stdout": self.stdout_text.get("1.0", tk.END),
            "stderr": self.stderr_text.get("1.0", tk.END),
            "info": self.info_text.get("1.0", tk.END),
        }

    def restore(self, snapshot: dict[str, str]) -> None:
        """Replace each tab's contents with the strings from snapshot()."""
        mapping = (
            ("combined", self.combined_text),
            ("stdout", self.stdout_text),
            ("stderr", self.stderr_text),
            ("info", self.info_text),
        )
        for key, widget in mapping:
            widget.configure(state=tk.NORMAL)
            widget.delete("1.0", tk.END)
            text = snapshot.get(key, "")
            if text.endswith("\n"):
                text = text[:-1]  # Text.get always tacks on a trailing newline
            widget.insert(tk.END, text)
            widget.configure(state=tk.DISABLED)

    def active_output_widget(self) -> tk.Text:
        widgets: list[tk.Text] = [self.combined_text, self.stdout_text, self.stderr_text, self.info_text]
        active_tab = self.notebook.index(self.notebook.select())  # type: ignore[no-untyped-call]
        return cast(tk.Text, widgets[active_tab])

    def copy_all(self) -> None:
        widget = self.active_output_widget()
        content = widget.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(content)

    def save_output(self) -> None:
        path = save_file_dialog(
            self,
            title="Save Output",
            default_name="pip_output.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            widget = self.active_output_widget()
            content = widget.get("1.0", tk.END)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)

    def search_output(self) -> None:
        term = self.search_var.get()
        if not term:
            return
        widget = self.active_output_widget()
        widget.tag_remove("search", "1.0", tk.END)
        widget.tag_configure("search", background="yellow")
        start = "1.0"
        while True:
            pos = widget.search(term, start, stopindex=tk.END)
            if not pos:
                break
            end = f"{pos}+{len(term)}c"
            widget.tag_add("search", pos, end)
            start = end
