import functools
import math
from itertools import pairwise
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from couplings_helpers import rich_world
from repair_helpers import pilot_world
from swm.cli import _couplings, _requirements, _rules, _terrain
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import Layer, NodeClass
from swm.rules.registry import load_registry
from swm.stages import layers as layers_stage
from swm.stages import topography
from swm.stages.layers import build_layers, layers_streams
from swm.stages.roads import RoadMap
from swm.stages.terrain import GRID_CELLS
from swm.stages.terrain_routes import RouteCost, least_cost_route, route_cost

RULES = load_registry()
PILOT = "tests/fixtures/pilot_hand_check.yaml"


@functools.cache
def pilot() -> Any:
    from pathlib import Path

    resolution = resolve(load_recipe(Path(PILOT)))
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    return resolution, terrain, requirements, _couplings(resolution, terrain, requirements)


# --- Mapped power lines (A1-A5) -------------------------------------------------------------


def test_every_power_link_is_a_mapped_line_with_its_id() -> None:
    _, _, layers = pilot_world()
    power = [link.link_id for link in layers.links if link.layer == Layer.POWER]
    assert [line.link_id for line in layers.power_lines] == power
    assert power == [f"SWM-POW-L{i:04d}" for i in range(1, 6)]


def test_routes_are_deterministic_on_land_and_join_their_ends() -> None:
    recipe, terrain, layers = pilot_world()
    again = build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed), RULES)
    assert again.power_lines == layers.power_lines
    nodes = {n.node_id: n for n in layers.nodes}
    land = np.asarray(terrain.land)
    for link in (k for k in layers.links if k.layer == Layer.POWER):
        start, end = nodes[link.from_id], nodes[link.to_id]
        assert link.points[0] == layers_stage.cell_centre_m(start.row, start.column, terrain.grid)
        assert link.points[-1] == layers_stage.cell_centre_m(end.row, end.column, terrain.grid)
        assert not link.crosses_sea
        for a, b in pairwise(link.points):
            row_a, col_a = _cell(a, terrain)
            row_b, col_b = _cell(b, terrain)
            for cell in layers_stage._segment_cells((row_a, col_a), (row_b, col_b)):
                assert land.flat[cell]


def _cell(point: tuple[float, float], terrain: Any) -> tuple[int, int]:
    from swm.coordinates import cell_of

    return cell_of(point[0], point[1], terrain.grid)


def test_a_route_is_never_shorter_than_the_straight_line_and_ridges_are_flagged() -> None:
    _, terrain, layers = pilot_world()
    for line in layers.power_lines:
        assert line.route_km >= line.straight_km - 1e-9
        vertices = [_cell(p, terrain) for p in
                    next(k.points for k in layers.links if k.link_id == line.link_id)]  # fmt: skip
        assert line.ridge_crossing == layers_stage._crosses_spine(vertices, terrain)
    assert any(line.ridge_crossing for line in layers.power_lines)
    assert not all(line.ridge_crossing for line in layers.power_lines)


@pytest.mark.parametrize(
    ("first", "second", "kv"),
    [
        (NodeClass.GENERATION, NodeClass.TRANSMISSION_SUBSTATION, 161),
        (NodeClass.GENERATION, NodeClass.DISTRIBUTION_SUBSTATION, 161),
        (NodeClass.TRANSMISSION_SUBSTATION, NodeClass.TRANSMISSION_SUBSTATION, 161),
        (NodeClass.TRANSMISSION_SUBSTATION, NodeClass.DISTRIBUTION_SUBSTATION, 69),
        (NodeClass.DISTRIBUTION_SUBSTATION, NodeClass.DISTRIBUTION_SUBSTATION, 69),
    ],
)
def test_the_voltage_class_follows_the_line_ends(
    first: NodeClass, second: NodeClass, kv: int
) -> None:
    assert layers_stage._voltage_kv(first, second, RULES) == kv


def test_towers_stand_at_both_ends_and_every_350_m() -> None:
    _, _, layers = pilot_world()
    for line in layers.power_lines:
        link = next(k for k in layers.links if k.link_id == line.link_id)
        towers = line.tower_points
        assert towers[0] == link.points[0]
        assert towers[-1] == link.points[-1]
        assert len(towers) == math.ceil(line.route_km * 1000 / 350 - 1e-9) + 1
        assert line.structure == "tower"


# --- Least cost (A3) ------------------------------------------------------------------------


def _wall(gap_cost: float) -> RouteCost:
    """A flat grid with a costly wall across column 128, open at a gap near the bottom."""
    multiplier = np.ones((GRID_CELLS, GRID_CELLS))
    multiplier[:, 128] = gap_cost
    multiplier[200:210, 128] = 1.0
    return RouteCost(multiplier, np.zeros((GRID_CELLS, GRID_CELLS), bool), 0.5, 0.1)


def test_a_route_takes_the_valley_when_the_detour_is_cheaper_and_crosses_when_not() -> None:
    start, end = 50 * GRID_CELLS + 100, 50 * GRID_CELLS + 156
    detour = least_cost_route(_wall(1000.0), start, end)
    assert detour is not None
    assert any(divmod(c, GRID_CELLS)[1] == 128 and divmod(c, GRID_CELLS)[0] >= 200 for c in detour)
    over = least_cost_route(_wall(2.0), start, end)
    assert over is not None
    assert max(divmod(c, GRID_CELLS)[0] for c in over) < 60


def test_the_sea_is_never_entered_and_a_river_crossing_costs_its_fixed_amount() -> None:
    terrain = pilot_world()[1]
    cost = route_cost(terrain, RULES)
    assert np.isinf(cost.multiplier[~np.asarray(terrain.land)]).all()
    flat = np.ones((GRID_CELLS, GRID_CELLS))
    river = np.zeros((GRID_CELLS, GRID_CELLS), bool)
    river[:, 128] = True
    crossing = RouteCost(flat, river, 0.5, 0.1)
    route = least_cost_route(crossing, 10 * GRID_CELLS + 120, 10 * GRID_CELLS + 136)
    assert route is not None
    assert sum(1 for c in route if divmod(c, GRID_CELLS)[1] == 128) == 1


# --- Feeds along roads (B1) and rule 4 (B2) -------------------------------------------------


def test_feeds_run_along_the_roads_between_straight_end_legs() -> None:
    _, terrain, requirements, couplings = pilot()
    roads = RoadMap(terrain, requirements.layers)
    feeds = [e for e in couplings.edges if e.route]
    assert feeds
    for edge in feeds:
        assert edge.route[0] == edge.points[0]
        assert edge.route[-1] == edge.points[1]
        assert edge.route_km is not None
        assert edge.route_km >= edge.length_km - 0.002
        for point in edge.route[1:-1]:
            foot = roads.nearest(point)
            assert foot is not None
            assert foot.offroad_m < 0.01


def test_only_power_feeds_from_substations_have_a_route() -> None:
    _, _, requirements, couplings = pilot()
    classes = {n.node_id: n.node_class for n in requirements.layers.nodes}
    for edge in couplings.edges:
        is_feed = (
            edge.supplier_layer == Layer.POWER
            and edge.role == "primary_supply"
            and classes[edge.supplier_id]
            in (NodeClass.DISTRIBUTION_SUBSTATION, NodeClass.TRANSMISSION_SUBSTATION)
        )
        assert bool(edge.route) == is_feed


def test_a_large_load_takes_transmission_and_a_small_one_the_nearest_of_either_class() -> None:
    from swm.stages import couplings as stage
    from swm.stages.couplings import _World

    _, terrain, layers = rich_world()
    world = _World(terrain, layers, RULES)
    clinic = next(n for n in layers.nodes if n.node_class == NodeClass.CLINIC)
    row = stage.resolve_row(Layer.POWER, NodeClass.CLINIC, dict(clinic.subtype), RULES)
    small = stage._LargeLoads({clinic.node_id: 0.1}, 5.0, 50)
    eligible = stage._eligible(Layer.POWER, small.suppliers(row, clinic), clinic, world)
    substations = [
        n
        for n in layers.nodes
        if n.node_class in (NodeClass.DISTRIBUTION_SUBSTATION, NodeClass.TRANSMISSION_SUBSTATION)
    ]
    nearest = min(substations, key=lambda n: (stage._distance2(n, clinic), n.node_id))
    assert eligible[0] == nearest
    assert {n.node_class for n in eligible} == {
        NodeClass.DISTRIBUTION_SUBSTATION,
        NodeClass.TRANSMISSION_SUBSTATION,
    }
    large = stage._LargeLoads({clinic.node_id: 5.0}, 5.0, 50)
    large_eligible = stage._eligible(Layer.POWER, large.suppliers(row, clinic), clinic, world)
    assert {n.node_class for n in large_eligible} == {NodeClass.TRANSMISSION_SUBSTATION}


# --- The ridge factor (C2) ------------------------------------------------------------------


def _one(value: float) -> np.ndarray:
    return np.array([value])


def _factor(ratio: float, x_over_lh: float, z_over_lh: float, escarpment: bool = False,
            rough: bool = False) -> float:  # fmt: skip
    half_length_km = 1.0
    feature = topography._Feature(
        height_m=_one(ratio * 1000.0),
        half_length_km=_one(half_length_km),
        offset_km=_one(x_over_lh * half_length_km),
        escarpment=np.array([escarpment]),
        applies=np.array([True]),
    )
    table = RULES.value("storm.topographic_factor")
    return float(topography._factor(feature, np.array([rough]), table, z_over_lh * 1000.0)[0])


@pytest.mark.parametrize(
    ("ratio", "rough", "escarpment", "k1"),
    [(0.20, False, False, 0.29), (0.35, False, False, 0.51), (0.50, True, False, 0.65),
     (0.30, False, True, 0.26), (0.45, True, True, 0.34)],
)  # fmt: skip
def test_k1_reproduces_table_2_3_a_at_its_knots(
    ratio: float, rough: bool, escarpment: bool, k1: float
) -> None:
    assert _factor(ratio, 0.0, 0.0, escarpment, rough) == pytest.approx(1.0 + k1)


@pytest.mark.parametrize(
    ("x", "escarpment", "k2"),
    [(-1.0, False, 0.33), (-0.5, False, 0.67), (0.5, False, 0.67), (1.0, False, 0.33),
     (1.5, False, 0.0), (0.5, True, 0.88), (2.0, True, 0.50), (3.5, True, 0.13)],
)  # fmt: skip
def test_k2_reproduces_table_2_3_b_at_its_knots(x: float, escarpment: bool, k2: float) -> None:
    k1 = 0.43 if not escarpment else 0.26
    factor = _factor(0.30, x, 0.0, escarpment)
    assert (factor - 1.0) / k1 == pytest.approx(k2, abs=0.006)


@pytest.mark.parametrize(
    ("z", "escarpment", "k3"),
    [(0.1, False, 0.74), (0.5, False, 0.22), (1.0, False, 0.05), (0.3, True, 0.47),
     (1.5, True, 0.02)],
)  # fmt: skip
def test_k3_reproduces_table_2_3_c_at_its_knots(z: float, escarpment: bool, k3: float) -> None:
    k1 = 0.43 if not escarpment else 0.26
    assert (_factor(0.30, 0.0, z, escarpment) - 1.0) / k1 == pytest.approx(k3)


def test_above_h_over_lh_0_5_k1_is_capped_and_lh_becomes_2h() -> None:
    capped = _factor(0.8, 0.0, 0.0)
    assert capped == pytest.approx(1.0 + 0.72)


def test_flat_ground_and_gentle_slopes_take_no_ridge_factor() -> None:
    flat = np.zeros((GRID_CELLS, GRID_CELLS))
    rough = np.zeros((GRID_CELLS, GRID_CELLS), bool)
    table = RULES.value("storm.topographic_factor")
    assert not topography._feature(flat, rough, 0.1, (0, 1), table).applies.any()
    columns = np.arange(GRID_CELLS)
    gentle = np.maximum(0.0, 30.0 - 0.2 * np.abs(columns - 128))[None, :] * np.ones((GRID_CELLS, 1))
    assert not topography._feature(gentle, rough, 0.1, (0, 1), table).applies.any()


def test_a_steep_isolated_ridge_takes_the_factor_at_its_crest_only() -> None:
    columns = np.arange(GRID_CELLS)
    ridge = np.maximum(0.0, 200.0 - 20.0 * np.abs(columns - 128))[None, :] * np.ones(
        (GRID_CELLS, 1)
    )
    rough = np.zeros((GRID_CELLS, GRID_CELLS), bool)
    table = RULES.value("storm.topographic_factor")
    feature = topography._feature(ridge, rough, 0.1, (0, 1), table)
    assert feature.applies[100, 128]
    assert not feature.applies[100, 60]
    assert feature.height_m[100, 128] == pytest.approx(200.0)


def test_the_pilot_ridge_factor_is_one_at_sea_and_above_one_somewhere_on_land() -> None:
    terrain = pilot_world()[1]
    factor = topography.speed_factor(terrain, RULES, 30.0)
    land = np.asarray(terrain.land)
    assert (factor[~land] == 1.0).all()
    assert (factor[land] > 1.0).any()
    assert factor.max() <= 1.0 + 0.72 + 1e-9


# --- Storm and crews (C1, D1) ---------------------------------------------------------------


@settings(max_examples=60)
@given(chances=st.lists(st.floats(0.0, 1.0), min_size=1, max_size=20), extra=st.floats(0.0, 1.0))
def test_a_longer_exposed_route_never_lowers_a_lines_failure_chance(
    chances: list[float], extra: float
) -> None:
    def line_chance(values: list[float]) -> float:
        survive = 1.0
        for value in values:
            survive *= 1.0 - value
        return 1.0 - survive

    assert line_chance(chances) <= line_chance([*chances, extra]) + 1e-12


def test_crews_reach_each_kilometre_by_road_then_off_road() -> None:
    from swm.stages.crews import build_crews
    from swm.stages.repair import build_repair, repair_streams
    from swm.stages.scenarios import kilometres, overhead_lines

    resolution, terrain, requirements, couplings = pilot()
    recipe = resolution.recipe
    crews = build_crews(recipe.unobserved, terrain, requirements.layers)
    rules = _rules(resolution)
    result = build_repair(
        recipe.unobserved.repair_rates, crews, terrain, requirements.layers, requirements,
        couplings, rules, repair_streams(recipe.root_seed),
    )  # fmt: skip
    lines = overhead_lines(requirements.layers, couplings)
    assert len(result.failure_points) == sum(len(kilometres(line)) for line in lines)
    for point in result.failure_points:
        assert point.travel_h is not None
        assert point.road_km is not None
        assert point.offroad_km is not None
        assert point.travel_h == pytest.approx(point.road_km / 40.0 + point.offroad_km / 2.0)
