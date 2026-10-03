"""Repair stage: permanent and emergency repair per node, and travel from the crew base.

Every damaged node has up to two alternative modes (structure v0.6 §4.4a):
- **permanent:** a lead time that holds no crew (assessment and parts), then crew work hours,
  restoring full capacity. The centre is the Hazus MR4 restoration mean for the node's class
  and damage state, and the spread its Hazus standard deviation / mean unless the recipe sets
  one; crew work is a placeholder by damage state, and lead time is the drawn repair time less
  the crew work, floored at 0;
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
from itertools import pairwise

import numpy as np

from swm import rng
from swm.draws import DrawMethod, Levers
from swm.recipe.dependencies import Role
from swm.recipe.schema import Layer, NodeClass, RepairRates
from swm.rules.registry import Registry
from swm.stages.couplings import CouplingsResult
from swm.stages.crews import ELIGIBLE_CLASS, CrewBase, CrewsResult, RoadNetwork
from swm.stages.layers import LayersResult, Node
from swm.stages.requirements import RequirementsResult
from swm.stages.roads import RoadMap, sub_polyline
from swm.stages.scenarios import (
    Kilometre,
    OverheadLine,
    crew_work_per_point_h,
    kilometres,
    overhead_lines,
)
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
    spread: float
    """The repair rate's spread: the Hazus standard deviation / mean, or the recipe's override."""
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
class LineRepair:
    """The repair of one overhead line, should the storm bring it down (§4.3b)."""

    line_id: str
    crew_work_h_per_failure_point: float
    """The scenario's crew work is this times the line's failure points (§4.3b)."""
    lead_time_h: float
    base_id: str | None
    travel_h: float | None
    """From the nearest crew base to the line's midpoint, by road then off road; None if no
    road on its landmass reaches it."""
    by_sea: bool


@dataclass(frozen=True)
class FailurePointTravel:
    """How a crew reaches one kilometre of a line, should it fail there (§4.3b, repair)."""

    line_id: str
    kilometre: int
    start_km: float
    end_km: float
    base_id: str | None
    road_km: float | None
    """From the crew base to the road point nearest the kilometre's midpoint."""
    offroad_km: float | None
    """From that road point to the line, walked and carried."""
    travel_h: float | None
    """None when no road on the line's landmass reaches it from any base."""


@dataclass(frozen=True)
class RepairResult:
    """The repair stage's output. Real but unobserved: never emitted."""

    travel: tuple[Travel, ...]
    permanent: tuple[PermanentRepair, ...]
    emergency: tuple[EmergencyRepair, ...]
    unrepairable: tuple[str, ...]
    """Nodes that cannot be repaired inside the window."""
    lines: tuple[LineRepair, ...]
    failure_points: tuple[FailurePointTravel, ...]
    """Travel to every kilometre of every overhead line (Work Order 6c, D1)."""
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
    levers: RepairRates,
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
    levers : RepairRates
        The recipe's repair-rate levers, in percent: the compliance gap, and the heterogeneity
        that overrides the Hazus spread when set.
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
        cell = (node.row, node.column)
        return _travel(base, node.node_id, cell, network, speed_kmh, mobilisation_h)

    def nearest(element_id: str, cell: tuple[int, int]) -> Travel | None:
        options = [
            trip
            for base in crews.bases
            if (trip := _travel(base, element_id, cell, network, speed_kmh, mobilisation_h))
        ]
        return min(options, key=lambda t: (t.travel_h, t.base_id)) if options else None

    travels = []
    for node in layers.nodes:
        trip = nearest(node.node_id, (node.row, node.column))
        if trip is None:
            notes.add(f"{node.node_class}: no road or sea route from a crew base; no travel time")
            continue
        travels.append(trip)
    permanent, unrepairable = _permanent(levers, layers, rules, streams, notes)
    emergency = _emergency(crews, layers, requirements, couplings, rules, travel, notes)
    mapped = overhead_lines(layers, couplings)
    reach = _RoadReach(crews.bases, RoadMap(terrain, layers), rules)
    lines = _line_repairs(mapped, rules, reach)
    points = [reach.to_kilometre(line, km) for line in mapped for km in kilometres(line)]
    return RepairResult(
        tuple(travels),
        tuple(permanent),
        tuple(emergency),
        tuple(unrepairable),
        tuple(lines),
        tuple(points),
        tuple(sorted(notes)),
    )


class _RoadReach:
    """Crew travel to a point near a line: by road to the nearest road point, then off road."""

    def __init__(self, bases: tuple[CrewBase, ...], roads: RoadMap, rules: Registry) -> None:
        self.bases = bases
        self.roads = roads
        self.road_kmh = rules.number("crews.road_speed_kmh")
        self.offroad_kmh = rules.number("crews.offroad_speed_kmh")

    def to_point(self, point: tuple[float, float]) -> tuple[str, float, float, float] | None:
        """Return (base id, road km, off-road km, hours) from the nearest base, or None."""
        foot = self.roads.nearest(point)
        if foot is None:
            return None
        best = None
        for base in self.bases:
            road_m = self.roads.distance_from(base.access_node_id, foot)
            if road_m is None:
                continue
            road_km = base.access_km + road_m / 1000
            offroad_km = foot.offroad_m / 1000
            hours = road_km / self.road_kmh + offroad_km / self.offroad_kmh
            if best is None or (hours, base.base_id) < (best[3], best[0]):
                best = (base.base_id, road_km, offroad_km, hours)
        return best

    def to_kilometre(self, line: OverheadLine, km: Kilometre) -> FailurePointTravel:
        trip = self.to_point(km.midpoint)
        if trip is None:
            return FailurePointTravel(
                line.line_id, km.index, km.start_km, km.end_km, None, None, None, None
            )
        base_id, road_km, offroad_km, hours = trip
        return FailurePointTravel(
            line.line_id, km.index, km.start_km, km.end_km, base_id, road_km, offroad_km, hours
        )


def _line_repairs(
    lines: tuple[OverheadLine, ...], rules: Registry, reach: _RoadReach
) -> list[LineRepair]:
    """Crew work per failure point, no lead time, and travel to the line's midpoint (§4.3b).

    A towered line's collapse is placed at its midpoint; a pole line's failure points take
    their own kilometre's travel (``failure_points``).
    """
    repairs = []
    for line in lines:
        work_h = crew_work_per_point_h(line, rules)
        trip = reach.to_point(_midpoint(line))
        if trip is None:
            repairs.append(LineRepair(line.line_id, work_h, 0.0, None, None, False))
            continue
        repairs.append(LineRepair(line.line_id, work_h, 0.0, trip[0], trip[3], False))
    return repairs


def _midpoint(line: OverheadLine) -> tuple[float, float]:
    steps = [
        math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]))
        for a, b in pairwise(line.points)
    ]
    half = math.fsum(steps) / 2
    return sub_polyline(line.points, steps, half, half)[0]


def _travel(
    base: CrewBase,
    element_id: str,
    cell: tuple[int, int],
    network: RoadNetwork,
    speed_kmh: float,
    mobilisation_h: float,
) -> Travel | None:
    """Travel from one base: by road if the roads join them, else to a seaport and by sea."""
    road = network.road_km(base.access_node_id)
    access = network.access(*cell)
    if access is not None and access[0].node_id in road:
        km = base.access_km + road[access[0].node_id] + access[1]
        return Travel(element_id, base.base_id, km, False, km / speed_kmh)
    seaports = [
        n for n in network.transport if n.node_class == NodeClass.SEAPORT and n.node_id in road
    ]
    if not seaports:
        return None
    # CHOICE: a node off the base's roads is reached from the base's nearest seaport; the
    # outlying-island mobilisation delay covers the crossing and the travel on the far side.
    port = min(seaports, key=lambda n: (road[n.node_id], n.node_id))
    km = base.access_km + road[port.node_id]
    return Travel(element_id, base.base_id, km, True, km / speed_kmh + mobilisation_h)


def _permanent(
    levers: RepairRates,
    layers: LayersResult,
    rules: Registry,
    streams: Mapping[Layer, np.random.Generator],
    notes: set[str],
) -> tuple[list[PermanentRepair], list[str]]:
    """Draw each node's repair rate once, and split its repair time at each damage state."""
    hazus = rules.value("repair.hazus_restoration_days")
    crew_work = rules.value("repair.crew_work_h")
    unrepairable_classes = set(rules.value("repair.unrepairable"))
    no_rows = set(rules.value("repair.no_repair_rows"))
    rates = _RateDraw(levers, DrawMethod.from_registry(rules))
    records: list[PermanentRepair] = []
    unrepairable: list[str] = []
    for node in layers.nodes:
        # Every node takes its draw, so a class becoming repairable never moves another's.
        u = float(streams[node.layer].random())
        if node.node_class in unrepairable_classes:
            unrepairable.append(node.node_id)
            continue
        if node.node_class in no_rows:
            continue
        if node.node_class not in hazus:
            notes.add(f"{node.node_class}: no Hazus restoration row; no permanent repair")
            continue
        # CHOICE: one draw per node serves every damage state, each at its own spread, so a
        # node slow to repair is slow at each.
        for state, work_h in crew_work.items():
            row = hazus[node.node_class][state]
            mean_h = float(row["mean"]) * HOURS_PER_DAY
            sd_h = float(row["sd"]) * HOURS_PER_DAY
            spread = rates.spread(mean_h, sd_h)
            repair_h = mean_h / rates.factor(spread, u)
            records.append(
                PermanentRepair(
                    node_id=node.node_id,
                    damage_state=state,
                    hazus_mean_h=mean_h,
                    hazus_sd_h=sd_h,
                    spread=spread,
                    repair_h=repair_h,
                    crew_work_h=float(work_h),
                    lead_time_h=max(0.0, repair_h - float(work_h)),
                )
            )
    return records, unrepairable


class _RateDraw:
    """The repair-rate draw: Hazus spread by default, the recipe's heterogeneity if set."""

    def __init__(self, levers: RepairRates, method: DrawMethod) -> None:
        self.override = levers.heterogeneity_pct
        self.gap = levers.compliance_gap_pct / 100.0
        self.method = method
        self._tables: dict[float, tuple[float, ...]] = {}

    def spread(self, mean_h: float, sd_h: float) -> float:
        """Return the rate spread (standard deviation / target) at one class and state."""
        if self.override is not None:
            return self.override / 100.0
        return sd_h / mean_h if mean_h > 0.0 else 0.0

    def factor(self, spread: float, u: float) -> float:
        """Draw the rate as a multiple of the Hazus rate: (1 - gap) x Q(u).

        CHOICE: the drawn quantity is the repair rate, so a positive gap slows repair (median
        time = Hazus mean / (1 - gap)). The reciprocal of a lognormal keeps its log spread, so
        the time takes the same spread as the rate.
        """
        levers = Levers(spread, self.gap)
        if levers.spread not in self._tables:
            self._tables[levers.spread] = self.method.mixture(levers.spread)
        return (1.0 - self.gap) * self.method.quantile(self._tables[levers.spread], u)


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
        "line_repair": [plain(line) for line in result.lines],
        "failure_point_travel": [plain(point) for point in result.failure_points],
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
            "mean_spread": _mean([p.spread for p in records]),
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
        "line_repair": _line_summary(result.lines),
        "notes": list(result.notes),
    }


def _line_summary(lines: tuple[LineRepair, ...]) -> dict[str, object]:
    travel = [line.travel_h for line in lines if line.travel_h is not None]
    return {
        "lines": len(lines),
        "crew_work_h_per_failure_point": sorted(
            {line.crew_work_h_per_failure_point for line in lines}
        ),
        "mean_travel_h": _mean(travel),
        "longest_travel_h": round(max(travel), 3) if travel else None,
    }


def _mean(values: list[float]) -> float | None:
    return round(math.fsum(values) / len(values), 3) if values else None
