"""Tests for proxy_utils pure-function helpers."""

from __future__ import annotations

from pip_ui.ui.proxy_utils import proxy_env_summary, redact_proxy_url, url_contains_credentials

# ---------------------------------------------------------------- redact_proxy_url


def test_redact_no_credentials() -> None:
    url = "http://proxy.corp.example.com:8080"
    assert redact_proxy_url(url) == url


def test_redact_replaces_user_and_password() -> None:
    url = "http://alice:s3cr3t@proxy.corp.example.com:8080"
    result = redact_proxy_url(url)
    assert "alice" not in result
    assert "s3cr3t" not in result
    assert "<redacted>:<redacted>@" in result


def test_redact_preserves_host_and_port() -> None:
    url = "https://user:pass@proxy.example.com:3128"
    result = redact_proxy_url(url)
    assert "proxy.example.com:3128" in result


def test_redact_https_scheme() -> None:
    url = "https://u:p@secure-proxy.corp:443"
    result = redact_proxy_url(url)
    assert result.startswith("https://")
    assert "<redacted>:<redacted>@" in result


# ---------------------------------------------------------------- url_contains_credentials


def test_no_credentials_returns_false() -> None:
    assert url_contains_credentials("http://proxy.example.com:8080") is False


def test_empty_string_returns_false() -> None:
    assert url_contains_credentials("") is False


def test_credentials_present_returns_true() -> None:
    assert url_contains_credentials("http://user:pass@proxy.example.com") is True


def test_user_only_no_password_returns_false() -> None:
    # pattern requires user:password — bare user without colon+password is not flagged
    assert url_contains_credentials("http://user@proxy.example.com") is False


# ---------------------------------------------------------------- proxy_env_summary


def test_empty_env_returns_empty_string() -> None:
    assert proxy_env_summary({}) == ""


def test_returns_only_known_keys() -> None:
    env = {"UNRELATED": "value", "HTTP_PROXY": "http://proxy:8080"}
    result = proxy_env_summary(env)
    assert "UNRELATED" not in result
    assert "HTTP_PROXY=http://proxy:8080" in result


def test_redacts_password_in_env() -> None:
    env = {"HTTPS_PROXY": "https://user:secret@proxy.corp.com:443"}
    result = proxy_env_summary(env)
    assert "secret" not in result
    assert "<redacted>:<redacted>@" in result


def test_multiple_env_vars_each_on_own_line() -> None:
    env = {"HTTP_PROXY": "http://proxy:80", "HTTPS_PROXY": "https://proxy:443"}
    lines = proxy_env_summary(env).splitlines()
    assert len(lines) == 2
    keys = {line.split("=")[0] for line in lines}
    assert keys == {"HTTP_PROXY", "HTTPS_PROXY"}


def test_no_proxy_included() -> None:
    env = {"NO_PROXY": "localhost,127.0.0.1"}
    result = proxy_env_summary(env)
    assert "NO_PROXY=localhost,127.0.0.1" in result


def test_lowercase_keys_included() -> None:
    env = {"http_proxy": "http://lower:8080"}
    result = proxy_env_summary(env)
    assert "http_proxy=http://lower:8080" in result
