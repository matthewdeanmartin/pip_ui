"""Tool tab row widget — displayed above the interpreter picker."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from pip_ui.tools import ToolPlugin, get_plugin, get_registry
from pip_ui.ui.dialogs import info_dialog


class ToolSwitcher(ttk.Frame):
    """A row of toggle buttons, one per registered tool plugin.

    Available tools are active; unavailable ones are greyed out and show an
    install hint when clicked.
    """

    def __init__(
        self,
        parent: tk.Misc,
        on_switch: Callable[[ToolPlugin], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.on_switch = on_switch
        self._buttons: dict[str, ttk.Button] = {}
        self._available: dict[str, bool] = {}
        self._active_name: str = "pip"
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Tool:").pack(side=tk.LEFT, padx=(4, 2))
        for plugin in get_registry():
            btn = ttk.Button(
                self,
                text=plugin.label,
                command=self._make_click_handler(plugin),
                width=len(plugin.label) + 2,
            )
            btn.pack(side=tk.LEFT, padx=1, pady=1)
            self._buttons[plugin.name] = btn
            # Start all non-pip tools as unavailable until detection completes.
            self._available[plugin.name] = plugin.name == "pip"
        self._refresh_states()

    def _make_click_handler(self, plugin: ToolPlugin) -> Callable[[], None]:
        def on_click() -> None:
            self._on_click(plugin)

        return on_click

    def _on_click(self, plugin: ToolPlugin) -> None:
        if not self._available.get(plugin.name, False):
            extra = plugin.extra or plugin.name
            info_dialog(
                self,
                f"{plugin.label} not found",
                f"{plugin.label} is not installed or not detectable.\n\n"
                f"Install it with:\n\n    pip install pip-ui-tkinter[{extra}]\n\n"
                f"Then restart pip-ui.",
            )
            return
        self._active_name = plugin.name
        self._refresh_states()
        self.on_switch(plugin)

    def set_available(self, plugin_name: str, available: bool) -> None:
        """Update availability state for a plugin (call via after() from background thread)."""
        self._available[plugin_name] = available
        self._refresh_states()

    def select(self, plugin_name: str) -> None:
        """Programmatically select a tool tab (restores from settings on startup)."""
        plugin = get_plugin(plugin_name)
        if plugin is not None and self._available.get(plugin_name, False):
            self._active_name = plugin_name
            self._refresh_states()
            self.on_switch(plugin)

    def _refresh_states(self) -> None:
        for name, btn in self._buttons.items():
            available = self._available.get(name, False)
            is_active = name == self._active_name
            if is_active:
                btn.config(style="Active.TButton")
            elif available:
                btn.config(style="TButton")
            else:
                btn.config(style="Disabled.TButton")

    @staticmethod
    def configure_styles(root: tk.Tk) -> None:
        """Register the Active and Disabled button styles once on the root window."""
        style = ttk.Style(root)
        style.configure("Active.TButton", relief="sunken", foreground="black")
        style.configure("Disabled.TButton", foreground="#999999")
