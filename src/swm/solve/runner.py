"""The solver's one way to play the true world: a run's hours out per end-use node.

The solver reads the true world and calls the dynamics engine; it never imports error
induction, and nothing in the generator imports it (CLAUDE.md §3).

Spec: structure v0.17 §5; Work Order 10, B1.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from swm.dynamics.engine import simulate
from swm.dynamics.records import Run, RunRequest
from swm.dynamics.world import Damage, EngineWorld

Plan = tuple[tuple[str, tuple[str, ...]], ...]
"""A crew plan: each crew's ordered repair jobs, by element id."""
PLAN_POLICY = "crew plan"


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

    def on(self, world: EngineWorld) -> "Runner":
        """Return a runner for another world over the same window, sharing no count."""
        return replace(self, world=world, runs=0)


def with_node(damage: Damage, node_id: str) -> Damage:
    """Return a damage with one more node taking complete damage at hour 0 (ruling Q4)."""
    if node_id in damage.nodes:
        return damage
    return replace(damage, nodes=tuple(sorted((*damage.nodes, node_id))))
