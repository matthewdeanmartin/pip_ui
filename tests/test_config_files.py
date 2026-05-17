"""Tests for config file discovery parsing and diagnostics expansion."""

from __future__ import annotations

import json
import os
import sys

from pip_ui.config_inspector import (
    ConfigInspector,
    IndexInfo,
    parse_config_files,
    parse_config_list,
)


def test_parse_config_list_basic():
    raw = "global.index-url = https://pypi.org/simple\nglobal.timeout = 60\n"
    result = parse_config_list(raw)
    assert result["global.index-url"] == "https://pypi.org/simple"
    assert result["global.timeout"] == "60"


def test_parse_config_list_ignores_blanks():
    raw = "\n\nglobal.index-url = https://pypi.org/simple\n\n"
    assert parse_config_list(raw) == {"global.index-url": "https://pypi.org/simple"}


def test_parse_config_files_finds_paths_unix():
    sample = (
        "env_var:\n"
        "    PIP_INDEX_URL\n"
        "env:\n"
        "    <none>\n"
        "global:\n"
        "    /etc/pip.conf, exists: False\n"
        "user:\n"
        "    /home/u/.pip/pip.conf, exists: True\n"
        "site:\n"
        "    /home/u/.venv/pip.conf, exists: False\n"
    )
    files = parse_config_files(sample)
    paths = [f.path for f in files]
    scopes = [f.scope for f in files]
    assert "/etc/pip.conf" in paths
    assert "/home/u/.pip/pip.conf" in paths
    assert "/home/u/.venv/pip.conf" in paths
    assert "global" in scopes
    assert "user" in scopes
    assert "site" in scopes


def test_parse_config_files_handles_windows_paths():
    sample = (
        "global:\n"
        "    C:\\ProgramData\\pip\\pip.ini, exists: False\n"
        "user:\n"
        "    C:\\Users\\u\\AppData\\Roaming\\pip\\pip.ini, exists: False\n"
    )
    files = parse_config_files(sample)
    assert len(files) == 2
    paths = [f.path for f in files]
    assert "C:\\ProgramData\\pip\\pip.ini" in paths


def test_parse_config_files_empty():
    assert not parse_config_files("")


def test_detect_index_info_returns_dataclass():
    inspector = ConfigInspector(sys.executable)
    info = inspector.detect_index_info()
    assert isinstance(info, IndexInfo)
    assert isinstance(info.extra_index_urls, list)
    assert isinstance(info.find_links, list)
    assert isinstance(info.trusted_hosts, list)


def test_diagnostics_markdown_includes_os_and_workdir():
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report(
        "markdown", last_command="pip list", last_exit_code=0, working_directory="/tmp"
    )
    assert "OS:" in report
    assert "/tmp" in report
    assert "Last Command" in report
    assert "pip list" in report


def test_diagnostics_json_includes_new_fields():
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report(
        "json", last_command="pip list", last_exit_code=0, working_directory="/tmp"
    )
    data = json.loads(report)
    assert data["working_directory"] == "/tmp"
    assert data["last_command"] == "pip list"
    assert data["last_exit_code"] == 0
    assert "os" in data
    assert "config_files" in data
    assert "index" in data
    assert "cache_info" in data


def test_diagnostics_text_format_includes_workdir():
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report(
        "text", last_command="pip list", last_exit_code=1, working_directory="/some/where"
    )
    assert "/some/where" in report
    assert "pip list" in report


def test_env_vars_redact_default():
    os.environ["PIP_INDEX_URL_TEST_REDACT"] = "https://user:secret@example.com/simple"
    try:
        inspector = ConfigInspector(sys.executable)
        # The actual var name is PIP_INDEX_URL_TEST_REDACT — it starts with PIP_
        env_vars = inspector.get_env_vars(show_secrets=False)
        val = env_vars.get("PIP_INDEX_URL_TEST_REDACT", "")
        assert "secret" not in val
        env_vars_unredacted = inspector.get_env_vars(show_secrets=True)
        assert env_vars_unredacted.get("PIP_INDEX_URL_TEST_REDACT") == "https://user:secret@example.com/simple"
    finally:
        del os.environ["PIP_INDEX_URL_TEST_REDACT"]
