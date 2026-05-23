"""devpi ToolPlugin — wraps the `devpi` CLI."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin
from pip_ui.ui.devpi_panel import DevpiPanel

_GROUPS = ["Client", "Info"]

_SPECS: dict[str, CommandSpec] = {
    "devpi_use": CommandSpec(
        name="devpi_use",
        label="Use Server",
        group="Client",
        description="Set the current devpi server URL.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="url",
                flag="",
                field_type="text",
                label="Server URL",
                help="URL of the devpi server (e.g. http://localhost:3141).",
                default=None,
                required=True,
            ),
        ],
    ),
    "devpi_login": CommandSpec(
        name="devpi_login",
        label="Login",
        group="Client",
        description="Login to the devpi server.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="username",
                flag="",
                field_type="text",
                label="Username",
                help="Username to authenticate with.",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="password",
                flag="--password",
                field_type="secret",
                label="Password",
                help="Password for authentication. Hidden in output and history.",
                default=None,
            ),
        ],
    ),
    "devpi_logoff": CommandSpec(
        name="devpi_logoff",
        label="Logoff",
        group="Client",
        description="Log off from the current devpi server.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[],
    ),
    "devpi_upload": CommandSpec(
        name="devpi_upload",
        label="Upload",
        group="Client",
        description="Upload packages to the current devpi index.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="formats",
                flag="--formats",
                field_type="dropdown",
                label="Formats",
                help="Distribution formats to upload.",
                default="sdist,bdist_wheel",
                choices=["sdist", "bdist_wheel", "sdist,bdist_wheel"],
            ),
            ArgSpec(
                name="with_docs",
                flag="--with-docs",
                field_type="checkbox",
                label="With Docs",
                help="Upload documentation along with the package.",
                default=False,
            ),
            ArgSpec(
                name="from_dir",
                flag="--from-dir",
                field_type="dir",
                label="From Directory",
                help="Upload all archives found in this directory.",
                default=None,
            ),
        ],
    ),
    "devpi_index_create": CommandSpec(
        name="devpi_index_create",
        label="Create Index",
        group="Client",
        description="Create a new devpi index.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="index_name",
                flag="",
                field_type="text",
                label="Index Name",
                help="Name of the index to create (e.g. user/dev).",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="bases",
                flag="bases=",
                field_type="text",
                label="Bases",
                help="Comma-separated base index list (e.g. root/pypi).",
                default=None,
            ),
            ArgSpec(
                name="volatile",
                flag="volatile=",
                field_type="checkbox",
                label="Volatile",
                help="Allow overwriting of existing release files.",
                default=True,
            ),
        ],
    ),
    "devpi_index_list": CommandSpec(
        name="devpi_index_list",
        label="List Indexes",
        group="Client",
        description="List all indexes on the current devpi server.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
    "devpi_index_delete": CommandSpec(
        name="devpi_index_delete",
        label="Delete Index",
        group="Client",
        description="Delete a devpi index.",
        safety_level=SafetyLevel.DESTRUCTIVE,
        args=[
            ArgSpec(
                name="index_name",
                flag="",
                field_type="text",
                label="Index Name",
                help="Name of the index to delete.",
                default=None,
                required=True,
            ),
        ],
    ),
    "devpi_test": CommandSpec(
        name="devpi_test",
        label="Test Package",
        group="Client",
        description="Test a package with tox via devpi.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="package",
                flag="",
                field_type="text",
                label="Package",
                help="Package spec to test (e.g. mypackage or mypackage==1.0).",
                default=None,
                required=True,
            ),
            ArgSpec(
                name="tox_args",
                flag="--tox-args",
                field_type="text",
                label="Tox Args",
                help="Extra arguments passed to tox.",
                default=None,
            ),
        ],
    ),
    "devpi_list": CommandSpec(
        name="devpi_list",
        label="List Packages",
        group="Client",
        description="List packages or versions on the current index.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="spec",
                flag="",
                field_type="text",
                label="Package Spec",
                help="Package spec like pkg or pkg>=1.0 (leave blank to list all).",
                default=None,
            ),
        ],
    ),
    "devpi_status": CommandSpec(
        name="devpi_status",
        label="Status",
        group="Info",
        description="Show the current devpi client status.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
    "devpi_version": CommandSpec(
        name="devpi_version",
        label="Version",
        group="Info",
        description="Show the devpi client version.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
}

DEVPI_PLUGIN = ToolPlugin(
    name="devpi",
    label="devpi",
    extra="devpi",
    run_via="global_cli",
    executable="devpi",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://devpi.net/docs/devpi/devpi/stable/+d/index.html",
    secret_flags=["--password"],
    panel_class=DevpiPanel,
)
