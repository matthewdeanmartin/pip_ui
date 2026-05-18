"""End-to-end integration tests for command argv construction and execution.

Each test:
  1. Builds the full argv the way the UI does (build_argv_for_spec + build_argv).
  2. Runs the subprocess and waits for it to finish.
  3. Asserts the process exits without an unexpected crash (exit code != -1).
     A non-zero exit code from the tool itself (e.g. twine check failing) is
     acceptable — what we're verifying is that the command was assembled and
     launched correctly.
"""

from __future__ import annotations

import queue
import sys
import tempfile
from pathlib import Path

import pytest

from pip_ui.forms import build_argv_for_spec
from pip_ui.runner import PipRunner
from pip_ui.tools import get_plugin

PYTHON = sys.executable

# Directory containing this project's own pyproject.toml — used as the
# source tree for build/twine/hatch/flit commands so they have a real project
# to work with.
PROJECT_DIR = str(Path(__file__).parent.parent.resolve())

# A temp dir used as the virtualenv destination and build output dir.
TMPDIR = tempfile.gettempdir()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_sync(argv: list[str], cwd: str = PROJECT_DIR, timeout: int = 120) -> tuple[int, str, str]:
    """Run *argv* synchronously and return (exit_code, stdout, stderr)."""
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    done: queue.Queue[int] = queue.Queue()

    runner = PipRunner()
    runner.run(
        argv,
        cwd=cwd,
        on_stdout=stdout_lines.append,
        on_stderr=stderr_lines.append,
        on_done=done.put,
    )

    try:
        exit_code = done.get(timeout=timeout)
    except queue.Empty:
        runner.cancel(force=True)
        pytest.fail(f"Command timed out after {timeout}s: {argv}")

    return exit_code, "".join(stdout_lines), "".join(stderr_lines)


def build_full_argv(plugin_name: str, spec_name: str, values: dict) -> list[str]:
    """Build the complete argv the way MainWindow does."""
    plugin = get_plugin(plugin_name)
    assert plugin is not None, f"Plugin '{plugin_name}' not found"
    spec = plugin.command_specs[spec_name]
    tool_args = build_argv_for_spec(spec, values)
    runner = PipRunner()
    return runner.build_argv(PYTHON, tool_args, plugin)


def default_values(plugin_name: str, spec_name: str) -> dict:
    """Return a dict of field defaults for the named spec."""
    plugin = get_plugin(plugin_name)
    assert plugin is not None
    spec = plugin.command_specs[spec_name]
    out: dict = {}
    for arg in spec.args:
        if arg.field_type == "checkbox":
            out[arg.name] = bool(arg.default)
        else:
            out[arg.name] = arg.default
    return out


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_build_wheel_argv_structure():
    """build: verify the argv is built correctly before running."""
    values = default_values("build", "build")
    values["srcdir"] = PROJECT_DIR
    values["wheel"] = True
    argv = build_full_argv("build", "build", values)
    # python -m build <srcdir> --wheel
    assert "-m" in argv
    assert "build" in argv
    assert "--wheel" in argv
    assert PROJECT_DIR in argv


@pytest.mark.integration
@pytest.mark.slow
def test_build_sdist_runs(tmp_path):
    """build: actually run 'python -m build --sdist' against this project."""
    values = default_values("build", "build")
    values["srcdir"] = PROJECT_DIR
    values["sdist"] = True
    values["outdir"] = str(tmp_path)
    argv = build_full_argv("build", "build", values)
    exit_code, stdout, stderr = run_sync(argv, cwd=PROJECT_DIR, timeout=120)
    # build exits 0 on success; any non-(-1) code means the command ran
    assert exit_code != -1, f"build subprocess failed to start.\nstderr: {stderr}"
    assert exit_code == 0, f"build --sdist failed (exit {exit_code}).\nstdout: {stdout}\nstderr: {stderr}"


# ---------------------------------------------------------------------------
# virtualenv
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_virtualenv_version_argv_structure():
    """venv_version now emits '--version' via SPECIAL_ARGV."""
    values = default_values("virtualenv", "venv_version")
    argv = build_full_argv("virtualenv", "venv_version", values)
    assert "-m" in argv
    assert "virtualenv" in argv
    assert "--version" in argv


@pytest.mark.integration
def test_virtualenv_version_runs():
    """virtualenv --version should exit 0 and print a version string."""
    values = default_values("virtualenv", "venv_version")
    argv = build_full_argv("virtualenv", "venv_version", values)
    exit_code, stdout, stderr = run_sync(argv)
    assert exit_code == 0, f"virtualenv --version failed.\nstdout: {stdout}\nstderr: {stderr}"
    combined = stdout + stderr
    assert any(ch.isdigit() for ch in combined), "Expected a version number in output"


@pytest.mark.integration
@pytest.mark.slow
def test_virtualenv_create_runs(tmp_path):
    """virtualenv: create a real venv in a temp directory."""
    dest = str(tmp_path / "testvenv")
    values = default_values("virtualenv", "create")
    values["dest"] = dest
    values["without_pip"] = True  # faster: skip seeding pip
    argv = build_full_argv("virtualenv", "create", values)
    exit_code, stdout, stderr = run_sync(argv, timeout=60)
    assert exit_code != -1, f"virtualenv subprocess failed to start.\nstderr: {stderr}"
    assert exit_code == 0, f"virtualenv create failed (exit {exit_code}).\nstdout: {stdout}\nstderr: {stderr}"


# ---------------------------------------------------------------------------
# twine check
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_twine_check_argv_structure():
    """twine check: verify argv is constructed correctly."""
    values = default_values("twine", "twine_check")
    values["dists"] = "dist/*"
    argv = build_full_argv("twine", "twine_check", values)
    # twine check dist/*
    assert argv[-1].endswith("twine") or "twine" in argv[0]
    assert "check" in argv
    assert "dist/*" in argv


@pytest.mark.integration
@pytest.mark.slow
def test_twine_check_runs_on_built_dist(tmp_path):
    """twine check: build a sdist, then run twine check on it."""
    # Step 1: build a sdist so there's something to check.
    build_plugin = get_plugin("build")
    assert build_plugin is not None
    build_spec = build_plugin.command_specs["build"]
    build_values = default_values("build", "build")
    build_values["srcdir"] = PROJECT_DIR
    build_values["sdist"] = True
    build_values["outdir"] = str(tmp_path)
    build_argv = PipRunner().build_argv(PYTHON, build_argv_for_spec(build_spec, build_values), build_plugin)
    build_code, _, build_err = run_sync(build_argv, cwd=PROJECT_DIR, timeout=120)
    if build_code != 0:
        pytest.skip(f"Skipping twine check: build step failed ({build_err})")

    # Step 2: twine check the dist we just built.
    dist_pattern = str(tmp_path / "*.tar.gz")
    values = default_values("twine", "twine_check")
    values["dists"] = dist_pattern
    argv = build_full_argv("twine", "twine_check", values)
    exit_code, stdout, stderr = run_sync(argv, timeout=60)
    assert exit_code != -1, f"twine check subprocess failed to start.\nstderr: {stderr}"
    assert exit_code == 0, f"twine check failed (exit {exit_code}).\nstdout: {stdout}\nstderr: {stderr}"


# ---------------------------------------------------------------------------
# twine version
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_twine_version_argv_structure():
    """twine_version now emits '--version' via SPECIAL_ARGV (not 'version' subcommand)."""
    values = default_values("twine", "twine_version")
    argv = build_full_argv("twine", "twine_version", values)
    assert "twine" in argv[0]
    assert "--version" in argv


@pytest.mark.integration
def test_twine_version_runs():
    """twine --version should exit 0 and print a version string."""
    values = default_values("twine", "twine_version")
    argv = build_full_argv("twine", "twine_version", values)
    exit_code, stdout, stderr = run_sync(argv)
    assert exit_code == 0, f"twine --version failed.\nstdout: {stdout}\nstderr: {stderr}"
    combined = stdout + stderr
    assert any(ch.isdigit() for ch in combined), "Expected version digits in output"


# ---------------------------------------------------------------------------
# pip-audit
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_pip_audit_version_argv_structure():
    """pip-audit audit_version now emits '--version' via SPECIAL_ARGV."""
    values = default_values("pip-audit", "audit_version")
    argv = build_full_argv("pip-audit", "audit_version", values)
    assert "-m" in argv
    assert "pip_audit" in argv
    assert "--version" in argv


@pytest.mark.integration
def test_pip_audit_version_runs():
    """pip-audit --version should exit 0 and print a version string."""
    values = default_values("pip-audit", "audit_version")
    argv = build_full_argv("pip-audit", "audit_version", values)
    exit_code, stdout, stderr = run_sync(argv)
    assert exit_code == 0, f"pip-audit --version failed.\nstdout: {stdout}\nstderr: {stderr}"
    combined = stdout + stderr
    assert any(ch.isdigit() for ch in combined), "Expected a version number in output"


@pytest.mark.integration
def test_pip_audit_argv_structure():
    """pip-audit audit: verify argv is built correctly."""
    values = default_values("pip-audit", "audit")
    values["skip_editable"] = True
    argv = build_full_argv("pip-audit", "audit", values)
    assert "-m" in argv
    assert "pip_audit" in argv
    assert "--skip-editable" in argv


# ---------------------------------------------------------------------------
# hatch
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_hatch_version_show_argv_structure():
    """hatch version show: verify argv tokens."""
    values = default_values("hatch", "hatch_version_show")
    argv = build_full_argv("hatch", "hatch_version_show", values)
    # hatch version show -> ["hatch", "version", "show"]
    assert "hatch" in argv[0]
    assert "version" in argv
    assert "show" in argv


@pytest.mark.integration
def test_hatch_version_show_runs():
    """hatch version show: subprocess should start (exit_code != -1).

    This project uses static versioning so hatch may exit non-zero — that's
    acceptable here.  We just verify the command was assembled and launched.
    """
    values = default_values("hatch", "hatch_version_show")
    argv = build_full_argv("hatch", "hatch_version_show", values)
    exit_code, _stdout, stderr = run_sync(argv, cwd=PROJECT_DIR)
    assert exit_code != -1, f"hatch version show subprocess failed to start.\nstderr: {stderr}"


@pytest.mark.integration
def test_hatch_build_argv_structure():
    """hatch build: verify the --target flag is included."""
    values = default_values("hatch", "hatch_build")
    values["target"] = "sdist"
    argv = build_full_argv("hatch", "hatch_build", values)
    assert "hatch" in argv[0]
    assert "build" in argv
    assert "--target" in argv
    assert "sdist" in argv


@pytest.mark.integration
def test_hatch_env_show_argv_structure():
    """hatch env show: verify multi-token subcommand."""
    values = default_values("hatch", "hatch_env_show")
    argv = build_full_argv("hatch", "hatch_env_show", values)
    assert "hatch" in argv[0]
    assert "env" in argv
    assert "show" in argv


@pytest.mark.integration
def test_hatch_env_show_runs():
    """hatch env show should exit 0 inside this project directory."""
    values = default_values("hatch", "hatch_env_show")
    argv = build_full_argv("hatch", "hatch_env_show", values)
    exit_code, stdout, stderr = run_sync(argv, cwd=PROJECT_DIR)
    assert exit_code == 0, f"hatch env show failed.\nstdout: {stdout}\nstderr: {stderr}"


# ---------------------------------------------------------------------------
# flit
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_flit_build_argv_structure():
    """flit build: verify argv tokens."""
    values = default_values("flit", "flit_build")
    argv = build_full_argv("flit", "flit_build", values)
    # flit build  (default format=wheel, not emitted because it's the default)
    assert "flit" in argv[0]
    assert "build" in argv


@pytest.mark.integration
def test_flit_build_sdist_argv_structure():
    """flit build --format sdist: verify the flag is emitted for non-default."""
    values = default_values("flit", "flit_build")
    values["format"] = "sdist"
    argv = build_full_argv("flit", "flit_build", values)
    assert "flit" in argv[0]
    assert "build" in argv
    assert "--format" in argv
    assert "sdist" in argv


# ---------------------------------------------------------------------------
# pipx — install & uninstall python3-alias
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_pipx_install_argv_structure():
    """pipx install: verify argv tokens."""
    values = default_values("pipx", "pipx_install")
    values["package"] = "python3-alias"
    argv = build_full_argv("pipx", "pipx_install", values)
    assert "pipx" in argv[0]
    assert "install" in argv
    assert "python3-alias" in argv


@pytest.mark.integration
def test_pipx_uninstall_argv_structure():
    """pipx uninstall: verify argv tokens."""
    values = default_values("pipx", "pipx_uninstall")
    values["package"] = "python3-alias"
    argv = build_full_argv("pipx", "pipx_uninstall", values)
    assert "pipx" in argv[0]
    assert "uninstall" in argv
    assert "python3-alias" in argv


@pytest.mark.integration
@pytest.mark.slow
def test_pipx_install_and_uninstall_python3_alias():
    """pipx: install then uninstall python3-alias (real network call)."""
    # Install
    install_values = default_values("pipx", "pipx_install")
    install_values["package"] = "python3-alias"
    install_argv = build_full_argv("pipx", "pipx_install", install_values)
    install_code, install_out, install_err = run_sync(install_argv, timeout=120)
    assert install_code != -1, f"pipx install subprocess failed to start.\nstderr: {install_err}"
    # pipx exits 0 on clean install or if the package is already installed
    assert install_code == 0, (
        f"pipx install python3-alias failed (exit {install_code}).\n" f"stdout: {install_out}\nstderr: {install_err}"
    )

    # Uninstall
    uninstall_values = default_values("pipx", "pipx_uninstall")
    uninstall_values["package"] = "python3-alias"
    uninstall_argv = build_full_argv("pipx", "pipx_uninstall", uninstall_values)
    uninstall_code, uninstall_out, uninstall_err = run_sync(uninstall_argv, timeout=60)
    assert uninstall_code != -1, f"pipx uninstall subprocess failed to start.\nstderr: {uninstall_err}"
    assert uninstall_code == 0, (
        f"pipx uninstall python3-alias failed (exit {uninstall_code}).\n"
        f"stdout: {uninstall_out}\nstderr: {uninstall_err}"
    )


# ---------------------------------------------------------------------------
# Sanity checks: spec names -> correct subcommand tokens
# ---------------------------------------------------------------------------


def test_build_argv_for_spec_twine_check():
    """twine_check spec builds ['check', 'dist/*']."""
    plugin = get_plugin("twine")
    assert plugin is not None
    spec = plugin.command_specs["twine_check"]
    argv = build_argv_for_spec(spec, {"dists": "dist/*", "strict": False})
    assert argv[0] == "check"
    assert "dist/*" in argv


def test_build_argv_for_spec_twine_version():
    """twine_version spec builds ['--version'] via SPECIAL_ARGV."""
    plugin = get_plugin("twine")
    assert plugin is not None
    spec = plugin.command_specs["twine_version"]
    argv = build_argv_for_spec(spec, {})
    assert argv == ["--version"]


def test_build_argv_for_spec_hatch_env_show():
    """hatch_env_show spec builds ['env', 'show']."""
    plugin = get_plugin("hatch")
    assert plugin is not None
    spec = plugin.command_specs["hatch_env_show"]
    argv = build_argv_for_spec(spec, {"json": False})
    assert argv[:2] == ["env", "show"]


def test_build_argv_for_spec_hatch_build():
    """hatch_build with target=sdist builds ['build', '--target', 'sdist']."""
    plugin = get_plugin("hatch")
    assert plugin is not None
    spec = plugin.command_specs["hatch_build"]
    argv = build_argv_for_spec(spec, {"target": "sdist", "clean": False, "clean_hooks_after": False})
    assert argv[0] == "build"
    assert "--target" in argv
    assert "sdist" in argv


def test_build_argv_for_spec_hatch_version_show():
    """hatch_version_show spec builds ['version', 'show']."""
    plugin = get_plugin("hatch")
    assert plugin is not None
    spec = plugin.command_specs["hatch_version_show"]
    argv = build_argv_for_spec(spec, {})
    assert argv == ["version", "show"]


def test_build_argv_for_spec_flit_build_default():
    """flit_build with default wheel format emits no --format flag."""
    plugin = get_plugin("flit")
    assert plugin is not None
    spec = plugin.command_specs["flit_build"]
    argv = build_argv_for_spec(spec, {"format": "wheel"})
    assert argv[0] == "build"
    assert "--format" not in argv


def test_build_argv_for_spec_flit_build_sdist():
    """flit_build with sdist format emits --format sdist."""
    plugin = get_plugin("flit")
    assert plugin is not None
    spec = plugin.command_specs["flit_build"]
    argv = build_argv_for_spec(spec, {"format": "sdist"})
    assert argv[0] == "build"
    assert "--format" in argv
    assert "sdist" in argv


def test_build_argv_for_spec_pipx_install():
    """pipx_install spec builds ['install', 'python3-alias']."""
    plugin = get_plugin("pipx")
    assert plugin is not None
    spec = plugin.command_specs["pipx_install"]
    argv = build_argv_for_spec(spec, {"package": "python3-alias", "force": False, "include_deps": False})
    assert argv[0] == "install"
    assert "python3-alias" in argv


def test_build_argv_for_spec_pipx_uninstall():
    """pipx_uninstall spec builds ['uninstall', 'python3-alias']."""
    plugin = get_plugin("pipx")
    assert plugin is not None
    spec = plugin.command_specs["pipx_uninstall"]
    argv = build_argv_for_spec(spec, {"package": "python3-alias"})
    assert argv[0] == "uninstall"
    assert "python3-alias" in argv


def test_build_argv_for_spec_audit_version():
    """audit_version spec builds ['--version'] via SPECIAL_ARGV."""
    plugin = get_plugin("pip-audit")
    assert plugin is not None
    spec = plugin.command_specs["audit_version"]
    argv = build_argv_for_spec(spec, {})
    assert argv == ["--version"]


def test_build_argv_for_spec_venv_version():
    """venv_version spec builds ['--version'] via SPECIAL_ARGV."""
    plugin = get_plugin("virtualenv")
    assert plugin is not None
    spec = plugin.command_specs["venv_version"]
    argv = build_argv_for_spec(spec, {})
    assert argv == ["--version"]
