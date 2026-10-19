"""The printable hand-trace pack: what a person needs to play one scenario forward by hand.

The pack is split so a tracer can work blind (Work Order 9, A1):
- ``trace_pack/`` is the blind pack: a one-page map, a one-page rules sheet and the tables,
  each as PDF pages and as CSV. Nothing in it comes from the reference run.
- ``trace_pack/answer/`` holds the reference run's timeline, hour by hour with the crews' jobs:
  the saved run's own values, printed separately so it can be set aside.

Every number in the tables is read from the world the engine plays out (``EngineWorld``) or from
the registry, never typed. The blind tables:
- **nodes:** layer, class, end use and service weight, capacities, requirement, own-layer
  response and the failure mode per commodity;
- **stocks**, **generators** and **tolerance:** each stock's quantity, units, draw per hour and
  refill; each generator's fail-to-start and run-hours draws; each telecom tolerance row (T, d,
  κ, d_eff) and whether manual switching applies;
- **dependencies:** supplier, consumer, commodity, κ, transfer form, feed configuration and
  whether the edge is a fuel-resupply edge;
- **links:** every within-layer link with its length, whether it stands on towers, the commodity
  it carries and its direction of flow;
- **damage_lines** and **damage_facilities:** each failure point's position along its line, its
  travel from the crew base and its crew work; each damaged facility's state, crew work and
  parts lead time;
- **crews**, **travel**, **crew_order** and **lifeline_weights:** the crews and their base, the
  trip from the base to every node, each repair job's group in the default crew order;
- **rules:** every engine number a trace uses, with its registry id.

The PDFs are written with a fixed producer, no creation date and no stream compression, so they
are identical on every platform. Needs the optional ``preview`` dependencies.

Spec: structure v0.12 §4.5 and §4.6 (printable hand-trace pack); Work Order 8, Part D; Work
Order 9, Part A.
"""

import io
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np

from swm.coordinates import domain_origin_m
from swm.dynamics.engine import crew_order, trip_hours
from swm.dynamics.output import state_rows
from swm.dynamics.records import Run
from swm.dynamics.travel import Site
from swm.dynamics.world import REFILL, Damage, EngineWorld
from swm.recipe.dependencies import Role
from swm.recipe.schema import LIFELINE_WEIGHTS, Layer
from swm.rules.registry import Registry
from swm.stages.buffers import BuffersResult
from swm.stages.couplings import CouplingsResult
from swm.stages.crews import CrewsResult
from swm.stages.layers import LayersResult
from swm.stages.repair import RepairResult
from swm.stages.requirements import RequirementsResult
from swm.stages.scenarios import OverheadLine, ScenarioDamage
from swm.stages.storm import StormScenario
from swm.stages.strength import StrengthResult
from swm.stages.terrain import TerrainResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

PRODUCER = "swm trace-pack"
ToKm = Callable[[tuple[float, float]], tuple[float, float]]
LINES_PER_PAGE = 58
DECIMALS = 6
"""Places kept for a computed length, distance or time in the tables (layout only)."""
M_PER_KM = 1000.0
MAP_MARGIN_KM = 1.0
"""White space around the island on the map (layout only)."""
CLUSTER_RADIUS_KM = 2.5
"""Nodes this close to a crowded node are drawn again in a larger-scale inset (layout only)."""
CLUSTER_MIN_NODES = 4
"""The fewest nodes that make a crowded neighbourhood worth an inset (layout only)."""
LABEL_CLEARANCE_KM = 0.5
"""Two nodes this close label on opposite sides (layout only)."""
MAX_INSETS = 2
"""Insets the page holds beside the main map (layout only)."""
INSET_MARGIN_KM = 0.6
"""White space around the inset's nodes (layout only)."""
LAYER_COLOURS = {
    Layer.POWER: "#2ca02c", Layer.TELECOM: "#9467bd", Layer.WATER: "#1f77b4",
    Layer.TRANSPORT: "#ff7f0e", Layer.FUEL: "#8c564b", Layer.HEALTHCARE: "#e377c2",
}  # fmt: skip
DAMAGE_COLOUR = "#d62728"
"""Damage is red, so no layer is drawn red."""
TRACK_COLOUR = "black"
MARKERS = {Layer.POWER: "s", Layer.TELECOM: "^", Layer.WATER: "o", Layer.TRANSPORT: "D",
           Layer.FUEL: "v", Layer.HEALTHCARE: "P"}  # fmt: skip
COMMODITY = {
    Layer.POWER: "electricity", Layer.TELECOM: "telecom service", Layer.WATER: "water",
    Layer.FUEL: "fuel", Layer.TRANSPORT: "none (roads: crew travel only)",
    Layer.HEALTHCARE: "none (patient referral)",
}  # fmt: skip
"""What a within-layer link carries in the engine (ruling D4): only the four flow layers."""

ENGINE_RULES = (
    ("dynamics.step_min", "step length"),
    ("dynamics.settling_cap_passes", "settling cap"),
    ("dynamics.trip_point", "trip point"),
    ("reserves.hospital.essential_load_fraction", "floor (hospital on generator)"),
    ("dynamics.threshold", "threshold θ (logistic and control edges)"),
    ("repair.crew_bound_lead_h", "crew-bound lead per job"),
    ("storm.line_crew_work_h", "line work per failure point"),
    ("storm.tower_crew_work_h", "line work per towered failure point"),
    ("repair.manual_switching_h", "manual switching on site"),
    ("crews.road_speed_kmh", "road speed"),
    ("crews.offroad_speed_kmh", "off-road speed"),
    ("crews.outlying_island_mobilisation_h", "sea-trip mobilisation"),
    ("reserves.battery_recharge_h", "battery recharge, empty to full"),
    ("reserves.fuel_resupply.lead_time_h", "fuel delivery lead time"),
    ("reserves.fuel_resupply.delivery_h", "fuel delivery interval"),
    ("reserves.main_refill_rate_fraction", "refill from the main, share of drain rate"),
    ("dynamics.horizon_h", "horizon"),
)
"""Every registry number a hand trace uses, in the order a trace meets them (A3)."""

COLUMNS: Mapping[str, tuple[str, ...]] = {
    "stocks": (
        "stock",
        "node",
        "kind",
        "covers",
        "quantity",
        "units",
        "draw_per_h",
        "hours",
        "refill",
        "generator_fuel",
        "rule",
    ),
    "generators": ("node", "fails_to_start", "run_hours_to_failure"),
    "tolerance": (
        "dependency",
        "consumer",
        "rule",
        "T_h",
        "ramp_to_h",
        "d",
        "kappa_public_share",
        "d_eff",
        "manual_switching",
    ),
    "damage_lines": (
        "line",
        "structure",
        "peak_gust_m_per_s",
        "failure_point",
        "km_along_line",
        "road_km",
        "offroad_km",
        "by_sea",
        "travel_h_from_base",
        "crew_work_h",
    ),
    "damage_facilities": (
        "node",
        "damage_state",
        "flood_depth_m",
        "repairable",
        "crew_work_h",
        "parts_lead_h",
    ),
    "crew_order": ("job", "group", "lifeline_weight", "why"),
}
"""The header of each table a scenario or world may leave empty, so an empty one still prints
its columns."""

NOTES = {
    "links": (
        "A node fed by more than one link of its own layer takes the largest upstream output "
        "(capped at 1); a link on a failed line passes nothing until repaired.",
        "A commodity with more than one feed group: each group delivers the smallest κ x g "
        "among its edges, the groups are summed, capped at 1 (telecom edges deliver g alone). "
        "A node's state is its condition x the lowest response across its commodities.",
    ),
    "crew_order": (
        "A free crew takes the open job with the smallest key (group, then -Lifeline weight), "
        "then the shortest trip from where it stands, then the lowest job id. It travels by "
        "road, then off road to a line; it never returns to base between jobs.",
    ),
}
"""The engine's combining and travel rules, one sentence each, printed with their tables."""


@dataclass(frozen=True)
class TraceInputs:
    """What the pack is drawn from."""

    scenario: int
    terrain: TerrainResult
    layers: LayersResult
    requirements: RequirementsResult
    couplings: CouplingsResult
    strength: StrengthResult
    buffers: BuffersResult
    crews: CrewsResult
    repair: RepairResult
    field: StormScenario
    damage: ScenarioDamage
    lines: tuple[OverheadLine, ...]
    world: EngineWorld
    """The world the engine plays out: every table value is read from it or the registry."""
    engine_damage: Damage
    """The scenario's damage as the engine takes it, with each failure point's site."""
    rules: Registry
    run: Run
    """The reference run: read only by the answer pack."""


@dataclass(frozen=True)
class TracePack:
    """The blind pack's PDFs and tables, and the answer's."""

    map_pdf: bytes
    tables_pdf: bytes
    rules_pdf: bytes
    tables: dict[str, list[dict[str, object]]]
    """The blind tables, ``rules`` included, as rows for CSV."""
    answer_pdf: bytes
    answer: dict[str, list[dict[str, object]]]


def trace_pack(inputs: TraceInputs) -> TracePack:
    """Build the hand-trace pack for one scenario.

    Parameters
    ----------
    inputs : TraceInputs
        The world's stages, the engine's world, the scenario's storm field and damage, the
        registry and the reference run.

    Returns
    -------
    TracePack
        The blind pack (map, rules sheet, tables) and the answer (the timeline).

    Spec: Work Order 9, A1-A4.
    """
    tables = blind_tables(inputs)
    rules = tables.pop("rules")
    answer = {"timeline": timeline_rows(inputs.run)}
    return TracePack(
        map_pdf=_map_pdf(inputs),
        tables_pdf=_tables_pdf(inputs.scenario, tables),
        rules_pdf=_tables_pdf(inputs.scenario, {"rules": rules}),
        tables={**tables, "rules": rules},
        answer_pdf=_tables_pdf(inputs.scenario, answer),
        answer=answer,
    )


def blind_tables(inputs: TraceInputs) -> dict[str, list[dict[str, object]]]:
    """Return every blind table: none reads the reference run (A1).

    Parameters
    ----------
    inputs : TraceInputs
        As for ``trace_pack``.

    Returns
    -------
    dict
        Table name to rows, in print order.

    Spec: Work Order 9, A2-A3.
    """
    return {
        "nodes": node_rows(inputs),
        "stocks": stock_rows(inputs),
        "generators": generator_rows(inputs),
        "tolerance": tolerance_rows(inputs),
        "dependencies": dependency_rows(inputs),
        "links": link_rows(inputs),
        "damage_lines": damage_line_rows(inputs),
        "damage_facilities": damage_facility_rows(inputs),
        "crews": crew_rows(inputs),
        "travel": travel_rows(inputs),
        "crew_order": crew_order_rows(inputs),
        "lifeline_weights": [
            {"class": end_use.value, "lifeline_weight": weight}
            for end_use, weight in LIFELINE_WEIGHTS.items()
        ],
        "rules": rule_rows(inputs.rules),
    }


# --- Node tables (A2) -----------------------------------------------------------------------


def node_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return one row per node: class, end use, capacities, requirement and responses."""
    needs = inputs.requirements.by_id()
    stage_nodes = {n.node_id: n for n in inputs.layers.nodes}
    modes: dict[str, list[str]] = {}
    for dependency in inputs.world.dependencies:
        floor = "" if dependency.floor is None else f" (floor {dependency.floor:g})"
        modes.setdefault(dependency.consumer_id, []).append(
            f"{dependency.supplier_layer.value}: {dependency.mode}{floor}"
        )
    rows: list[dict[str, object]] = []
    for node in inputs.world.nodes:
        need = needs[node.node_id]
        attributes = dict(stage_nodes[node.node_id].attributes)
        requirement = [
            f"{name} {value:g}"
            for name, value in (("MW", need.electricity_mw), ("m3/day", need.water_m3_per_day),
                                ("GJ/day", need.fuel_gj_per_day))
            if value is not None
        ]  # fmt: skip
        rows.append({
            "node": node.node_id,
            "layer": node.layer.value,
            "class": node.node_class.value,
            "end_use": "yes" if node.end_use_weight is not None else "no",
            "service_weight": node.end_use_weight,
            "capacity_mw": attributes.get("capacity_mw"),
            "capacity_m3_per_day": attributes.get("capacity_m3_per_day"),
            "requirement": "; ".join(requirement),
            "own_layer_response": "source" if node.source else node.own_mode,
            "failure_modes": "; ".join(sorted(modes.get(node.node_id, []))),
        })  # fmt: skip
    return rows


def stock_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return each stock: quantity, units, draw per hour, the hours it lasts and its refill."""
    units = {(r.node_id, r.kind): r.stock_units for r in inputs.buffers.reserves}
    return [
        {
            "stock": stock.stock_id,
            "node": stock.node_id,
            "kind": stock.kind,
            "covers": stock.covers.value,
            "quantity": stock.capacity,
            "units": units[(stock.node_id, stock.kind)],
            "draw_per_h": stock.draw_per_h,
            "hours": round(stock.capacity / stock.draw_per_h, DECIMALS)
            if stock.draw_per_h > 0.0
            else None,
            "refill": stock.refill,
            "generator_fuel": "yes" if stock.generator else "no",
            "rule": stock.rule_id,
        }
        for stock in inputs.world.stocks
    ]


def generator_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return each standby generator's drawn behaviour: fails to start, hours until it stops."""
    return [
        {
            "node": generator.node_id,
            "fails_to_start": "yes" if generator.fails_to_start else "no",
            "run_hours_to_failure": generator.run_hours_to_failure,
        }
        for generator in inputs.world.generators
    ]


def tolerance_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return each telecom tolerance row: T, d, κ (the public share), d_eff, manual switching."""
    rows = {t.dependency_id: t for t in inputs.buffers.tolerance}
    result: list[dict[str, object]] = []
    for dependency in inputs.world.dependencies:
        tolerance = dependency.tolerance
        if tolerance is None:
            continue
        row = rows[dependency.dependency_id]
        result.append({
            "dependency": dependency.dependency_id,
            "consumer": dependency.consumer_id,
            "rule": tolerance.rule_id,
            "T_h": tolerance.t_h,
            "ramp_to_h": tolerance.ramp_to_h,
            "d": row.d,
            "kappa_public_share": row.public_share,
            "d_eff": tolerance.d_eff,
            "manual_switching": "yes" if row.manual_switching else "no",
        })  # fmt: skip
    return result


def dependency_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return one row per coupling edge: supplier, consumer, commodity, κ, form and feeds."""
    kappa = {s.edge_id: s.kappa for s in inputs.strength.edges}
    return [
        {
            "edge": edge.edge_id,
            "dependency": edge.dependency_id,
            "supplier": edge.supplier_id,
            "consumer": edge.consumer_id,
            "commodity": edge.commodity,
            "kappa": round(kappa[edge.edge_id], DECIMALS),
            "transfer_form": edge.transfer_form,
            "feed_configuration": edge.feed_configuration.value,
            "feed_group": edge.feed_group,
            "fuel_resupply": "yes" if edge.role == Role.BUFFER_RESUPPLY else "no",
            "switched_on": edge.switched_on,
        }
        for edge in sorted(inputs.couplings.edges, key=lambda e: e.edge_id)
    ]


# --- Links (A2) -----------------------------------------------------------------------------


def link_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return every within-layer link: ends, length, towers, commodity and direction of flow."""
    flows: dict[str, list[tuple[str, str]]] = {}
    for carried in inputs.world.links:
        flows.setdefault(carried.link_id, []).append((carried.upstream_id, carried.downstream_id))
    rows: list[dict[str, object]] = []
    for link in sorted(inputs.layers.links, key=lambda link: link.link_id):
        directions = flows.get(link.link_id, [])
        if not directions:
            flow = "none"
        elif len(directions) > 1:
            flow = "both ways"
        else:
            flow = f"{directions[0][0]} -> {directions[0][1]}"
        rows.append({
            "link": link.link_id,
            "layer": link.layer.value,
            "from": link.from_id,
            "to": link.to_id,
            "length_km": round(polyline_km(link.points), DECIMALS),
            "on_towers": "yes" if link.link_id in inputs.world.towered else "no",
            "commodity": COMMODITY[link.layer],
            "flow": flow,
        })  # fmt: skip
    return rows


def polyline_km(points: Sequence[tuple[float, float]]) -> float:
    """Return a polyline's length in km (sqrt only)."""
    total_m = 0.0
    for a, b in pairwise(points):
        total_m += math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]))
    return total_m / M_PER_KM


# --- Damage, crews and travel (A2) ----------------------------------------------------------


def damage_line_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return each failed line's failure points: position, travel from the base, crew work."""
    gusts = {o.line_id: o.peak_gust_m_per_s for o in inputs.damage.failed_lines}
    structures = {line.line_id: line.structure.value for line in inputs.lines}
    base = inputs.world.crews[0].site
    rows: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for point in inputs.engine_damage.failure_points:
        counts[point.line_id] = counts.get(point.line_id, 0) + 1
        legs = inputs.world.legs(Site(base), Site(point.site, on_line=True))
        rows.append({
            "line": point.line_id,
            "structure": structures[point.line_id],
            "peak_gust_m_per_s": round(gusts[point.line_id], 3),
            "failure_point": counts[point.line_id],
            "km_along_line": point.km,
            "road_km": round(legs.road_km, DECIMALS),
            "offroad_km": round(legs.offroad_km, DECIMALS),
            "by_sea": "yes" if legs.by_sea else "no",
            "travel_h_from_base": round(trip_hours(legs, inputs.world.settings), DECIMALS),
            "crew_work_h": point.crew_work_h,
        })  # fmt: skip
    return rows


def damage_facility_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return each damaged facility: damage state, crew work and parts lead time."""
    repairs = {r.node_id: r for r in inputs.world.repairs}
    unrepairable = set(inputs.world.unrepairable)
    rows: list[dict[str, object]] = []
    for facility in inputs.damage.facilities:
        repair = repairs.get(facility.node_id)
        rows.append({
            "node": facility.node_id,
            "damage_state": facility.damage_state.value,
            "flood_depth_m": round(facility.flood_depth_m, 3),
            "repairable": "no" if facility.node_id in unrepairable else "yes",
            "crew_work_h": None if repair is None else repair.crew_work_h,
            "parts_lead_h": None if repair is None else repair.parts_lead_h,
        })  # fmt: skip
    return rows


def crew_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return each crew, its base and where the base stands on the map."""
    bases = {crew.crew_id: crew.base_id for crew in inputs.crews.crews}
    km = _km(inputs.terrain)
    rows: list[dict[str, object]] = []
    for crew in inputs.world.crews:
        x, y = km(crew.site)
        rows.append({
            "crew": crew.crew_id,
            "base": bases[crew.crew_id],
            "base_km_east": round(x, DECIMALS),
            "base_km_north": round(y, DECIMALS),
        })  # fmt: skip
    return rows


def travel_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return the trip from each crew base to every node: road km, off-road km, hours."""
    bases = {crew.site for crew in inputs.world.crews}
    rows: list[dict[str, object]] = []
    for base in sorted(bases):
        for node in inputs.world.nodes:
            legs = inputs.world.legs(Site(base), Site(node.site))
            rows.append({
                "node": node.node_id,
                "road_km": round(legs.road_km, DECIMALS),
                "offroad_km": round(legs.offroad_km, DECIMALS),
                "by_sea": "yes" if legs.by_sea else "no",
                "travel_h_from_base": round(trip_hours(legs, inputs.world.settings), DECIMALS),
            })  # fmt: skip
    return rows


def crew_order_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return each repair job's place in the default crew order, with the weight used."""
    elements = [*inputs.engine_damage.lines, *inputs.engine_damage.nodes]
    keyed = sorted((crew_order(inputs.world, e), e) for e in elements)
    return [
        {
            "job": f"repair:{element}",
            "group": group,
            "lifeline_weight": -weight if weight else None,
            "why": _why(inputs.world, element, group),
        }
        for (group, weight), element in keyed
    ]


def _why(world: EngineWorld, element_id: str, group: int) -> str:
    if group == 0:
        return "towered line" if element_id in world.towered else "transmission substation"
    if group == 1:
        if element_id in world.feeds_to_end_use:
            return "power feed to an end-use node"
        return "distribution substation"
    return "everything else"


def rule_rows(rules: Registry) -> list[dict[str, object]]:
    """Return every engine number a trace uses, read from the registry, and the refill rules."""
    rows: list[dict[str, object]] = [
        {
            "rule": rule_id,
            "what": what,
            "value": rules.value(rule_id),
            "units": rules.rule(rule_id).units,
        }
        for rule_id, what in ENGINE_RULES
    ]
    rows += [
        {"rule": f"refill: {kind}", "what": "how the stock refills", "value": refill,
         "units": None}
        for kind, refill in REFILL.items()
    ]  # fmt: skip
    rows.append({"rule": "refill: any other kind", "what": "how the stock refills",
                 "value": "none", "units": None})  # fmt: skip
    return rows


def timeline_rows(run: Run) -> list[dict[str, object]]:
    """Return the reference run's states and crew jobs hour by hour (its own values)."""
    per_hour = int(1.0 / run.step_h + 0.5)
    states = state_rows(run)
    rows = []
    for index in range(0, len(run.times), per_hour):
        row: dict[str, object] = dict(states[index])
        for crew, doing in run.crew_positions[index]:
            row[crew] = doing
        rows.append(row)
    return rows


# --- The map (A4) ---------------------------------------------------------------------------


def _km(terrain: TerrainResult) -> ToKm:
    west_m, south_m = domain_origin_m(terrain.grid)

    def km(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] - west_m) / M_PER_KM, (point[1] - south_m) / M_PER_KM

    return km


def _island_frame(terrain: TerrainResult) -> tuple[float, float, float, float]:
    """Return the land's extent in map km: west, east, south, north."""
    cell_km = terrain.grid.cell_size_m / M_PER_KM
    side_km = terrain.grid.cells * cell_km
    rows, columns = np.nonzero(terrain.land)
    west, east = float(columns.min()) * cell_km, float(columns.max() + 1) * cell_km
    south, north = side_km - float(rows.max() + 1) * cell_km, side_km - float(rows.min()) * cell_km
    return west, east, south, north


def clusters(inputs: TraceInputs) -> tuple[tuple[str, ...], ...]:
    """Return the crowded neighbourhoods drawn again at a larger scale, busiest first (A4).

    The busiest node has the most nodes within ``CLUSTER_RADIUS_KM`` (the lowest id on a tie);
    its cluster is it and those neighbours. The next cluster is found among the nodes left, up
    to ``MAX_INSETS``, while a cluster holds at least ``CLUSTER_MIN_NODES``.

    Parameters
    ----------
    inputs : TraceInputs
        As for ``trace_pack``.

    Returns
    -------
    tuple of tuple of str
        Each cluster's node ids, sorted.

    Spec: Work Order 9, A4 (an inset wherever labels collide).
    """
    sites = {n.node_id: n.site for n in inputs.world.nodes}
    reach_m = CLUSTER_RADIUS_KM * M_PER_KM
    left = set(sites)
    found: list[tuple[str, ...]] = []

    def near(a: str) -> tuple[str, ...]:
        ax, ay = sites[a]
        return tuple(sorted(
            b for b in left
            if (sites[b][0] - ax) * (sites[b][0] - ax) + (sites[b][1] - ay) * (sites[b][1] - ay)
            <= reach_m * reach_m
        ))  # fmt: skip

    while left and len(found) < MAX_INSETS:
        busiest = min(left, key=lambda a: (-len(near(a)), a))
        members = near(busiest)
        if len(members) < CLUSTER_MIN_NODES:
            break
        found.append(members)
        left -= set(members)
    return tuple(found)


def _map_pdf(inputs: TraceInputs) -> bytes:
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle

    figure = Figure(figsize=(11.69, 8.27))
    main = figure.add_axes((0.04, 0.05, 0.60, 0.88))
    km = _km(inputs.terrain)
    sites = {n.node_id: km(n.site) for n in inputs.world.nodes}
    groups = clusters(inputs)
    insets = [figure.add_axes((0.66, 0.53 - 0.47 * i, 0.32, 0.40)) for i in range(len(groups))]
    in_inset = {node_id for group in groups for node_id in group}
    for axes in (main, *insets):
        _land(axes, inputs.terrain)
        _overhead(axes, inputs, km)
        _couplings(axes, inputs, km)
        _failure_points(axes, inputs, km)
        _nodes(axes, inputs, km, skip=in_inset if axes is main else set())
        _base(axes, inputs, km)
        axes.set_aspect("equal")
        axes.tick_params(labelsize=6)
    west, east, south, north = _island_frame(inputs.terrain)
    main.set_xlim(west - MAP_MARGIN_KM, east + MAP_MARGIN_KM)
    main.set_ylim(south - MAP_MARGIN_KM, north + MAP_MARGIN_KM)
    for index, (axes, group) in enumerate(zip(insets, groups, strict=True)):
        xs, ys = [sites[n][0] for n in group], [sites[n][1] for n in group]
        box = (min(xs) - INSET_MARGIN_KM, max(xs) + INSET_MARGIN_KM,
               min(ys) - INSET_MARGIN_KM, max(ys) + INSET_MARGIN_KM)  # fmt: skip
        name = "AB"[index]
        main.add_patch(Rectangle((box[0], box[2]), box[1] - box[0], box[3] - box[2], fill=False,
                                 linestyle=":", linewidth=0.8, edgecolor="black"))  # fmt: skip
        main.annotate(f"inset {name}", (box[0], box[3]), fontsize=6, xytext=(0, 2),
                      textcoords="offset points")  # fmt: skip
        axes.set_xlim(box[0], box[1])
        axes.set_ylim(box[2], box[3])
        axes.set_title(f"Inset {name}: {len(group)} nodes at a larger scale", fontsize=7)
    _storm_inset(main.inset_axes((0.01, 0.01, 0.34, 0.34)), inputs)
    main.set_xlabel("km east", fontsize=7)
    main.set_ylabel("km north", fontsize=7)
    figure.suptitle(
        f"Hand-trace map, scenario {inputs.scenario}: nodes; links; overhead lines and power "
        "feeds with ids; switched-on couplings (arrows); crew base (star); failure points (x); "
        "damage in red",
        fontsize=8,
    )
    return pdf_pages([figure])


def _land(axes: "Axes", terrain: TerrainResult) -> None:
    side_km = terrain.grid.cells * terrain.grid.cell_size_m / M_PER_KM
    axes.contour(terrain.land.astype(float), levels=[0.5], colors="#888888", linewidths=0.6,
                 extent=(0, side_km, side_km, 0))  # fmt: skip


def _overhead(axes: "Axes", inputs: TraceInputs, km: ToKm) -> None:
    """Draw every within-layer link, and label every overhead line and feed with its id."""
    down = set(inputs.engine_damage.lines)
    for link in inputs.layers.links:
        points = [km(p) for p in link.points]
        axes.plot([p[0] for p in points], [p[1] for p in points],
                  color=DAMAGE_COLOUR if link.link_id in down else LAYER_COLOURS[link.layer],
                  linewidth=1.6 if link.layer == Layer.POWER else 0.8,
                  linestyle="--" if link.link_id in down else "-", alpha=0.85)  # fmt: skip
    for towered in inputs.layers.power_lines:
        points = [km(p) for p in towered.tower_points]
        axes.plot([p[0] for p in points], [p[1] for p in points], linestyle="", marker=".",
                  markersize=2.0, color="black")  # fmt: skip
    for line in inputs.lines:
        points = [km(p) for p in line.points]
        if line.kind.value == "power_feed":
            axes.plot([p[0] for p in points], [p[1] for p in points], color="#555555",
                      linewidth=0.5, linestyle=":")  # fmt: skip
        middle = points[len(points) // 2]
        axes.annotate(line.line_id.replace("SWM-", ""), middle, fontsize=4.2, clip_on=True,
                      color=DAMAGE_COLOUR if line.line_id in down else "#333333")  # fmt: skip


def _couplings(axes: "Axes", inputs: TraceInputs, km: ToKm) -> None:
    from matplotlib.patches import FancyArrowPatch

    sites = {n.node_id: n.site for n in inputs.world.nodes}
    for edge in inputs.couplings.edges:
        if not edge.switched_on:
            continue
        # A patch on the axes is clipped to them, so an arrow never runs off its panel.
        axes.add_patch(FancyArrowPatch(
            km(sites[edge.supplier_id]), km(sites[edge.consumer_id]), arrowstyle="-|>",
            mutation_scale=7, linewidth=0.5, alpha=0.5, shrinkA=4, shrinkB=4,
            color=LAYER_COLOURS[edge.supplier_layer],
        ))  # fmt: skip


def _failure_points(axes: "Axes", inputs: TraceInputs, km: ToKm) -> None:
    for point in inputs.engine_damage.failure_points:
        x, y = km(point.site)
        axes.plot([x], [y], marker="x", color=DAMAGE_COLOUR, markersize=7, markeredgewidth=1.4)
        axes.annotate(f"{point.line_id.replace('SWM-', '')} at {point.km:g} km", (x, y),
                      fontsize=4.5, color=DAMAGE_COLOUR, xytext=(4, -6),
                      textcoords="offset points", clip_on=True)  # fmt: skip


def _nodes(axes: "Axes", inputs: TraceInputs, km: ToKm, skip: set[str]) -> None:
    damaged = set(inputs.engine_damage.nodes)
    crowded_ids = crowded(inputs)
    for node in inputs.world.nodes:
        x, y = km(node.site)
        colour = DAMAGE_COLOUR if node.node_id in damaged else LAYER_COLOURS[node.layer]
        axes.plot([x], [y], marker=MARKERS[node.layer], markersize=6, markeredgecolor="black",
                  markeredgewidth=0.5, color=colour)  # fmt: skip
        if node.node_id in skip:
            continue
        label = f"{node.node_id.replace('SWM-', '')}\n{node.node_class.value}"
        # A node close to one with a lower id labels to the left and below, so the two clear.
        left = node.node_id in crowded_ids
        axes.annotate(label, (x, y), fontsize=5, xytext=(-4, -9) if left else (4, 2),
                      textcoords="offset points", ha="right" if left else "left",
                      clip_on=True)  # fmt: skip


def crowded(inputs: TraceInputs, clearance_km: float = 0.0) -> set[str]:
    """Return the nodes within a clearance (``LABEL_CLEARANCE_KM`` if 0) of a lower-id node."""
    reach_m = (clearance_km or LABEL_CLEARANCE_KM) * M_PER_KM
    nodes = inputs.world.nodes
    return {
        b.node_id for a in nodes for b in nodes
        if a.node_id < b.node_id
        and (b.site[0] - a.site[0]) * (b.site[0] - a.site[0])
        + (b.site[1] - a.site[1]) * (b.site[1] - a.site[1]) <= reach_m * reach_m
    }  # fmt: skip


def _base(axes: "Axes", inputs: TraceInputs, km: ToKm) -> None:
    for site in sorted({crew.site for crew in inputs.world.crews}):
        x, y = km(site)
        axes.plot([x], [y], marker="*", color="black", markersize=11)


def _storm_inset(axes: "Axes", inputs: TraceInputs) -> None:
    """Draw the island small, the storm track as an arrow and its closest approach (A4)."""
    from matplotlib.patches import FancyArrowPatch

    terrain = inputs.terrain
    side_km = terrain.grid.cells * terrain.grid.cell_size_m / M_PER_KM
    _land(axes, terrain)
    axes.set_xticks([])
    axes.set_yticks([])
    west, east, south, north = _island_frame(terrain)
    track = inputs.field.track
    if track is None:
        axes.set_xlim(west, east)
        axes.set_ylim(south, north)
        axes.set_title("No storm track in this scenario", fontsize=6)
        return
    (x, y), (east_step, south_step) = track.point_km, track.direction
    # The map's y runs north and the track's south: on the map the track runs (east, -south).
    centre = ((west + east) / 2.0, (south + north) / 2.0)
    along = (centre[0] - x) * east_step + (centre[1] - (side_km - y)) * -south_step
    nearest = (x + along * east_step, side_km - y - along * south_step)
    reach = (north - south) / 2.0
    start = (nearest[0] - reach * east_step, nearest[1] + reach * south_step)
    end = (nearest[0] + reach * east_step, nearest[1] - reach * south_step)
    axes.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10,
                                   linewidth=1.4, color=TRACK_COLOUR))  # fmt: skip
    axes.plot([centre[0], nearest[0]], [centre[1], nearest[1]], linestyle=":", linewidth=0.8,
              color=TRACK_COLOUR)  # fmt: skip
    xs, ys = [west, east, start[0], end[0]], [south, north, start[1], end[1]]
    axes.set_xlim(min(xs) - MAP_MARGIN_KM, max(xs) + MAP_MARGIN_KM)
    axes.set_ylim(min(ys) - MAP_MARGIN_KM, max(ys) + MAP_MARGIN_KM)
    axes.set_aspect("equal")
    axes.set_title(f"Storm track: closest approach {track.closest_approach_km:g} km",
                   fontsize=6)  # fmt: skip
    axes.set_facecolor("white")


# --- PDF pages ------------------------------------------------------------------------------


def _tables_pdf(scenario: int, tables: Mapping[str, list[dict[str, object]]]) -> bytes:
    from matplotlib.figure import Figure

    figures = []
    for name, rows in tables.items():
        notes = list(NOTES.get(name, ()))
        lines = notes + ([""] if notes else []) + _text_table(rows, COLUMNS.get(name, ()))
        for start in range(0, max(1, len(lines)), LINES_PER_PAGE):
            figure = Figure(figsize=(11.69, 8.27))
            page = start // LINES_PER_PAGE + 1
            figure.text(0.02, 0.97, f"Scenario {scenario}: {name} (page {page})", fontsize=10,
                        va="top")  # fmt: skip
            figure.text(0.02, 0.93, "\n".join(lines[start:start + LINES_PER_PAGE]), fontsize=5.2,
                        family="monospace", va="top")  # fmt: skip
            figures.append(figure)
    return pdf_pages(figures)


def _text_table(rows: Sequence[Mapping[str, object]], empty: Sequence[str]) -> list[str]:
    if not rows:
        return ["  ".join(empty), "(none)"] if empty else ["(none)"]
    columns = list(rows[0])
    cells = [[_text(row.get(c)) for c in columns] for row in rows]
    widths = [max(len(c), *(len(r[i]) for r in cells)) for i, c in enumerate(columns)]
    head = "  ".join(c.ljust(w) for c, w in zip(columns, widths, strict=True))
    return [head] + ["  ".join(v.ljust(w) for v, w in zip(r, widths, strict=True)) for r in cells]


def _text(value: object) -> str:
    return "" if value is None else str(value)


def pdf_pages(figures: Sequence["Figure"]) -> bytes:
    """Write figures as one PDF with fixed metadata and no stream compression."""
    import matplotlib
    from matplotlib.backends.backend_pdf import PdfPages

    buffer = io.BytesIO()
    with matplotlib.rc_context({"pdf.compression": 0, "svg.hashsalt": "swm"}):
        metadata = {"Creator": PRODUCER, "Producer": PRODUCER, "CreationDate": None}
        with PdfPages(buffer, metadata=metadata) as pages:
            for figure in figures:
                pages.savefig(figure)
    return buffer.getvalue()
