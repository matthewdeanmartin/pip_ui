"""Tests for pip_ui.requirements_detect."""

from __future__ import annotations

from pathlib import Path

from pip_ui.requirements_detect import detect_candidates, looks_like_requirements


def test_detects_requirements_txt(tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.31.0\nflask>=2.0\n")
    candidates = detect_candidates(tmp_path)
    paths = [c.path for c in candidates]
    assert req in paths


def test_detects_constraints_and_dev_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest\nmypy\n")
    (tmp_path / "constraints.txt").write_text("urllib3<2\n")
    candidates = detect_candidates(tmp_path)
    names = {c.path.name for c in candidates}
    assert {"requirements.txt", "requirements-dev.txt", "constraints.txt"}.issubset(names)


def test_pyproject_listed_when_present(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    candidates = detect_candidates(tmp_path)
    kinds = {c.kind for c in candidates}
    assert "pyproject" in kinds


def test_heuristic_picks_up_unconventional_filename(tmp_path: Path) -> None:
    pinned = tmp_path / "pinned-prod.txt"
    pinned.write_text("requests==2.31.0\nflask==3.0\nclick>=8\n")
    candidates = detect_candidates(tmp_path)
    paths = [c.path for c in candidates]
    assert pinned in paths


def test_heuristic_rejects_arbitrary_prose(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("This is a TODO list.\nBuy milk.\nFix the build pipeline tomorrow.\n")
    assert looks_like_requirements(notes) is False


def test_returns_empty_for_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    assert not detect_candidates(missing)
