"""The solver's one way to play the true world: a run's hours out per end-use node.

The solver reads the true world and calls the dynamics engine; it never imports error
induction, and nothing in the generator imports it (CLAUDE.md §3).

Spec: structure v0.17 §5; Work Order 10, B1 and B5.
"""

import os
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace

import numpy as np
from numpy.typing import NDArray

from swm.dynamics.engine import simulate
from swm.dynamics.records import Action, Run, RunRequest
from swm.dynamics.world import Damage, EngineWorld
from swm.recipe.schema import DamageState

Plan = tuple[tuple[str, tuple[str, ...]], ...]
"""A crew plan: each crew's ordered repair jobs, by element id."""
PLAN_POLICY = "crew plan"
PARALLEL_FROM = 64
"""CHOICE: a batch of at least this many runs is spread across every core (ruling Q8); a
smaller one runs in this process, where starting workers would cost more than it saves.
Results come back in the order asked, so a key never depends on the core count."""


@dataclass(frozen=True)
class Job:
    """One run of a batch: the damage, a crew plan (None: the default order) and the actions."""

    damage: Damage
    plan: Plan | None = None
    actions: tuple[Action, ...] = ()


@dataclass
class Runner:
    """Plays one world over one window, and counts the runs it makes."""

    world: EngineWorld
    window_h: float
    runs: int = field(default=0)

    @property
    def end_uses(self) -> tuple[str, ...]:
        """Return the end-use nodes, in id order: the columns of every row of hours out."""
        return tuple(sorted(n.node_id for n in self.world.nodes if n.end_use_weight is not None))

    def run(self, damage: Damage, plan: Plan | None = None) -> Run:
        """Play a damage out, under the default crew order or a plan.

        Parameters
        ----------
        damage : Damage
            What is damaged at hour 0.
        plan : Plan or None
            A crew plan, or None for the default crew order.

        Returns
        -------
        Run
            The engine's run.

        Spec: structure v0.16 §4.5; Work Order 10, C2.
        """
        self.runs += 1
        return simulate(self.world, _request(Job(damage, plan), self.window_h))

    def hours_out(self, damage: Damage, plan: Plan | None = None) -> Mapping[str, float]:
        """Return a run's hours out per end-use node, in h."""
        return self.run(damage, plan).hours_out

    def rows(self, jobs: Sequence[Job]) -> NDArray[np.float64]:
        """Return the hours out of many runs, one row per job, across every core.

        Parameters
        ----------
        jobs : sequence of Job
            The runs.

        Returns
        -------
        numpy.ndarray
            Hours out (h), shape (jobs, end uses), columns in ``end_uses`` order and rows in
            the order of ``jobs``.

        Spec: Work Order 10, B5 and E5 (every core, the results collected in order).
        """
        self.runs += len(jobs)
        columns = self.end_uses
        table = np.empty((len(jobs), len(columns)), dtype=np.float64)
        if len(jobs) < PARALLEL_FROM:
            for index, job in enumerate(jobs):
                table[index] = _play(self.world, self.window_h, columns, job)
            return table
        workers = os.cpu_count() or 1
        chunk = max(1, len(jobs) // (workers * 8))
        with ProcessPoolExecutor(
            max_workers=workers, initializer=_load, initargs=(self.world, self.window_h, columns)
        ) as pool:
            for index, row in enumerate(pool.map(_play_loaded, jobs, chunksize=chunk)):
                table[index] = row
        return table

    def on(self, world: EngineWorld) -> "Runner":
        """Return a runner for another world over the same window, sharing no count."""
        return replace(self, world=world, runs=0)


COMPLETE = DamageState.COMPLETE.value
"""A strike's damage state (ruling Q4)."""


def with_node(damage: Damage, node_id: str) -> Damage:
    """Return a damage with one more node taking complete damage at hour 0 (ruling Q4).

    The strike names its state, complete; a node the scenario already damaged takes complete
    damage in its place.
    """
    states = {**dict(damage.states), node_id: COMPLETE}
    return replace(
        damage,
        nodes=tuple(sorted({*damage.nodes, node_id})),
        states=tuple(sorted(states.items())),
    )


def _request(job: Job, window_h: float) -> RunRequest:
    policy = PLAN_POLICY if job.plan is not None else "default crew order"
    return RunRequest(
        job.damage, actions=job.actions, horizon_h=window_h, policy=policy, plan=job.plan
    )


_WORKER: list[tuple[EngineWorld, float, tuple[str, ...]]] = []
"""A worker process's world, window and columns, set once when the pool starts it."""


def _load(world: EngineWorld, window_h: float, columns: tuple[str, ...]) -> None:
    _WORKER[:] = [(world, window_h, columns)]


def _play_loaded(job: Job) -> tuple[float, ...]:
    world, window_h, columns = _WORKER[0]
    return _play(world, window_h, columns, job)


def _play(
    world: EngineWorld, window_h: float, columns: tuple[str, ...], job: Job
) -> tuple[float, ...]:
    hours = simulate(world, _request(job, window_h)).hours_out
    return tuple(hours[node] for node in columns)
