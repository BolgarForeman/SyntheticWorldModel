"""Buffers stage: reserves, backup and its availability, resupply, tolerance and failure modes.

From the sized layers, the requirements, the couplings and the ``reserves/``, ``availability/``
and ``failure_mode/`` streams, the stage draws what buys a consumer time when supply stops,
and how it responds when supply falls short:
- **stock reserves** (§4.4a): generator fuel at the expected load, batteries, hospital water at
  the emergency ration, supplies, blood stock, distribution storage, and LNG, oil and coal
  stocks. Each is drawn in hours around its target with the shared draw method; buffer time is
  the stock over the expected draw;
- **presence of backup** from the subtype attributes, never from the compliance gap;
- **generator availability**, a separate draw of fail-to-start and time to failure per set;
- **fuel resupply** on buffer-resupply edges;
- **the telecom tolerance buffer**, T hours at full function then level d, deepened by the
  public share: d_eff = 1 - κ(1 - d);
- **the failure mode** per node and commodity.

All are real but unobserved. The dynamics (Work Order 7) uses them; nothing here runs time.

Spec: structure v0.6 §4.4 and §4.4a; Work Order 5, Parts D and F; decision 0009.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from swm import rng
from swm.draws import DrawMethod, Levers
from swm.recipe.dependencies import DependencyType, Role, resolve_row
from swm.recipe.schema import CategoricalDrawnQuantity, ContinuousDrawnQuantity, Layer, NodeClass
from swm.rules.registry import Registry
from swm.stages.couplings import CouplingsResult, _percent_of, _permutation
from swm.stages.layers import LayersResult, Node
from swm.stages.requirements import RequirementsResult

HOURS_PER_DAY = 24.0
KWH_PER_MWH = 1000.0
L_PER_M3 = 1000.0

C = NodeClass
GENERATOR_FUEL_H: Mapping[NodeClass, str] = {
    C.EXCHANGE: "reserves.exchange.fuel_h",
    C.DATA_CENTRE: "reserves.data_centre.fuel_h",
    C.CABLE_LANDING: "reserves.cable_landing.fuel_h",
    C.TREATMENT: "reserves.treatment.fuel_h",
    C.PUMPING: "reserves.pumping.portable_generator_fuel_h",
    C.TERTIARY: "reserves.hospital.generator_fuel_h",
    C.REGIONAL: "reserves.hospital.generator_fuel_h",
    C.BLOOD_BANK: "reserves.blood_bank.generator_fuel_h",
}
"""The §4.4a generator-fuel target of each class that can hold a diesel standby set."""

BATTERY_H: Mapping[NodeClass, str] = {
    C.MAST: "reserves.mast.battery_h",
    C.EXCHANGE: "reserves.exchange.battery_h",
}
"""Classes that hold a battery by rule (§4.4a), with their target."""

HOSPITALS = (C.TERTIARY, C.REGIONAL)

CLASS_GAP: Mapping[NodeClass, str] = {
    C.TERTIARY: "reserves.compliance_gap.hospital_backup_pct",
    C.REGIONAL: "reserves.compliance_gap.hospital_backup_pct",
    C.TREATMENT: "reserves.compliance_gap.water_facilities_pct",
    C.PUMPING: "reserves.compliance_gap.water_facilities_pct",
    C.STORAGE: "reserves.compliance_gap.water_facilities_pct",
    C.EXCHANGE: "reserves.compliance_gap.exchange_data_centre_pct",
    C.DATA_CENTRE: "reserves.compliance_gap.exchange_data_centre_pct",
    C.MAST: "reserves.compliance_gap.mast_pct",
}
"""The §4.4a compliance gap by class. CHOICE: other classes take the recipe's reserves gap."""

TOLERANCE: Mapping[NodeClass, str] = {
    C.GENERATION: "tolerance.generation",
    C.IMPORT_TERMINAL: "tolerance.import_terminal",
    C.TRANSMISSION_SUBSTATION: "tolerance.substation",
    C.DISTRIBUTION_SUBSTATION: "tolerance.substation",
    C.PUMPING: "tolerance.pumping",
    C.TREATMENT: "tolerance.treatment",
    C.RESERVOIR: "tolerance.reservoir",
    C.SEAPORT: "tolerance.seaport_freight_yard",
    C.FREIGHT_YARD: "tolerance.seaport_freight_yard",
    C.DEPOT: "tolerance.depot",
    C.REFINERY: "tolerance.refinery",
    C.CLINIC: "tolerance.clinic",
    C.BLOOD_BANK: "tolerance.blood_bank",
}
"""The §4.4a tolerance row of each class; hospitals, airports and tank farms depend on their
subtype and are chosen in code."""

OIL_HOLDERS = (C.TANK_FARM, C.REFINERY, C.IMPORT_TERMINAL)

NATIONAL_STOCKS = frozenset({"lng", "oil_industry", "oil_government", "coal"})
"""Statutory stocks, which take the national-stocks gap rather than their class's."""


@dataclass(frozen=True)
class Reserve:
    """One stock that buys a node time when a supply stops."""

    node_id: str
    kind: str
    buffers: Layer
    """The supplier layer whose loss the stock covers."""
    stock: float
    stock_units: str
    draw_per_h: float
    """The expected draw on the stock, in stock units per hour."""
    hours: float
    """Buffer time at the expected draw: stock / draw."""
    target_hours: float
    compliance_gap: float


@dataclass(frozen=True)
class Backup:
    """Which backup a node has, and how its generator behaves (§4.4a; Work Order 5, D2-D3)."""

    node_id: str
    has_generator: bool
    has_battery: bool
    well_maintained: bool | None
    fails_to_start: bool | None
    run_hours_to_failure: float | None


@dataclass(frozen=True)
class Resupply:
    """Fuel resupply on one buffer-resupply edge (Work Order 5, D4)."""

    edge_id: str
    consumer_id: str
    lead_time_h: float
    delivery_h: float
    delivery_l: float


@dataclass(frozen=True)
class Tolerance:
    """The telecom tolerance buffer of one telecom dependency (§4.4 and §4.4a; F1)."""

    dependency_id: str
    consumer_id: str
    t_h: float
    ramp_to_h: float | None
    """For hosted hospital records: the level falls linearly from T to this hour."""
    d: float
    public_share: float
    d_eff: float
    slows_switching: bool
    """Substations: telecom loss slows switching and repair; it does not cut supply."""


@dataclass(frozen=True)
class FailureMode:
    """How a node responds to a shortfall on one commodity (§4.4a; F2)."""

    node_id: str
    supplier_layer: Layer
    dependency_type: str
    mode: str
    floor: float | None
    departed: bool


@dataclass(frozen=True)
class BuffersResult:
    """The buffers stage's output. Real but unobserved: never emitted."""

    reserves: tuple[Reserve, ...]
    backups: tuple[Backup, ...]
    resupply: tuple[Resupply, ...]
    tolerance: tuple[Tolerance, ...]
    failure_modes: tuple[FailureMode, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class BuffersStreams:
    """The buffers streams, one of each per layer."""

    reserves: Mapping[Layer, np.random.Generator]
    availability: Mapping[Layer, np.random.Generator]
    failure_mode: Mapping[Layer, np.random.Generator]


def buffers_streams(root_seed: int) -> BuffersStreams:
    """Return the ``reserves/``, ``availability/`` and ``failure_mode/`` streams per layer.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.

    Returns
    -------
    BuffersStreams
        The streams.

    Spec: Work Order 5, Parts D and F.
    """
    return BuffersStreams(
        reserves={layer: rng.stream(root_seed, f"reserves/{layer}") for layer in Layer},
        availability={layer: rng.stream(root_seed, f"availability/{layer}") for layer in Layer},
        failure_mode={layer: rng.stream(root_seed, f"failure_mode/{layer}") for layer in Layer},
    )


def build_buffers(
    reserves: ContinuousDrawnQuantity,
    failure_mode: CategoricalDrawnQuantity,
    layers: LayersResult,
    requirements: RequirementsResult,
    couplings: CouplingsResult,
    rules: Registry,
    streams: BuffersStreams,
) -> BuffersResult:
    """Draw every reserve, backup, resupply, tolerance buffer and failure mode.

    Parameters
    ----------
    reserves : ContinuousDrawnQuantity
        The recipe's reserve levers: heterogeneity, and the compliance gap for classes §4.4a
        gives none.
    failure_mode : CategoricalDrawnQuantity
        The recipe's failure-mode heterogeneity: the share departing from the class default.
    layers : LayersResult
        The layers, power sized.
    requirements : RequirementsResult
        The requirements.
    couplings : CouplingsResult
        The couplings.
    rules : Registry
        The modeling rules in force.
    streams : BuffersStreams
        The buffers streams.

    Returns
    -------
    BuffersResult
        The buffers and notes.

    Spec: structure v0.6 §4.4 and §4.4a; Work Order 5, Parts D and F.
    """
    context = _Context(reserves, layers, requirements, couplings, rules)
    backups = [_backup(node, context, streams.availability[node.layer]) for node in layers.nodes]
    stock = _reserves(context, streams.reserves)
    return BuffersResult(
        reserves=tuple(stock),
        backups=tuple(backups),
        resupply=tuple(_resupply(context)),
        tolerance=tuple(_tolerance(context)),
        failure_modes=tuple(_failure_modes(context, backups, failure_mode, streams.failure_mode)),
        notes=tuple(sorted(context.notes)),
    )


class _Context:
    """What every part of the stage reads, and the draw method with its tables."""

    def __init__(
        self,
        levers: ContinuousDrawnQuantity,
        layers: LayersResult,
        requirements: RequirementsResult,
        couplings: CouplingsResult,
        rules: Registry,
    ) -> None:
        self.rules = rules
        self.layers = layers
        self.couplings = couplings
        self.nodes = {node.node_id: node for node in layers.nodes}
        self.requirements = requirements.by_id()
        self.method = DrawMethod.from_registry(rules)
        self.heterogeneity = levers.heterogeneity_pct
        self.recipe_gap = levers.compliance_gap_pct
        self.edges = {edge.edge_id: edge for edge in couplings.edges}
        self.notes: set[str] = set()
        self._tables: dict[tuple[float, float], tuple[float, ...]] = {}

    def gap(self, node_class: NodeClass, kind: str = "") -> float:
        """Return the compliance gap of a reserve, as a fraction.

        The national LNG, oil and coal stocks take their own gap (decision 0010); other stocks
        take their class's §4.4a gap, or the recipe's where §4.4a lists none.
        """
        if kind in NATIONAL_STOCKS:
            return self.rules.number("reserves.compliance_gap.national_stocks_pct") / 100.0
        if node_class in CLASS_GAP:
            return self.rules.number(CLASS_GAP[node_class]) / 100.0
        return self.recipe_gap / 100.0

    def draw_hours(self, target_h: float, gap: float, u: float) -> float:
        """Draw buffer hours around a target with the shared method (median target x (1 - gap))."""
        levers = Levers(self.heterogeneity / 100.0, gap)
        key = (levers.heterogeneity, levers.compliance_gap)
        if key not in self._tables:
            self._tables[key] = self.method.mixture(levers.spread)
        return target_h * (1.0 - gap) * self.method.quantile(self._tables[key], u)

    def expected_load_mw(self, node: Node) -> float | None:
        """Return the load a backup set carries: a hospital's essential fraction, else all."""
        electricity = self.requirements[node.node_id].electricity_mw
        if electricity is None:
            return None
        if node.node_class in HOSPITALS:
            return electricity * self.rules.number("reserves.hospital.essential_load_fraction")
        return electricity

    def burn_l_per_h(self, node: Node) -> float | None:
        load = self.expected_load_mw(node)
        if load is None:
            return None
        # CHOICE: the set runs at the full-load rate per MW of the load it carries, as though
        # sized to that load; the part-load curve is not modelled.
        return load * self.rules.number("requirements.fuel.backup_generator_l_per_h_per_mw")

    def primary_fuel_edges_from(self, supplier_ids: set[str]) -> list[Any]:
        return [
            edge
            for edge in self.couplings.edges
            if edge.supplier_id in supplier_ids
            and edge.supplier_layer == Layer.FUEL
            and edge.role == Role.PRIMARY_SUPPLY
        ]


def _has_generator(node: Node) -> bool:
    return dict(node.subtype).get("standby_fuel") == "diesel"


def _backup(node: Node, context: _Context, stream: np.random.Generator) -> Backup:
    """Presence from the subtype attributes (D2), and a generator's availability draw (D3)."""
    has_generator = _has_generator(node)
    has_battery = node.node_class in BATTERY_H
    if not has_generator:
        return Backup(node.node_id, False, has_battery, None, None, None)
    rules = context.rules
    share = rules.number("reserves.generator_availability.well_maintained_share")
    well = float(stream.random()) < share
    figures = rules.value("reserves.generator_availability")[
        "well_maintained" if well else "poorly_maintained"
    ]
    fails = float(stream.random()) < float(figures["fail_to_start"])
    table = rules.value("draws.exponential_table")["quantiles"]
    run_h = float(figures["mttf_h"]) * context.method.quantile(table, float(stream.random()))
    return Backup(node.node_id, True, has_battery, well, fails, run_h)


def _reserves(context: _Context, streams: Mapping[Layer, np.random.Generator]) -> list[Reserve]:
    reserves: list[Reserve] = []
    oil_draw = _national_oil_draw_gj_per_h(context)
    oil_capacity = math.fsum(_storage(node) for node in context.layers.nodes if _holds_oil(node))
    farm_capacity = math.fsum(
        _storage(node) for node in context.layers.nodes if node.node_class == C.TANK_FARM
    )
    for node in context.layers.nodes:
        stream = streams[node.layer]
        for kind, buffers, target_h, draw, units in _stocks(node, context):
            gap = context.gap(node.node_class, kind)
            hours = context.draw_hours(target_h, gap, float(stream.random()))
            reserves.append(
                Reserve(
                    node.node_id, kind, buffers, hours * draw, units, draw, hours, target_h, gap
                )
            )
        if _holds_oil(node) and oil_capacity > 0.0:
            share = _storage(node) / oil_capacity
            days = context.rules.number("reserves.oil.industry_days")
            reserves.append(_bulk(node, "oil_industry", days, oil_draw * share, context, stream))
        if node.node_class == C.TANK_FARM and farm_capacity > 0.0:
            share = _storage(node) / farm_capacity
            days = context.rules.number("reserves.oil.government_days")
            reserves.append(_bulk(node, "oil_government", days, oil_draw * share, context, stream))
    return reserves


def _bulk(
    node: Node,
    kind: str,
    days: float,
    draw: float,
    context: _Context,
    stream: np.random.Generator,
) -> Reserve:
    target_h = days * HOURS_PER_DAY
    gap = context.gap(node.node_class, kind)
    hours = context.draw_hours(target_h, gap, float(stream.random()))
    return Reserve(node.node_id, kind, Layer.FUEL, hours * draw, "GJ", draw, hours, target_h, gap)


def _stocks(node: Node, context: _Context) -> list[tuple[str, Layer, float, float, str]]:
    """Return the node's own stocks: (kind, layer covered, target h, draw per h, units)."""
    rules, c = context.rules, node.node_class
    stocks: list[tuple[str, Layer, float, float, str]] = []
    load = context.expected_load_mw(node)
    burn = context.burn_l_per_h(node)
    if _has_generator(node) and burn is not None:
        if c in GENERATOR_FUEL_H:
            stocks.append(("generator_fuel", Layer.POWER, rules.number(GENERATOR_FUEL_H[c]),
                           burn, "L"))  # fmt: skip
        else:
            context.notes.add(
                f"{c}: a diesel standby set but no fuel target in section 4.4a; no stock drawn"
            )
    if c in BATTERY_H and load is not None:
        stocks.append(("battery", Layer.POWER, _battery_hours(node, context),
                       load * KWH_PER_MWH, "kWh"))  # fmt: skip
    if c in HOSPITALS:
        beds = float(dict(node.attributes)["bed_count"])
        ration = rules.number("reserves.hospital.water_ration_l_per_bed_day")
        per_h = beds * ration / L_PER_M3 / HOURS_PER_DAY
        stocks.append(("water", Layer.WATER, rules.number("reserves.hospital.water_h"), per_h,
                       "m3"))  # fmt: skip
        stocks.append(("supplies", Layer.TRANSPORT, rules.number("reserves.hospital.supplies_h"),
                       1.0, "hours of supplies"))  # fmt: skip
    if c == C.BLOOD_BANK:
        days = rules.number("reserves.blood_bank.blood_stock_days")
        stocks.append(("blood", Layer.TRANSPORT, days * HOURS_PER_DAY, 1.0, "hours of issue"))
    if c == C.STORAGE:
        per_h = _storage_peak_draw(node, context)
        if per_h > 0.0:
            stocks.append(("distribution_water", Layer.WATER,
                           rules.number("reserves.storage.peak_day_h"), per_h, "m3"))  # fmt: skip
    if c == C.IMPORT_TERMINAL and dict(node.subtype).get("product") == "lng":
        per_h = _send_out_gj_per_h({node.node_id}, context)
        stocks.append(("lng", Layer.TRANSPORT,
                       rules.number("reserves.lng.days") * HOURS_PER_DAY, per_h, "GJ"))  # fmt: skip
    if c == C.GENERATION and dict(node.subtype).get("fuel_kind") == "coal":
        fuel = context.requirements[node.node_id].fuel_gj_per_day or 0.0
        stocks.append(("coal", Layer.FUEL, rules.number("reserves.coal.days") * HOURS_PER_DAY,
                       fuel / HOURS_PER_DAY, "GJ"))  # fmt: skip
    return stocks


def _battery_hours(node: Node, context: _Context) -> float:
    rules = context.rules
    if node.node_class != C.MAST:
        return rules.number(BATTERY_H[node.node_class])
    # CHOICE: a mast is designated by its position among the masts, so the share needs no
    # draw and a share of 0 designates none.
    masts = [n for n in context.layers.nodes if n.node_class == C.MAST]
    designated = _percent_of(
        int(rules.number("reserves.mast.designated_share") * 100 + 0.5), len(masts)
    )
    if masts.index(node) < designated:
        return rules.number("reserves.mast.designated_battery_h")
    return rules.number("reserves.mast.battery_h")


def _storage(node: Node) -> float:
    return float(dict(node.attributes).get("storage_m3", 0.0))


def _holds_oil(node: Node) -> bool:
    if node.node_class == C.IMPORT_TERMINAL:
        return dict(node.subtype).get("product") == "oil"
    return node.node_class in (C.TANK_FARM, C.REFINERY)


def _storage_peak_draw(node: Node, context: _Context) -> float:
    """Peak-day demand on a storage node's water edges, per hour (m³/h)."""
    peak = context.rules.number("requirements.peak_factor")
    total = 0.0
    for edge in context.couplings.edges:
        if edge.supplier_id != node.node_id or edge.supplier_layer != Layer.WATER:
            continue
        water = context.requirements[edge.consumer_id].water_m3_per_day or 0.0
        share = 0.5 if edge.feed_configuration == "two_half" else 1.0
        total += water * share
    return total * peak / HOURS_PER_DAY


def _send_out_gj_per_h(supplier_ids: set[str], context: _Context) -> float:
    total = 0.0
    for edge in context.primary_fuel_edges_from(supplier_ids):
        fuel = context.requirements[edge.consumer_id].fuel_gj_per_day or 0.0
        total += fuel * (0.5 if edge.feed_configuration == "two_half" else 1.0)
    return total / HOURS_PER_DAY


def _national_oil_draw_gj_per_h(context: _Context) -> float:
    """Return the oil product demand (GJ/h): every primary fuel draw but LNG and coal plants."""
    total = 0.0
    for record in context.requirements.values():
        if record.fuel_gj_per_day is None:
            continue
        node = context.nodes[record.node_id]
        if node.node_class == C.GENERATION and dict(node.subtype).get("fuel_kind") != "oil":
            continue
        total += record.fuel_gj_per_day
    return total / HOURS_PER_DAY


def _resupply(context: _Context) -> list[Resupply]:
    rules = context.rules
    lead = rules.number("reserves.fuel_resupply.lead_time_h")
    delivery_h = rules.number("reserves.fuel_resupply.delivery_h")
    records = []
    for edge in context.couplings.edges:
        if edge.role != Role.BUFFER_RESUPPLY:
            continue
        burn = context.burn_l_per_h(context.nodes[edge.consumer_id]) or 0.0
        records.append(
            Resupply(edge.edge_id, edge.consumer_id, lead, delivery_h, delivery_h * burn)
        )
    return records


def _tolerance(context: _Context) -> list[Tolerance]:
    records = []
    for dependency in context.couplings.dependencies:
        if dependency.supplier_layer != Layer.TELECOM:
            continue
        node = context.nodes[dependency.consumer_id]
        rule_id = _tolerance_rule(node)
        if rule_id is None:
            context.notes.add(
                f"{node.node_class}: no telecom tolerance in section 4.4a for this subtype"
            )
            continue
        value = context.rules.value(rule_id)
        shares = [
            share
            for share in (context.edges[e].public_share_pct for e in dependency.edge_ids)
            if share is not None
        ]
        # A control edge exposes only its public share (rule 1); a service edge is all public.
        kappa = shares[0] / 100.0 if shares else 1.0
        d = float(value["d"])
        records.append(
            Tolerance(
                dependency_id=dependency.dependency_id,
                consumer_id=node.node_id,
                t_h=float(value["t_h"]),
                ramp_to_h=None if "ramp_to_h" not in value else float(value["ramp_to_h"]),
                d=d,
                public_share=kappa,
                d_eff=1.0 - kappa * (1.0 - d),
                slows_switching=rule_id == "tolerance.substation",
            )
        )
    return records


def _tolerance_rule(node: Node) -> str | None:
    subtype = dict(node.subtype)
    if node.node_class in HOSPITALS:
        hosted = subtype.get("records_hosted") is True
        return (
            "tolerance.hospital_records_hosted" if hosted else "tolerance.hospital_records_on_site"
        )
    if node.node_class == C.AIRPORT:
        towered = subtype.get("towered") is True
        return "tolerance.towered_airport" if towered else "tolerance.airport_not_towered"
    if node.node_class == C.TANK_FARM:
        connected = subtype.get("pipeline_connected") is True
        return "tolerance.tank_farm_pipeline" if connected else "tolerance.tank_farm_not_connected"
    return TOLERANCE.get(node.node_class)


def _failure_modes(
    context: _Context,
    backups: list[Backup],
    levers: CategoricalDrawnQuantity,
    streams: Mapping[Layer, np.random.Generator],
) -> list[FailureMode]:
    """Class defaults and departures, then a heterogeneity share departing, per layer (F2)."""
    rules = context.rules
    defaults = rules.value("failure_modes.defaults")
    departures = rules.value("failure_modes.class_departures")
    floor = rules.number("reserves.hospital.essential_load_fraction")
    generators = {b.node_id for b in backups if b.has_generator}
    modes: list[FailureMode] = []
    for dependency in context.couplings.dependencies:
        if dependency.role != Role.PRIMARY_SUPPLY:
            continue
        node = context.nodes[dependency.consumer_id]
        row = resolve_row(dependency.supplier_layer, node.node_class, dict(node.subtype), rules)
        kind = row.dependency_type or DependencyType.PHYSICAL_FLOW
        mode = str(defaults[kind.value])
        for departure in departures:
            if _departs(departure, node, dependency.supplier_layer, generators):
                mode = str(departure["mode"])
        modes.append(
            FailureMode(
                node_id=node.node_id,
                supplier_layer=dependency.supplier_layer,
                dependency_type=kind.value,
                mode=mode,
                floor=floor if mode == "step_to_floor" else None,
                departed=False,
            )
        )
    return _depart(modes, context, levers.heterogeneity_pct, streams)


def _departs(
    departure: Mapping[str, Any], node: Node, supplier: Layer, generators: set[str]
) -> bool:
    if departure["node_class"] != node.node_class:
        return False
    if departure["supplier"] is not None and departure["supplier"] != supplier:
        return False
    when = departure["when"]
    if when == "has_generator":
        return node.node_id in generators
    if when == "towered":
        return dict(node.subtype).get("towered") is True
    return True


def _depart(
    modes: list[FailureMode],
    context: _Context,
    heterogeneity_pct: int,
    streams: Mapping[Layer, np.random.Generator],
) -> list[FailureMode]:
    """Send round(h x count) of each layer's modes away from their class default, by draw."""
    # CHOICE: a departure turns a throttle into a trip and a trip or a step into a throttle,
    # and the share is counted per layer so each layer draws from its own stream.
    flipped = {"throttle": "trip", "trip": "throttle", "step_to_floor": "throttle"}
    result = list(modes)
    for layer in Layer:
        indices = [i for i, m in enumerate(modes) if context.nodes[m.node_id].layer == layer]
        order = _permutation(streams[layer], len(indices))
        for position in order[: _percent_of(heterogeneity_pct, len(indices))]:
            i = indices[position]
            mode = flipped[modes[i].mode]
            result[i] = FailureMode(
                node_id=modes[i].node_id,
                supplier_layer=modes[i].supplier_layer,
                dependency_type=modes[i].dependency_type,
                mode=mode,
                floor=None,
                departed=True,
            )
    return result


def buffer_tables(result: BuffersResult) -> dict[str, list[dict[str, object]]]:
    """Return every buffers table as plain data in a fixed order, for canonical output.

    Parameters
    ----------
    result : BuffersResult
        The buffers stage's output.

    Returns
    -------
    dict
        Tables by name, numbers rounded to six decimals.

    Spec: Work Order 5, Parts D and F.
    """

    def plain(record: object) -> dict[str, object]:
        row = {}
        for name, value in vars(record).items():
            if isinstance(value, float):
                value = round(value, 6)
            elif isinstance(value, Layer):
                value = value.value
            row[name] = value
        return row

    return {
        "reserves": [plain(r) for r in result.reserves],
        "backups": [plain(b) for b in result.backups],
        "resupply": [plain(r) for r in result.resupply],
        "tolerance": [plain(t) for t in result.tolerance],
        "failure_modes": [plain(m) for m in result.failure_modes],
    }


def statistics_record(result: BuffersResult) -> dict[str, object]:
    """Return counts and mean buffer hours per reserve kind, and the notes.

    Parameters
    ----------
    result : BuffersResult
        The buffers stage's output.

    Returns
    -------
    dict
        Plain data ready for canonical YAML.

    Spec: Work Order 5, Parts D and F.
    """
    kinds = sorted({r.kind for r in result.reserves})
    reserves = {}
    for kind in kinds:
        hours = [r.hours for r in result.reserves if r.kind == kind]
        targets = [r.target_hours for r in result.reserves if r.kind == kind]
        reserves[kind] = {
            "count": len(hours),
            "mean_hours": round(math.fsum(hours) / len(hours), 3),
            "mean_target_hours": round(math.fsum(targets) / len(targets), 3),
        }
    generators = [b for b in result.backups if b.has_generator]
    modes: dict[str, int] = {}
    for mode in result.failure_modes:
        modes[mode.mode] = modes.get(mode.mode, 0) + 1
    return {
        "reserves": reserves,
        "backup": {
            "generators": len(generators),
            "batteries": sum(b.has_battery for b in result.backups),
            "fail_to_start": sum(bool(b.fails_to_start) for b in generators),
            "well_maintained": sum(bool(b.well_maintained) for b in generators),
        },
        "resupply_edges": len(result.resupply),
        "tolerance_buffers": len(result.tolerance),
        "failure_modes": dict(sorted(modes.items())),
        "failure_modes_departed": sum(m.departed for m in result.failure_modes),
        "notes": list(result.notes),
    }
