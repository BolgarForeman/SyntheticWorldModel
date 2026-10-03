"""The road network as geometry: the nearest road point to a place, and routes along roads.

Roads are the transport layer's links, each a polyline in EPSG:32710 metres between two
transport nodes. A place joins the roads at the nearest point on any road of its own landmass;
a route between two road points runs along the roads, through the road nodes, by the shortest
way. Power feeds follow these routes (structure v0.8 §4.2), and crews reach a line failure by
road before going off road (§4.3b, repair).

Only +, -, x, / and sqrt are used.

Spec: structure v0.8 §4.2 (feeds along roads) and §4.3b (repair travel); Work Order 6c, B1 and D1.
"""

import heapq
import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

import numpy as np

from swm.coordinates import cell_of
from swm.recipe.schema import Layer
from swm.stages.layers import LayersResult, Link
from swm.stages.terrain import TerrainResult, _label_land

Point = tuple[float, float]


@dataclass(frozen=True)
class RoadPoint:
    """A point on a road: which road, how far along it, and how far it lies off the road."""

    road: int
    """Index of the road among the transport links."""
    along_m: float
    point: Point
    offroad_m: float


class RoadMap:
    """The transport links as roads, with their nodes as junctions."""

    def __init__(self, terrain: TerrainResult, layers: LayersResult) -> None:
        self.grid = terrain.grid
        self.labels, _ = _label_land(np.asarray(terrain.land))
        self.roads: list[Link] = [link for link in layers.links if link.layer == Layer.TRANSPORT]
        self.steps = [[_length(a, b) for a, b in pairwise(road.points)] for road in self.roads]
        self.lengths = [math.fsum(steps) for steps in self.steps]
        self.junctions: dict[str, list[tuple[str, int]]] = {}
        for index, road in enumerate(self.roads):
            self.junctions.setdefault(road.from_id, []).append((road.to_id, index))
            self.junctions.setdefault(road.to_id, []).append((road.from_id, index))
        self._trees: dict[str, tuple[dict[str, float], dict[str, tuple[str, int]]]] = {}

    def landmass(self, point: Point) -> int:
        """Return the label of the landmass a point lies on (0 at sea)."""
        row, column = cell_of(point[0], point[1], self.grid)
        return int(self.labels[row, column])

    def nearest(self, point: Point) -> RoadPoint | None:
        """Return the nearest point on a road of the point's own landmass, or None if none.

        Ties go to the lower road index, then the earlier segment, so the answer is the same
        on every platform.
        """
        island = self.landmass(point)
        best: tuple[float, int, float, Point] | None = None
        for index, road in enumerate(self.roads):
            # CHOICE: a point at sea (on a straight logical link over water) joins the nearest
            # road on any landmass; a point on land, only roads on its own landmass.
            if island != 0 and self.landmass(road.points[0]) != island:
                continue
            walked = 0.0
            for (a, b), step in zip(pairwise(road.points), self.steps[index], strict=True):
                share = _projection(point, a, b, step)
                foot = (a[0] + share * (b[0] - a[0]), a[1] + share * (b[1] - a[1]))
                distance = _length(point, foot)
                if best is None or distance < best[0]:
                    best = (distance, index, walked + share * step, foot)
                walked += step
        if best is None:
            return None
        distance, index, along, foot = best
        return RoadPoint(index, along, foot, distance)

    def route(self, start: RoadPoint, end: RoadPoint) -> tuple[list[Point], float] | None:
        """Return the polyline and length (m) of the shortest road route between two points.

        None when no road joins them.
        """
        if start.road == end.road:
            points = self._part(start.road, start.along_m, end.along_m)
            return points, abs(end.along_m - start.along_m)
        best: tuple[float, str, str] | None = None
        for first in self._ends(start):
            distances, _ = self._tree(first[0])
            for last in self._ends(end):
                if last[0] not in distances:
                    continue
                total = first[1] + distances[last[0]] + last[1]
                if best is None or total < best[0]:
                    best = (total, first[0], last[0])
        if best is None:
            return None
        total, first_node, last_node = best
        points = self._part(start.road, start.along_m, self._node_along(start.road, first_node))
        points += self._junction_path(first_node, last_node)
        points += self._part(end.road, self._node_along(end.road, last_node), end.along_m)
        return _deduplicated(points), total

    def distance_from(self, node_id: str, end: RoadPoint) -> float | None:
        """Return the road distance (m) from a transport node to a road point, or None."""
        distances, _ = self._tree(node_id)
        options = [distances[node] + leg for node, leg in self._ends(end) if node in distances]
        return min(options) if options else None

    def _ends(self, point: RoadPoint) -> list[tuple[str, float]]:
        """Return the road's two end nodes, with the distance (m) from the point to each."""
        road = self.roads[point.road]
        length = self.lengths[point.road]
        return [(road.from_id, point.along_m), (road.to_id, length - point.along_m)]

    def _node_along(self, index: int, node_id: str) -> float:
        return 0.0 if self.roads[index].from_id == node_id else self.lengths[index]

    def _tree(self, source: str) -> tuple[dict[str, float], dict[str, tuple[str, int]]]:
        """Shortest road distances from a node, and each node's way back toward it."""
        if source not in self._trees:
            settled: dict[str, float] = {}
            back: dict[str, tuple[str, int]] = {}
            frontier = [(0.0, source, "", -1)]
            while frontier:
                distance, node, previous, road = heapq.heappop(frontier)
                if node in settled:
                    continue
                settled[node] = distance
                if road >= 0:
                    back[node] = (previous, road)
                for other, index in sorted(self.junctions.get(node, [])):
                    if other not in settled:
                        heapq.heappush(
                            frontier, (distance + self.lengths[index], other, node, index)
                        )
            self._trees[source] = (settled, back)
        return self._trees[source]

    def _junction_path(self, first: str, last: str) -> list[Point]:
        """Return the roads' polylines from one node to another along the shortest way."""
        _, back = self._tree(first)
        pieces: list[list[Point]] = []
        node = last
        while node != first:
            previous, index = back[node]
            road = self.roads[index]
            points = list(road.points)
            pieces.append(points if road.from_id == previous else points[::-1])
            node = previous
        joined: list[Point] = []
        for piece in reversed(pieces):
            joined += piece
        return joined

    def _part(self, index: int, from_m: float, to_m: float) -> list[Point]:
        """Return the stretch of one road between two distances along it, in travel order."""
        low, high = min(from_m, to_m), max(from_m, to_m)
        points = sub_polyline(self.roads[index].points, self.steps[index], low, high)
        return points if from_m <= to_m else points[::-1]


def sub_polyline(
    points: Sequence[Point], steps: Sequence[float], start_m: float, end_m: float
) -> list[Point]:
    """Return the part of a polyline between two distances along it (start ≤ end), in metres.

    Parameters
    ----------
    points : sequence of (float, float)
        The polyline's vertices.
    steps : sequence of float
        Each segment's length, in m.
    start_m, end_m : float
        Distances along the polyline, in m.

    Returns
    -------
    list of (float, float)
        The vertices of that part, its two ends included.

    Spec: Work Order 6c, B1 and C1.
    """
    result: list[Point] = []
    walked = 0.0
    for (a, b), step in zip(pairwise(points), steps, strict=True):
        low, high = max(start_m, walked), min(end_m, walked + step)
        if high >= low and step > 0.0:
            for at in (low, high):
                share = (at - walked) / step
                point = (a[0] + share * (b[0] - a[0]), a[1] + share * (b[1] - a[1]))
                if not result or result[-1] != point:
                    result.append(point)
        walked += step
    return result or [points[0]]


def _projection(point: Point, a: Point, b: Point, step: float) -> float:
    """Share (0-1) along segment a-b of the point's nearest point on it."""
    if step == 0.0:
        return 0.0
    share = ((point[0] - a[0]) * (b[0] - a[0]) + (point[1] - a[1]) * (b[1] - a[1])) / (step * step)
    return min(max(share, 0.0), 1.0)


def _length(a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return math.sqrt(dx * dx + dy * dy)


def _deduplicated(points: list[Point]) -> list[Point]:
    kept: list[Point] = []
    for point in points:
        if not kept or kept[-1] != point:
            kept.append(point)
    return kept


def polyline_length_m(points: Sequence[Point]) -> float:
    """Return a polyline's length in metres.

    Parameters
    ----------
    points : sequence of (float, float)
        The vertices.

    Returns
    -------
    float
        The sum of the segments' lengths (exactly rounded).

    Spec: Work Order 6c, B1.
    """
    return math.fsum(_length(a, b) for a, b in pairwise(points))
