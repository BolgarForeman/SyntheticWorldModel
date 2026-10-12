"""The rule-card drills: one tiny world on generic nodes per mechanic, played by the engine.

Each drill is a world of two to four generic nodes (A, B, C, D and a source S) built here by
hand, damaged at hour 0 and run by the same engine as the world. Its answer is one number read
from the run. The rule card prints the drill's expected answer from its text file; the build
compares the two and stops if the engine does not reproduce the printed answer (WO 9, H3).

Nothing here is the mission's world: the nodes are A, B, C and their classes only choose the
engine's rules (a substation needs manual switching, a transmission substation leads the crew
order).

Spec: Work Order 9, H3; Trace pack ruling sheet v0.2, P4.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from swm.dynamics.engine import simulate
from swm.dynamics.records import Run, RunRequest
from swm.dynamics.world import (
    CrewStart,
    Damage,
    EngineDependency,
    EngineEdge,
    EngineNode,
    EngineWorld,
    FacilityRepair,
    FailurePoint,
    Generator,
    IntraLink,
    Resupply,
    Stock,
    Tolerance,
    settings_from,
)
from swm.recipe.schema import LIFELINE_WEIGHTS, EndUseClass, Layer, NodeClass
from swm.rules.registry import Registry

M_PER_KM = 1000.0
DRAW_PER_H = 10.0
"""Any draw: a drill's stock is set in hours, so the draw only fixes the units."""


class DrillError(ValueError):
    """A printed drill answer the engine does not reproduce."""


@dataclass(frozen=True)
class _Node:
    node_id: str
    layer: Layer
    node_class: NodeClass
    km_east: float = 0.0
    km_north: float = 0.0
    end_use: bool = False


def _node(spec: _Node, source: bool, own_mode: str | None = None) -> EngineNode:
    site = (spec.km_east * M_PER_KM, spec.km_north * M_PER_KM)
    return EngineNode(
        spec.node_id,
        spec.layer,
        spec.node_class,
        site,
        source,
        own_mode,
        1.0 if spec.end_use else None,
    )


def _need(
    consumer: str,
    layer: Layer,
    feeds: Sequence[tuple[str, float, str]],
    mode: str,
    floor: float | None = None,
    tolerance: Tolerance | None = None,
) -> EngineDependency:
    """Return a dependency whose feed groups each hold one edge: (supplier, κ, form)."""
    groups = tuple((EngineEdge(f"E-{s}-{consumer}", s, k, f, None),) for s, k, f in feeds)
    return EngineDependency(
        f"D-{consumer}-{layer.value}", consumer, layer, groups, mode, floor, tolerance
    )


def _world(rules: Registry, nodes: Sequence[EngineNode], **parts: Any) -> EngineWorld:
    """Return a world of the given nodes with nothing else, then the parts a drill sets."""
    empty = EngineWorld(
        nodes=tuple(sorted(nodes, key=lambda n: n.node_id)),
        dependencies=(),
        links=(),
        stocks=(),
        generators=(),
        resupply=(),
        repairs=(),
        unrepairable=(),
        emergencies=(),
        units={},
        crews=(),
        feeds_to_end_use={},
        towered=frozenset(),
        settings=settings_from(rules),
    )
    return replace(empty, **parts)


def _run(
    world: EngineWorld,
    nodes: Sequence[str] = (),
    lines: Sequence[str] = (),
    points: Sequence[FailurePoint] = (),
) -> Run:
    return simulate(world, RunRequest(Damage(tuple(nodes), tuple(lines), tuple(points))))


def _first(run: Run, node_id: str, test: Callable[[float], bool], after: float = 0.0) -> float:
    """Return the first hour at or after ``after`` when the node's state passes the test."""
    for t, state in zip(run.times, run.state(node_id), strict=True):
        if t >= after and test(state):
            return t
    raise DrillError(f"{node_id} never reaches the drill's state")


def _completion(run: Run, element_id: str) -> float:
    """Return the exact hour a crew finishes an element's repair (the crew log, not the step)."""
    for _, log in run.crews:
        for entry in log:
            if entry.job_id == f"repair:{element_id}" and entry.activity == "repair":
                return entry.end_h
    raise DrillError(f"{element_id} is never repaired")


# --- The drills, one per card, as each card's drill world specifies -------------------------


def _source(node_id: str, layer: Layer, node_class: NodeClass, km_east: float = 0.0,
            km_north: float = 0.0) -> EngineNode:  # fmt: skip
    return _node(_Node(node_id, layer, node_class, km_east, km_north), True)


def _consumer(node_id: str, layer: Layer, node_class: NodeClass, km_east: float = 0.0,
              km_north: float = 0.0, weight: float | None = 1.0) -> EngineNode:  # fmt: skip
    site = (km_east * M_PER_KM, km_north * M_PER_KM)
    return EngineNode(node_id, layer, node_class, site, True, None, weight)


def _road_km(rules: Registry, hours: float) -> float:
    """Return the km a crew drives in so many hours (a drill's distance is set in hours)."""
    return hours * rules.number("crews.road_speed_kmh")


def _fixed_repair(rules: Registry, node_id: str, done_h: float) -> FacilityRepair:
    """Return a repair a crew already on site finishes at an exact hour: lead, then work."""
    lead = rules.number("repair.crew_bound_lead_h")
    return FacilityRepair(node_id, 0.0, done_h - lead)


def weakest_supply(rules: Registry) -> tuple[float, ...]:
    """Card 1: power in full, throttled; water at 0.85, tripping: B's level at hour 0."""
    world = _world(
        rules,
        [_source("A_power", Layer.POWER, NodeClass.GENERATION),
         _source("A_water", Layer.WATER, NodeClass.TREATMENT),
         _consumer("B", Layer.HEALTHCARE, NodeClass.CLINIC)],
        dependencies=(_need("B", Layer.POWER, [("A_power", 1.0, "linear")], "throttle"),
                      _need("B", Layer.WATER, [("A_water", 0.85, "linear")], "trip")),
    )  # fmt: skip
    return (_run(world).at("B", 0.0),)


def throttle_trip_floor(rules: Registry) -> tuple[float, ...]:
    """Card 2: C trips on power arriving at 92 %, then at 89 %: its level each time."""
    levels = []
    for kappa in (0.92, 0.89):
        world = _world(
            rules,
            [_source("A", Layer.POWER, NodeClass.GENERATION),
             _consumer("C", Layer.HEALTHCARE, NodeClass.CLINIC)],
            dependencies=(_need("C", Layer.POWER, [("A", kappa, "linear")], "trip"),),
        )  # fmt: skip
        levels.append(_run(world).at("C", 0.0))
    return tuple(levels)


def passing_supply(rules: Registry) -> tuple[float, ...]:
    """Card 3: A at 0.6, then 0.4, passes fuel to B on a threshold arrow: what B receives."""
    received = []
    for level in (0.6, 0.4):
        world = _world(
            rules,
            [_source("S", Layer.POWER, NodeClass.GENERATION),
             _consumer("A", Layer.FUEL, NodeClass.DEPOT, weight=None),
             _consumer("B", Layer.HEALTHCARE, NodeClass.CLINIC)],
            dependencies=(_need("A", Layer.POWER, [("S", level, "linear")], "throttle"),
                          _need("B", Layer.FUEL, [("A", 1.0, "threshold")], "throttle")),
        )  # fmt: skip
        received.append(_run(world).at("B", 0.0))
    return tuple(received)


def two_supplies(rules: Registry) -> tuple[float, ...]:
    """Card 4: B fed by lines from A1 and A2, A1's line down; a pump fed two-full, one lost."""
    substation = EngineNode("B", Layer.POWER, NodeClass.DISTRIBUTION_SUBSTATION, (2000.0, 0.0),
                            False, "trip", None)  # fmt: skip
    own = _world(
        rules,
        [_source("A1", Layer.POWER, NodeClass.GENERATION),
         _source("A2", Layer.POWER, NodeClass.GENERATION, 4.0), substation],
        links=(IntraLink("A1-B", "A1", "B", True), IntraLink("A2-B", "A2", "B", True)),
    )  # fmt: skip
    point = FailurePoint("A1-B", 1.0, (1000.0, 0.0), rules.number("storm.line_crew_work_h"))
    first = _run(own, lines=("A1-B",), points=(point,)).at("B", 0.0)
    pump = _world(
        rules,
        [_source("S1", Layer.POWER, NodeClass.DISTRIBUTION_SUBSTATION),
         _source("S2", Layer.POWER, NodeClass.DISTRIBUTION_SUBSTATION, 1.0),
         _consumer("P", Layer.WATER, NodeClass.PUMPING, weight=None)],
        dependencies=(_need("P", Layer.POWER, [("S1", 1.0, "linear"), ("S2", 1.0, "linear")],
                            "throttle"),),
    )  # fmt: skip
    return first, _run(pump, nodes=("S1",)).at("P", 0.0)


def telecom_fallback(rules: Registry) -> tuple[float, ...]:
    """Card 5: B loses telecom at hour 0 (T 12 h, d 0.9, κ 1), back at hour 20: hours 6, 15, 21."""
    world = _world(
        rules,
        [_source("T", Layer.TELECOM, NodeClass.EXCHANGE),
         _consumer("B", Layer.HEALTHCARE, NodeClass.CLINIC)],
        dependencies=(_need("B", Layer.TELECOM, [("T", 1.0, "linear")], "throttle",
                            tolerance=Tolerance("tolerance.clinic", 12.0, 0.9)),),
        repairs=(_fixed_repair(rules, "T", 20.0),),
        crews=(CrewStart("crew 1", (0.0, 0.0)),),
    )  # fmt: skip
    run = _run(world, nodes=("T",))
    return run.at("B", 6.0), run.at("B", 15.0), run.at("B", 21.0)


def stocks(rules: Registry) -> tuple[float, ...]:
    """Card 6: B (trips) holds a 4 h battery; power lost 0-3 h: the hour the battery is full."""
    battery = Stock("B:battery", "B", "battery", Layer.POWER, 4.0 * DRAW_PER_H, DRAW_PER_H,
                    "battery", "reserves.exchange.battery_h")  # fmt: skip
    world = _world(
        rules,
        [_source("A", Layer.POWER, NodeClass.GENERATION),
         _consumer("B", Layer.TELECOM, NodeClass.EXCHANGE)],
        dependencies=(_need("B", Layer.POWER, [("A", 1.0, "linear")], "trip"),),
        stocks=(battery,), repairs=(_fixed_repair(rules, "A", 3.0),),
        crews=(CrewStart("crew 1", (0.0, 0.0)),),
    )  # fmt: skip
    run = _run(world, nodes=("A",))
    if min(run.state("B")) < 1.0:
        raise DrillError("the stocks drill prints that B never goes out; in the engine it does")
    full = next(t for t, level in zip(run.times, run.level("B:battery"), strict=True)
                if t > 0.0 and level >= battery.capacity)  # fmt: skip
    return (full,)


def fuel_deliveries(rules: Registry) -> tuple[float, ...]:
    """Card 7: B's generator holds 10 h; power stays off; depot D delivers: out from, back at."""
    tank = Stock("B:generator_fuel", "B", "generator_fuel", Layer.POWER, 10.0 * DRAW_PER_H,
                 DRAW_PER_H, "delivery", "reserves.hospital.generator_fuel_h", True)  # fmt: skip
    delivery = rules.number("reserves.fuel_resupply.delivery_h") * DRAW_PER_H
    world = _world(
        rules,
        [_source("A", Layer.POWER, NodeClass.GENERATION),
         _source("D", Layer.FUEL, NodeClass.DEPOT, 2.0),
         _consumer("B", Layer.HEALTHCARE, NodeClass.CLINIC)],
        dependencies=(_need("B", Layer.POWER, [("A", 1.0, "linear")], "trip"),),
        stocks=(tank,), generators=(Generator("B", False, 1.0e6),),
        resupply=(Resupply("R-1", "D", "B", tank.stock_id, delivery, 1.0, "threshold"),),
    )  # fmt: skip
    run = _run(world, nodes=("A",))
    out = _first(run, "B", lambda s: s < 1.0)
    return out, _first(run, "B", lambda s: s == 1.0, after=out)


def crew_sequence(rules: Registry) -> tuple[float, ...]:
    """Card 8: a crew 1 h from F; parts in at 5 h; 8 h of work: the hour the work is done."""
    world = _world(
        rules,
        [_source("A", Layer.POWER, NodeClass.GENERATION),
         _consumer("F", Layer.HEALTHCARE, NodeClass.CLINIC, _road_km(rules, 1.0))],
        repairs=(FacilityRepair("F", 5.0, 8.0),), crews=(CrewStart("crew 1", (0.0, 0.0)),),
    )  # fmt: skip
    return (_completion(_run(world, nodes=("F",)), "F"),)


def first_jobs(rules: Registry) -> dict[str, str]:
    """Card 9's world: two crews at the base, three jobs: each crew's first job."""
    weight = LIFELINE_WEIGHTS[EndUseClass.DISTRIBUTION_SUBSTATION]
    world = _world(
        rules,
        [_source("A", Layer.POWER, NodeClass.GENERATION),
         _consumer("P", Layer.WATER, NodeClass.PUMPING, _road_km(rules, 1.0), weight=None),
         _consumer("S_h", Layer.POWER, NodeClass.DISTRIBUTION_SUBSTATION, _road_km(rules, 3.0),
                   weight=weight),
         _consumer("S_c", Layer.POWER, NodeClass.DISTRIBUTION_SUBSTATION, _road_km(rules, 2.0),
                   weight=weight)],
        repairs=tuple(FacilityRepair(n, 0.0, 4.0) for n in ("P", "S_c", "S_h")),
        crews=(CrewStart("crew 1", (0.0, 0.0)), CrewStart("crew 2", (0.0, 0.0))),
    )  # fmt: skip
    run = _run(world, nodes=("P", "S_h", "S_c"))
    return {crew: log[0].job_id.removeprefix("repair:") for crew, log in run.crews}


def crew_order(rules: Registry) -> tuple[float, ...]:
    """Card 9: the two crews' first jobs are the two distribution substations, not the pump."""
    first = first_jobs(rules)
    if set(first.values()) != {"S_h", "S_c"}:
        raise DrillError(
            f"the crew-order drill expects S_h and S_c first; the engine gives {first}"
        )
    return ()


def travel_between_jobs(rules: Registry) -> tuple[float, ...]:
    """Card 10: no printed answer yet; ``travel_case`` shows the engine's rule for the report."""
    del rules
    return ()


def travel_case(rules: Registry) -> float:
    """One crew; B (8 km east) and C (8 km east, 6 km north) need 1 h each: C's work done.

    The engine times the second trip from B, where the crew stands: 0.15 h for 6 km.
    """
    world = _world(
        rules,
        [_source("A", Layer.POWER, NodeClass.GENERATION),
         _consumer("B", Layer.HEALTHCARE, NodeClass.CLINIC, 8.0),
         _consumer("C", Layer.HEALTHCARE, NodeClass.CLINIC, 8.0, 6.0)],
        repairs=(FacilityRepair("B", 0.0, 1.0), FacilityRepair("C", 0.0, 1.0)),
        crews=(CrewStart("crew 1", (0.0, 0.0)),),
    )  # fmt: skip
    return _completion(_run(world, nodes=("B", "C")), "C")


def manual_switching(rules: Registry) -> tuple[float, ...]:
    """Card 11: line L into S repaired at hour 20: S back with telecom up; and with it down."""
    back = []
    for telecom_down in (False, True):
        substation = EngineNode("S", Layer.POWER, NodeClass.DISTRIBUTION_SUBSTATION,
                                (10000.0, 0.0), False, "trip", None)  # fmt: skip
        row = rules.value("tolerance.substation")
        world = _world(
            rules,
            [_source("A", Layer.POWER, NodeClass.GENERATION),
             _source("T", Layer.TELECOM, NodeClass.EXCHANGE, 10.0, 1.0), substation],
            dependencies=(_need("S", Layer.TELECOM, [("T", 1.0, "threshold")], "throttle",
                                tolerance=Tolerance("tolerance.substation", float(row["t_h"]),
                                                    float(row["d"]))),),
            links=(IntraLink("L", "A", "S", True),),
            crews=(CrewStart("crew 1", (5000.0, 0.0)),
                   CrewStart("crew 2", (10000.0 + _road_km(rules, 1.0) * M_PER_KM, 0.0))),
        )  # fmt: skip
        work = 20.0 - rules.number("repair.crew_bound_lead_h")
        point = FailurePoint("L", 5.0, (5000.0, 0.0), work)
        run = _run(world, nodes=("T",) if telecom_down else (), lines=("L",), points=(point,))
        out = _first(run, "S", lambda s: s < 1.0)
        back.append(_first(run, "S", lambda s: s == 1.0, after=out))
    return tuple(back)


def time_and_scoring(rules: Registry) -> tuple[float, ...]:
    """Card 12: out (0) 0-6 h, then at 0.5 until hour 10: the hours out."""
    world = _world(
        rules,
        [_source("A1", Layer.POWER, NodeClass.GENERATION),
         _source("A2", Layer.POWER, NodeClass.GENERATION, 1.0),
         _consumer("B", Layer.HEALTHCARE, NodeClass.CLINIC, 0.5, 5.0)],
        dependencies=(_need("B", Layer.POWER, [("A1", 0.5, "linear"), ("A2", 0.5, "linear")],
                            "throttle"),),
        repairs=(_fixed_repair(rules, "A1", 6.0), _fixed_repair(rules, "A2", 10.0)),
        crews=(CrewStart("crew 1", (0.0, 0.0)), CrewStart("crew 2", (1000.0, 0.0))),
    )  # fmt: skip
    return (_run(world, nodes=("A1", "A2")).hours_out["B"],)


DRILLS: Mapping[str, Callable[[Registry], tuple[float, ...]]] = {
    "weakest_supply": weakest_supply,
    "throttle_trip_floor": throttle_trip_floor,
    "passing_supply": passing_supply,
    "two_supplies": two_supplies,
    "telecom_fallback": telecom_fallback,
    "stocks": stocks,
    "fuel_deliveries": fuel_deliveries,
    "crew_sequence": crew_sequence,
    "crew_order": crew_order,
    "travel_between_jobs": travel_between_jobs,
    "manual_switching": manual_switching,
    "time_and_scoring": time_and_scoring,
}
"""Each rule card's drill world, by the card's name: the numbers the engine gives, in the order
the card's answer prints them."""


def verify(card: str, expected: Sequence[float], rules: Registry) -> tuple[float, ...]:
    """Run a card's drill and return the engine's numbers; stop if they are not the printed ones.

    Parameters
    ----------
    card : str
        The rule card's name.
    expected : sequence of float
        The numbers the card's answer prints, in order.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    tuple of float
        The engine's numbers.

    Raises
    ------
    DrillError
        If the engine's numbers differ from the printed ones.

    Spec: Work Order 9, H3.
    """
    answer = DRILLS[card](rules)
    printed = tuple(expected)
    if len(answer) != len(printed) or any(
        abs(a - e) > TOLERANCE_H for a, e in zip(answer, printed, strict=True)
    ):
        shown = ", ".join(f"{v:g}" for v in printed)
        given = ", ".join(f"{v:g}" for v in answer)
        raise DrillError(f"the {card} drill prints {shown}; the engine gives {given}")
    return answer


TOLERANCE_H = 1e-9
"""A printed answer must equal the engine's (floating-point noise aside)."""
