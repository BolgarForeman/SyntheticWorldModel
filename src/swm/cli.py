"""Command-line entry point for the ``swm`` command."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pydantic
import yaml

from swm import __version__
from swm.recipe.buildability import unbuilt_features
from swm.recipe.io import load_recipe, write_resolved_recipe, write_stream_record
from swm.recipe.resolve import Resolution, resolve
from swm.rng import stream_record

EXIT_OK = 0
EXIT_BAD_RECIPE = 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``swm`` command.

    Parameters
    ----------
    argv : Sequence[str] or None
        Command-line arguments without the program name. ``None`` reads them from ``sys.argv``.

    Returns
    -------
    int
        The process exit code: 0 on success, 1 if the recipe cannot be read.

    Spec: CLAUDE.md §5 (``cli.py``); Work Order 1, item 4.
    """
    parser = _parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        return EXIT_OK
    try:
        resolution = resolve(load_recipe(Path(arguments.recipe)))
    except (OSError, ValueError, yaml.YAMLError) as error:
        # pydantic.ValidationError is a ValueError; its message names every failing field.
        sys.stderr.write(f"swm: cannot read {arguments.recipe}:\n{_describe(error)}\n")
        return EXIT_BAD_RECIPE
    if arguments.command == "resolve":
        _write_resolution(resolution, Path(arguments.out_dir))
    else:
        sys.stdout.write(check_report(resolution))
    return EXIT_OK


def check_report(resolution: Resolution) -> str:
    """Return the validation notes and buildability report for a resolved recipe.

    Parameters
    ----------
    resolution : Resolution
        A resolved recipe and its notes.

    Returns
    -------
    str
        The report, one item per line.

    Spec: Work Order 1, items 2 and 4.
    """
    lines = ["Validation notes:"]
    lines += [f"  - {note}" for note in resolution.notes] or ["  none"]
    lines.append("Not yet buildable:")
    unbuilt = unbuilt_features(resolution.recipe)
    lines += [f"  - {status.feature}: {status.arrival}" for status in unbuilt] or ["  none"]
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swm")
    parser.add_argument("--version", action="version", version=f"swm {__version__}")
    commands = parser.add_subparsers(dest="command")
    resolve_command = commands.add_parser(
        "resolve", help="write the resolved recipe and the stream record"
    )
    resolve_command.add_argument("recipe", help="recipe YAML file")
    resolve_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    check_command = commands.add_parser(
        "check-recipe", help="print validation notes and the buildability report"
    )
    check_command.add_argument("recipe", help="recipe YAML file")
    return parser


def _write_resolution(resolution: Resolution, out_dir: Path) -> None:
    recipe = resolution.recipe
    write_resolved_recipe(recipe, out_dir)
    write_stream_record(stream_record(recipe.root_seed, recipe.terrain.terrain_seed), out_dir)


def _describe(error: Exception) -> str:
    if isinstance(error, pydantic.ValidationError):
        return "\n".join(
            f"  {'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
    return f"  {error}"
