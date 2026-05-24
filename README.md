# pip-ui-tkinter

A Tkinter desktop GUI that puts a friendly face on Python's most-used packaging tools. Instead of remembering flags across `pip`, `pipx`, `build`, `twine`, `virtualenv`, `pip-audit`, `hatch`, `flit`, `pypi-server`, and `devpi`, you click through them in a single window — with discoverable forms, live output, and guardrails on the destructive bits.

## Why pip-ui-tkinter

- **One window, ten tools.** Switch between `pip`, `pipx`, `build`, `twine`, `virtualenv`, `pip-audit`, `hatch`, `flit`, `pypi-server`, and `devpi` from a single tool switcher. No need to context-switch between docs, terminals, and tutorials.
- **Discoverable commands.** Every subcommand and flag is laid out as a tree with a generated form. You see what's available without `--help`-ing your way through ten layers of subcommands.
- **Real CLI underneath.** The UI doesn't reimplement anything — it constructs the exact CLI invocation and runs it. The full argv is shown before and after every run, so you can copy/paste it into a script or learn what the UI just did.
- **Safety rails.** Commands are classified as read-only, environment-modifying, destructive, or risky-config. A `--safe-mode` flag prompts for confirmation before anything that would uninstall, purge, or rewrite configuration. Global installs are flagged. Secrets in flags are redacted in history and output.
- **Pure Python, pure stdlib UI.** Tkinter ships with Python — no Electron, no browser, no npm. The app launches fast and runs anywhere Python and Tk do.

## Features

### Multi-tool support

Each tool is a plugin with its own command catalog, run mode, and (where relevant) custom panel:

| Tool | What it does in pip-ui |
|---------------|--------------------------------------------------------------|
| `pip` | Install, uninstall, list, freeze, show, check, inspect, configure, cache, debug |
| `pipx` | Install and manage CLI apps in isolated envs; pick the Python they use |
| `build` | Build sdists and wheels for the current project |
| `virtualenv` | Create virtual environments with a guided form |
| `twine` | Upload, check, and register distributions |
| `pip-audit` | Scan an env or requirements file; results render in a dedicated panel |
| `hatch` | Project and environment commands with an environment panel |
| `flit` | Build and publish flit-managed projects |
| `pypi-server` | Run a local PyPI-compatible index for testing |
| `devpi` | Drive a devpi server and client from a dedicated panel |

### Interpreter & environment awareness

- Auto-discovers the system Python, the active `VIRTUAL_ENV`, project `.venv`, and `python`/`py` on `PATH`.
- Switch interpreters per-run from the dropdown; the UI invokes commands via `python -m <tool>` against the selected interpreter so you can target any env.
- Working-directory picker — point any command at a specific project.
- `--diagnostics` mode prints a Markdown report on the selected interpreter without launching the GUI.

### Forms generated from command specs

- Every command knows its required and optional arguments, types, choices, and help text. The form is rendered from that spec, so you get the right widget (checkbox, picker, multi-value, text) for the right flag.
- Per-command global options dialog (proxy, index URL, trusted hosts, etc.) so you don't repeat yourself.
- Requirements-file picker, index selector, and certificate tester live alongside the form.

### Live output and history

- Stdout/stderr stream into an output panel as the command runs — no waiting for completion to see what happened.
- Per-command output cache: re-selecting a command restores its last output instead of a blank panel.
- Command history records every run (argv, exit code, duration). Disable with `--no-history` if you prefer not to write it to disk.
- Common pip errors are intercepted and translated to a plain-language explanation.

### Safety and secrets

- `--safe-mode` puts a confirmation dialog in front of any destructive or config-mutating command.
- Auto-detection of global installs warns before they're committed.
- Tool plugins declare which flags carry secrets (tokens, passwords); those values are redacted in the output panel and history file.

### Self-update check

- The app checks for newer versions of `pip-ui-tkinter` in the background and surfaces an upgrade hint when one's available. Manual checks available from the menu.

## Quick start

```bash
pipx install pip-ui-tkinter
pip-ui
```

Useful flags:

```bash
pip-ui --interpreter /path/to/python   # start with a specific interpreter selected
pip-ui --working-directory ./myproj    # start in a specific project dir
pip-ui --safe-mode                     # confirm before destructive commands
pip-ui --no-history                    # do not record history to disk
pip-ui --diagnostics                   # print env diagnostics and exit
```

To get the optional tools that aren't `pip` itself, install the matching extra (`build`, `virtualenv`, `twine`, `pip-audit`, `hatch`, `flit`, `pipx`, `pypiserver`, `devpi`) or `all-tools` for everything.

## Requirements

- Python 3.10+
- Tkinter (bundled with python.org installers; on Linux install your distro's `python3-tk` package)

## Links

- Source: <https://github.com/matthewdeanmartin/pip_ui>
- Issues: <https://github.com/matthewdeanmartin/pip_ui/issues>
- Changelog: [CHANGELOG.md](https://github.com/matthewdeanmartin/pip_ui/blob/main/CHANGELOG.md)

## License

MIT — see [LICENSE](https://github.com/matthewdeanmartin/pip_ui/blob/main/LICENSE).
