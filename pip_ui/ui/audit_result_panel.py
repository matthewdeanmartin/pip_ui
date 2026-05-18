"""AuditResultPanel — sortable table of pip-audit JSON results."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any, ClassVar


def _severity_from_aliases(aliases: list[str]) -> str:
    """Heuristically derive severity from CVE/GHSA aliases."""
    for alias in aliases:
        alias_upper = alias.upper()
        if "CRITICAL" in alias_upper:
            return "CRITICAL"
        if "HIGH" in alias_upper:
            return "HIGH"
        if "MEDIUM" in alias_upper or "MODERATE" in alias_upper:
            return "MEDIUM"
        if "LOW" in alias_upper:
            return "LOW"
    return "Unknown"


_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "Unknown": 4}


class AuditResultPanel(ttk.Frame):
    """Displays pip-audit JSON output as a sortable treeview table."""

    COLUMNS = ("package", "installed", "vuln_id", "fix_version", "severity")
    COL_LABELS: ClassVar[dict[str, str]] = {
        "package": "Package",
        "installed": "Installed",
        "vuln_id": "Vuln ID",
        "fix_version": "Fix Version",
        "severity": "Severity",
    }

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self._sort_col: str = "severity"
        self._sort_reverse: bool = False
        self._rows: list[dict[str, str]] = []
        self._desc_map: dict[str, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        # Treeview with columns
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )
        scrollbar.config(command=self._tree.yview)
        self._tree.pack(fill=tk.BOTH, expand=True)

        for col in self.COLUMNS:

            def _make_sort_cmd(c: str) -> Any:
                return lambda: self._sort_by(c)

            self._tree.heading(
                col,
                text=self.COL_LABELS[col],
                command=_make_sort_cmd(col),
            )
            self._tree.column(col, width=140, anchor=tk.W)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Description area below
        sep = ttk.Separator(self, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=2)

        desc_frame = ttk.Frame(self)
        desc_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

        ttk.Label(desc_frame, text="Description:").pack(anchor=tk.W)
        desc_scroll = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL)
        desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._desc_text = tk.Text(
            desc_frame,
            height=5,
            wrap=tk.WORD,
            state=tk.DISABLED,
            yscrollcommand=desc_scroll.set,
        )
        self._desc_text.pack(fill=tk.X, expand=True)
        desc_scroll.config(command=self._desc_text.yview)

    # ---- public API ---------------------------------------------------------

    def load_json(self, json_str: str) -> bool:
        """Parse pip-audit JSON and populate the table. Returns True on success."""
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            self._show_raw(json_str)
            return False

        dependencies = data.get("dependencies", [])
        self._rows = []
        self._desc_map = {}
        self._tree.delete(*self._tree.get_children())

        for dep in dependencies:
            name = dep.get("name", "")
            version = dep.get("version", "")
            for vuln in dep.get("vulns", []):
                vuln_id = vuln.get("id", "")
                fix_versions = vuln.get("fix_versions", [])
                fix_str = ", ".join(fix_versions) if fix_versions else "None"
                aliases = vuln.get("aliases", [])
                severity = _severity_from_aliases(aliases)
                description = vuln.get("description", "")
                row = {
                    "package": name,
                    "installed": version,
                    "vuln_id": vuln_id,
                    "fix_version": fix_str,
                    "severity": severity,
                }
                self._rows.append(row)
                self._desc_map[vuln_id] = description

        self._refresh_tree()
        return True

    # ---- internal -----------------------------------------------------------

    def _show_raw(self, text: str) -> None:
        """Replace treeview with a plain text fallback."""
        self._tree.delete(*self._tree.get_children())
        self._set_desc(f"(Could not parse JSON output)\n\n{text[:2000]}")

    def _refresh_tree(self) -> None:
        self._tree.delete(*self._tree.get_children())
        rows = sorted(
            self._rows,
            key=lambda r: (
                _SEVERITY_ORDER.get(r["severity"], 4),
                r["package"],
                r["vuln_id"],
            ),
            reverse=self._sort_reverse,
        )
        if self._sort_col != "severity":
            rows = sorted(rows, key=lambda r: r[self._sort_col], reverse=self._sort_reverse)
        for row in rows:
            self._tree.insert(
                "",
                tk.END,
                iid=row["vuln_id"],
                values=(
                    row["package"],
                    row["installed"],
                    row["vuln_id"],
                    row["fix_version"],
                    row["severity"],
                ),
            )

    def _sort_by(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False
        self._refresh_tree()

    def _on_select(self, _event: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        vuln_id = sel[0]
        desc = self._desc_map.get(vuln_id, "")
        self._set_desc(desc or "(no description)")

    def _set_desc(self, text: str) -> None:
        self._desc_text.configure(state=tk.NORMAL)
        self._desc_text.delete("1.0", tk.END)
        self._desc_text.insert(tk.END, text)
        self._desc_text.configure(state=tk.DISABLED)
