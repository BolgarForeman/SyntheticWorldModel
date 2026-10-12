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
from swm.recipe.schema import Layer, NodeClass
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


# --- The drills, in the order of the ruling sheet -------------------------------------------

POWER_SOURCE = _Node("A", Layer.POWER, NodeClass.GENERATION)
WATER_SOURCE = _Node("B", Layer.WATER, NodeClass.TREATMENT)
CLINIC = _Node("C", Layer.HEALTHCARE, NodeClass.CLINIC, end_use=True)


def weakest_supply(rules: Registry) -> float:
    """C takes 60 % of its power and 80 % of its water and throttles: its state at hour 0."""
    world = _world(
        rules,
        [_node(POWER_SOURCE, True), _node(WATER_SOURCE, True), _node(CLINIC, True)],
        dependencies=(
            _need("C", Layer.POWER, [("A", 0.6, "linear")], "throttle"),
            _need("C", Layer.WATER, [("B", 0.8, "linear")], "throttle"),
        ),
    )
    return _run(world).at("C", 0.0)


def responses(rules: Registry) -> float:
    """C takes 60 % of its power and trips: its state at hour 0."""
    world = _world(
        rules,
        [_node(POWER_SOURCE, True), _node(CLINIC, True)],
        dependencies=(_need("C", Layer.POWER, [("A", 0.6, "linear")], "trip"),),
    )
    return _run(world).at("C", 0.0)


def partial_supply(rules: Registry) -> float:
    """B runs at 40 % and passes to C on a threshold edge: C's state at hour 0."""
    middle = _Node("B", Layer.TELECOM, NodeClass.EXCHANGE)
    world = _world(
        rules,
        [_node(POWER_SOURCE, True), _node(middle, True), _node(CLINIC, True)],
        dependencies=(
            _need("B", Layer.POWER, [("A", 0.4, "linear")], "throttle"),
            _need("C", Layer.TELECOM, [("B", 1.0, "threshold")], "throttle"),
        ),
    )
    return _run(world).at("C", 0.0)


def two_feeds(rules: Registry) -> float:
    """C has two power feeds of half each; A is damaged: C's state at hour 0."""
    second = _Node("B", Layer.POWER, NodeClass.GENERATION, km_east=1.0)
    world = _world(
        rules,
        [_node(POWER_SOURCE, True), _node(second, True), _node(CLINIC, True)],
        dependencies=(
            _need("C", Layer.POWER, [("A", 0.5, "linear"), ("B", 0.5, "linear")], "throttle"),
        ),
    )
    return _run(world, nodes=("A",)).at("C", 0.0)


def telecom_fallback(rules: Registry) -> float:
    """C loses telecom at hour 0 and falls back: its state at hour 30."""
    exchange = _Node("A", Layer.TELECOM, NodeClass.EXCHANGE)
    row = rules.value("tolerance.clinic")
    tolerance = Tolerance("tolerance.clinic", float(row["t_h"]), float(row["d"]))
    world = _world(
        rules,
        [_node(exchange, True), _node(CLINIC, True)],
        dependencies=(
            _need("C", Layer.TELECOM, [("A", 1.0, "threshold")], "throttle", tolerance=tolerance),
        ),
    )
    return _run(world, nodes=("A",)).at("C", 30.0)


def stocks(rules: Registry) -> float:
    """C trips without power but holds 3 h of battery; A is damaged: the hour C goes out."""
    exchange = _Node("C", Layer.TELECOM, NodeClass.EXCHANGE, end_use=True)
    battery = Stock(
        "C:battery",
        "C",
        "battery",
        Layer.POWER,
        3.0 * DRAW_PER_H,
        DRAW_PER_H,
        "battery",
        "reserves.exchange.battery_h",
    )
    world = _world(
        rules,
        [_node(POWER_SOURCE, True), _node(exchange, True)],
        dependencies=(_need("C", Layer.POWER, [("A", 1.0, "linear")], "trip"),),
        stocks=(battery,),
    )
    return _first(_run(world, nodes=("A",)), "C", lambda s: s < 1.0)


def deliveries(rules: Registry) -> float:
    """C runs on a generator with 6 h of fuel and a depot D delivers: the hour C comes back."""
    depot = _Node("D", Layer.FUEL, NodeClass.DEPOT, km_east=2.0)
    tank = Stock(
        "C:generator_fuel",
        "C",
        "generator_fuel",
        Layer.POWER,
        6.0 * DRAW_PER_H,
        DRAW_PER_H,
        "delivery",
        "reserves.hospital.generator_fuel_h",
        True,
    )
    delivery = rules.number("reserves.fuel_resupply.delivery_h") * DRAW_PER_H
    world = _world(
        rules,
        [_node(POWER_SOURCE, True), _node(depot, True), _node(CLINIC, True)],
        dependencies=(_need("C", Layer.POWER, [("A", 1.0, "linear")], "trip"),),
        stocks=(tank,),
        generators=(Generator("C", False, 1.0e6),),
        resupply=(Resupply("R-1", "D", "C", tank.stock_id, delivery, 1.0, "threshold"),),
    )
    run = _run(world, nodes=("A",))
    out = _first(run, "C", lambda s: s < 1.0)
    return _first(run, "C", lambda s: s == 1.0, after=out)


def _crew_world(
    rules: Registry, nodes: Sequence[_Node], repairs: Mapping[str, float], **parts: object
) -> EngineWorld:
    """Return a world of a source and the given nodes, one crew at the base (0 km, 0 km)."""
    return _world(
        rules,
        [_node(POWER_SOURCE, True), *(_node(n, True) for n in nodes)],
        repairs=tuple(FacilityRepair(n, 0.0, work) for n, work in sorted(repairs.items())),
        crews=(CrewStart("crew 1", (0.0, 0.0)),),
        **parts,
    )


def crew_sequence(rules: Registry) -> float:
    """One crew repairs C, 8 km away, with 3 h of work: the hour the work is done."""
    world = _crew_world(rules, [_Node("C", Layer.HEALTHCARE, NodeClass.CLINIC, 8.0)], {"C": 3.0})
    return _completion(_run(world, nodes=("C",)), "C")


def crew_priority(rules: Registry) -> float:
    """Return the hour C's repair is done: B (a transmission substation, 20 km) goes first.

    B and C (a clinic, 4 km) are damaged; one crew.
    """
    substation = _Node("B", Layer.POWER, NodeClass.TRANSMISSION_SUBSTATION, 20.0)
    clinic = _Node("C", Layer.HEALTHCARE, NodeClass.CLINIC, 4.0)
    world = _crew_world(rules, [substation, clinic], {"B": 2.0, "C": 2.0})
    return _completion(_run(world, nodes=("B", "C")), "C")


def travel_between_jobs(rules: Registry) -> float:
    """B (8 km east) and C (8 km east, 6 km north) need 1 h each; one crew: C's repair done."""
    first = _Node("B", Layer.HEALTHCARE, NodeClass.CLINIC, 8.0)
    second = _Node("C", Layer.HEALTHCARE, NodeClass.CLINIC, 8.0, 6.0)
    world = _crew_world(rules, [first, second], {"B": 1.0, "C": 1.0})
    return _completion(_run(world, nodes=("B", "C")), "C")


def manual_switching(rules: Registry) -> float:
    """Return the hour B is back on: line A-B is down, B's telecom is lost for good.

    The line fails 5 km from A; B is a substation, so a crew must switch it by hand.
    """
    substation = _Node("B", Layer.POWER, NodeClass.DISTRIBUTION_SUBSTATION, 10.0)
    exchange = _Node("T", Layer.TELECOM, NodeClass.EXCHANGE, 0.0, 3.0)
    row = rules.value("tolerance.substation")
    tolerance = Tolerance("tolerance.substation", float(row["t_h"]), float(row["d"]))
    world = _world(
        rules,
        [_node(POWER_SOURCE, True), _node(exchange, True), _node(substation, False, "trip")],
        dependencies=(
            _need("B", Layer.TELECOM, [("T", 1.0, "threshold")], "throttle", tolerance=tolerance),
        ),
        links=(IntraLink("A-B", "A", "B", True),),
        crews=(CrewStart("crew 1", (0.0, 0.0)),),
    )
    work = rules.number("storm.line_crew_work_h")
    point = FailurePoint("A-B", 5.0, (5.0 * M_PER_KM, 0.0), work)
    run = _run(world, nodes=("T",), lines=("A-B",), points=(point,))
    out = _first(run, "B", lambda s: s < 1.0)
    return _first(run, "B", lambda s: s == 1.0, after=out)


def time_steps(rules: Registry) -> float:
    """Return the step at which C is back on, its work done at the crew-sequence drill's hour."""
    world = _crew_world(rules, [_Node("C", Layer.HEALTHCARE, NodeClass.CLINIC, 8.0)], {"C": 3.0})
    run = _run(world, nodes=("C",))
    return _first(run, "C", lambda s: s == 1.0, after=run.step_h)


DRILLS: Mapping[str, Callable[[Registry], float]] = {
    "weakest_supply": weakest_supply,
    "responses": responses,
    "partial_supply": partial_supply,
    "two_feeds": two_feeds,
    "telecom_fallback": telecom_fallback,
    "stocks": stocks,
    "deliveries": deliveries,
    "crew_sequence": crew_sequence,
    "crew_priority": crew_priority,
    "travel_between_jobs": travel_between_jobs,
    "manual_switching": manual_switching,
    "time_steps": time_steps,
}
"""Each rule card's drill, by the card's name: the engine's answer to it."""


def verify(card: str, expected: float, rules: Registry) -> float:
    """Run a card's drill and return the engine's answer; stop if it is not the printed one.

    Parameters
    ----------
    card : str
        The rule card's name.
    expected : float
        The answer the card prints.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    float
        The engine's answer.

    Raises
    ------
    DrillError
        If the engine's answer differs from the printed one.

    Spec: Work Order 9, H3.
    """
    answer = DRILLS[card](rules)
    if abs(answer - expected) > TOLERANCE_H:
        raise DrillError(f"the {card} drill prints {expected:g}; the engine gives {answer:g}")
    return answer


TOLERANCE_H = 1e-9
"""A printed answer must equal the engine's (floating-point noise aside)."""
