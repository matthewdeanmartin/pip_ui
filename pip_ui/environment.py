"""Python interpreter discovery and validation."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import cast

from pip_ui.encoding import utf8_subprocess_kwargs
from pip_ui.models import InterpreterInfo


class InterpreterDiscovery:
    def discover(self) -> list[InterpreterInfo]:
        candidates: list[str] = []

        candidates.append(sys.executable)

        virtual_env = os.environ.get("VIRTUAL_ENV")
        if virtual_env:
            for rel in ("Scripts/python.exe", "bin/python"):
                candidate = str(Path(virtual_env) / rel)
                if Path(candidate).exists():
                    candidates.append(candidate)
                    break

        cwd = Path.cwd()
        for rel in (".venv/Scripts/python.exe", ".venv/bin/python"):
            candidate_path = cwd / rel
            if candidate_path.exists():
                candidates.append(str(candidate_path))

        path_names = ["python", "python3", "python3.12", "python3.13"]
        if sys.platform == "win32":
            path_names.append("py")

        for name in path_names:
            found = self.which(name)
            if found:
                candidates.append(found)

        seen: set[str] = set()
        unique: list[str] = []
        for c in candidates:
            resolved = str(Path(c).resolve()) if Path(c).exists() else c
            if resolved not in seen:
                seen.add(resolved)
                unique.append(c)

        results: list[InterpreterInfo] = []
        for path in unique:
            info = self.validate(path)
            if info is not None:
                results.append(info)

        return results

    def which(self, name: str) -> str | None:
        return shutil.which(name)

    def validate(self, path: str) -> InterpreterInfo | None:
        if not Path(path).exists():
            return None
        try:
            result = subprocess.run(
                [path, "-c", "import sys; print(sys.version.split()[0]); print(sys.prefix); print(sys.base_prefix)"],
                capture_output=True,
                **utf8_subprocess_kwargs(),
                check=False,
                shell=False,
                timeout=10,
            )  # nosec B603
            if result.returncode != 0:
                return None
            lines = result.stdout.strip().splitlines()
            if len(lines) < 3:
                return None
            version = lines[0].strip()
            prefix = lines[1].strip()
            base_prefix = lines[2].strip()
        except (OSError, subprocess.SubprocessError):
            return None

        pip_version = self.get_pip_version(path)
        is_venv = self.is_venv(prefix, base_prefix)
        env_type = self.detect_env_type(prefix, base_prefix)

        return InterpreterInfo(
            path=path,
            version=version,
            pip_version=pip_version,
            is_venv=is_venv,
            prefix=prefix,
            base_prefix=base_prefix,
            env_type=env_type,
        )

    def get_pip_version(self, path: str) -> str:
        try:
            result = cast(
                subprocess.CompletedProcess[str],
                subprocess.run(
                    [path, "-m", "pip", "--version"],
                    capture_output=True,
                    **utf8_subprocess_kwargs(),
                    check=False,
                    shell=False,
                    timeout=10,
                ),
            )  # nosec B603
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    return parts[1]
            return "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    def is_venv(self, prefix: str, base_prefix: str) -> bool:
        return prefix != base_prefix

    def detect_env_type(self, prefix: str, base_prefix: str) -> str:
        if prefix != base_prefix:
            conda_prefix = os.environ.get("CONDA_PREFIX", "")
            if conda_prefix and Path(prefix).resolve() == Path(conda_prefix).resolve():
                return "conda"
            return "venv"
        return "system"
