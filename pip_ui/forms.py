"""Form-to-argv translation logic, independent of Tkinter."""

from __future__ import annotations

from typing import Any

from pip_ui.command_specs import COMMAND_SPECS, SPECIAL_ARGV
from pip_ui.models import ArgSpec, CommandSpec


def build_argv_for_spec(spec: CommandSpec, values: dict[str, Any]) -> list[str]:
    """Build the pip argv portion (everything after `-m pip`) from form values."""
    if spec.name in SPECIAL_ARGV:
        return list(SPECIAL_ARGV[spec.name])

    # Config and cache subcommands map to two-token pip commands.
    if spec.name == "config_get":
        key = str(values.get("key") or "").strip()
        return ["config", "get", key] if key else ["config", "get"]
    if spec.name == "config_set":
        scope = str(values.get("scope") or "user").strip()
        key = str(values.get("key") or "").strip()
        value = str(values.get("value") or "")
        argv = ["config", f"--{scope}", "set"]
        if key:
            argv.append(key)
            argv.append(value)
        return argv
    if spec.name == "config_unset":
        scope = str(values.get("scope") or "user").strip()
        key = str(values.get("key") or "").strip()
        argv = ["config", f"--{scope}", "unset"]
        if key:
            argv.append(key)
        return argv
    if spec.name == "config_edit":
        scope = str(values.get("scope") or "user").strip()
        return ["config", f"--{scope}", "edit"]
    if spec.name == "cache_list":
        argv = ["cache", "list"]
        pattern = str(values.get("pattern") or "").strip()
        if pattern:
            argv.append(pattern)
        fmt = str(values.get("format") or "").strip()
        if fmt and fmt != "human":
            argv.extend(["--format", fmt])
        return argv
    if spec.name == "cache_remove":
        pattern = str(values.get("pattern") or "").strip()
        return ["cache", "remove", pattern] if pattern else ["cache", "remove"]
    if spec.name == "index_versions":
        pkg = str(values.get("package") or "").strip()
        argv: list[str] = ["index", "versions"]
        if pkg:
            argv.append(pkg)
        argv += render_general_args(spec, values, skip={"package"})
        return argv

    argv = [spec.name]
    argv += render_general_args(spec, values)
    return argv


def render_general_args(
    spec: CommandSpec,
    values: dict[str, Any],
    skip: set[str] | None = None,
) -> list[str]:
    skip = skip or set()
    out: list[str] = []
    for arg in spec.args:
        if arg.name in skip:
            continue
        value = values.get(arg.name)
        if arg.field_type == "checkbox":
            if value:
                if arg.flag:
                    out.append(arg.flag)
            continue
        if value in (None, ""):
            continue
        if arg.field_type == "multi":
            tokens = [t for t in str(value).split() if t]
            for token in tokens:
                if arg.flag:
                    out.append(arg.flag)
                out.append(token)
            continue
        if arg.field_type == "dropdown":
            if str(value) and str(value) != (str(arg.default) if arg.default is not None else ""):
                if arg.flag:
                    out.extend([arg.flag, str(value)])
            continue
        # text / file / dir
        if arg.flag:
            out.extend([arg.flag, str(value)])
        else:
            out.append(str(value))
    return out


# Global pip options that may appear on most commands (spec §9.1, §11.3).
GLOBAL_OPTIONS: list[ArgSpec] = [
    ArgSpec(
        name="g_verbose",
        flag="-v",
        field_type="checkbox",
        label="Verbose",
        help="Give more output (pip --verbose).",
        default=False,
    ),
    ArgSpec(
        name="g_quiet",
        flag="-q",
        field_type="checkbox",
        label="Quiet",
        help="Give less output (pip --quiet).",
        default=False,
    ),
    ArgSpec(
        name="g_isolated",
        flag="--isolated",
        field_type="checkbox",
        label="Isolated",
        help="Run pip in isolation from environment variables and user config.",
        default=False,
    ),
    ArgSpec(
        name="g_require_virtualenv",
        flag="--require-virtualenv",
        field_type="checkbox",
        label="Require Virtualenv",
        help="Allow pip to run only inside a virtual environment.",
        default=False,
    ),
    ArgSpec(
        name="g_no_input",
        flag="--no-input",
        field_type="checkbox",
        label="No Input",
        help="Disable prompting for input.",
        default=False,
    ),
    ArgSpec(
        name="g_disable_version_check",
        flag="--disable-pip-version-check",
        field_type="checkbox",
        label="Disable Pip Version Check",
        help="Don't check the PyPI for a new version of pip.",
        default=False,
    ),
    ArgSpec(
        name="g_no_color",
        flag="--no-color",
        field_type="checkbox",
        label="No Color",
        help="Disable colored output.",
        default=False,
    ),
    ArgSpec(
        name="g_proxy",
        flag="--proxy",
        field_type="text",
        label="Proxy",
        help="Specify a proxy in the form scheme://[user:password@]proxy.server:port.",
        default=None,
    ),
    ArgSpec(
        name="g_retries",
        flag="--retries",
        field_type="text",
        label="Retries",
        help="Maximum number of retries each connection should attempt.",
        default=None,
    ),
    ArgSpec(
        name="g_timeout",
        flag="--timeout",
        field_type="text",
        label="Timeout (seconds)",
        help="Socket timeout (seconds).",
        default=None,
    ),
    ArgSpec(
        name="g_cert",
        flag="--cert",
        field_type="file",
        label="Cert File",
        help="Path to PEM-encoded CA certificate bundle.",
        default=None,
    ),
    ArgSpec(
        name="g_client_cert",
        flag="--client-cert",
        field_type="file",
        label="Client Cert",
        help="Path to SSL client certificate (PEM, may contain key).",
        default=None,
    ),
    ArgSpec(
        name="g_cache_dir",
        flag="--cache-dir",
        field_type="dir",
        label="Cache Dir",
        help="Override the cache directory.",
        default=None,
    ),
    ArgSpec(
        name="g_log",
        flag="--log",
        field_type="file",
        label="Log File",
        help="Path to a verbose log file.",
        default=None,
    ),
]


def render_global_args(values: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for arg in GLOBAL_OPTIONS:
        v = values.get(arg.name)
        if arg.field_type == "checkbox":
            if v:
                out.append(arg.flag)
            continue
        if v in (None, ""):
            continue
        out.extend([arg.flag, str(v)])
    return out


def parse_raw_extra(raw: str) -> list[str]:
    """Tokenize a free-form extra-args string. Supports double-quoted segments."""
    if not raw:
        return []
    import shlex

    try:
        return shlex.split(raw, posix=True)
    except ValueError:
        return raw.split()


def all_commands() -> list[CommandSpec]:
    return list(COMMAND_SPECS.values())
