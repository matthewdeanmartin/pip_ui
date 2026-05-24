"""Unit tests for pypiserver_tool.py — plugin metadata validation."""

from __future__ import annotations

import pytest

from pip_ui.tools.pypiserver_tool import PYPISERVER_PLUGIN


def test_pypiserver_plugin_run_via():
    assert PYPISERVER_PLUGIN.run_via == "global_cli"
    assert PYPISERVER_PLUGIN.executable == "pypi-server"


def test_pypiserver_has_run_spec():
    assert "pypiserver_run" in PYPISERVER_PLUGIN.command_specs


def test_pypiserver_has_update_spec():
    assert "pypiserver_update" in PYPISERVER_PLUGIN.command_specs


def test_pypiserver_has_version_spec():
    assert "pypiserver_version" in PYPISERVER_PLUGIN.command_specs


def test_pypiserver_plugin_has_panel_class():
    pytest.importorskip("tkinter")
    assert PYPISERVER_PLUGIN.panel_class is not None


def test_pypiserver_run_has_port_arg():
    spec = PYPISERVER_PLUGIN.command_specs["pypiserver_run"]
    arg_names = {a.name for a in spec.args}
    assert "port" in arg_names


def test_pypiserver_run_has_packages_dir():
    spec = PYPISERVER_PLUGIN.command_specs["pypiserver_run"]
    pkg_arg = next(a for a in spec.args if a.name == "packages_dir")
    assert pkg_arg.required


def test_pypiserver_help_url():
    assert PYPISERVER_PLUGIN.help_url.startswith("http")


def test_pypiserver_all_specs_in_declared_groups():
    for spec in PYPISERVER_PLUGIN.command_specs.values():
        assert spec.group in PYPISERVER_PLUGIN.command_groups
