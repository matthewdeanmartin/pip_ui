"""Tests for cert_tester pure-function helpers."""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest

pytest.importorskip("tkinter")

from pip_ui.ui.cert_tester import run_cert_check  # pylint: disable=wrong-import-position


def _make_completed(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = stderr
    return r


def test_success_returns_true_with_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _make_completed(0, "pip 25.1"))
    ok, text = run_cert_check("/usr/bin/python", "/certs/ca.pem")
    assert ok is True
    assert "pip 25.1" in text


def test_nonzero_returncode_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _make_completed(1, "", "SSL error"))
    ok, text = run_cert_check("/usr/bin/python", "/certs/bad.pem")
    assert ok is False
    assert "SSL error" in text


def test_empty_output_returns_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _make_completed(0, "", ""))
    ok, text = run_cert_check("/usr/bin/python", "/certs/ca.pem")
    assert ok is True
    assert text == "(no output)"


def test_timeout_returns_false_with_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*_a: Any, **_kw: Any) -> None:
        raise subprocess.TimeoutExpired(cmd=[], timeout=20)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    ok, text = run_cert_check("/usr/bin/python", "/certs/ca.pem")
    assert ok is False
    assert "Timed out" in text


def test_oserror_returns_false_with_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_os(*_a: Any, **_kw: Any) -> None:
        raise OSError("No such file")

    monkeypatch.setattr(subprocess, "run", raise_os)
    ok, text = run_cert_check("/nonexistent/python", "/certs/ca.pem")
    assert ok is False
    assert "No such file" in text


def test_passes_cert_path_in_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **_kw: Any) -> MagicMock:
        captured["argv"] = argv
        return _make_completed(0, "ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_cert_check("/usr/bin/python", "/certs/mycert.pem")
    assert "/certs/mycert.pem" in captured["argv"]
    assert "--cert" in captured["argv"]


def test_passes_python_path_as_first_element(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **_kw: Any) -> MagicMock:
        captured["argv"] = argv
        return _make_completed(0, "ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_cert_check("/custom/python3", "/certs/ca.pem")
    assert captured["argv"][0] == "/custom/python3"


def test_combined_stdout_and_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _make_completed(1, "out:", "err"))
    _ok, text = run_cert_check("/usr/bin/python", "/certs/ca.pem")
    assert "out:" in text
    assert "err" in text
