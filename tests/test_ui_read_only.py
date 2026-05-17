"""Read-only UI tests for pip-ui."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any
from typing import cast
from unittest.mock import MagicMock

import pytest

from pip_ui.ui import config_view as config_view_module
from pip_ui.command_specs import COMMAND_SPECS
from pip_ui.models import InterpreterInfo
from pip_ui.ui.command_form import CommandForm
from pip_ui.ui.config_view import ConfigView
from pip_ui.ui.global_options_dialog import GlobalOptionsDialog
from pip_ui.ui.requirements_picker import RequirementsPicker


@pytest.fixture(scope="module")
def root():
    """Provides a headless Tk root for testing widgets."""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


def test_requirements_picker_detection(root, tmp_path):
    """Verify that RequirementsPicker detects and lists requirements files."""
    (tmp_path / "requirements.txt").write_text("requests\n")
    (tmp_path / "dev-requirements.txt").write_text("pytest\nmypy\n")
    (tmp_path / "other.txt").write_text("not a requirements file\n")

    on_change = MagicMock()
    picker = RequirementsPicker(root, on_change=on_change)
    picker.set_directory(tmp_path)

    # Check labels in the combobox
    labels = picker.combo["values"]
    assert "(none)" in labels
    assert "requirements.txt" in labels
    assert "dev-requirements.txt (heuristic)" in labels
    assert "other.txt" not in labels


def test_command_form_read_only_list(root):
    """Verify that CommandForm correctly renders a read-only command like 'list'."""
    spec = COMMAND_SPECS["list"]
    on_run = MagicMock()

    # We need a provider for global options
    global_options = {"g_verbose": False}

    def global_provider():
        return global_options

    form = CommandForm(root, on_run=on_run, global_values_provider=global_provider)
    form.set_command(spec)

    # Verify that the form has fields matching the spec
    spec_arg_names = {arg.name for arg in spec.args}
    form_arg_names = {fw.arg.name for fw in form.field_widgets}
    assert spec_arg_names.issubset(form_arg_names)

    # Simulate clicking 'Run'
    form.do_run()

    # on_run should be called with argv and a label
    assert on_run.called
    args, _kwargs = on_run.call_args
    argv = args[0]
    assert "list" in argv


def test_config_view_no_interpreter(root):
    """Verify that ConfigView shows a message when no interpreter is selected."""
    view = ConfigView(root, interpreter_info=None)
    try:
        # It should have one section saying "No Interpreter Selected"
        found = False
        for widget in view.content_frame.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and "No Interpreter Selected" in widget.cget("text"):
                found = True
                break
        assert found
    finally:
        view.destroy()


def test_config_view_with_interpreter(root):
    """Verify that ConfigView populates sections when an interpreter is provided."""
    info = InterpreterInfo(
        path="/usr/bin/python",
        version="3.12.0",
        env_type="system",
        is_venv=False,
        prefix="/usr",
        base_prefix="/usr",
        pip_version="24.0",
    )

    mock_ci_class = MagicMock()
    config_view_any = cast(Any, config_view_module)
    original_ci = config_view_any.ConfigInspector
    config_view_any.ConfigInspector = mock_ci_class

    mock_inspector_inst = mock_ci_class.return_value
    mock_inspector_inst.run_config_debug.return_value = "debug info"
    mock_inspector_inst.run_config_list.return_value = {"key": "value"}
    mock_inspector_inst.run_pip_debug.return_value = "pip debug info"
    mock_inspector_inst.run_cache_info.return_value = "cache info"
    mock_inspector_inst.run_cache_dir.return_value = "/cache/dir"
    mock_inspector_inst.get_pip_version.return_value = "24.0"

    view = None
    try:
        view = ConfigView(root, interpreter_info=info)
        # Verify that some sections were added
        assert len(view.content_frame.winfo_children()) > 1
    finally:
        if view:
            view.destroy()
        config_view_any.ConfigInspector = original_ci


def test_global_options_dialog_apply(root):
    """Verify that GlobalOptionsDialog correctly returns values on apply."""
    initial_values = {"g_verbose": True, "g_proxy": "http://proxy.com"}
    on_apply = MagicMock()

    dialog = GlobalOptionsDialog(root, initial_values, on_apply)
    try:
        # Check if vars are correctly initialized
        assert dialog.vars["g_verbose"].get() is True
        assert dialog.vars["g_proxy"].get() == "http://proxy.com"

        # Change a value
        cast(Any, dialog.vars["g_verbose"]).set(False)

        # Simulate 'OK'
        dialog.apply()

        assert on_apply.called
        args, _kwargs = on_apply.call_args
        new_values = args[0]
        assert new_values["g_verbose"] is False
        assert new_values["g_proxy"] == "http://proxy.com"
    finally:
        dialog.destroy()


def test_requirements_picker_selection(root, tmp_path):
    """Verify that selecting a file in RequirementsPicker triggers on_change."""
    req_path = tmp_path / "requirements.txt"
    req_path.write_text("requests\n")

    on_change = MagicMock()
    picker = RequirementsPicker(root, on_change=on_change)
    picker.set_directory(tmp_path)

    # Find the index for requirements.txt
    labels = list(picker.combo["values"])
    idx = labels.index("requirements.txt")

    # Simulate selection
    picker.combo.current(idx)
    picker.on_combo_select(None)

    on_change.assert_called_with(str(req_path))
