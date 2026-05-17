"""Modal dialog for editing pip global / advanced options.

The big Global Options block used to live inline on every command panel. It was
honking huge and rarely changed, so we moved it here and replaced the inline
block with a Settings button plus a compact chip-style summary of any values
that differ from their default.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk
from typing import Any, cast

from pip_ui.forms import GLOBAL_OPTIONS
from pip_ui.models import ArgSpec


class GlobalOptionsDialog(tk.Toplevel):
    """Modal Toplevel for editing the global pip options dictionary."""

    def __init__(
        self,
        parent: tk.Misc,
        values: dict[str, Any],
        on_apply: Callable[[dict[str, Any]], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.title("Global Options")
        self.transient(parent.winfo_toplevel())
        self.on_apply = on_apply
        self.result: dict[str, Any] | None = None
        self.vars: dict[str, tk.BooleanVar | tk.StringVar] = {}

        self.geometry("680x720")
        self.minsize(560, 600)
        self.build_ui(values)
        self.grab_set()

    def build_ui(self, values: dict[str, Any]) -> None:
        header = ttk.Frame(self, padding=8)
        header.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(
            header,
            text="Global / Advanced Options",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            header,
            text="These options are applied to every pip command. Empty fields are ignored.",
            foreground="gray",
            wraplength=560,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(2, 0))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(side=tk.TOP, fill=tk.X)

        # Pack the button row first (bottom) so it always reserves its space,
        # then a separator, then the scrollable body. This is the same pattern
        # used in the command form — without it the body claims everything and
        # the buttons get clipped on shorter screens.
        btns = ttk.Frame(self, padding=8)
        btns.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(btns, text="Reset", command=self.reset_defaults).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btns, text="OK", command=self.apply).pack(side=tk.RIGHT, padx=2)
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(side=tk.BOTTOM, fill=tk.X)

        body = ttk.Frame(self, padding=8)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        body.columnconfigure(1, weight=1)

        for row, arg in enumerate(GLOBAL_OPTIONS):
            self.add_field(body, arg, row, values.get(arg.name))

        self.bind("<Escape>", lambda _e: self.cancel())
        self.bind("<Return>", lambda _e: self.apply())

    def add_field(self, parent: tk.Widget, arg: ArgSpec, row: int, initial: Any) -> None:
        ttk.Label(parent, text=arg.label + ":").grid(row=row, column=0, sticky=tk.W, padx=4, pady=3)

        if arg.field_type == "checkbox":
            var: tk.BooleanVar | tk.StringVar = tk.BooleanVar(value=bool(initial))
            ttk.Checkbutton(parent, variable=cast(tk.BooleanVar, var)).grid(
                row=row, column=1, sticky=tk.W, padx=4, pady=3
            )
        elif arg.field_type in ("file", "dir"):
            var = tk.StringVar(value="" if initial in (None, "") else str(initial))
            wrap = ttk.Frame(parent)
            wrap.grid(row=row, column=1, sticky=tk.EW, padx=4, pady=3)
            entry = ttk.Entry(wrap, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            kind = arg.field_type

            def browse(
                field_kind: str = kind,
                target: tk.StringVar = var,
                label: str = arg.label,
            ) -> None:
                if field_kind == "file":
                    path = filedialog.askopenfilename(parent=self, title=f"Select {label}")
                else:
                    path = filedialog.askdirectory(parent=self, title=f"Select {label}")
                if path:
                    target.set(path)

            ttk.Button(wrap, text="Browse...", command=browse).pack(side=tk.LEFT, padx=(4, 0))
        else:
            var = tk.StringVar(value="" if initial in (None, "") else str(initial))
            ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky=tk.EW, padx=4, pady=3)

        ttk.Label(parent, text=arg.help, foreground="gray", wraplength=260).grid(
            row=row, column=2, sticky=tk.W, padx=4, pady=3
        )

        self.vars[arg.name] = var

    def collect(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for arg in GLOBAL_OPTIONS:
            var = self.vars[arg.name]
            if arg.field_type == "checkbox":
                out[arg.name] = bool(cast(tk.BooleanVar, var).get())
            else:
                value = cast(tk.StringVar, var).get().strip()
                out[arg.name] = value if value else None
        return out

    def reset_defaults(self) -> None:
        for arg in GLOBAL_OPTIONS:
            var = self.vars[arg.name]
            if arg.field_type == "checkbox":
                cast(tk.BooleanVar, var).set(bool(arg.default))
            else:
                cast(tk.StringVar, var).set("" if arg.default is None else str(arg.default))

    def apply(self) -> None:
        self.result = self.collect()
        self.on_apply(self.result)
        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()


def summarize_globals(values: dict[str, Any]) -> list[str]:
    """Return short chip-style strings for any non-default global option."""
    chips: list[str] = []
    for arg in GLOBAL_OPTIONS:
        v = values.get(arg.name)
        if arg.field_type == "checkbox":
            if bool(v) != bool(arg.default):
                chips.append(arg.label if v else f"!{arg.label}")
            continue
        if v in (None, ""):
            continue
        if str(v) == ("" if arg.default is None else str(arg.default)):
            continue
        text = str(v)
        if len(text) > 30:
            text = text[:27] + "..."
        chips.append(f"{arg.label}={text}")
    return chips
