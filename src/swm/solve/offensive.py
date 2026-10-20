"""The offensive model: strike k nodes at hour 0 on the calm world (rulings Q3 and Q4).

A struck node takes complete damage, and the crews repair it in the default order. Lines are not
targets. Every set of k distinct nodes is an answer; the attacker maximizes the loss.

Spec: structure v0.17 §5 (the three Phase 2 models); Work Order 10, Part D.
"""

import itertools
from collections.abc import Iterator, Sequence

from swm.dynamics.world import Damage, EngineWorld
from swm.solve.runner import with_node

CALM = Damage((), (), ())
"""The calm world: no storm, nothing damaged (ruling Q3)."""
NO_STRIKE = "no strike"


def targets(world: EngineWorld) -> tuple[str, ...]:
    """Return the nodes a strike may target: every node, in id order (lines are not targets)."""
    return tuple(sorted(n.node_id for n in world.nodes))


def strike_sets(nodes: Sequence[str], k: int) -> Iterator[tuple[str, ...]]:
    """Yield every set of k distinct nodes, in lexicographic order.

    Parameters
    ----------
    nodes : sequence of str
        The targets, in id order.
    k : int
        Nodes struck.

    Yields
    ------
    tuple of str
        One strike, its nodes in id order.

    Spec: Work Order 10, D2.
    """
    yield from itertools.combinations(sorted(nodes), k)


def strike(nodes: Sequence[str]) -> Damage:
    """Return the calm world with each node completely damaged at hour 0 (ruling Q4)."""
    damage = CALM
    for node in nodes:
        damage = with_node(damage, node)
    return damage


def strike_text(nodes: Sequence[str]) -> str:
    """Return a strike as the key prints it: its nodes, in id order."""
    return ", ".join(sorted(nodes))
