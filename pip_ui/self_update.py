"""Self-upgrade helpers for pip-ui.

Checks PyPI in the background for a newer pip-ui release and offers a one-click
upgrade. Uses only the standard library — no network call is made unless this
module is imported and ``check_latest_version`` is invoked.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

PYPI_URL = "https://pypi.org/pypi/pip_ui/json"
USER_AGENT = "pip-ui-self-update/1.0"


@dataclass(frozen=True)
class UpgradeInfo:
    current: str
    latest: str
    available: bool


def parse_version(value: str) -> tuple[int, ...]:
    """Parse a PEP 440-ish version into a tuple for comparison.

    Anything that doesn't parse cleanly returns ``(0,)`` so it sorts as oldest.
    """
    parts: list[int] = []
    for chunk in value.strip().split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            return (0,)
        parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def fetch_latest_version(timeout: float = 5.0) -> str | None:
    """Fetch the latest version of pip-ui from PyPI. Returns None on failure."""
    req = urllib.request.Request(PYPI_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            payload = json.load(resp)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        return None
    info = payload.get("info") or {}
    version = info.get("version")
    return version if isinstance(version, str) else None


def check_latest_version(current: str, on_result: Callable[[UpgradeInfo | None], None]) -> None:
    """Check PyPI for the latest version in a background thread.

    Invokes ``on_result`` with the upgrade info, or ``None`` on failure. The
    callback runs on the worker thread; UI code should marshal it back to the
    main thread itself.
    """

    def worker() -> None:
        latest = fetch_latest_version()
        if latest is None:
            on_result(None)
            return
        on_result(UpgradeInfo(current=current, latest=latest, available=is_newer(latest, current)))

    thread = threading.Thread(target=worker, daemon=True, name="pip-ui-update-check")
    thread.start()
