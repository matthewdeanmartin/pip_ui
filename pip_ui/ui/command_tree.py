"""Command tree panel with search and grouping."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from pip_ui.command_specs import COMMAND_GROUPS, get_commands_by_group


class CommandTree(ttk.Frame):
    def __init__(self, parent: tk.Widget, on_select: Callable[[str], None], **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.on_select = on_select
        self.group_ids: dict[str, str] = {}
        self.item_to_command: dict[str, str] = {}
        self.build_ui()

    def build_ui(self) -> None:
        search_frame = ttk.Frame(self)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.filter_commands())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        scrollbar = ttk.Scrollbar(self)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            self,
            yscrollcommand=scrollbar.set,
            selectmode="browse",
            show="tree",
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        scrollbar.config(command=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        self.populate_tree()

    def populate_tree(self, filter_text: str = "") -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.group_ids = {}
        self.item_to_command = {}

        commands_by_group = get_commands_by_group()
        ft = filter_text.lower().strip()

        for group in COMMAND_GROUPS:
            specs = commands_by_group.get(group, [])
            matching = [
                s
                for s in specs
                if not ft or ft in s.name.lower() or ft in s.label.lower() or ft in s.description.lower()
            ]
            if not matching:
                continue
            group_id = self.tree.insert("", tk.END, text=group, open=bool(ft))
            self.group_ids[group] = group_id
            for spec in matching:
                item_id = self.tree.insert(group_id, tk.END, text=spec.label)
                self.item_to_command[item_id] = spec.name

    def filter_commands(self) -> None:
        self.populate_tree(self.search_var.get())

    def on_tree_select(self, event: Any) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        command_name = self.item_to_command.get(item_id)
        if command_name:
            self.on_select(command_name)

    def focus_search(self) -> None:
        self.search_var.set("")
