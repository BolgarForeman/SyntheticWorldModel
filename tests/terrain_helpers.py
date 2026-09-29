"""Builders and invariant checks shared by the terrain tests."""

from typing import Any

import numpy as np

from swm.recipe.resolve import resolve
from swm.recipe.schema import Recipe
from swm.stages.terrain import (
    BASE_RELIEF_M,
    D8_OFFSETS,
    GRID_CELLS,
    MAX_ELEVATION_AT_100_M,
    TerrainResult,
    build_terrain,
    terrain_streams,
)


def build(root_seed: int = 91577, **terrain: Any) -> TerrainResult:
    """Build terrain from a terrain section given in part; character keys go in ``character``."""
    recipe = resolve(Recipe.model_validate({"root_seed": root_seed, "terrain": terrain})).recipe
    streams = terrain_streams(recipe.root_seed, recipe.terrain.terrain_seed)
    return build_terrain(recipe.terrain, streams)


def downstream(result: TerrainResult) -> np.ndarray:
    """Flat index of each cell's downstream cell; sea cells point to themselves."""
    cells = np.arange(GRID_CELLS * GRID_CELLS)
    offsets = np.array([dr * GRID_CELLS + dc for dr, dc in D8_OFFSETS])
    direction = result.flow_direction.ravel()
    return np.where(direction >= 0, cells + offsets[direction], cells)


def drains_to_sea(result: TerrainResult) -> bool:
    """True if following flow directions from every land cell ends at sea."""
    pointer = downstream(result)
    for _ in range(17):  # 2**17 steps exceed any path on a 256 x 256 grid
        pointer = pointer[pointer]
    return not result.land.ravel()[pointer].any()


def area_tolerance_km2(result: TerrainResult) -> float:
    """One cell's area times the number of perimeter cells: the quantisation allowance."""
    land = result.land
    padded = np.pad(land, 1)
    sea_neighbour = ~padded[:-2, 1:-1] | ~padded[2:, 1:-1] | ~padded[1:-1, :-2] | ~padded[1:-1, 2:]
    perimeter = int(np.count_nonzero(land & sea_neighbour))
    return perimeter * (result.grid.cell_size_m / 1000) ** 2


def elevation_bound_m(mountainous: int) -> float:
    return BASE_RELIEF_M + mountainous / 100 * (MAX_ELEVATION_AT_100_M - BASE_RELIEF_M)


def coastal(land: np.ndarray) -> np.ndarray:
    """Land cells with a sea cell among their four neighbours."""
    padded = np.pad(land, 1)
    sea_neighbour = ~padded[:-2, 1:-1] | ~padded[2:, 1:-1] | ~padded[1:-1, :-2] | ~padded[1:-1, 2:]
    return land & sea_neighbour


def coastline_index(result: TerrainResult) -> float:
    """Coastline length (land-sea cell edges) over the perimeter of a circle of equal area."""
    land = np.asarray(result.land)
    padded = np.pad(land, 1)
    neighbours = (padded[:-2, 1:-1], padded[2:, 1:-1], padded[1:-1, :-2], padded[1:-1, 2:])
    edges = sum(int(np.count_nonzero(land & ~neighbour)) for neighbour in neighbours)
    return edges / (2 * np.sqrt(np.pi * np.count_nonzero(land)))


def river_mouths_and_heads(result: TerrainResult) -> tuple[np.ndarray, np.ndarray]:
    """River mouths (flow into the sea) and heads (no river flows in), as flat masks."""
    land = result.land.ravel()
    river = result.river.ravel()
    after = downstream(result)
    mouths = river & ~land[after]
    inflow = np.bincount(after[river & ~mouths], minlength=river.size)
    return mouths, river & (inflow == 0)


def main_island_ratio(result: TerrainResult) -> float:
    """Length over width of the main island along its principal axes (test measure only)."""
    from swm.stages.terrain import _label_land

    labels, sizes = _label_land(np.asarray(result.land))
    rows, columns = np.nonzero(labels == 1 + int(np.argmax(sizes)))
    points = np.column_stack([rows, columns]).astype(float)
    points -= points.mean(axis=0)
    _, axes = np.linalg.eigh(np.cov(points.T))
    projected = points @ axes
    return float(np.ptp(projected[:, 1]) / np.ptp(projected[:, 0]))
