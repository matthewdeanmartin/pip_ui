# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-05-24

### Added

- `poetry` tool plugin: add/remove/update/show dependencies, lock, check, manage virtual environments, build, publish, version bump, and run commands inside the project environment.
- `pipenv` tool plugin: install/uninstall/upgrade/update/sync/clean packages, generate and verify Pipfile.lock, export requirements.txt, inspect dependency graph, run scripts, audit for vulnerabilities, and manage the project virtualenv.
- `uv` tool plugin: add/remove dependencies, sync and lock the project, display dependency tree, export lockfile, run commands, create virtual environments, build distributions, publish to an index, manage Python versions, and manage the uv cache.
- `deptry` tool plugin: scan for missing, unused, transitive, and misplaced dependencies in the project source tree.

## [0.2.0] - 2026-05-23

### Added

- Tool plugin architecture: `build`, `virtualenv`, `twine`, `pip-audit`, `hatch`, `flit`, `pipx`, `pypiserver`, and `devpi` are now first-class plugins with their own command catalogs, forms, and (where relevant) dedicated panels.
- Tool switcher UI — switch between all supported tools from a single toolbar.
- `pypiserver` plugin: run a local PyPI-compatible index for testing and offline workflows.
- `devpi` plugin: drive a devpi server and client with a dedicated panel.
- `tool_detector` module: auto-detects which optional tools are installed and enables them at startup.
- Per-tool optional extras in `pyproject.toml` so users install only what they need.
- `settings.py` support for persisting user preferences across sessions.
- Help panel improvements: links and descriptions per tool.
- Output panel: per-command output cache restores last output when re-selecting a command.
- Integration and end-to-end test suite (`test_integration_e2e.py`).
- Custom panel smoke tests (`test_custom_panels_smoke.py`).
- Security scan via `bandit` added to CI.

## [0.1.0] - 2026-04-26

### Added

- Initial release with `pip` support: install, uninstall, list, freeze, show, check, inspect, configure, cache, debug commands.
- Command spec model (`models.py`): typed `ArgSpec` and `CommandSpec` definitions covering required/optional args, field types, safety levels, and help text.
- Form renderer: generates the correct widget (checkbox, dropdown, file picker, multi-value, text) from each command spec.
- Safety classification: commands tagged as read-only, environment-modifying, destructive, or risky-config; `--safe-mode` prompts before destructive runs.
- Runner: constructs the exact CLI argv, streams stdout/stderr live, records exit code and duration.
- Command history: every run is appended to disk; `--no-history` disables it.
- `config_inspector.py`: reads and surfaces pip configuration from all standard locations.
- Config view panel: displays active pip config in the UI.
- `environment.py`: auto-discovers system Python, active `VIRTUAL_ENV`, project `.venv`, and `python`/`py` on `PATH`.
- Interpreter picker dropdown for targeting any discovered environment.
- `--diagnostics` flag: prints a Markdown env report and exits without launching the GUI.
- Self-update check (`self_update.py`): background check for newer `pip-ui-tkinter` releases on PyPI.
- Global options dialog: per-run proxy, index URL, trusted hosts, and cert settings.
- Requirements-file picker widget.
- Certificate tester panel.
- Index selector panel.
- Proxy dialog.
- Common pip error interception with plain-language explanations in the output panel.
- `--interpreter` and `--working-directory` CLI flags.
- Secret flag redaction: tokens and passwords hidden in output panel and history file.
- Full unit test suite covering command specs, config inspector, environment discovery, history, runner, safety, forms, encoding, and more.
