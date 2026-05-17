"""HTTPS certificate tester dialog.

Lets corporate users point at a PEM bundle (or a folder of .pem/.crt files)
and immediately discover whether pip can use them.  The test runs
``pip index versions pip --cert <path>`` against the active interpreter.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

from pip_ui.encoding import utf8_subprocess_kwargs

LABEL_TESTING = "Testing…"


def run_cert_check(python_path: str, cert_path: str) -> tuple[bool, str]:
    """Run ``pip index versions pip --cert <path>`` and return (success, output).

    Extracted for testability — does not touch Tk state.
    """
    argv = [python_path, "-m", "pip", "index", "versions", "pip", "--cert", cert_path]
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
    except OSError as exc:
        return False, f"Error: {exc}"


LABEL_OK = "✔  Certificate works"
LABEL_FAIL = "✗  Certificate failed"
LABEL_READY = "Select a certificate to test."


class CertTesterDialog(tk.Toplevel):
    """Modal dialog for testing PEM cert files or a whole folder."""

    def __init__(self, parent: tk.Misc, python_path: str | None, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.title("HTTPS Certificate Tester")
        self.geometry("620x460")
        self.minsize(540, 380)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.python_path = python_path
        self.thread: threading.Thread | None = None
        self.result_queue: list[tuple[bool, str]] = []
        self.build_ui()
        self.after(100, self.poll)

    # ------------------------------------------------------------------ build

    def build_ui(self) -> None:
        pad: dict[str, Any] = {"padx": 10, "pady": 4}

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

        self.cert_var = tk.StringVar()
        row = ttk.Frame(file_frame)
        row.pack(fill=tk.X, padx=4, pady=4)
        ttk.Entry(row, textvariable=self.cert_var, width=46).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Browse…", command=self.browse_file).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(file_frame, text="Test Certificate", command=self.test_file).pack(anchor=tk.W, padx=4, pady=(0, 4))

        # --- Folder scan ---
        folder_frame = ttk.LabelFrame(self, text="Scan a folder — try every .pem / .crt / .cer file")
        folder_frame.pack(fill=tk.X, **pad)

        self.folder_var = tk.StringVar()
        row2 = ttk.Frame(folder_frame)
        row2.pack(fill=tk.X, padx=4, pady=4)
        ttk.Entry(row2, textvariable=self.folder_var, width=46).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row2, text="Browse…", command=self.browse_folder).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(folder_frame, text="Scan Folder", command=self.scan_folder).pack(anchor=tk.W, padx=4, pady=(0, 4))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        # --- Status / output ---
        self.status_var = tk.StringVar(value=LABEL_READY)
        self.status_label = ttk.Label(
            self, textvariable=self.status_var, font=("TkDefaultFont", 10, "bold"), foreground="#444"
        )
        self.status_label.pack(anchor=tk.W, **pad)

        out_frame = ttk.Frame(self)
        out_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))
        sb = ttk.Scrollbar(out_frame, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.output = tk.Text(
            out_frame,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            yscrollcommand=sb.set,
            height=8,
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.output.yview)

        ttk.Button(self, text="Close", command=self.destroy).pack(anchor=tk.E, padx=10, pady=4)

    # ---------------------------------------------------------------- helpers

    def write(self, text: str) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)
        self.output.configure(state=tk.DISABLED)

    def browse_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select certificate file",
            filetypes=[("Certificate files", "*.pem *.crt *.cer"), ("All files", "*.*")],
        )
        if path:
            self.cert_var.set(path)

    def browse_folder(self) -> None:
        path = filedialog.askdirectory(parent=self, title="Select folder containing certificates")
        if path:
            self.folder_var.set(path)

    def no_interpreter_warning(self) -> bool:
        if not self.python_path:
            self.status_var.set("No interpreter selected — choose one in the main window first.")
            self.status_label.config(foreground="red")
            return True
        return False

    # ------------------------------------------------------------------ tests

    def test_file(self) -> None:
        if self.no_interpreter_warning():
            return
        path = self.cert_var.get().strip()
        if not path:
            self.status_var.set("Enter a certificate file path first.")
            return
        if not os.path.isfile(path):
            self.status_var.set(f"File not found: {path}")
            self.status_label.config(foreground="red")
            return
        self.run_test(path)

    def scan_folder(self) -> None:
        if self.no_interpreter_warning():
            return
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self.status_var.set("Enter a valid folder path first.")
            return
        certs = [str(p) for p in Path(folder).iterdir() if p.suffix.lower() in {".pem", ".crt", ".cer"} and p.is_file()]
        if not certs:
            self.status_var.set("No .pem/.crt/.cer files found in that folder.")
            return
        self.status_var.set(f"Scanning {len(certs)} file(s)…")
        self.status_label.config(foreground="#444")
        self.write("")

        # Run tests sequentially in a background thread.
        def worker() -> None:
            lines: list[str] = []
            found: str | None = None
            for cert in certs:
                ok, _detail = self.check_cert(cert)
                icon = "✔" if ok else "✗"
                lines.append(f"{icon}  {os.path.basename(cert)}")
                if ok and found is None:
                    found = cert
            summary = "\n".join(lines)
            if found:
                summary += f"\n\nFirst working cert:\n  {found}"
            self.result_queue.append((bool(found), summary))

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()

    def run_test(self, cert_path: str) -> None:
        self.status_var.set(LABEL_TESTING)
        self.status_label.config(foreground="#444")
        self.write("")

        def worker() -> None:
            ok, output = self.check_cert(cert_path)
            self.result_queue.append((ok, output))

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()

    def check_cert(self, cert_path: str) -> tuple[bool, str]:
        python = self.python_path or sys.executable
        return run_cert_check(python, cert_path)

    # ----------------------------------------------------------------- polling

    def poll(self) -> None:
        if self.result_queue:
            ok, text = self.result_queue.pop(0)
            if ok:
                self.status_var.set(LABEL_OK)
                self.status_label.config(foreground="green")
            else:
                self.status_var.set(LABEL_FAIL)
                self.status_label.config(foreground="red")
            self.write(text)
            self.thread = None
        self.after(100, self.poll)
