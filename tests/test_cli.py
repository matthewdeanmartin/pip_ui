"""Smoke tests for the CLI entry point."""

from types import SimpleNamespace

import pip_ui
from pip_ui.__about__ import __version__
from pip_ui.models import InterpreterInfo
from pip_ui.ui.main_window import MainWindow


def test_import() -> None:
    """Package can be imported."""
    assert pip_ui is not None


def test_version() -> None:
    """Package exposes a version string."""
    assert isinstance(__version__, str)
    assert __version__


def test_on_interpreter_change_handles_early_startup_callback() -> None:
    """Interpreter change callback should tolerate firing before all widgets exist."""

    class FakeVar:
        def __init__(self) -> None:
            self.value = ""

        def set(self, value: str) -> None:
            self.value = value

    class FakeSettings:
        def __init__(self) -> None:
            self.saved: dict[str, str] = {}

        def set(self, key: str, value: str) -> None:
            self.saved[key] = value

    info = InterpreterInfo(
        path="C:\\Python313\\python.exe",
        version="3.13.3",
        pip_version="25.1",
        is_venv=False,
        prefix="C:\\Python313",
        base_prefix="C:\\Python313",
        env_type="system",
    )
    fake_window = SimpleNamespace(
        current_interpreter=None,
        status_interpreter_var=FakeVar(),
        settings=FakeSettings(),
        command_form=None,
        help_panel=None,
    )

    MainWindow.on_interpreter_change(fake_window, info)

    assert fake_window.current_interpreter == info
    assert fake_window.status_interpreter_var.value == "C:\\Python313\\python.exe (3.13.3, pip 25.1)"
    assert fake_window.settings.saved["last_interpreter"] == "C:\\Python313\\python.exe"
