"""Terrain stage: the ground of a spine island.

Builds elevation, coastline, drainage, land cover and urban extents from the terrain section of a
resolved recipe and the terrain streams. World-building arithmetic uses only +, -, *, / and sqrt,
elementwise, so the ground is the same bytes on every platform (CLAUDE.md §4).

Coordinates are local metres from the domain origin at the south-west corner, x east and y north.
Row 0 of every array is the northern edge. They are tied to no real place (open decision 9).
"""

import hashlib
import heapq
from collections import deque
from dataclasses import dataclass
from enum import IntEnum

import numpy as np
from numpy.typing import NDArray

from swm import rng
from swm.recipe.schema import MapType, Terrain, TerrainCharacter, UrbanPattern

# CHOICE: a fixed 256 x 256 grid for every area in Phase 1; revisited at scale.
GRID_CELLS = 256
"""Cells per side of the square domain. CHOICE: fixed for Phase 1; revisited at scale."""

MAX_ELEVATION_AT_100_M = 4_000.0
"""Highest elevation at mountainous = 100, in m.

placeholder (open decision: realism ranges), anchored on Taiwan's highest peak, about 3,950 m.
"""

TERRAIN_STREAM_PATHS = (
    "terrain/elevation",
    "terrain/coastline",
    "terrain/drainage",
    "terrain/land_cover",
    "terrain/urban_extents",
)

# D8 neighbour offsets as (row, column); a flow direction is an index into this tuple.
D8_OFFSETS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
SQRT_2 = 2.0**0.5


class CoverClass(IntEnum):
    """Land-cover class per cell. Sea cells carry SEA."""

    SEA = 0
    OPEN = 1
    URBAN = 2
    FOREST = 3
    WETLAND = 4
    BARREN = 5


# CHOICE: every mapping from a character index or shape setting to a stage parameter below.
@dataclass(frozen=True)
class TerrainMappings:
    """How each character index and shape setting maps to the stage's parameters.

    Every value is a CHOICE (Work Order 2, A7), reviewed by the design side against the preview.
    Lengths marked "domain" are fractions of the domain side; "cells" are grid cells.
    """

    spine_control_points: int = 5
    """Control points of the spine spline (count)."""
    spine_start_v: float = 0.14
    """Northern end of the spine (domain)."""
    spine_end_v: float = 0.86
    """Southern end of the spine (domain)."""
    spine_lateral_jitter: float = 0.05
    """Largest east-west offset of a control point from the centre line (domain)."""
    spine_samples_per_segment: int = 16
    """Polyline samples per spline segment (count)."""
    island_half_width: float = 0.12
    """Distance from spine to coast at the island's middle (domain)."""
    end_half_width_share: float = 0.35
    """Half-width at the spine's ends, as a share of the middle half-width (ratio)."""
    coast_noise_at_0: float = 0.04
    """Shoreline noise amplitude at coastline complexity 0 (share of the half-width)."""
    coast_noise_at_100: float = 0.50
    """Shoreline noise amplitude at coastline complexity 100 (share of the half-width)."""
    coast_noise_lattice_cells: int = 16
    """Coarsest lattice spacing of the shoreline noise (cells)."""
    coast_noise_octaves: int = 4
    """Octaves of shoreline noise (count)."""
    relief_share: float = 0.60
    """Share of the ridge profile that noise can remove (ratio)."""
    relief_noise_lattice_cells: int = 16
    """Coarsest lattice spacing of the relief noise (cells)."""
    relief_noise_octaves: int = 5
    """Octaves of relief noise (count)."""
    border_cells: int = 4
    """Sea margin kept clear at the domain edge (cells)."""
    outlying_island_radius_min_cells: int = 2
    """Smallest outlying-island radius (cells)."""
    outlying_island_radius_max_cells: int = 4
    """Largest outlying-island radius (cells)."""
    outlying_island_gap_cells: int = 3
    """Open water kept between an outlying island and any other land (cells)."""
    outlying_island_peak_share: float = 0.15
    """Outlying-island peak as a share of the maximum elevation (ratio)."""
    outlying_island_attempts: int = 5_000
    """Placement attempts before the stage reports failure (count)."""
    river_threshold_share_at_100: float = 0.004
    """Upstream area that starts a river at river density 100 (share of land cells)."""
    river_threshold_min_cells: int = 3
    """Smallest upstream area that starts a river (cells)."""
    lowland_share: float = 0.15
    """Lowland: ground at or below this share of the island's highest point (ratio)."""
    flat_slope: float = 0.06
    """Flat ground: slope at or below this (m/m)."""
    near_water_cells: int = 6
    """Near water: within this distance of the coast or a river (cells, chessboard)."""
    wetland_max_share: float = 0.30
    """Wetland share of land at lowland and wetland 100 (ratio)."""
    barren_high_share: float = 0.80
    """High barren ground: at or above this share of the island's highest point (ratio)."""
    barren_steep_slope: float = 0.45
    """Steep barren ground: slope at or above this, when also high (m/m)."""
    dry_barren_max_share: float = 0.40
    """Barren share of land added by aridity at 100 (ratio)."""
    forest_max_share: float = 0.75
    """Forest share of land at forested 100 and aridity 0 (ratio)."""
    forest_aridity_loss: float = 0.80
    """Share of the forest target removed at aridity 100 (ratio)."""
    forest_noise_lattice_cells: int = 8
    """Coarsest lattice spacing of forest patchiness (cells)."""
    urban_max_share: float = 0.20
    """Urban share of land at urban density 100 (ratio)."""
    several_cities_min: int = 3
    """Fewest cities under 'several cities' (count)."""
    several_cities_max: int = 5
    """Most cities under 'several cities' (count)."""
    dispersed_towns: int = 12
    """Towns under 'dispersed towns' (count)."""
    city_spacing_cells: int = 10
    """Least distance between city centres (cells, chessboard)."""
    town_spacing_cells: int = 5
    """Least distance between dispersed-town centres (cells, chessboard)."""


TERRAIN_MAPPINGS = TerrainMappings()
"""The mappings in force. CHOICE: every value; see ``TerrainMappings``."""


@dataclass(frozen=True)
class TerrainStreams:
    """The five terrain streams. The stage can reach no other stream."""

    elevation: np.random.Generator
    coastline: np.random.Generator
    drainage: np.random.Generator
    land_cover: np.random.Generator
    urban_extents: np.random.Generator


@dataclass(frozen=True)
class Grid:
    """The square domain."""

    cells: int
    """Cells per side."""
    cell_size_m: float
    """Side of one cell, in m."""
    origin_m: tuple[float, float]
    """Domain origin (x, y) in local metres: the south-west corner."""


@dataclass(frozen=True)
class City:
    """One urban extent. Used for siting only; not a population or demand field."""

    city_id: int
    centre_row: int
    centre_column: int
    cell_count: int


@dataclass(frozen=True)
class TerrainStatistics:
    """Realised statistics of the ground."""

    land_area_km2: float
    max_elevation_m: float
    river_length_km: float
    cover_shares: dict[str, float]
    island_count: int
    city_count: int


@dataclass(frozen=True)
class TerrainResult:
    """The terrain stage's output. Arrays are read-only, indexed [row, column], row 0 north."""

    grid: Grid
    elevation_dm: NDArray[np.int32]
    land: NDArray[np.bool_]
    flow_direction: NDArray[np.int8]
    flow_accumulation: NDArray[np.int32]
    river: NDArray[np.bool_]
    land_cover: NDArray[np.uint8]
    urban_id: NDArray[np.int16]
    cities: tuple[City, ...]
    statistics: TerrainStatistics


def terrain_streams(root_seed: int, terrain_seed: int) -> TerrainStreams:
    """Return the terrain streams, and only those.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.
    terrain_seed : int
        The recipe's terrain seed.

    Returns
    -------
    TerrainStreams
        One generator per ``terrain/*`` path.

    Spec: structure v0.3 §3 (independent random streams); Work Order 2, A1.
    """
    generators = [rng.stream(root_seed, path, terrain_seed) for path in TERRAIN_STREAM_PATHS]
    return TerrainStreams(*generators)


def build_terrain(terrain: Terrain, streams: TerrainStreams) -> TerrainResult:
    """Build the ground of a spine island.

    Parameters
    ----------
    terrain : Terrain
        The resolved recipe's terrain section; ``area_km2`` is the target land area, in km².
    streams : TerrainStreams
        The terrain streams.

    Returns
    -------
    TerrainResult
        Elevation, land mask, drainage, land cover, urban extents and realised statistics.

    Spec: structure v0.3 §4.1; Work Order 2, A2-A9.
    """
    if terrain.map_type != MapType.SPINE_ISLAND:
        raise ValueError(f"map type {terrain.map_type} is not built yet; it arrives in Phase 5")
    if terrain.area_km2 is None:
        raise ValueError("build_terrain needs a resolved recipe: terrain.area_km2 is not set")
    mappings = TERRAIN_MAPPINGS
    character = terrain.character
    max_elevation_m = character.mountainous / 100 * MAX_ELEVATION_AT_100_M

    field, spine_elevation = _spine_island(character.coastline_complexity, streams, mappings)
    land = _single_landmass(field > 0, mappings.border_cells)
    elevation_m = np.where(land, max_elevation_m * spine_elevation, 0.0)
    land, elevation_m = _add_outlying_islands(
        land, elevation_m, character.outlying_islands, max_elevation_m, streams.coastline, mappings
    )
    elevation_dm = _quantise_dm(elevation_m, land)
    land_cells = int(np.count_nonzero(land))
    cell_size_m = (terrain.area_km2 * 1_000_000 / land_cells) ** 0.5

    flow_direction, flow_accumulation = _drainage(elevation_dm, land)
    river = _rivers(flow_accumulation, land, character.river_density, mappings)
    slope = _slope(elevation_dm, cell_size_m)
    water_distance = _chessboard_distance(~land | river, mappings.near_water_cells + 1)
    urban_id, cities = _urban_extents(
        land, elevation_dm, slope, water_distance, character.urban_density,
        terrain.urban_pattern, streams.urban_extents, mappings,
    )  # fmt: skip
    land_cover = _land_cover(
        land, elevation_dm, slope, water_distance, urban_id, character, streams.land_cover,
        mappings,
    )  # fmt: skip
    grid = Grid(GRID_CELLS, cell_size_m, (0.0, 0.0))
    statistics = _statistics(grid, elevation_dm, land, river, flow_direction, land_cover, cities)
    return TerrainResult(
        grid=grid,
        elevation_dm=_frozen(elevation_dm),
        land=_frozen(land),
        flow_direction=_frozen(flow_direction),
        flow_accumulation=_frozen(flow_accumulation),
        river=_frozen(river),
        land_cover=_frozen(land_cover),
        urban_id=_frozen(urban_id),
        cities=cities,
        statistics=statistics,
    )


def statistics_record(result: TerrainResult) -> dict[str, object]:
    """Return the realised statistics as plain data, in a fixed key order.

    Parameters
    ----------
    result : TerrainResult
        The terrain stage's output.

    Returns
    -------
    dict
        Statistics, rounded to fixed decimals, ready for canonical YAML.

    Spec: Work Order 2, A9 and A11.
    """
    stats = result.statistics
    return {
        "grid_cells": result.grid.cells,
        "cell_size_m": round(result.grid.cell_size_m, 3),
        "land_area_km2": stats.land_area_km2,
        "max_elevation_m": stats.max_elevation_m,
        "river_length_km": stats.river_length_km,
        "island_count": stats.island_count,
        "city_count": stats.city_count,
        "cover_shares": dict(stats.cover_shares),
    }


def array_hashes(result: TerrainResult) -> list[tuple[str, str]]:
    """Return the SHA-256 of every array's bytes, in a fixed order and byte layout.

    Parameters
    ----------
    result : TerrainResult
        The terrain stage's output.

    Returns
    -------
    list of (str, str)
        (array name, hex digest), little-endian, C order.

    Spec: CLAUDE.md §7 (identity check); Work Order 2, A11.
    """
    cities = np.array(
        [[c.city_id, c.centre_row, c.centre_column, c.cell_count] for c in result.cities],
        dtype="<i4",
    ).reshape(-1, 4)
    arrays = (
        ("elevation_dm", result.elevation_dm.astype("<i4")),
        ("land", result.land.astype("u1")),
        ("flow_direction", result.flow_direction.astype("i1")),
        ("flow_accumulation", result.flow_accumulation.astype("<i4")),
        ("river", result.river.astype("u1")),
        ("land_cover", result.land_cover.astype("u1")),
        ("urban_id", result.urban_id.astype("<i2")),
        ("cities", cities),
    )
    return [
        (name, hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest())
        for name, array in arrays
    ]


# --- Shape ----------------------------------------------------------------------------------


def _spine_island(
    coastline_complexity: int, streams: TerrainStreams, mappings: TerrainMappings
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return the land field (land where positive) and the unit ridge profile (0-1)."""
    spine = _spine_polyline(streams.elevation, mappings)
    distance, along = _distance_to_polyline(spine)
    taper = mappings.end_half_width_share + (1 - mappings.end_half_width_share) * 4 * along * (
        1 - along
    )
    half_width = mappings.island_half_width * taper
    coast_amplitude = mappings.coast_noise_at_0 + (
        mappings.coast_noise_at_100 - mappings.coast_noise_at_0
    ) * (coastline_complexity / 100)
    coast_noise = _value_noise(
        _draw_seed(streams.coastline),
        mappings.coast_noise_lattice_cells,
        mappings.coast_noise_octaves,
    )
    field = 1 - distance / half_width + coast_amplitude * (2 * coast_noise - 1)
    relief = _value_noise(
        _draw_seed(streams.elevation),
        mappings.relief_noise_lattice_cells,
        mappings.relief_noise_octaves,
    )
    shape = np.clip(field, 0.0, 1.0)
    profile = shape * shape * ((1 - mappings.relief_share) + mappings.relief_share * relief)
    return field, profile


def _spine_polyline(stream: np.random.Generator, mappings: TerrainMappings) -> NDArray[np.float64]:
    """Return points (v, u) along a Catmull-Rom spline through jittered control points."""
    count = mappings.spine_control_points
    v = np.linspace(mappings.spine_start_v, mappings.spine_end_v, count)
    jitter = stream.random(count)
    u = 0.5 + mappings.spine_lateral_jitter * (2 * jitter - 1)
    control = np.column_stack([v, u])
    padded = np.vstack([2 * control[0] - control[1], control, 2 * control[-1] - control[-2]])
    t = np.arange(mappings.spine_samples_per_segment) / mappings.spine_samples_per_segment
    t2, t3 = t * t, t * t * t
    pieces = []
    for i in range(count - 1):
        p0, p1, p2, p3 = padded[i], padded[i + 1], padded[i + 2], padded[i + 3]
        # Catmull-Rom basis: a cubic polynomial through p1 and p2.
        pieces.append(
            0.5
            * (
                np.outer(2 * np.ones_like(t), p1)
                + np.outer(t, p2 - p0)
                + np.outer(t2, 2 * p0 - 5 * p1 + 4 * p2 - p3)
                + np.outer(t3, 3 * p1 - p0 - 3 * p2 + p3)
            )
        )
    pieces.append(control[-1:])
    return np.vstack(pieces)


def _distance_to_polyline(
    points: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return each cell centre's distance to the polyline and its position along it (0-1)."""
    centres = (np.arange(GRID_CELLS) + 0.5) / GRID_CELLS
    v = centres[:, None] * np.ones((1, GRID_CELLS))
    u = np.ones((GRID_CELLS, 1)) * centres[None, :]
    best = np.full((GRID_CELLS, GRID_CELLS), np.inf)
    along = np.zeros((GRID_CELLS, GRID_CELLS))
    segments = len(points) - 1
    for index in range(segments):
        (av, au), (bv, bu) = points[index], points[index + 1]
        dv, du = bv - av, bu - au
        length2 = dv * dv + du * du
        t = np.clip(((v - av) * dv + (u - au) * du) / length2, 0.0, 1.0)
        ev, eu = v - (av + t * dv), u - (au + t * du)
        distance2 = ev * ev + eu * eu
        closer = distance2 < best
        best = np.where(closer, distance2, best)
        along = np.where(closer, (index + t) / segments, along)
    return np.sqrt(best), along


def _single_landmass(land: NDArray[np.bool_], border_cells: int) -> NDArray[np.bool_]:
    """Keep the largest landmass, clear the border, and turn enclosed water into land."""
    land = land.copy()
    land[:border_cells, :] = land[-border_cells:, :] = False
    land[:, :border_cells] = land[:, -border_cells:] = False
    labels, sizes = _label_land(land)
    if not sizes:
        raise ValueError("the spine island has no land at these settings")
    largest = 1 + max(range(len(sizes)), key=lambda i: (sizes[i], -i))
    main = labels == largest
    # CHOICE: water enclosed by the island becomes land; Phase 1 has no lakes or lagoons.
    return ~_open_sea(~main)


def _add_outlying_islands(
    land: NDArray[np.bool_],
    elevation_m: NDArray[np.float64],
    count: int,
    max_elevation_m: float,
    stream: np.random.Generator,
    mappings: TerrainMappings,
) -> tuple[NDArray[np.bool_], NDArray[np.float64]]:
    """Add exactly ``count`` small islands, each clear of all other land."""
    land, elevation_m = land.copy(), elevation_m.copy()
    margin = mappings.border_cells + mappings.outlying_island_radius_max_cells
    placed = attempts = 0
    while placed < count:
        attempts += 1
        if attempts > mappings.outlying_island_attempts:
            raise ValueError(f"could not place {count} outlying islands clear of other land")
        radius = int(
            stream.integers(
                mappings.outlying_island_radius_min_cells,
                mappings.outlying_island_radius_max_cells + 1,
            )
        )
        row, column = (int(value) for value in stream.integers(margin, GRID_CELLS - margin, 2))
        reach = radius + mappings.outlying_island_gap_cells
        window = land[row - reach : row + reach + 1, column - reach : column + reach + 1]
        if window.any():
            continue
        rows = np.arange(-radius, radius + 1)
        distance2 = rows[:, None] * rows[:, None] + rows[None, :] * rows[None, :]
        disc = distance2 <= radius * radius
        peak = mappings.outlying_island_peak_share * max_elevation_m
        cone = peak * (1 - np.sqrt(distance2) / (radius + 1))
        box = (slice(row - radius, row + radius + 1), slice(column - radius, column + radius + 1))
        land[box] |= disc
        elevation_m[box] = np.where(disc, cone, elevation_m[box])
        placed += 1
    return land, elevation_m


def _quantise_dm(elevation_m: NDArray[np.float64], land: NDArray[np.bool_]) -> NDArray[np.int32]:
    decimetres = np.floor(elevation_m * 10 + 0.5).astype(np.int32)
    return np.where(land, decimetres, 0).astype(np.int32)


# --- Drainage -------------------------------------------------------------------------------


def _drainage(
    elevation_dm: NDArray[np.int32], land: NDArray[np.bool_]
) -> tuple[NDArray[np.int8], NDArray[np.int32]]:
    """Return D8 flow directions (-1 at sea) and flow accumulation in cells (0 at sea)."""
    filled, parent, order = _priority_flood(elevation_dm, land)
    direction = np.full(land.size, -1, dtype=np.int8)
    downstream = np.full(land.size, -1, dtype=np.int64)
    offsets = [dr * GRID_CELLS + dc for dr, dc in D8_OFFSETS]
    for cell in order:
        best_code, best_score = -1, 0
        for code, offset in enumerate(offsets):
            drop = int(filled[cell] - filled[cell + offset])
            # Steepest descent: compare drop / distance squared, exactly in integers.
            score = drop * drop * (2 if code in (1, 3, 4, 6) else 1) if drop > 0 else 0
            if score > best_score:
                best_code, best_score = code, score
        if best_code < 0:
            best_code = offsets.index(parent[cell] - cell)
        direction[cell] = best_code
        downstream[cell] = cell + offsets[best_code]
    accumulation = np.where(land.ravel(), 1, 0).astype(np.int32)
    for cell in reversed(order):
        target = downstream[cell]
        if land.flat[target]:
            accumulation[target] += accumulation[cell]
    shape = land.shape
    return direction.reshape(shape), accumulation.reshape(shape)


def _priority_flood(
    elevation_dm: NDArray[np.int32], land: NDArray[np.bool_]
) -> tuple[NDArray[np.int64], NDArray[np.int64], list[int]]:
    """Fill depressions from the sea inward; ties are broken by cell index."""
    flat_land = land.ravel()
    filled = elevation_dm.ravel().astype(np.int64)
    parent = np.full(flat_land.size, -1, dtype=np.int64)
    visited = ~flat_land
    offsets = [dr * GRID_CELLS + dc for dr, dc in D8_OFFSETS]
    heap: list[tuple[int, int]] = []
    coast = land & _dilate(~land)
    for coast_cell in np.flatnonzero(coast):
        start = int(coast_cell)
        parent[start] = next(start + o for o in offsets if not flat_land[start + o])
        visited[start] = True
        heap.append((int(filled[start]), start))
    heapq.heapify(heap)
    order: list[int] = []
    while heap:
        level, cell = heapq.heappop(heap)
        order.append(cell)
        for offset in offsets:
            neighbour = cell + offset
            if not visited[neighbour]:
                visited[neighbour] = True
                filled[neighbour] = max(int(filled[neighbour]), level)
                parent[neighbour] = cell
                heapq.heappush(heap, (int(filled[neighbour]), neighbour))
    return filled, parent, order


def _rivers(
    accumulation: NDArray[np.int32],
    land: NDArray[np.bool_],
    river_density: int,
    mappings: TerrainMappings,
) -> NDArray[np.bool_]:
    """Return river cells: land whose upstream area reaches the threshold for the density."""
    if river_density == 0:
        return np.zeros_like(land)
    land_cells = int(np.count_nonzero(land))
    threshold = mappings.river_threshold_share_at_100 * land_cells * 100 / river_density
    threshold_cells = max(mappings.river_threshold_min_cells, int(threshold + 0.5))
    return land & (accumulation >= threshold_cells)


# --- Land cover and urban extents -----------------------------------------------------------


def _urban_extents(
    land: NDArray[np.bool_],
    elevation_dm: NDArray[np.int32],
    slope: NDArray[np.float64],
    water_distance: NDArray[np.int64],
    urban_density: int,
    pattern: UrbanPattern,
    stream: np.random.Generator,
    mappings: TerrainMappings,
) -> tuple[NDArray[np.int16], tuple[City, ...]]:
    """Site cities on flat lowland near water and grow each to its share of the urban area."""
    urban_id = np.full(land.shape, -1, dtype=np.int16)
    target = int(np.count_nonzero(land) * mappings.urban_max_share * urban_density / 100 + 0.5)
    sizes = _city_sizes(target, pattern, stream, mappings)
    if not sizes:
        return urban_id, ()
    spacing = (
        mappings.town_spacing_cells
        if pattern == UrbanPattern.DISPERSED_TOWNS
        else mappings.city_spacing_cells
    )
    suitable = _lowland(land, elevation_dm, mappings) & (slope <= mappings.flat_slope)
    suitable &= water_distance <= mappings.near_water_cells
    score = _site_score(elevation_dm, slope, water_distance, mappings) + 0.1 * stream.random(
        land.shape
    )
    centres = _pick_centres(suitable, land, score, len(sizes), spacing)
    nearest = _nearest_centre(centres)
    cities = []
    for city_id, ((row, column), size) in enumerate(zip(centres, sizes, strict=True)):
        # CHOICE: a city grows only over land nearer its own centre, so none swallows another.
        cells = _grow(land & (nearest == city_id), row, column, size)
        urban_id.flat[cells] = city_id
        cities.append(City(city_id, row, column, len(cells)))
    return urban_id, tuple(cities)


def _nearest_centre(centres: list[tuple[int, int]]) -> NDArray[np.int64]:
    """Return, per cell, the index of the nearest centre; ties go to the lower index."""
    rows = np.arange(GRID_CELLS, dtype=np.int64)[:, None]
    columns = np.arange(GRID_CELLS, dtype=np.int64)[None, :]
    best = np.full((GRID_CELLS, GRID_CELLS), np.iinfo(np.int64).max)
    nearest = np.zeros((GRID_CELLS, GRID_CELLS), dtype=np.int64)
    for index, (row, column) in enumerate(centres):
        distance2 = (rows - row) * (rows - row) + (columns - column) * (columns - column)
        closer = distance2 < best
        best = np.where(closer, distance2, best)
        nearest = np.where(closer, index, nearest)
    return nearest


def _city_sizes(
    target: int, pattern: UrbanPattern, stream: np.random.Generator, mappings: TerrainMappings
) -> list[int]:
    """Split the urban cell target across cities: rank-size for several, even for dispersed."""
    if target == 0:
        return []
    if pattern == UrbanPattern.ONE_DOMINANT_CITY:
        return [target]
    if pattern == UrbanPattern.SEVERAL_CITIES:
        count = int(stream.integers(mappings.several_cities_min, mappings.several_cities_max + 1))
        # CHOICE: rank-size rule; the k-th city gets a share proportional to 1/k.
        weights = [1 / rank for rank in range(1, count + 1)]
        total = sum(weights)
        sizes = [int(target * weight / total + 0.5) for weight in weights]
        sizes[0] += target - sum(sizes)
    else:
        count = min(mappings.dispersed_towns, target)
        sizes = [target // count + (1 if i < target % count else 0) for i in range(count)]
    return [size for size in sizes if size > 0]


def _pick_centres(
    suitable: NDArray[np.bool_],
    land: NDArray[np.bool_],
    score: NDArray[np.float64],
    count: int,
    spacing: int,
) -> list[tuple[int, int]]:
    """Take the best-scoring cells, keeping centres apart; fall back to any land if needed."""
    # CHOICE: if flat lowland near water cannot hold every city, the rest go on the best land.
    centres: list[tuple[int, int]] = []
    for pool in (suitable, land):
        candidates = np.flatnonzero(pool.ravel())
        for cell in candidates[np.argsort(score.ravel()[candidates], kind="stable")]:
            row, column = divmod(int(cell), GRID_CELLS)
            if all(max(abs(row - r), abs(column - c)) >= spacing for r, c in centres):
                centres.append((row, column))
                if len(centres) == count:
                    return centres
    raise ValueError(f"could not site {count} urban centres {spacing} cells apart")


def _grow(available: NDArray[np.bool_], row: int, column: int, size: int) -> list[int]:
    """Grow a compact footprint from a centre over available land, nearest cells first."""
    start = row * GRID_CELLS + column
    heap = [(0, start)]
    seen = {start}
    cells: list[int] = []
    while heap and len(cells) < size:
        _, cell = heapq.heappop(heap)
        if not available.flat[cell]:
            continue
        cells.append(cell)
        r, c = divmod(cell, GRID_CELLS)
        for dr, dc in D8_OFFSETS:
            neighbour = (r + dr) * GRID_CELLS + (c + dc)
            if neighbour not in seen:
                seen.add(neighbour)
                distance2 = (r + dr - row) ** 2 + (c + dc - column) ** 2
                heapq.heappush(heap, (distance2, neighbour))
    return cells


def _land_cover(
    land: NDArray[np.bool_],
    elevation_dm: NDArray[np.int32],
    slope: NDArray[np.float64],
    water_distance: NDArray[np.int64],
    urban_id: NDArray[np.int16],
    character: TerrainCharacter,
    stream: np.random.Generator,
    mappings: TerrainMappings,
) -> NDArray[np.uint8]:
    """Assign one cover class per land cell: urban, wetland, barren, forest, then open."""
    # CHOICE: classes claim cells in this order, each taking its best-ranked remaining cells.
    cover = np.where(land, CoverClass.OPEN, CoverClass.SEA).astype(np.uint8)
    cover[urban_id >= 0] = CoverClass.URBAN
    land_cells = int(np.count_nonzero(land))
    peak_dm = max(int(elevation_dm.max()), 1)
    height = elevation_dm / peak_dm

    wet_ok = _lowland(land, elevation_dm, mappings) & (slope <= mappings.flat_slope)
    wet_ok &= water_distance <= mappings.near_water_cells
    wet_target = _share_to_cells(
        land_cells, mappings.wetland_max_share, character.lowland_and_wetland
    )
    _assign(
        cover,
        wet_ok,
        height + water_distance / mappings.near_water_cells,
        wet_target,
        CoverClass.WETLAND,
    )

    high = (height >= mappings.barren_high_share) & (slope >= mappings.barren_steep_slope)
    cover[(cover == CoverClass.OPEN) & high & (elevation_dm > 0)] = CoverClass.BARREN

    forest_share = mappings.forest_max_share * (
        1 - mappings.forest_aridity_loss * character.aridity / 100
    )
    forest_target = _share_to_cells(land_cells, forest_share, character.forested)
    patchiness = _value_noise(_draw_seed(stream), mappings.forest_noise_lattice_cells, 3)
    slope_term = np.clip(slope / mappings.barren_steep_slope, 0.0, 1.0)
    mid_height = 1 - 2 * np.abs(height - 0.45)
    forest_score = 0.25 * slope_term + 0.25 * mid_height + 0.5 * patchiness
    _assign(cover, cover == CoverClass.OPEN, -forest_score, forest_target, CoverClass.FOREST)

    dry_target = _share_to_cells(land_cells, mappings.dry_barren_max_share, character.aridity)
    dryness = water_distance / mappings.near_water_cells + height
    _assign(cover, cover == CoverClass.OPEN, -dryness, dry_target, CoverClass.BARREN)
    return cover


def _assign(
    cover: NDArray[np.uint8],
    eligible: NDArray[np.bool_],
    rank_key: NDArray[np.float64],
    target: int,
    cover_class: CoverClass,
) -> None:
    """Give ``cover_class`` to up to ``target`` eligible open cells with the lowest key."""
    candidates = np.flatnonzero((eligible & (cover == CoverClass.OPEN)).ravel())
    chosen = candidates[np.argsort(rank_key.ravel()[candidates], kind="stable")][:target]
    cover.flat[chosen] = cover_class


def _share_to_cells(land_cells: int, max_share: float, index: int) -> int:
    return int(land_cells * max_share * index / 100 + 0.5)


def _lowland(
    land: NDArray[np.bool_], elevation_dm: NDArray[np.int32], mappings: TerrainMappings
) -> NDArray[np.bool_]:
    peak_dm = int(elevation_dm.max())
    return land & (elevation_dm <= mappings.lowland_share * peak_dm)


def _site_score(
    elevation_dm: NDArray[np.int32],
    slope: NDArray[np.float64],
    water_distance: NDArray[np.int64],
    mappings: TerrainMappings,
) -> NDArray[np.float64]:
    """Lower is better: low, flat and close to the coast or a river."""
    peak_dm = max(int(elevation_dm.max()), 1)
    return (
        elevation_dm / peak_dm
        + slope / mappings.flat_slope
        + water_distance / mappings.near_water_cells
    )


# --- Grid helpers ---------------------------------------------------------------------------


def _slope(elevation_dm: NDArray[np.int32], cell_size_m: float) -> NDArray[np.float64]:
    """Return the slope magnitude in m/m from central differences."""
    elevation = np.pad(elevation_dm / 10, 1, mode="edge")
    gradient_x = (elevation[1:-1, 2:] - elevation[1:-1, :-2]) / (2 * cell_size_m)
    gradient_y = (elevation[2:, 1:-1] - elevation[:-2, 1:-1]) / (2 * cell_size_m)
    return np.sqrt(gradient_x * gradient_x + gradient_y * gradient_y)


def _dilate(mask: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Grow a mask by one cell in all eight directions."""
    padded = np.pad(mask, 1)
    grown = mask.copy()
    for dr, dc in D8_OFFSETS:
        grown |= padded[1 + dr : 1 + dr + mask.shape[0], 1 + dc : 1 + dc + mask.shape[1]]
    return grown


def _chessboard_distance(sources: NDArray[np.bool_], cap: int) -> NDArray[np.int64]:
    """Return the chessboard distance to the nearest source cell, capped at ``cap``."""
    distance = np.full(sources.shape, cap, dtype=np.int64)
    distance[sources] = 0
    reached = sources.copy()
    for step in range(1, cap):
        reached = _dilate(reached)
        distance[reached & (distance == cap)] = step
    return distance


def _open_sea(water: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Return the water connected (four ways) to the domain edge."""
    sea = np.zeros_like(water)
    sea[0, :], sea[-1, :], sea[:, 0], sea[:, -1] = (
        water[0, :],
        water[-1, :],
        water[:, 0],
        water[:, -1],
    )
    while True:
        padded = np.pad(sea, 1)
        grown = sea | padded[:-2, 1:-1] | padded[2:, 1:-1] | padded[1:-1, :-2] | padded[1:-1, 2:]
        grown &= water
        if np.array_equal(grown, sea):
            return sea
        sea = grown


def _label_land(land: NDArray[np.bool_]) -> tuple[NDArray[np.int32], list[int]]:
    """Label eight-connected landmasses 1, 2, ... in scan order; return labels and sizes."""
    labels = np.zeros(land.shape, dtype=np.int32)
    sizes: list[int] = []
    for start in np.flatnonzero(land.ravel()):
        if labels.flat[start]:
            continue
        sizes.append(0)
        label = len(sizes)
        labels.flat[start] = label
        queue = deque([int(start)])
        while queue:
            cell = queue.popleft()
            sizes[-1] += 1
            r, c = divmod(cell, GRID_CELLS)
            for dr, dc in D8_OFFSETS:
                rr, cc = r + dr, c + dc
                if 0 <= rr < GRID_CELLS and 0 <= cc < GRID_CELLS:
                    neighbour = rr * GRID_CELLS + cc
                    if land.flat[neighbour] and not labels.flat[neighbour]:
                        labels.flat[neighbour] = label
                        queue.append(neighbour)
    return labels, sizes


# --- Value noise ----------------------------------------------------------------------------

_HASH_ROW = np.uint64(0x9E3779B97F4A7C15)
_HASH_COLUMN = np.uint64(0xC2B2AE3D27D4EB4F)
_MIX_1 = np.uint64(0xBF58476D1CE4E5B9)
_MIX_2 = np.uint64(0x94D049BB133111EB)
_UNIT = 2.0**-53


def _draw_seed(stream: np.random.Generator) -> int:
    return int(stream.integers(0, 2**63))


def _lattice_values(
    rows: NDArray[np.int64], columns: NDArray[np.int64], seed: int
) -> NDArray[np.float64]:
    """Hash integer lattice points to uniform values in [0, 1) (splitmix64 finaliser)."""
    value = (rows.astype(np.uint64) * _HASH_ROW) ^ (columns.astype(np.uint64) * _HASH_COLUMN)
    value ^= np.uint64(seed)
    value ^= value >> np.uint64(30)
    value *= _MIX_1
    value ^= value >> np.uint64(27)
    value *= _MIX_2
    value ^= value >> np.uint64(31)
    return (value >> np.uint64(11)).astype(np.float64) * _UNIT


def _value_noise(seed: int, lattice_cells: int, octaves: int) -> NDArray[np.float64]:
    """Multi-octave value noise in [0, 1) on an integer-hash lattice, smoothstep-interpolated."""
    total = np.zeros((GRID_CELLS, GRID_CELLS))
    amplitude, norm, step = 1.0, 0.0, lattice_cells
    for octave in range(octaves):
        total += amplitude * _lattice_octave((seed + octave * 0x632BE5AB) % 2**64, max(step, 1))
        norm += amplitude
        amplitude, step = amplitude / 2, step // 2
    return total / norm


def _lattice_octave(seed: int, step: int) -> NDArray[np.float64]:
    index = np.arange(GRID_CELLS, dtype=np.int64)
    base = index // step
    fraction = (index % step) / step
    smooth = fraction * fraction * (3 - 2 * fraction)
    r0, c0 = base[:, None], base[None, :]
    v00 = _lattice_values(r0, c0, seed)
    v01 = _lattice_values(r0, c0 + 1, seed)
    v10 = _lattice_values(r0 + 1, c0, seed)
    v11 = _lattice_values(r0 + 1, c0 + 1, seed)
    sr, sc = smooth[:, None], smooth[None, :]
    top = v00 + (v01 - v00) * sc
    bottom = v10 + (v11 - v10) * sc
    return top + (bottom - top) * sr


# --- Statistics -----------------------------------------------------------------------------


def _statistics(
    grid: Grid,
    elevation_dm: NDArray[np.int32],
    land: NDArray[np.bool_],
    river: NDArray[np.bool_],
    flow_direction: NDArray[np.int8],
    land_cover: NDArray[np.uint8],
    cities: tuple[City, ...],
) -> TerrainStatistics:
    """Compute realised statistics from integer counts, so they are exact on every platform."""
    land_cells = int(np.count_nonzero(land))
    cell_area_km2 = grid.cell_size_m * grid.cell_size_m / 1_000_000
    river_codes = flow_direction[river]
    cardinal = int(np.count_nonzero(np.isin(river_codes, (1, 3, 4, 6))))
    diagonal = int(river_codes.size) - cardinal
    shares = {
        cover.name.lower(): round(int(np.count_nonzero(land_cover == cover)) / land_cells, 6)
        for cover in CoverClass
        if cover != CoverClass.SEA
    }
    _, sizes = _label_land(land)
    return TerrainStatistics(
        land_area_km2=round(land_cells * cell_area_km2, 3),
        max_elevation_m=int(elevation_dm.max()) / 10,
        river_length_km=round((cardinal + diagonal * SQRT_2) * grid.cell_size_m / 1000, 3),
        cover_shares=shares,
        island_count=len(sizes),
        city_count=len(cities),
    )


def _frozen[T: np.generic](array: NDArray[T]) -> NDArray[T]:
    array = np.array(array, copy=True)
    array.flags.writeable = False
    return array
