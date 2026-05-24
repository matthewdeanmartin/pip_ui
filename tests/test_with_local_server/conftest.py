"""Pytest fixtures for localhost-only local-server integration tests."""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest

from pip_ui.encoding import utf8_subprocess_kwargs

from .helpers import (
    PROJECT_ROOT,
    LocalDevpiServer,
    LocalPypiServer,
    build_gui_argv,
    default_values,
    find_free_port,
    require_executables,
    resolve_interpreter_local_executable,
    run_subprocess,
    terminate_process,
    wait_for_url,
)


@pytest.fixture()
def pypiserver_instance(tmp_path: Path) -> Generator[LocalPypiServer, None, None]:
    """Start a disposable pypiserver instance that never falls back to pypi.org."""
    require_executables("pypi-server")

    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()
    log_path = tmp_path / "pypiserver.log"
    port = find_free_port()

    values = default_values("pypiserver", "pypiserver_run")
    values["port"] = str(port)
    values["host"] = "localhost"
    values["packages_dir"] = str(packages_dir)
    values["disable_fallback"] = True
    values["password_file"] = "."
    argv = build_gui_argv("pypiserver", "pypiserver_run", values, raw_extra="-a .")

    with log_path.open("w", encoding="utf-8") as log_file:
        try:
            with subprocess.Popen(  # nosec B603
                argv,
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                shell=False,
                **utf8_subprocess_kwargs(strip_venv=True),
            ) as process:
                try:
                    wait_for_url(f"http://localhost:{port}/simple/", timeout=30.0)
                    yield LocalPypiServer(
                        url=f"http://localhost:{port}",
                        simple_url=f"http://localhost:{port}/simple/",
                        port=port,
                        packages_dir=packages_dir,
                        argv=tuple(argv),
                        log_path=log_path,
                    )
                finally:
                    terminate_process(process)
        except OSError as exc:
            pytest.skip(f"Unable to start pypiserver: {exc}")


@pytest.fixture()
def devpi_server_instance(tmp_path: Path) -> Generator[LocalDevpiServer, None, None]:
    """Start a disposable offline devpi-server instance."""
    require_executables("devpi-init", "devpi-server")

    server_dir = tmp_path / "server"
    server_dir.mkdir()
    log_path = tmp_path / "devpi-server.log"
    port = find_free_port()

    devpi_init_exe = resolve_interpreter_local_executable("devpi-init")
    devpi_server_exe = resolve_interpreter_local_executable("devpi-server")
    assert devpi_init_exe is not None
    assert devpi_server_exe is not None

    init_result = run_subprocess(
        [str(devpi_init_exe), "--serverdir", str(server_dir), "--root-passwd", "localdevpi", "--no-root-pypi"],
        cwd=PROJECT_ROOT,
        timeout=60,
        strip_venv=True,
    )
    assert init_result.returncode == 0, init_result.stderr or init_result.stdout

    start_argv = [
        str(devpi_server_exe),
        "--offline-mode",
        "--host",
        "localhost",
        "--port",
        str(port),
        "--serverdir",
        str(server_dir),
    ]
    with log_path.open("w", encoding="utf-8") as log_file:
        try:
            with subprocess.Popen(  # nosec B603
                start_argv,
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                shell=False,
                **utf8_subprocess_kwargs(strip_venv=True),
            ) as process:
                try:
                    wait_for_url(f"http://localhost:{port}/+api", timeout=45.0)
                    yield LocalDevpiServer(
                        url=f"http://localhost:{port}",
                        port=port,
                        server_dir=server_dir,
                        argv=tuple(start_argv),
                        log_path=log_path,
                    )
                finally:
                    terminate_process(process)
        except OSError as exc:
            pytest.skip(f"Unable to start devpi-server: {exc}")
