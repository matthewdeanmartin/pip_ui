"""Top-bar dropdown for selecting a requirements file.

Detected files in the current working directory are shown in a combobox. The
choice propagates to per-command forms that accept ``-r``; the user can still
override the value at the command level.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk
from typing import Any

from pip_ui.requirements_detect import RequirementsCandidate, detect_candidates

NONE_LABEL = "(none)"


class RequirementsPicker(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_change: Callable[[str | None], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.on_change = on_change
        self.candidates: list[RequirementsCandidate] = []
        self.labels: list[str] = []
        self.directory: Path = Path.cwd()
        self.build_ui()

    def build_ui(self) -> None:
        ttk.Label(self, text="Requirements:").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_var = tk.StringVar(value=NONE_LABEL)
        self.combo = ttk.Combobox(self, textvariable=self.combo_var, state="readonly", width=32)
        self.combo.pack(side=tk.LEFT, padx=2)
        self.combo.bind("<<ComboboxSelected>>", self.on_combo_select)
        ttk.Button(self, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=2)

    def set_directory(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.refresh()

    def refresh(self) -> None:
        previous = self.combo_var.get()
        self.candidates = detect_candidates(self.directory)
        self.labels = [NONE_LABEL, *(c.label for c in self.candidates)]
        self.combo["values"] = self.labels

        # Auto-select when there's exactly one requirements-style file (we
        # ignore a pyproject.toml that just happens to live alongside it,
        # since it's a different kind of artifact).
        auto = [c for c in self.candidates if c.kind in ("requirements", "heuristic")]
        if previous == NONE_LABEL and len(auto) == 1:
            chosen = auto[0]
            self.combo_var.set(chosen.label)
            self.on_change(str(chosen.path))
            return

        # Preserve prior selection by label when still available; otherwise reset.
        if previous not in self.labels:
            self.combo_var.set(NONE_LABEL)
            self.on_change(None)

    def on_combo_select(self, _event: Any) -> None:
        idx = self.combo.current()
        if idx <= 0 or (idx - 1) >= len(self.candidates):
            self.on_change(None)
            return
        chosen = self.candidates[idx - 1]
        self.on_change(str(chosen.path))

    def get_selected_path(self) -> str | None:
        idx = self.combo.current()
        if idx <= 0 or (idx - 1) >= len(self.candidates):
            return None
        return str(self.candidates[idx - 1].path)
