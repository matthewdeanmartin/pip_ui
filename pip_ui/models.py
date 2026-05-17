"""Data models for pip-ui."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class SafetyLevel(enum.Enum):
    READ_ONLY = "read_only"
    MODIFIES_ENV = "modifies_env"
    DESTRUCTIVE = "destructive"
    RISKY_CONFIG = "risky_config"


@dataclass
class ArgSpec:
    name: str
    flag: str
    field_type: str
    label: str
    help: str
    default: object = None
    choices: list[str] = field(default_factory=list)
    required: bool = False


@dataclass
class CommandSpec:
    name: str
    label: str
    group: str
    description: str
    safety_level: SafetyLevel
    args: list[ArgSpec] = field(default_factory=list)
    supports_dry_run: bool = False
    supports_report: bool = False


@dataclass
class RunResult:
    command_label: str
    argv: list[str]
    stdout: str
    stderr: str
    combined: str
    exit_code: int
    start_time: datetime
    end_time: datetime
    interpreter_path: str
    working_directory: str


@dataclass
class HistoryEntry:
    timestamp: datetime
    command_label: str
    argv_redacted: list[str]
    command_redacted: str
    exit_code: int
    duration: float
    interpreter_path: str
    working_directory: str


@dataclass
class InterpreterInfo:
    path: str
    version: str
    pip_version: str
    is_venv: bool
    prefix: str
    base_prefix: str
    env_type: str

    def display_label(self) -> str:
        venv_tag = " [venv]" if self.is_venv else ""
        return f"{self.path} ({self.version}, pip {self.pip_version}){venv_tag}"
