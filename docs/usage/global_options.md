# Global Options

`pip` supports many global flags that affect the behavior of almost every command. `pip-ui-tkinter` provides a dedicated dialog for managing these settings to keep individual command forms clean and focused.

## Accessing Global Options

Click the **Global Options...** button at the bottom of any command form. This opens a modal dialog where you can configure:

- **Verbosity (`-v` / `-q`):** Control how much output `pip` generates.
- **Isolation (`--isolated`):** Run `pip` in isolation from environment variables and user configuration.
- **Network Settings:**
  - **Proxy:** Specify a proxy server.
  - **Timeout:** Set socket timeouts.
  - **Retries:** Set the maximum number of connection retries.
  - **Certs:** Path to CA certificates or client certificates.
- **Caching:** Override the default cache directory or disable caching.
- **Environment Constraints:** Force `pip` to only run inside a virtual environment (`--require-virtualenv`).

## Active Options Summary

When you change a global option from its default value, a "chip-style" summary appears next to the **Global Options...** button on the main form. This ensures you always know which hidden flags are being appended to your command.

## Resetting Defaults

You can quickly revert all global options to their standard `pip` defaults using the **Reset** button within the Global Options dialog.
