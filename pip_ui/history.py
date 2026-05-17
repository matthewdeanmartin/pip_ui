"""Command history stored as JSON Lines."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pip_ui.models import HistoryEntry


class CommandHistory:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir if data_dir is not None else Path.home() / ".pip_ui"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "history.jsonl"

    def add(self, entry: HistoryEntry) -> None:
        record = {
            "timestamp": entry.timestamp.isoformat(),
            "command_label": entry.command_label,
            "argv_redacted": entry.argv_redacted,
            "command_redacted": entry.command_redacted,
            "exit_code": entry.exit_code,
            "duration": entry.duration,
            "interpreter_path": entry.interpreter_path,
            "working_directory": entry.working_directory,
        }
        with open(self.history_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def load(self) -> list[HistoryEntry]:
        if not self.history_file.exists():
            return []
        entries: list[HistoryEntry] = []
        with open(self.history_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    entry = HistoryEntry(
                        timestamp=datetime.fromisoformat(record["timestamp"]),
                        command_label=record["command_label"],
                        argv_redacted=record["argv_redacted"],
                        command_redacted=record["command_redacted"],
                        exit_code=record["exit_code"],
                        duration=record["duration"],
                        interpreter_path=record["interpreter_path"],
                        working_directory=record["working_directory"],
                    )
                    entries.append(entry)
                except (KeyError, ValueError):
                    continue
        return entries

    def clear(self) -> None:
        if self.history_file.exists():
            self.history_file.write_text("", encoding="utf-8")
