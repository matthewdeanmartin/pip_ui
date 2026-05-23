"""Unit tests for devpi_tool.py — plugin validation."""

from __future__ import annotations

from pip_ui.tools.devpi_tool import DEVPI_PLUGIN


def test_devpi_plugin_run_via():
    assert DEVPI_PLUGIN.run_via == "global_cli"
    assert DEVPI_PLUGIN.executable == "devpi"


def test_devpi_has_use_spec():
    assert "devpi_use" in DEVPI_PLUGIN.command_specs


def test_devpi_has_login_spec():
    assert "devpi_login" in DEVPI_PLUGIN.command_specs


def test_devpi_has_upload_spec():
    assert "devpi_upload" in DEVPI_PLUGIN.command_specs


def test_devpi_has_index_create_spec():
    assert "devpi_index_create" in DEVPI_PLUGIN.command_specs


def test_devpi_has_index_list_spec():
    assert "devpi_index_list" in DEVPI_PLUGIN.command_specs


def test_devpi_secret_flags():
    assert "--password" in DEVPI_PLUGIN.secret_flags


def test_devpi_login_has_password_secret():
    spec = DEVPI_PLUGIN.command_specs["devpi_login"]
    secret_arg = next((a for a in spec.args if a.name == "password"), None)
    assert secret_arg is not None
    assert secret_arg.field_type == "secret"


def test_devpi_plugin_has_panel_class():
    assert DEVPI_PLUGIN.panel_class is not None


def test_devpi_help_url():
    assert DEVPI_PLUGIN.help_url.startswith("http")


def test_devpi_all_specs_in_declared_groups():
    for spec in DEVPI_PLUGIN.command_specs.values():
        assert spec.group in DEVPI_PLUGIN.command_groups
