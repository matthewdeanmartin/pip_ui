"""Smoke tests for custom panel widget construction (no display needed)."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="module")
def root():
    try:
        r = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tkinter not available: {exc}")
    r.withdraw()
    yield r
    r.destroy()


def _form_kwargs(root):
    return dict(
        on_run=MagicMock(),
        on_form_change=MagicMock(),
        global_values_provider=lambda: {},
        on_open_global_options=MagicMock(),
        global_requirements_provider=lambda: None,
    )


# ---- VirtualenvPanel --------------------------------------------------------


def test_virtualenv_panel_constructs(root):
    from pip_ui.ui.virtualenv_panel import VirtualenvPanel

    panel = VirtualenvPanel(root, **_form_kwargs(root))
    assert panel.command_form is not None
    panel.destroy()


def test_virtualenv_panel_activate_btn_disabled_initially(root):
    from pip_ui.ui.virtualenv_panel import VirtualenvPanel

    panel = VirtualenvPanel(root, **_form_kwargs(root))
    assert str(panel._activate_btn["state"]) == "disabled"
    panel.destroy()


def test_virtualenv_panel_activate_btn_enabled_after_create(root):
    from pip_ui.ui.virtualenv_panel import VirtualenvPanel

    panel = VirtualenvPanel(root, **_form_kwargs(root))
    panel.notify_run_done(0, "create", [".venv"])
    assert str(panel._activate_btn["state"]) == "normal"
    panel.destroy()


def test_virtualenv_panel_activate_btn_stays_disabled_on_error(root):
    from pip_ui.ui.virtualenv_panel import VirtualenvPanel

    panel = VirtualenvPanel(root, **_form_kwargs(root))
    panel.notify_run_done(1, "create", [".venv"])
    assert str(panel._activate_btn["state"]) == "disabled"
    panel.destroy()


def test_virtualenv_panel_delegates_spec(root):
    from pip_ui.tools.virtualenv_tool import VIRTUALENV_PLUGIN
    from pip_ui.ui.virtualenv_panel import VirtualenvPanel

    panel = VirtualenvPanel(root, **_form_kwargs(root))
    spec = VIRTUALENV_PLUGIN.command_specs["create"]
    panel.set_command(spec)
    assert panel.spec is not None
    assert panel.spec.name == "create"
    panel.destroy()


# ---- HatchEnvPanel ----------------------------------------------------------


def test_hatch_env_panel_constructs(root):
    from pip_ui.ui.hatch_env_panel import HatchEnvPanel

    panel = HatchEnvPanel(root, **_form_kwargs(root))
    assert panel.command_form is not None
    assert panel._tree is not None
    panel.destroy()


def test_hatch_env_panel_has_tree_columns(root):
    from pip_ui.ui.hatch_env_panel import HatchEnvPanel

    panel = HatchEnvPanel(root, **_form_kwargs(root))
    cols = panel._tree["columns"]
    assert "name" in cols
    assert "path" in cols
    panel.destroy()


def test_hatch_env_panel_set_workdir(root):
    from pip_ui.ui.hatch_env_panel import HatchEnvPanel

    panel = HatchEnvPanel(root, **_form_kwargs(root))
    panel.set_workdir("/some/project")
    assert panel._workdir == "/some/project"
    panel.destroy()


# ---- PipxAppsPanel ----------------------------------------------------------


def test_pipx_apps_panel_constructs(root):
    from pip_ui.ui.pipx_apps_panel import PipxAppsPanel

    panel = PipxAppsPanel(root, **_form_kwargs(root))
    assert panel.command_form is not None
    assert panel._tree is not None
    panel.destroy()


def test_pipx_apps_panel_has_expected_columns(root):
    from pip_ui.ui.pipx_apps_panel import PipxAppsPanel

    panel = PipxAppsPanel(root, **_form_kwargs(root))
    cols = panel._tree["columns"]
    assert "app" in cols
    assert "version" in cols
    assert "path" in cols
    panel.destroy()


def test_pipx_apps_panel_notify_run_done_no_crash(root):
    from pip_ui.ui.pipx_apps_panel import PipxAppsPanel

    panel = PipxAppsPanel(root, **_form_kwargs(root))
    # Should not raise even if pipx isn't installed
    panel.notify_run_done(0, "pipx_install", [])
    panel.destroy()
