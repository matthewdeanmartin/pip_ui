"""pypiserver ToolPlugin — wraps the `pypi-server` CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

if TYPE_CHECKING:
    from pip_ui.ui.pypiserver_panel import PypiServerPanel

_PYPISERVER_PANEL_CLASS: type[PypiServerPanel] | None

try:
    from pip_ui.ui.pypiserver_panel import PypiServerPanel as _PYPISERVER_PANEL_CLASS
except ModuleNotFoundError:
    _PYPISERVER_PANEL_CLASS = None

_GROUPS = ["Server", "Packages"]

_SPECS: dict[str, CommandSpec] = {
    "pypiserver_run": CommandSpec(
        name="pypiserver_run",
        label="Start Server",
        group="Server",
        description="Start the pypiserver to serve Python packages.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="port",
                flag="-p",
                field_type="text",
                label="Port",
                help="Port to listen on.",
                default="8080",
            ),
            ArgSpec(
                name="host",
                flag="-i",
                field_type="text",
                label="Host / Interface",
                help="Network interface to bind to.",
                default="0.0.0.0",
            ),
            ArgSpec(
                name="packages_dir",
                flag="",
                field_type="dir",
                label="Packages Directory",
                help="Directory containing Python packages to serve (positional).",
                default="./packages",
                required=True,
            ),
            ArgSpec(
                name="log_file",
                flag="--log-file",
                field_type="file",
                label="Log File",
                help="Path to a file where logs will be written.",
                default=None,
            ),
            ArgSpec(
                name="fallback_url",
                flag="--fallback-url",
                field_type="text",
                label="Fallback URL",
                help="Redirect to this URL for packages not found locally.",
                default="https://pypi.org/simple",
            ),
            ArgSpec(
                name="disable_fallback",
                flag="--disable-fallback",
                field_type="checkbox",
                label="Disable Fallback",
                help="Disable redirecting to the fallback URL.",
                default=False,
            ),
            ArgSpec(
                name="password_file",
                flag="-P",
                field_type="file",
                label="Password File",
                help="htpasswd file for upload authentication (use '.' to disable authentication).",
                default=None,
            ),
            ArgSpec(
                name="verbose",
                flag="-v",
                field_type="checkbox",
                label="Verbose",
                help="Enable verbose logging.",
                default=False,
            ),
        ],
    ),
    "pypiserver_update": CommandSpec(
        name="pypiserver_update",
        label="Update Packages",
        group="Packages",
        description="Update packages in the packages directory.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="packages_dir",
                flag="",
                field_type="dir",
                label="Packages Directory",
                help="Directory containing packages to update (positional).",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="download_directory",
                flag="-d",
                field_type="dir",
                label="Download Directory",
                help="Directory to download updated packages into.",
                default=None,
            ),
        ],
    ),
    "pypiserver_version": CommandSpec(
        name="pypiserver_version",
        label="Version",
        group="Server",
        description="Show pypiserver version.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
}

PYPISERVER_PLUGIN = ToolPlugin(
    name="pypiserver",
    label="pypiserver",
    extra="pypiserver",
    run_via="global_cli",
    executable="pypi-server",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://pypiserver.readthedocs.io/en/latest/",
    is_project_scoped=False,
    panel_class=_PYPISERVER_PANEL_CLASS,
)
