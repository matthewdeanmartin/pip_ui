"""pip-audit ToolPlugin — wraps `python -m pip_audit`."""

from __future__ import annotations

from pip_ui.models import ArgSpec, CommandSpec, SafetyLevel
from pip_ui.tools import ToolPlugin

_GROUPS = ["Audit"]

_SPECS: dict[str, CommandSpec] = {
    "audit": CommandSpec(
        name="audit",
        label="Audit",
        group="Audit",
        description="Audit Python packages for known vulnerabilities.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[
            ArgSpec(
                name="requirement",
                flag="--requirement",
                field_type="file",
                label="Requirements File",
                help="Audit packages from this requirements file instead of the current environment.",
                default=None,
            ),
            ArgSpec(
                name="output_format",
                flag="--output-format",
                field_type="dropdown",
                label="Output Format",
                help="Output format for the audit results.",
                default="columns",
                choices=["columns", "json", "cyclonedx-json", "cyclonedx-xml"],
            ),
            ArgSpec(
                name="vulnerability_service",
                flag="--vulnerability-service",
                field_type="dropdown",
                label="Vulnerability Service",
                help="Vulnerability database to use.",
                default="osv",
                choices=["osv", "pypi"],
            ),
            ArgSpec(
                name="fix",
                flag="--fix",
                field_type="checkbox",
                label="Auto-fix",
                help="Upgrade vulnerable packages to the latest safe version (changes environment).",
                default=False,
            ),
            ArgSpec(
                name="dry_run",
                flag="--dry-run",
                field_type="checkbox",
                label="Dry Run",
                help="Show what would be fixed without making changes (requires --fix).",
                default=False,
            ),
            ArgSpec(
                name="skip_editable",
                flag="--skip-editable",
                field_type="checkbox",
                label="Skip Editable",
                help="Skip auditing editable installs.",
                default=False,
            ),
            ArgSpec(
                name="ignore_vuln",
                flag="--ignore-vuln",
                field_type="multi",
                label="Ignore Vulnerabilities",
                help="Vulnerability IDs to ignore (space-separated, e.g. GHSA-xxxx PYSEC-xxxx).",
                default=None,
            ),
            ArgSpec(
                name="disable_pip",
                flag="--disable-pip",
                field_type="checkbox",
                label="Disable pip",
                help="Do not use pip to resolve dependencies.",
                default=False,
            ),
            ArgSpec(
                name="no_deps",
                flag="--no-deps",
                field_type="checkbox",
                label="No Dependencies",
                help="Only audit the explicitly listed packages, not their dependencies.",
                default=False,
            ),
            ArgSpec(
                name="timeout",
                flag="--timeout",
                field_type="text",
                label="Timeout (seconds)",
                help="HTTP request timeout in seconds.",
                default=None,
            ),
        ],
    ),
    "audit_version": CommandSpec(
        name="audit_version",
        label="Version",
        group="Audit",
        description="Show pip-audit version.",
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    ),
}

PIP_AUDIT_PLUGIN = ToolPlugin(
    name="pip-audit",
    label="pip-audit",
    extra="pip-audit",
    run_via="python_module",
    module="pip_audit",
    executable="pip-audit",
    command_specs=_SPECS,
    command_groups=_GROUPS,
    help_url="https://pypi.org/project/pip-audit/",
)
