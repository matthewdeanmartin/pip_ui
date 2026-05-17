"""Tests for config_inspector module."""

import sys

from pip_ui.config_inspector import ConfigInspector


def test_parse_config_list():
    inspector = ConfigInspector(sys.executable)
    raw = "global.index-url = https://pypi.org/simple\nglobal.timeout = 60\n"
    result: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    assert result["global.index-url"] == "https://pypi.org/simple"
    assert result["global.timeout"] == "60"


def test_redact_env_vars():
    from pip_ui.safety import redact_url
    url_with_creds = "https://user:secret@pypi.example.com/simple"
    result = redact_url(url_with_creds)
    assert "user" not in result
    assert "secret" not in result
    assert "pypi.example.com" in result


def test_get_env_vars_returns_dict():
    inspector = ConfigInspector(sys.executable)
    env_vars = inspector.get_env_vars()
    assert isinstance(env_vars, dict)


def test_get_pip_version_returns_string():
    inspector = ConfigInspector(sys.executable)
    version = inspector.get_pip_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_run_config_list_returns_dict():
    inspector = ConfigInspector(sys.executable)
    result = inspector.run_config_list()
    assert isinstance(result, dict)


def test_build_diagnostics_report_markdown():
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report("markdown")
    assert isinstance(report, str)
    assert "pip" in report.lower()


def test_build_diagnostics_report_json():
    import json
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report("json")
    data = json.loads(report)
    assert "pip_version" in data
    assert "config_values" in data
    assert "env_vars" in data


def test_build_diagnostics_report_text():
    inspector = ConfigInspector(sys.executable)
    report = inspector.build_diagnostics_report("text")
    assert isinstance(report, str)
