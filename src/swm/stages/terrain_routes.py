"""Least-cost routes over the terrain grid, for mapped power lines (structure v0.8 §4.2).

A route moves between the eight neighbours of a cell. Entering a cell costs the step's length
times (1 + slope weight x slope + height weight x elevation / peak), plus a fixed cost for each
river crossing (stepping onto a river cell from off it). Sea cells cannot be entered, so lines
follow valleys and go round mountains unless the detour costs more than the crossing.

The search is A* with the octile distance as its estimate: every step costs at least its
length, so the estimate never overstates the remaining cost and the route is least-cost. Ties
break on cell index, so the route is the same on every platform. Only +, -, x, / and sqrt.

Spec: structure v0.8 §4.2 (mapped power lines: route); Work Order 6c, A3 and A6.
"""

import heapq
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from swm.rules.registry import Registry
from swm.stages.terrain import D8_OFFSETS, GRID_CELLS, TerrainResult, _slope

M_PER_KM = 1000.0
SQRT_2 = math.sqrt(2.0)


@dataclass(frozen=True)
class RouteCost:
    """The cost of entering each cell, per km of step, and what the search reads."""

    multiplier: NDArray[np.float64]
    """1 + slope weight x slope + height weight x elevation / peak; inf at sea."""
    river: NDArray[np.bool_]
    river_crossing_km: float
    cell_km: float


def route_cost(terrain: TerrainResult, rules: Registry) -> RouteCost:
    """Return the per-cell cost the router reads, from the registry's weights.

    Parameters
    ----------
    terrain : TerrainResult
        The ground: land, elevation, rivers and cell size.
    rules : Registry
        The modeling rules in force (``layers.power_lines.route_cost``).

    Returns
    -------
    RouteCost
        The cost multiplier per cell (infinite at sea), the river mask and crossing cost.

    Spec: structure v0.8 §4.2; Work Order 6c, A3.
    """
    weights = rules.value("layers.power_lines.route_cost")
    elevation = np.asarray(terrain.elevation_dm)
    land = np.asarray(terrain.land)
    peak_dm = max(int(elevation.max()), 1)
    slope = _slope(elevation, terrain.grid.cell_size_m)
    multiplier = (
        1.0
        + float(weights["slope_weight"]) * slope
        + float(weights["height_weight"]) * (elevation / peak_dm)
    )
    return RouteCost(
        multiplier=np.where(land, multiplier, np.inf),
        river=np.asarray(terrain.river),
        river_crossing_km=float(weights["river_crossing_km"]),
        cell_km=terrain.grid.cell_size_m / M_PER_KM,
    )


def least_cost_route(cost: RouteCost, start: int, end: int) -> list[int] | None:
    """Return the cells of the least-cost route between two cells, or None if sea parts them.

    Parameters
    ----------
    cost : RouteCost
        The per-cell cost.
    start, end : int
        Flat cell indices (row x grid cells + column) of the route's ends, both on land.

    Returns
    -------
    list of int or None
        The cells from start to end inclusive; None when no land route joins them.

    Spec: structure v0.8 §4.2; Work Order 6c, A3 and A6.
    """
    multiplier = cost.multiplier.ravel()
    river = cost.river.ravel()
    end_row, end_column = divmod(end, GRID_CELLS)
    best = {start: 0.0}
    came_from: dict[int, int] = {}
    frontier = [(_estimate(start, end_row, end_column, cost.cell_km), start)]
    done: set[int] = set()
    while frontier:
        _, cell = heapq.heappop(frontier)
        if cell in done:
            continue
        if cell == end:
            return _walk_back(came_from, start, end)
        done.add(cell)
        row, column = divmod(cell, GRID_CELLS)
        for dr, dc in D8_OFFSETS:
            r, c = row + dr, column + dc
            if not (0 <= r < GRID_CELLS and 0 <= c < GRID_CELLS):
                continue
            nxt = r * GRID_CELLS + c
            if nxt in done or math.isinf(multiplier[nxt]):
                continue
            step_km = cost.cell_km * (SQRT_2 if dr and dc else 1.0)
            added = step_km * float(multiplier[nxt])
            if river[nxt] and not river[cell]:
                added += cost.river_crossing_km
            reached = best[cell] + added
            if reached < best.get(nxt, math.inf):
                best[nxt] = reached
                came_from[nxt] = cell
                priority = reached + _estimate(nxt, end_row, end_column, cost.cell_km)
                heapq.heappush(frontier, (priority, nxt))
    return None


def _estimate(cell: int, end_row: int, end_column: int, cell_km: float) -> float:
    """Octile distance to the end, in km: a lower bound on the remaining cost."""
    row, column = divmod(cell, GRID_CELLS)
    dr, dc = abs(row - end_row), abs(column - end_column)
    return cell_km * (max(dr, dc) + (SQRT_2 - 1.0) * min(dr, dc))


def _walk_back(came_from: dict[int, int], start: int, end: int) -> list[int]:
    cells = [end]
    while cells[-1] != start:
        cells.append(came_from[cells[-1]])
    cells.reverse()
    return cells


def turning_points(cells: list[int]) -> list[tuple[int, int]]:
    """Return a route's (row, column) cells where it changes direction, with both ends.

    Parameters
    ----------
    cells : list of int
        The route's flat cell indices, in order.

    Returns
    -------
    list of (int, int)
        The vertices of the route as a polyline.

    Spec: Work Order 6c, A3.
    """
    points = [divmod(cell, GRID_CELLS) for cell in cells]
    if len(points) <= 2:
        return points
    vertices = [points[0]]
    for before, here, after in zip(points, points[1:], points[2:], strict=False):
        if (here[0] - before[0], here[1] - before[1]) != (after[0] - here[0], after[1] - here[1]):
            vertices.append(here)
    vertices.append(points[-1])
    return vertices
