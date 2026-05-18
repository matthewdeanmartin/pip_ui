"""PipxPythonPicker — Python selector for pipx (path only, no pip version)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from pip_ui.environment import InterpreterDiscovery
from pip_ui.models import InterpreterInfo


class PipxPythonPicker(ttk.Frame):
    """Dropdown showing discovered Python interpreters for use with pipx --python."""

    def __init__(
        self,
        parent: tk.Misc,
        on_change: Callable[[str | None], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_change = on_change
        self._interpreters: list[InterpreterInfo] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        ttk.Label(self, text="pipx Python:").pack(side=tk.LEFT, padx=(0, 4))
        self._var = tk.StringVar()
        self._combo = ttk.Combobox(self, textvariable=self._var, state="readonly", width=45)
        self._combo.pack(side=tk.LEFT, padx=2)
        self._combo.bind("<<ComboboxSelected>>", self._on_select)
        ttk.Button(self, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=2)

    def refresh(self) -> None:
        discovery = InterpreterDiscovery()
        self._interpreters = discovery.discover()
        labels = ["(pipx default)", *[f"{i.path} ({i.version})" for i in self._interpreters]]
        self._combo["values"] = labels
        self._combo.current(0)
        self._on_change(None)

    def get_python_path(self) -> str | None:
        idx = self._combo.current()
        if idx <= 0:
            return None
        actual_idx = idx - 1
        if 0 <= actual_idx < len(self._interpreters):
            return self._interpreters[actual_idx].path
        return None

    def _on_select(self, _event: Any) -> None:
        self._on_change(self.get_python_path())
