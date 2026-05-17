"""Subprocess runner for pip commands."""

from __future__ import annotations

import re
import subprocess  # nosec B404
import threading
from collections.abc import Callable
from typing import TextIO

from pip_ui.encoding import utf8_subprocess_kwargs

CRED_RE = re.compile(r"(://)[^:@/\s]+:[^@/\s]+@")


class PipRunner:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.cancelled = False
        self.killed = False

    def build_argv(self, python_path: str, pip_args: list[str]) -> list[str]:
        return [python_path, "-m", "pip", *pip_args]

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
        return [CRED_RE.sub(r"\1<redacted>:<redacted>@", arg) for arg in argv]

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def run(
        self,
        argv: list[str],
        cwd: str,
        on_stdout: Callable[[str], None],
        on_stderr: Callable[[str], None],
        on_done: Callable[[int], None],
        env: dict[str, str] | None = None,
    ) -> None:
        self.cancelled = False
        self.killed = False

        def worker() -> None:
            kwargs = utf8_subprocess_kwargs()
            if env is not None:
                merged = dict(kwargs.get("env") or {})
                merged.update(env)
                kwargs["env"] = merged
            try:
                with subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    shell=False,
                    **kwargs,
                ) as process:  # nosec B603
                    self.process = process
                    assert process.stdout is not None
                    assert process.stderr is not None

                    stdout_thread = threading.Thread(
                        target=self.read_stream,
                        args=(process.stdout, on_stdout),
                        daemon=True,
                    )
                    stderr_thread = threading.Thread(
                        target=self.read_stream,
                        args=(process.stderr, on_stderr),
                        daemon=True,
                    )
                    stdout_thread.start()
                    stderr_thread.start()
                    stdout_thread.join()
                    stderr_thread.join()
                    process.wait()
                    if self.killed:
                        exit_code = -9
                    elif self.cancelled:
                        exit_code = -1
                    else:
                        exit_code = process.returncode if process.returncode is not None else -1
            except (OSError, subprocess.SubprocessError):
                exit_code = -1
            finally:
                on_done(exit_code)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def read_stream(self, stream: TextIO, callback: Callable[[str], None]) -> None:
        for line in iter(stream.readline, ""):
            callback(line)

    def cancel(self, force: bool = False) -> bool:
        """Cancel the running process.

        Returns True if a signal was sent. ``force=True`` escalates to kill.
        """
        if self.process is None:
            return False
        try:
            if force:
                self.killed = True
                self.process.kill()
            else:
                self.cancelled = True
                self.process.terminate()
            return True
        except OSError:
            return False
