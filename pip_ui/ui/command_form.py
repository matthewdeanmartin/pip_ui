"""Dynamic form generated from CommandSpec."""

from __future__ import annotations

import json
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, simpledialog, ttk
from typing import Any, cast

from pip_ui.forms import (
    GLOBAL_OPTIONS,
    build_argv_for_spec,
    parse_raw_extra,
    render_global_args,
)
from pip_ui.models import ArgSpec, CommandSpec
from pip_ui.presets import PresetStore
from pip_ui.runner import PipRunner
from pip_ui.ui.dialogs import info_dialog
from pip_ui.ui.global_options_dialog import summarize_globals

MONO_FONT = ("Consolas", 10)

# Field name on per-command forms that means "requirements file". When the user
# picks a global requirements file in the toolbar, we propagate it onto these
# fields (which the user can still override per command).
REQUIREMENTS_FIELD_NAME = "requirements_file"


def default_global_values() -> dict[str, Any]:
    """Return a values dict matching every GLOBAL_OPTIONS default."""
    return {arg.name: arg.default for arg in GLOBAL_OPTIONS}


class FieldWidget:
    def __init__(self, arg: ArgSpec, parent: tk.Misc) -> None:
        self.arg = arg
        self.var: tk.BooleanVar | tk.StringVar
        self.widget: tk.Widget

        if arg.field_type == "checkbox":
            self.var = tk.BooleanVar(value=bool(arg.default))
            self.widget = ttk.Checkbutton(parent, variable=self.var)
        elif arg.field_type == "dropdown":
            initial = str(arg.default) if arg.default is not None else (arg.choices[0] if arg.choices else "")
            self.var = tk.StringVar(value=initial)
            self.widget = ttk.Combobox(parent, textvariable=self.var, values=arg.choices, state="readonly")
        elif arg.field_type in ("file", "dir"):
            self.var = tk.StringVar(value=str(arg.default) if arg.default is not None else "")
            frame = ttk.Frame(parent)
            entry = ttk.Entry(frame, textvariable=self.var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if arg.field_type == "file":
                ttk.Button(frame, text="Browse...", command=self.browse_file).pack(side=tk.LEFT)
            else:
                ttk.Button(frame, text="Browse...", command=self.browse_dir).pack(side=tk.LEFT)
            self.widget = frame
        elif arg.field_type == "multi":
            self.var = tk.StringVar(value=str(arg.default) if arg.default is not None else "")
            self.widget = ttk.Entry(parent, textvariable=self.var)
        else:
            self.var = tk.StringVar(value=str(arg.default) if arg.default is not None else "")
            self.widget = ttk.Entry(parent, textvariable=self.var)

    def browse_file(self) -> None:
        path = filedialog.askopenfilename(title=f"Select {self.arg.label}")
        if path:
            cast(tk.StringVar, self.var).set(path)

    def browse_dir(self) -> None:
        path = filedialog.askdirectory(title=f"Select {self.arg.label}")
        if path:
            cast(tk.StringVar, self.var).set(path)

    def get_value(self) -> Any:
        if self.arg.field_type == "checkbox":
            return cast(tk.BooleanVar, self.var).get()
        val = cast(tk.StringVar, self.var).get()
        return val if val else None

    def set_value(self, value: Any) -> None:
        if self.arg.field_type == "checkbox":
            cast(tk.BooleanVar, self.var).set(bool(value))
        else:
            cast(tk.StringVar, self.var).set("" if value is None else str(value))

    def reset(self) -> None:
        if self.arg.field_type == "checkbox":
            cast(tk.BooleanVar, self.var).set(bool(self.arg.default))
        elif self.arg.field_type == "dropdown":
            default = (
                str(self.arg.default)
                if self.arg.default is not None
                else (self.arg.choices[0] if self.arg.choices else "")
            )
            cast(tk.StringVar, self.var).set(default)
        else:
            cast(tk.StringVar, self.var).set(str(self.arg.default) if self.arg.default is not None else "")

    def trace(self, callback: Callable[[], None]) -> None:
        self.var.trace_add("write", lambda *a: callback())


class CommandForm(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_run: Callable[[list[str], str], None],
        on_form_change: Callable[[], None] | None = None,
        global_values_provider: Callable[[], dict[str, Any]] | None = None,
        on_open_global_options: Callable[[], None] | None = None,
        global_requirements_provider: Callable[[], str | None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.on_run = on_run
        self.on_form_change = on_form_change
        self.global_values_provider = global_values_provider or default_global_values
        self.on_open_global_options = on_open_global_options
        self.global_requirements_provider = global_requirements_provider or (lambda: None)
        self.spec: CommandSpec | None = None
        self.field_widgets: list[FieldWidget] = []
        self.raw_extra_var = tk.StringVar(value="")
        self.presets = PresetStore()
        self.build_ui()

    def build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        self.title_label = ttk.Label(header, text="Select a command", font=("TkDefaultFont", 12, "bold"))
        self.title_label.pack(anchor=tk.W)
        self.desc_label = ttk.Label(header, text="", wraplength=500, justify=tk.LEFT)
        self.desc_label.pack(anchor=tk.W)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        # Pack the bottom strip first (bottom → up) so it reserves its space
        # before the scrollable canvas claims the rest. Without this, an
        # `expand=True` canvas plus `expand=False` button row leaves the
        # buttons clipped off the bottom of the pane.
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
        self.run_btn = ttk.Button(btn_frame, text="Run (Ctrl+R)", command=self.do_run, state=tk.DISABLED)
        self.run_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Copy Command", command=self.copy_command).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Reset Form", command=self.reset).pack(side=tk.LEFT, padx=2)
        self.dry_run_btn = ttk.Button(btn_frame, text="Dry Run", command=self.do_dry_run, state=tk.DISABLED)
        self.dry_run_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Save Preset...", command=self.save_preset).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Load Preset...", command=self.load_preset).pack(side=tk.LEFT, padx=2)

        preview_frame = ttk.LabelFrame(self, text="Command Preview")
        preview_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
        self.preview_shell = tk.Text(preview_frame, height=2, font=MONO_FONT, wrap=tk.WORD, state=tk.DISABLED)
        self.preview_shell.pack(fill=tk.X, padx=4, pady=2)
        self.preview_argv = tk.Text(preview_frame, height=3, font=MONO_FONT, wrap=tk.WORD, state=tk.DISABLED)
        self.preview_argv.pack(fill=tk.X, padx=4, pady=2)

        globals_frame = ttk.Frame(self)
        globals_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=2)
        ttk.Button(
            globals_frame,
            text="Global Options...",
            command=self.open_global_options,
        ).pack(side=tk.LEFT, padx=4, pady=2)
        self.globals_summary_var = tk.StringVar(value="(all defaults)")
        ttk.Label(
            globals_frame,
            textvariable=self.globals_summary_var,
            foreground="#444",
            wraplength=600,
            justify=tk.LEFT,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Now the scrollable fields area fills whatever space is left.
        canvas_host = ttk.Frame(self)
        canvas_host.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.form_scrollbar = ttk.Scrollbar(canvas_host, orient=tk.VERTICAL)
        self.form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.form_canvas = tk.Canvas(canvas_host, borderwidth=0, highlightthickness=0)
        self.form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.form_canvas.configure(yscrollcommand=self.form_scrollbar.set)
        self.form_scrollbar.config(command=self.form_canvas.yview)
        self.fields_frame = ttk.Frame(self.form_canvas)
        self.form_canvas_window = self.form_canvas.create_window((0, 0), window=self.fields_frame, anchor=tk.NW)
        self.fields_frame.bind("<Configure>", self.on_fields_configure)
        self.form_canvas.bind("<Configure>", self.on_canvas_configure)
        self.form_canvas.bind("<Enter>", lambda e: self.form_canvas.bind_all("<MouseWheel>", self.on_mouse_wheel))
        self.form_canvas.bind("<Leave>", lambda e: self.form_canvas.unbind_all("<MouseWheel>"))

    def on_fields_configure(self, _event: Any) -> None:
        self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))

    def on_canvas_configure(self, event: Any) -> None:
        self.form_canvas.itemconfig(self.form_canvas_window, width=event.width)

    def on_mouse_wheel(self, event: Any) -> None:
        delta = -1 if getattr(event, "delta", 0) > 0 else 1
        self.form_canvas.yview_scroll(delta, "units")

    def add_field(self, parent: tk.Widget, arg: ArgSpec, row: int) -> FieldWidget:
        ttk.Label(parent, text=arg.label + ("*" if arg.required else "") + ":").grid(
            row=row, column=0, sticky=tk.W, padx=8, pady=3
        )
        fw = FieldWidget(arg, parent)
        fw.widget.grid(row=row, column=1, sticky=tk.EW, padx=8, pady=3)
        ttk.Label(parent, text=arg.help, foreground="gray", wraplength=300).grid(
            row=row, column=2, sticky=tk.W, padx=4, pady=3
        )
        fw.trace(self.update_preview)
        return fw

    def set_command(self, spec: CommandSpec) -> None:
        self.spec = spec
        self.title_label.config(text=spec.label)
        self.desc_label.config(text=spec.description)
        self.field_widgets = []

        for widget in self.fields_frame.winfo_children():
            widget.destroy()

        row = 0
        for arg in spec.args:
            fw = self.add_field(self.fields_frame, arg, row)
            self.field_widgets.append(fw)
            row += 1

        # Raw extra arguments (always available).
        ttk.Separator(self.fields_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky=tk.EW, padx=4, pady=6
        )
        row += 1
        ttk.Label(self.fields_frame, text="Extra Args:").grid(row=row, column=0, sticky=tk.W, padx=8, pady=3)
        raw_entry = ttk.Entry(self.fields_frame, textvariable=self.raw_extra_var)
        raw_entry.grid(row=row, column=1, sticky=tk.EW, padx=8, pady=3)
        ttk.Label(
            self.fields_frame,
            text="Free-form arguments appended verbatim (shell-tokenized).",
            foreground="gray",
            wraplength=300,
        ).grid(row=row, column=2, sticky=tk.W, padx=4, pady=3)
        self.raw_extra_var.trace_add("write", lambda *a: self.update_preview())
        row += 1

        self.fields_frame.columnconfigure(1, weight=1)

        # Pre-fill requirements_file from the global toolbar selection (per spec).
        global_req = self.global_requirements_provider()
        if global_req:
            for fw in self.field_widgets:
                if fw.arg.name == REQUIREMENTS_FIELD_NAME and fw.get_value() in (None, ""):
                    fw.set_value(global_req)

        self.run_btn.config(state=tk.NORMAL)
        self.dry_run_btn.config(state=tk.NORMAL if spec.supports_dry_run else tk.DISABLED)
        self.raw_extra_var.set("")
        self.refresh_globals_summary()
        self.update_preview()

    def collect_values(self) -> dict[str, Any]:
        return {fw.arg.name: fw.get_value() for fw in self.field_widgets}

    def collect_global_values(self) -> dict[str, Any]:
        return dict(self.global_values_provider())

    def get_argv(self) -> list[str]:
        if self.spec is None:
            return []
        argv = build_argv_for_spec(self.spec, self.collect_values())
        argv += render_global_args(self.collect_global_values())
        argv += parse_raw_extra(self.raw_extra_var.get())
        return argv

    def refresh_globals_summary(self) -> None:
        chips = summarize_globals(self.collect_global_values())
        if not chips:
            self.globals_summary_var.set("(all defaults)")
        else:
            self.globals_summary_var.set("  •  ".join(chips))

    def open_global_options(self) -> None:
        if self.on_open_global_options is not None:
            self.on_open_global_options()

    def update_preview(self) -> None:
        argv = self.get_argv()
        runner = PipRunner()
        shell_str = runner.format_command(["python", "-m", "pip", *argv])
        argv_json = json.dumps(argv, indent=None)

        self.preview_shell.configure(state=tk.NORMAL)
        self.preview_shell.delete("1.0", tk.END)
        self.preview_shell.insert(tk.END, shell_str)
        self.preview_shell.configure(state=tk.DISABLED)

        self.preview_argv.configure(state=tk.NORMAL)
        self.preview_argv.delete("1.0", tk.END)
        self.preview_argv.insert(tk.END, argv_json)
        self.preview_argv.configure(state=tk.DISABLED)

        if self.on_form_change is not None:
            self.on_form_change()

    def reset(self) -> None:
        for fw in self.field_widgets:
            fw.reset()
        self.raw_extra_var.set("")
        self.update_preview()

    def do_run(self) -> None:
        if self.spec is None:
            return
        argv = self.get_argv()
        self.on_run(argv, self.spec.label)

    def do_dry_run(self) -> None:
        if self.spec is None:
            return
        argv = self.get_argv()
        if "--dry-run" not in argv:
            argv.append("--dry-run")
        self.on_run(argv, f"{self.spec.label} (dry run)")

    def copy_command(self) -> None:
        argv = self.get_argv()
        runner = PipRunner()
        text = runner.format_command(["python", "-m", "pip", *argv])
        self.clipboard_clear()
        self.clipboard_append(text)

    def apply_global_requirements(self, path: str | None) -> None:
        """Push the toolbar-selected requirements file onto the current form's field."""
        if not path:
            return
        for fw in self.field_widgets:
            if fw.arg.name == REQUIREMENTS_FIELD_NAME and fw.get_value() in (None, ""):
                fw.set_value(path)

    def save_preset(self) -> None:
        if self.spec is None:
            return
        name = simpledialog.askstring("Save Preset", "Preset name:", parent=self)
        if not name:
            return
        snapshot = {
            "fields": self.collect_values(),
            "globals": self.collect_global_values(),
            "raw": self.raw_extra_var.get(),
        }
        self.presets.save(name, self.spec.name, snapshot)

    def load_preset(self) -> None:
        if self.spec is None:
            return
        names = self.presets.names_for(self.spec.name)
        if not names:
            info_dialog(self, "No Presets", f"No saved presets for {self.spec.label}.")
            return
        win = tk.Toplevel(self)
        win.title("Load Preset")
        ttk.Label(win, text="Choose a preset:").pack(padx=8, pady=4, anchor=tk.W)
        lb = tk.Listbox(win, height=min(12, len(names)))
        for n in names:
            lb.insert(tk.END, n)
        lb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        def apply_selected() -> None:
            sel = lb.curselection()  # type: ignore[no-untyped-call]
            if not sel:
                return
            chosen = names[sel[0]]
            preset = self.presets.get(chosen)
            if preset is None:
                return
            values = preset.get("values", {})
            fields = values.get("fields", {})
            raw = values.get("raw", "")
            for fw in self.field_widgets:
                if fw.arg.name in fields:
                    fw.set_value(fields[fw.arg.name])
            self.raw_extra_var.set(str(raw or ""))
            win.destroy()
            self.update_preview()

        def delete_selected() -> None:
            sel = lb.curselection()  # type: ignore[no-untyped-call]
            if not sel:
                return
            chosen = names[sel[0]]
            self.presets.delete(chosen)
            win.destroy()

        btn = ttk.Frame(win)
        btn.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(btn, text="Load", command=apply_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Delete", command=delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=2)
