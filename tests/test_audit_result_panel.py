"""Unit tests for AuditResultPanel.load_json."""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

import json
import tkinter as tk

import pytest


@pytest.fixture(scope="module")
def root():
    try:
        r = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tkinter not available: {exc}")
    r.withdraw()
    yield r
    r.destroy()


def _make_panel(root):
    from pip_ui.ui.audit_result_panel import AuditResultPanel

    panel = AuditResultPanel(root)
    return panel


def test_load_valid_json_no_vulns(root):
    panel = _make_panel(root)
    data = {"dependencies": [{"name": "requests", "version": "2.28.0", "vulns": []}]}
    assert panel.load_json(json.dumps(data)) is True
    assert len(panel._tree.get_children()) == 0
    panel.destroy()


def test_load_valid_json_with_vuln(root):
    panel = _make_panel(root)
    data = {
        "dependencies": [
            {
                "name": "pillow",
                "version": "9.0.0",
                "vulns": [
                    {
                        "id": "PYSEC-2023-1",
                        "fix_versions": ["9.3.0"],
                        "aliases": ["CVE-2023-1234"],
                        "description": "Buffer overflow in Pillow.",
                    }
                ],
            }
        ]
    }
    assert panel.load_json(json.dumps(data)) is True
    children = panel._tree.get_children()
    assert len(children) == 1
    values = panel._tree.item(children[0], "values")
    assert values[0] == "pillow"
    assert values[1] == "9.0.0"
    assert values[2] == "PYSEC-2023-1"
    assert values[3] == "9.3.0"
    panel.destroy()


def test_load_malformed_json_returns_false(root):
    panel = _make_panel(root)
    assert panel.load_json("not json at all") is False
    panel.destroy()


def test_load_empty_dependencies(root):
    panel = _make_panel(root)
    assert panel.load_json(json.dumps({"dependencies": []})) is True
    assert len(panel._tree.get_children()) == 0
    panel.destroy()


def test_load_multiple_vulns_same_package(root):
    panel = _make_panel(root)
    data = {
        "dependencies": [
            {
                "name": "numpy",
                "version": "1.23.0",
                "vulns": [
                    {"id": "PYSEC-A", "fix_versions": [], "aliases": [], "description": "A"},
                    {"id": "PYSEC-B", "fix_versions": ["1.24.0"], "aliases": [], "description": "B"},
                ],
            }
        ]
    }
    assert panel.load_json(json.dumps(data)) is True
    assert len(panel._tree.get_children()) == 2
    panel.destroy()


def test_severity_unknown_when_no_aliases(root):
    panel = _make_panel(root)
    data = {
        "dependencies": [
            {
                "name": "pkg",
                "version": "1.0",
                "vulns": [{"id": "X-1", "fix_versions": [], "aliases": [], "description": ""}],
            }
        ]
    }
    panel.load_json(json.dumps(data))
    children = panel._tree.get_children()
    values = panel._tree.item(children[0], "values")
    assert values[4] == "Unknown"
    panel.destroy()


def test_sort_by_column_toggles(root):
    panel = _make_panel(root)
    data = {
        "dependencies": [
            {
                "name": "alpha",
                "version": "1.0",
                "vulns": [{"id": "ID-1", "fix_versions": [], "aliases": [], "description": ""}],
            },
            {
                "name": "beta",
                "version": "2.0",
                "vulns": [{"id": "ID-2", "fix_versions": [], "aliases": [], "description": ""}],
            },
        ]
    }
    panel.load_json(json.dumps(data))
    panel._sort_by("package")
    assert panel._sort_col == "package"
    assert panel._sort_reverse is False
    panel._sort_by("package")
    assert panel._sort_reverse is True
    panel.destroy()
