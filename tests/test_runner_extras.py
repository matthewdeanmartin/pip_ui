"""Tests for runner.py extras — build_prefix logic for each run_via value."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pip_ui.runner import PipRunner
from pip_ui.tools import get_plugin


def test_build_prefix_pip_default() -> None:
    runner = PipRunner()
    plugin = get_plugin("pip")
    prefix = runner.build_prefix("/usr/bin/python", plugin)
    assert prefix == ["/usr/bin/python", "-m", "pip"]


def test_build_prefix_pip_without_plugin() -> None:
    runner = PipRunner()
    prefix = runner.build_prefix("/usr/bin/python", None)
    assert prefix == ["/usr/bin/python", "-m", "pip"]


def test_build_prefix_build_module() -> None:
    runner = PipRunner()
    plugin = get_plugin("build")
    assert plugin is not None
    prefix = runner.build_prefix("/usr/bin/python", plugin)
    assert prefix == ["/usr/bin/python", "-m", "build"]


def test_build_prefix_virtualenv_module() -> None:
    runner = PipRunner()
    plugin = get_plugin("virtualenv")
    assert plugin is not None
    prefix = runner.build_prefix("/usr/bin/python", plugin)
    assert prefix == ["/usr/bin/python", "-m", "virtualenv"]


def test_build_prefix_pip_audit_module() -> None:
    runner = PipRunner()
    plugin = get_plugin("pip-audit")
    assert plugin is not None
    prefix = runner.build_prefix("/usr/bin/python", plugin)
    assert prefix == ["/usr/bin/python", "-m", "pip_audit"]


def test_build_prefix_global_cli_falls_back_to_which(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = PipRunner()
    plugin = get_plugin("twine")
    assert plugin is not None

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/local/bin/{name}")
    # interpreter dir won't have twine next to it for a fake path
    prefix = runner.build_prefix("/fake/python", plugin)
    assert "/usr/local/bin/twine" in prefix


def test_build_prefix_global_cli_uses_interpreter_local_first(tmp_path: Path) -> None:
    runner = PipRunner()
    plugin = get_plugin("hatch")
    assert plugin is not None

    # Create a fake Scripts/hatch.exe next to interpreter
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    exe = scripts / "hatch.exe"
    exe.write_bytes(b"")
    exe.chmod(0o755)

    python_path = str(scripts / "python.exe")
    prefix = runner.build_prefix(python_path, plugin)
    # Should prefer the interpreter-local copy
    assert any("hatch" in p for p in prefix)


def test_build_argv_with_plugin() -> None:
    runner = PipRunner()
    plugin = get_plugin("build")
    assert plugin is not None
    argv = runner.build_argv("/usr/bin/python", ["--wheel"], plugin)
    assert argv == ["/usr/bin/python", "-m", "build", "--wheel"]


def test_redact_argv_secret_flag() -> None:
    argv = ["twine", "upload", "--password", "s3cr3t", "dist/*.whl"]
    result = PipRunner.redact_argv(argv, secret_flags=["--password"])
    assert result[3] == "<redacted>"
    assert result[2] == "--password"
    assert result[4] == "dist/*.whl"


def test_redact_argv_no_secret_flags() -> None:
    argv = ["twine", "upload", "--verbose", "dist/*.whl"]
    result = PipRunner.redact_argv(argv)
    assert result == argv


def test_redact_argv_multiple_secret_flags() -> None:
    argv = ["hatch", "publish", "--auth", "token123", "--user", "bob"]
    result = PipRunner.redact_argv(argv, secret_flags=["--auth"])
    assert result[3] == "<redacted>"
    assert result[5] == "bob"  # --user not in secret_flags
