# pip-ui Extras — Final Steps and Future Work

**Date written:** 2026-05-17\
**Status:** Implementation complete through section 13. Remaining items are docs/polish only.

Cross-reference: `spec/spec_extras.md`, `spec/extras_remaining.md`

______________________________________________________________________

## What is done

Everything in `extras_remaining.md` sections 1–13 has been implemented and passes the full
test suite (286 tests). A brief inventory:

| Section | What shipped |
|---------|-------------|
| 1 | `pyproject.toml` `[project.optional-dependencies]` extras |
| 2 | `pip_ui/tools/` registry — `ToolPlugin` dataclass + one `*_tool.py` per tool |
| 3 | `pip_ui/tool_detector.py` — two-tier detection (interpreter-local + global PATH) |
| 4 | `pip_ui/runner.py` — `build_prefix(plugin)`, `build_argv(plugin)`, `redact_argv(secret_flags)` |
| 5 | `models.py` — `"secret"` field type documented |
| 6 | `CommandForm` — secret entry (`show="*"`), `apply_show_secrets`, `on_show_secrets_toggle` |
| 7 | `ToolSwitcher` — tab row, greyed unavailable tabs, install-hint dialog |
| 8 | `MainWindow` — tool switching, interpreter row show/hide, dir label rename, title bar, help menu, output cache clear, `swap_middle_panel`, pipx Python picker, project status detection |
| 9a | `pip_ui/ui/virtualenv_panel.py` — `VirtualenvPanel` with activate-in-new-terminal button |
| 9b | `pip_ui/ui/audit_result_panel.py` — `AuditResultPanel` sortable CVE table; shown as a Toplevel after `audit --output-format json` exits 0 |
| 9c | `pip_ui/ui/hatch_env_panel.py` — `HatchEnvPanel` with live env table, right-click menu, row-click pre-fill |
| 9d | `pip_ui/ui/pipx_apps_panel.py` — `PipxAppsPanel` with live apps table, right-click menu, row-click pre-fill |
| 10 | `pip_ui/ui/pipx_python_picker.py` — `PipxPythonPicker` shown in place of interpreter row when pipx is active |
| 11 | `HelpPanel.set_base_url(url)`, `set_project_status(status)` — dynamic doc URL + project name/version in Overview tab |
| 12 | `AppSettings.get_tool_options(name)`, `set_tool_options(name, opts)` — per-tool settings dict |
| 13 | 82 new unit/smoke tests across five new test files |

______________________________________________________________________

## What is NOT done (known gaps)

### From the original remaining list

- **Section 8 — Tools menu "Switch Tool" submenu** (low priority).\
  The tab row makes this redundant. Omitted intentionally.

- **Section 8 — About dialog tool mention.**\
  The About dialog still hard-codes the pip description. Small cosmetic gap.

- **Section 14 — Docs / README.**\
  See the Docs section below.

### Remaining limitations (post-fix)

- **`AuditResultPanel` pops a new Toplevel window.**\
  The spec says "parse and show" but is silent on modal vs. inline. The current
  implementation opens a `Toplevel`. Works fine; a future iteration could embed it in the
  middle pane instead.

- **`pip-audit` uses a plain `CommandForm`, not `AuditResultPanel` as its `panel_class`.**\
  Intentional: the result panel is a post-run display, not an input form. The trigger lives
  in `MainWindow._try_show_audit_result`.

______________________________________________________________________

## Missing wiring — FIXED

All five wiring gaps have been closed:

1. **`browse_workdir` → `set_workdir` on custom panels.** ✅\
   `MainWindow.browse_workdir` now calls `self.command_form.set_workdir(path)` when the
   active panel supports it.

1. **`OutputPanel.get_stdout_text()`.** ✅\
   Method added to `OutputPanel`. `_try_show_audit_result` calls it directly without the
   `hasattr` guard.

1. **`notify_run_done` ordering bug.** ✅\
   `on_run_done` now captures `finished_command = self.current_run_command` before setting
   it to `None`, so custom-panel notification and audit post-processing use the correct name.

1. **pipx `--python` injection.** ✅\
   `run_command` now injects `--python <path>` into `effective_pip_args` when the active
   tool is pipx and a non-default Python was selected in `PipxPythonPicker`. The
   `current_interpreter is None` guard is relaxed for pipx (global_cli tool).

1. **Help panel "Command Help" tab for non-pip tools.** ✅\
   `HelpPanel` now has `set_active_plugin(plugin)` which stores `run_via`, `module`, and
   `executable`. `populate_command_help` dispatches on `run_via`:

   - `python_module` + pip → existing `pip help <sub>` path
   - `python_module` + other → `python -m <module> <sub> --help`
   - `global_cli` → `<executable> <subcommand parts> --help`
     `on_tool_switch` in `MainWindow` calls `help_panel.set_active_plugin(plugin)`.

**Remaining before 0.3.0 release:**

______________________________________________________________________

- **Version number.**\
  `__version__` is still `"0.1.0"` in `pip_ui/__about__.py`. Bump to `"0.3.0"` when
  section 14 (docs) is complete.

______________________________________________________________________

## Section 14 — Docs (remaining)

- **`README.md` extras install table.**\
  Add a table under the Installation section:

  | Extra | What you get |
  |-------|-------------|
  | `pip install pip-ui-tkinter[build]` | `python -m build` support |
  | `pip install pip-ui-tkinter[virtualenv]` | `virtualenv` panel with activate button |
  | `pip install pip-ui-tkinter[twine]` | Twine upload/check panel |
  | `pip install pip-ui-tkinter[pip-audit]` | Vulnerability audit with CVE table |
  | `pip install pip-ui-tkinter[hatch]` | Hatch env/build/publish panel |
  | `pip install pip-ui-tkinter[flit]` | Flit build/publish panel |
  | `pip install pip-ui-tkinter[pipx]` | pipx apps panel |
  | `pip install pip-ui-tkinter[all-tools]` | Everything above |

- **`CHANGELOG.md` 0.3.0 entry.**\
  Write release notes once the missing wiring (above) is closed.

- **mkdocs pages.**\
  One page per tool (`docs/tools/build.md`, `docs/tools/virtualenv.md`, etc.) with the
  command reference table from `spec/spec_extras.md`. The `mkdocs.yml` nav already has a
  `Tools` section placeholder.

- **Screenshot update.**\
  Replace the pip-only screenshot in `README.md` with one showing the tool tab row and at
  least the HatchEnvPanel or PipxAppsPanel.

______________________________________________________________________

## Future / nice-to-have (not planned for 0.3.0)

- **Tools menu "Switch Tool" submenu** — keyboard-accessible alternative to the tab row.
- **About dialog** — mention the active tool and its version.
- **Twine GlobalOptionsDialog** — store `.pypirc` repository aliases and offer a
  "Test connection" button.
- **flit project status chip** — same as hatch (`flit project: {name} {version}` in the
  status bar). Already detected in `_detect_project_status` since both tools share
  `is_project_scoped=True`.
- **`tool_options` UI** — per-tool preferences dialog (e.g. default pipx Python, default
  hatch env name). The storage (`get_tool_options` / `set_tool_options`) is ready; no dialog
  exists yet.
- **Integration tests** — `MainWindow` with each extra installed, tab-switch round-trips,
  correct detection result. Blocked on a headless Tk display in CI.
- **pip-audit JSON in output panel** — embed `AuditResultPanel` directly in the middle pane
  instead of a floating Toplevel, by temporarily swapping it for the output panel after a
  JSON audit run completes.

______________________________________________________________________

## Dependency order for remaining work

```
fix browse_workdir wiring  ─┐
fix OutputPanel.get_stdout ─┼─▶ audit panel works end-to-end
fix pipx --python inject   ─┘
fix help panel strategy    ──▶ non-pip help text works
version bump              ──▶ 0.3.0 release
README + CHANGELOG         ──▶ publish
mkdocs pages               ──▶ docs site update
```
