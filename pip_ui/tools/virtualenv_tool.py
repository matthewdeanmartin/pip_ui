"""virtualenv ToolPlugin — wraps `python -m virtualenv`."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin
from pip_ui.ui.virtualenv_panel import VirtualenvPanel

_GROUPS = ["Create", "Manage"]

_SPECS: dict[str, CommandSpec] = {
    "create": CommandSpec(
        name="create",
        label="Create Env",
        group="Create",
        description="Create a new virtual environment at the specified destination path.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="dest",
                flag="",
                field_type="dir",
                label="Destination",
                help="Path for the new virtual environment.",
                default=".venv",
                required=True,
            ),
            ArgSpec(
                name="python",
                flag="--python",
                field_type="text",
                label="Python",
                help="Python interpreter to use (path or version, e.g. python3.11).",
                default=None,
            ),
            ArgSpec(
                name="system_site_packages",
                flag="--system-site-packages",
                field_type="checkbox",
                label="System Site Packages",
                help="Give the virtual environment access to the system site-packages.",
                default=False,
            ),
            ArgSpec(
                name="copies",
                flag="--copies",
                field_type="checkbox",
                label="Use Copies",
                help="Use copies rather than symlinks for the interpreter.",
                default=False,
            ),
            ArgSpec(
                name="clear",
                flag="--clear",
                field_type="checkbox",
                label="Clear",
                help="Delete the contents of the environment directory if it already exists.",
                default=False,
            ),
            ArgSpec(
                name="prompt",
                flag="--prompt",
                field_type="text",
                label="Prompt",
                help="Provide an alternative prompt prefix for this environment.",
                default=None,
            ),
            ArgSpec(
                name="creator",
                flag="--creator",
                field_type="dropdown",
                label="Creator",
                help="Method used to create the virtual environment.",
                default="builtin",
                choices=["builtin", "venv", "cpython3-posix"],
            ),
            ArgSpec(
                name="seeder",
                flag="--seeder",
                field_type="dropdown",
                label="Seeder",
                help="Method used to seed the virtual environment with initial packages.",
                default="app-data",
                choices=["app-data", "pip"],
            ),
            ArgSpec(
                name="without_pip",
                flag="--without-pip",
                field_type="checkbox",
                label="Without pip",
                help="Do not install pip into the new environment.",
                default=False,
            ),
        ],
    ),
    "venv_version": CommandSpec(
        name="venv_version",
        label="Version",
        group="Manage",
        description="Show virtualenv version.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
}

VIRTUALENV_PLUGIN = ToolPlugin(
    name="virtualenv",
    label="virtualenv",
    extra="virtualenv",
    run_via="python_module",
    module="virtualenv",
    executable="virtualenv",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://virtualenv.pypa.io/en/latest/",
    panel_class=VirtualenvPanel,
)
