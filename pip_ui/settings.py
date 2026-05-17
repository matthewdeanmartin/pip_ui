"""Application settings persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

DEFAULTS: dict[str, Any] = {
    "last_interpreter": None,
    "last_working_dir": None,
    "window_width": 1100,
    "window_height": 700,
    "redact_secrets": True,
    "show_advanced": False,
}


class AppSettings:
    def __init__(self) -> None:
        self.data_dir = Path.home() / ".pip_ui"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.data_dir / "settings.json"
        self.cache: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        if not self.settings_file.exists():
            self.cache = dict(DEFAULTS)
            return self.cache
        try:
            with open(self.settings_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            data = {}
        merged = dict(DEFAULTS)
        merged.update(data)
        self.cache = merged
        return self.cache

    def save(self, data: dict[str, Any]) -> None:
        self.cache = data
        with open(self.settings_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        if not self.cache:
            self.load()
        return self.cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if not self.cache:
            self.load()
        self.cache[key] = value
        self.save(self.cache)
