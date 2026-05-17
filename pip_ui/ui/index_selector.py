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

_DEFAULT_LABEL = WELL_KNOWN_INDEXES[0][0]
_CUSTOM_SENTINEL = "<Add custom repo...>"
_MANAGE_SENTINEL = "<Manage custom repos...>"


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
        self._settings = settings
        self._on_change = on_change
        self._var = tk.StringVar()
        self._build_ui()
        self._reload_choices()
        self._var.trace_add("write", self._on_var_change)

    # ------------------------------------------------------------------ build

    def _build_ui(self) -> None:
        ttk.Label(self, text="Index:").pack(side=tk.LEFT, padx=(0, 2))
        self._combo = ttk.Combobox(self, textvariable=self._var, state="readonly", width=32)
        self._combo.pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------ data

    def _custom_repos(self) -> list[tuple[str, str]]:
        raw = self._settings.get("custom_indexes", [])
        if not isinstance(raw, list):
            return []
        result: list[tuple[str, str]] = []
        for item in raw:
            if isinstance(item, dict) and "label" in item and "url" in item:
                result.append((item["label"], item["url"]))
        return result

    def _save_custom_repos(self, repos: list[tuple[str, str]]) -> None:
        self._settings.set("custom_indexes", [{"label": lbl, "url": url} for lbl, url in repos])

    def _all_choices(self) -> list[tuple[str, str | None]]:
        choices: list[tuple[str, str | None]] = []
        for label, url in WELL_KNOWN_INDEXES:
            # First entry (PyPI default) maps to None — no flag injected.
            choices.append((label, url if label != _DEFAULT_LABEL else None))
        for label, url in self._custom_repos():
            choices.append((label, url))
        return choices

    def _reload_choices(self) -> None:
        choices = self._all_choices()
        display = [label for label, _ in choices] + [_CUSTOM_SENTINEL, _MANAGE_SENTINEL]
        current = self._var.get()
        self._combo.config(values=display)
        if current not in display:
            self._var.set(_DEFAULT_LABEL)
        # Restore previously saved selection from settings.
        saved = self._settings.get("active_index_label", _DEFAULT_LABEL)
        if saved in display:
            self._var.set(saved)

    # ------------------------------------------------------------------ events

    def _on_var_change(self, *_: Any) -> None:
        selected = self._var.get()
        if selected == _CUSTOM_SENTINEL:
            self._add_custom()
            return
        if selected == _MANAGE_SENTINEL:
            self._manage_custom()
            return
        url = self._url_for_label(selected)
        self._settings.set("active_index_label", selected)
        self._on_change(url)

    def _url_for_label(self, label: str) -> str | None:
        for lbl, url in self._all_choices():
            if lbl == label:
                return url
        return None

    # ----------------------------------------------------------------- dialogs

    def _add_custom(self) -> None:
        label = simpledialog.askstring("Custom Index — Label", "Display name for this index:", parent=self)
        if not label:
            self._var.set(_DEFAULT_LABEL)
            return
        url = simpledialog.askstring("Custom Index — URL", "Index URL (must end with /simple):", parent=self)
        if not url:
            self._var.set(_DEFAULT_LABEL)
            return
        url = url.strip().rstrip("/")
        repos = self._custom_repos()
        repos.append((label.strip(), url))
        self._save_custom_repos(repos)
        self._reload_choices()
        self._var.set(label.strip())

    def _manage_custom(self) -> None:
        repos = self._custom_repos()
        win = tk.Toplevel(self)
        win.title("Manage Custom Indexes")
        win.geometry("560x320")
        win.transient(self.winfo_toplevel())  # type: ignore[no-untyped-call]
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

        def _populate() -> None:
            for row in tree.get_children():
                tree.delete(row)
            for lbl, url in repos:
                tree.insert("", tk.END, values=(lbl, url))

        _populate()

        btn_row = ttk.Frame(win)
        btn_row.pack(fill=tk.X, padx=8, pady=4)

        def _delete() -> None:
            sel = tree.selection()
            if not sel:
                return
            idx = tree.index(sel[0])
            repos.pop(idx)
            _populate()

        ttk.Button(btn_row, text="Delete Selected", command=_delete).pack(side=tk.LEFT, padx=2)

        def _close() -> None:
            self._save_custom_repos(repos)
            self._reload_choices()
            win.destroy()
            self._var.set(_DEFAULT_LABEL)

        ttk.Button(btn_row, text="Close", command=_close).pack(side=tk.RIGHT, padx=2)
        win.protocol("WM_DELETE_WINDOW", _close)

    # ----------------------------------------------------------------- public

    def current_index_url(self) -> str | None:
        """Return the active ``--index-url`` value, or ``None`` for the default."""
        selected = self._var.get()
        if selected in (_CUSTOM_SENTINEL, _MANAGE_SENTINEL):
            return None
        return self._url_for_label(selected)
