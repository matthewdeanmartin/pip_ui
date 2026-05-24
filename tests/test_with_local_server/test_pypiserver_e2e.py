"""End-to-end localhost-only tests for the pypiserver workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from pip_ui.__about__ import __version__

from .helpers import (
    PROJECT_ROOT,
    REPO_PYTHON,
    LocalPypiServer,
    default_values,
    require_executables,
    require_modules,
    run_gui_command,
    run_subprocess,
    venv_python_path,
)

PACKAGE_NAME = "pip-ui-tkinter"
pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.timeout(300)]


def test_pypiserver_round_trip_build_upload_install(pypiserver_instance: LocalPypiServer, tmp_path: Path) -> None:
    """Build the project, upload to local pypiserver, then install it into a fresh venv."""
    require_modules("build", "virtualenv")
    require_executables("twine")

    dist_dir = tmp_path / "dist"
    verify_dir = tmp_path / "verify"
    verify_dir.mkdir()
    install_venv = tmp_path / "install-venv"

    build_values = default_values("build", "build")
    build_values["srcdir"] = str(PROJECT_ROOT)
    build_values["outdir"] = str(dist_dir)
    build_values["no_isolation"] = True
    build_values["skip_dependency_check"] = True
    build_result = run_gui_command(
        "build",
        "build",
        build_values,
        cwd=PROJECT_ROOT,
        python_path=REPO_PYTHON,
        timeout=180,
    )
    assert build_result.exit_code == 0, build_result.stderr or build_result.stdout
    assert any(dist_dir.glob("*.whl"))
    assert any(dist_dir.glob("*.tar.gz"))

    upload_values = default_values("twine", "twine_upload")
    upload_values["dists"] = str(dist_dir / "*")
    upload_values["repository_url"] = f"{pypiserver_instance.url}/"
    upload_values["username"] = "local"
    upload_values["password"] = "local"
    upload_values["disable_progress_bar"] = True
    upload_result = run_gui_command("twine", "twine_upload", upload_values, cwd=PROJECT_ROOT, timeout=180)
    assert upload_result.exit_code == 0, upload_result.stderr or upload_result.stdout
    assert any(pypiserver_instance.packages_dir.iterdir())

    create_values = default_values("virtualenv", "create")
    create_values["dest"] = str(install_venv)
    create_result = run_gui_command(
        "virtualenv",
        "create",
        create_values,
        cwd=tmp_path,
        python_path=REPO_PYTHON,
        timeout=180,
    )
    assert create_result.exit_code == 0, create_result.stderr or create_result.stdout

    install_values = default_values("pip", "install")
    install_values["packages"] = f"{PACKAGE_NAME}=={__version__}"
    install_values["index_url"] = pypiserver_instance.simple_url
    install_values["trusted_host"] = "localhost"
    install_values["no_cache_dir"] = True
    install_result = run_gui_command(
        "pip",
        "install",
        install_values,
        cwd=verify_dir,
        python_path=venv_python_path(install_venv),
        global_values={"g_disable_version_check": True, "g_no_input": True},
        timeout=180,
    )
    assert install_result.exit_code == 0, install_result.stderr or install_result.stdout

    verify_result = run_subprocess(
        [
            str(venv_python_path(install_venv)),
            "-c",
            (
                "import importlib.metadata as m; import pathlib, pip_ui; "
                "print(m.version('pip-ui-tkinter')); "
                "print(pathlib.Path(pip_ui.__file__).resolve())"
            ),
        ],
        cwd=verify_dir,
        timeout=60,
    )
    assert verify_result.returncode == 0, verify_result.stderr or verify_result.stdout
    version, module_path = verify_result.stdout.strip().splitlines()
    assert version == __version__
    assert "site-packages" in module_path.lower()
