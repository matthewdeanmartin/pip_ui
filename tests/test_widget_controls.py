"""Widget-level tests for small Tkinter control components."""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast
from unittest.mock import MagicMock

import pytest

try:
    import tkinter as tk
    from tkinter import ttk

    from pip_ui.models import CommandSpec, InterpreterInfo, SafetyLevel
    from pip_ui.tools import ToolPlugin
    from pip_ui.ui import interpreter_picker as interpreter_picker_module
    from pip_ui.ui import pipx_python_picker as pipx_python_picker_module
    from pip_ui.ui import tool_switcher as tool_switcher_module
    from pip_ui.ui.command_tree import CommandTree
except ModuleNotFoundError:
    pytest.skip("tkinter not installed", allow_module_level=True)


@pytest.fixture(scope="module")
def root() -> Iterator[tk.Tk]:
    """Provide a headless Tk root for widget tests."""
    try:
        app = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tkinter initialize failed: {exc}")
    app.withdraw()
    yield app
    app.destroy()


def make_interpreter(
    path: str,
    version: str,
    *,
    pip_version: str = "25.1",
    is_venv: bool = False,
) -> InterpreterInfo:
    """Create an InterpreterInfo with stable defaults."""
    return InterpreterInfo(
        path=path,
        version=version,
        pip_version=pip_version,
        is_venv=is_venv,
        prefix=path.rsplit("\\", maxsplit=1)[0],
        base_prefix=path.rsplit("\\", maxsplit=1)[0],
        env_type="venv" if is_venv else "system",
    )


def make_plugin(name: str, label: str, *, extra: str | None = None) -> ToolPlugin:
    """Create a minimal plugin definition for ToolSwitcher tests."""
    return ToolPlugin(
        name=name,
        label=label,
        extra=extra or name,
        run_via="python_module",
        executable=name,
        command_specs={},
        command_groups=[],
        help_url=f"https://example.com/{name}",
    )


def make_spec(name: str, label: str, group: str, description: str) -> CommandSpec:
    """Create a minimal read-only command spec for tree tests."""
    return CommandSpec(
        name=name,
        label=label,
        group=group,
        description=description,
        safety_level=SafetyLevel.READ_ONLY,
        args=[],
    )


def test_tool_switcher_clicking_unavailable_tool_shows_install_hint(
    root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable tool tabs should show a hint instead of switching."""
    pip_plugin = make_plugin("pip", "Pip")
    build_plugin = make_plugin("build", "Build")
    plugins = (pip_plugin, build_plugin)
    info_dialog = MagicMock()

    monkeypatch.setattr(tool_switcher_module, "get_registry", lambda: plugins)
    monkeypatch.setattr(
        tool_switcher_module,
        "get_plugin",
        lambda name: next((p for p in plugins if p.name == name), None),
    )
    monkeypatch.setattr(tool_switcher_module, "info_dialog", info_dialog)

    on_switch = MagicMock()
    switcher = tool_switcher_module.ToolSwitcher(root, on_switch=on_switch)
    try:
        switcher._buttons["build"].invoke()

        info_dialog.assert_called_once()
        assert "pip install pip-ui-tkinter[build]" in info_dialog.call_args.args[2]
        on_switch.assert_not_called()
        assert switcher._buttons["build"].cget("style") == "Disabled.TButton"
    finally:
        switcher.destroy()


def test_tool_switcher_selects_available_tool_and_configures_styles(
    root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Available tabs should switch tools and update their ttk style."""
    pip_plugin = make_plugin("pip", "Pip")
    build_plugin = make_plugin("build", "Build")
    plugins = (pip_plugin, build_plugin)

    monkeypatch.setattr(tool_switcher_module, "get_registry", lambda: plugins)
    monkeypatch.setattr(
        tool_switcher_module,
        "get_plugin",
        lambda name: next((p for p in plugins if p.name == name), None),
    )

    on_switch = MagicMock()
    switcher = tool_switcher_module.ToolSwitcher(root, on_switch=on_switch)
    try:
        tool_switcher_module.ToolSwitcher.configure_styles(root)
        assert ttk.Style(root).lookup("Active.TButton", "foreground") == "black"

        switcher.set_available("build", True)
        switcher.select("build")

        assert on_switch.call_args.args == (build_plugin,)
        assert switcher._buttons["build"].cget("style") == "Active.TButton"
        assert switcher._buttons["pip"].cget("style") == "TButton"
    finally:
        switcher.destroy()


def test_interpreter_picker_refresh_select_and_set_from_path(
    root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """InterpreterPicker should track discovered interpreters and selection changes."""
    first = make_interpreter("C:\\Python312\\python.exe", "3.12.9")
    second = make_interpreter("C:\\Python313\\python.exe", "3.13.2", is_venv=True)

    class FakeDiscovery:
        def discover(self) -> list[InterpreterInfo]:
            return [first, second]

        def validate(self, path: str) -> InterpreterInfo | None:
            return {"C:\\Python312\\python.exe": first, "C:\\Python313\\python.exe": second}.get(path)

    monkeypatch.setattr(interpreter_picker_module, "InterpreterDiscovery", FakeDiscovery)

    on_change = MagicMock()
    picker = interpreter_picker_module.InterpreterPicker(root, on_change=on_change)
    try:
        assert list(picker.combo["values"]) == [first.display_label(), second.display_label()]
        assert picker.get_selected() == first
        assert on_change.call_args.args == (first,)

        picker.combo.current(1)
        picker.on_combo_select(None)
        assert picker.get_selected() == second
        assert on_change.call_args.args == (second,)

        picker.set_from_path(first.path)
        assert picker.get_selected() == first
        assert on_change.call_args.args == (first,)
    finally:
        picker.destroy()


def test_interpreter_picker_browse_handles_invalid_and_valid_paths(
    root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Browsing should reject invalid executables and accept validated ones."""
    selected = make_interpreter("C:\\Custom\\python.exe", "3.13.3")
    browse_results = iter(["C:\\bad\\python.exe", selected.path])
    error_dialog = MagicMock()

    class FakeDiscovery:
        def discover(self) -> list[InterpreterInfo]:
            return []

        def validate(self, path: str) -> InterpreterInfo | None:
            return selected if path == selected.path else None

    monkeypatch.setattr(interpreter_picker_module, "InterpreterDiscovery", FakeDiscovery)
    monkeypatch.setattr(interpreter_picker_module, "browse_interpreter_dialog", lambda _parent: next(browse_results))
    monkeypatch.setattr(interpreter_picker_module, "error_dialog", error_dialog)

    on_change = MagicMock()
    picker = interpreter_picker_module.InterpreterPicker(root, on_change=on_change)
    try:
        picker.browse()
        error_dialog.assert_called_once()
        assert picker.get_selected() is None
        on_change.assert_not_called()

        picker.browse()
        assert picker.get_selected() == selected
        assert list(picker.combo["values"]) == [selected.display_label()]
        assert on_change.call_args.args == (selected,)
    finally:
        picker.destroy()


def test_pipx_python_picker_tracks_default_and_explicit_selection(
    root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PipxPythonPicker should map combobox rows back to interpreter paths."""
    first = make_interpreter("C:\\Python311\\python.exe", "3.11.11")
    second = make_interpreter("C:\\Python313\\python.exe", "3.13.3")

    class FakeDiscovery:
        def discover(self) -> list[InterpreterInfo]:
            return [first, second]

    monkeypatch.setattr(pipx_python_picker_module, "InterpreterDiscovery", FakeDiscovery)

    on_change = MagicMock()
    picker = pipx_python_picker_module.PipxPythonPicker(root, on_change=on_change)
    try:
        assert list(picker._combo["values"]) == [
            "(pipx default)",
            f"{first.path} ({first.version})",
            f"{second.path} ({second.version})",
        ]
        assert picker.get_python_path() is None
        assert on_change.call_args.args == (None,)

        picker._combo.current(2)
        picker._on_select(None)

        assert picker.get_python_path() == second.path
        assert on_change.call_args.args == (second.path,)
    finally:
        picker.destroy()


def test_command_tree_loads_filters_selects_and_resets_search(root: tk.Tk) -> None:
    """CommandTree should support filtering and selection on loaded plugin commands."""
    on_select = MagicMock()
    tree = CommandTree(cast(tk.Widget, root), on_select=on_select)
    try:
        assert tree.tree.get_children()

        install = make_spec("install", "Install", "Packages", "Install packages into the environment.")
        inspect = make_spec("inspect", "Inspect", "Diagnostics", "Show package metadata and environment details.")
        tree.load_plugin({"install": install, "inspect": inspect}, ["Packages", "Diagnostics"])
        assert len(tree.tree.get_children()) == 2

        tree.search_var.set("metadata")
        visible_groups = tree.tree.get_children()
        assert len(visible_groups) == 1

        item_ids = tree.tree.get_children(visible_groups[0])
        assert len(item_ids) == 1
        assert tree.item_to_command[item_ids[0]] == "inspect"

        tree.tree.selection_set(item_ids[0])
        tree.on_tree_select(None)
        on_select.assert_called_once_with("inspect")

        tree.focus_search()
        assert tree.search_var.get() == ""
        assert len(tree.tree.get_children()) == 2
    finally:
        tree.destroy()
