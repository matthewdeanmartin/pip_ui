"""Tests for CLI entry points and lightweight UI wiring."""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest

import pip_ui
import pip_ui.cli as cli_module
from pip_ui.__about__ import __version__
from pip_ui.models import InterpreterInfo


def test_import() -> None:
    """Package can be imported."""
    assert pip_ui is not None


def test_version() -> None:
    """Package exposes a version string."""
    assert isinstance(__version__, str)
    assert __version__


def test_on_interpreter_change_handles_early_startup_callback() -> None:
    """Interpreter change callback should tolerate firing before all widgets exist."""
    pytest.importorskip("tkinter")
    from pip_ui.ui.main_window import MainWindow  # pylint: disable=import-outside-toplevel

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

    MainWindow.on_interpreter_change(cast(Any, fake_window), info)

    assert fake_window.current_interpreter == info
    assert fake_window.status_interpreter_var.value == "C:\\Python313\\python.exe (3.13.3, pip 25.1)"
    assert fake_window.settings.saved["last_interpreter"] == "C:\\Python313\\python.exe"


def test_main_runs_diagnostics_without_launching_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    """Diagnostics mode should call the report path and skip the UI."""
    calls: dict[str, object] = {}

    monkeypatch.setattr(cli_module, "configure_utf8_stdio", lambda: calls.setdefault("utf8", True))
    monkeypatch.setattr(cli_module, "run_diagnostics", lambda path: calls.setdefault("diagnostics", path))
    monkeypatch.setattr(sys, "argv", ["pip-ui", "--diagnostics", "--interpreter", "C:\\Python313\\python.exe"])

    cli_module.main()

    assert calls["utf8"] is True
    assert calls["diagnostics"] == "C:\\Python313\\python.exe"


def test_main_exits_when_tkinter_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI should emit a helpful error if Tkinter is missing."""
    monkeypatch.setattr(cli_module, "configure_utf8_stdio", lambda: None)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(sys, "argv", ["pip-ui"])

    with pytest.raises(SystemExit) as excinfo:
        cli_module.main()

    assert excinfo.value.code == 1
    assert "Tkinter is not available" in capsys.readouterr().err


def test_main_launches_window_and_applies_cli_options(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI should pass startup options into the main window."""
    created: dict[str, object] = {}

    class FakeVar:
        def __init__(self) -> None:
            self.value: str | None = None

        def set(self, value: str) -> None:
            self.value = value

    class FakeInterpreterPicker:
        def __init__(self) -> None:
            self.paths: list[str] = []

        def set_from_path(self, path: str) -> None:
            self.paths.append(path)

    class FakeMainWindow:
        def __init__(self, *, no_history: bool, safe_mode: bool) -> None:
            created["app"] = self
            self.no_history = no_history
            self.safe_mode = safe_mode
            self.after_calls: list[int] = []
            self.interpreter_picker = FakeInterpreterPicker()
            self.workdir_var = FakeVar()
            self.status_workdir_var = FakeVar()
            self.mainloop_called = False

        def after(self, delay: int, callback: object) -> None:
            self.after_calls.append(delay)
            assert callable(callback)
            callback()

        def mainloop(self) -> None:
            self.mainloop_called = True

    fake_module = ModuleType("pip_ui.ui.main_window")
    cast(Any, fake_module).MainWindow = FakeMainWindow

    monkeypatch.setattr(cli_module, "configure_utf8_stdio", lambda: None)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    monkeypatch.setitem(sys.modules, "pip_ui.ui.main_window", fake_module)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pip-ui",
            "--interpreter",
            "C:\\Python313\\python.exe",
            "--working-directory",
            "C:\\work",
            "--no-history",
            "--safe-mode",
        ],
    )

    cli_module.main()

    app = created["app"]
    assert isinstance(app, FakeMainWindow)
    assert app.no_history is True
    assert app.safe_mode is True
    assert app.after_calls == [200]
    assert app.interpreter_picker.paths == ["C:\\Python313\\python.exe"]
    assert app.workdir_var.value == "C:\\work"
    assert app.status_workdir_var.value == "C:\\work"
    assert app.mainloop_called is True


def test_main_closes_cleanly_on_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl+C while the GUI mainloop is running should close without a traceback."""
    created: dict[str, object] = {}

    class FakeMainWindow:
        def __init__(self, *, no_history: bool, safe_mode: bool) -> None:
            _ = (no_history, safe_mode)
            created["app"] = self
            self.closed = False

        def mainloop(self) -> None:
            raise KeyboardInterrupt

        def on_close(self) -> None:
            self.closed = True

    fake_module = ModuleType("pip_ui.ui.main_window")
    cast(Any, fake_module).MainWindow = FakeMainWindow

    monkeypatch.setattr(cli_module, "configure_utf8_stdio", lambda: None)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    monkeypatch.setitem(sys.modules, "pip_ui.ui.main_window", fake_module)
    monkeypatch.setattr(sys, "argv", ["pip-ui"])

    cli_module.main()

    app = created["app"]
    assert isinstance(app, FakeMainWindow)
    assert app.closed is True


def test_run_diagnostics_uses_first_discovered_interpreter(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Diagnostics should default to the first discovered interpreter."""
    interpreter = InterpreterInfo(
        path="C:\\Python313\\python.exe",
        version="3.13.3",
        pip_version="25.1",
        is_venv=False,
        prefix="C:\\Python313",
        base_prefix="C:\\Python313",
        env_type="system",
    )
    seen: dict[str, str] = {}

    class FakeDiscovery:
        def discover(self) -> list[InterpreterInfo]:
            return [interpreter]

        def validate(self, interpreter_path: str) -> InterpreterInfo | None:
            seen["validated"] = interpreter_path
            return interpreter

    class FakeInspector:
        def __init__(self, path: str) -> None:
            seen["inspector_path"] = path

        def build_diagnostics_report(self, fmt: str) -> str:
            seen["format"] = fmt
            return "# diagnostics"

    environment_module = ModuleType("pip_ui.environment")
    cast(Any, environment_module).InterpreterDiscovery = FakeDiscovery
    config_module = ModuleType("pip_ui.config_inspector")
    cast(Any, config_module).ConfigInspector = FakeInspector

    monkeypatch.setitem(sys.modules, "pip_ui.environment", environment_module)
    monkeypatch.setitem(sys.modules, "pip_ui.config_inspector", config_module)

    cli_module.run_diagnostics(None)

    captured = capsys.readouterr()
    assert captured.out == "# diagnostics\n"
    assert captured.err == ""
    assert seen["inspector_path"] == interpreter.path
    assert seen["format"] == "markdown"
    assert "validated" not in seen


def test_run_diagnostics_warns_and_falls_back_when_validation_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An invalid requested interpreter should fall back to a discovered one."""
    interpreter = InterpreterInfo(
        path="C:\\Python313\\python.exe",
        version="3.13.3",
        pip_version="25.1",
        is_venv=False,
        prefix="C:\\Python313",
        base_prefix="C:\\Python313",
        env_type="system",
    )
    seen: dict[str, str] = {}

    class FakeDiscovery:
        def discover(self) -> list[InterpreterInfo]:
            return [interpreter]

        def validate(self, interpreter_path: str) -> InterpreterInfo | None:  # pylint: disable=useless-return
            seen["validated"] = interpreter_path
            return None

    class FakeInspector:
        def __init__(self, path: str) -> None:
            seen["inspector_path"] = path

        def build_diagnostics_report(self, fmt: str) -> str:
            seen["format"] = fmt
            return "# fallback diagnostics"

    environment_module = ModuleType("pip_ui.environment")
    cast(Any, environment_module).InterpreterDiscovery = FakeDiscovery
    config_module = ModuleType("pip_ui.config_inspector")
    cast(Any, config_module).ConfigInspector = FakeInspector

    monkeypatch.setitem(sys.modules, "pip_ui.environment", environment_module)
    monkeypatch.setitem(sys.modules, "pip_ui.config_inspector", config_module)

    cli_module.run_diagnostics("C:\\missing\\python.exe")

    captured = capsys.readouterr()
    assert "Could not validate interpreter" in captured.err
    assert captured.out == "# fallback diagnostics\n"
    assert seen["validated"] == "C:\\missing\\python.exe"
    assert seen["inspector_path"] == interpreter.path
    assert seen["format"] == "markdown"


def test_run_diagnostics_exits_when_no_interpreters_are_found(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Diagnostics should fail cleanly when no interpreters are available."""

    class FakeDiscovery:
        def discover(self) -> list[InterpreterInfo]:
            return []

        def validate(self, interpreter_path: str) -> InterpreterInfo | None:  # pylint: disable=useless-return
            _ = interpreter_path
            return None

    environment_module = ModuleType("pip_ui.environment")
    cast(Any, environment_module).InterpreterDiscovery = FakeDiscovery

    monkeypatch.setitem(sys.modules, "pip_ui.environment", environment_module)

    with pytest.raises(SystemExit) as excinfo:
        cli_module.run_diagnostics("C:\\missing\\python.exe")

    assert excinfo.value.code == 1
    assert "No Python interpreters found." in capsys.readouterr().err
