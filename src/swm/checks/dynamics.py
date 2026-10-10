"""The calm-world run: with no damage, nothing in the world moves (structure v0.9 §4.5, D8).

With no damage, every node holds state 1, every stock stays full, and no crew, delivery or
tolerance clock moves, for the whole horizon. Any deviation fails the build.

Spec: structure v0.9 §4.5 (the calm-world check); Work Order 7, F1.
"""

from swm.dynamics.engine import simulate
from swm.dynamics.records import RunRequest
from swm.dynamics.world import Damage, EngineWorld


def calm_run_problems(world: EngineWorld, horizon_h: float | None = None) -> list[str]:
    """Run the world with no damage and return every deviation from a calm world.

    Parameters
    ----------
    world : EngineWorld
        The world the engine plays out.
    horizon_h : float or None
        Hours to run; None takes the registry's default horizon.

    Returns
    -------
    list of str
        One line per deviation; empty when the world stays calm.

    Spec: Work Order 7, F1.
    """
    run = simulate(world, RunRequest(Damage((), (), ()), horizon_h=horizon_h))
    problems = []
    for column, node_id in enumerate(run.node_ids):
        low = min(row[column] for row in run.states)
        if low != 1.0:
            hour = next(
                t for t, row in zip(run.times, run.states, strict=True) if row[column] != 1.0
            )
            problems.append(f"{node_id} falls to {low} (first at hour {hour})")
    for column, stock_id in enumerate(run.stock_ids):
        if any(row[column] != run.levels[0][column] for row in run.levels):
            problems.append(f"{stock_id} moves from full")
    if any(entries for _, entries in run.crews):
        problems.append("a crew moves")
    if run.deliveries:
        problems.append("a fuel delivery is made")
    if run.completions:
        problems.append("a repair completes")
    if run.capped:
        problems.append(f"{len(run.capped)} steps hit the settling cap")
    return problems
