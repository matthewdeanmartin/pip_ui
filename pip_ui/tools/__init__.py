# pylint: disable=import-outside-toplevel

"""Tool plugin registry for pip-ui extras."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from pip_ui.models import CommandSpec


@dataclass
class ToolPlugin:
    name: str
    label: str
    extra: str
    run_via: Literal["python_module", "global_cli"]
    executable: str
    command_specs: dict[str, CommandSpec]
    command_groups: list[str]
    help_url: str
    module: str = ""
    panel_class: type | None = None
    global_options_class: type | None = None
    # Flag names whose values should be redacted in output/history
    secret_flags: list[str] = field(default_factory=list)
    # Whether Dir picker should be labelled "Project Dir:" for this tool
    is_project_scoped: bool = False
    # Whether the interpreter picker should be hidden for this tool
    hide_interpreter_picker: bool = False


def _build_registry() -> list[ToolPlugin]:
    from pip_ui.tools.build_tool import BUILD_PLUGIN
    from pip_ui.tools.flit_tool import FLIT_PLUGIN
    from pip_ui.tools.hatch_tool import HATCH_PLUGIN
    from pip_ui.tools.pip_audit_tool import PIP_AUDIT_PLUGIN
    from pip_ui.tools.pip_tool import PIP_PLUGIN
    from pip_ui.tools.pipx_tool import PIPX_PLUGIN
    from pip_ui.tools.twine_tool import TWINE_PLUGIN
    from pip_ui.tools.virtualenv_tool import VIRTUALENV_PLUGIN

    return [
        PIP_PLUGIN,
        BUILD_PLUGIN,
        VIRTUALENV_PLUGIN,
        TWINE_PLUGIN,
        PIP_AUDIT_PLUGIN,
        HATCH_PLUGIN,
        FLIT_PLUGIN,
        PIPX_PLUGIN,
    ]


@lru_cache(maxsize=1)
def get_registry() -> tuple[ToolPlugin, ...]:
    return tuple(_build_registry())


def get_plugin(name: str) -> ToolPlugin | None:
    for p in get_registry():
        if p.name == name:
            return p
    return None
