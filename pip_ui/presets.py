"""Named presets for command forms."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class PresetStore:
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir if data_dir is not None else Path.home() / ".pip_ui"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.presets_file = self.data_dir / "presets.json"

    def load(self) -> dict[str, dict[str, Any]]:
        if not self.presets_file.exists():
            return {}
        try:
            with open(self.presets_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    def save_all(self, presets: dict[str, dict[str, Any]]) -> None:
        with open(self.presets_file, "w", encoding="utf-8") as fh:
            json.dump(presets, fh, indent=2)

    def save(self, name: str, command_name: str, values: dict[str, Any]) -> None:
        presets = self.load()
        presets[name] = {"command": command_name, "values": values}
        self.save_all(presets)

    def get(self, name: str) -> Optional[dict[str, Any]]:
        return self.load().get(name)

    def delete(self, name: str) -> None:
        presets = self.load()
        if name in presets:
            del presets[name]
            self.save_all(presets)

    def names_for(self, command_name: str) -> list[str]:
        return [n for n, p in self.load().items() if p.get("command") == command_name]
