"""Pure-function helpers for proxy URL handling, extracted for testability."""

from __future__ import annotations

import os
import re

_CREDENTIAL_PATTERN = re.compile(r"(://)[^:@/\s]+:[^@/\s]+@")
_REDACT_PATTERN = re.compile(r"(://)[^:@/\s]+:[^@/\s]+@")

PROXY_ENV_KEYS = ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "NO_PROXY", "no_proxy"]


def redact_proxy_url(url: str) -> str:
    """Replace credentials in a proxy URL with ``<redacted>``."""
    return _REDACT_PATTERN.sub(r"\1<redacted>:<redacted>@", url)


def proxy_env_summary(env: dict[str, str] | None = None) -> str:
    """Return a display string of active proxy environment variables.

    Passwords are redacted.  Pass *env* explicitly for testing; defaults to
    ``os.environ``.
    """
    source = env if env is not None else os.environ
    lines: list[str] = []
    for k in PROXY_ENV_KEYS:
        v = source.get(k)
        if v:
            lines.append(f"{k}={redact_proxy_url(v)}")
    return "\n".join(lines)


def url_contains_credentials(url: str) -> bool:
    """Return True if *url* embeds a username:password pair."""
    return bool(_CREDENTIAL_PATTERN.search(url))
