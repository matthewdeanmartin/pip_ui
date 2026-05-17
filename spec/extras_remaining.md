# Remaining Work: pip-ui Extras

Cross-reference: `spec/spec_extras.md`

This document lists every discrete piece of work needed to implement the extras spec, grouped by layer. Items within a section can largely be done in parallel; sections have ordering dependencies as noted.

---

## 0. Pre-work (do first)

- [ ] Move `docs/spec_extras.md` — done; canonical copy is now `spec/spec_extras.md`. Delete the `docs/` copy.
- [ ] Add `spec/` to `.gitignore` exclusions if docs are excluded, or confirm spec files are committed.
- [ ] Verify `pyproject.toml` extras syntax with a dry `hatch build` (no new deps yet, just the `[project.optional-dependencies]` table structure).

---

## 1. `pyproject.toml` extras ✅

- [x] Add `[project.optional-dependencies]` section with one entry per tool:
  ```toml
  build      = ["build>=1.0"]
  virtualenv = ["virtualenv>=20.0"]
  twine      = ["twine>=5.0"]
  pip-audit  = ["pip-audit>=2.7"]
  hatch      = ["hatch>=1.9"]
  flit       = ["flit>=3.9"]
  pipx       = ["pipx>=1.4"]
  all-tools  = ["build>=1.0", "virtualenv>=20.0", "twine>=5.0",
                "pip-audit>=2.7", "hatch>=1.9", "flit>=3.9", "pipx>=1.4"]
  ```
- [ ] Update `README.md` install section to document extras.

---

## 2. Core data model (`pip_ui/tools/`) ✅

- [x] Create `pip_ui/tools/__init__.py` with `ToolPlugin` dataclass, `get_registry()`, `get_plugin()`
- [x] Create `pip_ui/tools/pip_tool.py`
- [x] Create `pip_ui/tools/build_tool.py`
- [x] Create `pip_ui/tools/virtualenv_tool.py`
- [x] Create `pip_ui/tools/twine_tool.py`
- [x] Create `pip_ui/tools/pip_audit_tool.py`
- [x] Create `pip_ui/tools/hatch_tool.py`
- [x] Create `pip_ui/tools/flit_tool.py`
- [x] Create `pip_ui/tools/pipx_tool.py`

---

## 3. Detection logic (`pip_ui/tool_detector.py`) ✅

- [x] `_probe_module`, `_which_in_interpreter`, `is_available`, `detect_all_tools` (background thread + callback)
- [ ] Write unit tests (mock `subprocess.run` and `shutil.which`)

---

## 4. Runner generalisation (`pip_ui/runner.py`) ✅

- [x] `build_prefix(interpreter_path, plugin)` — python_module vs global_cli
- [x] `build_argv` accepts optional `plugin` parameter (backwards compat)
- [x] `redact_argv` extended with `secret_flags` parameter
- [x] `main_window.py` updated to pass active plugin and secret_flags

---

## 5. `models.py` changes ✅

- [x] `"secret"` documented in `ArgSpec.field_type` comment

---

## 6. `CommandForm` changes ✅

- [x] `field_type == "secret"` renders as `ttk.Entry(show="*")`
- [x] `set_show_secret(reveal)` on `FieldWidget`; `apply_show_secrets(reveal)` on `CommandForm`
- [x] `on_show_secrets_toggle` in `MainWindow` propagates to form

---

## 7. Tool switcher widget ✅

- [x] `ToolSwitcher` — tab row of toggle buttons with active/disabled visual states
- [x] Clicking unavailable tab shows install-hint dialog
- [x] `set_available`, `select`, `configure_styles`

---

## 8. `MainWindow` integration (`pip_ui/ui/main_window.py`) ✅ (core done)

- [x] `ToolSwitcher` added as full-width tab row above interpreter picker
- [x] `self.active_plugin` (default pip)
- [x] `on_tool_switch`: rebuilds tree, clears form, hides interpreter row for pipx, renames Dir label, updates title bar, updates Help menu, clears output cache
- [x] `_start_tool_detection` background thread; re-runs on interpreter change
- [x] Restore `"active_tool"` from settings on startup
- [x] `run_command` passes active plugin and secret_flags to runner
- [x] `autorun_on_select` extended with all tool auto-run commands
- [x] Help menu: dynamic "Documentation" label + pip Release Notes hidden for non-pip tools
- [ ] Tools menu: "Switch Tool" submenu (low priority — tab row makes it redundant)
- [ ] `swap_middle_panel` for custom panel classes (needed for sections 9a–9d)
- [ ] About dialog tool mention

---

## 9. Custom panels

Each can be developed and tested independently once `CommandForm` and `ToolPlugin` exist.

### 9a. `VirtualenvPanel` (`pip_ui/ui/virtualenv_panel.py`)

- [ ] Thin wrapper: `CommandForm` for args + "Activate in new terminal" button shown after a successful `create` run.
- [ ] Button launches: Windows: `start cmd /K "{venv_path}\Scripts\activate.bat"`; POSIX: `x-terminal-emulator -e bash --init-file "{venv_path}/bin/activate"` with fallbacks to gnome-terminal, xterm.
- [ ] Button is disabled/hidden until a `create` command exits 0 and the dest dir field is non-empty.

### 9b. `AuditResultPanel` (`pip_ui/ui/audit_result_panel.py`)

- [ ] `AuditResultPanel(parent)` — `ttk.Treeview` with columns: Package, Installed, Vuln ID, Fix Version, Severity.
- [ ] `load_json(json_str)` — parses pip-audit JSON output (schema: `{"dependencies": [{"name", "version", "vulns": [{"id", "fix_versions", "aliases", "description"}]}]}`). Maps CVE severity from aliases heuristically (CRITICAL/HIGH/MEDIUM/LOW from CVSS score range in description, or Unknown).
- [ ] Sortable columns (click header toggles asc/desc).
- [ ] Row selection shows full vuln description in a text widget below the table.
- [ ] Falls back to a `tk.Text` raw display if JSON parse fails.
- [ ] Activated by `main_window.py` post-processing: after `audit` exits, if `--output json` was in argv, parse and show; otherwise raw panel.

### 9c. `HatchEnvPanel` (`pip_ui/ui/hatch_env_panel.py`)

- [ ] `ttk.Treeview` table: Name, Type, Python, Path.
- [ ] Populated by running `hatch env show --json` in the working directory. Runs in background thread; updates via queue.
- [ ] Refresh button + auto-refresh after any `env_create` / `env_remove` / `env_prune` completes.
- [ ] Right-click context menu: Create (opens form pre-filled), Remove (confirms then runs), Shell (launches terminal with `hatch shell {env}`).
- [ ] Row click pre-fills env name field in the `CommandForm` below.
- [ ] `CommandForm` sits below the table in the same vertical pane.

### 9d. `PipxAppsPanel` (`pip_ui/ui/pipx_apps_panel.py`)

- [ ] `ttk.Treeview` table: App, Version, Python, Install Path.
- [ ] Populated by `pipx list --json`. Background thread + queue refresh.
- [ ] Refresh button + auto-refresh after `install` / `uninstall` / `upgrade` / `upgrade_all` exits.
- [ ] Right-click: Upgrade, Uninstall (with confirm), Open install path in file manager.
- [ ] Row click pre-fills the app/package name field in the `CommandForm` below.

---

## 10. pipx Python picker (`pip_ui/ui/pipx_python_picker.py`)

**Depends on:** Section 8 (toolbar show/hide)

- [ ] `PipxPythonPicker(parent, on_change)` — a dropdown populated by the same interpreter discovery as `InterpreterPicker`, showing only the Python path + version string (no pip version).
- [ ] Exposes `get_python_path() -> str | None`.
- [ ] Shown in place of the interpreter picker row when pipx is the active tool.
- [ ] Selected python path is passed as `--python {path}` to any pipx command whose spec includes a `python` arg.

---

## 11. Help panel updates (`pip_ui/ui/help_panel.py`)

- [ ] `update_for_command` already accepts `CommandSpec`; no signature change needed.
- [ ] Add `set_base_url(url)` so the panel fetches docs from the active tool's `help_url` instead of pip's.
- [ ] For project-scoped tools (hatch, flit), detect `pyproject.toml` in the working directory and show project name + version as a status line at the top of the help panel.

---

## 12. Settings updates (`pip_ui/settings.py`)

- [ ] Document (and handle migration for) two new keys: `"active_tool"` (str), `"tool_options"` (dict).
- [ ] `get_tool_options(tool_name) -> dict` and `set_tool_options(tool_name, opts)` convenience methods.

---

## 13. Tests

- [ ] Unit tests for each `*_tool.py` — validate command specs produce correct argv lists.
- [ ] Unit tests for `tool_detector.py` — mock subprocess and shutil.which.
- [ ] Unit tests for `runner.py` changes — verify prefix logic for each `run_via` value.
- [ ] Unit tests for `AuditResultPanel.load_json` — valid JSON, empty results, malformed JSON.
- [ ] Smoke tests (no-display) for `VirtualenvPanel`, `HatchEnvPanel`, `PipxAppsPanel` widget construction.
- [ ] Integration test: `MainWindow` with each extra installed, tab switch round-trips, tool is correctly detected.

---

## 14. Docs / README

- [ ] Update `README.md`: extras install table, screenshot showing tab row.
- [ ] Update `CHANGELOG.md` with the 0.3.0 entry once shipped.
- [ ] `mkdocs` pages: one page per tool with command reference.

---

## Dependency order summary

```
1 (pyproject extras)
2 (data model) → 3 (detection) → 7 (switcher widget)
2 → 4 (runner) → 8 (MainWindow)
2 → 5 (models) → 6 (CommandForm secret field)
7 + 6 + 4 → 8 (MainWindow integration)
8 → 9a, 9b, 9c, 9d (custom panels)
8 → 10 (pipx picker)
8 → 11 (help panel)
Everything → 13 (tests)
Everything → 14 (docs)
```

Sections 2–6 and 1 can all proceed in parallel before 7 and 8 are started.
