import functools
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


def test_the_line_curve_passes_through_0_05_per_km_at_45_m_per_s() -> None:
    table = RULES.value("storm.line_fragility_table")
    assert table["failures_per_km"][45] == pytest.approx(0.05, abs=1e-9)


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
    line = stage.OverheadLine("L", LineKind.POWER_FEED, Structure.POLE, "a", "b", (), short)
    longer = stage.OverheadLine(
        "M", LineKind.POWER_FEED, Structure.POLE, "a", "b", (), short + extra
    )
    tower = stage.OverheadLine("T", LineKind.POWER_LINK, Structure.TOWER, "a", "b", (), short)
    for chosen in (line, tower):
        assert (
            reader.failure_probability(chosen, low)
            <= reader.failure_probability(chosen, low + step) + 1e-12
        )
    assert reader.failure_probability(line, low) <= reader.failure_probability(longer, low) + 1e-12


@settings(max_examples=60)
@given(base=st.floats(0.0, 1.0), exponent=st.floats(0.0, 60.0))
def test_the_power_by_roots_matches_the_power(base: float, exponent: float) -> None:
    quantised = round(exponent * 1024) / 1024
    assert stage._power(base, exponent) == pytest.approx(base**quantised, rel=1e-9, abs=1e-12)


def test_a_line_on_poles_fails_with_one_minus_survival_to_the_length() -> None:
    reader = stage._LineReader(pipeline()[1], RULES)
    line = stage.OverheadLine("L", LineKind.TELECOM_LINK, Structure.POLE, "a", "b", (), 10.0)
    assert reader.failure_probability(line, 45.0) == pytest.approx(1 - 0.95**10, rel=1e-9)


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
    for line in result.lines:
        ends = {classes[line.from_id], classes[line.to_id]}
        if line.kind == LineKind.POWER_LINK:
            towers = ends <= {NodeClass.GENERATION, NodeClass.TRANSMISSION_SUBSTATION}
        elif line.kind == LineKind.POWER_FEED:
            towers = classes[line.from_id] == NodeClass.TRANSMISSION_SUBSTATION
        else:
            towers = False
        assert (line.structure == Structure.TOWER) == towers


def test_a_point_falls_in_the_cell_of_its_node() -> None:
    _, terrain, requirements, *_ = pipeline()
    for node in requirements.layers.nodes:
        assert stage.cell_of(node.x_m, node.y_m, terrain.grid) == (node.row, node.column)


def test_a_line_reads_its_peak_gust_along_its_length() -> None:
    _, terrain, requirements, _, storm, result = pipeline()
    reader = stage._LineReader(terrain, RULES)
    nodes = {n.node_id: n for n in requirements.layers.nodes}
    for scenario, damage in zip(storm.scenarios[:2], result.scenarios[:2], strict=True):
        gust = scenario.wind_m_per_s * reader.factor
        for line, outcome in zip(result.lines, damage.lines, strict=True):
            cells = reader.cells(line)
            for end in (line.from_id, line.to_id):
                assert nodes[end].row * 256 + nodes[end].column in cells
            assert outcome.peak_gust_m_per_s == float(gust.ravel()[cells].max())


def test_the_gust_factor_is_1_30_at_the_coast_and_1_75_a_km_inland() -> None:
    terrain = pipeline()[1]
    reader = stage._LineReader(terrain, RULES)
    land = np.asarray(terrain.land)
    assert np.allclose(reader.factor[~land], 1.30)
    inland = stage._coast_distance_km(land, terrain.grid.cell_size_m / 1000, 1.0) >= 1.0
    assert np.allclose(reader.factor[land & inland], 1.75)


# --- Damage draws (D2, D3) ------------------------------------------------------------------


def test_each_line_fails_when_its_draw_falls_under_its_chance() -> None:
    resolution, *_, result = pipeline()
    streams = scenarios_streams(resolution.recipe.root_seed, 8)
    for scenario, stream in zip(result.scenarios, streams, strict=True):
        for outcome in scenario.lines:
            assert outcome.failed == (float(stream.random()) < outcome.failure_probability)


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


def test_the_pilot_damages_lines_only_and_something_in_every_scenario() -> None:
    result: ScenariosResult = pipeline()[-1]
    for scenario in result.scenarios:
        assert scenario.failed_lines
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
    broken = stage.LineOutcome(first.lines[0].line_id, 0.0, 0.0, True)
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
        assert (record.crew_work_h, record.lead_time_h) == (6.0, 0.0)
        assert record.travel_h is not None
        assert record.travel_h > 0.0


def test_a_lines_midpoint_lies_on_it() -> None:
    _, terrain, _, _, _, result = pipeline()
    reader = stage._LineReader(terrain, RULES)
    for line in result.lines:
        row, column = stage.midpoint_cell(line, terrain.grid)
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
