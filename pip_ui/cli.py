"""Command-line entry point for pip_ui."""

from __future__ import annotations

import argparse

from pip_ui.__about__ import __version__


def main() -> None:
    """Run the pip_ui CLI."""
    parser = argparse.ArgumentParser(
        prog="pip_ui",
        description="A pip UI tool",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    # TODO: add subcommands here
    args = parser.parse_args()
    _ = args  # remove once subcommands are added


if __name__ == "__main__":
    main()
