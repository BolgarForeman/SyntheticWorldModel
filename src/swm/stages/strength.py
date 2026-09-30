"""Strength stage: coupling strength κ on every edge, and each dependency's supply ratio.

Derived, never drawn (structure v0.6 §4.4): κ = min(1, available supply / requirement), where
available supply is the supplier's capacity shared pro rata among its consumers. The uncapped
ratio is recorded as headroom. Telecom and transport are served or not: a telecom edge's κ is
its public share (rule 1) or 1, a transport edge's is 1.

A dependency's supply ratio R_φ in the undisturbed world adds its feed groups: each group
supplies the smallest headroom among its edges (two half feeds are both needed), and the
groups add (either of two full feeds covers the need). The world check needs R_φ ≥ 1 for
every consumer and commodity.

Spec: structure v0.6 §4.4 (coupling strength, world check) and §4.4a; Work Order 5, Part E;
decision 0009.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from swm.recipe.schema import Layer, NodeClass
from swm.rules.registry import Registry
from swm.stages.couplings import CouplingEdge, CouplingsResult
from swm.stages.layers import LayersResult, Node
from swm.stages.requirements import NodeRequirements, RequirementsResult

HOURS_PER_DAY = 24.0
L_PER_M3 = 1000.0

BINARY = (Layer.TELECOM, Layer.TRANSPORT)
"""Layers whose requirement is served or not (§4.4a)."""


@dataclass(frozen=True)
class EdgeStrength:
    """Coupling strength of one edge. Real but unobserved: never emitted."""

    edge_id: str
    requirement: float | None
    """What the edge must carry (MW, m³/day or GJ/day); None where served-or-not."""
    available: float | None
    headroom: float | None
    """Uncapped available supply / requirement."""
    kappa: float


@dataclass(frozen=True)
class SupplyRatio:
    """A dependency's supply ratio R_φ in the undisturbed world."""

    dependency_id: str
    consumer_id: str
    supplier_layer: Layer
    ratio: float
    """Capped at 1."""
    uncapped: float


@dataclass(frozen=True)
class StrengthResult:
    """The strength stage's output."""

    edges: tuple[EdgeStrength, ...]
    ratios: tuple[SupplyRatio, ...]
    notes: tuple[str, ...]


def build_strength(
    layers: LayersResult,
    requirements: RequirementsResult,
    couplings: CouplingsResult,
    rules: Registry,
) -> StrengthResult:
    """Derive κ and headroom on every edge, and R_φ for every primary-supply dependency.

    Parameters
    ----------
    layers : LayersResult
        The layers, power sized.
    requirements : RequirementsResult
        The requirements.
    couplings : CouplingsResult
        The couplings.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    StrengthResult
        Edge strengths, supply ratios and notes.

    Spec: structure v0.6 §4.4; Work Order 5, E1.
    """
    nodes = {node.node_id: node for node in layers.nodes}
    needs = requirements.by_id()
    capacity = _Capacity(rules)
    requirement = {
        edge.edge_id: _requirement(edge, needs[edge.consumer_id], nodes[edge.consumer_id], rules)
        for edge in couplings.edges
    }
    primary: dict[str, float] = {}
    everything: dict[str, float] = {}
    for edge in couplings.edges:
        amount = requirement[edge.edge_id]
        if amount is None:
            continue
        everything[edge.supplier_id] = everything.get(edge.supplier_id, 0.0) + amount
        if edge.role == "primary_supply":
            primary[edge.supplier_id] = primary.get(edge.supplier_id, 0.0) + amount
    notes: set[str] = set()
    strengths = []
    for edge in couplings.edges:
        amount = requirement[edge.edge_id]
        if amount is None or edge.supplier_layer in BINARY:
            share = edge.public_share_pct
            strengths.append(
                EdgeStrength(edge.edge_id, None, None, None, 1.0 if share is None else share / 100)
            )
            continue
        # CHOICE: a buffer edge is weighed against every draw on its supplier, as though every
        # generator ran at once; primary edges only against the undisturbed primary draws.
        load = (primary if edge.role == "primary_supply" else everything)[edge.supplier_id]
        supply = capacity.of(nodes[edge.supplier_id], edge.supplier_layer, notes)
        available = supply * amount / load if load > 0.0 else supply
        headroom = available / amount if amount > 0.0 else math.inf
        strengths.append(
            EdgeStrength(edge.edge_id, amount, available, headroom, min(1.0, headroom))
        )
    ratios = _ratios(couplings, {s.edge_id: s for s in strengths})
    return StrengthResult(tuple(strengths), tuple(ratios), tuple(sorted(notes)))


def _requirement(
    edge: CouplingEdge, need: NodeRequirements, consumer: Node, rules: Registry
) -> float | None:
    """Return what one edge must carry, in its supplier's units; None if served-or-not."""
    if edge.supplier_layer in BINARY:
        return None
    if edge.role == "buffer_resupply":
        # A generator's fuel at its expected load, as a daily rate in GJ.
        load = need.electricity_mw or 0.0
        if consumer.node_class in (NodeClass.TERTIARY, NodeClass.REGIONAL):
            load *= rules.number("reserves.hospital.essential_load_fraction")
        litres = load * rules.number("requirements.fuel.backup_generator_l_per_h_per_mw")
        per_day = litres * HOURS_PER_DAY / L_PER_M3
        return per_day * rules.number("requirements.fuel.diesel_gj_per_m3")
    amount = {
        Layer.POWER: need.electricity_mw,
        Layer.WATER: need.water_m3_per_day,
        Layer.FUEL: need.fuel_gj_per_day,
    }[edge.supplier_layer]
    if amount is None:
        return None
    # Two half feeds are both needed, so each carries half; a full feed carries it all.
    return amount / 2 if edge.feed_configuration == "two_half" else amount


class _Capacity:
    """A supplier's capacity in the units its consumers draw (MW, m³/day, GJ/day)."""

    def __init__(self, rules: Registry) -> None:
        self.rules = rules
        self.days: Mapping[str, float] = rules.value("strength.supply_days")

    def of(self, node: Node, layer: Layer, notes: set[str]) -> float:
        attributes = dict(node.attributes)
        rules = self.rules
        if layer == Layer.POWER:
            mva = float(attributes["capacity_mva"])
            return mva * rules.number("sizing.power.power_factor")
        if node.node_class == NodeClass.PUMPING:
            return float(attributes["capacity_m3_per_day"])
        volume = float(attributes["storage_m3"])
        key = node.node_class.value
        if node.node_class == NodeClass.IMPORT_TERMINAL:
            key = f"import_terminal_{dict(node.subtype)['product']}"
        days = float(self.days[key])
        per_day = volume / days
        if layer == Layer.WATER:
            return per_day
        return per_day * self._energy(node)

    def _energy(self, node: Node) -> float:
        """GJ per m³ of what a fuel store holds."""
        product = dict(node.subtype).get("product")
        if product == "lng":
            return self.rules.number("strength.lng_gj_per_m3")
        if product == "coal":
            return self.rules.number("strength.coal_gj_per_m3")
        # CHOICE: tank farms, refineries, depots and oil terminals hold oil products, counted
        # at the energy of diesel.
        return self.rules.number("requirements.fuel.diesel_gj_per_m3")


def _ratios(couplings: CouplingsResult, strengths: Mapping[str, EdgeStrength]) -> list[SupplyRatio]:
    edges = {edge.edge_id: edge for edge in couplings.edges}
    ratios = []
    for dependency in couplings.dependencies:
        if dependency.role != "primary_supply":
            continue
        if dependency.supplier_layer in BINARY:
            # Served or not; the private share of a control edge is the utility's own network.
            uncapped = 1.0 if dependency.edge_ids else 0.0
        else:
            groups: dict[int, list[float]] = {}
            for edge_id in dependency.edge_ids:
                headroom = strengths[edge_id].headroom
                groups.setdefault(edges[edge_id].feed_group, []).append(
                    math.inf if headroom is None else headroom
                )
            uncapped = math.fsum(min(group) for group in groups.values())
        ratios.append(
            SupplyRatio(
                dependency.dependency_id,
                dependency.consumer_id,
                dependency.supplier_layer,
                min(1.0, uncapped),
                uncapped,
            )
        )
    return ratios


def strength_tables(result: StrengthResult) -> dict[str, list[dict[str, object]]]:
    """Return the edge strengths and supply ratios as plain data, for canonical output.

    Parameters
    ----------
    result : StrengthResult
        The strength stage's output.

    Returns
    -------
    dict
        Tables by name; numbers rounded to six decimals, infinite headroom as None.

    Spec: Work Order 5, E1.
    """

    def num(value: float | None) -> float | None:
        if value is None or math.isinf(value):
            return None
        return round(value, 6)

    return {
        "edges": [
            {
                "id": s.edge_id,
                "requirement": num(s.requirement),
                "available": num(s.available),
                "headroom": num(s.headroom),
                "kappa": num(s.kappa),
            }
            for s in result.edges
        ],
        "ratios": [
            {
                "dependency": r.dependency_id,
                "consumer": r.consumer_id,
                "supplier_layer": r.supplier_layer.value,
                "ratio": num(r.ratio),
                "uncapped": num(r.uncapped),
            }
            for r in result.ratios
        ],
    }


def statistics_record(result: StrengthResult) -> dict[str, object]:
    """Return κ and headroom summaries, and the notes.

    Parameters
    ----------
    result : StrengthResult
        The strength stage's output.

    Returns
    -------
    dict
        Plain data ready for canonical YAML.

    Spec: Work Order 5, E1.
    """
    kappas = [s.kappa for s in result.edges]
    headrooms = [s.headroom for s in result.edges if s.headroom is not None]
    finite = [h for h in headrooms if not math.isinf(h)]
    short = [r for r in result.ratios if r.ratio < 1.0]
    return {
        "edges": len(kappas),
        "kappa_below_1": sum(k < 1.0 for k in kappas),
        "min_kappa": round(min(kappas), 6) if kappas else None,
        "min_headroom": round(min(finite), 6) if finite else None,
        "dependencies": len(result.ratios),
        "dependencies_short": len(short),
        "notes": list(result.notes),
    }
