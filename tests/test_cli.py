"""Smoke tests for the CLI entry point."""

import pip_ui
from pip_ui.__about__ import __version__


def test_import() -> None:
    """Package can be imported."""
    assert pip_ui is not None


def test_version() -> None:
    """Package exposes a version string."""
    assert isinstance(__version__, str)
    assert __version__
