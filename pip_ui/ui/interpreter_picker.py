"""Interpreter selection widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from pip_ui.environment import InterpreterDiscovery
from pip_ui.models import InterpreterInfo


class InterpreterPicker(ttk.Frame):
    def __init__(
        self, parent: tk.Widget, on_change: Callable[[Optional[InterpreterInfo]], None], **kwargs: Any
    ) -> None:
        super().__init__(parent, **kwargs)
        self.on_change = on_change
        self.interpreters: list[InterpreterInfo] = []
        self.selected: Optional[InterpreterInfo] = None
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        ttk.Label(self, text="Python:").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.combo_var, state="readonly", width=50)
        self.combo.pack(side=tk.LEFT, padx=2)
        self.combo.bind("<<ComboboxSelected>>", self.on_combo_select)
        ttk.Button(self, text="Browse...", command=self.browse).pack(side=tk.LEFT, padx=2)
        ttk.Button(self, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=2)

    def refresh(self) -> None:
        discovery = InterpreterDiscovery()
        self.interpreters = discovery.discover()
        labels = [i.display_label() for i in self.interpreters]
        self.combo["values"] = labels
        if self.interpreters:
            self.combo.current(0)
            self.selected = self.interpreters[0]
            self.on_change(self.selected)

    def on_combo_select(self, event: Any) -> None:
        idx = self.combo.current()
        if 0 <= idx < len(self.interpreters):
            self.selected = self.interpreters[idx]
            self.on_change(self.selected)

    def browse(self) -> None:
        from pip_ui.environment import InterpreterDiscovery
        from pip_ui.ui.dialogs import browse_interpreter_dialog

        path = browse_interpreter_dialog(self)
        if not path:
            return
        discovery = InterpreterDiscovery()
        info = discovery.validate(path)
        if info is None:
            from pip_ui.ui.dialogs import error_dialog

            error_dialog(self, "Invalid Interpreter", f"Could not validate Python interpreter at:\n{path}")
            return
        self.interpreters.append(info)
        labels = [i.display_label() for i in self.interpreters]
        self.combo["values"] = labels
        self.combo.current(len(self.interpreters) - 1)
        self.selected = info
        self.on_change(self.selected)

    def get_selected(self) -> Optional[InterpreterInfo]:
        return self.selected

    def set_from_path(self, path: str) -> None:
        for i, info in enumerate(self.interpreters):
            if info.path == path:
                self.combo.current(i)
                self.selected = info
                self.on_change(self.selected)
                return
