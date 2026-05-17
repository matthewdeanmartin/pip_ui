"""Safety classification and confirmation utilities."""

from __future__ import annotations

import re

from pip_ui.models import InterpreterInfo, SafetyLevel

COMMAND_SAFETY: dict[str, SafetyLevel] = {
    "install": SafetyLevel.MODIFIES_ENV,
    "uninstall": SafetyLevel.DESTRUCTIVE,
    "list": SafetyLevel.READ_ONLY,
    "show": SafetyLevel.READ_ONLY,
    "freeze": SafetyLevel.READ_ONLY,
    "check": SafetyLevel.READ_ONLY,
    "inspect": SafetyLevel.READ_ONLY,
    "index_versions": SafetyLevel.READ_ONLY,
    "download": SafetyLevel.MODIFIES_ENV,
    "wheel": SafetyLevel.MODIFIES_ENV,
    "lock": SafetyLevel.MODIFIES_ENV,
    "config_list": SafetyLevel.READ_ONLY,
    "config_debug": SafetyLevel.READ_ONLY,
    "config_get": SafetyLevel.READ_ONLY,
    "config_set": SafetyLevel.RISKY_CONFIG,
    "config_unset": SafetyLevel.RISKY_CONFIG,
    "config_edit": SafetyLevel.RISKY_CONFIG,
    "cache_dir": SafetyLevel.READ_ONLY,
    "cache_info": SafetyLevel.READ_ONLY,
    "cache_list": SafetyLevel.READ_ONLY,
    "cache_remove": SafetyLevel.DESTRUCTIVE,
    "cache_purge": SafetyLevel.DESTRUCTIVE,
    "debug": SafetyLevel.READ_ONLY,
    "version": SafetyLevel.READ_ONLY,
    "help": SafetyLevel.READ_ONLY,
}

CONFIRMATION_MESSAGES: dict[str, str] = {
    "uninstall": (
        "This will permanently remove the selected packages from your Python environment. "
        "Are you sure you want to continue?"
    ),
    "cache_remove": "This will permanently remove matching items from the pip cache. Continue?",
    "cache_purge": (
        "This removes ALL cached pip artifacts. They may need to be re-downloaded later. "
        "Are you sure you want to purge the cache?"
    ),
    "config_set": (
        "This will write a value into a pip configuration file. The change persists across pip runs. Continue?"
    ),
    "config_unset": "This will remove a value from a pip configuration file. Continue?",
    "config_edit": "This will open the pip config file in an external editor. Continue?",
}


def classify_command(command_name: str) -> SafetyLevel:
    return COMMAND_SAFETY.get(command_name, SafetyLevel.MODIFIES_ENV)


def check_global_install(interpreter_info: InterpreterInfo) -> str | None:
    if not interpreter_info.is_venv:
        return (
            f"Warning: You are about to install packages into a global Python environment "
            f"({interpreter_info.path}). This may affect system tools and other projects. "
            f"Consider using a virtual environment instead."
        )
    return None


CRED_RE = re.compile(r"(://)[^:@/\s]+:[^@/\s]+@")


def redact_url(url: str) -> str:
    return CRED_RE.sub(r"\1<redacted>:<redacted>@", url)


def contains_credentials(value: str) -> bool:
    return bool(CRED_RE.search(value))


def needs_confirmation(safety_level: SafetyLevel) -> bool:
    return safety_level in (SafetyLevel.DESTRUCTIVE, SafetyLevel.RISKY_CONFIG)


def confirmation_message(command_name: str) -> str:
    return CONFIRMATION_MESSAGES.get(
        command_name,
        f"This action ({command_name}) may modify your environment. Are you sure you want to continue?",
    )


def collect_argv_warnings(argv: list[str]) -> list[str]:
    """Inspect a pip argv list and return user-facing warnings."""
    warnings: list[str] = []
    joined = " ".join(argv)
    if "--break-system-packages" in argv:
        warnings.append(
            "--break-system-packages is set. This overrides Python's externally-managed marker "
            "and may damage system tooling. Strongly prefer a virtual environment."
        )
    if "--trusted-host" in argv:
        warnings.append(
            "--trusted-host is set. pip will skip TLS validation for that host. " + "Use only on networks you trust."
        )
    if "--user" in argv:
        warnings.append(
            "--user installs into the per-user site-packages. This is fine for global Python but is ignored "
            "(and may error) inside a virtual environment."
        )
    for arg in argv:
        if isinstance(arg, str) and contains_credentials(arg):
            warnings.append(
                "Detected credentials embedded in an index/proxy URL. They will be redacted in the UI "
                "and history but sent to pip as-is."
            )
            break
    if "--no-index" in argv and not any(a.startswith("--find-links") or a == "-f" for a in argv):
        warnings.append("--no-index is set but no --find-links source was provided; pip will have no source.")
    if any(arg.startswith("http://") for arg in argv):
        warnings.append("A plain http:// URL was supplied. Prefer https:// for package indexes.")
    _ = joined  # keep available if we want to add regex hints later
    return warnings


EXTERNALLY_MANAGED_HINT = (
    "pip reports this environment is 'externally managed' (PEP 668). "
    "The system Python is intentionally locked. Use a virtual environment, pipx, or your OS package manager. "
    "Do NOT enable --break-system-packages unless you accept the risk."
)


def explain_pip_error(stderr: str) -> list[str]:
    """Return human-readable hints for common pip error patterns."""
    hints: list[str] = []
    lower = stderr.lower()
    if "externally-managed-environment" in lower or "externally managed" in lower:
        hints.append(EXTERNALLY_MANAGED_HINT)
    if "no matching distribution" in lower:
        hints.append(
            "pip could not find a matching distribution. Check the package name spelling, Python version, "
            "platform, and the active --index-url."
        )
    if "permission denied" in lower or "errno 13" in lower:
        hints.append(
            "Permission denied. You may be installing into a system location. Try a virtual environment " + "or --user."
        )
    if "ssl" in lower and ("certificate" in lower or "verify failed" in lower):
        hints.append(
            "SSL certificate failure. Check your network proxy, --cert, --client-cert, or system CA bundle. "
            "Avoid --trusted-host unless you understand the risk."
        )
    if "could not find a version" in lower:
        hints.append("pip's resolver could not find a compatible version. Try relaxing pins or use --pre.")
    if "hash mismatch" in lower or "hashes are required" in lower:
        hints.append("Hash check failed. Regenerate hashes or pin the exact wheel intended.")
    if "conflict" in lower and "depend" in lower:
        hints.append("Dependency conflict detected. Inspect the resolver output above.")
    if "proxy" in lower and ("could not connect" in lower or "tunnel" in lower):
        hints.append("Proxy connection failed. Verify HTTPS_PROXY / HTTP_PROXY / --proxy settings.")
    return hints
