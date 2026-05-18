"""Tests for runner module."""

from __future__ import annotations

import subprocess
import threading
from typing import Any

import pytest

from pip_ui.runner import PipRunner


def test_build_argv() -> None:
    runner = PipRunner()
    result = runner.build_argv("/usr/bin/python", ["install", "requests"])
    assert result == ["/usr/bin/python", "-m", "pip", "install", "requests"]


def test_build_argv_empty_pip_args() -> None:
    runner = PipRunner()
    result = runner.build_argv("/usr/bin/python", [])
    assert result == ["/usr/bin/python", "-m", "pip"]


def test_redact_argv_no_credentials() -> None:
    argv = ["/usr/bin/python", "-m", "pip", "install", "--index-url", "https://pypi.org/simple"]
    result = PipRunner.redact_argv(argv)
    assert result == argv


def test_redact_argv_with_credentials() -> None:
    argv = ["/usr/bin/python", "-m", "pip", "install", "--index-url", "https://user:pass@pypi.example.com/simple"]
    result = PipRunner.redact_argv(argv)
    assert "user" not in result[5]
    assert "pass" not in result[5]
    assert "<redacted>:<redacted>@" in result[5]


def test_redact_argv_preserves_safe_args() -> None:
    argv = ["python", "-m", "pip", "list", "--format", "json"]
    result = PipRunner.redact_argv(argv)
    assert result == argv


def test_format_command() -> None:
    runner = PipRunner()
    argv = ["/usr/bin/python", "-m", "pip", "install", "requests"]
    result = runner.format_command(argv)
    assert isinstance(result, str)
    assert "pip" in result
    assert "install" in result
    assert "requests" in result


def test_format_command_quotes_spaces() -> None:
    runner = PipRunner()
    argv = ["python", "-m", "pip", "install", "some package"]
    result = runner.format_command(argv)
    assert '"some package"' in result


def test_cancel_no_process() -> None:
    runner = PipRunner()
    runner.cancel()


def test_run_uses_utf8_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    done = threading.Event()

    class FakeStream:
        def readline(self) -> str:
            return ""

    class FakePopen:
        def __init__(self, *_args: object, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.stdout = FakeStream()
            self.stderr = FakeStream()
            self.returncode = 0

        def __enter__(self) -> Any:
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self) -> int:
            return self.returncode

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    runner = PipRunner()
    runner.run(["python", "-m", "pip", "list"], ".", lambda _line: None, lambda _line: None, lambda _code: done.set())

    assert done.wait(timeout=2)
    assert captured["text"] is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["env"]["PYTHONUTF8"] == "1"
    assert captured["env"]["PYTHONIOENCODING"] == "utf-8"
