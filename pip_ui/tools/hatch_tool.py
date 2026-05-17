"""hatch ToolPlugin — wraps the `hatch` CLI."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

_GROUPS = ["Environment", "Build", "Publish", "Project", "Run"]

_SPECS: dict[str, CommandSpec] = {
    "hatch_env_show": CommandSpec(
        name="hatch_env_show",
        label="Show Envs",
        group="Environment",
        description="Show all defined hatch environments for the current project.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="json",
                flag="--json",
                field_type="checkbox",
                label="JSON Output",
                help="Output as JSON (used internally by the env table panel).",
                default=False,
            ),
        ],
    ),
    "hatch_env_create": CommandSpec(
        name="hatch_env_create",
        label="Create Env",
        group="Environment",
        description="Create a hatch environment.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="env_name",
                flag="",
                field_type="text",
                label="Environment Name",
                help="Name of the environment to create (default: default).",
                default="default",
            ),
        ],
    ),
    "hatch_env_remove": CommandSpec(
        name="hatch_env_remove",
        label="Remove Env",
        group="Environment",
        description="Remove a hatch environment.",
        safety_level=SafetyLevel.DESTRUCTIVE,
        args=[
            ArgSpec(
                name="env_name",
                flag="",
                field_type="text",
                label="Environment Name",
                help="Name of the environment to remove.",
                default=None,
                required=True,
            ),
        ],
    ),
    "hatch_env_prune": CommandSpec(
        name="hatch_env_prune",
        label="Prune Envs",
        group="Environment",
        description="Remove all hatch environments for this project.",
        safety_level=SafetyLevel.DESTRUCTIVE,
        args=[],
    ),
    "hatch_build": CommandSpec(
        name="hatch_build",
        label="Build",
        group="Build",
        description="Build the project (wheel, sdist, or app target).",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="target",
                flag="--target",
                field_type="dropdown",
                label="Target",
                help="Build target to run.",
                default="wheel",
                choices=["wheel", "sdist", "app"],
            ),
            ArgSpec(
                name="clean",
                flag="--clean",
                field_type="checkbox",
                label="Clean",
                help="Remove existing build artifacts before building.",
                default=False,
            ),
            ArgSpec(
                name="clean_hooks_after",
                flag="--clean-hooks-after",
                field_type="checkbox",
                label="Clean Hooks After",
                help="Remove build hook artifacts after building.",
                default=False,
            ),
        ],
    ),
    "hatch_publish": CommandSpec(
        name="hatch_publish",
        label="Publish",
        group="Publish",
        description="Publish the project to a package index.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="target",
                flag="--publisher",
                field_type="dropdown",
                label="Publisher",
                help="Publisher to use.",
                default="index",
                choices=["index"],
            ),
            ArgSpec(
                name="repo",
                flag="--repo",
                field_type="text",
                label="Repository",
                help="Repository to publish to (e.g. main, test).",
                default=None,
            ),
            ArgSpec(
                name="user",
                flag="--user",
                field_type="text",
                label="Username",
                help="Username for authentication.",
                default=None,
            ),
            ArgSpec(
                name="auth",
                flag="--auth",
                field_type="secret",
                label="Auth / Token",
                help="Password or API token. Hidden in output and history.",
                default=None,
            ),
        ],
    ),
    "hatch_version_show": CommandSpec(
        name="hatch_version_show",
        label="Show Version",
        group="Project",
        description="Show the current project version.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
    "hatch_version_set": CommandSpec(
        name="hatch_version_set",
        label="Set Version",
        group="Project",
        description="Update the project version.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="version",
                flag="",
                field_type="text",
                label="Version",
                help="New version string (e.g. 1.2.3) or increment keyword (major, minor, patch).",
                default=None,
                required=True,
            ),
        ],
    ),
    "hatch_run": CommandSpec(
        name="hatch_run",
        label="Run Script",
        group="Run",
        description="Run a command inside a hatch environment.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="env_name",
                flag="--env",
                field_type="text",
                label="Environment",
                help="Environment to run in (default: default).",
                default=None,
            ),
            ArgSpec(
                name="command",
                flag="",
                field_type="text",
                label="Command",
                help="Command to run (e.g. pytest, python -m mypackage).",
                default=None,
                required=True,
            ),
        ],
    ),
    "hatch_fmt": CommandSpec(
        name="hatch_fmt",
        label="Format",
        group="Run",
        description="Run the project formatter.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="check",
                flag="--check",
                field_type="checkbox",
                label="Check Only",
                help="Check formatting without making changes.",
                default=False,
            ),
        ],
    ),
    "hatch_lint": CommandSpec(
        name="hatch_lint",
        label="Lint",
        group="Run",
        description="Run the project linter.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
}

HATCH_PLUGIN = ToolPlugin(
    name="hatch",
    label="hatch",
    extra="hatch",
    run_via="global_cli",
    executable="hatch",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://hatch.pypa.io/latest/",
    secret_flags=["--auth"],
    is_project_scoped=True,
)
