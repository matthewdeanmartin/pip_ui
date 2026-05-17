"""HTTPS certificate tester dialog.

Lets corporate users point at a PEM bundle (or a folder of .pem/.crt files)
and immediately discover whether pip can use them.  The test runs
``pip index versions pip --cert <path>`` against the active interpreter.
"""

from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

from pip_ui.encoding import utf8_subprocess_kwargs

_LABEL_TESTING = "Testing…"
_LABEL_OK = "✔  Certificate works"
_LABEL_FAIL = "✗  Certificate failed"
_LABEL_READY = "Select a certificate to test."


class CertTesterDialog(tk.Toplevel):
    """Modal dialog for testing PEM cert files or a whole folder."""

    def __init__(self, parent: tk.Misc, python_path: str | None, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.title("HTTPS Certificate Tester")
        self.geometry("620x460")
        self.minsize(540, 380)
        self.transient(parent.winfo_toplevel())  # type: ignore[no-untyped-call]
        self.grab_set()
        self._python_path = python_path
        self._thread: threading.Thread | None = None
        self._result_queue: list[tuple[bool, str]] = []
        self._build_ui()
        self.after(100, self._poll)

    # ------------------------------------------------------------------ build

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 4}

        header = ttk.Frame(self)
        header.pack(fill=tk.X, **pad)
        ttk.Label(
            header,
            text="HTTPS Certificate Tester",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            header,
            text=(
                "Test whether a PEM certificate bundle works with pip. "
                "Useful when behind a corporate TLS-intercepting proxy."
            ),
            wraplength=580,
            justify=tk.LEFT,
            foreground="gray",
        ).pack(anchor=tk.W)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        # --- Single file ---
        file_frame = ttk.LabelFrame(self, text="Test a single certificate file (.pem / .crt / .cer)")
        file_frame.pack(fill=tk.X, **pad)

        self._cert_var = tk.StringVar()
        row = ttk.Frame(file_frame)
        row.pack(fill=tk.X, padx=4, pady=4)
        ttk.Entry(row, textvariable=self._cert_var, width=46).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Browse…", command=self._browse_file).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(file_frame, text="Test Certificate", command=self._test_file).pack(anchor=tk.W, padx=4, pady=(0, 4))

        # --- Folder scan ---
        folder_frame = ttk.LabelFrame(self, text="Scan a folder — try every .pem / .crt / .cer file")
        folder_frame.pack(fill=tk.X, **pad)

        self._folder_var = tk.StringVar()
        row2 = ttk.Frame(folder_frame)
        row2.pack(fill=tk.X, padx=4, pady=4)
        ttk.Entry(row2, textvariable=self._folder_var, width=46).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row2, text="Browse…", command=self._browse_folder).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(folder_frame, text="Scan Folder", command=self._scan_folder).pack(anchor=tk.W, padx=4, pady=(0, 4))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        # --- Status / output ---
        self._status_var = tk.StringVar(value=_LABEL_READY)
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
            height=8,
        )
        self._output.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self._output.yview)

        ttk.Button(self, text="Close", command=self.destroy).pack(anchor=tk.E, padx=10, pady=4)

    # ---------------------------------------------------------------- helpers

    def _write(self, text: str) -> None:
        self._output.configure(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.insert(tk.END, text)
        self._output.configure(state=tk.DISABLED)

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select certificate file",
            filetypes=[("Certificate files", "*.pem *.crt *.cer"), ("All files", "*.*")],
        )
        if path:
            self._cert_var.set(path)

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(parent=self, title="Select folder containing certificates")
        if path:
            self._folder_var.set(path)

    def _no_interpreter_warning(self) -> bool:
        if not self._python_path:
            self._status_var.set("No interpreter selected — choose one in the main window first.")
            self._status_label.config(foreground="red")
            return True
        return False

    # ------------------------------------------------------------------ tests

    def _test_file(self) -> None:
        if self._no_interpreter_warning():
            return
        path = self._cert_var.get().strip()
        if not path:
            self._status_var.set("Enter a certificate file path first.")
            return
        if not os.path.isfile(path):
            self._status_var.set(f"File not found: {path}")
            self._status_label.config(foreground="red")
            return
        self._run_test(path)

    def _scan_folder(self) -> None:
        if self._no_interpreter_warning():
            return
        folder = self._folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self._status_var.set("Enter a valid folder path first.")
            return
        certs = [str(p) for p in Path(folder).iterdir() if p.suffix.lower() in {".pem", ".crt", ".cer"} and p.is_file()]
        if not certs:
            self._status_var.set("No .pem/.crt/.cer files found in that folder.")
            return
        self._status_var.set(f"Scanning {len(certs)} file(s)…")
        self._status_label.config(foreground="#444")
        self._write("")

        # Run tests sequentially in a background thread.
        def worker() -> None:
            lines: list[str] = []
            found: str | None = None
            for cert in certs:
                ok, _detail = self._check_cert(cert)
                icon = "✔" if ok else "✗"
                lines.append(f"{icon}  {os.path.basename(cert)}")
                if ok and found is None:
                    found = cert
            summary = "\n".join(lines)
            if found:
                summary += f"\n\nFirst working cert:\n  {found}"
            self._result_queue.append((bool(found), summary))

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _run_test(self, cert_path: str) -> None:
        self._status_var.set(_LABEL_TESTING)
        self._status_label.config(foreground="#444")
        self._write("")

        def worker() -> None:
            ok, output = self._check_cert(cert_path)
            self._result_queue.append((ok, output))

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _check_cert(self, cert_path: str) -> tuple[bool, str]:
        """Run ``pip index versions pip --cert <path>`` and return (success, output)."""
        argv = [self._python_path, "-m", "pip", "index", "versions", "pip", "--cert", cert_path]
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
            return result.returncode == 0, combined or "(no output)"
        except subprocess.TimeoutExpired:
            return False, "Timed out after 20 seconds."
        except Exception as exc:
            return False, f"Error: {exc}"

    # ----------------------------------------------------------------- polling

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
