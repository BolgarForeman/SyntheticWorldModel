import dataclasses
from typing import Any

import numpy as np
import pytest

from couplings_helpers import World, couple, requirements_of, rich_world
from repair_helpers import crews_of, pilot_world, repair_of
from swm import rng
from swm.draws import DrawMethod
from swm.recipe.dependencies import Role
from swm.recipe.schema import Layer, NodeClass
from swm.rules.registry import load_registry
from swm.stages import repair as stage
from swm.stages.crews import RoadNetwork
from swm.stages.terrain import _label_land

C = NodeClass
RULES = load_registry()
HAZUS_DAYS = {
    (C.DISTRIBUTION_SUBSTATION, "slight"): 1.0,
    (C.DISTRIBUTION_SUBSTATION, "moderate"): 3.0,
    (C.MAST, "moderate"): 1.0,
    (C.TREATMENT, "moderate"): 1.9,
    (C.TERTIARY, "slight"): 5.0,
    (C.BRIDGE, "moderate"): 2.5,
}
"""Hazus MR4 restoration means (days), as the registry records them."""


@pytest.fixture(scope="module")
def rich() -> World:
    return rich_world()


@pytest.fixture(scope="module")
def exact(rich: World) -> Any:
    """Heterogeneity 0 and gap 0: every repair sits on its Hazus centre."""
    return repair_of(rich)


def classes(world: World) -> dict[str, NodeClass]:
    return {n.node_id: n.node_class for n in requirements_of(world).layers.nodes}


# --- Permanent repair (G1) ------------------------------------------------------------------


def test_at_zero_levers_lead_time_plus_crew_work_is_the_hazus_centre(exact: Any) -> None:
    assert exact.permanent
    for record in exact.permanent:
        assert record.repair_h == pytest.approx(record.hazus_mean_h)
        if record.hazus_mean_h >= record.crew_work_h:
            assert record.lead_time_h + record.crew_work_h == pytest.approx(record.hazus_mean_h)
        else:
            assert record.lead_time_h == 0.0


def test_the_centres_are_the_registry_hazus_means(exact: Any, rich: World) -> None:
    by_id = classes(rich)
    seen = set()
    for record in exact.permanent:
        key = (by_id[record.node_id], record.damage_state)
        if key in HAZUS_DAYS:
            assert record.hazus_mean_h == pytest.approx(HAZUS_DAYS[key] * 24)
            seen.add(key)
    assert seen == set(HAZUS_DAYS)


def test_every_damage_state_is_recorded_with_its_crew_work(exact: Any, rich: World) -> None:
    work = {(r.damage_state, r.crew_work_h) for r in exact.permanent}
    assert work == {("slight", 8.0), ("moderate", 24.0), ("extensive", 72.0), ("complete", 168.0)}
    states: dict[str, list[str]] = {}
    for record in exact.permanent:
        states.setdefault(record.node_id, []).append(record.damage_state)
    assert all(s == ["slight", "moderate", "extensive", "complete"] for s in states.values())


def test_by_default_each_state_takes_the_hazus_spread(rich: World) -> None:
    result = repair_of(rich, heterogeneity_pct=None)
    method = DrawMethod.from_registry(RULES)
    streams = stage.repair_streams(rich[0].root_seed)
    draws = {
        n.node_id: float(streams[n.layer].random()) for n in requirements_of(rich).layers.nodes
    }
    spreads = set()
    for record in result.permanent:
        expected = record.hazus_sd_h / record.hazus_mean_h if record.hazus_mean_h else 0.0
        assert record.spread == pytest.approx(expected)
        quantile = method.quantile(method.mixture(expected), draws[record.node_id])
        assert record.repair_h == pytest.approx(record.hazus_mean_h / quantile)
        spreads.add(round(record.spread, 6))
    assert len(spreads) > 5


def test_the_recipe_heterogeneity_overrides_the_hazus_spread(rich: World) -> None:
    result = repair_of(rich, heterogeneity_pct=30)
    assert {r.spread for r in result.permanent} == {0.3}


def test_a_positive_gap_slows_repair(rich: World) -> None:
    slowed = repair_of(rich, gap_pct=20)
    for record in slowed.permanent:
        assert record.repair_h == pytest.approx(record.hazus_mean_h / 0.8)


def test_heterogeneity_spreads_nodes_but_one_draw_serves_every_damage_state(rich: World) -> None:
    result = repair_of(rich, heterogeneity_pct=45)
    ratios: dict[str, set[float]] = {}
    for record in result.permanent:
        if record.hazus_mean_h > 0.0:
            ratios.setdefault(record.node_id, set()).add(
                round(record.repair_h / record.hazus_mean_h, 9)
            )
    assert all(len(r) == 1 for r in ratios.values())
    assert len({next(iter(r)) for r in ratios.values()}) > len(ratios) // 2


def test_reservoirs_are_unrepairable_and_junctions_have_no_repair_rows(
    exact: Any, rich: World
) -> None:
    by_id = classes(rich)
    reservoirs = sorted(i for i, c in by_id.items() if c == C.RESERVOIR)
    assert reservoirs
    assert list(exact.unrepairable) == reservoirs
    repaired = {r.node_id for r in exact.permanent}
    assert not repaired & set(reservoirs)
    assert any(c == C.ROAD_JUNCTION for c in by_id.values())
    assert not any(by_id[i] == C.ROAD_JUNCTION for i in repaired)
    assert RULES.value("repair.no_repair_rows") == ["road_junction", "rail_node"]
    assert not any("road_junction" in note for note in exact.notes)


def test_a_class_with_no_hazus_row_and_no_ruling_is_noted(rich: World) -> None:
    result = repair_of(rich, overrides={"repair.no_repair_rows": ["rail_node"]})
    assert "road_junction: no Hazus restoration row; no permanent repair" in result.notes


def test_every_node_draws_so_a_rule_change_moves_no_other_node(rich: World) -> None:
    before = repair_of(rich, heterogeneity_pct=45)
    masts = {"repair.unrepairable": ["reservoir", "mast"]}
    after = repair_of(rich, heterogeneity_pct=45, overrides=masts)
    mast_ids = {i for i, c in classes(rich).items() if c == C.MAST}
    assert mast_ids <= set(after.unrepairable)
    assert set(after.permanent) == {r for r in before.permanent if r.node_id not in mast_ids}


# --- Emergency repair (G2) ------------------------------------------------------------------


def test_emergency_modes_only_at_distribution_substations_and_masts(
    exact: Any, rich: World
) -> None:
    by_id = classes(rich)
    kinds = {(by_id[e.node_id], e.unit_kind) for e in exact.emergency}
    assert kinds == {(C.DISTRIBUTION_SUBSTATION, "mobile_substation"), (C.MAST, "mobile_cell_site")}
    eligible = sorted(i for i, c in by_id.items() if c in (C.DISTRIBUTION_SUBSTATION, C.MAST))
    assert sorted(e.node_id for e in exact.emergency) == eligible


def test_emergency_set_up_plus_travel_from_the_pool_base(exact: Any, rich: World) -> None:
    travel = {t.node_id: t for t in repair_of(rich, crew_base=1).travel}
    for option in exact.emergency:
        set_up = 12.0 if option.unit_kind == "mobile_substation" else 14.0
        assert option.set_up_h == set_up
        assert option.travel_h == pytest.approx(travel[option.node_id].travel_h)
        assert option.total_h == pytest.approx(set_up + option.travel_h)


def test_a_mobile_substation_restores_25_mva_against_the_normal_peak(rich: World) -> None:
    small = {"repair.emergency.mobile_substation": {"hours_including_travel": [12.0, 24.0],
                                                    "capacity_mva": 1.0}}  # fmt: skip
    result = repair_of(rich, overrides=small)
    needs = requirements_of(rich).by_id()
    peaks: dict[str, float] = {}
    for edge in couple(rich).edges:
        if edge.supplier_layer == Layer.POWER and edge.role == Role.PRIMARY_SUPPLY:
            share = 0.5 if edge.feed_configuration == "two_half" else 1.0
            peak = (needs[edge.consumer_id].peak_mw or 0.0) * share
            peaks[edge.supplier_id] = peaks.get(edge.supplier_id, 0.0) + peak
    substations = [e for e in result.emergency if e.unit_kind == "mobile_substation"]
    assert any(e.restored_share < 1.0 for e in substations)
    for option in substations:
        assert option.capacity_mva == 1.0
        assert option.restored_share == pytest.approx(min(1.0, 0.9 / peaks[option.node_id]))
    masts = [e for e in result.emergency if e.unit_kind == "mobile_cell_site"]
    assert all(e.restored_share == 0.5 and e.capacity_mva is None for e in masts)


def test_a_pool_without_a_unit_kind_offers_no_such_option(rich: World) -> None:
    result = repair_of(rich, mobile_cell_sites=0)
    assert {e.unit_kind for e in result.emergency} == {"mobile_substation"}
    assert "mast: the emergency pool holds no mobile_cell_site" in result.notes


# --- Travel (G3) ----------------------------------------------------------------------------


def test_travel_is_road_distance_over_speed_and_its_own_term(exact: Any, rich: World) -> None:
    slower = repair_of(rich, overrides={"crews.road_speed_kmh": 20.0})
    for fast, slow in zip(exact.travel, slower.travel, strict=True):
        assert fast.travel_h == pytest.approx(fast.road_km / 40.0)
        assert slow.travel_h == pytest.approx(2 * fast.travel_h)
    assert slower.permanent == exact.permanent


def test_each_node_takes_its_nearest_base(rich: World) -> None:
    three = repair_of(rich, crews=3, crew_base=3)
    for base_id in ("CRB-0001", "CRB-0002", "CRB-0003"):
        assert any(t.base_id == base_id for t in three.travel)
    one = {t.node_id: t.travel_h for t in repair_of(rich).travel}
    assert all(t.travel_h <= one[t.node_id] + 1e-9 for t in three.travel)


def test_a_node_off_the_roads_is_reached_by_sea_after_the_mobilisation_delay(rich: World) -> None:
    layers = requirements_of(rich).layers
    network = RoadNetwork(rich[1], layers)
    labels, sizes = _label_land(np.asarray(rich[1].land))
    roads = {int(labels[n.row, n.column]) for n in network.transport}
    island = min(set(range(1, len(sizes) + 1)) - roads)
    rows, columns = np.nonzero(labels == island)
    moved = dataclasses.replace(layers.nodes[0], row=int(rows[0]), column=int(columns[0]))
    base = crews_of(rich).bases[0]
    trip = stage._travel(base, moved, network, 40.0, 12.0)
    assert trip is not None
    assert trip.by_sea
    road = network.road_km(base.access_node_id)
    ports = [n for n in network.transport if n.node_class == C.SEAPORT and n.node_id in road]
    nearest = min(road[p.node_id] for p in ports)
    assert trip.road_km == pytest.approx(base.access_km + nearest)
    assert trip.travel_h == pytest.approx(trip.road_km / 40.0 + 12.0)


# --- The pilot ------------------------------------------------------------------------------


def test_the_pilot_records_repair_for_every_node_but_its_reservoir() -> None:
    world = pilot_world()
    result = repair_of(world, heterogeneity_pct=45, gap_pct=20)
    ids = {n.node_id for n in world[2].nodes}
    assert list(result.unrepairable) == ["SWM-WAT-0001"]
    assert {r.node_id for r in result.permanent} == ids - {"SWM-WAT-0001"}
    assert {t.node_id for t in result.travel} == ids
    assert not any(t.by_sea for t in result.travel)


# --- Streams and separation -----------------------------------------------------------------


def test_the_stage_opens_only_its_own_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    original = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> Any:
        opened.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    stage.repair_streams(3)
    assert sorted(opened) == sorted(f"repair/{layer}" for layer in Layer)
    assert set(opened) <= set(rng.STREAM_REGISTRY)
    assert "unobserved/repair_rates" not in rng.STREAM_REGISTRY
    assert "unobserved/crews_and_depots" not in rng.STREAM_REGISTRY


def test_the_tables_hold_every_record(exact: Any) -> None:
    tables = stage.repair_tables(exact)
    assert list(tables) == ["travel", "permanent_repair", "emergency_repair", "unrepairable"]
    assert len(tables["permanent_repair"]) == len(exact.permanent)
