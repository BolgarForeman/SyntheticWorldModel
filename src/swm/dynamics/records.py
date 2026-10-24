"""What a run is asked to do, and what it records (structure v0.9 §4.5; Work Order 7, E2).

A run records every node's state and every stock's level at every step, every crew's position
and job, every repair completion and delivery, the passes each step took, and the unweighted
hours out per end-use node, counted as a fraction when supply is partial.

Spec: structure v0.9 §4.5 (saved reference runs); Work Order 7, D1 and E2.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from swm.dynamics.world import Damage
from swm.recipe.schema import Layer


@dataclass(frozen=True)
class Protect:
    """Protect an element: it starts the run undamaged (the fortification convention)."""

    element_id: str


@dataclass(frozen=True)
class AddReserve:
    """Add hours of reserve to a stock, at its draw."""

    stock_id: str
    hours: float


@dataclass(frozen=True)
class AddStock:
    """Give a node a new stock on one commodity it has none for (Work Order 10, E2).

    The stock is counted in hours of the node's full draw: it drains at most one hour per hour,
    so a stock of the window's hours covers the node for the whole window (ruling Q6).
    """

    node_id: str
    covers: Layer
    hours: float


Action = Protect | AddReserve | AddStock


@dataclass(frozen=True)
class RunRequest:
    """One run: a scenario's damage, the actions, the crew policy and the limits relaxed."""

    damage: Damage
    actions: tuple[Action, ...] = ()
    horizon_h: float | None = None
    """None takes the registry's default horizon."""
    relaxed: frozenset[str] = frozenset()
    """Limits set to their relaxed value, by rule id (D11)."""
    removed: tuple[str, ...] = ()
    """Coupling edges deleted from the world before the run (D11)."""
    policy: str = "default crew order"
    scenario: int | None = None
    plan: tuple[tuple[str, tuple[str, ...]], ...] | None = None
    """A crew plan: each crew's ordered repair jobs, by element id (Work Order 10, C2). None
    keeps the default crew order. Switching trips are not planned: they arise from the world's
    state and go to crews by the default rule."""


@dataclass(frozen=True)
class CrewEntry:
    """One stretch of a crew's time on one job."""

    crew_id: str
    job_id: str
    activity: str
    """travel, assess, repair or switch."""
    start_h: float
    end_h: float


@dataclass(frozen=True)
class Completion:
    """A repair, switching trip or emergency unit that took effect."""

    element_id: str
    kind: str
    time_h: float


@dataclass(frozen=True)
class Delivery:
    """A fuel delivery to a generator tank."""

    edge_id: str
    consumer_id: str
    time_h: float
    amount: float


@dataclass(frozen=True)
class Run:
    """One run's record."""

    request: RunRequest
    horizon_h: float
    step_h: float
    node_ids: tuple[str, ...]
    stock_ids: tuple[str, ...]
    times: tuple[float, ...]
    states: tuple[tuple[float, ...], ...]
    """Per step, every node's state, in node order."""
    levels: tuple[tuple[float, ...], ...]
    """Per step, every stock's level (inf when relaxed to unlimited), in stock order."""
    passes: tuple[int, ...]
    capped: tuple[float, ...]
    """Steps whose settling hit the cap (hours)."""
    crews: tuple[tuple[str, tuple[CrewEntry, ...]], ...]
    crew_positions: tuple[tuple[tuple[str, str], ...], ...]
    completions: tuple[Completion, ...]
    deliveries: tuple[Delivery, ...]
    hours_out: Mapping[str, float] = field(default_factory=dict)
    """Unweighted hours out per end-use node over the horizon."""

    @classmethod
    def build(cls, *, end_use: Mapping[str, float | None], **fields: object) -> "Run":
        """Assemble a run and count its hours out per end-use node."""
        run = cls(**fields)  # type: ignore[arg-type]
        hours = {}
        for column, node_id in enumerate(run.node_ids):
            if end_use.get(node_id) is None:
                continue
            out = [FULL - states[column] for states in run.states[:-1]]
            hours[node_id] = math.fsum(out) * run.step_h
        object.__setattr__(run, "hours_out", hours)
        return run

    def state(self, node_id: str) -> tuple[float, ...]:
        """Return one node's state at every step."""
        column = self.node_ids.index(node_id)
        return tuple(row[column] for row in self.states)

    def level(self, stock_id: str) -> tuple[float, ...]:
        """Return one stock's level at every step."""
        column = self.stock_ids.index(stock_id)
        return tuple(row[column] for row in self.levels)

    def at(self, node_id: str, hour: float) -> float:
        """Return a node's state at the step that starts at (or just before) an hour."""
        step = int(hour / self.step_h + 1e-9)
        return self.state(node_id)[min(step, len(self.times) - 1)]

    def summary(self) -> dict[str, object]:
        """Return the E3 summary: hours out, the node out longest, last repair, most passes."""
        out = [(hours, node_id) for node_id, hours in self.hours_out.items() if hours > 0.0]
        # Ties go to the lowest id; a run with no hours out has no node out longest.
        top = max(out, key=lambda item: (item[0], [-ord(c) for c in item[1]]), default=None)
        longest = None if top is None else (top[1], top[0])
        repairs = [c.time_h for c in self.completions if c.kind in ("facility", "line")]
        return {
            "hours_out": round(math.fsum(self.hours_out.values()), 6),
            "longest_out": None if longest is None else longest[0],
            "longest_out_hours": None if longest is None else round(longest[1], 6),
            "last_repair_h": max(repairs) if repairs else None,
            "most_passes": max(self.passes, default=0),
            "capped_steps": len(self.capped),
        }


FULL = 1.0
