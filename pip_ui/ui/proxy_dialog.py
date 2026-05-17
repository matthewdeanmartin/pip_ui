"""HTTP proxy configuration and test dialog.

Helps corporate users set up --proxy for pip.  Shows what is currently active
(env vars + global options) and lets the user test connectivity.
"""

from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

from pip_ui.encoding import utf8_subprocess_kwargs

_LABEL_TESTING = "Testing…"
_LABEL_OK = "✔  Proxy works"
_LABEL_FAIL = "✗  Proxy test failed"


class ProxyDialog(tk.Toplevel):
    """Modal dialog for viewing, setting, and testing HTTP proxy configuration."""

    def __init__(
        self,
        parent: tk.Misc,
        python_path: str | None,
        current_proxy: str | None,
        on_apply: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.title("HTTP Proxy Configuration")
        self.geometry("600x500")
        self.minsize(520, 420)
        self.transient(parent.winfo_toplevel())  # type: ignore[no-untyped-call]
        self.grab_set()
        self._python_path = python_path
        self._on_apply = on_apply
        self._result_queue: list[tuple[bool, str]] = []
        self._thread: threading.Thread | None = None
        self._build_ui(current_proxy)
        self.after(100, self._poll)

    # ------------------------------------------------------------------ build

    def _build_ui(self, current_proxy: str | None) -> None:
        pad: dict[str, Any] = {"padx": 10, "pady": 4}

        header = ttk.Frame(self)
        header.pack(fill=tk.X, **pad)
        ttk.Label(
            header,
            text="HTTP Proxy Configuration",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            header,
            text=("Configure or test a proxy server for pip. " "Format: scheme://[user:password@]host:port"),
            wraplength=560,
            foreground="gray",
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        # --- Environment variables in effect ---
        env_frame = ttk.LabelFrame(self, text="Active proxy environment variables")
        env_frame.pack(fill=tk.X, **pad)
        env_text = self._read_proxy_env()
        ttk.Label(
            env_frame,
            text=env_text or "(none set)",
            foreground="#333",
            font=("Consolas", 9),
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=4, pady=4)

        # --- Proxy entry ---
        entry_frame = ttk.LabelFrame(self, text="Proxy URL for this session (--proxy flag)")
        entry_frame.pack(fill=tk.X, **pad)

        self._proxy_var = tk.StringVar(value=current_proxy or "")
        entry_row = ttk.Frame(entry_frame)
        entry_row.pack(fill=tk.X, padx=4, pady=4)
        ttk.Entry(entry_row, textvariable=self._proxy_var, width=46).pack(side=tk.LEFT, fill=tk.X, expand=True)

        hint = ttk.Frame(entry_frame)
        hint.pack(fill=tk.X, padx=4, pady=(0, 4))
        ttk.Label(
            hint,
            text="Tip: use http://proxy.corp.example.com:8080 — avoid embedding passwords here; use a netrc file instead.",
            foreground="gray",
            wraplength=540,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        btn_row = ttk.Frame(entry_frame)
        btn_row.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(btn_row, text="Apply to Global Options", command=self._apply).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Clear Proxy", command=self._clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Test Proxy", command=self._test).pack(side=tk.LEFT, padx=2)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        # --- Status + output ---
        self._status_var = tk.StringVar(value="Enter a proxy URL and click Test Proxy.")
        self._status_label = ttk.Label(
            self, textvariable=self._status_var, font=("TkDefaultFont", 10, "bold"), foreground="#444"
        )
        self._status_label.pack(anchor=tk.W, **pad)

        out_frame = ttk.Frame(self)
        out_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))
        sb = ttk.Scrollbar(out_frame, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._output = tk.Text(
            out_frame,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            yscrollcommand=sb.set,
            height=6,
        )
        self._output.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self._output.yview)

        ttk.Button(self, text="Close", command=self.destroy).pack(anchor=tk.E, padx=10, pady=4)

    # ---------------------------------------------------------------- helpers

    def _read_proxy_env(self) -> str:
        keys = ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "NO_PROXY", "no_proxy"]
        lines: list[str] = []
        for k in keys:
            v = os.environ.get(k)
            if v:
                # Redact password portion for display.
                import re

                v_display = re.sub(r"(://)[^:@/\s]+:[^@/\s]+@", r"\1<redacted>:<redacted>@", v)
                lines.append(f"{k}={v_display}")
        return "\n".join(lines)

    def _write(self, text: str) -> None:
        self._output.configure(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.insert(tk.END, text)
        self._output.configure(state=tk.DISABLED)

    def _check_credentials(self, url: str) -> bool:
        import re

        return bool(re.search(r"://[^:@/\s]+:[^@/\s]+@", url))

    # --------------------------------------------------------------- actions

    def _apply(self) -> None:
        proxy = self._proxy_var.get().strip()
        if self._check_credentials(proxy):
            from pip_ui.ui.dialogs import confirm_dialog

            ok = confirm_dialog(
                self,
                "Credentials in proxy URL",
                "The proxy URL contains a password. It will be saved in plain text in settings.\n\n"
                "Consider storing credentials in a netrc file (~/.netrc) instead.\n\n"
                "Continue anyway?",
            )
            if not ok:
                return
        if self._on_apply:
            self._on_apply(proxy or None)
        self.destroy()

    def _clear(self) -> None:
        self._proxy_var.set("")

    def _test(self) -> None:
        if not self._python_path:
            self._status_var.set("No interpreter selected — choose one in the main window first.")
            self._status_label.config(foreground="red")
            return
        proxy = self._proxy_var.get().strip()
        if not proxy:
            self._status_var.set("Enter a proxy URL first.")
            return
        self._status_var.set(_LABEL_TESTING)
        self._status_label.config(foreground="#444")
        self._write("")

        def worker() -> None:
            argv = [self._python_path, "-m", "pip", "index", "versions", "pip", "--proxy", proxy]
            try:
                result = subprocess.run(  # nosec B603
                    argv,
                    capture_output=True,
                    timeout=20,
                    check=False,
                    shell=False,
                    **utf8_subprocess_kwargs(),
                )
                combined = (result.stdout + result.stderr).strip()
                self._result_queue.append((result.returncode == 0, combined or "(no output)"))
            except subprocess.TimeoutExpired:
                self._result_queue.append((False, "Timed out after 20 seconds."))
            except Exception as exc:
                self._result_queue.append((False, f"Error: {exc}"))

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    # --------------------------------------------------------------- polling

    def _poll(self) -> None:
        if self._result_queue:
            ok, text = self._result_queue.pop(0)
            if ok:
                self._status_var.set(_LABEL_OK)
                self._status_label.config(foreground="green")
            else:
                self._status_var.set(_LABEL_FAIL)
                self._status_label.config(foreground="red")
            self._write(text)
            self._thread = None
        self.after(100, self._poll)
