# Configuration & Editors

Understanding where `pip` gets its settings is crucial for troubleshooting. `pip-ui-tkinter` provides tools to inspect and edit your configuration safely.

## Configuration Dashboard

Open the **Configuration Dashboard** (from the menu or toolbar) to see a comprehensive view of your `pip` environment:

- **Active Interpreter:** Details about the selected Python version and its virtual environment status.
- **Config Files:** A list of all configuration files `pip` is aware of, including their scope (global, user, or site) and whether they currently exist.
- **Environment Variables:** Values like `PIP_INDEX_URL` or `VIRTUAL_ENV` that might be overriding your config files.
- **Index Settings:** A summary of your package indexes, extra indexes, and trusted hosts.
- **Secrets Redaction:** By default, sensitive information (like passwords in URLs) is redacted. You can toggle **Show Sensitive Values** to view them.

## Editing Configuration

The `config_edit` command allows you to open your `pip` configuration file in an external editor.

### Editor Opener

When you run `config_edit`, `pip-ui-tkinter` invokes `pip config edit`.

- **Windows:** If no editor is configured in your environment (via `EDITOR` or `VISUAL` variables), `pip-ui-tkinter` defaults to `notepad.exe` to ensure the file opens successfully.
- **POSIX:** It relies on your system's default editor configuration.

## Exporting Diagnostics

The Configuration Dashboard includes an **Export Diagnostics...** button. This generates a Markdown, JSON, or Text report containing all the information in the dashboard. This is perfect for attaching to bug reports or sharing with team members when troubleshooting environment issues.
