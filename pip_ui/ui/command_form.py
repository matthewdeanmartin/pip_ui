"""Dynamic form generated from CommandSpec."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any, Callable, Optional

from pip_ui.models import ArgSpec, CommandSpec

MONO_FONT = ("Consolas", 10)


class FieldWidget:
    def __init__(self, arg: ArgSpec, parent: tk.Widget) -> None:
        self.arg = arg
        self.var: tk.Variable

        if arg.field_type == "checkbox":
            self.var = tk.BooleanVar(value=bool(arg.default))
            self.widget = ttk.Checkbutton(parent, variable=self.var)
        elif arg.field_type == "dropdown":
            self.var = tk.StringVar(value=str(arg.default) if arg.default is not None else (arg.choices[0] if arg.choices else ""))
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
            self.var.set(path)

    def browse_dir(self) -> None:
        path = filedialog.askdirectory(title=f"Select {self.arg.label}")
        if path:
            self.var.set(path)

    def get_value(self) -> Any:
        if self.arg.field_type == "checkbox":
            return self.var.get()
        val = self.var.get()
        return val if val else None

    def reset(self) -> None:
        if self.arg.field_type == "checkbox":
            self.var.set(bool(self.arg.default))
        elif self.arg.field_type == "dropdown":
            default = str(self.arg.default) if self.arg.default is not None else (self.arg.choices[0] if self.arg.choices else "")
            self.var.set(default)
        else:
            self.var.set(str(self.arg.default) if self.arg.default is not None else "")

    def trace(self, callback: Callable[[], None]) -> None:
        self.var.trace_add("write", lambda *a: callback())


class CommandForm(ttk.Frame):
    def __init__(self, parent: tk.Widget, on_run: Callable[[list[str], str], None], **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.on_run = on_run
        self.spec: Optional[CommandSpec] = None
        self.field_widgets: list[FieldWidget] = []
        self.build_ui()

    def build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=8, pady=4)
        self.title_label = ttk.Label(header, text="Select a command", font=("TkDefaultFont", 12, "bold"))
        self.title_label.pack(anchor=tk.W)
        self.desc_label = ttk.Label(header, text="", wraplength=500, justify=tk.LEFT)
        self.desc_label.pack(anchor=tk.W)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=2)

        self.form_canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.form_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.form_canvas.yview)
        self.form_canvas.configure(yscrollcommand=self.form_scrollbar.set)
        self.form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.form_canvas.pack(fill=tk.BOTH, expand=True)
        self.fields_frame = ttk.Frame(self.form_canvas)
        self.form_canvas_window = self.form_canvas.create_window((0, 0), window=self.fields_frame, anchor=tk.NW)
        self.fields_frame.bind("<Configure>", self.on_fields_configure)
        self.form_canvas.bind("<Configure>", self.on_canvas_configure)

        preview_frame = ttk.LabelFrame(self, text="Command Preview")
        preview_frame.pack(fill=tk.X, padx=8, pady=4)
        self.preview_shell = tk.Text(preview_frame, height=2, font=MONO_FONT, wrap=tk.WORD, state=tk.DISABLED)
        self.preview_shell.pack(fill=tk.X, padx=4, pady=2)
        self.preview_argv = tk.Text(preview_frame, height=2, font=MONO_FONT, wrap=tk.WORD, state=tk.DISABLED)
        self.preview_argv.pack(fill=tk.X, padx=4, pady=2)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=4)
        self.run_btn = ttk.Button(btn_frame, text="Run (Ctrl+R)", command=self.do_run, state=tk.DISABLED)
        self.run_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Copy Command", command=self.copy_command).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Reset Form", command=self.reset).pack(side=tk.LEFT, padx=2)
        self.dry_run_btn = ttk.Button(btn_frame, text="Dry Run", command=self.do_dry_run, state=tk.DISABLED)
        self.dry_run_btn.pack(side=tk.LEFT, padx=2)

    def on_fields_configure(self, event: Any) -> None:
        self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))

    def on_canvas_configure(self, event: Any) -> None:
        self.form_canvas.itemconfig(self.form_canvas_window, width=event.width)

    def set_command(self, spec: CommandSpec) -> None:
        self.spec = spec
        self.title_label.config(text=spec.label)
        self.desc_label.config(text=spec.description)
        self.field_widgets = []

        for widget in self.fields_frame.winfo_children():
            widget.destroy()

        for i, arg in enumerate(spec.args):
            ttk.Label(self.fields_frame, text=arg.label + ("*" if arg.required else "") + ":").grid(
                row=i, column=0, sticky=tk.W, padx=8, pady=3
            )
            fw = FieldWidget(arg, self.fields_frame)
            fw.widget.grid(row=i, column=1, sticky=tk.EW, padx=8, pady=3)
            ttk.Label(self.fields_frame, text=arg.help, foreground="gray", wraplength=300).grid(
                row=i, column=2, sticky=tk.W, padx=4, pady=3
            )
            fw.trace(self.update_preview)
            self.field_widgets.append(fw)

        self.fields_frame.columnconfigure(1, weight=1)

        self.run_btn.config(state=tk.NORMAL)
        self.dry_run_btn.config(state=tk.NORMAL if spec.supports_dry_run else tk.DISABLED)
        self.update_preview()

    def get_argv(self) -> list[str]:
        if self.spec is None:
            return []
        args: list[str] = []

        if self.spec.name == "config_list":
            return ["config", "list"]
        if self.spec.name == "config_debug":
            return ["config", "debug"]
        if self.spec.name == "cache_dir":
            return ["cache", "dir"]
        if self.spec.name == "cache_info":
            return ["cache", "info"]
        if self.spec.name == "debug":
            return ["debug"]
        if self.spec.name == "version":
            return ["--version"]
        if self.spec.name == "help":
            return ["help"]

        args.append(self.spec.name)

        for fw in self.field_widgets:
            arg = fw.arg
            value = fw.get_value()
            if arg.field_type == "checkbox":
                if value:
                    args.append(arg.flag)
            elif arg.field_type == "multi":
                if value:
                    tokens = str(value).split()
                    for token in tokens:
                        if arg.flag:
                            args.append(arg.flag)
                        args.append(token)
            elif arg.field_type == "dropdown":
                if value and value != arg.default:
                    args.extend([arg.flag, str(value)])
            else:
                if value:
                    if arg.flag:
                        args.extend([arg.flag, str(value)])
                    else:
                        args.append(str(value))

        return args

    def update_preview(self) -> None:
        from pip_ui.runner import PipRunner
        argv = self.get_argv()
        runner = PipRunner()
        shell_str = runner.format_command(["python", "-m", "pip"] + argv)
        argv_json = json.dumps(argv, indent=None)

        self.preview_shell.configure(state=tk.NORMAL)
        self.preview_shell.delete("1.0", tk.END)
        self.preview_shell.insert(tk.END, shell_str)
        self.preview_shell.configure(state=tk.DISABLED)

        self.preview_argv.configure(state=tk.NORMAL)
        self.preview_argv.delete("1.0", tk.END)
        self.preview_argv.insert(tk.END, argv_json)
        self.preview_argv.configure(state=tk.DISABLED)

    def reset(self) -> None:
        for fw in self.field_widgets:
            fw.reset()
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
        from pip_ui.runner import PipRunner
        argv = self.get_argv()
        runner = PipRunner()
        text = runner.format_command(["python", "-m", "pip"] + argv)
        self.clipboard_clear()
        self.clipboard_append(text)
