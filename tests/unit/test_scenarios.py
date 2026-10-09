import functools
import itertools
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from swm import rng
from swm.checks.calm import calm_world_problems
from swm.cli import _couplings, _requirements, _rules, _storm, _terrain, main
from swm.recipe.io import load_recipe
from swm.recipe.resolve import Resolution, resolve
from swm.recipe.schema import DamageState, Layer, NodeClass
from swm.rules.registry import load_registry
from swm.stages import scenarios as stage
from swm.stages.repair import build_repair, repair_streams
from swm.stages.scenarios import (
    LineKind,
    ScenariosResult,
    Structure,
    build_scenarios,
    overhead_lines,
    scenarios_streams,
)

RULES = load_registry()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PILOT = FIXTURES / "pilot_hand_check.yaml"
SEVERITY_70 = FIXTURES / "storm_sensitivity" / "pilot_severity_70.yaml"


@functools.cache
def pipeline(path: Path = PILOT, severity: int | None = None, scenarios: int | None = None) -> Any:
    """Resolve a recipe and build what the scenarios stage reads, then the scenarios."""
    recipe = load_recipe(path)
    shared = recipe.shared_causes
    if severity is not None or scenarios is not None:
        storm = shared.hazards.storm_corridor.model_copy(
            update={
                "severity": shared.hazards.storm_corridor.severity if severity is None else severity
            }
        )
        hazards = shared.hazards.model_copy(update={"storm_corridor": storm})
        shared = shared.model_copy(
            update={"hazards": hazards, "scenarios": scenarios or shared.scenarios}
        )
        recipe = recipe.model_copy(update={"shared_causes": shared})
    resolution: Resolution = resolve(recipe)
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    couplings = _couplings(resolution, terrain, requirements)
    storm = _storm(resolution, terrain)
    result = build_scenarios(
        resolution.recipe.shared_causes.facility_damage_cap,
        storm,
        terrain,
        requirements.layers,
        couplings,
        _rules(resolution),
        scenarios_streams(resolution.recipe.root_seed, resolution.recipe.shared_causes.scenarios),
    )
    return resolution, terrain, requirements, couplings, storm, result


# --- Fragility tables (D1) ------------------------------------------------------------------


def _lognormal(gust: float, median: float, beta: float) -> float:
    if gust <= 0.0:
        return 0.0
    return 0.5 * (1.0 + math.erf(math.log(gust / median) / beta / math.sqrt(2.0)))


@pytest.mark.parametrize(
    ("rule_id", "column"),
    [
        ("storm.line_fragility_table", "failures_per_km"),
        ("storm.tower_fragility_table", "collapse"),
    ],
)
def test_the_stored_tables_reproduce_the_offline_curves_at_their_knots(
    rule_id: str, column: str
) -> None:
    table = RULES.value(rule_id)
    for gust, value in zip(table["gust_m_per_s"], table[column], strict=True):
        expected = _lognormal(gust, table["median_m_per_s"], table["beta"])
        # The stored median is rounded to 6 decimals; the curve was built from the full one.
        assert value == pytest.approx(expected, abs=1e-6)


def test_the_line_curve_is_the_declared_calibration_and_keeps_the_old_anchor() -> None:
    import importlib.util

    builder_path = FIXTURES.parents[1] / "tools" / "build_fragility_tables.py"
    spec = importlib.util.spec_from_file_location("build_fragility_tables", builder_path)
    assert spec is not None
    assert spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    table = RULES.value("storm.line_fragility_table")
    assert table["median_m_per_s"] == builder.LINE_MEDIAN
    assert table["beta"] == 0.4
    rule = RULES.rule("storm.line_fragility_table")
    assert rule.status == "ruled"
    # Recalibrated for routed lines and the directional ridge factor (PR 14 answers), then
    # for its ceiling and towers designed for their site (PR 14 second answers).
    assert [h.value["median_m_per_s"] for h in rule.history[-3:]] == [
        121.7185,
        159.9394,
        201.7763,
    ]
    assert [h.decision for h in rule.history[-3:]] == ["0012", "0013", "0013"]
    assert rule.history[-3].value["beta"] == 0.3
    targets = RULES.rule("storm.line_fragility_anchor")
    assert targets.value == {"severity_50_length_share": 0.10, "severity_70_length_share": 0.30}
    assert targets.history[-1].value == {"gust_m_per_s": 45.0, "failures_per_km": 0.05}


def test_towers_hardly_fail_below_210_km_per_h_and_half_fail_at_285() -> None:
    table = RULES.value("storm.tower_fragility_table")
    knots = (tuple(table["gust_m_per_s"]), tuple(table["collapse"]))
    assert stage._interpolate(knots, 210 / 3.6) < 0.002
    assert stage._interpolate(knots, 285 / 3.6) == pytest.approx(0.5, abs=0.01)


@settings(max_examples=60, deadline=None)
@given(
    low=st.floats(0.0, 119.0), step=st.floats(0.0, 30.0), short=st.floats(0.01, 30.0),
    extra=st.floats(0.0, 30.0),
)  # fmt: skip
def test_lines_fail_more_often_at_higher_gust_and_greater_length(
    low: float, step: float, short: float, extra: float
) -> None:
    reader = stage._LineReader(pipeline()[1], RULES)
    piece = reader.piece_probability
    assert piece(low, short) <= piece(low + step, short) + 1e-12
    assert piece(low, short) <= piece(low, short + extra) + 1e-12
    assert reader.tower_probability(low) <= reader.tower_probability(low + step) + 1e-12


@settings(max_examples=60)
@given(base=st.floats(0.0, 1.0), exponent=st.floats(0.0, 60.0))
def test_the_power_by_roots_matches_the_power(base: float, exponent: float) -> None:
    quantised = round(exponent * 1024) / 1024
    assert stage._power(base, exponent) == pytest.approx(base**quantised, rel=1e-9, abs=1e-12)


def test_a_piece_fails_with_one_minus_survival_to_its_length() -> None:
    reader = stage._LineReader(pipeline()[1], RULES)
    per_km = stage._interpolate(reader.line_table, 80.0)
    assert reader.piece_probability(80.0, 1.0) == pytest.approx(per_km, rel=1e-9)
    assert reader.piece_probability(80.0, 0.25) == pytest.approx(1 - (1 - per_km) ** 0.25, rel=1e-9)


def test_a_line_splits_into_whole_kilometres_and_a_remainder() -> None:
    _, terrain, _, _, _, result = pipeline()
    reader = stage._LineReader(terrain, RULES)
    for line in result.lines:
        pieces = reader.pieces(line)
        assert pieces[0].start_km == 0.0
        for a, b in itertools.pairwise(pieces):
            assert a.end_km == b.start_km
            assert a.end_km - a.start_km == pytest.approx(1.0)
        assert pieces[-1].end_km == pytest.approx(line.length_km, abs=0.002)
        assert len(pieces) == max(1, math.ceil(pieces[-1].end_km - 1e-9))


# --- Overhead lines and their gust (D1) -----------------------------------------------------


def test_overhead_lines_are_power_and_telecom_links_and_substation_feeds() -> None:
    _, _, requirements, couplings, _, result = pipeline()
    layers = requirements.layers
    classes = {n.node_id: n.node_class for n in layers.nodes}
    links = {k.link_id for k in layers.links if k.layer in (Layer.POWER, Layer.TELECOM)}
    feeds = {
        e.edge_id
        for e in couplings.edges
        if e.supplier_layer == Layer.POWER
        and e.role == "primary_supply"
        and classes[e.supplier_id]
        in (NodeClass.DISTRIBUTION_SUBSTATION, NodeClass.TRANSMISSION_SUBSTATION)
    }
    assert {line.line_id for line in result.lines} == links | feeds
    routes = {e.edge_id: e.route for e in couplings.edges}
    for line in result.lines:
        # Every mapped power line is on towers; feeds and telecom links on poles (§4.2).
        assert (line.structure == Structure.TOWER) == (line.kind == LineKind.POWER_LINK)
        if line.kind == LineKind.POWER_FEED:
            assert line.points == routes[line.line_id]


def test_a_point_falls_in_the_cell_of_its_node() -> None:
    _, terrain, requirements, *_ = pipeline()
    for node in requirements.layers.nodes:
        assert stage.cell_of(node.x_m, node.y_m, terrain.grid) == (node.row, node.column)


def test_a_line_reads_its_peak_gust_along_its_length() -> None:
    _, terrain, requirements, _, storm, result = pipeline()
    reader = stage._LineReader(terrain, RULES)
    nodes = {n.node_id: n for n in requirements.layers.nodes}
    for scenario, damage in zip(storm.scenarios[:2], result.scenarios[:2], strict=True):
        for line, outcome in zip(result.lines, damage.lines, strict=True):
            gust = reader.gust(scenario, line.structure)
            cells = reader.cells(line)
            for end in (line.from_id, line.to_id):
                assert nodes[end].row * 256 + nodes[end].column in cells
            pieces = reader.pieces(line)
            peak = max(float(gust.ravel()[piece.cells].max()) for piece in pieces)
            assert outcome.peak_gust_m_per_s == peak


def test_the_gust_factor_is_1_38_at_the_coast_and_1_66_a_km_inland() -> None:
    terrain = pipeline()[1]
    reader = stage._LineReader(terrain, RULES)
    land = np.asarray(terrain.land)
    assert np.allclose(reader.factor[~land], 1.38)
    inland = stage._coast_distance_km(land, terrain.grid.cell_size_m / 1000, 1.0) >= 1.0
    assert np.allclose(reader.factor[land & inland], 1.66)
    assert RULES.rule("storm.gust_factors").history[-1].value == {"inland": 1.75, "coast": 1.30}


# --- Damage draws (D2, D3) ------------------------------------------------------------------


def test_each_kilometre_fails_at_its_own_gust_and_each_failure_is_a_point() -> None:
    resolution, terrain, _, _, storm, result = pipeline()
    reader = stage._LineReader(terrain, RULES)
    streams = scenarios_streams(resolution.recipe.root_seed, 8)
    for field, scenario, stream in zip(storm.scenarios, result.scenarios, streams, strict=True):
        gust = reader.gust(field, Structure.POLE).ravel()
        for line, outcome in zip(result.lines, scenario.lines, strict=True):
            if line.structure == Structure.TOWER:
                failed = float(stream.random()) < reader.tower_probability(
                    outcome.peak_gust_m_per_s
                )
                assert outcome.failed == failed
                assert outcome.failure_points == int(failed)
                assert outcome.crew_work_h == 72.0 * int(failed)
                continue
            points = []
            for piece in reader.pieces(line):
                chance = reader.piece_probability(
                    float(gust[piece.cells].max()), piece.end_km - piece.start_km
                )
                if float(stream.random()) < chance:
                    points.append((piece.start_km + piece.end_km) / 2)
            assert outcome.failure_km == tuple(points)
            assert outcome.failure_points == len(points)
            assert outcome.failed == bool(points)
            assert outcome.crew_work_h == 6.0 * len(points)


@pytest.mark.parametrize(
    ("over", "state"),
    [(0.01, "slight"), (0.5, "slight"), (0.51, "moderate"), (1.5, "moderate"),
     (1.51, "extensive"), (3.0, "extensive"), (3.01, "complete")],
)  # fmt: skip
def test_the_damage_state_follows_the_depth_over_the_threshold(over: float, state: str) -> None:
    assert stage.damage_state(over, RULES) == DamageState(state)


def test_a_flooded_facility_is_damaged_at_its_state_held_to_the_cap() -> None:
    layers = pipeline()[2].layers
    plant = next(n for n in layers.nodes if n.node_class == NodeClass.GENERATION)
    depth = np.zeros((256, 256))
    depth[plant.row, plant.column] = 3.2 + 2.0
    held = stage._flooded(depth, layers, RULES, DamageState.MODERATE)
    free = stage._flooded(depth, layers, RULES, DamageState.COMPLETE)
    assert [(d.node_id, d.damage_state, d.capped) for d in held] == [
        (plant.node_id, DamageState.MODERATE, True)
    ]
    assert free[0].damage_state == DamageState.EXTENSIVE
    assert free[0].depth_over_m == pytest.approx(2.0)
    depth[plant.row, plant.column] = 3.2
    assert stage._flooded(depth, layers, RULES, DamageState.COMPLETE) == []


def test_the_pilot_damages_no_facility() -> None:
    # With routed lines and the ridge factor the pilot's line-length share leaves its 10%
    # window; it is reported, not tuned (Work Order 6c, C3).
    result: ScenariosResult = pipeline()[-1]
    for scenario in result.scenarios:
        assert scenario.facilities == ()


def test_at_severity_70_the_flood_reaches_the_pilot_plant() -> None:
    recipe, pilot = load_recipe(SEVERITY_70), load_recipe(PILOT)
    storm = recipe.shared_causes.hazards.storm_corridor
    assert storm.severity == 70
    shared = recipe.shared_causes.model_copy(
        update={"hazards": recipe.shared_causes.hazards.model_copy(
            update={"storm_corridor": pilot.shared_causes.hazards.storm_corridor})}
    )  # fmt: skip
    assert recipe.model_copy(update={"shared_causes": shared}) == pilot
    result = pipeline(SEVERITY_70)[-1]
    damaged = [d for s in result.scenarios for d in s.facilities]
    assert damaged
    assert {d.node_class for d in damaged} == {"generation"}


# --- The calm world check (G1) --------------------------------------------------------------


def test_with_no_storm_nothing_is_damaged_and_the_check_passes() -> None:
    *_, storm, result = pipeline(severity=0, scenarios=3)
    assert storm.severity == 0
    assert all(not s.failed_lines and not s.facilities for s in result.scenarios)
    assert calm_world_problems(storm, result) == []


def test_the_calm_check_names_anything_damaged_with_no_storm() -> None:
    *_, storm, result = pipeline(severity=0, scenarios=3)
    first = result.scenarios[0]
    broken = stage.LineOutcome(first.lines[0].line_id, 0.0, 0.0, True, 1, (0.5,), 6.0)
    damaged = stage.ScenarioDamage(0, (broken, *first.lines[1:]), first.facilities)
    faulty = ScenariosResult(result.elements, result.lines, (damaged, *result.scenarios[1:]))
    assert calm_world_problems(storm, faulty) == [
        f"scenario 0: line {broken.line_id} failed with no storm"
    ]


# --- Streams, protectability and repair (A1, E1, F1) ----------------------------------------


def test_changing_the_scenario_count_moves_no_earlier_scenario() -> None:
    three = pipeline(scenarios=3)[-1]
    eight = pipeline()[-1]
    assert three.scenarios == eight.scenarios[:3]


def test_the_stage_opens_only_its_own_damage_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    original = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> Any:
        opened.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    scenarios_streams(3, 2)
    assert opened == [
        "shared_causes/storm_corridor/0/damage", "shared_causes/storm_corridor/1/damage"
    ]  # fmt: skip
    assert "shared_causes/scenarios" not in rng.STREAM_REGISTRY
    assert "shared_causes/storm_corridor/199/damage" in rng.STREAM_REGISTRY


def test_every_facility_and_overhead_line_is_protectable() -> None:
    _, _, requirements, _, _, result = pipeline()
    facilities = {
        n.node_id
        for n in requirements.layers.nodes
        if n.node_class not in (NodeClass.ROAD_JUNCTION, NodeClass.RAIL_NODE)
    }
    assert {e.element_id for e in result.elements} == facilities | {
        line.line_id for line in result.lines
    }
    assert all(e.protectable for e in result.elements)


def test_each_overhead_line_has_6_h_of_crew_work_and_travel_to_its_midpoint() -> None:
    from repair_helpers import crews_of
    from swm.recipe.schema import RepairRates

    resolution, terrain, requirements, couplings, *_ = pipeline()
    world = (resolution.recipe, terrain, requirements.layers)
    repair = build_repair(
        RepairRates(), crews_of(world), terrain, requirements.layers, requirements, couplings,
        RULES, repair_streams(resolution.recipe.root_seed),
    )  # fmt: skip
    lines = overhead_lines(requirements.layers, couplings)
    assert [r.line_id for r in repair.lines] == [line.line_id for line in lines]
    for record in repair.lines:
        line = next(line for line in lines if line.line_id == record.line_id)
        expected = 72.0 if line.structure == Structure.TOWER else 6.0
        assert (record.crew_work_h_per_failure_point, record.lead_time_h) == (expected, 0.0)
        assert record.travel_h is not None
        assert record.travel_h > 0.0


def test_a_lines_midpoint_lies_on_it() -> None:
    _, terrain, _, _, _, result = pipeline()
    reader = stage._LineReader(terrain, RULES)
    for line in result.lines:
        midpoints = [km.midpoint for km in stage.kilometres(line)]
        row, column = stage.cell_of(*midpoints[len(midpoints) // 2], terrain.grid)
        crossed = reader.cells(line)
        # The path is rasterised at half-cell steps, so the true midpoint lies within a cell.
        nearest = np.min(np.maximum(np.abs(crossed // 256 - row), np.abs(crossed % 256 - column)))
        assert nearest <= 1


def test_swm_scenarios_writes_statistics_and_hashes(tmp_path: Path) -> None:
    assert main(["scenarios", str(PILOT), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "scenarios_stats.yaml").read_text(encoding="utf-8")
    assert "\noverhead_lines:\n" in stats
    hashes = (tmp_path / "scenarios_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in hashes] == [
        "elements", "line_outcomes", "facility_damage"
    ]  # fmt: skip
