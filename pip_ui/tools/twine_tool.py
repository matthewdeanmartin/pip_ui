"""twine ToolPlugin — wraps the `twine` CLI."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

_GROUPS = ["Upload", "Check"]

_SPECS: dict[str, CommandSpec] = {
    "twine_upload": CommandSpec(
        name="twine_upload",
        label="Upload",
        group="Upload",
        description="Upload distributions to PyPI or another package index.",
        safety_level=SafetyLevel.MODIFIES_ENV,
        args=[
            ArgSpec(
                name="dists",
                flag="",
                field_type="multi",
                label="Distributions",
                help="Glob pattern or paths to distribution files to upload (e.g. dist/*).",
                default="dist/*",
                required=True,
            ),
            ArgSpec(
                name="repository",
                flag="--repository",
                field_type="text",
                label="Repository",
                help="Repository name from .pypirc (default: pypi).",
                default=None,
            ),
            ArgSpec(
                name="repository_url",
                flag="--repository-url",
                field_type="text",
                label="Repository URL",
                help="URL of the repository (overrides --repository).",
                default=None,
            ),
            ArgSpec(
                name="username",
                flag="--username",
                field_type="text",
                label="Username",
                help="Username for authentication (use __token__ for API tokens).",
                default=None,
            ),
            ArgSpec(
                name="password",
                flag="--password",
                field_type="secret",
                label="Password / Token",
                help="Password or API token. Hidden in output and history.",
                default=None,
            ),
            ArgSpec(
                name="skip_existing",
                flag="--skip-existing",
                field_type="checkbox",
                label="Skip Existing",
                help="Skip uploading files that already exist on the index.",
                default=False,
            ),
            ArgSpec(
                name="cert",
                flag="--cert",
                field_type="file",
                label="CA Cert",
                help="Path to a CA certificate bundle.",
                default=None,
            ),
            ArgSpec(
                name="client_cert",
                flag="--client-cert",
                field_type="file",
                label="Client Cert",
                help="Path to a client SSL certificate (PEM).",
                default=None,
            ),
            ArgSpec(
                name="verbose",
                flag="--verbose",
                field_type="checkbox",
                label="Verbose",
                help="Show additional logging.",
                default=False,
            ),
            ArgSpec(
                name="disable_progress_bar",
                flag="--disable-progress-bar",
                field_type="checkbox",
                label="Disable Progress Bar",
                help="Disable the progress bar.",
                default=False,
            ),
        ],
    ),
    "twine_check": CommandSpec(
        name="twine_check",
        label="Check",
        group="Check",
        description="Check that distribution files will render correctly on PyPI.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="dists",
                flag="",
                field_type="multi",
                label="Distributions",
                help="Paths to distribution files to check.",
                default="dist/*",
                required=True,
            ),
            ArgSpec(
                name="strict",
                flag="--strict",
                field_type="checkbox",
                label="Strict",
                help="Fail on warnings as well as errors.",
                default=False,
            ),
        ],
    ),
    "twine_version": CommandSpec(
        name="twine_version",
        label="Version",
        group="Check",
        description="Show twine version.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
}

TWINE_PLUGIN = ToolPlugin(
    name="twine",
    label="twine",
    extra="twine",
    run_via="global_cli",
    executable="twine",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://twine.readthedocs.io/en/stable/",
    secret_flags=["--password"],
    is_project_scoped=True,
)
