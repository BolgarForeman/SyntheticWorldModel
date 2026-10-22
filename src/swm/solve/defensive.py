"""The defensive model: protect condition and add reserves before the storm (Q5, Q6, Q7).

Up to the budget (a ceiling: units may be left unspent):
- **protect condition** (cost 2): the element is undamaged in every scenario. Targets: every
  element the storm can damage (facilities, overhead lines and routed power feeds);
- **add reserve** (cost 1): a stock on one inbound dependency of one node, covering the
  request's window at the node's full draw: a new stock where the node has none for that
  commodity, otherwise the window's hours added to the stock it has. At most one per dependency,
  and only on a storable commodity: power, water, fuel and transport, never telecom (v0.18).

The objective is the expected weighted service-hours lost over the scenarios, equally weighted.

Spec: structure v0.17 §5 (the three Phase 2 models); Work Order 10, Part E.
"""

import itertools
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from swm.dynamics.records import Action, AddReserve, AddStock, Protect
from swm.dynamics.world import Damage, EngineWorld, Stock
from swm.recipe.schema import Layer
from swm.rules.registry import Registry

NO_ACTION = "no action"
PROTECT = "protect"
RESERVE = "reserve"


@dataclass(frozen=True, order=True)
class Reserve:
    """A reserve on one inbound dependency: the consumer and the commodity it covers."""

    node_id: str
    covers: Layer


@dataclass(frozen=True)
class Defence:
    """One defensive answer: the elements protected and the reserves added."""

    protects: tuple[str, ...] = ()
    reserves: tuple[Reserve, ...] = ()

    def cost(self, protect_cost: int, reserve_cost: int) -> int:
        """Return the answer's cost in units."""
        return protect_cost * len(self.protects) + reserve_cost * len(self.reserves)

    def targets(self) -> set[str]:
        """Return the elements its actions touch: protected elements and reserved nodes."""
        return {*self.protects, *(r.node_id for r in self.reserves)}


def reserves_of(world: EngineWorld, storable: Sequence[Layer]) -> tuple[Reserve, ...]:
    """Return every inbound dependency a reserve can go on, in (node, commodity) order.

    Parameters
    ----------
    world : EngineWorld
        The world.
    storable : sequence of Layer
        The commodities that can be stored (registry ``solve.reservable_commodities``):
        telecom is not among them.

    Returns
    -------
    tuple of Reserve
        One per inbound dependency on a storable commodity.

    Spec: structure v0.18 §5; WO-10c answers, 1.
    """
    return tuple(sorted(
        {Reserve(d.consumer_id, d.supplier_layer) for d in world.dependencies
         if d.supplier_layer in storable}
    ))  # fmt: skip


def storable(rules: Registry) -> tuple[Layer, ...]:
    """Return the commodities a reserve can go on, from the registry."""
    return tuple(Layer(value) for value in rules.value("solve.reservable_commodities"))


def defences(
    protectable: Sequence[str],
    reserves: Sequence[Reserve],
    budget: int,
    protect_cost: int,
    reserve_cost: int,
) -> Iterator[Defence]:
    """Yield every affordable answer, spending under the budget included, in a fixed order.

    Answers come by number of protections, then which, then number of reserves, then which,
    each in lexicographic order.

    Parameters
    ----------
    protectable : sequence of str
        Every element protection can target, in id order.
    reserves : sequence of Reserve
        Every dependency a reserve can go on.
    budget : int
        The budget, in cost units (a ceiling).
    protect_cost, reserve_cost : int
        Each action's cost, in units.

    Yields
    ------
    Defence
        One answer.

    Spec: Work Order 10, E1 (the budget a ceiling: spending under it is searched).
    """
    for protect_count in range(budget // protect_cost + 1):
        left = budget - protect_count * protect_cost
        for protects in itertools.combinations(sorted(protectable), protect_count):
            for reserve_count in range(left // reserve_cost + 1):
                for chosen in itertools.combinations(sorted(reserves), reserve_count):
                    yield Defence(protects, chosen)


def defence_text(defence: Defence) -> str:
    """Return an answer as the key prints it."""
    parts = [f"{PROTECT} {element}" for element in defence.protects]
    parts += [f"{RESERVE} {r.node_id} {r.covers}" for r in defence.reserves]
    return "; ".join(parts) if parts else NO_ACTION


def defence_of(text: str) -> Defence:
    """Read an answer back from its printed text (the inverse of ``defence_text``)."""
    if text == NO_ACTION:
        return Defence()
    protects, reserves = [], []
    for part in text.split("; "):
        kind, _, rest = part.partition(" ")
        if kind == PROTECT:
            protects.append(rest)
        else:
            node, _, covers = rest.partition(" ")
            reserves.append(Reserve(node, Layer(covers)))
    return Defence(tuple(protects), tuple(reserves))


def scenario_actions(
    defence: Defence, damage: Damage, stocks: Sequence[Stock], window_h: float
) -> tuple[Action, ...]:
    """Return the actions one scenario's run takes for an answer.

    A protection of an element the scenario did not damage changes nothing in that run, so it is
    left out: this is what lets runs be reused between answers (Work Order 10, E4 and E5). A
    reserve adds the window's hours to the node's first stock for that commodity, in the order
    the engine draws them, or creates a stock where there is none.

    Parameters
    ----------
    defence : Defence
        The answer.
    damage : Damage
        The scenario's damage.
    stocks : sequence of Stock
        The world's stocks.
    window_h : float
        The request's window, in h (ruling Q6).

    Returns
    -------
    tuple of Action
        Protections first, then reserves, each in order.

    Spec: Work Order 10, E1, E2 and E4.
    """
    damaged = {*damage.nodes, *damage.lines}
    actions: list[Action] = [Protect(e) for e in defence.protects if e in damaged]
    for reserve in defence.reserves:
        held = sorted(
            (s for s in stocks if s.node_id == reserve.node_id and s.covers == reserve.covers),
            key=lambda s: (s.generator, s.stock_id),
        )
        if held:
            actions.append(AddReserve(held[0].stock_id, window_h))
        else:
            actions.append(AddStock(reserve.node_id, reserve.covers, window_h))
    return tuple(actions)
