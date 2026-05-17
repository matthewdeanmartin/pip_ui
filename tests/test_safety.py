"""Tests for safety module."""

from pip_ui.models import InterpreterInfo, SafetyLevel
from pip_ui.safety import (
    check_global_install,
    classify_command,
    confirmation_message,
    needs_confirmation,
    redact_url,
)


def test_readonly_commands():
    for cmd in ("list", "show", "freeze", "check"):
        assert classify_command(cmd) == SafetyLevel.READ_ONLY, f"{cmd} should be READ_ONLY"


def test_modifies_env():
    level = classify_command("install")
    assert level in (SafetyLevel.MODIFIES_ENV, SafetyLevel.DESTRUCTIVE, SafetyLevel.RISKY_CONFIG)


def test_destructive():
    assert classify_command("uninstall") == SafetyLevel.DESTRUCTIVE


def test_redact_url_with_creds():
    url = "https://myuser:mypassword@pypi.example.com/simple"
    result = redact_url(url)
    assert "myuser" not in result
    assert "mypassword" not in result
    assert "<redacted>:<redacted>@" in result
    assert "pypi.example.com" in result


def test_redact_url_no_creds():
    url = "https://pypi.org/simple"
    result = redact_url(url)
    assert result == url


def test_redact_url_http_with_creds():
    url = "http://admin:secret@internal.example.com/packages"
    result = redact_url(url)
    assert "admin" not in result
    assert "secret" not in result


def test_needs_confirmation_readonly():
    assert needs_confirmation(SafetyLevel.READ_ONLY) is False


def test_needs_confirmation_modifies_env():
    assert needs_confirmation(SafetyLevel.MODIFIES_ENV) is False


def test_needs_confirmation_destructive():
    assert needs_confirmation(SafetyLevel.DESTRUCTIVE) is True


def test_needs_confirmation_risky_config():
    assert needs_confirmation(SafetyLevel.RISKY_CONFIG) is True


def test_check_global_install_warns_for_system():
    info = InterpreterInfo(
        path="/usr/bin/python3",
        version="3.11.0",
        pip_version="23.0",
        is_venv=False,
        prefix="/usr",
        base_prefix="/usr",
        env_type="system",
    )
    warning = check_global_install(info)
    assert warning is not None
    assert len(warning) > 0


def test_check_global_install_no_warn_for_venv():
    info = InterpreterInfo(
        path="/home/user/.venv/bin/python",
        version="3.11.0",
        pip_version="23.0",
        is_venv=True,
        prefix="/home/user/.venv",
        base_prefix="/usr",
        env_type="venv",
    )
    warning = check_global_install(info)
    assert warning is None


def test_confirmation_message_returns_string():
    msg = confirmation_message("uninstall")
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_confirmation_message_unknown_command():
    msg = confirmation_message("some_unknown_command")
    assert isinstance(msg, str)
    assert len(msg) > 0
