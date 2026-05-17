"""Tests for config_inspector module."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import pytest

from pip_ui.config_inspector import ConfigInspector, parse_config_list
from pip_ui.safety import redact_url


def test_parse_config_list() -> None:
    raw = "global.index-url = https://pypi.org/simple\nglobal.timeout = 60\n"
    result = parse_config_list(raw)
    assert result["global.index-url"] == "https://pypi.org/simple"
    assert result["global.timeout"] == "60"


def test_redact_env_vars() -> None:
    url_with_creds = "https://user:secret@pypi.example.com/simple"
    result = redact_url(url_with_creds)
    assert "user" not in result
    assert "secret" not in result
    assert "pypi.example.com" in result


def test_get_env_vars_returns_dict() -> None:
    inspector = ConfigInspector(sys.executable)
    env_vars = inspector.get_env_vars()
    assert isinstance(env_vars, dict)


def test_get_pip_version_returns_string() -> None:
    inspector = ConfigInspector(sys.executable)
    version = inspector.get_pip_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_run_config_list_returns_dict() -> None:
    inspector = ConfigInspector(sys.executable)
    result = inspector.run_config_list()
    assert isinstance(result, dict)


def test_build_diagnostics_report_markdown() -> None:
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report("markdown")
    assert isinstance(report, str)
    assert "pip" in report.lower()


def test_build_diagnostics_report_json() -> None:
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report("json")
    data = json.loads(report)
    assert "pip_version" in data
    assert "config_values" in data
    assert "env_vars" in data


def test_build_diagnostics_report_text() -> None:
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report("text")
    assert isinstance(report, str)


def test_detect_index_info_reads_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    inspector = ConfigInspector(sys.executable)
    monkeypatch.setattr(inspector, "run_config_list", lambda: {})
    monkeypatch.setattr(
        inspector,
        "get_env_vars",
        lambda show_secrets=False: {
            "PIP_INDEX_URL": "https://user:secret@example.com/simple",
            "PIP_EXTRA_INDEX_URL": "https://extra1/simple https://extra2/simple",
            "PIP_TRUSTED_HOST": "internal.example.com mirror.example.com",
            "PIP_FIND_LINKS": "https://wheels/simple",
            "PIP_NO_INDEX": "true",
        },
    )

    info = inspector.detect_index_info()

    assert info.main_index_url == "https://user:secret@example.com/simple"
    assert info.extra_index_urls == ["https://extra1/simple", "https://extra2/simple"]
    assert info.trusted_hosts == ["internal.example.com", "mirror.example.com"]
    assert info.find_links == ["https://wheels/simple"]
    assert info.no_index is True
    assert info.has_credentials is True


def test_run_pip_command_uses_utf8_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(args=["python"], returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    inspector = ConfigInspector(sys.executable)
    stdout, stderr, returncode = inspector.run_pip_command(["inspect"])

    assert stdout == "{}"
    assert stderr == ""
    assert returncode == 0
    assert captured["text"] is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["env"]["PYTHONUTF8"] == "1"
    assert captured["env"]["PYTHONIOENCODING"] == "utf-8"
