"""Tests for UTF-8 defaults."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import cast

import pytest

from pip_ui.encoding import (
    UTF8_ENCODING,
    UTF8_OUTPUT_ERRORS,
    UTF8_SUBPROCESS_ERRORS,
    build_utf8_subprocess_env,
    configure_utf8_stdio,
    utf8_subprocess_kwargs,
)


def test_build_utf8_subprocess_env_sets_python_defaults() -> None:
    env = build_utf8_subprocess_env({})

    assert env["PYTHONUTF8"] == "1"
    assert env["PYTHONIOENCODING"] == UTF8_ENCODING


def test_build_utf8_subprocess_env_preserves_existing_values() -> None:
    base_env = cast(MutableMapping[str, str], {"PYTHONUTF8": "0", "PYTHONIOENCODING": "latin-1"})

    env = build_utf8_subprocess_env(base_env)

    assert env["PYTHONUTF8"] == "0"
    assert env["PYTHONIOENCODING"] == "latin-1"


def test_utf8_subprocess_kwargs_include_encoding_and_env() -> None:
    kwargs = utf8_subprocess_kwargs()

    assert kwargs["text"] is True
    assert kwargs["encoding"] == UTF8_ENCODING
    assert kwargs["errors"] == UTF8_SUBPROCESS_ERRORS
    assert kwargs["env"]["PYTHONUTF8"] == "1"
    assert kwargs["env"]["PYTHONIOENCODING"] == UTF8_ENCODING


def test_configure_utf8_stdio_reconfigures_output_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str]] = []

    class FakeStream:
        def __init__(self, name: str) -> None:
            self.name = name

        def reconfigure(self, *, encoding: str, errors: str) -> None:
            calls.append((self.name, encoding, errors))

    monkeypatch.setattr("sys.stdout", FakeStream("stdout"))
    monkeypatch.setattr("sys.stderr", FakeStream("stderr"))

    configure_utf8_stdio()

    assert calls == [
        ("stdout", UTF8_ENCODING, UTF8_OUTPUT_ERRORS),
        ("stderr", UTF8_ENCODING, UTF8_OUTPUT_ERRORS),
    ]
