"""Detect requirements files in the current working directory.

Looks for ``requirements*.txt`` files and other ``*.txt`` files that *look* like
requirement files based on simple heuristics. Also reports a ``pyproject.toml``
if present (pip supports installing from a local project via ``-e .`` which uses
``pyproject.toml``).

Search is non-recursive (current directory only) per spec §2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Lines that obviously look like pip requirement specifiers.
_REQ_LINE_RE = re.compile(
    r"""^\s*
    (?:
        -r\s+\S+        # -r other-requirements.txt
      | -c\s+\S+        # -c constraints.txt
      | -e\s+.+         # -e editable
      | --[a-zA-Z-]+    # other pip options
      | [A-Za-z_][\w.\-]*\s*  # bare distribution name
        (?:\[[\w,.\-\s]*\])?  # optional extras
        (?:[<>=!~][^;\s]+)?   # optional version spec
        (?:\s*;.*)?           # optional environment marker
    )\s*$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class RequirementsCandidate:
    path: Path
    label: str
    kind: str  # 'requirements', 'pyproject', 'heuristic'


def detect_candidates(directory: Path) -> list[RequirementsCandidate]:
    """Return likely requirements/project files in *directory* (non-recursive)."""
    if not directory.exists() or not directory.is_dir():
        return []

    seen: set[Path] = set()
    results: list[RequirementsCandidate] = []

    # 1. Anything literally named requirements*.txt or constraints*.txt.
    explicit_globs = ("requirements*.txt", "constraints*.txt", "reqs*.txt")
    for pattern in explicit_globs:
        for path in sorted(directory.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                results.append(RequirementsCandidate(path=path, label=path.name, kind="requirements"))

    # 2. Heuristically inspect other .txt files.
    for path in sorted(directory.glob("*.txt")):
        if not path.is_file() or path in seen:
            continue
        if looks_like_requirements(path):
            seen.add(path)
            results.append(RequirementsCandidate(path=path, label=f"{path.name} (heuristic)", kind="heuristic"))

    # 3. pyproject.toml — pip supports `-e .` against it.
    pyproject = directory / "pyproject.toml"
    if pyproject.is_file():
        results.append(RequirementsCandidate(path=pyproject, label="pyproject.toml", kind="pyproject"))

    return results


def looks_like_requirements(path: Path, sample_lines: int = 30) -> bool:
    """Heuristic: does this .txt file look like a pip requirements file?

    A file passes if a majority of its non-blank, non-comment lines look like
    requirement specifiers (PEP 508-ish) or pip options.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            lines = []
            for i, raw in enumerate(fh):
                if i >= sample_lines:
                    break
                lines.append(raw)
    except OSError:
        return False

    meaningful = 0
    matched = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        meaningful += 1
        if _REQ_LINE_RE.match(line):
            matched += 1

    if meaningful == 0:
        return False
    # Require at least two meaningful lines, and >=80% looking like requirements.
    return meaningful >= 2 and (matched / meaningful) >= 0.8
