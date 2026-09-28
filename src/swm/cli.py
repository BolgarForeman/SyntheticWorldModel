"""Command-line entry point for the ``swm`` command."""

import argparse
from collections.abc import Sequence

from swm import __version__


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``swm`` command.

    Parameters
    ----------
    argv : Sequence[str] or None
        Command-line arguments without the program name. ``None`` reads them from ``sys.argv``.

    Returns
    -------
    int
        The process exit code.

    Spec: CLAUDE.md §5 (``cli.py``); Work Order 0 item 4.
    """
    parser = argparse.ArgumentParser(prog="swm")
    parser.add_argument("--version", action="version", version=f"swm {__version__}")
    parser.parse_args(argv)
    return 0
