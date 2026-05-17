"""Tests for the preset store."""

from __future__ import annotations

from pathlib import Path

from pip_ui.presets import PresetStore


def test_save_and_get(tmp_path: Path) -> None:
    store = PresetStore(data_dir=tmp_path)
    store.save("Install requests", "install", {"fields": {"packages": "requests"}})
    preset = store.get("Install requests")
    assert preset is not None
    assert preset["command"] == "install"
    assert preset["values"]["fields"]["packages"] == "requests"


def test_names_for(tmp_path: Path) -> None:
    store = PresetStore(data_dir=tmp_path)
    store.save("install one", "install", {})
    store.save("install two", "install", {})
    store.save("list outdated", "list", {})
    assert sorted(store.names_for("install")) == ["install one", "install two"]
    assert store.names_for("list") == ["list outdated"]


def test_delete(tmp_path: Path) -> None:
    store = PresetStore(data_dir=tmp_path)
    store.save("p", "install", {})
    store.delete("p")
    assert store.get("p") is None


def test_persists_across_instances(tmp_path: Path) -> None:
    store1 = PresetStore(data_dir=tmp_path)
    store1.save("p", "install", {"fields": {"upgrade": True}})
    store2 = PresetStore(data_dir=tmp_path)
    assert store2.get("p") is not None


def test_load_empty_returns_dict(tmp_path: Path) -> None:
    store = PresetStore(data_dir=tmp_path)
    assert store.load() == {}


def test_save_overwrites(tmp_path: Path) -> None:
    store = PresetStore(data_dir=tmp_path)
    store.save("p", "install", {"v": 1})
    store.save("p", "install", {"v": 2})
    p = store.get("p")
    assert p is not None
    assert p["values"]["v"] == 2


def test_load_invalid_json_returns_empty_dict(tmp_path: Path) -> None:
    store = PresetStore(data_dir=tmp_path)
    store.presets_file.write_text("{not json}", encoding="utf-8")
    assert store.load() == {}
