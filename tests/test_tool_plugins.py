"""Unit tests for *_tool.py modules — argv list validation."""

from __future__ import annotations

from pip_ui.tools import get_plugin, get_registry
from pip_ui.tools.build_tool import BUILD_PLUGIN
from pip_ui.tools.flit_tool import FLIT_PLUGIN
from pip_ui.tools.hatch_tool import HATCH_PLUGIN
from pip_ui.tools.pip_audit_tool import PIP_AUDIT_PLUGIN
from pip_ui.tools.pip_tool import PIP_PLUGIN
from pip_ui.tools.pipx_tool import PIPX_PLUGIN
from pip_ui.tools.twine_tool import TWINE_PLUGIN
from pip_ui.tools.virtualenv_tool import VIRTUALENV_PLUGIN

# ---- registry ---------------------------------------------------------------


def test_registry_contains_all_tools():
    registry = get_registry()
    names = {p.name for p in registry}
    assert names == {"pip", "build", "virtualenv", "twine", "pip-audit", "hatch", "flit", "pipx", "pypiserver", "devpi"}


def test_get_plugin_pip():
    plugin = get_plugin("pip")
    assert plugin is not None
    assert plugin.name == "pip"


def test_get_plugin_missing():
    assert get_plugin("nonexistent") is None


def test_all_plugins_have_help_url():
    for plugin in get_registry():
        assert plugin.help_url.startswith("http"), f"{plugin.name} missing help_url"


def test_all_plugins_have_command_specs():
    for plugin in get_registry():
        assert plugin.command_specs, f"{plugin.name} has no command_specs"


def test_all_plugins_have_command_groups():
    for plugin in get_registry():
        assert plugin.command_groups, f"{plugin.name} has no command_groups"


def test_all_specs_in_a_declared_group():
    for plugin in get_registry():
        for spec in plugin.command_specs.values():
            assert (
                spec.group in plugin.command_groups
            ), f"{plugin.name}/{spec.name}: group '{spec.group}' not in {plugin.command_groups}"


# ---- pip ----------------------------------------------------------------


def test_pip_plugin_install_spec():
    spec = PIP_PLUGIN.command_specs["install"]
    assert spec.label == "Install"
    arg_names = {a.name for a in spec.args}
    assert "packages" in arg_names
    assert "upgrade" in arg_names


def test_pip_plugin_run_via():
    assert PIP_PLUGIN.run_via == "python_module"
    assert PIP_PLUGIN.module == "pip"


# ---- build ---------------------------------------------------------------


def test_build_plugin_has_build_spec():
    assert "build" in BUILD_PLUGIN.command_specs


def test_build_plugin_run_via():
    assert BUILD_PLUGIN.run_via == "python_module"
    assert BUILD_PLUGIN.module == "build"


def test_build_spec_args_include_outdir():
    spec = BUILD_PLUGIN.command_specs["build"]
    flags = {a.flag for a in spec.args}
    assert "--outdir" in flags


# ---- virtualenv ---------------------------------------------------------


def test_virtualenv_plugin_run_via():
    assert VIRTUALENV_PLUGIN.run_via == "python_module"
    assert VIRTUALENV_PLUGIN.module == "virtualenv"


def test_virtualenv_create_has_dest():
    spec = VIRTUALENV_PLUGIN.command_specs["create"]
    arg_names = {a.name for a in spec.args}
    assert "dest" in arg_names


def test_virtualenv_create_dest_is_required():
    spec = VIRTUALENV_PLUGIN.command_specs["create"]
    dest_arg = next(a for a in spec.args if a.name == "dest")
    assert dest_arg.required


def test_virtualenv_plugin_has_panel_class():
    assert VIRTUALENV_PLUGIN.panel_class is not None


# ---- twine --------------------------------------------------------------


def test_twine_plugin_run_via():
    assert TWINE_PLUGIN.run_via == "global_cli"
    assert TWINE_PLUGIN.executable == "twine"


def test_twine_upload_has_password_secret():
    spec = TWINE_PLUGIN.command_specs["twine_upload"]
    secret_arg = next((a for a in spec.args if a.name == "password"), None)
    assert secret_arg is not None
    assert secret_arg.field_type == "secret"


def test_twine_secret_flags_include_password():
    assert "--password" in TWINE_PLUGIN.secret_flags


# ---- pip-audit ----------------------------------------------------------


def test_pip_audit_plugin_run_via():
    assert PIP_AUDIT_PLUGIN.run_via == "python_module"
    assert PIP_AUDIT_PLUGIN.module == "pip_audit"


def test_pip_audit_output_format_choices():
    spec = PIP_AUDIT_PLUGIN.command_specs["audit"]
    fmt_arg = next(a for a in spec.args if a.name == "output_format")
    assert "json" in fmt_arg.choices
    assert "columns" in fmt_arg.choices


# ---- hatch ---------------------------------------------------------------


def test_hatch_plugin_run_via():
    assert HATCH_PLUGIN.run_via == "global_cli"
    assert HATCH_PLUGIN.executable == "hatch"


def test_hatch_is_project_scoped():
    assert HATCH_PLUGIN.is_project_scoped is True


def test_hatch_publish_has_auth_secret():
    spec = HATCH_PLUGIN.command_specs["hatch_publish"]
    auth_arg = next((a for a in spec.args if a.name == "auth"), None)
    assert auth_arg is not None
    assert auth_arg.field_type == "secret"


def test_hatch_secret_flags():
    assert "--auth" in HATCH_PLUGIN.secret_flags


def test_hatch_has_env_specs():
    for name in ("hatch_env_show", "hatch_env_create", "hatch_env_remove", "hatch_env_prune"):
        assert name in HATCH_PLUGIN.command_specs


def test_hatch_plugin_has_panel_class():
    assert HATCH_PLUGIN.panel_class is not None


# ---- flit ---------------------------------------------------------------


def test_flit_plugin_run_via():
    assert FLIT_PLUGIN.run_via == "global_cli"
    assert FLIT_PLUGIN.executable == "flit"


def test_flit_has_build_and_publish():
    assert "flit_build" in FLIT_PLUGIN.command_specs
    assert "flit_publish" in FLIT_PLUGIN.command_specs


# ---- pipx ---------------------------------------------------------------


def test_pipx_plugin_run_via():
    assert PIPX_PLUGIN.run_via == "global_cli"
    assert PIPX_PLUGIN.executable == "pipx"


def test_pipx_hides_interpreter_picker():
    assert PIPX_PLUGIN.hide_interpreter_picker is True


def test_pipx_has_install_and_list():
    assert "pipx_install" in PIPX_PLUGIN.command_specs
    assert "pipx_list" in PIPX_PLUGIN.command_specs


def test_pipx_plugin_has_panel_class():
    assert PIPX_PLUGIN.panel_class is not None
