"""Integration tests for dry-run mode."""

from __future__ import annotations

import pytest

from pip_ui.ui.main_window import MainWindow


# @pytest.mark.skipif(sys.platform == "win32", reason="Tkinter tests can be flaky on CI windows")
def test_main_window_dry_run_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that MainWindow in dry_run mode 'executes' a command by printing it."""
    pytest.importorskip("tkinter")

    # Mock tool detection to avoid background threads firing after destroy()
    monkeypatch.setattr(MainWindow, "_start_tool_detection", lambda self: None)
    # Mock version check too
    monkeypatch.setattr("pip_ui.ui.main_window.check_latest_version", lambda v, cb: None)

    # Create root but don't start mainloop
    app = MainWindow(dry_run=True, no_history=True)

    # Select a command (e.g., 'list')
    app.command_tree.on_select("list")

    # Wait for auto-run if applicable or manually trigger
    app.run_command(["list"], "List Packages")

    # Poll queues to process output
    app.poll_queues()

    output = app.output_panel.get_stdout_text()
    assert "Dry run:" in output
    assert "-m pip list" in output

    app.destroy()
