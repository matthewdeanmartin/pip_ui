"""Tests for application settings persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from pip_ui.settings import DEFAULTS, AppSettings


def patch_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))


def test_load_returns_defaults_when_file_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """load should return defaults when no settings file exists yet."""
    patch_home(monkeypatch, tmp_path)

    settings = AppSettings()

    assert settings.load() == DEFAULTS
    assert settings.cache == DEFAULTS


def test_load_merges_saved_values_with_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Persisted settings should overlay the default values."""
    patch_home(monkeypatch, tmp_path)
    settings_dir = tmp_path / ".pip_ui"
    settings_dir.mkdir()
    (settings_dir / "settings.json").write_text(
        '{"window_width": 900, "last_working_dir": "C:\\\\work"}',
        encoding="utf-8",
    )

    settings = AppSettings()
    loaded = settings.load()

    assert loaded["window_width"] == 900
    assert loaded["last_working_dir"] == "C:\\work"
    assert loaded["window_height"] == DEFAULTS["window_height"]
    assert loaded["redact_secrets"] is True


def test_load_recovers_from_invalid_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Corrupt settings files should fall back to defaults."""
    patch_home(monkeypatch, tmp_path)
    settings_dir = tmp_path / ".pip_ui"
    settings_dir.mkdir()
    (settings_dir / "settings.json").write_text("{not-json", encoding="utf-8")

    settings = AppSettings()

    assert settings.load() == DEFAULTS


def test_get_triggers_lazy_load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get should load settings on first access."""
    patch_home(monkeypatch, tmp_path)

    settings = AppSettings()

    assert settings.get("window_width") == DEFAULTS["window_width"]
    assert settings.cache["window_width"] == DEFAULTS["window_width"]


def test_set_updates_cache_and_persists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """set should load defaults, update the cache, and write the settings file."""
    patch_home(monkeypatch, tmp_path)

    settings = AppSettings()
    settings.set("show_advanced", True)

    reloaded = AppSettings()
    assert reloaded.get("show_advanced") is True
    assert reloaded.get("redact_secrets") is True


def test_get_tool_options_returns_empty_dict_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_home(monkeypatch, tmp_path)
    settings = AppSettings()
    assert settings.get_tool_options("hatch") == {}


def test_set_tool_options_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_home(monkeypatch, tmp_path)
    settings = AppSettings()
    settings.set_tool_options("twine", {"repository": "testpypi"})
    assert settings.get_tool_options("twine") == {"repository": "testpypi"}


def test_set_tool_options_does_not_clobber_other_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_home(monkeypatch, tmp_path)
    settings = AppSettings()
    settings.set_tool_options("hatch", {"env": "default"})
    settings.set_tool_options("twine", {"repository": "pypi"})
    assert settings.get_tool_options("hatch") == {"env": "default"}
    assert settings.get_tool_options("twine") == {"repository": "pypi"}


def test_active_tool_default_is_pip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    patch_home(monkeypatch, tmp_path)
    settings = AppSettings()
    assert settings.get("active_tool") == "pip"
