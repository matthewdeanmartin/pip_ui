"""flit ToolPlugin — wraps the `flit` CLI."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

_GROUPS = ["Build", "Publish"]

_SPECS: dict[str, CommandSpec] = {
    "flit_build": CommandSpec(
        name="flit_build",
        label="Build",
        group="Build",
        description="Build a wheel and/or sdist from the current project.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="format",
                flag="--format",
                field_type="dropdown",
                label="Format",
                help="Which distribution format to build.",
                default="wheel",
                choices=["wheel", "sdist"],
            ),
        ],
    ),
    "flit_publish": CommandSpec(
        name="flit_publish",
        label="Publish",
        group="Publish",
        description="Upload the project to PyPI or another index.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="repository",
                flag="--repository",
                field_type="text",
                label="Repository",
                help="Repository section name in .pypirc (default: pypi).",
                default=None,
            ),
            ArgSpec(
                name="pypirc",
                flag="--pypirc",
                field_type="file",
                label=".pypirc File",
                help="Path to a .pypirc config file.",
                default=None,
            ),
            ArgSpec(
                name="format",
                flag="--format",
                field_type="dropdown",
                label="Format",
                help="Distribution format to upload.",
                default="wheel",
                choices=["wheel", "sdist"],
            ),
        ],
    ),
    "flit_install": CommandSpec(
        name="flit_install",
        label="Install (dev)",
        group="Build",
        description="Install this package in the current environment for development.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="symlink",
                flag="--symlink",
                field_type="checkbox",
                label="Symlink",
                help="Use a symlink to the source directory instead of copying.",
                default=False,
            ),
            ArgSpec(
                name="pth_file",
                flag="--pth-file",
                field_type="checkbox",
                label=".pth File",
                help="Add a .pth file for the source directory instead of copying.",
                default=False,
            ),
            ArgSpec(
                name="deps",
                flag="--deps",
                field_type="dropdown",
                label="Dependencies",
                help="Which set of dependencies to install.",
                default="all",
                choices=["all", "develop", "production", "none"],
            ),
        ],
    ),
}

FLIT_PLUGIN = ToolPlugin(
    name="flit",
    label="flit",
    extra="flit",
    run_via="global_cli",
    executable="flit",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://flit.pypa.io/en/stable/",
    is_project_scoped=True,
)
