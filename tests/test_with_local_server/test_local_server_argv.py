"""Command-building checks for local-server related tools."""

from __future__ import annotations

from .helpers import build_gui_argv, default_values


def test_pypiserver_version_argv_uses_dash_dash_version() -> None:
    """pypiserver version should use the top-level --version flag."""
    argv = build_gui_argv("pypiserver", "pypiserver_version", default_values("pypiserver", "pypiserver_version"))
    assert argv[-1] == "--version"


def test_devpi_version_argv_uses_dash_dash_version() -> None:
    """devpi version should use the top-level --version flag."""
    argv = build_gui_argv("devpi", "devpi_version", default_values("devpi", "devpi_version"))
    assert argv[-1] == "--version"


def test_devpi_index_create_argv_uses_create_flag_and_keyvalues() -> None:
    """devpi index creation should use the real CLI form: index -c NAME key=value."""
    values = default_values("devpi", "devpi_index_create")
    values["index_name"] = "testindex"
    values["bases"] = ""
    values["volatile"] = True
    argv = build_gui_argv("devpi", "devpi_index_create", values)
    assert argv[-5:] == ["index", "-c", "testindex", "bases=", "volatile=True"]


def test_devpi_index_delete_argv_uses_delete_flag() -> None:
    """devpi index deletion should use --delete instead of a delete subcommand."""
    values = default_values("devpi", "devpi_index_delete")
    values["index_name"] = "testindex"
    argv = build_gui_argv("devpi", "devpi_index_delete", values)
    assert argv[-3:] == ["index", "--delete", "testindex"]


def test_devpi_index_list_argv_uses_list_flag() -> None:
    """devpi index listing should use index -l."""
    argv = build_gui_argv("devpi", "devpi_index_list", default_values("devpi", "devpi_index_list"))
    assert argv[-2:] == ["index", "-l"]
