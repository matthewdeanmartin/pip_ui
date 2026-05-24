"""End-to-end localhost-only tests for the devpi workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from pip_ui.__about__ import __version__

from .helpers import (
    PROJECT_ROOT,
    REPO_PYTHON,
    LocalDevpiServer,
    default_values,
    require_executables,
    require_modules,
    run_gui_command,
    run_subprocess,
    venv_python_path,
)

PACKAGE_NAME = "pip-ui-tkinter"
pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.timeout(300)]


def test_devpi_round_trip_build_upload_install(devpi_server_instance: LocalDevpiServer, tmp_path: Path) -> None:
    """Build the project, upload artifacts to devpi, then install them from the local simple index."""
    require_modules("build", "virtualenv")
    require_executables("devpi")

    client_dir = tmp_path / "client"
    client_dir.mkdir()
    dist_dir = tmp_path / "dist"
    verify_dir = tmp_path / "verify"
    verify_dir.mkdir()
    install_venv = tmp_path / "install-venv"
    client_extra = f'--clientdir "{client_dir}"'

    use_values = default_values("devpi", "devpi_use")
    use_values["url"] = devpi_server_instance.url
    use_result = run_gui_command("devpi", "devpi_use", use_values, cwd=tmp_path, raw_extra=client_extra, timeout=60)
    assert use_result.exit_code == 0, use_result.stderr or use_result.stdout

    login_values = default_values("devpi", "devpi_login")
    login_values["username"] = "root"
    login_values["password"] = "localdevpi"
    login_result = run_gui_command(
        "devpi",
        "devpi_login",
        login_values,
        cwd=tmp_path,
        raw_extra=client_extra,
        timeout=60,
    )
    assert login_result.exit_code == 0, login_result.stderr or login_result.stdout

    create_index_values = default_values("devpi", "devpi_index_create")
    create_index_values["index_name"] = "testindex"
    create_index_values["bases"] = ""
    create_index_values["volatile"] = True
    create_index_result = run_gui_command(
        "devpi",
        "devpi_index_create",
        create_index_values,
        cwd=tmp_path,
        raw_extra=client_extra,
        timeout=60,
    )
    assert create_index_result.exit_code == 0, create_index_result.stderr or create_index_result.stdout

    list_indexes_result = run_gui_command(
        "devpi",
        "devpi_index_list",
        default_values("devpi", "devpi_index_list"),
        cwd=tmp_path,
        raw_extra=client_extra,
        timeout=60,
    )
    assert list_indexes_result.exit_code == 0, list_indexes_result.stderr or list_indexes_result.stdout
    assert "root/testindex" in list_indexes_result.stdout

    use_index_values = default_values("devpi", "devpi_use")
    use_index_values["url"] = f"{devpi_server_instance.url}/root/testindex"
    use_index_result = run_gui_command("devpi", "devpi_use", use_index_values, cwd=tmp_path, raw_extra=client_extra)
    assert use_index_result.exit_code == 0, use_index_result.stderr or use_index_result.stdout

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

    create_venv_values = default_values("virtualenv", "create")
    create_venv_values["dest"] = str(install_venv)
    create_venv_result = run_gui_command(
        "virtualenv",
        "create",
        create_venv_values,
        cwd=tmp_path,
        python_path=REPO_PYTHON,
        timeout=180,
    )
    assert create_venv_result.exit_code == 0, create_venv_result.stderr or create_venv_result.stdout

    upload_result = run_gui_command(
        "devpi",
        "devpi_upload",
        default_values("devpi", "devpi_upload"),
        cwd=tmp_path,
        raw_extra=f'{client_extra} --from-dir "{dist_dir}"',
        timeout=180,
    )
    assert upload_result.exit_code == 0, upload_result.stderr or upload_result.stdout

    install_values = default_values("pip", "install")
    install_values["packages"] = f"{PACKAGE_NAME}=={__version__}"
    install_values["index_url"] = f"{devpi_server_instance.url}/root/testindex/+simple/"
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
