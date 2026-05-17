"""Tests for history module."""

from datetime import datetime
from pathlib import Path

import pytest

from pip_ui.history import CommandHistory
from pip_ui.models import HistoryEntry


def make_entry(label: str = "Install", exit_code: int = 0) -> HistoryEntry:
    return HistoryEntry(
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        command_label=label,
        argv_redacted=["python", "-m", "pip", "install", "requests"],
        command_redacted="python -m pip install requests",
        exit_code=exit_code,
        duration=1.23,
        interpreter_path="/usr/bin/python3",
        working_directory="/home/user/project",
    )


def test_add_and_load(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    entry = make_entry()
    history.add(entry)
    loaded = history.load()
    assert len(loaded) == 1
    assert loaded[0].command_label == "Install"
    assert loaded[0].exit_code == 0
    assert loaded[0].duration == pytest.approx(1.23)


def test_history_persists_to_file(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    history.add(make_entry("Freeze"))
    history2 = CommandHistory(data_dir=tmp_path)
    loaded = history2.load()
    assert len(loaded) == 1
    assert loaded[0].command_label == "Freeze"


def test_clear(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    history.add(make_entry())
    history.add(make_entry("List"))
    history.clear()
    loaded = history.load()
    assert len(loaded) == 0


def test_multiple_entries(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    for label in ["Install", "List", "Freeze", "Check"]:
        history.add(make_entry(label))
    loaded = history.load()
    assert len(loaded) == 4
    labels = [e.command_label for e in loaded]
    assert "Install" in labels
    assert "Check" in labels


def test_load_empty(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    loaded = history.load()
    assert not loaded


def test_entry_timestamp_preserved(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    ts = datetime(2024, 6, 1, 12, 0, 0)
    entry = HistoryEntry(
        timestamp=ts,
        command_label="Test",
        argv_redacted=["python", "-m", "pip", "list"],
        command_redacted="python -m pip list",
        exit_code=0,
        duration=0.5,
        interpreter_path="/usr/bin/python3",
        working_directory="/tmp",
    )
    history.add(entry)
    loaded = history.load()
    assert loaded[0].timestamp == ts


def test_load_skips_invalid_json_line(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    history.history_file.write_text("{invalid json}\n", encoding="utf-8")
    assert not history.load()


def test_load_skips_missing_fields(tmp_path: Path) -> None:
    history = CommandHistory(data_dir=tmp_path)
    history.history_file.write_text('{"timestamp":"2024-06-01T12:00:00"}\n', encoding="utf-8")
    assert not history.load()
