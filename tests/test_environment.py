"""Tests for environment module."""

from __future__ import annotations

import subprocess
import sys

import pytest

from pip_ui.environment import InterpreterDiscovery
from pip_ui.models import InterpreterInfo


def test_is_venv_true():
    discovery = InterpreterDiscovery()
    assert discovery.is_venv("/home/user/.venv", "/usr") is True


def test_is_venv_false():
    discovery = InterpreterDiscovery()
    assert discovery.is_venv("/usr", "/usr") is False


def test_validate_returns_none_for_nonexistent():
    discovery = InterpreterDiscovery()
    result = discovery.validate("/nonexistent/path/to/python")
    assert result is None


def test_validate_returns_none_for_invalid_path():
    discovery = InterpreterDiscovery()
    result = discovery.validate("/tmp/not_a_python_executable")
    assert result is None


def test_validate_current_interpreter():
    discovery = InterpreterDiscovery()
    result = discovery.validate(sys.executable)
    assert result is not None
    assert result.path == sys.executable
    assert result.version
    assert result.pip_version


def test_discover_finds_at_least_one():
    discovery = InterpreterDiscovery()
    results = discovery.discover()
    assert len(results) >= 1


def test_discover_returns_list_of_interpreter_info():
    discovery = InterpreterDiscovery()
    results = discovery.discover()
    for item in results:
        assert isinstance(item, InterpreterInfo)
        assert item.path
        assert item.version


def test_is_venv_edge_cases():
    discovery = InterpreterDiscovery()
    assert discovery.is_venv("", "") is False
    assert discovery.is_venv("/a/b/c", "/a/b") is True


def test_get_pip_version_returns_unknown_on_probe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    discovery = InterpreterDiscovery()

    def raise_os_error(*args: object, **kwargs: object) -> None:
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "run", raise_os_error)

    assert discovery.get_pip_version(sys.executable) == "unknown"
