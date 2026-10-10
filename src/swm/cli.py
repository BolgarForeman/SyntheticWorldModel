"""Command-line entry point for the ``swm`` command."""

import argparse
import hashlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import pydantic
import yaml

from swm import __version__
from swm.checks.calm import calm_world_problems
from swm.checks.signature import link_signature_problems
from swm.checks.undisturbed import undisturbed_supply_check
from swm.recipe.buildability import unbuilt_features
from swm.recipe.io import (
    canonical_yaml,
    load_recipe,
    write_binary,
    write_canonical_yaml,
    write_csv,
    write_hash_list,
    write_resolved_recipe,
    write_stream_record,
)
from swm.recipe.resolve import Resolution, resolve
from swm.rng import stream_record
from swm.rules.page import rules_page_html
from swm.rules.registry import Registry, load_registry
from swm.rules.theta import theta_text
from swm.stages import buffers as buffers_stage
from swm.stages import couplings as couplings_stage
from swm.stages import crews as crews_stage
from swm.stages import layers as layers_stage
from swm.stages import repair as repair_stage
from swm.stages import requirements as requirements_stage
from swm.stages import scenarios as scenarios_stage
from swm.stages import storm as storm_stage
from swm.stages import strength as strength_stage
from swm.stages.buffers import buffers_streams, build_buffers
from swm.stages.couplings import CouplingsResult, build_couplings, couplings_streams
from swm.stages.crews import build_crews
from swm.stages.layers import LayersResult, build_layers, layers_streams
from swm.stages.repair import build_repair, repair_streams
from swm.stages.requirements import RequirementsResult, build_requirements, requirements_streams
from swm.stages.scenarios import build_scenarios, scenarios_streams
from swm.stages.storm import StormResult, build_storm, storm_streams
from swm.stages.strength import StrengthResult, build_strength
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
REQUIREMENTS_STATS_FILE = "requirements_stats.yaml"
BUFFERS_STATS_FILE = "buffers_stats.yaml"
BUFFERS_HASHES_FILE = "buffers_sha256.txt"
STRENGTH_STATS_FILE = "strength_stats.yaml"
STRENGTH_HASHES_FILE = "strength_sha256.txt"
REPAIR_STATS_FILE = "repair_stats.yaml"
REPAIR_HASHES_FILE = "repair_sha256.txt"
STORM_STATS_FILE = "storm_stats.yaml"
STORM_FACILITIES_FILE = "storm_facilities.yaml"
STORM_HASHES_FILE = "storm_sha256.txt"
SCENARIOS_STATS_FILE = "scenarios_stats.yaml"
SCENARIOS_HASHES_FILE = "scenarios_sha256.txt"
REQUIREMENTS_HASHES_FILE = "requirements_sha256.txt"
COUPLINGS_STATS_FILE = "couplings_stats.yaml"
COUPLINGS_HASHES_FILE = "couplings_sha256.txt"
COUPLINGS_EDGES_CSV = "couplings_edges.csv"


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
    if arguments.command == "rules":
        if arguments.theta:
            # UTF-8 bytes, not the console's code page: the list must read the same everywhere.
            sys.stdout.flush()
            sys.stdout.buffer.write(theta_text(load_registry()).encode("utf-8"))
        else:
            write_binary(rules_page_html(load_registry()), Path(arguments.output))
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
    _check_signature(result)
    out_dir = Path(arguments.out_dir)
    nodes = canonical_yaml({"nodes": layers_stage.node_table(result)})
    links = canonical_yaml(
        {
            "links": layers_stage.link_table(result),
            "power_lines": layers_stage.power_line_table(result),
        }
    )
    write_canonical_yaml(
        _stamped(layers_stage.statistics_record(result), resolution), out_dir / LAYERS_STATS_FILE
    )
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


def _requirements_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    terrain = _terrain(resolution)
    result = _requirements(resolution, terrain)
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(
        _stamped(requirements_stage.statistics_record(result), resolution),
        out_dir / REQUIREMENTS_STATS_FILE,
    )
    table = canonical_yaml({"requirements": requirements_stage.requirement_table(result)})
    write_hash_list(
        [("requirements", hashlib.sha256(table).hexdigest())], out_dir / REQUIREMENTS_HASHES_FILE
    )
    for note in result.notes:
        sys.stdout.write(f"requirements: {note}\n")


def _couplings_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    layers = requirements.layers
    result = _couplings(resolution, terrain, requirements)
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(
        _stamped(couplings_stage.statistics_record(result), resolution),
        out_dir / COUPLINGS_STATS_FILE,
    )
    tables = {
        "edges": canonical_yaml({"edges": couplings_stage.edge_table(result)}),
        "dependencies": canonical_yaml({"dependencies": couplings_stage.dependency_table(result)}),
    }
    hashes = [(name, hashlib.sha256(table).hexdigest()) for name, table in tables.items()]
    write_hash_list(hashes, out_dir / COUPLINGS_HASHES_FILE)
    # For inspection only, outside the identity check (decision 0008, review 3).
    write_csv(
        couplings_stage.switched_on_edge_summary(result, layers), out_dir / COUPLINGS_EDGES_CSV
    )
    sys.stdout.write(
        f"total edges {result.total_edges}: {result.intra_layer_links} intra-layer links and "
        f"{result.switched_on_edges} switched-on coupling edges "
        f"({len(result.edges)} coupling edges in all)\n"
    )


def _preview_couplings_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    try:
        from swm.preview import couplings_preview_png
    except ImportError as error:
        raise CommandError(
            "the preview needs matplotlib; install it with: uv sync --extra preview"
        ) from error
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    layers = requirements.layers
    result = _couplings(resolution, terrain, requirements)
    title = f"{Path(arguments.recipe).name}: couplings"
    write_binary(couplings_preview_png(layers, result, title), Path(arguments.output))


def _export_gis_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    try:
        from swm.manifest.inspection import export_gis
    except ImportError as error:
        raise CommandError(
            "the export needs pyogrio, shapely and rasterio; install them with: "
            "uv sync --extra export"
        ) from error
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    layers = requirements.layers
    couplings = _couplings(resolution, terrain, requirements)
    stamp = _rules_stamp(resolution)
    for path in export_gis(terrain, layers, couplings, Path(arguments.out_dir), stamp):
        sys.stdout.write(f"{path}\n")


def _preview_world_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    try:
        from swm.preview import world_preview_png
    except ImportError as error:
        raise CommandError(
            "the preview needs matplotlib; install it with: uv sync --extra preview"
        ) from error
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    result = requirements.layers
    couplings = None if arguments.no_couplings else _couplings(resolution, terrain, requirements)
    title = f"{Path(arguments.recipe).name}: {resolution.recipe.terrain.map_type} with its layers"
    write_binary(world_preview_png(terrain, result, title, couplings), Path(arguments.output))


def _layers(resolution: Resolution, terrain: TerrainResult) -> LayersResult:
    """Return the layers as they stand once power is sized to load (decision 0010)."""
    return _requirements(resolution, terrain).layers


def _drawn_layers(resolution: Resolution, terrain: TerrainResult) -> LayersResult:
    recipe = resolution.recipe
    try:
        return build_layers(
            recipe.layers, terrain, layers_streams(recipe.root_seed), _rules(resolution)
        )
    except ValueError as error:
        raise CommandError(str(error)) from error


def _requirements(resolution: Resolution, terrain: TerrainResult) -> RequirementsResult:
    recipe = resolution.recipe
    return build_requirements(
        recipe.unobserved.requirements,
        _drawn_layers(resolution, terrain),
        _rules(resolution),
        requirements_streams(recipe.root_seed),
        recipe.couplings.distribution_voltage_kv,
    )


def _buffers_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    recipe = resolution.recipe
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    couplings = _couplings(resolution, terrain, requirements)
    result = build_buffers(
        recipe.unobserved.reserves,
        recipe.unobserved.failure_mode,
        requirements.layers,
        requirements,
        couplings,
        _rules(resolution),
        buffers_streams(recipe.root_seed),
    )
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(
        _stamped(buffers_stage.statistics_record(result), resolution),
        out_dir / BUFFERS_STATS_FILE,
    )
    tables = buffers_stage.buffer_tables(result)
    hashes = [
        (name, hashlib.sha256(canonical_yaml({name: rows})).hexdigest())
        for name, rows in tables.items()
    ]
    write_hash_list(hashes, out_dir / BUFFERS_HASHES_FILE)
    for note in result.notes:
        sys.stdout.write(f"buffers: {note}\n")


def _strength_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    result = _strength(resolution)
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(
        _stamped(strength_stage.statistics_record(result), resolution),
        out_dir / STRENGTH_STATS_FILE,
    )
    tables = strength_stage.strength_tables(result)
    hashes = [
        (name, hashlib.sha256(canonical_yaml({name: rows})).hexdigest())
        for name, rows in tables.items()
    ]
    write_hash_list(hashes, out_dir / STRENGTH_HASHES_FILE)
    _check_supply(result)


def _repair_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    recipe = resolution.recipe
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    couplings = _couplings(resolution, terrain, requirements)
    rules = _rules(resolution)
    try:
        crews = build_crews(recipe.unobserved, terrain, requirements.layers)
    except ValueError as error:
        raise CommandError(str(error)) from error
    result = build_repair(
        recipe.unobserved.repair_rates,
        crews,
        terrain,
        requirements.layers,
        requirements,
        couplings,
        rules,
        repair_streams(recipe.root_seed),
    )
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(
        _stamped(repair_stage.statistics_record(result, crews), resolution),
        out_dir / REPAIR_STATS_FILE,
    )
    tables = crews_stage.crews_tables(crews) | repair_stage.repair_tables(result)
    hashes = [
        (name, hashlib.sha256(canonical_yaml({name: rows})).hexdigest())
        for name, rows in tables.items()
    ]
    write_hash_list(hashes, out_dir / REPAIR_HASHES_FILE)
    for note in result.notes:
        sys.stdout.write(f"repair: {note}\n")


def _storm(resolution: Resolution, terrain: TerrainResult) -> StormResult:
    recipe = resolution.recipe
    shared = recipe.shared_causes
    return build_storm(
        shared.hazards.storm_corridor,
        shared.scenarios,
        recipe.terrain.character.mountainous,
        terrain,
        _rules(resolution),
        storm_streams(recipe.root_seed, shared.scenarios),
    )


def _storm_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    shared = resolution.recipe.shared_causes
    terrain = _terrain(resolution)
    layers = _drawn_layers(resolution, terrain)
    rules = _rules(resolution)
    result = _storm(resolution, terrain)
    exposure = storm_stage.facility_exposure(result, layers, rules)
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(
        _stamped(storm_stage.statistics_record(result, exposure), resolution),
        out_dir / STORM_STATS_FILE,
    )
    write_canonical_yaml(
        {"facilities": storm_stage.exposure_table(exposure)}, out_dir / STORM_FACILITIES_FILE
    )
    write_hash_list(storm_stage.storm_hashes(result), out_dir / STORM_HASHES_FILE)
    if arguments.scenario is None:
        return
    if not 0 <= arguments.scenario < shared.scenarios:
        raise CommandError(
            f"--scenario {arguments.scenario}: the recipe draws scenarios 0 to "
            f"{shared.scenarios - 1}"
        )
    try:
        from swm.preview import storm_preview_png
    except ImportError as error:
        raise CommandError(
            "the preview needs matplotlib; install it with: uv sync --extra preview"
        ) from error
    title = f"{Path(arguments.recipe).name}: storm scenario {arguments.scenario}"
    couplings = _couplings(resolution, terrain, _requirements(resolution, terrain))
    feeds = [edge.route for edge in couplings.edges if edge.route]
    png = storm_preview_png(terrain, layers, result, arguments.scenario, title, feeds)
    write_binary(png, out_dir / f"storm_scenario_{arguments.scenario}.png")


def _scenarios_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    recipe = resolution.recipe
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    couplings = _couplings(resolution, terrain, requirements)
    storm = _storm(resolution, terrain)
    result = build_scenarios(
        recipe.shared_causes.facility_damage_cap,
        storm,
        terrain,
        requirements.layers,
        couplings,
        _rules(resolution),
        scenarios_streams(recipe.root_seed, recipe.shared_causes.scenarios),
    )
    out_dir = Path(arguments.out_dir)
    write_canonical_yaml(
        _stamped(scenarios_stage.statistics_record(result), resolution),
        out_dir / SCENARIOS_STATS_FILE,
    )
    hashes = [
        (name, hashlib.sha256(canonical_yaml({name: rows})).hexdigest())
        for name, rows in scenarios_stage.scenarios_tables(result).items()
    ]
    write_hash_list(hashes, out_dir / SCENARIOS_HASHES_FILE)
    problems = calm_world_problems(storm, result)
    if problems:
        raise CommandError("calm world check:\n" + "\n".join(problems))
    for scenario in result.scenarios:
        sys.stdout.write(
            f"scenario {scenario.index}: {len(scenario.failed_lines)} lines down, "
            f"{len(scenario.facilities)} facilities damaged\n"
        )


def _check_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    _check_signature(requirements.layers)
    couplings = _couplings(resolution, terrain, requirements)
    rules = _rules(resolution)
    _check_supply(build_strength(requirements.layers, requirements, couplings, rules))


def _check_signature(layers: LayersResult) -> None:
    """Report the link-signature check; a world with a forbidden link stops the build (0.1)."""
    problems = link_signature_problems(layers)
    if problems:
        raise CommandError("link signature check:\n" + "\n".join(problems))
    sys.stdout.write("link signature: every link joins classes its layer allows\n")


def _check_supply(result: StrengthResult) -> None:
    """Report the undisturbed-supply check; a world that fails it stops the build (E2)."""
    check = undisturbed_supply_check(result)
    if not check.passed:
        raise CommandError(check.report().rstrip("\n"))
    sys.stdout.write(check.report())


def _strength(resolution: Resolution) -> StrengthResult:
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    couplings = _couplings(resolution, terrain, requirements)
    return build_strength(requirements.layers, requirements, couplings, _rules(resolution))


def _couplings(
    resolution: Resolution, terrain: TerrainResult, requirements: RequirementsResult
) -> CouplingsResult:
    recipe = resolution.recipe
    return build_couplings(
        recipe.couplings,
        recipe.dynamics.transfer_forms,
        terrain,
        requirements.layers,
        requirements,
        _rules(resolution),
        couplings_streams(recipe.root_seed),
    )


def _rules(resolution: Resolution) -> Registry:
    """Return the registry with the recipe's overrides applied (Work Order 5, A3)."""
    return load_registry().with_overrides(resolution.recipe.modeling_rules.overrides)


def _rules_stamp(resolution: Resolution) -> dict[str, object]:
    """Return the θ* record stamped on every world.

    The registry and its overrides, the relaxed limits and the removed dependencies (Work
    Order 7, B3 and C4).
    """
    rules = resolution.recipe.modeling_rules
    return {
        "registry_version": rules.registry_version,
        "registry_sha256": rules.registry_sha256,
        "overrides": dict(rules.overrides),
        "relaxed_limits": list(rules.relaxed_limits),
        "removed_dependencies": list(resolution.recipe.dynamics.removed_dependencies),
    }


def _stamped(record: dict[str, object], resolution: Resolution) -> dict[str, object]:
    """Put the modeling rules that built the world at the head of a stage's statistics."""
    return {"modeling_rules": _rules_stamp(resolution), **record}


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
    "requirements": _requirements_command,
    "couplings": _couplings_command,
    "buffers": _buffers_command,
    "strength": _strength_command,
    "repair": _repair_command,
    "storm": _storm_command,
    "scenarios": _scenarios_command,
    "check": _check_command,
    "preview-couplings": _preview_couplings_command,
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
    buffers_command = commands.add_parser(
        "buffers", help="draw reserves, backup, tolerance and failure modes; write statistics"
    )
    buffers_command.add_argument("recipe", help="recipe YAML file")
    buffers_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    strength_command = commands.add_parser(
        "strength", help="derive coupling strength; write statistics and run the supply check"
    )
    strength_command.add_argument("recipe", help="recipe YAML file")
    strength_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    repair_command = commands.add_parser(
        "repair", help="site crew bases; record travel, permanent and emergency repair"
    )
    repair_command.add_argument("recipe", help="recipe YAML file")
    repair_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    storm_command = commands.add_parser(
        "storm", help="build the storm's wind and flood per scenario; write statistics"
    )
    storm_command.add_argument("recipe", help="recipe YAML file")
    storm_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    scenarios_command = commands.add_parser(
        "scenarios", help="draw what each storm scenario damages; write statistics"
    )
    scenarios_command.add_argument("recipe", help="recipe YAML file")
    scenarios_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    storm_command.add_argument(
        "--scenario",
        type=int,
        default=None,
        help="also render this scenario's preview PNG (needs the preview extra)",
    )
    world_check = commands.add_parser(
        "check", help="run the world checks: every consumer supplied before any disruption"
    )
    world_check.add_argument("recipe", help="recipe YAML file")
    requirements_command = commands.add_parser(
        "requirements", help="draw the requirements; write their statistics and table hash"
    )
    requirements_command.add_argument("recipe", help="recipe YAML file")
    requirements_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    rules_command = commands.add_parser(
        "rules", help="render the modeling rules registry as one HTML page, or print Theta"
    )
    rules_output = rules_command.add_mutually_exclusive_group(required=True)
    rules_output.add_argument("-o", "--output", help="HTML file to write")
    rules_output.add_argument(
        "--theta", action="store_true", help="print the Theta List (θ*) and the objectives"
    )
    couplings_command = commands.add_parser(
        "couplings", help="build the couplings; write their statistics and table hashes"
    )
    couplings_command.add_argument("recipe", help="recipe YAML file")
    couplings_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    schematic_command = commands.add_parser(
        "preview-couplings", help="render the couplings as a schematic PNG for the hand trace"
    )
    schematic_command.add_argument("recipe", help="recipe YAML file")
    schematic_command.add_argument("-o", "--output", required=True, help="PNG file to write")
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
    world_command.add_argument(
        "--no-couplings", action="store_true", help="leave the coupling edges off the map"
    )
    return parser


def _describe(error: Exception) -> str:
    if isinstance(error, pydantic.ValidationError):
        return "\n".join(
            f"  {'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
    return f"  {error}"
