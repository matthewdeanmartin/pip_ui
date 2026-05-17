"""Tests for the chip-style summarizer used in the new Global Options UI."""

from __future__ import annotations

from pip_ui.ui.command_form import default_global_values
from pip_ui.ui.global_options_dialog import summarize_globals


def test_summary_empty_when_all_defaults() -> None:
    assert summarize_globals(default_global_values()) == []


def test_summary_shows_enabled_boolean() -> None:
    values = default_global_values()
    values["g_verbose"] = True
    chips = summarize_globals(values)
    assert any("Verbose" in c for c in chips)


def test_summary_shows_textual_override() -> None:
    values = default_global_values()
    values["g_proxy"] = "http://corp.proxy:8080"
    chips = summarize_globals(values)
    assert any("Proxy=" in c for c in chips)


def test_summary_truncates_long_values() -> None:
    values = default_global_values()
    values["g_cache_dir"] = "/very/long/path/" + ("x" * 80)
    chips = summarize_globals(values)
    chip = next(c for c in chips if c.startswith("Cache Dir="))
    assert chip.endswith("...")
