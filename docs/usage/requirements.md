# Picking Requirements

`pip-ui-tkinter` provides two ways to manage requirements files, making it easy to work with multiple projects or complex installation workflows.

## Global Requirements File

In the top toolbar, you can select a "Global Requirements" file. This is useful when you are working on a specific project and frequently need to install or update its requirements.

When a global requirements file is selected:

- It is automatically pre-filled into the `Requirements File` field for commands that support it (like `install` or `uninstall`).
- You can still override this selection on a per-command basis if needed.

## Per-Command Selection

Every command form that accepts a requirements file includes a dedicated field with a **Browse...** button.

- **Requirements File (`-r`):** Specify one or more requirements files to install from.
- **Constraints File (`-c`):** Constrain version numbers of installed packages without including them as direct requirements.

## Saving current state to Requirements

After running a command like `freeze`, you can easily copy the output or save it directly to a file from the output panel to update your project's `requirements.txt`.
