# Presets

`pip-ui-tkinter` allows you to save and load **Presets**, a feature not available in standard `pip`. Presets are perfect for complex commands that you run frequently.

## Saving a Preset

1. Configure a command exactly how you want it (fill in package names, toggle options, etc.).
2. Don't forget to configure any **Global Options** you want included in the preset.
3. Click the **Save Preset...** button.
4. Give your preset a descriptive name (e.g., "Install with Internal Index" or "Dry Run Upgrade All").

## Loading a Preset

1. Select the command you want to run.
2. Click **Load Preset...**
3. Choose from the list of presets specifically saved for that command.
4. The form and global options will be instantly populated with your saved settings.

## Managing Presets

- **Context-Specific:** Presets are tied to specific commands. You won't see your `install` presets when you are viewing the `list` command form.
- **Storage:** Presets are stored locally in your home directory (`~/.pip_ui/presets.json`), making them persistent across sessions.
- **Deletion:** You can delete presets from the **Load Preset** dialog.
