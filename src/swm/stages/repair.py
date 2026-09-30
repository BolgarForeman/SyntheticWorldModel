"""Repair stage: permanent and emergency repair per node, and travel from the crew base.

Every damaged node has up to two alternative modes (structure v0.6 §4.4a):
- **permanent:** a lead time that holds no crew (assessment and parts), then crew work hours,
  restoring full capacity. The centre is the Hazus MR4 restoration mean for the node's class
  and damage state; crew work is a placeholder by damage state, and lead time is the drawn
  repair time less the crew work, floored at 0;
- **emergency**, for distribution substations (a mobile substation) and masts (a mobile cell
  site) only: set-up plus travel, using one unit from a finite pool, restoring reduced capacity
  for the rest of the event.

Travel over roads from the crew base is its own term, recorded per node, never a multiplier on
repair time. Reservoirs cannot be repaired inside the window.

The stage records repair per node and damage state; which nodes are damaged, and how badly, is
Work Order 6. All of it is real but unobserved.

Spec: structure v0.6 §4.4 and §4.4a (repair); Work Order 5, Part G; decision 0009.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np

from swm import rng
from swm.draws import DrawMethod, Levers
from swm.recipe.dependencies import Role
from swm.recipe.schema import ContinuousDrawnQuantity, Layer, NodeClass
from swm.rules.registry import Registry
from swm.stages.couplings import CouplingsResult
from swm.stages.crews import ELIGIBLE_CLASS, CrewBase, CrewsResult, RoadNetwork
from swm.stages.layers import LayersResult, Node
from swm.stages.requirements import RequirementsResult
from swm.stages.terrain import TerrainResult

HOURS_PER_DAY = 24.0


@dataclass(frozen=True)
class Travel:
    """Travel from a crew base to a node: road distance, and hours at the crews' road speed."""

    node_id: str
    base_id: str
    road_km: float
    """From the base to the node, or to the seaport a crew sails from if ``by_sea``."""
    by_sea: bool
    """The node is off the base's road network; the mobilisation delay covers the crossing."""
    travel_h: float


@dataclass(frozen=True)
class PermanentRepair:
    """The permanent repair of one node at one damage state."""

    node_id: str
    damage_state: str
    hazus_mean_h: float
    hazus_sd_h: float
    repair_h: float
    """Drawn around the Hazus mean; lead time plus crew work, unless the floor applies."""
    crew_work_h: float
    lead_time_h: float
    """repair_h less the crew work, floored at 0: it holds no crew."""


@dataclass(frozen=True)
class EmergencyRepair:
    """The emergency mode of one eligible node: a mobile unit from the pool."""

    node_id: str
    unit_kind: str
    set_up_h: float
    travel_h: float
    """From the base the pool is kept at."""
    total_h: float
    capacity_mva: float | None
    restored_share: float
    """Share of the node's normal peak load the unit restores for the rest of the event."""


@dataclass(frozen=True)
class RepairResult:
    """The repair stage's output. Real but unobserved: never emitted."""

    travel: tuple[Travel, ...]
    permanent: tuple[PermanentRepair, ...]
    emergency: tuple[EmergencyRepair, ...]
    unrepairable: tuple[str, ...]
    """Nodes that cannot be repaired inside the window."""
    notes: tuple[str, ...]


def repair_streams(root_seed: int) -> Mapping[Layer, np.random.Generator]:
    """Return the ``repair/<layer>`` streams.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.

    Returns
    -------
    Mapping
        One stream per layer.

    Spec: Work Order 5, G1.
    """
    return {layer: rng.stream(root_seed, f"repair/{layer}") for layer in Layer}


def build_repair(
    levers: ContinuousDrawnQuantity,
    crews: CrewsResult,
    terrain: TerrainResult,
    layers: LayersResult,
    requirements: RequirementsResult,
    couplings: CouplingsResult,
    rules: Registry,
    streams: Mapping[Layer, np.random.Generator],
) -> RepairResult:
    """Record travel, permanent repair and emergency repair for every node.

    Parameters
    ----------
    levers : ContinuousDrawnQuantity
        The recipe's repair-rate levers: heterogeneity and compliance gap, in percent.
    crews : CrewsResult
        The crew bases and the emergency pool.
    terrain : TerrainResult
        The ground: land and cell size, for the legs that join a node to the roads.
    layers : LayersResult
        The layers, power sized; the transport links are the roads.
    requirements : RequirementsResult
        The requirements: the peak loads a mobile substation is weighed against.
    couplings : CouplingsResult
        The couplings: which consumers each distribution substation supplies.
    rules : Registry
        The modeling rules in force.
    streams : Mapping
        The ``repair/<layer>`` streams.

    Returns
    -------
    RepairResult
        Travel, permanent and emergency repair, the unrepairable nodes and notes.

    Spec: structure v0.6 §4.4a (repair); Work Order 5, G1-G3.
    """
    network = RoadNetwork(terrain, layers)
    speed_kmh = rules.number("crews.road_speed_kmh")
    mobilisation_h = rules.number("crews.outlying_island_mobilisation_h")
    notes: set[str] = set()

    def travel(base: CrewBase, node: Node) -> Travel | None:
        return _travel(base, node, network, speed_kmh, mobilisation_h)

    travels = []
    for node in layers.nodes:
        options = [t for base in crews.bases if (t := travel(base, node)) is not None]
        if not options:
            notes.add(f"{node.node_class}: no road or sea route from a crew base; no travel time")
            continue
        travels.append(min(options, key=lambda t: (t.travel_h, t.base_id)))
    permanent, unrepairable = _permanent(levers, layers, rules, streams, notes)
    emergency = _emergency(crews, layers, requirements, couplings, rules, travel, notes)
    return RepairResult(
        tuple(travels),
        tuple(permanent),
        tuple(emergency),
        tuple(unrepairable),
        tuple(sorted(notes)),
    )


def _travel(
    base: CrewBase, node: Node, network: RoadNetwork, speed_kmh: float, mobilisation_h: float
) -> Travel | None:
    """Travel from one base: by road if the roads join them, else to a seaport and by sea."""
    road = network.road_km(base.access_node_id)
    access = network.access(node.row, node.column)
    if access is not None and access[0].node_id in road:
        km = base.access_km + road[access[0].node_id] + access[1]
        return Travel(node.node_id, base.base_id, km, False, km / speed_kmh)
    seaports = [
        n for n in network.transport if n.node_class == NodeClass.SEAPORT and n.node_id in road
    ]
    if not seaports:
        return None
    # CHOICE: a node off the base's roads is reached from the base's nearest seaport; the
    # outlying-island mobilisation delay covers the crossing and the travel on the far side.
    port = min(seaports, key=lambda n: (road[n.node_id], n.node_id))
    km = base.access_km + road[port.node_id]
    return Travel(node.node_id, base.base_id, km, True, km / speed_kmh + mobilisation_h)


def _permanent(
    levers: ContinuousDrawnQuantity,
    layers: LayersResult,
    rules: Registry,
    streams: Mapping[Layer, np.random.Generator],
    notes: set[str],
) -> tuple[list[PermanentRepair], list[str]]:
    """Draw each node's repair rate once, and split its repair time at each damage state."""
    hazus = rules.value("repair.hazus_restoration_days")
    crew_work = rules.value("repair.crew_work_h")
    unrepairable_classes = set(rules.value("repair.unrepairable"))
    method = DrawMethod.from_registry(rules)
    rate = Levers.from_percent(levers.heterogeneity_pct, levers.compliance_gap_pct)
    table = method.mixture(rate.spread)
    records: list[PermanentRepair] = []
    unrepairable: list[str] = []
    for node in layers.nodes:
        # Every node takes its draw, so a class becoming repairable never moves another's.
        u = float(streams[node.layer].random())
        if node.node_class in unrepairable_classes:
            unrepairable.append(node.node_id)
            continue
        if node.node_class not in hazus:
            notes.add(f"{node.node_class}: no Hazus restoration row; no permanent repair")
            continue
        # CHOICE: the drawn quantity is the repair rate, so a positive compliance gap slows
        # repair (median time = Hazus mean / (1 - gap)); one draw per node serves every damage
        # state, so a node slow to repair is slow at each.
        factor = (1.0 - rate.compliance_gap) * method.quantile(table, u)
        # CHOICE: the damage states recorded are those with crew work hours (§4.4a).
        for state in crew_work:
            mean_h = float(hazus[node.node_class][state]["mean"]) * HOURS_PER_DAY
            repair_h = mean_h / factor
            work_h = float(crew_work[state])
            records.append(
                PermanentRepair(
                    node_id=node.node_id,
                    damage_state=state,
                    hazus_mean_h=mean_h,
                    hazus_sd_h=float(hazus[node.node_class][state]["sd"]) * HOURS_PER_DAY,
                    repair_h=repair_h,
                    crew_work_h=work_h,
                    lead_time_h=max(0.0, repair_h - work_h),
                )
            )
    return records, unrepairable


def _emergency(
    crews: CrewsResult,
    layers: LayersResult,
    requirements: RequirementsResult,
    couplings: CouplingsResult,
    rules: Registry,
    travel: Callable[[CrewBase, Node], Travel | None],
    notes: set[str],
) -> list[EmergencyRepair]:
    """Record the emergency mode of every node of an eligible class, if the pool has a unit."""
    bases = {base.base_id: base for base in crews.bases}
    homes: dict[str, CrewBase] = {}
    for unit in crews.units:
        homes.setdefault(unit.kind, bases[unit.base_id])
    peaks = _normal_peak_mw(requirements, couplings)
    power_factor = rules.number("sizing.power.power_factor")
    records: list[EmergencyRepair] = []
    for node in layers.nodes:
        for kind, node_class in ELIGIBLE_CLASS.items():
            if node.node_class != node_class:
                continue
            if kind not in homes:
                notes.add(f"{node_class}: the emergency pool holds no {kind}")
                continue
            trip = travel(homes[kind], node)
            if trip is None:
                continue
            peak_mw = peaks.get(node.node_id, 0.0)
            set_up_h, capacity_mva, share = _unit(kind, peak_mw, power_factor, rules)
            records.append(
                EmergencyRepair(
                    node.node_id,
                    kind,
                    set_up_h,
                    trip.travel_h,
                    set_up_h + trip.travel_h,
                    capacity_mva,
                    share,
                )
            )
    return records


def _unit(
    kind: str, peak_mw: float, power_factor: float, rules: Registry
) -> tuple[float, float | None, float]:
    """Return a mobile unit's set-up hours, its capacity (MVA) and the share it restores."""
    if kind == "mobile_substation":
        value = rules.value("repair.emergency.mobile_substation")
        # CHOICE: §4.4a gives 12-24 h including travel; the low end is the set-up at no
        # travel, and travel is added as its own term.
        set_up_h = float(value["hours_including_travel"][0])
        capacity_mva = float(value["capacity_mva"])
        supply_mw = capacity_mva * power_factor
        share = 1.0 if peak_mw <= supply_mw else supply_mw / peak_mw
        return set_up_h, capacity_mva, share
    value = rules.value("repair.emergency.mobile_cell_site")
    # CHOICE: the mobile cell site's 14 h is its set-up; travel is added as its own term.
    return float(value["hours"]), None, float(value["capacity"])


def _normal_peak_mw(
    requirements: RequirementsResult, couplings: CouplingsResult
) -> dict[str, float]:
    """Peak load (MW) each power supplier carries in the undisturbed world, on primary edges."""
    needs = requirements.by_id()
    peaks: dict[str, float] = {}
    for edge in couplings.edges:
        if edge.supplier_layer != Layer.POWER or edge.role != Role.PRIMARY_SUPPLY:
            continue
        peak = needs[edge.consumer_id].peak_mw or 0.0
        share = peak / 2 if edge.feed_configuration == "two_half" else peak
        peaks[edge.supplier_id] = peaks.get(edge.supplier_id, 0.0) + share
    return peaks


def repair_tables(result: RepairResult) -> dict[str, list[dict[str, object]]]:
    """Return every repair table as plain data in a fixed order, for canonical output.

    Parameters
    ----------
    result : RepairResult
        The repair stage's output.

    Returns
    -------
    dict
        Tables by name, numbers rounded to six decimals.

    Spec: Work Order 5, Part G.
    """

    def plain(record: object) -> dict[str, object]:
        return {
            name: round(value, 6) if isinstance(value, float) else value
            for name, value in vars(record).items()
        }

    return {
        "travel": [plain(t) for t in result.travel],
        "permanent_repair": [plain(p) for p in result.permanent],
        "emergency_repair": [plain(e) for e in result.emergency],
        "unrepairable": [{"node_id": node_id} for node_id in result.unrepairable],
    }


def statistics_record(result: RepairResult, crews: CrewsResult) -> dict[str, object]:
    """Return the crews, travel, repair times per damage state and emergency options.

    Parameters
    ----------
    result : RepairResult
        The repair stage's output.
    crews : CrewsResult
        The crews stage's output.

    Returns
    -------
    dict
        Plain data ready for canonical YAML.

    Spec: Work Order 5, Parts G and H.
    """
    states: dict[str, object] = {}
    for state in dict.fromkeys(p.damage_state for p in result.permanent):
        records = [p for p in result.permanent if p.damage_state == state]
        states[state] = {
            "nodes": len(records),
            "mean_hazus_h": _mean([p.hazus_mean_h for p in records]),
            "mean_repair_h": _mean([p.repair_h for p in records]),
            "mean_lead_time_h": _mean([p.lead_time_h for p in records]),
            "lead_time_floored": sum(p.repair_h < p.crew_work_h for p in records),
        }
    emergency: dict[str, object] = {}
    for kind in dict.fromkeys(e.unit_kind for e in result.emergency):
        options = [e for e in result.emergency if e.unit_kind == kind]
        emergency[kind] = {
            "options": len(options),
            "mean_total_h": _mean([e.total_h for e in options]),
            "least_restored_share": round(min(e.restored_share for e in options), 6),
        }
    travel_h = [t.travel_h for t in result.travel]
    return {
        "crew_bases": [
            {
                "base_id": b.base_id,
                "city_id": b.city_id,
                "access_node_id": b.access_node_id,
                "crews": b.crews,
            }
            for b in crews.bases
        ],
        "crews": len(crews.crews),
        "mobile_units": {
            kind: sum(u.kind == kind for u in crews.units)
            for kind in dict.fromkeys(u.kind for u in crews.units)
        },
        "travel": {
            "nodes": len(travel_h),
            "by_sea": sum(t.by_sea for t in result.travel),
            "mean_h": _mean(travel_h),
            "longest_h": round(max(travel_h), 3) if travel_h else None,
        },
        "permanent_repair": states,
        "emergency_repair": emergency,
        "unrepairable": list(result.unrepairable),
        "notes": list(result.notes),
    }


def _mean(values: list[float]) -> float | None:
    return round(math.fsum(values) / len(values), 3) if values else None
