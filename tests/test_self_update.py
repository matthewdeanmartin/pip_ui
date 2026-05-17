"""Tests for pip_ui.self_update."""

from __future__ import annotations

from pip_ui.self_update import is_newer, parse_version


def test_parse_version_simple() -> None:
    assert parse_version("0.1.0") == (0, 1, 0)
    assert parse_version("12.34.56") == (12, 34, 56)


def test_parse_version_with_suffix() -> None:
    # Anything after a non-digit in a chunk is truncated.
    assert parse_version("1.2.3rc1") == (1, 2, 3)
    assert parse_version("1.2") == (1, 2)


def test_parse_version_garbage_falls_back_to_zero() -> None:
    assert parse_version("not-a-version") == (0,)


def test_is_newer_basic() -> None:
    assert is_newer("0.2.0", "0.1.0") is True
    assert is_newer("0.1.1", "0.1.0") is True
    assert is_newer("0.1.0", "0.1.0") is False
    assert is_newer("0.0.9", "0.1.0") is False
