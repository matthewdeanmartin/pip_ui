"""pip ToolPlugin — wraps existing COMMAND_SPECS unchanged."""

from __future__ import annotations

from pip_ui.command_specs import COMMAND_GROUPS, COMMAND_SPECS
from pip_ui.tools import ToolPlugin

PIP_PLUGIN = ToolPlugin(
    name="pip",
    label="pip",
    extra="",
    run_via="python_module",
    module="pip",
    executable="pip",
    command_specs=COMMAND_SPECS,
    command_groups=list(COMMAND_GROUPS),
    help_url="https://pip.pypa.io/en/stable/",
)
