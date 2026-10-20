"""The solver's one way to play the true world: a run's hours out per end-use node.

The solver reads the true world and calls the dynamics engine; it never imports error
induction, and nothing in the generator imports it (CLAUDE.md §3).

Spec: structure v0.17 §5; Work Order 10, B1.
"""

import os
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace

from swm.dynamics.engine import simulate
from swm.dynamics.records import Run, RunRequest
from swm.dynamics.world import Damage, EngineWorld
from swm.recipe.schema import DamageState

Plan = tuple[tuple[str, tuple[str, ...]], ...]
"""A crew plan: each crew's ordered repair jobs, by element id."""
PLAN_POLICY = "crew plan"
PARALLEL_FROM = 64
"""CHOICE: a batch of at least this many runs is spread across every core (ruling Q8); a
smaller one runs in this process, where starting workers would cost more than it saves.
Results come back in the order asked, so a key never depends on the core count."""
Job = tuple[Damage, Plan | None]
"""One run of a batch: the damage, and a crew plan or None for the default order."""


@dataclass
class Runner:
    """Plays one world over one window, and counts the runs it makes."""

    world: EngineWorld
    window_h: float
    runs: int = field(default=0)

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
        policy = PLAN_POLICY if plan is not None else "default crew order"
        request = RunRequest(damage, horizon_h=self.window_h, policy=policy, plan=plan)
        return simulate(self.world, request)

    def hours_out(self, damage: Damage, plan: Plan | None = None) -> Mapping[str, float]:
        """Return a run's hours out per end-use node, in h."""
        return self.run(damage, plan).hours_out

    def hours_out_all(self, jobs: Sequence[Job]) -> list[Mapping[str, float]]:
        """Return the hours out of many runs, in the order given, across every core.

        Parameters
        ----------
        jobs : sequence of Job
            Each run's damage and plan.

        Returns
        -------
        list of Mapping[str, float]
            Each run's hours out per end-use node, in the order of ``jobs``.

        Spec: Work Order 10, B5 and E5 (every core, the results collected in order).
        """
        self.runs += len(jobs)
        if len(jobs) < PARALLEL_FROM:
            return [dict(_play(self.world, self.window_h, job)) for job in jobs]
        workers = os.cpu_count() or 1
        chunk = max(1, len(jobs) // (workers * 4))
        with ProcessPoolExecutor(
            max_workers=workers, initializer=_load, initargs=(self.world, self.window_h)
        ) as pool:
            return list(pool.map(_play_loaded, jobs, chunksize=chunk))

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


_WORKER: list[tuple[EngineWorld, float]] = []
"""A worker process's world and window, set once when the pool starts it."""


def _load(world: EngineWorld, window_h: float) -> None:
    _WORKER[:] = [(world, window_h)]


def _play_loaded(job: Job) -> dict[str, float]:
    world, window_h = _WORKER[0]
    return _play(world, window_h, job)


def _play(world: EngineWorld, window_h: float, job: Job) -> dict[str, float]:
    damage, plan = job
    policy = PLAN_POLICY if plan is not None else "default crew order"
    request = RunRequest(damage, horizon_h=window_h, policy=policy, plan=plan)
    return dict(simulate(world, request).hours_out)
