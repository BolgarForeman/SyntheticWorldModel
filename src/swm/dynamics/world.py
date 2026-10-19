"""What the engine plays out: the world as nodes, edges, links, stocks and repairs.

The engine reads only this model, so a test can build a one-node world by hand and the
degradation profiles can be checked node by node. ``world_from_stages`` builds it from the
generator's stage outputs; nothing here draws a random number.

Spec: structure v0.9 §4.5; Work Order 7, D1-D4.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from swm.coordinates import cell_centre_m
from swm.dynamics.travel import LegFinder, straight_legs
from swm.recipe.dependencies import Role
from swm.recipe.schema import LIFELINE_WEIGHTS, EndUseClass, Layer, NodeClass
from swm.rules.registry import Registry
from swm.stages.buffers import BuffersResult, tolerance_rule
from swm.stages.couplings import CouplingsResult
from swm.stages.crews import CrewsResult
from swm.stages.layers import SIGNATURE_CHAINS, SIGNATURE_TIES, LayersResult, Node
from swm.stages.repair import RepairResult
from swm.stages.requirements import RequirementsResult
from swm.stages.scenarios import LineOutcome, OverheadLine, Structure
from swm.stages.strength import StrengthResult
from swm.stages.terrain import Grid

Point = tuple[float, float]

FLOW_LAYERS = (Layer.POWER, Layer.TELECOM, Layer.WATER, Layer.FUEL)
"""Layers whose links carry the layer's commodity (D4); roads and referral links carry none."""

SUBSTATIONS = frozenset({NodeClass.TRANSMISSION_SUBSTATION, NodeClass.DISTRIBUTION_SUBSTATION})

M_PER_KM = 1000.0


@dataclass(frozen=True)
class EngineNode:
    """One node as the engine sees it."""

    node_id: str
    layer: Layer
    node_class: NodeClass
    site: Point
    """EPSG:32710 metres."""
    source: bool
    """The first stage of its layer's signature: it takes nothing from its own layer."""
    own_mode: str | None
    """How it responds to a shortfall of its own layer's commodity; None for a source."""
    end_use_weight: float | None
    """Its Lifeline service weight if it is an end-use node, else None."""


@dataclass(frozen=True)
class EngineEdge:
    """One coupling edge: a supplier serving one dependency (§4.5: delivers κ x g_δ(x))."""

    edge_id: str
    supplier_id: str
    kappa: float
    transfer_form: str
    line_id: str | None
    """The overhead line the edge runs on (a power feed), or None."""


@dataclass(frozen=True)
class EngineDependency:
    """One consumer's need for one commodity, its feed groups and its response."""

    dependency_id: str
    consumer_id: str
    supplier_layer: Layer
    groups: tuple[tuple[EngineEdge, ...], ...]
    """Edges in a group are all needed; any one group serves (as the strength stage reads)."""
    mode: str
    """throttle, trip or step_to_floor (§4.4a, D2)."""
    floor: float | None
    tolerance: "Tolerance | None" = None


@dataclass(frozen=True)
class Tolerance:
    """A telecom tolerance row: full function for T hours, then d_eff (§4.4a)."""

    rule_id: str
    t_h: float
    d_eff: float
    ramp_to_h: float | None = None
    """Hosted hospital records: the level falls linearly from T to this hour."""


@dataclass(frozen=True)
class IntraLink:
    """A link that carries its layer's commodity from upstream to downstream (D4)."""

    link_id: str
    upstream_id: str
    downstream_id: str
    line: bool
    """An overhead line the storm can bring down (power and telecom links)."""


@dataclass(frozen=True)
class Stock:
    """A stock that covers its own commodity's shortfall at one node (§4.4a, D5)."""

    stock_id: str
    node_id: str
    kind: str
    covers: Layer
    capacity: float
    draw_per_h: float
    refill: str
    """battery, main, pumps, delivery or none (D5)."""
    rule_id: str
    """The registry limit that sets it, for relaxing (D11)."""
    generator: bool = False
    """Generator fuel: usable only while the set runs."""


@dataclass(frozen=True)
class Generator:
    """A standby generator's availability draw (§4.4a)."""

    node_id: str
    fails_to_start: bool
    run_hours_to_failure: float


@dataclass(frozen=True)
class Resupply:
    """Fuel deliveries to a generator tank on a buffer-resupply edge (D5)."""

    edge_id: str
    depot_id: str
    consumer_id: str
    stock_id: str
    delivery: float
    """Fuel per delivery, in the tank's units."""
    kappa: float
    transfer_form: str


@dataclass(frozen=True)
class FacilityRepair:
    """The permanent repair of one damaged node (§4.4a, D6)."""

    node_id: str
    parts_lead_h: float
    """max(0, Hazus lead time - crew-bound lead time); runs from hour 0 with no crew."""
    crew_work_h: float


@dataclass(frozen=True)
class Emergency:
    """A mobile unit that can restore one eligible node to a reduced share (§4.4a)."""

    node_id: str
    unit_kind: str
    arrival_h: float
    restored_share: float


@dataclass(frozen=True)
class FailurePoint:
    """One place a failed line must be repaired: a failed kilometre or a collapsed tower."""

    line_id: str
    km: float
    site: Point
    crew_work_h: float


@dataclass(frozen=True)
class Damage:
    """What the storm damaged at hour 0 in one scenario."""

    nodes: tuple[str, ...]
    lines: tuple[str, ...]
    failure_points: tuple[FailurePoint, ...]


@dataclass(frozen=True)
class CrewStart:
    """A repair crew and the site it starts from."""

    crew_id: str
    site: Point


@dataclass(frozen=True)
class EngineWorld:
    """Everything the engine plays out, built once per world."""

    nodes: tuple[EngineNode, ...]
    dependencies: tuple[EngineDependency, ...]
    links: tuple[IntraLink, ...]
    stocks: tuple[Stock, ...]
    generators: tuple[Generator, ...]
    resupply: tuple[Resupply, ...]
    repairs: tuple[FacilityRepair, ...]
    unrepairable: tuple[str, ...]
    emergencies: tuple[Emergency, ...]
    units: Mapping[str, int]
    """Mobile units per kind in the emergency pool."""
    crews: tuple[CrewStart, ...]
    feeds_to_end_use: Mapping[str, float]
    """Power feeds (line ids) to end-use consumers, with the consumer's Lifeline weight."""
    towered: frozenset[str]
    """Line ids on towers."""
    settings: "Settings"
    pump_capacity_m3_per_h: Mapping[str, float] = field(default_factory=dict)
    legs: LegFinder = straight_legs
    """How crews travel between sites: the world's roads, or straight lines in a test."""

    def node(self, node_id: str) -> EngineNode:
        """Return a node by id."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(node_id)


@dataclass(frozen=True)
class Settings:
    """The registry values the engine reads (§4.5), by rule."""

    trip_point: float
    threshold: float
    step_h: float
    settling_cap: int
    horizon_h: float
    crew_bound_lead_h: float
    manual_switching_h: float
    battery_recharge_h: float
    main_refill_fraction: float
    delivery_lead_h: float
    delivery_interval_h: float
    road_kmh: float
    offroad_kmh: float
    mobilisation_h: float
    substation_rank: str = "highest supplied weight"
    """How a distribution substation ranks in crew-order group 2.

    Read from ``dynamics.substation_crew_rank``.
    """


def settings_from(rules: Registry) -> Settings:
    """Return the engine's settings from the registry.

    Parameters
    ----------
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    Settings
        The values, by rule.

    Spec: structure v0.9 §4.5; Work Order 7, A2-A5.
    """
    return Settings(
        trip_point=rules.number("dynamics.trip_point"),
        threshold=rules.number("dynamics.threshold"),
        step_h=rules.number("dynamics.step_min") / 60.0,
        settling_cap=int(rules.number("dynamics.settling_cap_passes")),
        horizon_h=rules.number("dynamics.horizon_h"),
        crew_bound_lead_h=rules.number("repair.crew_bound_lead_h"),
        manual_switching_h=rules.number("repair.manual_switching_h"),
        battery_recharge_h=rules.number("reserves.battery_recharge_h"),
        main_refill_fraction=rules.number("reserves.main_refill_rate_fraction"),
        delivery_lead_h=rules.number("reserves.fuel_resupply.lead_time_h"),
        # Deliveries come every delivery_h hours, the 24 h a delivery carries (PR 7b answers).
        delivery_interval_h=rules.number("reserves.fuel_resupply.delivery_h"),
        road_kmh=rules.number("crews.road_speed_kmh"),
        offroad_kmh=rules.number("crews.offroad_speed_kmh"),
        mobilisation_h=rules.number("crews.outlying_island_mobilisation_h"),
        substation_rank=str(rules.value("dynamics.substation_crew_rank")),
    )


# --- Building the engine's world from the stages ---------------------------------------------


@dataclass(frozen=True)
class StageOutputs:
    """The generator's stage outputs the engine is built from."""

    layers: LayersResult
    requirements: RequirementsResult
    couplings: CouplingsResult
    strength: StrengthResult
    buffers: BuffersResult
    crews: CrewsResult
    repair: RepairResult
    lines: tuple[OverheadLine, ...]
    grid: Grid


STOCK_RULES: Mapping[tuple[str, str], str] = {
    ("generator_fuel", NodeClass.EXCHANGE): "reserves.exchange.fuel_h",
    ("generator_fuel", NodeClass.DATA_CENTRE): "reserves.data_centre.fuel_h",
    ("generator_fuel", NodeClass.CABLE_LANDING): "reserves.cable_landing.fuel_h",
    ("generator_fuel", NodeClass.TREATMENT): "reserves.treatment.fuel_h",
    ("generator_fuel", NodeClass.PUMPING): "reserves.pumping.portable_generator_fuel_h",
    ("generator_fuel", NodeClass.TERTIARY): "reserves.hospital.generator_fuel_h",
    ("generator_fuel", NodeClass.REGIONAL): "reserves.hospital.generator_fuel_h",
    ("generator_fuel", NodeClass.BLOOD_BANK): "reserves.blood_bank.generator_fuel_h",
    ("battery", NodeClass.EXCHANGE): "reserves.exchange.battery_h",
    ("water", NodeClass.TERTIARY): "reserves.hospital.water_h",
    ("water", NodeClass.REGIONAL): "reserves.hospital.water_h",
    ("supplies", NodeClass.TERTIARY): "reserves.hospital.supplies_h",
    ("supplies", NodeClass.REGIONAL): "reserves.hospital.supplies_h",
    ("blood", NodeClass.BLOOD_BANK): "reserves.blood_bank.blood_stock_days",
    ("distribution_water", NodeClass.STORAGE): "reserves.storage.peak_day_h",
    ("lng", NodeClass.IMPORT_TERMINAL): "reserves.lng.days",
    ("coal", NodeClass.GENERATION): "reserves.coal.days",
    ("purified_water", NodeClass.GENERATION): "reserves.generation.purified_water_h",
    ("makeup_water", NodeClass.DATA_CENTRE): "reserves.data_centre.makeup_water_h",
    ("backup_power", NodeClass.SEAPORT): "reserves.seaport.backup_power_h",
}
"""The registry limit behind each stock kind at each class, for relaxing (D11)."""

REFILL: Mapping[str, str] = {
    "battery": "battery",
    "generator_fuel": "delivery",
    "purified_water": "main",
    "makeup_water": "main",
    "water": "main",
    "distribution_water": "pumps",
}
"""How each stock kind refills (D5; hospital water from the main, PR 7b answers 2); every other
kind (supplies, blood, the national stocks) does not refill inside the window."""


def world_from_stages(stages: StageOutputs, rules: Registry) -> EngineWorld:
    """Build the engine's world from the generator's stage outputs.

    Parameters
    ----------
    stages : StageOutputs
        The layers, requirements, couplings, strength, buffers, crews, repair and lines.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    EngineWorld
        The world the engine plays out.

    Spec: structure v0.9 §4.5; Work Order 7, D1-D4.
    """
    layers = stages.layers
    nodes_by_id = {node.node_id: node for node in layers.nodes}
    engine_nodes = tuple(_engine_node(node, rules) for node in sorted(layers.nodes, key=_id))
    stocks = _stocks(stages, nodes_by_id)
    return EngineWorld(
        nodes=engine_nodes,
        dependencies=_dependencies(stages),
        links=_links(layers),
        stocks=stocks,
        generators=tuple(
            Generator(b.node_id, bool(b.fails_to_start), float(b.run_hours_to_failure or 0.0))
            for b in sorted(stages.buffers.backups, key=lambda b: b.node_id)
            if b.has_generator
        ),
        resupply=_resupply(stages, stocks),
        repairs=tuple(
            FacilityRepair(
                p.node_id,
                max(0.0, p.lead_time_h - rules.number("repair.crew_bound_lead_h")),
                p.crew_work_h,
            )
            for p in stages.repair.permanent
        ),
        unrepairable=tuple(sorted(stages.repair.unrepairable)),
        emergencies=tuple(
            Emergency(e.node_id, e.unit_kind, e.total_h, e.restored_share)
            for e in sorted(stages.repair.emergency, key=lambda e: e.node_id)
        ),
        units=_unit_counts(stages.crews),
        crews=_crew_starts(stages.crews, stages.grid),
        feeds_to_end_use=_feeds_to_end_use(stages, nodes_by_id),
        towered=frozenset(
            line.line_id for line in stages.lines if line.structure == Structure.TOWER
        ),
        settings=settings_from(rules),
        pump_capacity_m3_per_h={
            node.node_id: float(dict(node.attributes)["capacity_m3_per_day"]) / 24.0
            for node in layers.nodes
            if node.node_class == NodeClass.PUMPING
        },
    )


def _id(node: Node) -> str:
    return node.node_id


def _stage_of(layer: Layer, node_class: NodeClass) -> int | None:
    for chain in SIGNATURE_CHAINS.get(layer, ()):
        for index, stage in enumerate(chain):
            if node_class in stage:
                return index
    return None


def _engine_node(node: Node, rules: Registry) -> EngineNode:
    stage = _stage_of(node.layer, node.node_class)
    source = node.layer not in FLOW_LAYERS or stage in (None, 0)
    weight = None
    if node.node_class.value in {c.value for c in EndUseClass}:
        weight = LIFELINE_WEIGHTS[EndUseClass(node.node_class.value)]
    return EngineNode(
        node_id=node.node_id,
        layer=node.layer,
        node_class=node.node_class,
        site=(node.x_m, node.y_m),
        source=source,
        own_mode=None if source else own_layer_mode(node.node_class, node.layer, rules),
        end_use_weight=weight,
    )


def own_layer_mode(node_class: NodeClass, layer: Layer, rules: Registry) -> str:
    """Return a node's response to a shortfall of its own layer's commodity.

    Links carry physical flow (D4), so the default is the physical-flow default, departed from
    by the class departures that name no supplier or this layer (§4.4a).

    Parameters
    ----------
    node_class : NodeClass
        The node's class.
    layer : Layer
        Its own layer.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    str
        throttle or trip.

    Spec: structure v0.9 §4.4a (failure mode) and §4.5 (links); ruling D4.
    """
    # Own-layer supply takes the class default and departures with no heterogeneity draw; the
    # failure-mode draws exist only for cross-layer dependencies (ruled, decision 0014 second
    # addendum).
    mode = str(rules.value("failure_modes.defaults")["physical_flow"])
    for departure in rules.value("failure_modes.class_departures"):
        if departure["node_class"] != node_class or departure["when"] is not None:
            continue
        if departure["supplier"] in (None, layer.value):
            mode = str(departure["mode"])
    return mode


def _dependencies(stages: StageOutputs) -> tuple[EngineDependency, ...]:
    couplings = stages.couplings
    edges = {edge.edge_id: edge for edge in couplings.edges}
    kappa = {s.edge_id: s.kappa for s in stages.strength.edges}
    modes = {(m.node_id, m.supplier_layer): m for m in stages.buffers.failure_modes}
    tolerance = {t.dependency_id: t for t in stages.buffers.tolerance}
    feeds = {line.line_id for line in stages.lines}
    result = []
    for dependency in sorted(couplings.dependencies, key=lambda d: d.dependency_id):
        if dependency.role != Role.PRIMARY_SUPPLY or not dependency.edge_ids:
            continue
        groups: dict[int, list[EngineEdge]] = {}
        for edge_id in dependency.edge_ids:
            edge = edges[edge_id]
            groups.setdefault(edge.feed_group, []).append(
                EngineEdge(
                    edge_id,
                    edge.supplier_id,
                    kappa[edge_id],
                    edge.transfer_form,
                    edge_id if edge_id in feeds else None,
                )
            )
        mode = modes[(dependency.consumer_id, dependency.supplier_layer)]
        row = tolerance.get(dependency.dependency_id)
        result.append(
            EngineDependency(
                dependency_id=dependency.dependency_id,
                consumer_id=dependency.consumer_id,
                supplier_layer=dependency.supplier_layer,
                groups=tuple(tuple(groups[g]) for g in sorted(groups)),
                mode=mode.mode,
                floor=mode.floor,
                tolerance=None if row is None else _tolerance(row.consumer_id, row, stages),
            )
        )
    return tuple(result)


def _tolerance(consumer_id: str, row: Any, stages: StageOutputs) -> Tolerance:
    node = next(n for n in stages.layers.nodes if n.node_id == consumer_id)
    rule_id = tolerance_rule(node)
    if rule_id is None:
        raise KeyError(f"{consumer_id} holds a tolerance buffer but no tolerance row")
    return Tolerance(rule_id, row.t_h, row.d_eff, row.ramp_to_h)


def _links(layers: LayersResult) -> tuple[IntraLink, ...]:
    classes = {node.node_id: node.node_class for node in layers.nodes}
    links = []
    for link in sorted(layers.links, key=lambda link: link.link_id):
        if link.layer not in FLOW_LAYERS:
            continue
        a, b = classes[link.from_id], classes[link.to_id]
        stage_a, stage_b = _stage_of(link.layer, a), _stage_of(link.layer, b)
        line = link.layer in (Layer.POWER, Layer.TELECOM)
        if stage_a is None or stage_b is None:
            continue
        if stage_a < stage_b:
            links.append(IntraLink(link.link_id, link.from_id, link.to_id, line))
        elif stage_b < stage_a:
            links.append(IntraLink(link.link_id, link.to_id, link.from_id, line))
        else:
            # A tie (or two nodes of one stage) carries flow either way (D4).
            tie = a in SIGNATURE_TIES.get(link.layer, ()) or a == b
            if tie:
                links.append(IntraLink(link.link_id, link.from_id, link.to_id, line))
                links.append(IntraLink(link.link_id, link.to_id, link.from_id, line))
    return tuple(links)


def _stocks(stages: StageOutputs, nodes: Mapping[str, Node]) -> tuple[Stock, ...]:
    result = []
    for reserve in stages.buffers.reserves:
        node = nodes[reserve.node_id]
        rule_id = STOCK_RULES.get((reserve.kind, node.node_class))
        if rule_id is None:
            rule_id = _bulk_rule(reserve.kind, node)
        result.append(
            Stock(
                stock_id=f"{reserve.node_id}:{reserve.kind}",
                node_id=reserve.node_id,
                kind=reserve.kind,
                covers=reserve.buffers,
                capacity=reserve.stock,
                draw_per_h=reserve.draw_per_h,
                refill=REFILL.get(reserve.kind, "none"),
                rule_id=rule_id,
                generator=reserve.kind == "generator_fuel",
            )
        )
    return tuple(sorted(result, key=lambda s: s.stock_id))


def _bulk_rule(kind: str, node: Node) -> str:
    rules = {
        "oil_industry": "reserves.oil.industry_days",
        "oil_government": "reserves.oil.government_days",
    }
    if kind in rules:
        return rules[kind]
    if kind == "battery" and node.node_class == NodeClass.MAST:
        return "reserves.mast.battery_h"
    raise KeyError(f"no registry limit for the {kind} stock at {node.node_class}")


def _resupply(stages: StageOutputs, stocks: tuple[Stock, ...]) -> tuple[Resupply, ...]:
    edges = {edge.edge_id: edge for edge in stages.couplings.edges}
    kappa = {s.edge_id: s.kappa for s in stages.strength.edges}
    tanks = {s.node_id: s for s in stocks if s.generator}
    result = []
    for record in sorted(stages.buffers.resupply, key=lambda r: r.edge_id):
        tank = tanks.get(record.consumer_id)
        if tank is None:
            continue
        edge = edges[record.edge_id]
        result.append(
            Resupply(
                record.edge_id,
                edge.supplier_id,
                record.consumer_id,
                tank.stock_id,
                record.delivery_l,
                kappa[record.edge_id],
                edge.transfer_form,
            )
        )
    return tuple(result)


def _unit_counts(crews: CrewsResult) -> dict[str, int]:
    counts: dict[str, int] = {}
    for unit in crews.units:
        counts[unit.kind] = counts.get(unit.kind, 0) + 1
    return dict(sorted(counts.items()))


def _crew_starts(crews: CrewsResult, grid: Grid) -> tuple[CrewStart, ...]:
    bases = {base.base_id: base for base in crews.bases}
    result = []
    for crew in sorted(crews.crews, key=lambda c: c.crew_id):
        base = bases[crew.base_id]
        result.append(CrewStart(crew.crew_id, cell_centre_m(base.row, base.column, grid)))
    return tuple(result)


def _feeds_to_end_use(stages: StageOutputs, nodes: Mapping[str, Node]) -> dict[str, float]:
    feeds: dict[str, float] = {}
    end_uses = {c.value for c in EndUseClass}
    for line in stages.lines:
        if line.kind.value != "power_feed":
            continue
        consumer = nodes[line.to_id]
        if consumer.node_class.value in end_uses:
            feeds[line.line_id] = LIFELINE_WEIGHTS[EndUseClass(consumer.node_class.value)]
    return dict(sorted(feeds.items()))


def failure_points(
    outcomes: Sequence[LineOutcome], lines: Sequence[OverheadLine]
) -> tuple[FailurePoint, ...]:
    """Return where each failed line must be repaired, in order along the line.

    Parameters
    ----------
    outcomes : sequence of LineOutcome
        One scenario's line outcomes.
    lines : sequence of OverheadLine
        The overhead lines.

    Returns
    -------
    tuple of FailurePoint
        Each failure point at its km along the line, with its site and crew work.

    Spec: structure v0.9 §4.3b (repair); Work Order 7, D4.
    """
    by_id = {line.line_id: line for line in lines}
    points = []
    for outcome in outcomes:
        if not outcome.failed:
            continue
        line = by_id[outcome.line_id]
        work = outcome.crew_work_h / outcome.failure_points if outcome.failure_points else 0.0
        for km in outcome.failure_km:
            points.append(FailurePoint(line.line_id, km, point_at_km(line, km), work))
    return tuple(points)


def point_at_km(line: OverheadLine, km: float) -> Point:
    """Return the point a given distance along a line's polyline (sqrt only)."""
    walked = 0.0
    target = km * M_PER_KM
    for a, b in pairwise(line.points):
        step = math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]))
        if walked + step >= target and step > 0.0:
            share = (target - walked) / step
            return (a[0] + share * (b[0] - a[0]), a[1] + share * (b[1] - a[1]))
        walked += step
    return line.points[-1]
