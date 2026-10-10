"""Crew travel between any two sites: by road, then off road to a line (§4.5, D6).

The engine asks for the legs of a trip, not its hours, so relaxing a speed or the
mobilisation delay sets that part to zero (D11):
- **road km:** from each end to its nearest road point (a facility's access leg, driven), and
  along the roads between them;
- **off-road km:** from the road to a line's failure point, walked and carried;
- **by sea:** the two ends lie on landmasses no road joins; the outlying-island mobilisation
  delay covers the crossing.

Only +, -, x, / and sqrt are used.

Spec: structure v0.9 §4.3b (repair travel) and §4.5 (repair and crews); Work Order 7, D4.
"""

import math
from dataclasses import dataclass, field
from typing import Protocol

from swm.stages.layers import LayersResult
from swm.stages.roads import RoadMap, RoadPoint
from swm.stages.terrain import TerrainResult

Point = tuple[float, float]
M_PER_KM = 1000.0


@dataclass(frozen=True)
class Site:
    """Where a crew is or goes: a point, and whether it lies off the roads on a line."""

    point: Point
    on_line: bool = False


@dataclass(frozen=True)
class Legs:
    """The parts of one trip."""

    road_km: float
    offroad_km: float
    by_sea: bool


class LegFinder(Protocol):
    """Finds the legs of a trip between two sites."""

    def __call__(self, start: Site, end: Site) -> Legs:
        """Return the legs from ``start`` to ``end``."""
        ...


def straight_legs(start: Site, end: Site) -> Legs:
    """Return a straight road trip between two sites: for constructed worlds in tests.

    Parameters
    ----------
    start, end : Site
        The two ends.

    Returns
    -------
    Legs
        The straight-line distance as road km; nothing off road; never by sea.

    Spec: Work Order 7, F2 and F5 (constructed cases).
    """
    return Legs(_distance(start.point, end.point) / M_PER_KM, 0.0, False)


@dataclass
class RoadLegs:
    """Trips over the world's roads, remembered once found (deterministic)."""

    roads: RoadMap
    _feet: dict[Point, RoadPoint | None] = field(default_factory=dict)
    _trips: dict[tuple[Site, Site], Legs] = field(default_factory=dict)

    @classmethod
    def of(cls, terrain: TerrainResult, layers: LayersResult) -> "RoadLegs":
        """Return the leg finder for a world's roads."""
        return cls(RoadMap(terrain, layers))

    def __call__(self, start: Site, end: Site) -> Legs:
        """Return the legs from ``start`` to ``end``, by road and then off road."""
        key = (start, end)
        if key not in self._trips:
            self._trips[key] = self._find(start, end)
        return self._trips[key]

    def _foot(self, point: Point) -> RoadPoint | None:
        if point not in self._feet:
            self._feet[point] = self.roads.nearest(point)
        return self._feet[point]

    def _find(self, start: Site, end: Site) -> Legs:
        if start.point == end.point:
            return Legs(0.0, 0.0, False)
        a, b = self._foot(start.point), self._foot(end.point)
        route = None if a is None or b is None else self.roads.route(a, b)
        if a is None or b is None or route is None:
            # CHOICE: two sites no road joins are a sea trip: the straight distance at road
            # speed plus the outlying-island mobilisation delay.
            return Legs(_distance(start.point, end.point) / M_PER_KM, 0.0, True)
        road_m, offroad_m = route[1], 0.0
        for foot, site in ((a, start), (b, end)):
            if site.on_line:
                offroad_m += foot.offroad_m
            else:
                road_m += foot.offroad_m
        return Legs(road_m / M_PER_KM, offroad_m / M_PER_KM, False)


def _distance(a: Point, b: Point) -> float:
    return math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]))
