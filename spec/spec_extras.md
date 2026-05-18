# Spec: pip-ui Extras — PyPA Tool Support

**Status:** Revised — open questions resolved\
**Scope:** Optional install extras for wheel, build, virtualenv, twine, pip-audit, hatch, flit, pipx\
**Out of scope:** Tools requiring native code compilation; tools where PyPA/PSF is not the primary maintainer

______________________________________________________________________

## Background

pip-ui currently wraps `python -m pip` exclusively. The architecture is well-suited for expansion: `command_specs.py`
defines commands as data, `main_window.py` builds the left-side tree and middle panels from those specs, and `runner.py`
shells out to a subprocess. The only pip-specific coupling is the runner's `python -m pip` prefix and the global-options
model which maps to pip's `--verbose`, `--proxy`, etc.

Each new tool has its own command model. Some (build, wheel, twine) are pure CLI wrappers with a similar
flag-and-positional structure to pip. Others (virtualenv, hatch, flit, pipx) have richer state (environments, projects,
apps) that benefits from custom middle-panel widgets beyond the generic `CommandForm`. The goal is to keep pip-ui as the
single entry point while making each tool's UX feel appropriate.

______________________________________________________________________

## Packaging: Extras

Each tool is an optional install extra. Users install only what they need:

```
pip install pip-ui-tkinter[build]
pip install pip-ui-tkinter[all-tools]
```

Extras defined in `pyproject.toml`:

| Extra | Dependencies added |
|--------------|--------------------|
| `build` | `build>=1.0` |
| `virtualenv` | `virtualenv>=20.0` |
| `twine` | `twine>=5.0` |
| `pip-audit` | `pip-audit>=2.7` |
| `hatch` | `hatch>=1.9` |
| `flit` | `flit>=3.9` |
| `pipx` | `pipx>=1.4` |
| `all` | all of the above |

The base `pip-ui-tkinter` package remains zero-dependency. Each extra is detected at runtime with
`importlib.util.find_spec()` or a `shutil.which()` call. If the tool is not installed, its tree section is either hidden
or shows a one-line "install with: pip install pip-ui-tkinter[X]" placeholder node.

______________________________________________________________________

## Architecture Changes

### Tool registry

Introduce a `ToolPlugin` dataclass parallel to the existing `CommandSpec` structure:

```python
@dataclass
class ToolPlugin:
    name: str  # "build", "twine", etc.
    label: str  # display name in the top-level switcher
    extra: str  # pyproject extra name
    executable: str  # what to shutil.which() / importlib.find_spec()
    run_prefix: list[str]  # e.g. ["python", "-m", "build"] or ["twine"]
    command_specs: dict[str, CommandSpec]
    command_groups: list[str]
    panel_class: type | None  # None = use generic CommandForm
    help_url: str
```

A `TOOL_REGISTRY: list[ToolPlugin]` in a new `pip_ui/tools/__init__.py` replaces the hard-coded `COMMAND_SPECS` import
in `main_window.py`.

### Tool switcher

The toolbar gains a **tool tab row** rendered as a `ttk.Notebook` (or a row of `ttk.Button` toggles if styling proves awkward) spanning the full width above the interpreter picker. Tabs: **pip** (always present) plus any detected tools. Tools that are not installed are shown as greyed-out tabs with a tooltip: "Install with: pip install pip-ui-tkinter[X]". Clicking a greyed tab shows an info dialog with the install command.

Tabs are ordered: pip · build · virtualenv · twine · pip-audit · hatch · flit · pipx.

Detection runs at startup and again whenever the interpreter changes. See **Detection Logic** below — global-path tools (twine, hatch, flit, pipx) are shown if found anywhere on `$PATH`, not just inside the selected interpreter.

Switching tabs:

1. Replaces `command_tree` contents with the selected tool's groups and commands.
1. Swaps `command_form` (middle-top panel) for the tool's `panel_class`, or falls back to `CommandForm`.
1. Updates the help panel's documentation URL base.
1. For tools where the interpreter picker is irrelevant (pipx), hides the interpreter row and shows the tool-specific controls instead (see pipx section).
1. For project-scoped tools (hatch, flit), renames the "Dir:" label to "Project Dir:".
1. Persists the last-used tool in `AppSettings`.

The title bar updates to `pip-ui v{version} — {tool label}`.

### Runner generalisation

`PipRunner` currently hard-codes `[interpreter_path, "-m", "pip"]` as the argv prefix. Extract this to a
`build_prefix(interpreter, tool_plugin)` method. For `pip`, prefix is unchanged. For `python -m build`, it's
`[interpreter_path, "-m", "build"]`. For `twine`, it's `[twine_executable]` resolved via `shutil.which()` inside the
active interpreter's Scripts/bin directory.

### Safety model

Reuse `SafetyLevel` unchanged. Each tool's `CommandSpec` carries its own safety level. The confirmation dialog text is
generalised to reference the tool name rather than hard-coding "pip".

### Global options

Global options (verbose, proxy, cert, timeout) are pip-specific. Each tool plugin declares
`global_options_class: type | None`. `None` means no global options dialog is shown for that tool. Tools that have
relevant global-style flags (e.g. twine's `--repository`) get their own `GlobalOptionsDialog` subclass.

______________________________________________________________________

## Per-Tool Specs

### `build` (`python -m build`)

**Groups:** Build

| Command | Label | Safety | Key Args |
|---------------|-------------|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `build` | Build | `MODIFIES_ENV` | source dir (positional, dir picker); `--wheel` checkbox; `--sdist` checkbox; `--outdir` dir picker; `--no-isolation` checkbox; `--skip-dependency-check` checkbox; `--installer` dropdown (pip/uv) |
| `build_wheel` | Build Wheel | `MODIFIES_ENV` | source dir; `--outdir`; `--no-isolation` |
| `build_sdist` | Build sdist | `MODIFIES_ENV` | source dir; `--outdir` |

Auto-run on select: none (requires a source dir).\
Working directory is used as the default source dir.\
The `pyproject.toml` in the working directory is detected and shown as a hint in the help panel.

______________________________________________________________________

### `wheel` (`pip wheel` — already in pip, but surfaced more prominently)

This command already exists in `COMMAND_SPECS`. No new extra needed. The existing "Artifacts" group gains better
visibility via the tool switcher if users install nothing extra.

______________________________________________________________________

### `virtualenv`

**Groups:** Create, Manage

| Command | Label | Safety | Key Args |
|-----------|------------|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `create` | Create Env | `MODIFIES_ENV` | dest dir (positional, dir picker, required); `--python` text (interpreter path); `--system-site-packages` checkbox; `--copies` checkbox; `--clear` checkbox; `--prompt` text; `--creator` dropdown (builtin/venv/cpython3-posix); `--seeder` dropdown (pip/app-data) |
| `version` | Version | `READ_ONLY` | — |

**Custom middle panel:** `VirtualenvPanel` — after a successful `create`, shows a one-click "Activate in new terminal"
button that launches a shell with the env activated (Windows: `cmd /K activate.bat`; POSIX:
`bash --init-file activate`).

Auto-run on select: `version`.

______________________________________________________________________

### `twine`

**Groups:** Upload, Check

| Command | Label | Safety | Key Args |
|-----------|-------------|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `upload` | Upload | `MODIFIES_ENV` | dists glob (multi, file picker, required); `--repository` text (default: pypi); `--repository-url` text; `--username` text; `--password` secret text; `--skip-existing` checkbox; `--disable-progress-bar` checkbox; `--cert` file; `--client-cert` file; `--verbose` checkbox |
| `check` | Check Dists | `READ_ONLY` | dists (multi, file picker, required); `--strict` checkbox |
| `version` | Version | `READ_ONLY` | — |

**Note:** `--password` is a `secret` field type — rendered as `ttk.Entry(show="*")` and redacted in output/history. The
existing `show_secrets` toggle reveals it.

**Custom middle panel:** Not required; `CommandForm` handles it. The `GlobalOptionsDialog` equivalent for twine stores
`.pypirc`-sourced repository aliases and offers a "Test connection" button that runs `twine check` on a dummy file.

**pip-audit output:** The `--output` format dropdown is shown to the user. When `json` is selected, a post-process step
parses the output and replaces the raw text panel with `AuditResultPanel`: a sortable table with columns (package,
installed version, vuln ID, fix version, severity). For all other formats the raw output panel is used unchanged.

Auto-run on select: `version`.

______________________________________________________________________

### `pip-audit`

**Groups:** Audit

| Command | Label | Safety | Key Args |
|-----------|---------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `audit` | Audit | `READ_ONLY` | `--requirement` file picker (multi); `--output` dropdown (columns/json/cyclonedx-json/cyclonedx-xml); `--vulnerability-service` dropdown (osv/pypi); `--fix` checkbox (safety: `MODIFIES_ENV`); `--dry-run` checkbox; `--skip-editable` checkbox; `--ignore-vuln` multi text; `--disable-pip` checkbox; `--no-deps` checkbox; `--timeout` spinbox |
| `version` | Version | `READ_ONLY` | — |

**Custom middle panel:** `AuditResultPanel` — parses JSON output from `--output json` and renders a sortable table of
CVEs with severity, package, affected version, and fix version columns. Falls back to raw text if JSON parsing fails.

Auto-run on select: `version`. `audit` itself is not auto-run (may be slow and makes network calls).

______________________________________________________________________

### `hatch`

Hatch is project-scoped. The working directory must contain a `pyproject.toml` with `[tool.hatch]` for most commands to
be meaningful.

**Groups:** Environment, Build, Publish, Project, Run

| Command | Label | Safety | Key Args |
|----------------|--------------|----------------|---------------------------------------------------------------------------------------|
| `env_show` | Show Envs | `READ_ONLY` | `--json` checkbox |
| `env_create` | Create Env | `MODIFIES_ENV` | env name text (default: default) |
| `env_remove` | Remove Env | `DESTRUCTIVE` | env name text |
| `env_prune` | Prune Envs | `DESTRUCTIVE` | — |
| `build` | Build | `MODIFIES_ENV` | target dropdown (wheel/sdist/app); `--clean` checkbox; `--clean-hooks-after` checkbox |
| `publish` | Publish | `MODIFIES_ENV` | target dropdown (pypi/test); `--user` text; `--auth` secret text; `--repo` text |
| `version_show` | Show Version | `READ_ONLY` | — |
| `version_set` | Set Version | `MODIFIES_ENV` | version text (required) |
| `run` | Run Script | `MODIFIES_ENV` | env text; command text (required) |
| `fmt` | Format | `MODIFIES_ENV` | `--check` checkbox |
| `lint` | Lint | `READ_ONLY` | — |

**Custom middle panel:** `HatchEnvPanel` — top section shows a live-refreshed table of known environments (name, type,
path, python version) populated by running `hatch env show --json`. Bottom section is the standard `CommandForm`. The
env table has a right-click menu: Create, Remove, Shell.

**Toolbar change:** When hatch or flit is the active tool, the "Dir:" label in the toolbar is renamed to "Project Dir:". A status chip "hatch project: {name} {version}" is added to the status bar when a valid `pyproject.toml` is detected in the working directory.

Auto-run on select: `env_show`, `version_show`.

______________________________________________________________________

### `flit`

Flit is simpler than hatch. It requires a `pyproject.toml` (or legacy `flit.ini`) in the working directory.

**Groups:** Build, Publish

| Command | Label | Safety | Key Args |
|-----------|---------------|----------------|--------------------------------------------------------------------------------------------------------------------------------|
| `build` | Build | `MODIFIES_ENV` | `--format` dropdown (wheel/sdist) |
| `publish` | Publish | `MODIFIES_ENV` | `--repository` text (default: pypi); `--pypirc` file; `--format` dropdown (wheel/sdist); `--env` text (for token from env var) |
| `install` | Install (dev) | `MODIFIES_ENV` | `--symlink` checkbox; `--pth-file` checkbox; `--deps` dropdown (all/develop/production/none) |

**No custom panel** — `CommandForm` is sufficient given flit's small command surface.

Auto-run on select: none.

The help panel shows a link to flit's docs and a detected project name/version from `pyproject.toml` when available.

______________________________________________________________________

### `pipx`

pipx manages applications in isolated environments. It manages its own internal venvs and does not use the selected interpreter the way pip does.

**Toolbar change when pipx is active:** The interpreter picker row is hidden. In its place a **Python picker** dropdown appears, populated by `pipx pythons` (or the same interpreter discovery logic used elsewhere, since `pipx` accepts `--python <path>`). The user selects a Python version to use for new installs; existing pipx apps are unaffected. If no Python is selected, pipx uses its default.

**Groups:** Apps, Environments

| Command | Label | Safety | Key Args |
|-----------------|------------------|----------------|---------------------------------------------------------------------------------------------------------------------------------|
| `install` | Install App | `MODIFIES_ENV` | package (text, required); `--python` text; `--index-url` text; `--pip-args` text; `--force` checkbox; `--include-deps` checkbox |
| `uninstall` | Uninstall App | `DESTRUCTIVE` | package (text, required) |
| `uninstall_all` | Uninstall All | `DESTRUCTIVE` | — |
| `upgrade` | Upgrade App | `MODIFIES_ENV` | package (text, required); `--pip-args` text |
| `upgrade_all` | Upgrade All | `MODIFIES_ENV` | `--skip` multi text; `--include-injected` checkbox |
| `inject` | Inject | `MODIFIES_ENV` | app (text, required); packages (multi, required); `--include-apps` checkbox; `--include-deps` checkbox |
| `list` | List Apps | `READ_ONLY` | `--json` checkbox; `--short` checkbox; `--include-injected` checkbox |
| `run` | Run (ephemeral) | `MODIFIES_ENV` | package (text, required); args (multi); `--python` text; `--index-url` text |
| `runpip` | Run pip in App | `MODIFIES_ENV` | app (text, required); pip args (multi, required) |
| `ensurepath` | Ensure PATH | `MODIFIES_ENV` | — |
| `environment` | Show Environment | `READ_ONLY` | `--json` checkbox |

**Custom middle panel:** `PipxAppsPanel` — top section shows a live-refreshed table of installed pipx apps (app name,
version, python, path) populated by `pipx list --json`. Selecting a row pre-fills the app name field in the command form
below. Right-click menu: Upgrade, Uninstall, Open install path.

Auto-run on select: `list`, `environment`.

______________________________________________________________________

## Middle Panel Swap Protocol

The existing `build_main_panels()` in `main_window.py` creates `command_form` and `output_panel` inside a vertical
`PanedWindow`. The swap protocol is:

1. `tool_plugin.panel_class` is `None` → use existing `CommandForm` unchanged.
1. `tool_plugin.panel_class` is a class → instantiate it in place of `CommandForm`. The class must implement the same
   interface: `set_command(spec)`, `get_argv()`, `do_run()`, `update_preview()`. Custom panels embed a `CommandForm`
   internally for the argument fields; the custom part sits above it (e.g. the env table in `HatchEnvPanel`).
1. On tool switch, the old panel is destroyed and the new one is packed in its place. `output_panel` is always preserved
   across switches.

______________________________________________________________________

## Menu Changes

### File menu

No change.

### Tools menu

Add a **Switch Tool** submenu listing all registered tools (including unavailable ones greyed out with their install
hint).

### Help menu

The "pip Documentation" item becomes dynamic: it resolves to the active tool's `help_url`. "pip Release Notes" is shown
only when pip is the active tool.

______________________________________________________________________

## Settings Persistence

`AppSettings` gains:

- `"active_tool"`: str — last active tool name, default `"pip"`.
- `"tool_options"`: dict[str, dict] — per-tool equivalent of `global_options`, keyed by tool name.

______________________________________________________________________

## Detection Logic

Detection runs at two moments: application startup, and whenever the interpreter changes.

**Two-tier detection:**

1. **Global path** — `shutil.which(executable)` against the ambient `$PATH`. If found, the tool tab is active even without a selected interpreter. This covers hatch, flit, twine, pipx installed into the user's system or a global venv.
1. **Interpreter-local** — for `python -m` tools (build, pip-audit, virtualenv), run a fast import probe: `python -c "import build; print('ok')"` via the selected interpreter. If the selected interpreter changes, probes re-run.

A tool is considered available if *either* tier succeeds. Tab state is updated immediately when detection completes (async, non-blocking — runs in a thread; tabs update via `after()` callback).

```python
def is_available(plugin: ToolPlugin, interpreter: InterpreterInfo | None) -> bool:
    if plugin.run_via == "python_module":
        # interpreter-local probe
        return interpreter is not None and _probe_module(interpreter.path, plugin.module)
    else:
        # global path probe (twine, hatch, flit, pipx)
        local = _which_in_interpreter(interpreter, plugin.executable) if interpreter else None
        return bool(local or shutil.which(plugin.executable))
```

For `python -m` tools installed globally (e.g. `pip install build` without a venv), the global probe also checks `shutil.which("python") + "-m" + module` as a fallback.

`ToolPlugin` gains a `run_via: Literal["python_module", "global_cli"]` field and, for module-based tools, a `module: str` field (e.g. `"build"`, `"pip_audit"`).

______________________________________________________________________

## File Layout

```
pip_ui/
  tools/
    __init__.py        # TOOL_REGISTRY, ToolPlugin dataclass
    pip_tool.py        # existing pip commands migrated here
    build_tool.py
    virtualenv_tool.py
    twine_tool.py
    pip_audit_tool.py
    hatch_tool.py
    flit_tool.py
    pipx_tool.py
  ui/
    hatch_env_panel.py
    pipx_apps_panel.py
    audit_result_panel.py
    virtualenv_panel.py
    tool_switcher.py   # tab row widget, lives above the interpreter picker
```

`command_specs.py` is kept as-is for backwards compatibility; `pip_tool.py` imports from it.

______________________________________________________________________

## What Is Not Changing

- The application is still called **pip-ui** / **pip-ui-tkinter**.
- The interpreter picker, requirements picker, index selector, global options, proxy dialog, cert tester, output panel,
  help panel, history, and settings system are all unchanged or minimally extended.
- Zero new mandatory dependencies. The base install stays stdlib-only.
- No pip internals are used by any of the new tools either.

______________________________________________________________________

## Resolved Design Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Switcher widget: dropdown or tab row? | **Tab row** — more discoverable; greyed tabs for unavailable tools |
| 2 | pip-audit JSON: always force it or let user choose? | **User chooses** — AuditResultPanel activates only when JSON format is selected |
| 3 | Rename "Dir:" to "Project Dir:" for hatch/flit? | **Yes** — label updates on tab switch |
| 4 | pipx interpreter picker: hide or replace? | **Hide interpreter row; show a Python picker** populated from interpreter discovery |
| 5 | Detect tools on the global PATH even without a selected interpreter? | **Yes** — two-tier detection: global `$PATH` first, interpreter-local second |
