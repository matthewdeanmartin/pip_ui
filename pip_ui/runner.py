"""Subprocess runner for pip commands."""

from __future__ import annotations

import re
import subprocess
import threading
from typing import Callable, Optional


class PipRunner:
    def __init__(self) -> None:
        self.process: Optional[subprocess.Popen[str]] = None
        self.cancelled = False

    def build_argv(self, python_path: str, pip_args: list[str]) -> list[str]:
        return [python_path, "-m", "pip"] + pip_args

    def format_command(self, argv: list[str]) -> str:
        parts = []
        for arg in argv:
            if " " in arg or not arg:
                parts.append(f'"{arg}"')
            else:
                parts.append(arg)
        return " ".join(parts)

    @staticmethod
    def redact_argv(argv: list[str]) -> list[str]:
        pattern = re.compile(r"(://)[^:@/]+:[^@/]+@")
        return [pattern.sub(r"\1<redacted>:<redacted>@", arg) for arg in argv]

    def run(
        self,
        argv: list[str],
        cwd: str,
        on_stdout: Callable[[str], None],
        on_stderr: Callable[[str], None],
        on_done: Callable[[int], None],
    ) -> None:
        self.cancelled = False

        def worker() -> None:
            try:
                self.process = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=cwd,
                    shell=False,
                )
                assert self.process.stdout is not None
                assert self.process.stderr is not None

                stdout_thread = threading.Thread(
                    target=self.read_stream,
                    args=(self.process.stdout, on_stdout),
                    daemon=True,
                )
                stderr_thread = threading.Thread(
                    target=self.read_stream,
                    args=(self.process.stderr, on_stderr),
                    daemon=True,
                )
                stdout_thread.start()
                stderr_thread.start()
                stdout_thread.join()
                stderr_thread.join()
                self.process.wait()
                exit_code = self.process.returncode if not self.cancelled else -1
            except Exception:
                exit_code = -1
            finally:
                on_done(exit_code)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def read_stream(self, stream: object, callback: Callable[[str], None]) -> None:
        import io
        for line in iter(stream.readline, ""):  # type: ignore[attr-defined]
            callback(line)

    def cancel(self) -> None:
        self.cancelled = True
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception:
                pass
