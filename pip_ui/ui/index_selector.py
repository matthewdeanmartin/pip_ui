"""Index/repository selector widget.

Provides a labeled combobox pre-populated with well-known indexes plus any
custom repos stored in settings.  Selecting a value adjusts the --index-url
that gets merged into pip commands.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import simpledialog, ttk
from typing import Any

WELL_KNOWN_INDEXES: list[tuple[str, str]] = [
    ("PyPI (default)", "https://pypi.org/simple"),
    ("PyPI Test", "https://test.pypi.org/simple"),
    ("piwheels (Raspberry Pi)", "https://www.piwheels.org/simple"),
]

DEFAULT_LABEL = WELL_KNOWN_INDEXES[0][0]
CUSTOM_SENTINEL = "<Add custom repo...>"
MANAGE_SENTINEL = "<Manage custom repos...>"


class IndexSelector(ttk.Frame):
    """Combobox + button for choosing the active package index.

    Emits ``on_change(url_or_none)`` whenever the selection changes.
    *url_or_none* is ``None`` when the default PyPI is selected (so no
    ``--index-url`` flag is injected).
    """

    def __init__(
        self,
        parent: tk.Misc,
        settings: Any,
        on_change: Callable[[str | None], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.settings = settings
        self.on_change = on_change
        self.var = tk.StringVar()
        self.build_ui()
        self.reload_choices()
        self.var.trace_add("write", self.on_var_change)

    # ------------------------------------------------------------------ build

    def build_ui(self) -> None:
        ttk.Label(self, text="Index:").pack(side=tk.LEFT, padx=(0, 2))
        self.combo = ttk.Combobox(self, textvariable=self.var, state="readonly", width=32)
        self.combo.pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------ data

    def custom_repos(self) -> list[tuple[str, str]]:
        raw = self.settings.get("custom_indexes", [])
        if not isinstance(raw, list):
            return []
        result: list[tuple[str, str]] = []
        for item in raw:
            if isinstance(item, dict) and "label" in item and "url" in item:
                result.append((item["label"], item["url"]))
        return result

    def save_custom_repos(self, repos: list[tuple[str, str]]) -> None:
        self.settings.set("custom_indexes", [{"label": lbl, "url": url} for lbl, url in repos])

    def all_choices(self) -> list[tuple[str, str | None]]:
        choices: list[tuple[str, str | None]] = []
        for label, url in WELL_KNOWN_INDEXES:
            # First entry (PyPI default) maps to None — no flag injected.
            choices.append((label, url if label != DEFAULT_LABEL else None))
        for label, url in self.custom_repos():
            choices.append((label, url))
        return choices

    def reload_choices(self) -> None:
        choices = self.all_choices()
        display = [label for label, _ in choices] + [CUSTOM_SENTINEL, MANAGE_SENTINEL]
        current = self.var.get()
        self.combo.config(values=display)
        if current not in display:
            self.var.set(DEFAULT_LABEL)
        # Restore previously saved selection from settings.
        saved = self.settings.get("active_index_label", DEFAULT_LABEL)
        if saved in display:
            self.var.set(saved)

    # ------------------------------------------------------------------ events

    def on_var_change(self, *_: Any) -> None:
        selected = self.var.get()
        if selected == CUSTOM_SENTINEL:
            self.add_custom()
            return
        if selected == MANAGE_SENTINEL:
            self.manage_custom()
            return
        url = self.url_for_label(selected)
        self.settings.set("active_index_label", selected)
        self.on_change(url)

    def url_for_label(self, label: str) -> str | None:
        for lbl, url in self.all_choices():
            if lbl == label:
                return url
        return None

    # ----------------------------------------------------------------- dialogs

    def add_custom(self) -> None:
        label = simpledialog.askstring("Custom Index — Label", "Display name for this index:", parent=self)
        if not label:
            self.var.set(DEFAULT_LABEL)
            return
        url = simpledialog.askstring("Custom Index — URL", "Index URL (must end with /simple):", parent=self)
        if not url:
            self.var.set(DEFAULT_LABEL)
            return
        url = url.strip().rstrip("/")
        repos = self.custom_repos()
        repos.append((label.strip(), url))
        self.save_custom_repos(repos)
        self.reload_choices()
        self.var.set(label.strip())

    def manage_custom(self) -> None:
        repos = self.custom_repos()
        win = tk.Toplevel(self)
        win.title("Manage Custom Indexes")
        win.geometry("560x320")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        ttk.Label(win, text="Custom package indexes (name → URL)").pack(anchor=tk.W, padx=8, pady=(8, 2))

        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ("Label", "URL")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=8)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=200)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        def populate() -> None:
            for row in tree.get_children():
                tree.delete(row)
            for lbl, url in repos:
                tree.insert("", tk.END, values=(lbl, url))

        populate()

        btn_row = ttk.Frame(win)
        btn_row.pack(fill=tk.X, padx=8, pady=4)

        def delete() -> None:
            sel = tree.selection()
            if not sel:
                return
            idx = tree.index(sel[0])
            repos.pop(idx)
            populate()

        ttk.Button(btn_row, text="Delete Selected", command=delete).pack(side=tk.LEFT, padx=2)

        def close() -> None:
            self.save_custom_repos(repos)
            self.reload_choices()
            win.destroy()
            self.var.set(DEFAULT_LABEL)

        ttk.Button(btn_row, text="Close", command=close).pack(side=tk.RIGHT, padx=2)
        win.protocol("WM_DELETE_WINDOW", close)

    # ----------------------------------------------------------------- public

    def current_index_url(self) -> str | None:
        """Return the active ``--index-url`` value, or ``None`` for the default."""
        selected = self.var.get()
        if selected in (CUSTOM_SENTINEL, MANAGE_SENTINEL):
            return None
        return self.url_for_label(selected)
