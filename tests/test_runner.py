"""Tests for runner module."""

from pip_ui.runner import PipRunner


def test_build_argv():
    runner = PipRunner()
    result = runner.build_argv("/usr/bin/python", ["install", "requests"])
    assert result == ["/usr/bin/python", "-m", "pip", "install", "requests"]


def test_build_argv_empty_pip_args():
    runner = PipRunner()
    result = runner.build_argv("/usr/bin/python", [])
    assert result == ["/usr/bin/python", "-m", "pip"]


def test_redact_argv_no_credentials():
    argv = ["/usr/bin/python", "-m", "pip", "install", "--index-url", "https://pypi.org/simple"]
    result = PipRunner.redact_argv(argv)
    assert result == argv


def test_redact_argv_with_credentials():
    argv = ["/usr/bin/python", "-m", "pip", "install", "--index-url", "https://user:pass@pypi.example.com/simple"]
    result = PipRunner.redact_argv(argv)
    assert "user" not in result[5]
    assert "pass" not in result[5]
    assert "<redacted>:<redacted>@" in result[5]


def test_redact_argv_preserves_safe_args():
    argv = ["python", "-m", "pip", "list", "--format", "json"]
    result = PipRunner.redact_argv(argv)
    assert result == argv


def test_format_command():
    runner = PipRunner()
    argv = ["/usr/bin/python", "-m", "pip", "install", "requests"]
    result = runner.format_command(argv)
    assert isinstance(result, str)
    assert "pip" in result
    assert "install" in result
    assert "requests" in result


def test_format_command_quotes_spaces():
    runner = PipRunner()
    argv = ["python", "-m", "pip", "install", "some package"]
    result = runner.format_command(argv)
    assert '"some package"' in result


def test_cancel_no_process():
    runner = PipRunner()
    runner.cancel()
