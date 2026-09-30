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

Power is sized here, once every load is known (decision 0010): total generation is the total
peak load of every power consumer times the reserve margin, and each transmission substation
carries at least the load it feeds. The stage returns the layers with those capacities.

Spec: structure v0.6 §4.4 and §4.4a; Work Order 5, Part B; decision 0009.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

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
L_PER_M3 = 1000.0
DAYS_PER_YEAR = 365.0
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
    power: "PowerSizing"
    layers: LayersResult
    """The layers with generation and transmission sized to load."""
    notes: tuple[str, ...]

    def by_id(self) -> dict[str, NodeRequirements]:
        """Return the requirements keyed by node id."""
        return {node.node_id: node for node in self.nodes}


@dataclass(frozen=True)
class PowerSizing:
    """How power was sized to load (decision 0010)."""

    total_peak_mw: float
    """Peak load of every power consumer (MW)."""
    transmission_fed_peak_mw: float
    """Peak load of the consumers a transmission substation supplies directly (MW)."""
    threshold_mw: float
    """The rule 4 threshold in force (MW)."""
    generation_mw: float
    """Total generation capacity after sizing (MW)."""


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
    distribution_voltage_kv: float,
) -> RequirementsResult:
    """Draw every node's requirement for each commodity it consumes, then size power to load.

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
    distribution_voltage_kv : float
        The recipe's distribution voltage, which sets the rule 4 threshold.

    Returns
    -------
    RequirementsResult
        One record per node, the levers, the power sizing, the sized layers and notes.

    Spec: structure v0.6 §4.2, §4.4 and §4.4a; Work Order 5, B1-B4; decision 0010.
    """
    method = DrawMethod.from_registry(rules)
    drawn = Levers.from_percent(levers.heterogeneity_pct, levers.compliance_gap_pct)
    capped = drawn.spread > method.largest_spread
    quantiles = method.mixture(drawn.spread)
    targets = _Targets(rules)
    notes: set[str] = set()
    records = []
    generation_draws: dict[str, float] = {}
    for node in layers.nodes:
        stream = streams[node.layer]

        def around(target: float | None, stream: np.random.Generator = stream) -> float | None:
            if target is None:
                return None
            scale = target * (1.0 - drawn.compliance_gap)
            return scale * method.quantile(quantiles, float(stream.random()))

        consumed = _consumed(node, rules)
        electricity = around(targets.electricity(node)) if Layer.POWER in consumed else None
        water = around(targets.water(node)) if Layer.WATER in consumed else None
        fuel = None
        if Layer.FUEL in consumed and node.node_class == NodeClass.GENERATION:
            # A plant's fuel follows its sized capacity; its draw is taken here, in order.
            generation_draws[node.node_id] = float(stream.random())
        elif Layer.FUEL in consumed:
            fuel = around(targets.fuel(node))
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
    threshold = float(
        rules.value("dependencies.rule_4.transmission_threshold_mw")[f"{distribution_voltage_kv:g}"]
    )
    sized, power = _size_power(layers, records, rules, threshold, streams[Layer.POWER], notes)
    plants = {node.node_id: node for node in sized.nodes if node.node_id in generation_draws}
    records = [
        replace(
            record,
            fuel_gj_per_day=targets.generation_fuel(plants[record.node_id])
            * (1.0 - drawn.compliance_gap)
            * method.quantile(quantiles, generation_draws[record.node_id]),
        )
        if record.node_id in plants
        else record
        for record in records
    ]
    if capped:
        notes.add(
            f"requirements spread {drawn.spread:.2f} is above the largest tabulated "
            f"{method.largest_spread:g}; held to it"
        )
    return RequirementsResult(tuple(records), drawn, capped, power, sized, tuple(sorted(notes)))


def transmission_fed(
    row_suppliers: tuple[NodeClass, ...], peak_mw: float, threshold_mw: float
) -> bool:
    """Return whether a transmission substation supplies a power consumer (§4.3a rule 4).

    Parameters
    ----------
    row_suppliers : tuple of NodeClass
        The supplier classes its power row names.
    peak_mw : float
        Its peak load (MW).
    threshold_mw : float
        The rule 4 threshold (MW).

    Returns
    -------
    bool
        True at or above the threshold, or where its row names only a transmission substation.

    Spec: structure v0.6 §4.3a rule 4; decision 0010.
    """
    only_transmission = set(row_suppliers) == {NodeClass.TRANSMISSION_SUBSTATION}
    return peak_mw >= threshold_mw or only_transmission


def _size_power(
    layers: LayersResult,
    records: list[NodeRequirements],
    rules: Registry,
    threshold_mw: float,
    stream: np.random.Generator,
    notes: set[str],
) -> tuple[LayersResult, PowerSizing]:
    """Size generation and transmission to load (structure v0.6 §4.2; decision 0010).

    Total generation is the total peak load of every power consumer times the reserve margin.
    A transmission substation carries at least the reserve margin times the distribution
    capacity it feeds over the power links, plus the transmission-fed load converted to MVA
    with the power factor. The generation total is split across plants by draw.
    """
    margin = rules.number("sizing.power.reserve_margin")
    power_factor = rules.number("sizing.power.power_factor")
    floor = rules.number("sizing.power.generation_split_floor")
    nodes = {node.node_id: node for node in layers.nodes}
    peaks = [(record, nodes[record.node_id]) for record in records if record.peak_mw is not None]
    total_peak = math.fsum(record.peak_mw or 0.0 for record, _ in peaks)
    large_peak = math.fsum(
        record.peak_mw or 0.0
        for record, node in peaks
        if transmission_fed(_power_suppliers(node, rules), record.peak_mw or 0.0, threshold_mw)
    )
    distribution = {
        node.node_id: float(dict(node.attributes)["capacity_mva"])
        for node in layers.nodes
        if node.node_class == NodeClass.DISTRIBUTION_SUBSTATION
    }
    power_links = [link for link in layers.links if link.layer == Layer.POWER]
    sized: dict[str, dict[str, AttributeValue]] = {}
    for node in layers.nodes:
        if node.node_class != NodeClass.TRANSMISSION_SUBSTATION:
            continue
        ends = [(link.from_id, link.to_id) for link in power_links]
        fed = sorted(b if a == node.node_id else a for a, b in ends if node.node_id in (a, b))
        # CHOICE: every transmission substation can carry all transmission-fed load, since the
        # couplings stage, which comes later, decides which one supplies each large consumer.
        load_mva = math.fsum(distribution[i] for i in fed if i in distribution)
        needed = math.ceil(margin * (load_mva + large_peak / power_factor))
        drawn = int(dict(node.attributes)["capacity_mva"])
        sized[node.node_id] = {"capacity_mva": max(drawn, needed)}
    plants = [node for node in layers.nodes if node.node_class == NodeClass.GENERATION]
    generation = math.fsum(float(dict(p.attributes)["capacity_mw"]) for p in plants)
    if plants and total_peak == 0.0:
        notes.add("generation: no power consumers, so plants keep drawn capacities")
    elif plants:
        total_mw = total_peak * margin
        weights = [floor + float(stream.random()) for _ in plants]
        whole = math.fsum(weights)
        for plant, weight in zip(plants, weights, strict=True):
            sized[plant.node_id] = {"capacity_mw": round(total_mw * weight / whole, 1)}
        generation = math.fsum(float(sized[p.node_id]["capacity_mw"]) for p in plants)
    resized = tuple(
        replace(
            node, attributes=tuple(sorted({**dict(node.attributes), **sized[node.node_id]}.items()))
        )
        if node.node_id in sized
        else node
        for node in layers.nodes
    )
    power = PowerSizing(
        total_peak_mw=total_peak,
        transmission_fed_peak_mw=large_peak,
        threshold_mw=threshold_mw,
        generation_mw=generation,
    )
    return replace(layers, nodes=resized), power


def _power_suppliers(node: Node, rules: Registry) -> tuple[NodeClass, ...]:
    row = resolve_row(Layer.POWER, node.node_class, dict(node.subtype), rules)
    return tuple(option.node_class for option in row.suppliers)


def _consumed(node: Node, rules: Registry) -> set[Layer]:
    """Supplier layers the node takes a primary-supply dependency from (core or optional)."""
    # CHOICE: a requirement is drawn for every commodity the table lets the node take, core or
    # optional, since requirements come before density decides which optional edges exist.
    # Buffer-resupply fuel is a backup burn, recorded as a rate, not a requirement.
    subtype = dict(node.subtype)
    consumed = set()
    for supplier, consumer in coupling_pairs():
        if consumer != node.layer:
            continue
        row = resolve_row(supplier, node.node_class, subtype, rules)
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
        # CHOICE: a data centre's water follows its target site load, not its drawn one, so
        # the two requirements are drawn independently around their own targets.
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

    def fuel(self, node: Node) -> float:
        """Target fuel draw of a transport consumer (GJ/day); placeholders (decision 0010)."""
        attributes = dict(node.attributes)
        if node.node_class == NodeClass.AIRPORT:
            table = self.rules.value(REQ + "throughput.airport_passengers_per_year")
            passengers = float(table[str(attributes["size_class"])])
            litres = passengers * self.n("fuel.airport_jet_fuel_l_per_passenger")
            return litres / L_PER_M3 / DAYS_PER_YEAR * self.n("fuel.jet_fuel_gj_per_m3")
        if node.node_class == NodeClass.SEAPORT:
            table = self.rules.value(REQ + "throughput.seaport_teu_per_year")
            boxes = float(table[str(attributes["size_class"])]) / self.n("throughput.teu_per_box")
            per_box = self.n("fuel.seaport_cargo_diesel_l_per_box") + self.n(
                "fuel.seaport_bunkers_l_per_box"
            )
            litres = boxes * per_box
            return litres / L_PER_M3 / DAYS_PER_YEAR * self.n("fuel.diesel_gj_per_m3")
        area = float(attributes["area_m2"])
        litres_per_day = area * self.n("fuel.freight_yard_diesel_l_per_m2_day")
        return litres_per_day / L_PER_M3 * self.n("fuel.diesel_gj_per_m3")

    def generation_fuel(self, node: Node) -> float:
        """Target fuel draw of a thermal plant at its sized capacity (GJ/day)."""
        attributes, subtype = dict(node.attributes), dict(node.subtype)
        # CHOICE: a plant's output is its capacity times a capacity factor near 1 / the
        # reserve margin, since generation is sized to load times that margin.
        heat_rate = self.n(f"fuel.{subtype['fuel_kind']}_gj_per_mwh")
        output_mw = float(attributes["capacity_mw"]) * self.n("fuel.generation_capacity_factor")
        return output_mw * HOURS_PER_DAY * heat_rate

    def backup_burn(self, node: Node, electricity_mw: float | None) -> float | None:
        """Full-load burn of the node's diesel standby generator, if it has one (L/h)."""
        if electricity_mw is None or dict(node.subtype).get("standby_fuel") != "diesel":
            return None
        # CHOICE: the rate is at full load on the node's drawn electricity; the reserves stage
        # turns it into hours at the expected (essential) load (PR 5b).
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
        "power_sizing": {
            "total_peak_mw": _round(result.power.total_peak_mw),
            "transmission_fed_peak_mw": _round(result.power.transmission_fed_peak_mw),
            "threshold_mw": result.power.threshold_mw,
            "generation_mw": _round(result.power.generation_mw),
        },
        "telecom_consumers": sum(n.telecom for n in nodes),
        "transport_consumers": sum(n.transport for n in nodes),
        "notes": list(result.notes),
    }
    return record


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)
