"""build ToolPlugin — wraps `python -m build`."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

_GROUPS = ["Build"]

_SPECS: dict[str, CommandSpec] = {
    "build": CommandSpec(
        name="build",
        label="Build",
        group="Build",
        description="Build a wheel and/or sdist from the project in the working directory.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="srcdir",
                flag="",
                field_type="dir",
                label="Source Directory",
                help="Path to the project source directory (defaults to working directory).",
                default=".",
            ),
            ArgSpec(
                name="wheel",
                flag="--wheel",
                field_type="checkbox",
                label="Wheel only",
                help="Build a wheel distribution only.",
                default=False,
            ),
            ArgSpec(
                name="sdist",
                flag="--sdist",
                field_type="checkbox",
                label="sdist only",
                help="Build a source distribution only.",
                default=False,
            ),
            ArgSpec(
                name="outdir",
                flag="--outdir",
                field_type="dir",
                label="Output Directory",
                help="Output directory for the built distributions (default: dist/).",
                default=None,
            ),
            ArgSpec(
                name="no_isolation",
                flag="--no-isolation",
                field_type="checkbox",
                label="No Isolation",
                help="Disable build isolation; use the current environment directly.",
                default=False,
            ),
            ArgSpec(
                name="skip_dependency_check",
                flag="--skip-dependency-check",
                field_type="checkbox",
                label="Skip Dependency Check",
                help="Skip checking build dependencies (use with --no-isolation).",
                default=False,
            ),
            ArgSpec(
                name="installer",
                flag="--installer",
                field_type="dropdown",
                label="Installer",
                help="Python package installer to use in the isolated build environment.",
                default="pip",
                choices=["pip", "uv"],
            ),
            ArgSpec(
                name="verbose",
                flag="--verbose",
                field_type="checkbox",
                label="Verbose",
                help="Run in verbose mode.",
                default=False,
            ),
        ],
    ),
}

BUILD_PLUGIN = ToolPlugin(
    name="build",
    label="build",
    extra="build",
    run_via="python_module",
    module="build",
    executable="python-build",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://build.pypa.io/en/stable/",
    is_project_scoped=True,
)
