"""Tests for argv-based safety warnings and error hints."""

from pip_ui.models import SafetyLevel
from pip_ui.safety import (
    classify_command,
    collect_argv_warnings,
    confirmation_message,
    contains_credentials,
    explain_pip_error,
)


def test_warn_break_system_packages():
    warnings = collect_argv_warnings(["install", "requests", "--break-system-packages"])
    assert any("break-system-packages" in w for w in warnings)


def test_warn_trusted_host():
    warnings = collect_argv_warnings(["install", "requests", "--trusted-host", "internal.example.com"])
    assert any("trusted-host" in w.lower() for w in warnings)


def test_warn_user_install():
    warnings = collect_argv_warnings(["install", "requests", "--user"])
    assert any("--user" in w for w in warnings)


def test_warn_http():
    warnings = collect_argv_warnings(["install", "requests", "-i", "http://internal/simple"])
    assert any("http://" in w for w in warnings)


def test_warn_credentials_in_url():
    warnings = collect_argv_warnings(["install", "requests", "-i", "https://u:p@internal.example.com/simple"])
    assert any("credential" in w.lower() for w in warnings)


def test_warn_no_index_without_find_links():
    warnings = collect_argv_warnings(["install", "requests", "--no-index"])
    assert any("no-index" in w.lower() for w in warnings)


def test_no_warn_no_index_with_find_links():
    warnings = collect_argv_warnings(["install", "requests", "--no-index", "-f", "./wh"])
    assert all("no source" not in w for w in warnings)


def test_no_warn_for_plain_install():
    warnings = collect_argv_warnings(["install", "requests"])
    assert not warnings


def test_contains_credentials_yes():
    assert contains_credentials("https://user:pw@example.com/pkg") is True


def test_contains_credentials_no():
    assert contains_credentials("https://example.com/simple/") is False


def test_classify_new_commands():
    assert classify_command("inspect") == SafetyLevel.READ_ONLY
    assert classify_command("download") == SafetyLevel.MODIFIES_ENV
    assert classify_command("wheel") == SafetyLevel.MODIFIES_ENV
    assert classify_command("config_set") == SafetyLevel.RISKY_CONFIG
    assert classify_command("config_unset") == SafetyLevel.RISKY_CONFIG
    assert classify_command("config_edit") == SafetyLevel.RISKY_CONFIG
    assert classify_command("config_get") == SafetyLevel.READ_ONLY
    assert classify_command("cache_remove") == SafetyLevel.DESTRUCTIVE
    assert classify_command("cache_purge") == SafetyLevel.DESTRUCTIVE
    assert classify_command("cache_list") == SafetyLevel.READ_ONLY


def test_confirmation_messages_for_destructive():
    for cmd in ("uninstall", "cache_purge", "cache_remove", "config_set", "config_unset"):
        msg = confirmation_message(cmd)
        assert isinstance(msg, str)
        assert len(msg) > 10


def test_explain_externally_managed():
    stderr = "error: externally-managed-environment\n\nThis environment is managed."
    hints = explain_pip_error(stderr)
    assert any("externally managed" in h.lower() or "external" in h.lower() for h in hints)


def test_explain_no_matching_distribution():
    hints = explain_pip_error("ERROR: No matching distribution found for foo==9.9.9")
    assert any("matching distribution" in h.lower() or "index-url" in h.lower() for h in hints)


def test_explain_ssl():
    hints = explain_pip_error("ssl certificate verify failed")
    assert any("ssl" in h.lower() for h in hints)


def test_explain_unknown_returns_empty():
    assert not explain_pip_error("some completely unrelated output")
