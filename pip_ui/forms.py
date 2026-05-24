"""Form-to-argv translation logic, independent of Tkinter."""

from __future__ import annotations

import shlex
from typing import Any

from pip_ui.command_specs import COMMAND_SPECS, SPECIAL_ARGV
from pip_ui.models import ArgSpec, CommandSpec

# Tool name prefixes stripped when building the argv subcommand token.
# e.g. "twine_upload" -> "upload", "hatch_build" -> "build"
_TOOL_PREFIXES = ("twine_", "hatch_", "flit_", "pipx_", "venv_", "audit_", "pypiserver_", "devpi_")

# Spec names whose tool takes no subcommand — flags/positionals go directly to the
# module/executable with no leading subcommand token.
# "audit"  → python -m pip_audit [flags]
# "build"  → python -m build [flags]
# "create" → python -m virtualenv <dest> [flags]
_NO_SUBCOMMAND = frozenset({"audit", "build", "create"})


def _subcommand_for(spec_name: str) -> str:
    """Return a space-joined subcommand string for a spec name.

    Strips known tool prefixes, then converts remaining underscores to spaces
    so that multi-word subcommands split into separate argv tokens.
    e.g. hatch_env_show -> "env show"  (caller splits on spaces)
         twine_upload   -> "upload"
         pipx_list      -> "list"
         audit          -> ""  (pip_audit takes no subcommand)
    """
    if spec_name in _NO_SUBCOMMAND:
        return ""
    name = spec_name
    for prefix in _TOOL_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    return name.replace("_", " ")


def build_argv_for_spec(spec: CommandSpec, values: dict[str, Any]) -> list[str]:
    """Build the tool argv portion (everything after the executable prefix) from form values."""
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
        config_argv = ["config", f"--{scope}", "set"]
        if key:
            config_argv.append(key)
            config_argv.append(value)
        return config_argv
    if spec.name == "config_unset":
        scope = str(values.get("scope") or "user").strip()
        key = str(values.get("key") or "").strip()
        config_argv = ["config", f"--{scope}", "unset"]
        if key:
            config_argv.append(key)
        return config_argv
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
        index_argv: list[str] = ["index", "versions"]
        if pkg:
            index_argv.append(pkg)
        index_argv += render_general_args(spec, values, skip={"package"})
        return index_argv
    if spec.name == "devpi_index_create":
        index_name = str(values.get("index_name") or "").strip()
        index_argv = ["index", "-c"]
        if index_name:
            index_argv.append(index_name)
        bases = values.get("bases")
        if bases is not None:
            index_argv.append(f"bases={bases}")
        if "volatile" in values:
            index_argv.append(f"volatile={'True' if values.get('volatile') else 'False'}")
        return index_argv
    if spec.name == "devpi_index_delete":
        index_name = str(values.get("index_name") or "").strip()
        index_argv = ["index", "--delete"]
        if index_name:
            index_argv.append(index_name)
        return index_argv

    # Generic path: derive subcommand token(s) from the spec name.
    # Multi-word subcommands (e.g. hatch_env_show -> "env show") become
    # separate tokens when split on spaces.
    subcmd = _subcommand_for(spec.name)
    argv = subcmd.split()
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
            if value and arg.flag:
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
            if str(value) and str(value) != (str(arg.default) if arg.default is not None else "") and arg.flag:
                out.extend([arg.flag, str(value)])
            continue
        # text / file / dir
        if arg.flag:
            out.extend([arg.flag, str(value)])
        else:
            # Positional arg: only emit if different from the default so tools
            # that treat an explicit default (e.g. "." or ".venv") as an error
            # can rely on their own built-in default instead.
            if str(value) != str(arg.default if arg.default is not None else ""):
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

    try:
        return shlex.split(raw, posix=True)
    except ValueError:
        return raw.split()


def all_commands() -> list[CommandSpec]:
    return list(COMMAND_SPECS.values())
