"""The three rules of thumb: most connections first, biggest first, nearest supplier.

Each is an answer, scored like any other and reported as a distance from the optimum; none
passes or fails (ruling Q11). Each rule ranks the elements a model acts on.

Spec: structure v0.17 §7 (check 5); Work Order 10, B4.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace

from swm.dynamics.world import EngineDependency, EngineWorld
from swm.recipe.schema import Layer
from swm.stages.layers import LayersResult

MOST_CONNECTIONS = "most connections first"
BIGGEST = "biggest first"
NEAREST_SUPPLIER = "nearest supplier"
RULES_OF_THUMB = (MOST_CONNECTIONS, BIGGEST, NEAREST_SUPPLIER)

CAPACITY_ATTRIBUTES = ("capacity_mw", "capacity_mva", "capacity_m3_per_day", "storage_m3")
"""CHOICE: the node attributes that carry capacity, each in its own unit. An element's share is
of its layer's total in the same unit, since a layer can hold two (power: MW at generation,
MVA at substations; water: m³/day through treatment and pumping, m³ in storage). Healthcare,
telecom and transport nodes, and every line, carry no capacity and rank last."""
LINE_DEGREE = 2
"""A line joins two elements (Work Order 10, B4)."""


def degrees(world: EngineWorld) -> dict[str, int]:
    """Return each node's degree: its within-layer links plus its couplings.

    Couplings are every coupling edge the engine plays, switched on and hidden: the edges of
    the dependencies and the buffer-resupply edges, each counted once.

    Parameters
    ----------
    world : EngineWorld
        The world played out.

    Returns
    -------
    dict of str to int
        Degree per node id.

    Spec: Work Order 10, B4 (most connections first).
    """
    count = {n.node_id: 0 for n in world.nodes}
    for link in world.links:
        count[link.upstream_id] += 1
        count[link.downstream_id] += 1
    edges: dict[str, tuple[str, str]] = {}
    for dependency in world.dependencies:
        for group in dependency.groups:
            for edge in group:
                edges[edge.edge_id] = (edge.supplier_id, dependency.consumer_id)
    for resupply in world.resupply:
        edges[resupply.edge_id] = (resupply.depot_id, resupply.consumer_id)
    for supplier, consumer in edges.values():
        count[supplier] += 1
        count[consumer] += 1
    return count


def capacity_shares(layers: LayersResult) -> dict[str, float]:
    """Return each node's share of its layer's total capacity in its own unit.

    Parameters
    ----------
    layers : LayersResult
        The sized layers (the requirements stage's).

    Returns
    -------
    dict of str to float
        Share per node id, for nodes whose class carries capacity.

    Spec: Work Order 10, B4 (biggest first).
    """
    held: dict[str, tuple[Layer, str, float]] = {}
    for node in layers.nodes:
        attributes = dict(node.attributes)
        unit = next((a for a in CAPACITY_ATTRIBUTES if attributes.get(a) is not None), None)
        if unit is not None:
            held[node.node_id] = (node.layer, unit, float(attributes[unit]))
    totals: dict[tuple[Layer, str], float] = {}
    for layer, unit, value in held.values():
        totals[(layer, unit)] = totals.get((layer, unit), 0.0) + value
    return {
        node_id: value / totals[(layer, unit)]
        for node_id, (layer, unit, value) in held.items()
        if totals[(layer, unit)] > 0.0
    }


def rank_by_degree(elements: Sequence[str], world: EngineWorld) -> tuple[str, ...]:
    """Rank elements by degree, highest first, ties to the lowest id; a line counts 2."""
    node_degree = degrees(world)
    return tuple(sorted(elements, key=lambda e: (-node_degree.get(e, LINE_DEGREE), e)))


def rank_by_capacity(elements: Sequence[str], shares: Mapping[str, float]) -> tuple[str, ...]:
    """Rank elements by capacity share, largest first; no capacity last; ties to the lowest id."""
    return tuple(sorted(elements, key=lambda e: (e not in shares, -shares.get(e, 0.0), e)))


def nearest_supplier_world(
    world: EngineWorld, eligible: Mapping[tuple[str, Layer], Sequence[str]]
) -> EngineWorld:
    """Return a copy of the world in which every consumer's coupling goes to its nearest supplier.

    The copy keeps every element of the true world, so the true scenarios' damage falls on it
    alike. A coupling whose supplier moves exists only in the copy, so it runs on no line and
    takes no damage.

    CHOICE: a dependency with n distinct suppliers takes its n nearest eligible ones. A supplier
    already among them keeps its coupling; each other moves to the nearest one not yet used,
    keeping its edge's κ and transfer form. Transport dependencies are left
    as they are: rule 3 already lists every origin that reaches the consumer, any one serving.
    A buffer-resupply edge's depot moves to the nearest eligible fuel supplier.

    Parameters
    ----------
    world : EngineWorld
        The true world.
    eligible : Mapping[tuple[str, Layer], Sequence[str]]
        Each consumer's eligible suppliers of each commodity, nearest first
        (``swm.stages.couplings.eligible_suppliers``).

    Returns
    -------
    EngineWorld
        The copy.

    Spec: Work Order 10, B4 (nearest supplier).
    """
    dependencies = tuple(_nearest(d, eligible) for d in world.dependencies)
    resupply = tuple(
        replace(r, depot_id=eligible[(r.consumer_id, Layer.FUEL)][0])
        if eligible.get((r.consumer_id, Layer.FUEL))
        else r
        for r in world.resupply
    )
    return replace(world, dependencies=dependencies, resupply=resupply)


def _nearest(
    dependency: EngineDependency, eligible: Mapping[tuple[str, Layer], Sequence[str]]
) -> EngineDependency:
    options = eligible.get((dependency.consumer_id, dependency.supplier_layer), ())
    if dependency.supplier_layer == Layer.TRANSPORT or not options:
        return dependency
    present = list(dict.fromkeys(e.supplier_id for g in dependency.groups for e in g))
    nearest = list(options[: len(present)])
    # A supplier already among the nearest keeps its coupling; the others move to the nearest
    # suppliers the dependency does not yet use.
    leaving = [s for s in present if s not in nearest]
    moved = dict(zip(leaving, [s for s in nearest if s not in present], strict=False))
    groups = tuple(
        tuple(
            edge
            if moved.get(edge.supplier_id, edge.supplier_id) == edge.supplier_id
            else replace(edge, supplier_id=moved[edge.supplier_id], line_id=None)
            for edge in group
        )
        for group in dependency.groups
    )
    return replace(dependency, groups=groups)
