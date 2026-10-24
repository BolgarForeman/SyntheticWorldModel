"""The restorative model: sequence the repair crews over one named scenario (ruling Q2).

A plan gives each crew an ordered list of jobs. Every failed element in the scenario is repaired
once, by one crew, and a crew may have no jobs. Both crews start at the base at hour 0; travel,
preparation and manual switching follow the engine's rules (spec §4.5).

Spec: structure v0.17 §5 (the three Phase 2 models); Work Order 10, Part C.
"""

import itertools
import math
from collections.abc import Iterator, Sequence

from swm.dynamics.engine import QUICK, facility_repair, quick_paths
from swm.dynamics.records import CrewEntry
from swm.dynamics.world import Damage, EngineWorld
from swm.solve.runner import Plan, Runner


def repair_jobs(world: EngineWorld, damage: Damage) -> tuple[str, ...]:
    """Return the elements a scenario leaves for the crews: its repair jobs, in id order.

    A damaged node is a job when the world holds its repair and it is not unrepairable; every
    downed line is a job; a node with a quick path opens one more, named ``quick:<node>``
    (Work Order 11, B4). Switching trips are not jobs a plan sequences: they arise from the
    world's state (Work Order 10, C1).

    Parameters
    ----------
    world : EngineWorld
        The world played out.
    damage : Damage
        The scenario's damage.

    Returns
    -------
    tuple of str
        Element ids, and the quick-path job ids.

    Spec: structure v0.19 §4.5 (repair and crews); Work Order 10, C1; Work Order 11, B4.
    """
    unrepairable = set(world.unrepairable)
    nodes = [
        n for n in damage.nodes
        if n not in unrepairable and facility_repair(world, damage, n) is not None
    ]  # fmt: skip
    quick = [f"{QUICK}:{p.node_id}" for p in quick_paths(world, damage)]
    return tuple(sorted({*nodes, *damage.lines, *quick}))


def plan_count(jobs: int, crews: int) -> int:
    """Return how many plans there are: every split of the jobs between the crews, in every order.

    Ordered lists of n distinct jobs over k labelled crews number n! x C(n + k - 1, k - 1).

    Parameters
    ----------
    jobs : int
        The repair jobs.
    crews : int
        The crews.

    Returns
    -------
    int
        The number of plans.

    Spec: Work Order 10, C3.
    """
    return math.factorial(jobs) * math.comb(jobs + crews - 1, crews - 1)


def plans(jobs: Sequence[str], crews: Sequence[str]) -> Iterator[Plan]:
    """Yield every plan: each order of the jobs, cut into one list per crew, in a fixed order.

    Parameters
    ----------
    jobs : sequence of str
        The repair jobs, by element id.
    crews : sequence of str
        The crew ids.

    Yields
    ------
    Plan
        Each crew's ordered jobs. Orders come in lexicographic order of the sorted jobs, and
        each order's cuts in lexicographic order.

    Spec: Work Order 10, C3.
    """
    for order in itertools.permutations(sorted(jobs)):
        for cuts in itertools.combinations_with_replacement(range(len(order) + 1), len(crews) - 1):
            bounds = (0, *cuts, len(order))
            yield tuple(
                (crew, tuple(order[bounds[i] : bounds[i + 1]])) for i, crew in enumerate(crews)
            )


NO_JOBS = "no jobs"


def plan_text(plan: Plan) -> str:
    """Return a plan as the key prints it: each crew and its jobs, in order."""
    return "; ".join(f"{crew}: {', '.join(jobs) if jobs else NO_JOBS}" for crew, jobs in plan)


def plan_of(text: str) -> Plan:
    """Read a plan back from its printed text (the inverse of ``plan_text``)."""
    plan = []
    for part in text.split("; "):
        crew, _, jobs = part.partition(": ")
        plan.append((crew, () if jobs == NO_JOBS else tuple(jobs.split(", "))))
    return tuple(plan)


def ranked_plan(runner: Runner, damage: Damage, ranking: Sequence[str]) -> Plan:
    """Turn a ranking of the jobs into a plan: each crew takes the next job when it comes free.

    The crews take jobs in rank order. Each job goes to the crew that comes free first (ties to
    the lowest crew id), from when it finishes the jobs it already holds.

    CHOICE: a crew's free time is read from a run in which the jobs not yet given out are
    appended to the first crew's list; a crew's earlier jobs run the same whatever follows them.

    Parameters
    ----------
    runner : Runner
        Plays the world.
    damage : Damage
        The scenario's damage.
    ranking : sequence of str
        The repair jobs, first ranked first.

    Returns
    -------
    Plan
        Each crew's ordered jobs.

    Spec: Work Order 10, B4 (how a ranking becomes an answer: restorative).
    """
    crews = [c.crew_id for c in runner.world.crews]
    held: dict[str, list[str]] = {crew: [] for crew in crews}
    for index, job in enumerate(ranking):
        rest = list(ranking[index:])
        trial = tuple(
            (crew, tuple(held[crew] + (rest if crew == crews[0] else []))) for crew in crews
        )
        run = runner.run(damage, trial)
        free_at = {crew: _free_after(run.crews, crew, held[crew]) for crew in crews}
        chosen = min(crews, key=lambda crew: (free_at[crew], crew))
        held[chosen].append(job)
    return tuple((crew, tuple(held[crew])) for crew in crews)


def _free_after(
    logs: Sequence[tuple[str, tuple[CrewEntry, ...]]], crew: str, jobs: Sequence[str]
) -> float:
    """Return when a crew finishes the jobs it holds (0 for a crew holding none)."""
    if not jobs:
        return 0.0
    held = {f"repair:{job}" for job in jobs}
    return max(entry.end_h for entry in dict(logs)[crew] if entry.job_id in held)
