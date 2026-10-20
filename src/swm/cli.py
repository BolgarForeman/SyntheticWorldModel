"""Command-line entry point for the ``swm`` command."""

import argparse
import hashlib
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import pydantic
import yaml

from swm import __version__
from swm.checks.calm import calm_world_problems
from swm.checks.dynamics import calm_run_problems
from swm.checks.signature import link_signature_problems
from swm.checks.undisturbed import undisturbed_supply_check
from swm.dynamics.engine import simulate
from swm.dynamics.output import crew_rows, run_record, state_rows, stock_rows, trajectory_text
from swm.dynamics.records import RunRequest
from swm.dynamics.travel import RoadLegs
from swm.dynamics.world import Damage, EngineWorld, StageOutputs, failure_points, world_from_stages
from swm.emit.observed import ObservedWorld
from swm.emit.sources import EmittedSources, emit_sources
from swm.manifest.truth import TruthInputs, truth_manifest
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
from swm.recipe.schema import RECORDED_NOT_APPLIED, errors_above_zero
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
from swm.stages.buffers import BuffersResult, buffers_streams, build_buffers
from swm.stages.couplings import CouplingsResult, build_couplings, couplings_streams
from swm.stages.crews import CrewsResult, build_crews
from swm.stages.emission import build_observed
from swm.stages.layers import LayersResult, build_layers, layers_streams
from swm.stages.repair import RepairResult, build_repair, repair_streams
from swm.stages.requirements import RequirementsResult, build_requirements, requirements_streams
from swm.stages.scenarios import ScenariosResult, build_scenarios, scenarios_streams
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
TRACE_SCENARIO = 7
"""The pilot's restorative-model scenario, the hand trace's default (Pilot Spec v0.7)."""
TRACE_PACK_DIR = "trace_pack"
BOARD_SIZES = ("11x17", "tiled-letter", "24x36", "36x48")
"""The trace game's board sizes, the first the default (WO 9, H1)."""
TRUTH_FILE = "truth/manifest.yaml"
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
    out = Path(arguments.out_dir)
    rules = _rules(resolution)
    root = resolution.recipe.root_seed
    for path in export_gis(terrain, layers, couplings, out, stamp, rules, root):
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


@dataclass(frozen=True)
class _Built:
    """Every stage of one world, built once."""

    rules: Registry
    terrain: TerrainResult
    requirements: RequirementsResult
    couplings: CouplingsResult
    strength: StrengthResult
    buffers: BuffersResult
    crews: CrewsResult
    repair: RepairResult
    storm: StormResult
    scenarios: ScenariosResult


def _built(resolution: Resolution) -> _Built:
    """Build every stage of the world, from the terrain to the scenarios."""
    recipe = resolution.recipe
    rules = _rules(resolution)
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    layers = requirements.layers
    couplings = _couplings(resolution, terrain, requirements)
    strength = build_strength(layers, requirements, couplings, rules)
    buffers = build_buffers(
        recipe.unobserved.reserves, recipe.unobserved.failure_mode, layers, requirements,
        couplings, rules, buffers_streams(recipe.root_seed),
    )  # fmt: skip
    try:
        crews = build_crews(recipe.unobserved, terrain, layers)
    except ValueError as error:
        raise CommandError(str(error)) from error
    repair = build_repair(
        recipe.unobserved.repair_rates, crews, terrain, layers, requirements, couplings, rules,
        repair_streams(recipe.root_seed),
    )  # fmt: skip
    storm = _storm(resolution, terrain)
    scenarios = build_scenarios(
        recipe.shared_causes.facility_damage_cap, storm, terrain, layers, couplings, rules,
        scenarios_streams(recipe.root_seed, recipe.shared_causes.scenarios),
    )  # fmt: skip
    return _Built(rules, terrain, requirements, couplings, strength, buffers, crews, repair,
                  storm, scenarios)  # fmt: skip


@dataclass(frozen=True)
class _Engine:
    """The engine's world, and each scenario's damage, built from the stages."""

    world: EngineWorld
    damage: tuple[Damage, ...]
    end_use: tuple[str, ...]


def _engine(resolution: Resolution, built: _Built | None = None) -> _Engine:
    """Assemble the engine's world from the stages (Work Order 7, D1)."""
    b = built or _built(resolution)
    layers = b.requirements.layers
    stages = StageOutputs(layers, b.requirements, b.couplings, b.strength, b.buffers, b.crews,
                          b.repair, b.scenarios.lines, b.terrain.grid)  # fmt: skip
    world = replace(world_from_stages(stages, b.rules), legs=RoadLegs.of(b.terrain, layers))
    damage = tuple(
        Damage(
            nodes=tuple(sorted(f.node_id for f in scenario.facilities)),
            lines=tuple(sorted(o.line_id for o in scenario.failed_lines)),
            failure_points=failure_points(scenario.lines, b.scenarios.lines),
        )
        for scenario in b.scenarios.scenarios
    )
    end_use = tuple(n.node_id for n in world.nodes if n.end_use_weight is not None)
    return _Engine(world, damage, end_use)


def _observed(resolution: Resolution, built: _Built) -> ObservedWorld:
    recipe = resolution.recipe
    return build_observed(recipe.layers, built.terrain, built.requirements.layers, built.rules,
                          recipe.root_seed)  # fmt: skip


def _warn_errors_not_applied(resolution: Resolution) -> None:
    """Print one warning naming every source whose error settings Phase 1 does not apply (C2)."""
    sources = errors_above_zero(resolution.recipe.errors)
    if sources:
        sys.stderr.write(f"warning: {RECORDED_NOT_APPLIED}: {', '.join(sources)}\n")


def _emit_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    _warn_errors_not_applied(resolution)
    built = _built(resolution)
    _write_sources(emit_sources(_observed(resolution, built)), Path(arguments.out_dir))


def _write_sources(emitted: EmittedSources, out_dir: Path) -> None:
    for path, body in emitted.files.items():
        write_binary(body, out_dir / path)


def _trace_pack_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    built = _built(resolution)
    _write_trace_pack(
        resolution, built, arguments.scenario, Path(arguments.out_dir), arguments.board_size
    )


def _write_trace_pack(
    resolution: Resolution, built: _Built, scenario: int, out_dir: Path, board_size: str
) -> None:
    """Write the trace game for one scenario: game, sealed answer and data (WO 9, A and H)."""
    try:
        from swm.trace_game.drills import DrillError
        from swm.trace_game.pack import trace_game
        from swm.trace_pack import COLUMNS, TraceInputs, trace_pack
    except ImportError as error:  # pragma: no cover - the preview extra is installed in CI
        raise CommandError(
            "the trace pack needs the preview extra: uv sync --extra preview"
        ) from error
    engine = _engine(resolution, built)
    if not 0 <= scenario < len(engine.damage):
        raise CommandError(f"scenario {scenario} is not among the {len(engine.damage)} drawn")
    run = simulate(engine.world, RunRequest(engine.damage[scenario], scenario=scenario))
    inputs = TraceInputs(
        scenario, built.terrain, built.requirements.layers, built.requirements, built.couplings,
        built.strength, built.buffers, built.crews, built.repair,
        built.storm.scenarios[scenario], built.scenarios.scenarios[scenario],
        built.scenarios.lines, engine.world, engine.damage[scenario], built.rules, run,
    )  # fmt: skip
    pack = trace_pack(inputs)
    try:
        game = trace_game(inputs, board_size)
    except DrillError as error:
        raise CommandError(str(error)) from error
    # What a player gets; the sealed answer; PR 9a's tables as the data appendix (WO 9, H1).
    folder = out_dir / TRACE_PACK_DIR
    for name, body in game.game.items():
        write_binary(body, folder / "game" / name)
    for name, body in game.answer.items():
        write_binary(body, folder / "answer" / name)
    for name, rows in game.answer_tables.items():
        write_csv(rows, folder / "answer" / f"{name}.csv")
    write_binary(pack.answer_pdf, folder / "answer" / "timeline.pdf")
    for name, rows in pack.answer.items():
        write_csv(rows, folder / "answer" / f"{name}.csv")
    data = folder / "data"
    write_binary(pack.map_pdf, data / "map.pdf")
    write_binary(pack.rules_pdf, data / "rules.pdf")
    write_binary(pack.tables_pdf, data / "tables.pdf")
    for name, rows in pack.tables.items():
        write_csv(rows, data / f"{name}.csv", COLUMNS.get(name, ()))


def _build_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    """Write the world's full tree: resolved recipe, sources, truth and trace pack (E1)."""
    out_dir = Path(arguments.out_dir)
    _warn_errors_not_applied(resolution)
    built = _built(resolution)
    write_resolved_recipe(resolution.recipe, out_dir)
    observed = _observed(resolution, built)
    emitted = emit_sources(observed)
    _write_sources(emitted, out_dir)
    recipe = resolution.recipe
    streams = stream_record(recipe.root_seed, recipe.terrain.terrain_seed)
    manifest = truth_manifest(TruthInputs(
        recipe, built.rules, built.requirements.layers, built.requirements, built.couplings,
        built.strength, built.buffers, built.crews, built.repair, observed, emitted, streams,
    ))  # fmt: skip
    write_canonical_yaml(_stamped(manifest, resolution), out_dir / TRUTH_FILE)
    _write_trace_pack(resolution, built, arguments.scenario, out_dir, arguments.board_size)
    sys.stdout.write(f"{len(emitted.files)} source files, the truth manifest and the trace pack\n")


def _request(
    resolution: Resolution, engine: _Engine, scenario: int, arguments: argparse.Namespace
) -> RunRequest:
    recipe = resolution.recipe
    if not 0 <= scenario < len(engine.damage):
        raise CommandError(f"scenario {scenario} is not among the {len(engine.damage)} drawn")
    relaxed = set(recipe.modeling_rules.relaxed_limits) | set(arguments.relax or ())
    registry = _rules(resolution)
    for rule_id in sorted(relaxed):
        if not registry.has(rule_id) or not registry.rule(rule_id).is_limit:
            raise CommandError(f"--relax {rule_id}: not a limit in the registry")
    return RunRequest(
        damage=engine.damage[scenario],
        horizon_h=arguments.horizon,
        relaxed=frozenset(relaxed),
        removed=recipe.dynamics.removed_dependencies,
        scenario=scenario,
    )


def _simulate_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    engine = _engine(resolution)
    indices = range(len(engine.damage)) if arguments.scenario is None else [arguments.scenario]
    stamp = _rules_stamp(resolution)
    for index in indices:
        try:
            run = simulate(engine.world, _request(resolution, engine, index, arguments))
        except ValueError as error:
            raise CommandError(str(error)) from error
        if arguments.scenario is not None:
            sys.stdout.write(trajectory_text(run, engine.end_use, arguments.node))
        if arguments.out_dir:
            out_dir = Path(arguments.out_dir)
            write_canonical_yaml(run_record(run, stamp), out_dir / f"run_{index}.yaml")
            write_csv(state_rows(run), out_dir / f"run_{index}_states.csv")
            write_csv(stock_rows(run), out_dir / f"run_{index}_stocks.csv")
            write_csv(crew_rows(run), out_dir / f"run_{index}_crews.csv")
        if arguments.plot:
            from swm.preview import timeline_png

            write_binary(timeline_png(run, engine.end_use), Path(arguments.plot))
        summary = run.summary()
        sys.stdout.write(
            f"scenario {index}: {summary['hours_out']} hours out; longest "
            f"{summary['longest_out']}; last repair {summary['last_repair_h']} h; most passes "
            f"{summary['most_passes']}\n"
        )


def _check_command(resolution: Resolution, arguments: argparse.Namespace) -> None:
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    _check_signature(requirements.layers)
    couplings = _couplings(resolution, terrain, requirements)
    rules = _rules(resolution)
    _check_supply(build_strength(requirements.layers, requirements, couplings, rules))
    engine = _engine(resolution)
    problems = calm_run_problems(engine.world)
    if problems:
        raise CommandError("calm-world run:\n" + "\n".join(problems))
    sys.stdout.write("calm-world run: every node holds 1 and nothing moves for the horizon\n")


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
        "out_of_range": list(rules.out_of_range),
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
    "simulate": _simulate_command,
    "emit": _emit_command,
    "build": _build_command,
    "trace-pack": _trace_pack_command,
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
    simulate_command = commands.add_parser(
        "simulate", help="play storm scenarios out over time; print, save and plot the runs"
    )
    simulate_command.add_argument("recipe", help="recipe YAML file")
    simulate_command.add_argument(
        "--scenario", type=int, default=None, help="one scenario (default: every scenario)"
    )
    simulate_command.add_argument("--horizon", type=float, default=None, help="hours to run")
    simulate_command.add_argument(
        "--relax", action="append", help="relax a limit by rule id (repeatable)"
    )
    simulate_command.add_argument("--node", default=None, help="print one node in full")
    simulate_command.add_argument("-o", "--out-dir", default=None, help="write the run files")
    simulate_command.add_argument("--plot", default=None, help="timeline PNG to write")
    emit_command = commands.add_parser("emit", help="write the world's source files, sources/")
    emit_command.add_argument("recipe", help="recipe YAML file")
    emit_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    build_command = commands.add_parser(
        "build", help="write the world's full tree: resolved recipe, sources, truth, trace pack"
    )
    build_command.add_argument("recipe", help="recipe YAML file")
    build_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    build_command.add_argument(
        "--scenario", type=int, default=TRACE_SCENARIO, help="the trace pack's scenario (7)"
    )
    build_command.add_argument(
        "--board-size", choices=BOARD_SIZES, default=BOARD_SIZES[0], help="the game board's size"
    )
    pack_command = commands.add_parser(
        "trace-pack", help="write the printable hand-trace pack for one scenario"
    )
    pack_command.add_argument("recipe", help="recipe YAML file")
    pack_command.add_argument("-o", "--out-dir", required=True, help="output folder")
    pack_command.add_argument(
        "--scenario", type=int, default=TRACE_SCENARIO, help="the scenario (default 7)"
    )
    pack_command.add_argument(
        "--board-size",
        choices=BOARD_SIZES,
        default=BOARD_SIZES[0],
        help="the game board's size: 11x17 (default), tiled-letter, 24x36 or 36x48",
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
