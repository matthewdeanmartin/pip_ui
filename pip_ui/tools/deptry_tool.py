"""deptry ToolPlugin — wraps the `deptry` CLI."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

_GROUPS = ["Analysis"]

_SPECS: dict[str, CommandSpec] = {
    "deptry_check": CommandSpec(
        name="deptry_check",
        label="Check",
        group="Analysis",
        description="Find dependency issues in the project (missing, unused, transitive, misplaced).",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="root",
                flag="",
                field_type="text",
                label="Root",
                help="Root directory (or directories) to scan. Defaults to '.'.",
                default=".",
            ),
            ArgSpec(
                name="verbose",
                flag="--verbose",
                field_type="checkbox",
                label="Verbose",
                help="Display more information about files, imports, and dependencies.",
                default=False,
            ),
            ArgSpec(
                name="ignore",
                flag="--ignore",
                field_type="text",
                label="Ignore Codes",
                help="Comma-separated error codes to ignore (e.g. DEP001,DEP002).",
                default=None,
            ),
            ArgSpec(
                name="extend_exclude",
                flag="--extend-exclude",
                field_type="text",
                label="Extend Exclude",
                help="Regex for additional directories/files to exclude (space-separated for multiple).",
                default=None,
            ),
            ArgSpec(
                name="config",
                flag="--config",
                field_type="file",
                label="Config File",
                help="Path to pyproject.toml to read configuration from.",
                default=None,
            ),
            ArgSpec(
                name="no_ansi",
                flag="--no-ansi",
                field_type="checkbox",
                label="No ANSI",
                help="Disable ANSI characters in terminal output.",
                default=False,
            ),
        ],
    ),
}

DEPTRY_PLUGIN = ToolPlugin(
    name="deptry",
    label="deptry",
    extra="deptry",
    run_via="global_cli",
    executable="deptry",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://deptry.com/",
    is_project_scoped=True,
)
