"""The hand-trace pack (Work Order 9, Part A): every printed number comes from the engine's
world or the registry, the blind pack holds nothing from the reference run, and the answer is
the saved run's own timeline.
"""

import functools
from pathlib import Path
from typing import Any

import pytest

from swm.cli import _built, _engine
from swm.dynamics.engine import crew_order, simulate, trip_hours
from swm.dynamics.records import Protect, RunRequest
from swm.dynamics.travel import Site
from swm.dynamics.world import REFILL
from swm.recipe.dependencies import Role
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import LIFELINE_WEIGHTS
from swm.trace_pack import (
    COLUMNS,
    DECIMALS,
    ENGINE_RULES,
    TraceInputs,
    blind_tables,
    clusters,
    polyline_km,
    trace_pack,
)

PILOT = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"
SCENARIO = 7


@functools.cache
def pilot() -> Any:
    resolution = resolve(load_recipe(PILOT))
    built = _built(resolution)
    return built, _engine(resolution, built)


def inputs(actions: tuple[Any, ...] = ()) -> TraceInputs:
    built, engine = pilot()
    damage = engine.damage[SCENARIO]
    run = simulate(engine.world, RunRequest(damage, actions=actions, scenario=SCENARIO))
    return TraceInputs(
        SCENARIO, built.terrain, built.requirements.layers, built.requirements, built.couplings,
        built.strength, built.buffers, built.crews, built.repair,
        built.storm.scenarios[SCENARIO], built.scenarios.scenarios[SCENARIO],
        built.scenarios.lines, engine.world, damage, built.rules, run,
    )  # fmt: skip


@functools.cache
def tables() -> dict[str, list[dict[str, object]]]:
    return blind_tables(inputs())


# --- Every value equals its source (A5) -----------------------------------------------------


def test_each_stock_row_is_the_engines_stock() -> None:
    world = pilot()[1].world
    units = {(r.node_id, r.kind): r.stock_units for r in pilot()[0].buffers.reserves}
    rows = tables()["stocks"]
    assert [r["stock"] for r in rows] == [s.stock_id for s in world.stocks]
    for row, stock in zip(rows, world.stocks, strict=True):
        assert row["quantity"] == stock.capacity
        assert row["draw_per_h"] == stock.draw_per_h
        assert row["units"] == units[(stock.node_id, stock.kind)]
        assert row["refill"] == stock.refill
        assert row["rule"] == stock.rule_id
        assert row["covers"] == stock.covers.value


def test_each_generator_and_tolerance_row_is_the_engines() -> None:
    world = pilot()[1].world
    generators = tables()["generators"]
    printed = [(r["node"], r["fails_to_start"] == "yes", r["run_hours_to_failure"])
               for r in generators]  # fmt: skip
    assert printed == [(g.node_id, g.fails_to_start, g.run_hours_to_failure)
                       for g in world.generators]  # fmt: skip
    rows = {r["dependency"]: r for r in tables()["tolerance"]}
    held = [d for d in world.dependencies if d.tolerance is not None]
    assert held
    assert set(rows) == {d.dependency_id for d in held}
    for dependency in held:
        row, tolerance = rows[dependency.dependency_id], dependency.tolerance
        assert tolerance is not None
        assert row["T_h"] == tolerance.t_h
        assert row["d_eff"] == tolerance.d_eff
        assert row["d_eff"] == pytest.approx(
            1.0 - float(row["kappa_public_share"]) * (1.0 - float(row["d"]))
        )  # type: ignore[arg-type]


def test_each_node_row_carries_its_end_use_weight_and_capacity() -> None:
    built, engine = pilot()
    attributes = {n.node_id: dict(n.attributes) for n in built.requirements.layers.nodes}
    for row, node in zip(tables()["nodes"], engine.world.nodes, strict=True):
        assert row["node"] == node.node_id
        assert row["service_weight"] == node.end_use_weight
        assert (row["end_use"] == "yes") == (node.end_use_weight is not None)
        assert row["capacity_mw"] == attributes[node.node_id].get("capacity_mw")
        assert row["capacity_m3_per_day"] == attributes[node.node_id].get("capacity_m3_per_day")


def test_each_dependency_row_carries_its_feeds_and_resupply_role() -> None:
    edges = {e.edge_id: e for e in pilot()[0].couplings.edges}
    rows = tables()["dependencies"]
    assert len(rows) == len(edges)
    assert any(r["fuel_resupply"] == "yes" for r in rows)
    for row in rows:
        edge = edges[str(row["edge"])]
        assert row["feed_configuration"] == edge.feed_configuration.value
        assert (row["fuel_resupply"] == "yes") == (edge.role == Role.BUFFER_RESUPPLY)


def test_each_link_row_has_its_length_towers_and_flow() -> None:
    built, engine = pilot()
    overhead = {line.line_id: line.length_km for line in built.scenarios.lines}
    links = {link.link_id: link for link in built.requirements.layers.links}
    rows = tables()["links"]
    assert len(rows) == len(links)
    for row in rows:
        link = links[str(row["link"])]
        assert row["length_km"] == round(polyline_km(link.points), DECIMALS)
        if link.link_id in overhead:
            assert row["length_km"] == pytest.approx(overhead[link.link_id], abs=1e-3)
        assert (row["on_towers"] == "yes") == (link.link_id in engine.world.towered)
    carried = {link.link_id for link in engine.world.links}
    assert {r["link"] for r in rows if r["flow"] != "none"} == carried


def test_each_failure_point_row_is_the_engines_failure_point() -> None:
    engine = pilot()[1]
    damage = engine.damage[SCENARIO]
    rows = tables()["damage_lines"]
    assert len(rows) == len(damage.failure_points)
    base = engine.world.crews[0].site
    for row, point in zip(rows, damage.failure_points, strict=True):
        assert row["line"] == point.line_id
        assert row["km_along_line"] == point.km
        assert row["crew_work_h"] == point.crew_work_h
        legs = engine.world.legs(Site(base), Site(point.site, on_line=True))
        expected = round(trip_hours(legs, engine.world.settings), DECIMALS)
        assert row["travel_h_from_base"] == expected


def test_the_travel_from_base_is_the_reference_runs_first_trip() -> None:
    # Each crew's first trip leaves the base at hour 0 for its job's first failure point.
    run = inputs().run
    first_points: dict[str, float] = {}
    for row in tables()["damage_lines"]:
        first_points.setdefault(str(row["line"]), float(row["travel_h_from_base"]))  # type: ignore[arg-type]
    checked = 0
    for _, log in run.crews:
        trip = log[0]
        line = trip.job_id.removeprefix("repair:")
        if trip.activity == "travel" and trip.start_h == 0.0 and line in first_points:
            assert round(trip.end_h, DECIMALS) == first_points[line]
            checked += 1
    assert checked


def test_each_crew_order_row_is_the_engines_key() -> None:
    world = pilot()[1].world
    rows = tables()["crew_order"]
    assert rows
    keys = [crew_order(world, str(r["job"]).removeprefix("repair:")) for r in rows]
    assert keys == sorted(keys)
    for row, (group, weight) in zip(rows, keys, strict=True):
        assert row["group"] == group
        assert row["lifeline_weight"] == (-weight if weight else None)
    assert {r["class"]: r["lifeline_weight"] for r in tables()["lifeline_weights"]} == {
        c.value: w for c, w in LIFELINE_WEIGHTS.items()}  # fmt: skip


def test_each_travel_row_is_the_trip_from_base() -> None:
    world = pilot()[1].world
    base = world.crews[0].site
    for row, node in zip(tables()["travel"], world.nodes, strict=True):
        legs = world.legs(Site(base), Site(node.site))
        assert row["road_km"] == round(legs.road_km, DECIMALS)
        assert row["travel_h_from_base"] == round(trip_hours(legs, world.settings), DECIMALS)


def test_the_rules_sheet_reads_the_registry_and_the_engine() -> None:
    built, engine = pilot()
    rows = {r["rule"]: r for r in tables()["rules"]}
    for rule_id, _ in ENGINE_RULES:
        assert rows[rule_id]["value"] == built.rules.value(rule_id)
        assert rows[rule_id]["units"] == built.rules.rule(rule_id).units
    settings = engine.world.settings
    assert float(rows["dynamics.step_min"]["value"]) / 60.0 == settings.step_h  # type: ignore[arg-type]
    assert rows["dynamics.trip_point"]["value"] == settings.trip_point
    assert rows["repair.crew_bound_lead_h"]["value"] == settings.crew_bound_lead_h
    assert rows["crews.offroad_speed_kmh"]["value"] == settings.offroad_kmh
    for kind, refill in REFILL.items():
        assert rows[f"refill: {kind}"]["value"] == refill


def test_every_table_that_may_be_empty_declares_its_columns() -> None:
    for name, columns in COLUMNS.items():
        rows = tables()[name]
        if rows:
            assert tuple(rows[0]) == columns, name
    assert tables()["damage_facilities"] == []


# --- The blind pack holds no reference-run value (A1, A5) -----------------------------------


def test_the_blind_pack_does_not_depend_on_the_run() -> None:
    plain = trace_pack(inputs())
    # Protecting the towered line changes the whole run; the blind pack must not move.
    other = trace_pack(inputs((Protect("SWM-POW-L0004"),)))
    assert plain.answer != other.answer
    assert plain.map_pdf == other.map_pdf
    assert plain.tables_pdf == other.tables_pdf
    assert plain.rules_pdf == other.rules_pdf
    assert plain.tables == other.tables
    assert "timeline" not in plain.tables


def test_the_map_insets_the_crowded_clusters() -> None:
    groups = clusters(inputs())
    assert groups
    seen = [node for group in groups for node in group]
    assert len(seen) == len(set(seen))
    assert "SWM-POW-0001" in groups[0]
