"""What the game's pages say, as plain data: node cards, briefing, sheets and the sealed answer.

Every number is read from the world the engine plays out, the scenario's damage or the
registry (WO 9, H10). The game's pages never read the reference run; only ``answer_*`` does,
for the sealed answer (H8).

Spec: Work Order 9, H2 and H5-H8; Trace pack ruling sheet v0.2, P3, P6 and P7.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from swm.dynamics.records import Run
from swm.dynamics.world import SUBSTATIONS, EngineDependency, EngineWorld
from swm.recipe.schema import Layer
from swm.rules.registry import Registry
from swm.trace_pack import TraceInputs, damage_facility_rows, damage_line_rows, travel_rows

TRIP, THROTTLE, FLOOR, FALLBACK, STOCK = "⚡", "◐", "▁", "◷", "▮"
"""The card symbols (ruling P3). CHOICE: fallback is ◷, a clock face: the bundled font (DejaVu)
has no ⏳ and no other hourglass, and a missing glyph would print as a box."""
SYMBOL = {"trip": TRIP, "throttle": THROTTLE, "step_to_floor": FLOOR}
LEGEND = (
    (TRIP, "trip: runs fully while the supply received is at least the trip point, else stops"),
    (THROTTLE, "throttle: runs at the share of the supply it receives"),
    (FLOOR, "floor: on its generator, steps down to the floor share"),
    (FALLBACK, "fallback: full for T hours after telecom is lost, then d_eff"),
    (STOCK, "stock: covers its own supply for the hours shown, then runs out"),
)


@dataclass(frozen=True)
class NodeCard:
    """One node's card: header, needs, back-up and supplies, each a list of lines."""

    node_id: str
    header: tuple[str, ...]
    needs: tuple[str, ...]
    backup: tuple[str, ...]
    supplies: tuple[str, ...]


def short(node_id: str) -> str:
    """Return a world id as the game prints it, without the world's prefix."""
    return node_id.removeprefix("SWM-")


def number(value: float) -> str:
    """Return a number as a card prints it: at most three decimals, no trailing zeros."""
    return f"{round(value, 3):g}"


# --- Node cards (H2) ------------------------------------------------------------------------


def node_cards(inputs: TraceInputs) -> tuple[NodeCard, ...]:
    """Return one card per node, in id order; no damage and no scenario content (ruling P3).

    Parameters
    ----------
    inputs : TraceInputs
        The world's stages and the engine's world.

    Returns
    -------
    tuple of NodeCard
        The cards.

    Spec: Work Order 9, H2.
    """
    world = inputs.world
    switched_on = {e.edge_id for e in inputs.couplings.edges if e.switched_on}
    rules = inputs.rules
    cards = []
    for node in world.nodes:
        weight = (f"end use, weight {number(node.end_use_weight)}"
                  if node.end_use_weight is not None else "not an end use")  # fmt: skip
        header = (short(node.node_id), node.node_class.value.replace("_", " "), weight)
        cards.append(NodeCard(
            node.node_id, header, _needs(world, node.node_id, switched_on),
            _backup(world, node.node_id, rules), _supplies(inputs, node.node_id, switched_on),
        ))  # fmt: skip
    return tuple(cards)


def _needs(world: EngineWorld, node_id: str, switched_on: set[str]) -> tuple[str, ...]:
    node = world.node(node_id)
    lines: list[str] = []
    if not node.source and node.own_mode is not None:
        upstream = sorted({short(link.upstream_id) for link in world.links
                           if link.downstream_id == node_id})  # fmt: skip
        lines.append(f"{SYMBOL[node.own_mode]} {node.layer.value} (own network): best of")
        lines.append("   " + ", ".join(upstream))
    for dependency in world.dependencies:
        if dependency.consumer_id == node_id:
            lines += _need_lines(dependency, switched_on)
    return tuple(lines) or ("nothing",)


def _need_lines(dependency: EngineDependency, switched_on: set[str]) -> list[str]:
    floor = "" if dependency.floor is None else f" to {number(dependency.floor)}"
    lines = [f"{SYMBOL[dependency.mode]}{floor} {dependency.supplier_layer.value}:"]
    feeds = len(dependency.groups)
    for group in dependency.groups:
        for edge in group:
            # A hidden coupling is real and the engine plays it, but no source shows it.
            hidden = "" if edge.edge_id in switched_on else " (hidden)"
            kappa = "" if dependency.supplier_layer == Layer.TELECOM else f" κ {number(edge.kappa)}"
            lines.append(f"   {short(edge.supplier_id)}{kappa} {edge.transfer_form}{hidden}")
    if feeds > 1:
        lines.append(f"   ({feeds} feeds add, max 1)")
    return lines


def _backup(world: EngineWorld, node_id: str, rules: Registry) -> tuple[str, ...]:
    lines: list[str] = []
    for stock in world.stocks:
        if stock.node_id != node_id:
            continue
        hours = stock.capacity / stock.draw_per_h if stock.draw_per_h > 0.0 else math.inf
        refill = {"none": "no refill", "delivery": "refill by delivery"}.get(
            stock.refill, f"refill: {stock.refill}"
        )
        lines.append(f"{STOCK} {stock.kind.replace('_', ' ')}: {number(hours)} h")
        lines.append(f"   covers {stock.covers.value}; {refill}")
    for generator in world.generators:
        if generator.node_id == node_id:
            runs = f"stops after {number(generator.run_hours_to_failure)} h"
            lines.append("   generator " + ("fails to start" if generator.fails_to_start else runs))
    for dependency in world.dependencies:
        tolerance = dependency.tolerance
        if dependency.consumer_id == node_id and tolerance is not None:
            lines.append(f"{FALLBACK} telecom: full {number(tolerance.t_h)} h, then "
                         f"{number(tolerance.d_eff)}")  # fmt: skip
            if tolerance.ramp_to_h is not None:
                lines.append(f"   falling evenly until hour {number(tolerance.ramp_to_h)}")
    node = world.node(node_id)
    telecom = any(d.consumer_id == node_id and d.supplier_layer == Layer.TELECOM
                  for d in world.dependencies)  # fmt: skip
    if node.node_class in SUBSTATIONS and telecom:
        lines.append(f"manual switching if telecom is down: "
                     f"{number(rules.number('repair.manual_switching_h'))} h on site")  # fmt: skip
    return tuple(lines) or ("none",)


def _supplies(inputs: TraceInputs, node_id: str, switched_on: set[str]) -> tuple[str, ...]:
    """Return the nodes this node supplies: switched-on couplings and its network's links."""
    consumers = {e.consumer_id for e in inputs.couplings.edges
                 if e.supplier_id == node_id and e.edge_id in switched_on}  # fmt: skip
    consumers |= {link.downstream_id for link in inputs.world.links
                  if link.upstream_id == node_id}  # fmt: skip
    names = sorted(short(c) for c in consumers)
    return tuple(", ".join(names[i : i + 3]) for i in range(0, len(names), 3)) or ("none",)


# --- Briefing (H5) --------------------------------------------------------------------------


def briefing(inputs: TraceInputs) -> dict[str, object]:
    """Return the mission briefing: the storm, what failed, the crews and the horizon (H5).

    It states what failed, never what it causes.

    Parameters
    ----------
    inputs : TraceInputs
        The world, the scenario's storm and damage, and the registry.

    Returns
    -------
    dict
        ``storm``, ``lines`` (failure points), ``line_ends`` (each failed line's ends and
        structure), ``facilities``, ``crews``, ``base`` and ``horizon_h``.

    Spec: Work Order 9, H5.
    """
    track = inputs.field.track
    storm = ("No storm track crosses this scenario." if track is None else
             f"Closest approach {number(track.closest_approach_km)} km; peak wind "
             f"{number(track.peak_wind_m_per_s)} m/s; radius of maximum wind "
             f"{number(track.radius_max_wind_km)} km.")  # fmt: skip
    crews = [c.crew_id for c in inputs.world.crews]
    return {
        "storm": storm,
        "lines": damage_line_rows(inputs),
        "line_ends": {
            line.line_id: (line.from_id, line.to_id, line.structure.value)
            for line in inputs.lines
            if line.line_id in inputs.engine_damage.lines
        },
        "facilities": damage_facility_rows(inputs),
        "crews": len(crews),
        "base": sorted({c.base_id for c in inputs.crews.crews}),
        "horizon_h": inputs.rules.number("dynamics.horizon_h"),
    }


def travel_hours(inputs: TraceInputs) -> dict[str, float]:
    """Return each node's travel hours from the crew base (the board's map side)."""
    return {str(row["node"]): float(str(row["travel_h_from_base"])) for row in travel_rows(inputs)}


# --- Sheets and tokens (H6, H7) -------------------------------------------------------------


def outage_rows(world: EngineWorld) -> list[tuple[str, float]]:
    """Return every end-use node with its Lifeline weight, for the outage sheet (H6)."""
    return [(n.node_id, n.end_use_weight) for n in world.nodes if n.end_use_weight is not None]


SHEETS: Mapping[str, tuple[str, ...]] = {
    "Crew sheet": ("Time (h)", "Crew", "Job", "Doing", "Until (h)"),
    "Event log": ("Exact time (h)", "Step (h)", "Event", "What changes"),
    "Outage sheet": (
        "Node",
        "Weight",
        "Out at (h)",
        "Back at (h)",
        "State while out",
        "Hours x (1 - state)",
        "Weight x that",
    ),
    "Decision log": ("Time (h)", "Decision", "Why", "Card or rule used"),
    "Play-test feedback": ("Time (h)", "Question or stall", "Card or page"),
}
"""Each log sheet's columns (H6; the feedback sheet, ruling P10)."""


def tokens(inputs: TraceInputs) -> dict[str, int]:
    """Return how many of each token the sheet carries (H7)."""
    lines = len(inputs.lines)
    return {
        "damage marker": lines + len(inputs.world.nodes) // 4,
        "crew pawn": len(inputs.world.crews),
        "out marker": len(outage_rows(inputs.world)),
        "clock": 1,
        "stock clock": len(inputs.world.stocks),
    }


# --- The sealed answer (H8) -----------------------------------------------------------------


def step_of(hour: float, step_h: float) -> float:
    """Return the step at which an event at an exact hour takes effect: the first at or after."""
    steps = math.floor(hour / step_h + STEP_SLACK)
    if steps * step_h < hour - STEP_SLACK:
        steps += 1
    return steps * step_h


STEP_SLACK = 1e-9
"""Floating-point noise allowed when an exact hour falls on a step."""

ACTIVITY = {
    "travel": "arrives for",
    "assess": "finishes preparing",
    "wait for parts": "has parts for",
    "repair": "finishes the work on",
    "switch": "finishes switching",
}


def answer_events(run: Run) -> list[dict[str, object]]:
    """Return the engine's events, one per line: exact time, the step it takes effect, what.

    Parameters
    ----------
    run : Run
        The reference run.

    Returns
    -------
    list of dict
        ``exact_h``, ``step_h`` and ``event``, sorted by step, exact time and text.

    Spec: Work Order 9, H8.
    """
    events: list[tuple[float, float, str]] = []
    for crew, log in run.crews:
        for entry in log:
            job = short(entry.job_id.removeprefix("repair:"))
            if entry.activity == "travel":
                events.append((entry.start_h, entry.start_h, f"{crew} sets out for {job}"))
            doing = ACTIVITY.get(entry.activity, entry.activity)
            events.append((entry.end_h, entry.end_h, f"{crew} {doing} {job}"))
    for completion in run.completions:
        events.append((completion.time_h, completion.time_h,
                       f"{short(completion.element_id)} back in service"))  # fmt: skip
    for delivery in run.deliveries:
        events.append((delivery.time_h, delivery.time_h,
                       f"fuel delivery to {short(delivery.consumer_id)}"))  # fmt: skip
    events += _stock_events(run) + _state_events(run)
    kept = sorted((step_of(exact, run.step_h), round(exact, 6), text)
                  for exact, _, text in events if exact <= run.horizon_h)  # fmt: skip
    return [{"exact_h": exact, "step_h": step, "event": text} for step, exact, text in kept]


def _stock_events(run: Run) -> list[tuple[float, float, str]]:
    events = []
    for column, stock_id in enumerate(run.stock_ids):
        for index in range(1, len(run.times)):
            before, now = run.levels[index - 1][column], run.levels[index][column]
            if before > 0.0 and now <= 0.0:
                t = run.times[index]
                events.append((t, t, f"stock {short(stock_id)} runs out"))
    return events


def _state_events(run: Run) -> list[tuple[float, float, str]]:
    events = []
    for column, node_id in enumerate(run.node_ids):
        for index in range(len(run.times)):
            now = run.states[index][column]
            before = 1.0 if index == 0 else run.states[index - 1][column]
            if now != before:
                t = run.times[index]
                events.append((t, t, f"{short(node_id)} state {number(before)} -> {number(now)}"))
    return events


def answer_outages(run: Run, world: EngineWorld) -> list[dict[str, object]]:
    """Return each end-use node's outage intervals and its hours out (H8)."""
    rows = []
    for node_id, weight in outage_rows(world):
        intervals = _intervals(run, node_id)
        rows.append({
            "node": short(node_id),
            "weight": weight,
            "out_intervals_h": "; ".join(f"{number(a)}-{number(b)}" for a, b in intervals),
            "hours_out": round(run.hours_out[node_id], 6),
            "weighted_hours": round(weight * run.hours_out[node_id], 6),
        })  # fmt: skip
    return rows


def _intervals(run: Run, node_id: str) -> list[tuple[float, float]]:
    states = run.state(node_id)
    intervals: list[tuple[float, float]] = []
    start: float | None = None
    for t, state in zip(run.times, states, strict=True):
        if state < 1.0 and start is None:
            start = t
        elif state >= 1.0 and start is not None:
            intervals.append((start, t))
            start = None
    if start is not None:
        intervals.append((start, run.horizon_h))
    return intervals


def answer_score(run: Run, world: EngineWorld) -> dict[str, float]:
    """Return the score: weighted service-hours lost (Lifeline), and unweighted hours out (P7)."""
    weights = dict(outage_rows(world))
    return {
        "weighted_service_hours_lost": round(
            math.fsum(weights[n] * h for n, h in run.hours_out.items()), 6),
        "hours_out": round(math.fsum(run.hours_out.values()), 6),
    }  # fmt: skip


def end_use_ids(world: EngineWorld) -> Sequence[str]:
    """Return the end-use node ids, in id order."""
    return [node_id for node_id, _ in outage_rows(world)]
