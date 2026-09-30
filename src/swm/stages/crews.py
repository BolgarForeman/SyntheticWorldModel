"""Crews stage: crew bases sited in towns by road access, the crews, and the emergency pool.

Crews are counted in the recipe and form one pool. Crew bases (``crew_base``, distinct from the
fuel depot class) sit at town centres. They are chosen one at a time, each time taking the town
that most shortens the total road distance from the nearest base to every node. The emergency
pool of mobile units comes from the modeling rules registry.

Nothing here is drawn, so the stage reads no stream. All of it is real but unobserved.

Spec: structure v0.6 §4.4 and §4.4a (crews, repair: pilot); Work Order 5, Part H; decision 0011.
"""

import heapq
import math
from dataclasses import dataclass

import numpy as np

from swm.recipe.schema import Layer, NodeClass
from swm.rules.registry import Registry
from swm.stages.layers import LayersResult, Node
from swm.stages.terrain import City, TerrainResult, _label_land

M_PER_KM = 1000.0

MOBILE_UNIT_CODES = {"mobile_substation": "MSS", "mobile_cell_site": "MCS"}
"""Identifier prefix of each mobile unit kind in the emergency pool."""


ELIGIBLE_CLASS = {
    "mobile_substation": NodeClass.DISTRIBUTION_SUBSTATION,
    "mobile_cell_site": NodeClass.MAST,
}
"""The one class each mobile unit kind serves (§4.4a: no other class has an emergency mode)."""


@dataclass(frozen=True)
class CrewBase:
    """One crew base, at a town centre, joined to the roads at its nearest transport node."""

    base_id: str
    city_id: int
    row: int
    column: int
    access_node_id: str
    access_km: float
    """Straight-line distance from the base to the transport node it joins the roads at."""
    crews: int


@dataclass(frozen=True)
class Crew:
    """One repair crew and the base it starts from."""

    crew_id: str
    base_id: str


@dataclass(frozen=True)
class MobileUnit:
    """One unit of the emergency pool and the base it is kept at."""

    unit_id: str
    kind: str
    base_id: str


@dataclass(frozen=True)
class CrewsResult:
    """The crews stage's output. Real but unobserved: never emitted."""

    bases: tuple[CrewBase, ...]
    crews: tuple[Crew, ...]
    units: tuple[MobileUnit, ...]


class RoadNetwork:
    """The transport links as a road graph, with the straight leg that joins a cell to it.

    A cell joins the roads at the nearest transport node on its own landmass, as consumers do
    in the couplings stage. Road distances are shortest paths over the transport links' lengths.

    Spec: structure v0.6 §4.4a (travel over roads); Work Order 5, G3.
    """

    def __init__(self, terrain: TerrainResult, layers: LayersResult) -> None:
        self.labels, _ = _label_land(np.asarray(terrain.land))
        self.cell_km = terrain.grid.cell_size_m / M_PER_KM
        self.transport = [node for node in layers.nodes if node.layer == Layer.TRANSPORT]
        self.neighbours: dict[str, list[tuple[str, float]]] = {
            node.node_id: [] for node in self.transport
        }
        for link in layers.links:
            if link.layer == Layer.TRANSPORT:
                self.neighbours[link.from_id].append((link.to_id, link.length_km))
                self.neighbours[link.to_id].append((link.from_id, link.length_km))
        self._distances: dict[str, dict[str, float]] = {}

    def access(self, row: int, column: int) -> tuple[Node, float] | None:
        """Return the transport node a cell joins the roads at, and the straight leg in km."""
        island = self.labels[row, column]
        on_island = [n for n in self.transport if self.labels[n.row, n.column] == island]
        if not on_island:
            return None
        nearest = min(on_island, key=lambda n: (_cells2(n.row - row, n.column - column), n.node_id))
        return nearest, self.leg_km(row, column, nearest.row, nearest.column)

    def leg_km(self, row: int, column: int, to_row: int, to_column: int) -> float:
        """Straight-line distance between two cells, in km."""
        return math.sqrt(_cells2(to_row - row, to_column - column)) * self.cell_km

    def road_km(self, from_id: str) -> dict[str, float]:
        """Shortest road distance (km) from one transport node to every node it reaches."""
        if from_id not in self._distances:
            self._distances[from_id] = self._shortest_paths(from_id)
        return self._distances[from_id]

    def _shortest_paths(self, from_id: str) -> dict[str, float]:
        settled: dict[str, float] = {}
        frontier = [(0.0, from_id)]
        while frontier:
            km, node_id = heapq.heappop(frontier)
            if node_id in settled:
                continue
            settled[node_id] = km
            for other, length_km in self.neighbours[node_id]:
                if other not in settled:
                    heapq.heappush(frontier, (km + length_km, other))
        return settled


def build_crews(
    crews: int, crew_base: int, terrain: TerrainResult, layers: LayersResult, rules: Registry
) -> CrewsResult:
    """Site the crew bases, deal the crews to them, and keep the emergency pool at the first.

    Parameters
    ----------
    crews : int
        Repair crews in the world, in one pool (recipe ``unobserved.crews``).
    crew_base : int
        Crew bases to site (recipe ``unobserved.crew_base``).
    terrain : TerrainResult
        The ground: land, cities and cell size.
    layers : LayersResult
        The layers; the transport links are the roads.
    rules : Registry
        The modeling rules in force (the emergency pool).

    Returns
    -------
    CrewsResult
        The bases in the order sited, the crews and the mobile units.

    Raises
    ------
    ValueError
        If the world has fewer towns on the main road network than ``crew_base`` asks for.

    Spec: structure v0.6 §4.4a (crews; repair: pilot); Work Order 5, H1-H2.
    """
    network = RoadNetwork(terrain, layers)
    sited = _site_bases(crew_base, terrain.cities, layers.nodes, network)
    # CHOICE: the crews are dealt to the bases in turn, starting at the first sited.
    shares = [crews // crew_base + (1 if i < crews % crew_base else 0) for i in range(crew_base)]
    bases = tuple(
        CrewBase(
            f"CRB-{i + 1:04d}",
            city.city_id,
            city.centre_row,
            city.centre_column,
            node.node_id,
            km,
            shares[i],
        )
        for i, (city, node, km) in enumerate(sited)
    )
    crew_list = tuple(Crew(f"CRW-{i + 1:04d}", bases[i % crew_base].base_id) for i in range(crews))
    return CrewsResult(bases, crew_list, _emergency_pool(bases[0], rules))


def _site_bases(
    count: int, cities: tuple[City, ...], nodes: tuple[Node, ...], network: RoadNetwork
) -> list[tuple[City, Node, float]]:
    """Choose the towns one at a time, each most shortening the total distance to every node."""
    candidates = _candidates(cities, network)
    if len(candidates) < count:
        raise ValueError(
            f"unobserved.crew_base = {count}: the world has {len(candidates)} towns on the main "
            "road network to site crew bases in; lower the setting"
        )
    reach = [
        (node, access)
        for node in nodes
        if (access := network.access(node.row, node.column)) is not None
    ]
    # CHOICE: road access is the total road distance from the nearest base to every node the
    # main road network reaches (a greedy p-median); nodes reached only by sea do not count.
    best: dict[int, float] = {}
    chosen: list[tuple[City, Node, float]] = []
    for _ in range(count):
        scores = []
        for city, node, km in candidates:
            if any(city.city_id == c.city_id for c, _, _ in chosen):
                continue
            distances = _distances_from(node, km, reach, network)
            total = math.fsum(min(d, best.get(i, math.inf)) for i, d in distances.items())
            scores.append((total, city.city_id, city, node, km))
        _, _, city, node, km = min(scores, key=lambda s: (s[0], s[1]))
        chosen.append((city, node, km))
        for i, d in _distances_from(node, km, reach, network).items():
            best[i] = min(d, best.get(i, math.inf))
    return chosen


def _candidates(cities: tuple[City, ...], network: RoadNetwork) -> list[tuple[City, Node, float]]:
    """Towns whose centre joins the main road network: the component with the most nodes."""
    main = _main_component(network)
    candidates = []
    for city in sorted(cities, key=lambda c: c.city_id):
        access = network.access(city.centre_row, city.centre_column)
        if access is not None and access[0].node_id in main:
            candidates.append((city, access[0], access[1]))
    return candidates


def _main_component(network: RoadNetwork) -> set[str]:
    components: list[set[str]] = []
    for node in sorted(network.transport, key=lambda n: n.node_id):
        if not any(node.node_id in c for c in components):
            components.append(set(network.road_km(node.node_id)))
    if not components:
        return set()
    return min(components, key=lambda c: (-len(c), min(c)))


def _distances_from(
    access_node: Node,
    access_km: float,
    reach: list[tuple[Node, tuple[Node, float]]],
    network: RoadNetwork,
) -> dict[int, float]:
    """Road distance (km) from a base to each node it reaches by road, by position in reach."""
    road = network.road_km(access_node.node_id)
    return {
        i: access_km + road[joins.node_id] + leg_km
        for i, (_, (joins, leg_km)) in enumerate(reach)
        if joins.node_id in road
    }


def _emergency_pool(home: CrewBase, rules: Registry) -> tuple[MobileUnit, ...]:
    # CHOICE: the pool is kept at the first sited base, the one with the best road access.
    pool = rules.value("repair.emergency.pool")
    return tuple(
        MobileUnit(f"{MOBILE_UNIT_CODES[kind]}-{i + 1:04d}", kind, home.base_id)
        for kind in sorted(pool)
        for i in range(int(pool[kind]))
    )


def _cells2(dr: int, dc: int) -> int:
    return dr * dr + dc * dc


def crews_tables(result: CrewsResult) -> dict[str, list[dict[str, object]]]:
    """Return the crew bases, crews and mobile units as plain data in a fixed order.

    Parameters
    ----------
    result : CrewsResult
        The crews stage's output.

    Returns
    -------
    dict
        Tables by name, numbers rounded to six decimals.

    Spec: Work Order 5, Part H.
    """
    return {
        "crew_bases": [
            {**vars(base), "access_km": round(base.access_km, 6)} for base in result.bases
        ],
        "crews": [dict(vars(crew)) for crew in result.crews],
        "mobile_units": [dict(vars(unit)) for unit in result.units],
    }
