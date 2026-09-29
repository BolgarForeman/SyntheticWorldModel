"""Requirements stage: what each node draws from each layer it depends on, in normal operation.

From the layers result, the recipe's requirement levers and the ``requirements/<layer>``
streams, the stage gives every node a requirement for each commodity it consumes under the
dependency table (§4.3a): electricity in MW, water in m³/day, fuel in GJ/day for thermal
generation, and telecom and transport access as served-or-not. Each numeric requirement is
drawn around its design target (§4.4a, from the modeling rules registry) with the shared draw
method. Requirements depend only on node class, subtype and size attributes, and come before
couplings because peak load decides which substation supplies a consumer (§4.3a rule 4).

Backup generators draw nothing while grid power is up, so their burn is recorded only as a
rate, for the reserves stage.

Spec: structure v0.6 §4.4 and §4.4a; Work Order 5, Part B; decision 0009.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np

from swm import rng
from swm.draws import DrawMethod, Levers
from swm.recipe.dependencies import Dependency, Role, coupling_pairs, resolve_row
from swm.recipe.schema import ContinuousDrawnQuantity, Layer, NodeClass
from swm.rules.registry import Registry
from swm.stages.layers import AttributeValue, LayersResult, Node

HOURS_PER_DAY = 24.0
HOURS_PER_YEAR = 8760.0
SECONDS_PER_DAY = 86400.0
KW_PER_MW = 1000.0
CUBIC_METRES_PER_BARREL = 0.158987294928
"""One US oil barrel of 42 US gallons (a unit definition)."""

REQ = "requirements."

Attributes = dict[str, AttributeValue]


@dataclass(frozen=True)
class NodeRequirements:
    """One node's normal-operation requirements. Real but unobserved: never emitted."""

    node_id: str
    layer: Layer
    node_class: NodeClass
    electricity_mw: float | None
    """Average electrical draw (MW); None if the node takes no power."""
    peak_mw: float | None
    """Electricity times the peak factor (MW); decides the supplying substation (rule 4)."""
    water_m3_per_day: float | None
    fuel_gj_per_day: float | None
    """Thermal generation only; other fuel draws have no target yet."""
    backup_burn_l_per_h: float | None
    """Full-load burn of a diesel standby generator (L/h): a rate, not a requirement."""
    telecom: bool
    """Whether the node needs telecom (served or not)."""
    transport: bool
    """Whether the node needs transport access (served or not)."""


@dataclass(frozen=True)
class RequirementsResult:
    """The requirements stage's output."""

    nodes: tuple[NodeRequirements, ...]
    levers: Levers
    spread_capped: bool
    notes: tuple[str, ...]

    def by_id(self) -> dict[str, NodeRequirements]:
        """Return the requirements keyed by node id."""
        return {node.node_id: node for node in self.nodes}


def requirements_streams(root_seed: int) -> Mapping[Layer, np.random.Generator]:
    """Return the ``requirements/<layer>`` streams.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.

    Returns
    -------
    Mapping[Layer, numpy.random.Generator]
        One stream per layer.

    Spec: Work Order 5, B1.
    """
    return {layer: rng.stream(root_seed, f"requirements/{layer}") for layer in Layer}


def build_requirements(
    levers: ContinuousDrawnQuantity,
    layers: LayersResult,
    rules: Registry,
    streams: Mapping[Layer, np.random.Generator],
) -> RequirementsResult:
    """Draw every node's requirement for each commodity it consumes.

    Parameters
    ----------
    levers : ContinuousDrawnQuantity
        The recipe's heterogeneity and compliance gap for requirements.
    layers : LayersResult
        The layers stage's output.
    rules : Registry
        The modeling rules in force, with the recipe's overrides.
    streams : Mapping[Layer, numpy.random.Generator]
        The requirements streams.

    Returns
    -------
    RequirementsResult
        One record per node, the levers and notes.

    Spec: structure v0.6 §4.4 and §4.4a; Work Order 5, B1-B4.
    """
    method = DrawMethod.from_registry(rules)
    drawn = Levers.from_percent(levers.heterogeneity_pct, levers.compliance_gap_pct)
    capped = drawn.spread > method.largest_spread
    quantiles = method.mixture(drawn.spread)
    targets = _Targets(rules)
    notes: set[str] = set()
    records = []
    for node in layers.nodes:
        stream = streams[node.layer]

        def around(target: float | None, stream: np.random.Generator = stream) -> float | None:
            if target is None:
                return None
            scale = target * (1.0 - drawn.compliance_gap)
            return scale * method.quantile(quantiles, float(stream.random()))

        consumed = _consumed(node)
        electricity = around(targets.electricity(node)) if Layer.POWER in consumed else None
        water = around(targets.water(node)) if Layer.WATER in consumed else None
        fuel = around(targets.fuel(node, notes)) if Layer.FUEL in consumed else None
        records.append(
            NodeRequirements(
                node_id=node.node_id,
                layer=node.layer,
                node_class=node.node_class,
                electricity_mw=electricity,
                peak_mw=None if electricity is None else electricity * targets.peak_factor,
                water_m3_per_day=water,
                fuel_gj_per_day=fuel,
                backup_burn_l_per_h=targets.backup_burn(node, electricity),
                telecom=Layer.TELECOM in consumed,
                transport=Layer.TRANSPORT in consumed,
            )
        )
    if capped:
        notes.add(
            f"requirements spread {drawn.spread:.2f} is above the largest tabulated "
            f"{method.largest_spread:g}; held to it"
        )
    return RequirementsResult(tuple(records), drawn, capped, tuple(sorted(notes)))


def _consumed(node: Node) -> set[Layer]:
    """Supplier layers the node takes a primary-supply dependency from (core or optional)."""
    subtype = dict(node.subtype)
    consumed = set()
    for supplier, consumer in coupling_pairs():
        if consumer != node.layer:
            continue
        row = resolve_row(supplier, node.node_class, subtype)
        if row.dependency != Dependency.NONE and row.role == Role.PRIMARY_SUPPLY:
            consumed.add(supplier)
    return consumed


class _Targets:
    """Design targets per class, read from the registry (§4.4a)."""

    def __init__(self, rules: Registry) -> None:
        self.rules = rules
        self.peak_factor = rules.number(REQ + "peak_factor")

    def n(self, rule_id: str) -> float:
        return self.rules.number(REQ + rule_id)

    def electricity(self, node: Node) -> float:
        """Target average electrical draw (MW)."""
        c = NodeClass
        attributes, subtype = dict(node.attributes), dict(node.subtype)
        per_bed = {c.TERTIARY: "tertiary_kw_per_bed", c.REGIONAL: "regional_kw_per_bed"}
        if node.node_class in per_bed:
            beds = float(attributes["bed_count"])
            return beds * self.n("electricity." + per_bed[node.node_class]) / KW_PER_MW
        constant = {
            c.CLINIC: "clinic_mw", c.BLOOD_BANK: "blood_bank_mw", c.EXCHANGE: "exchange_mw",
            c.MAST: "mast_mw", c.CABLE_LANDING: "cable_landing_mw",
            c.FREIGHT_YARD: "freight_yard_mw", c.TANK_FARM: "tank_farm_mw", c.DEPOT: "depot_mw",
        }  # fmt: skip
        if node.node_class in constant:
            return self.n("electricity." + constant[node.node_class])
        derived: Mapping[NodeClass, Callable[[Attributes, Attributes], float]] = {
            c.DATA_CENTRE: lambda a, s: self.data_centre_site_mw(),
            c.TREATMENT: self._treatment,
            c.PUMPING: self._pumping,
            c.SEAPORT: self._seaport,
            c.AIRPORT: self._airport,
            c.REFINERY: lambda a, s: self.refinery_barrels() * self.n(
                "electricity.refinery_kwh_per_barrel"
            ) / HOURS_PER_DAY / KW_PER_MW,
            c.IMPORT_TERMINAL: self._terminal,
        }  # fmt: skip
        return derived[node.node_class](attributes, subtype)

    def data_centre_site_mw(self) -> float:
        return self.n("electricity.data_centre_it_load_mw") * self.n("electricity.data_centre_pue")

    def refinery_barrels(self) -> float:
        return self.n("throughput.refinery_barrels_per_day")

    def _treatment(self, attributes: Attributes, subtype: Attributes) -> float:
        flow = float(attributes["capacity_m3_per_day"])
        return flow * self.n("electricity.treatment_kwh_per_m3") / HOURS_PER_DAY / KW_PER_MW

    def _pumping(self, attributes: Attributes, subtype: Attributes) -> float:
        flow_m3_per_s = float(attributes["capacity_m3_per_day"]) / SECONDS_PER_DAY
        power_kw = (
            self.n("electricity.gravity_m_per_s2")
            * flow_m3_per_s
            * self.n("electricity.pumping_head_m")
            / self.n("electricity.pumping_efficiency")
        )
        return power_kw / KW_PER_MW

    def _seaport(self, attributes: Attributes, subtype: Attributes) -> float:
        teu = self.rules.value(REQ + "throughput.seaport_teu_per_year")[
            str(attributes["size_class"])
        ]
        boxes = float(teu) / self.n("throughput.teu_per_box")
        return boxes * self.n("electricity.seaport_kwh_per_box") / HOURS_PER_YEAR / KW_PER_MW

    def _airport(self, attributes: Attributes, subtype: Attributes) -> float:
        table = self.rules.value(REQ + "throughput.airport_passengers_per_year")
        passengers = float(table[str(attributes["size_class"])])
        kwh = passengers * self.n("electricity.airport_kwh_per_passenger")
        return kwh / HOURS_PER_YEAR / KW_PER_MW

    def _terminal(self, attributes: Attributes, subtype: Attributes) -> float:
        product = str(subtype["product"])
        if product == "lng":
            return self.n("throughput.lng_terminal_mtpa") * self.n(
                "electricity.import_terminal_lng_mw_per_mtpa"
            )
        return self.n(f"electricity.import_terminal_{product}_mw")

    def water(self, node: Node) -> float:
        """Target water draw (m³/day)."""
        c = NodeClass
        attributes = dict(node.attributes)
        per_bed = {c.TERTIARY: "tertiary_m3_per_bed_day", c.REGIONAL: "regional_m3_per_bed_day"}
        if node.node_class in per_bed:
            return float(attributes["bed_count"]) * self.n("water." + per_bed[node.node_class])
        if node.node_class == c.DATA_CENTRE:
            return self.data_centre_site_mw() * self.n("water.data_centre_m3_per_mw_day")
        if node.node_class == c.REFINERY:
            crude = self.refinery_barrels() * CUBIC_METRES_PER_BARREL
            return crude * self.n("water.refinery_m3_per_m3_crude")
        constant = {
            c.CLINIC: "clinic_m3_per_day", c.BLOOD_BANK: "blood_bank_m3_per_day",
            c.GENERATION: "generation_municipal_m3_per_day",
            c.TANK_FARM: "fuel_facility_m3_per_day", c.IMPORT_TERMINAL: "fuel_facility_m3_per_day",
            c.DEPOT: "fuel_facility_m3_per_day",
        }  # fmt: skip
        return self.n("water." + constant[node.node_class])

    def fuel(self, node: Node, notes: set[str]) -> float | None:
        """Target fuel draw (GJ/day); None, with a note, where no target exists yet."""
        if node.node_class != NodeClass.GENERATION:
            open_rule = {
                NodeClass.AIRPORT: "airport_jet_fuel",
                NodeClass.FREIGHT_YARD: "freight_yard_diesel",
                NodeClass.SEAPORT: "seaport_fuel",
            }[node.node_class]
            decision = self.rules.rule(REQ + "fuel." + open_rule).open_decision
            notes.add(f"{node.node_class}: fuel draw has no target (open decision: {decision})")
            return None
        attributes, subtype = dict(node.attributes), dict(node.subtype)
        heat_rate = self.n(f"fuel.{subtype['fuel_kind']}_gj_per_mwh")
        output_mw = float(attributes["capacity_mw"]) * self.n("fuel.generation_capacity_factor")
        return output_mw * HOURS_PER_DAY * heat_rate

    def backup_burn(self, node: Node, electricity_mw: float | None) -> float | None:
        """Full-load burn of the node's diesel standby generator, if it has one (L/h)."""
        if electricity_mw is None or dict(node.subtype).get("standby_fuel") != "diesel":
            return None
        return electricity_mw * self.n("fuel.backup_generator_l_per_h_per_mw")


def requirement_table(result: RequirementsResult) -> list[dict[str, object]]:
    """Return the requirements as plain data in a fixed key order, for canonical output.

    Parameters
    ----------
    result : RequirementsResult
        The requirements stage's output.

    Returns
    -------
    list of dict
        One row per node; numbers rounded to six decimals.

    Spec: Work Order 5, B2.
    """
    return [
        {
            "id": node.node_id,
            "class": node.node_class.value,
            "electricity_mw": _round(node.electricity_mw),
            "peak_mw": _round(node.peak_mw),
            "water_m3_per_day": _round(node.water_m3_per_day),
            "fuel_gj_per_day": _round(node.fuel_gj_per_day),
            "backup_burn_l_per_h": _round(node.backup_burn_l_per_h),
            "telecom": node.telecom,
            "transport": node.transport,
        }
        for node in result.nodes
    ]


def statistics_record(result: RequirementsResult) -> dict[str, object]:
    """Return totals per commodity, the levers and the notes, in a fixed order.

    Parameters
    ----------
    result : RequirementsResult
        The requirements stage's output.

    Returns
    -------
    dict
        Plain data ready for canonical YAML.

    Spec: Work Order 5, B2 and B3.
    """

    def total(values: list[float | None]) -> dict[str, object]:
        present = [v for v in values if v is not None]
        return {"nodes": len(present), "total": _round(math.fsum(present))}

    nodes = result.nodes
    record: dict[str, object] = {
        "levers": {
            "heterogeneity": result.levers.heterogeneity,
            "compliance_gap": result.levers.compliance_gap,
            "spread": _round(result.levers.spread),
            "spread_capped": result.spread_capped,
        },
        "electricity_mw": total([n.electricity_mw for n in nodes]),
        "peak_mw": total([n.peak_mw for n in nodes]),
        "water_m3_per_day": total([n.water_m3_per_day for n in nodes]),
        "fuel_gj_per_day": total([n.fuel_gj_per_day for n in nodes]),
        "backup_burn_l_per_h": total([n.backup_burn_l_per_h for n in nodes]),
        "telecom_consumers": sum(n.telecom for n in nodes),
        "transport_consumers": sum(n.transport for n in nodes),
        "notes": list(result.notes),
    }
    return record


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)
