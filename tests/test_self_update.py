"""Tests for pip_ui.self_update."""

from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.request

import pytest

from pip_ui import self_update
from pip_ui.self_update import UpgradeInfo, fetch_latest_version, is_newer, parse_version


def test_parse_version_simple() -> None:
    assert parse_version("0.1.0") == (0, 1, 0)
    assert parse_version("12.34.56") == (12, 34, 56)


def test_parse_version_with_suffix() -> None:
    # Anything after a non-digit in a chunk is truncated.
    assert parse_version("1.2.3rc1") == (1, 2, 3)
    assert parse_version("1.2") == (1, 2)


def test_parse_version_garbage_falls_back_to_zero() -> None:
    assert parse_version("not-a-version") == (0,)


def test_is_newer_basic() -> None:
    assert is_newer("0.2.0", "0.1.0") is True
    assert is_newer("0.1.1", "0.1.0") is True
    assert is_newer("0.1.0", "0.1.0") is False
    assert is_newer("0.0.9", "0.1.0") is False


def test_fetch_latest_version_reads_pypi_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_latest_version should parse the version from the PyPI payload."""
    seen: dict[str, object] = {}

    def fake_urlopen(request: urllib.request.Request, timeout: float = 0.0) -> io.StringIO:
        seen["url"] = request.full_url
        seen["user_agent"] = request.get_header("User-agent")
        seen["timeout"] = timeout
        return io.StringIO(json.dumps({"info": {"version": "0.2.0"}}))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert fetch_latest_version(timeout=7.5) == "0.2.0"
    assert seen == {
        "url": self_update.PYPI_URL,
        "user_agent": self_update.USER_AGENT,
        "timeout": 7.5,
    }


def test_fetch_latest_version_returns_none_on_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-string version data should be ignored."""
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout=0.0: io.StringIO(json.dumps({"info": {"version": 123}})),
    )

    assert fetch_latest_version() is None


def test_fetch_latest_version_returns_none_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network failures should return None rather than raising."""

    def fake_urlopen(request: urllib.request.Request, timeout: float = 0.0) -> io.StringIO:
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert fetch_latest_version() is None


def test_check_latest_version_reports_upgrade_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """check_latest_version should invoke the callback with upgrade details."""
    seen: dict[str, object] = {}

    class FakeThread:
        def __init__(self, *, target: object, daemon: bool, name: str) -> None:
            seen["target"] = target
            seen["daemon"] = daemon
            seen["name"] = name

        def start(self) -> None:
            target = seen["target"]
            assert callable(target)
            target()

    monkeypatch.setattr(threading, "Thread", FakeThread)
    monkeypatch.setattr(self_update, "fetch_latest_version", lambda: "0.2.0")

    results: list[UpgradeInfo | None] = []
    self_update.check_latest_version("0.1.0", results.append)

    assert results == [UpgradeInfo(current="0.1.0", latest="0.2.0", available=True)]
    assert seen["daemon"] is True
    assert seen["name"] == "pip-ui-update-check"


def test_check_latest_version_reports_none_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """check_latest_version should surface fetch failures as None."""

    class FakeThread:
        def __init__(self, *, target: object, daemon: bool, name: str) -> None:
            self.target = target

        def start(self) -> None:
            assert callable(self.target)
            self.target()

    monkeypatch.setattr(threading, "Thread", FakeThread)
    monkeypatch.setattr(self_update, "fetch_latest_version", lambda: None)

    results: list[UpgradeInfo | None] = []
    self_update.check_latest_version("0.1.0", results.append)

    assert results == [None]
