"""Tests for python -m pip_ui entrypoint behavior."""

from __future__ import annotations

import runpy
import sys
from types import ModuleType
from typing import Any, cast

import pytest


def test_module_main_invokes_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running pip_ui as a module should call pip_ui.cli.main."""
    calls: list[str] = []
    fake_cli = ModuleType("pip_ui.cli")

    def fake_main() -> None:
        calls.append("called")

    cast(Any, fake_cli).main = fake_main

    monkeypatch.setitem(sys.modules, "pip_ui.cli", fake_cli)

    runpy.run_module("pip_ui.__main__", run_name="__main__")

    assert calls == ["called"]
