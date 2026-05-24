"""pipx ToolPlugin — wraps the `pipx` CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

if TYPE_CHECKING:
    from pip_ui.ui.pipx_apps_panel import PipxAppsPanel

_PIPX_APPS_PANEL_CLASS: type[PipxAppsPanel] | None

try:
    from pip_ui.ui.pipx_apps_panel import PipxAppsPanel as _PIPX_APPS_PANEL_CLASS
except ModuleNotFoundError:
    _PIPX_APPS_PANEL_CLASS = None

_GROUPS = ["Apps", "Environments"]

_SPECS: dict[str, CommandSpec] = {
    "pipx_install": CommandSpec(
        name="pipx_install",
        label="Install App",
        group="Apps",
        description="Install a CLI application in an isolated environment.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="package",
                flag="",
                field_type="text",
                label="Package",
                help="Package spec to install (e.g. black, ruff==0.4.0).",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="python",
                flag="--python",
                field_type="text",
                label="Python",
                help="Python interpreter to use for the isolated environment.",
                default=None,
            ),
            ArgSpec(
                name="index_url",
                flag="--index-url",
                field_type="text",
                label="Index URL",
                help="Base URL of the package index.",
                default=None,
            ),
            ArgSpec(
                name="pip_args",
                flag="--pip-args",
                field_type="text",
                label="pip Args",
                help="Extra arguments passed to pip when installing.",
                default=None,
            ),
            ArgSpec(
                name="force",
                flag="--force",
                field_type="checkbox",
                label="Force Reinstall",
                help="Reinstall even if the app is already installed.",
                default=False,
            ),
            ArgSpec(
                name="include_deps",
                flag="--include-deps",
                field_type="checkbox",
                label="Include Dependencies",
                help="Also expose apps from the package's dependencies.",
                default=False,
            ),
        ],
    ),
    "pipx_uninstall": CommandSpec(
        name="pipx_uninstall",
        label="Uninstall App",
        group="Apps",
        description="Uninstall an application and its isolated environment.",
        safety_level=SafetyLevel.DESTRUCTIVE,
        args=[
            ArgSpec(
                name="package",
                flag="",
                field_type="text",
                label="App / Package",
                help="Name of the installed application to remove.",
                default=None,
                required=True,
            ),
        ],
    ),
    "pipx_uninstall_all": CommandSpec(
        name="pipx_uninstall_all",
        label="Uninstall All",
        group="Apps",
        description="Uninstall all pipx-managed applications.",
        safety_level=SafetyLevel.DESTRUCTIVE,
        args=[],
    ),
    "pipx_upgrade": CommandSpec(
        name="pipx_upgrade",
        label="Upgrade App",
        group="Apps",
        description="Upgrade an installed application to the latest version.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="package",
                flag="",
                field_type="text",
                label="App / Package",
                help="Name of the installed application to upgrade.",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="pip_args",
                flag="--pip-args",
                field_type="text",
                label="pip Args",
                help="Extra arguments passed to pip during upgrade.",
                default=None,
            ),
        ],
    ),
    "pipx_upgrade_all": CommandSpec(
        name="pipx_upgrade_all",
        label="Upgrade All",
        group="Apps",
        description="Upgrade all installed pipx applications.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="skip",
                flag="--skip",
                field_type="multi",
                label="Skip",
                help="Skip upgrading these packages (space-separated).",
                default=None,
            ),
            ArgSpec(
                name="include_injected",
                flag="--include-injected",
                field_type="checkbox",
                label="Include Injected",
                help="Also upgrade packages injected into app environments.",
                default=False,
            ),
        ],
    ),
    "pipx_inject": CommandSpec(
        name="pipx_inject",
        label="Inject",
        group="Apps",
        description="Install packages into an existing pipx app environment.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="app",
                flag="",
                field_type="text",
                label="App",
                help="Name of the pipx app environment to inject into.",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="packages",
                flag="",
                field_type="multi",
                label="Packages",
                help="Packages to inject (space-separated).",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="include_apps",
                flag="--include-apps",
                field_type="checkbox",
                label="Include Apps",
                help="Also expose the injected packages' apps.",
                default=False,
            ),
            ArgSpec(
                name="include_deps",
                flag="--include-deps",
                field_type="checkbox",
                label="Include Dependencies",
                help="Also expose apps from injected packages' dependencies.",
                default=False,
            ),
        ],
    ),
    "pipx_list": CommandSpec(
        name="pipx_list",
        label="List Apps",
        group="Apps",
        description="List installed pipx applications.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="json",
                flag="--json",
                field_type="checkbox",
                label="JSON Output",
                help="Output as JSON (used internally by the apps table panel).",
                default=False,
            ),
            ArgSpec(
                name="short",
                flag="--short",
                field_type="checkbox",
                label="Short",
                help="List only app names and versions.",
                default=False,
            ),
            ArgSpec(
                name="include_injected",
                flag="--include-injected",
                field_type="checkbox",
                label="Include Injected",
                help="Show packages injected into app environments.",
                default=False,
            ),
        ],
    ),
    "pipx_run": CommandSpec(
        name="pipx_run",
        label="Run (ephemeral)",
        group="Apps",
        description="Run an application in a temporary environment without installing it permanently.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="package",
                flag="",
                field_type="text",
                label="Package",
                help="Package to run (e.g. cowsay, black==24.0).",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="args",
                flag="",
                field_type="multi",
                label="Arguments",
                help="Arguments to pass to the application.",
                default=None,
            ),
            ArgSpec(
                name="python",
                flag="--python",
                field_type="text",
                label="Python",
                help="Python interpreter for the temporary environment.",
                default=None,
            ),
            ArgSpec(
                name="index_url",
                flag="--index-url",
                field_type="text",
                label="Index URL",
                help="Base URL of the package index.",
                default=None,
            ),
        ],
    ),
    "pipx_runpip": CommandSpec(
        name="pipx_runpip",
        label="Run pip in App",
        group="Environments",
        description="Run pip inside a pipx app's isolated environment.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="app",
                flag="",
                field_type="text",
                label="App",
                help="Name of the pipx app environment.",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="pip_args",
                flag="",
                field_type="multi",
                label="pip Arguments",
                help="Arguments to pass to pip (e.g. list --outdated).",
                default=None,
                required=True,
            ),
        ],
    ),
    "pipx_ensurepath": CommandSpec(
        name="pipx_ensurepath",
        label="Ensure PATH",
        group="Environments",
        description="Ensure the pipx bin directory is on PATH.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[],
    ),
    "pipx_environment": CommandSpec(
        name="pipx_environment",
        label="Show Environment",
        group="Environments",
        description="Show pipx environment configuration (paths, Python, etc.).",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="json",
                flag="--json",
                field_type="checkbox",
                label="JSON Output",
                help="Output as JSON.",
                default=False,
            ),
        ],
    ),
}

PIPX_PLUGIN = ToolPlugin(
    name="pipx",
    label="pipx",
    extra="pipx",
    run_via="global_cli",
    executable="pipx",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://pipx.pypa.io/stable/",
    hide_interpreter_picker=True,
    panel_class=_PIPX_APPS_PANEL_CLASS,
)
