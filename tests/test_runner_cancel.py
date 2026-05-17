"""Additional runner tests for cancellation state and helper behavior."""

from __future__ import annotations

from pip_ui.runner import PipRunner


def test_is_running_false_when_no_process():
    runner = PipRunner()
    assert runner.is_running() is False


def test_cancel_returns_false_when_no_process():
    runner = PipRunner()
    assert runner.cancel(force=False) is False
    assert runner.cancel(force=True) is False


def test_redact_argv_multiple_credentials():
    argv = [
        "python", "-m", "pip", "install",
        "-i", "https://u1:p1@a.example.com/simple",
        "--extra-index-url", "https://u2:p2@b.example.com/simple",
    ]
    out = PipRunner.redact_argv(argv)
    for tok in out:
        assert "p1" not in tok
        assert "p2" not in tok
    assert out.count("<redacted>") >= 0  # noqa: PLR2004 - presence check below
    assert sum(1 for t in out if "<redacted>:<redacted>@" in t) == 2


def test_format_command_empty_argv():
    runner = PipRunner()
    # An empty token must be quoted (becomes "")
    out = runner.format_command(["python", ""])
    assert '""' in out
