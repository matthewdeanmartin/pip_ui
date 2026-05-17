"""Safety classification and confirmation utilities."""

from __future__ import annotations

import re

from pip_ui.models import InterpreterInfo, SafetyLevel

COMMAND_SAFETY: dict[str, SafetyLevel] = {
    "install": SafetyLevel.MODIFIES_ENV,
    "uninstall": SafetyLevel.DESTRUCTIVE,
    "list": SafetyLevel.READ_ONLY,
    "show": SafetyLevel.READ_ONLY,
    "freeze": SafetyLevel.READ_ONLY,
    "check": SafetyLevel.READ_ONLY,
    "config_list": SafetyLevel.READ_ONLY,
    "config_debug": SafetyLevel.READ_ONLY,
    "cache_dir": SafetyLevel.READ_ONLY,
    "cache_info": SafetyLevel.READ_ONLY,
    "debug": SafetyLevel.READ_ONLY,
    "version": SafetyLevel.READ_ONLY,
    "help": SafetyLevel.READ_ONLY,
}

CONFIRMATION_MESSAGES: dict[str, str] = {
    "uninstall": "This will permanently remove the selected packages from your Python environment. Are you sure you want to continue?",
    "install": "This will modify your Python environment by installing packages. Are you sure you want to continue?",
}


def classify_command(command_name: str) -> SafetyLevel:
    return COMMAND_SAFETY.get(command_name, SafetyLevel.MODIFIES_ENV)


def check_global_install(interpreter_info: InterpreterInfo) -> str | None:
    if not interpreter_info.is_venv:
        return (
            f"Warning: You are about to install packages into a global Python environment "
            f"({interpreter_info.path}). This may affect system tools and other projects. "
            f"Consider using a virtual environment instead."
        )
    return None


def redact_url(url: str) -> str:
    return re.sub(r"(://)[^:@/]+:[^@/]+@", r"\1<redacted>:<redacted>@", url)


def needs_confirmation(safety_level: SafetyLevel) -> bool:
    return safety_level in (SafetyLevel.DESTRUCTIVE, SafetyLevel.RISKY_CONFIG)


def confirmation_message(command_name: str) -> str:
    return CONFIRMATION_MESSAGES.get(
        command_name,
        f"This action ({command_name}) may modify your environment. Are you sure you want to continue?",
    )
