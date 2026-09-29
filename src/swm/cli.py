"""Command-line entry point for the ``swm`` command."""

import argparse
import hashlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import pydantic
import yaml

from swm import __version__
from swm.recipe.buildability import unbuilt_features
from swm.recipe.io import (
    canonical_yaml,
    load_recipe,
    write_binary,
    write_canonical_yaml,
    write_hash_list,
    write_resolved_recipe,
    write_stream_record,
)
from swm.recipe.resolve import Resolution, resolve
from swm.rng import stream_record
from swm.stages import layers as layers_stage
from swm.stages.layers import LayersResult, build_layers, layers_streams
from swm.stages.terrain import (
    TerrainResult,
    array_hashes,
    build_terrain,
    statistics_record,
    terrain_streams,
)

EXIT_OK = 0
EXIT_FAILED = 1
TERRAIN_STATS_FILE = "terrain_stats.yaml"
TERRAIN_HASHES_FILE = "terrain_sha256.txt"
LAYERS_STATS_FILE = "layers_stats.yaml"
LAYERS_NODES_FILE = "layers_nodes.yaml"
LAYERS_LINKS_FILE = "layers_links.yaml"
LAYERS_HASHES_FILE = "layers_sha256.txt"


class CommandError(Exception):
    """A command could not finish; the message says why."""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``swm`` command.

    Parameters
    ----------
    argv : Sequence[str] or None
        Command-line arguments without the program name. ``None`` reads them from ``sys.argv``.

    Returns
    -------
    int
        The process exit code: 0 on success, 1 if the recipe cannot be read or the command
        cannot finish.

    Spec: CLAUDE.md §5 (``cli.py``); Work Order 1, item 4; Work Order 2, A10 and A11.
    """
    arguments = _parser().parse_args(argv)
    if arguments.command is None:
        return EXIT_OK
    try:
        resolution = resolve(load_recipe(Path(arguments.recipe)))
    except (OSError, ValueError, yaml.YAMLError) as error:
        # pydantic.ValidationError is a ValueError; its message names every failing field.
        sys.stderr.write(f"swm: cannot read {arguments.recipe}:\n{_describe(error)}\n")
        return EXIT_FAILED
    try:
        COMMANDS[arguments.command](resolution, arguments)
    except CommandError as error:
        sys.stderr.write(f"swm {arguments.command}: {error}\n")
        return EXIT_FAILED
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
    lines += [
        f"  - {status.feature}: {status.arrival}" + (f" ({status.note})" if status.note else "")
        for status in unbuilt
    ] or ["  none"]
    return "\n".join(lines) + "\n"


def _resolve_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    recipe = resolution.recipe
    out_dir = Path(arguments.out_dir)
    write_resolved_recipe(recipe, out_dir)
    write_stream_record(stream_record(recipe.root_seed, recipe.terrain.terrain_seed), out_dir)


def _check_recipe_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    sys.stdout.write(check_report(resolution))


def _terrain_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    result = _terrain(resolution)
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(statistics_record(result), out_dir / TERRAIN_STATS_FILE)
    write_hash_list(array_hashes(result), out_dir / TERRAIN_HASHES_FILE)


def _preview_terrain_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    try:
        from swm.preview import terrain_preview_png
    except ImportError as error:
        raise CommandError(
            "the preview needs matplotlib; install it with: uv sync --extra preview"
        ) from error
    result = _terrain(resolution)
    title = f"{Path(arguments.recipe).name}: {resolution.recipe.terrain.map_type}"
    write_binary(terrain_preview_png(result, title), Path(arguments.output))


def _layers_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    terrain = _terrain(resolution)
    result = _layers(resolution, terrain)
    out_dir = Path(arguments.out_dir)
    nodes = canonical_yaml({"nodes": layers_stage.node_table(result)})
    links = canonical_yaml({"links": layers_stage.link_table(result)})
    write_canonical_yaml(layers_stage.statistics_record(result), out_dir / LAYERS_STATS_FILE)
    write_binary(nodes, out_dir / LAYERS_NODES_FILE)
    write_binary(links, out_dir / LAYERS_LINKS_FILE)
    hashes = [
        (LAYERS_NODES_FILE, hashlib.sha256(nodes).hexdigest()),
        (LAYERS_LINKS_FILE, hashlib.sha256(links).hexdigest()),
    ]
    write_hash_list(hashes, out_dir / LAYERS_HASHES_FILE)
    for stats in result.statistics:
        for note in stats.notes:
            sys.stdout.write(f"{stats.layer}: {note}\n")


def _export_gis_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    try:
        from swm.manifest.inspection import export_gis
    except ImportError as error:
        raise CommandError(
            "the export needs pyogrio, shapely and rasterio; install them with: "
            "uv sync --extra export"
        ) from error
    terrain = _terrain(resolution)
    for path in export_gis(terrain, _layers(resolution, terrain), Path(arguments.out_dir)):
        sys.stdout.write(f"{path}\n")


def _preview_world_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    try:
        from swm.preview import world_preview_png
    except ImportError as error:
        raise CommandError(
            "the preview needs matplotlib; install it with: uv sync --extra preview"
        ) from error
    terrain = _terrain(resolution)
    result = _layers(resolution, terrain)
    title = f"{Path(arguments.recipe).name}: {resolution.recipe.terrain.map_type} with its layers"
    write_binary(world_preview_png(terrain, result, title), Path(arguments.output))


def _layers(resolution: Resolution, terrain: TerrainResult) -> LayersResult:
    recipe = resolution.recipe
    try:
        return build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed))
    except ValueError as error:
        raise CommandError(str(error)) from error


def _terrain(resolution: Resolution) -> TerrainResult:
    recipe = resolution.recipe
    try:
        streams = terrain_streams(recipe.root_seed, recipe.terrain.terrain_seed)
        return build_terrain(recipe.terrain, streams)
    except ValueError as error:
        raise CommandError(str(error)) from error


COMMANDS: dict[str, Callable[[Resolution, argparse.Namespace], None]] = {
    "resolve": _resolve_command,
    "check-recipe": _check_recipe_command,
    "terrain": _terrain_command,
    "preview-terrain": _preview_terrain_command,
    "layers": _layers_command,
    "export-gis": _export_gis_command,
    "preview-world": _preview_world_command,
}


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
    terrain_command = commands.add_parser(
        "terrain", help="build the terrain; write its statistics and array hashes"
    )
    terrain_command.add_argument("recipe", help="recipe YAML file")
    terrain_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    preview_command = commands.add_parser(
        "preview-terrain", help="render a shaded map of the terrain as PNG"
    )
    preview_command.add_argument("recipe", help="recipe YAML file")
    preview_command.add_argument("-o", "--output", required=True, help="PNG file to write")
    layers_command = commands.add_parser(
        "layers", help="site the layers; write their statistics, node and link tables and hashes"
    )
    layers_command.add_argument("recipe", help="recipe YAML file")
    layers_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    export_command = commands.add_parser(
        "export-gis", help="write world.gpkg and GeoTIFFs in EPSG:32710 for inspection"
    )
    export_command.add_argument("recipe", help="recipe YAML file")
    export_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    world_command = commands.add_parser(
        "preview-world", help="render the terrain with every node and link as PNG"
    )
    world_command.add_argument("recipe", help="recipe YAML file")
    world_command.add_argument("-o", "--output", required=True, help="PNG file to write")
    return parser


def _describe(error: Exception) -> str:
    if isinstance(error, pydantic.ValidationError):
        return "\n".join(
            f"  {'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
    return f"  {error}"
