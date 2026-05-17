"""Command-line entry point for pip_ui."""

from __future__ import annotations

import argparse
import sys

from pip_ui.__about__ import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pip-ui",
        description="A Tkinter GUI for pip. Runs commands via: python -m pip",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--interpreter",
        metavar="PATH",
        help="Path to the Python interpreter to use.",
        default=None,
    )
    parser.add_argument(
        "--working-directory",
        metavar="PATH",
        help="Working directory for pip commands.",
        default=None,
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Print a diagnostics report and exit without launching the GUI.",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not record command history.",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Prompt for confirmation before any potentially destructive command.",
    )

    args = parser.parse_args()

    if args.diagnostics:
        run_diagnostics(args.interpreter)
        return

    try:
        import tkinter as tk
    except ImportError:
        print(
            "Error: Tkinter is not available in this Python installation.\n"
            "On Debian/Ubuntu: sudo apt-get install python3-tk\n"
            "On Fedora: sudo dnf install python3-tkinter\n"
            "On macOS: install Python from python.org (includes Tk)\n"
            "On Windows: re-run the Python installer and ensure 'tcl/tk' is checked.",
            file=sys.stderr,
        )
        sys.exit(1)

    from pip_ui.ui.main_window import MainWindow

    app = MainWindow(
        no_history=args.no_history,
        safe_mode=args.safe_mode,
    )

    if args.interpreter:
        app.after(200, lambda: app.interpreter_picker.set_from_path(args.interpreter))

    if args.working_directory:
        app.workdir_var.set(args.working_directory)

    app.mainloop()


def run_diagnostics(interpreter_path: str | None) -> None:
    from pip_ui.environment import InterpreterDiscovery

    discovery = InterpreterDiscovery()
    interpreters = discovery.discover()

    if interpreter_path:
        target = discovery.validate(interpreter_path)
        if target is None:
            print(f"Warning: Could not validate interpreter at: {interpreter_path}", file=sys.stderr)
            target = interpreters[0] if interpreters else None
    else:
        target = interpreters[0] if interpreters else None

    if target is None:
        print("No Python interpreters found.", file=sys.stderr)
        sys.exit(1)

    from pip_ui.config_inspector import ConfigInspector

    inspector = ConfigInspector(target.path)
    report = inspector.build_diagnostics_report("markdown")
    print(report)


if __name__ == "__main__":
    main()
