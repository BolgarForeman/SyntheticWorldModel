"""Storm stage: the typhoon's wind field and flood depth, per scenario, on the terrain grid.

A typhoon moves on a straight track that passes over or near the island (structure v0.7 §4.3b).
Each scenario draws its peak 10-minute wind at sea within the severity's CWA class band, its
closest approach to the island's centre, its radius of maximum wind, its heading and its
rainfall. The wind at each place is built in order:
1. the modified Rankine profile (exponent 0.5), taken at its peak over the storm's passage;
2. sea to land: land keeps 0.83 of the sea wind, the drop over the first km inland;
3. the Taiwan wind-code surface factor by land cover;
4. the mountain lee: places with the spine line between them and the track keep 0.6;
5. random variation: a smooth field from a Wendland kernel, spread 10%.

Winds are stored in m/s at 10-minute averaging. Flood depth is the scenario's flood stage (set by
its rainfall) less each cell's height above the nearest drainage.

The stage reads the terrain, the recipe and the rules, and its own streams. Everything it
produces is real but unobserved. At runtime only +, -, x, / and sqrt are used (§3).

Spec: structure v0.7 §4.3b; Work Order 6, Parts A-B; decision 0012 and its addendum.
"""

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from swm import rng
from swm.recipe.schema import Hazard, HazardSettings
from swm.rules.registry import Registry
from swm.stages.layers import LayersResult
from swm.stages.terrain import D8_OFFSETS, GRID_CELLS, CoverClass, TerrainResult, _label_land

M_PER_KM = 1000.0
CM_PER_M = 100.0

IRWIN_HALL_TERMS = 12
"""Uniform draws summed for one normal value: mean 6, variance 1 (Irwin-Hall)."""

KERNEL_RADIUS_SHARE = 0.5
"""Kernel support as a share of the correlation length. CHOICE: a kernel sum's correlation
reaches zero at twice the kernel's support, so half the length gives zero at the length."""

LATTICE_SPACING_SHARE = 0.25
"""Lattice spacing of the kernel sum as a share of the kernel support. CHOICE: four lattice
points per support radius keep the field's variance even across cells."""


@dataclass(frozen=True)
class Track:
    """One scenario's straight track and the storm that moves along it."""

    point_km: tuple[float, float]
    """The track's nearest point to the island's centre: (km east, km south) of the corner."""
    direction: tuple[float, float]
    """Unit vector of travel: (east, south) components."""
    peak_wind_m_per_s: float
    """Peak 10-minute wind at sea."""
    closest_approach_km: float
    """Distance from the island's centre to the track."""
    radius_max_wind_km: float


@dataclass(frozen=True)
class StormScenario:
    """One scenario's fields on the terrain grid."""

    index: int
    track: Track | None
    """None when there is no storm (severity 0, or the storm switched off)."""
    rain_mm: float
    flood_stage_m: float
    wind_m_per_s: NDArray[np.float64]
    flood_depth_m: NDArray[np.float64]
    lee: NDArray[np.bool_]
    inside_radius_share: float
    """Share of land cells within the radius of maximum wind of the track."""


@dataclass(frozen=True)
class StormResult:
    """The storm stage's output. Real but unobserved: never emitted."""

    severity: int
    anchor_m_per_s: float
    storm_class: str | None
    rain_rung_mm: float
    """The severity's rung on the rainfall ladder; each scenario draws around it."""
    height_above_drainage_m: NDArray[np.float64]
    scenarios: tuple[StormScenario, ...]


@dataclass(frozen=True)
class FacilityExposure:
    """What the storm brings to one node, per scenario."""

    node_id: str
    node_class: str
    height_above_drainage_m: float
    flood_threshold_m: float | None
    """Depth above grade at which the node floods out; None for classes not flood-damaged."""
    wind_m_per_s: tuple[float, ...]
    flood_depth_m: tuple[float, ...]
    """Water depth above grade."""
    floods_out: tuple[bool, ...]


@dataclass(frozen=True)
class StormStreams:
    """Each scenario's own track and variation streams."""

    track: tuple[np.random.Generator, ...]
    variation: tuple[np.random.Generator, ...]


def storm_streams(root_seed: int, scenarios: int) -> StormStreams:
    """Return the track and variation streams of each scenario.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.
    scenarios : int
        How many scenarios the recipe draws.

    Returns
    -------
    StormStreams
        One track and one variation stream per scenario, keyed by the scenario's index, so
        changing the count never moves an earlier scenario.

    Spec: Work Order 6, A1.
    """
    base = f"shared_causes/{Hazard.STORM_CORRIDOR}"
    return StormStreams(
        track=tuple(rng.stream(root_seed, f"{base}/{i}/track") for i in range(scenarios)),
        variation=tuple(rng.stream(root_seed, f"{base}/{i}/variation") for i in range(scenarios)),
    )


def build_storm(
    storm: HazardSettings,
    scenarios: int,
    mountainous: int,
    terrain: TerrainResult,
    rules: Registry,
    streams: StormStreams,
) -> StormResult:
    """Build every scenario's wind field and flood depth.

    Parameters
    ----------
    storm : HazardSettings
        The recipe's storm corridor: switched on, severity (0-100), correlation length (km).
    scenarios : int
        How many scenarios to draw.
    mountainous : int
        The recipe's terrain mountainous index (0-100); a flat island (0) has no lee.
    terrain : TerrainResult
        The ground: land, elevation, drainage, land cover, cities and the spine line.
    rules : Registry
        The modeling rules in force.
    streams : StormStreams
        The scenarios' streams.

    Returns
    -------
    StormResult
        The severity's anchor, class and rainfall rung, the height above drainage, and each
        scenario's track, rainfall, flood stage, wind (m/s, 10-minute) and flood depth (m).

    Spec: structure v0.7 §4.3b; Work Order 6, A2-A4 and B1-B2; decision 0012 addendum.
    """
    severity = storm.severity if storm.switched_on else 0
    anchor = _anchor_m_per_s(severity, rules)
    band = _class_band(anchor, rules) if severity > 0 else None
    rung = _rain_rung_mm(severity, rules)
    height = height_above_drainage_m(terrain)
    ground = _Ground(terrain, rules, has_lee=mountainous > 0)
    built = []
    for index in range(scenarios):
        if band is None:
            built.append(_calm(index, terrain))
            continue
        draw = _draw_track(band[1], band[2], anchor, rung, ground, streams.track[index])
        built.append(
            _scenario(index, draw, ground, height, storm.correlation_km, streams.variation[index])
        )
    return StormResult(
        severity=severity,
        anchor_m_per_s=anchor if severity > 0 else 0.0,
        storm_class=band[0] if band else None,
        rain_rung_mm=rung,
        height_above_drainage_m=_frozen(height),
        scenarios=tuple(built),
    )


# --- Severity and rainfall (B1) -------------------------------------------------------------


def _anchor_m_per_s(severity: int, rules: Registry) -> float:
    anchor = rules.value("storm.severity_anchor")
    return float(anchor["at_severity_0_m_per_s"]) + float(anchor["per_severity_m_per_s"]) * severity


def _class_band(anchor: float, rules: Registry) -> tuple[str, float, float]:
    """Return the CWA class whose band holds the anchor, and the band (m/s)."""
    for name, (low, high) in rules.value("storm.cwa_classes").items():
        if low <= anchor <= high:
            return str(name), float(low), float(high)
    raise ValueError(f"a peak wind of {anchor} m/s falls in no CWA typhoon class")


def _rain_rung_mm(severity: int, rules: Registry) -> float:
    if severity == 0:
        return 0.0
    for step in rules.value("storm.rainfall_mm"):
        if severity <= int(step["up_to_severity"]):
            return float(step["rain_mm"])
    raise ValueError(f"severity {severity} is above the rainfall ladder")


def flood_stage_m(rain_mm: float, rules: Registry) -> float:
    """Return the flood stage for a 24-hour rainfall: 1 m per 150 mm above 150 mm.

    Parameters
    ----------
    rain_mm : float
        The scenario's 24-hour rainfall, in mm.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    float
        The flood stage in m (300 mm gives 1 m, 450 mm 2 m, 600 mm 3 m), never below 0.

    Spec: structure v0.7 §4.3b (severity, flood); decision 0012 addendum.
    """
    stage = rules.value("storm.flood_stage_m")
    return max(0.0, (rain_mm - float(stage["zero_at_rain_mm"])) / float(stage["rain_mm_per_m"]))


# --- The ground the field reads -------------------------------------------------------------


class _Ground:
    """Cell coordinates and every factor of the field that does not depend on the track."""

    def __init__(self, terrain: TerrainResult, rules: Registry, has_lee: bool) -> None:
        self.terrain = terrain
        self.rules = rules
        self.has_lee = has_lee
        self.cell_km = terrain.grid.cell_size_m / M_PER_KM
        centres = (np.arange(GRID_CELLS) + 0.5) * self.cell_km
        self.x_km = np.ones((GRID_CELLS, 1)) * centres[None, :]
        self.y_km = centres[:, None] * np.ones((1, GRID_CELLS))
        self.land = np.asarray(terrain.land)
        self.land_cells = np.flatnonzero(self.land.ravel())
        self.surface = self._surface_and_coast()
        self.centre_km = self._island_centre_km()

    def _island_centre_km(self) -> tuple[float, float]:
        """Return the main island's centroid from integer sums of its cells (exact everywhere).

        CHOICE: "the island's centre" is the centroid of the largest landmass.
        """
        labels, sizes = _label_land(self.land)
        largest = 1 + max(range(len(sizes)), key=lambda i: (sizes[i], -i))
        rows, columns = np.nonzero(labels == largest)
        count = rows.size
        mean_column = (int(columns.astype(np.int64).sum()) + 0.5 * count) / count
        mean_row = (int(rows.astype(np.int64).sum()) + 0.5 * count) / count
        return mean_column * self.cell_km, mean_row * self.cell_km

    def _surface_and_coast(self) -> NDArray[np.float64]:
        """Sea-to-land factor times the surface factor: 1 at sea."""
        sea_to_land = self.rules.value("storm.sea_to_land")
        keep = float(sea_to_land["land_factor"])
        transition_km = float(sea_to_land["transition_km"])
        # CHOICE: the drop runs linearly with distance from the coast over the transition
        # length, so all of it has happened 1 km inland.
        share = np.minimum(
            _coast_distance_km(self.land, self.cell_km, transition_km), transition_km
        )
        coast = 1.0 - (1.0 - keep) * share / transition_km
        return np.where(self.land, coast * self._cover_factor(), 1.0)

    def _cover_factor(self) -> NDArray[np.float64]:
        factors = self.rules.value("storm.surface_factors")
        urban = np.asarray(self.terrain.urban_id)
        cover = np.asarray(self.terrain.land_cover)
        factor = np.where(
            cover == CoverClass.FOREST, float(factors["wooded"]), float(factors["open"])
        )
        if not self.terrain.cities:
            return factor
        # The largest urban extent is the city core and every other one a town (decision 0012
        # addendum, answer 6).
        core = min(self.terrain.cities, key=lambda c: (-c.cell_count, c.city_id))
        factor = np.where(urban >= 0, float(factors["town"]), factor)
        return np.where(urban == core.city_id, float(factors["city_core"]), factor)


def _coast_distance_km(
    land: NDArray[np.bool_], cell_km: float, cap_km: float
) -> NDArray[np.float64]:
    """Straight-line distance from each land cell to the nearest sea cell, capped (km)."""
    reach = int(cap_km / cell_km) + 1
    distance = np.full(land.shape, cap_km)
    sea = np.pad(~land, reach, constant_values=True)
    size = land.shape[0]
    for dr in range(-reach, reach + 1):
        for dc in range(-reach, reach + 1):
            km = math.sqrt(dr * dr + dc * dc) * cell_km
            if km == 0.0 or km >= cap_km:
                continue
            shifted = sea[reach + dr : reach + dr + size, reach + dc : reach + dc + size]
            distance = np.where(shifted & (km < distance), km, distance)
    return distance


# --- The track, peak wind and rainfall (A2, B1) ---------------------------------------------


@dataclass(frozen=True)
class _Draw:
    track: Track
    rain_mm: float


def _draw_track(
    low: float,
    high: float,
    anchor: float,
    rung_mm: float,
    ground: _Ground,
    stream: np.random.Generator,
) -> _Draw:
    """Draw the peak wind, closest approach, radius, heading and rainfall of one scenario."""
    rules = ground.rules
    # CHOICE: the peak wind is triangular over the class band with its mode at the severity's
    # anchor, so every draw stays in the class and the anchor is the likeliest value.
    peak = _triangular(low, anchor, high, float(stream.random()))
    # CHOICE: closest approach, radius and rainfall are uniform over their ruled ranges.
    approach = _uniform(rules.value("storm.closest_approach_km"), float(stream.random()))
    radius = _uniform(rules.value("storm.radius_max_wind_km"), float(stream.random()))
    east, south = _heading(stream)
    spread = rules.number("storm.rainfall_spread_mm")
    rain = rung_mm - spread + 2.0 * spread * float(stream.random())
    # The track lies the closest approach to the right of the centre; since the heading covers
    # every direction, that reaches every line at that distance.
    cx, cy = ground.centre_km
    point = (cx - south * approach, cy + east * approach)
    return _Draw(Track(point, (east, south), peak, approach, radius), rain)


def _uniform(bounds: Sequence[float], u: float) -> float:
    low, high = float(bounds[0]), float(bounds[1])
    return low + (high - low) * u


def _triangular(low: float, mode: float, high: float, u: float) -> float:
    """Inverse of the triangular distribution on [low, high] with the given mode (sqrt only)."""
    width = high - low
    if u * width <= mode - low:
        return low + math.sqrt(u * width * (mode - low))
    return high - math.sqrt((1.0 - u) * width * (high - mode))


def _heading(stream: np.random.Generator) -> tuple[float, float]:
    """Draw a uniformly random unit vector, by rejection from the square (no trigonometry)."""
    while True:
        east, south = 2.0 * float(stream.random()) - 1.0, 2.0 * float(stream.random()) - 1.0
        length2 = east * east + south * south
        if 0.0 < length2 <= 1.0:
            length = math.sqrt(length2)
            return east / length, south / length


# --- The field (A2) -------------------------------------------------------------------------


def _scenario(
    index: int,
    draw: _Draw,
    ground: _Ground,
    height: NDArray[np.float64],
    correlation_km: int,
    stream: np.random.Generator,
) -> StormScenario:
    rules, track = ground.rules, draw.track
    radius_km = track.radius_max_wind_km
    offset = _signed_distance_km(track, ground)
    distance = np.abs(offset)
    profile = _profile(track.peak_wind_m_per_s, distance, radius_km)
    lee = _lee(track, offset, ground)
    lee_factor = np.where(lee, rules.number("storm.lee_factor"), 1.0)
    spread = float(rules.value("storm.variation")["spread"])
    variation = 1.0 + spread * _variation(ground, float(correlation_km), stream)
    wind = np.maximum(profile * ground.surface * lee_factor * variation, 0.0)
    stage = flood_stage_m(draw.rain_mm, rules)
    flood = np.where(ground.land, np.maximum(stage - height, 0.0), 0.0)
    land_distance = distance.ravel()[ground.land_cells]
    inside = int(np.count_nonzero(land_distance <= radius_km)) / ground.land_cells.size
    return StormScenario(
        index, track, draw.rain_mm, stage, _frozen(wind), _frozen(flood), _frozen(lee), inside
    )


def _calm(index: int, terrain: TerrainResult) -> StormScenario:
    zeros = np.zeros(terrain.land.shape)
    lee = np.zeros(zeros.shape, bool)
    return StormScenario(index, None, 0.0, 0.0, _frozen(zeros), _frozen(zeros), _frozen(lee), 0.0)


def _signed_distance_km(track: Track, ground: _Ground) -> NDArray[np.float64]:
    """Distance from each cell centre to the track line, positive to the right of travel."""
    return _offset_km(track, ground.x_km, ground.y_km)


def signed_distance_km(track: Track, cell_size_m: float) -> NDArray[np.float64]:
    """Return each cell's distance from the track line, positive to the right of travel.

    Parameters
    ----------
    track : Track
        The scenario's straight track.
    cell_size_m : float
        The terrain grid's cell size, in m.

    Returns
    -------
    numpy.ndarray
        Signed distance in km, one per cell (row 0 the northern edge).

    Spec: structure v0.7 §4.3b (the wind field); PR 14 answer 1.
    """
    cell_km = cell_size_m / M_PER_KM
    centres = (np.arange(GRID_CELLS) + 0.5) * cell_km
    x_km = np.ones((GRID_CELLS, 1)) * centres[None, :]
    y_km = centres[:, None] * np.ones((1, GRID_CELLS))
    return _offset_km(track, x_km, y_km)


def _offset_km(
    track: Track, x_km: NDArray[np.float64], y_km: NDArray[np.float64]
) -> NDArray[np.float64]:
    east, south = track.direction
    px, py = track.point_km
    offset: NDArray[np.float64] = (x_km - px) * (-south) + (y_km - py) * east
    return offset


def _profile(
    peak: float, distance_km: NDArray[np.float64], radius_km: float
) -> NDArray[np.float64]:
    """Return the modified Rankine wind at each cell, at its peak over the storm's passage.

    Inside the radius the wind rises linearly to the peak, and beyond it falls as
    sqrt(R_max / r). A cell whose closest approach is within the radius meets the eyewall as the
    storm passes, so its peak is the storm's peak; beyond it, the peak is at closest approach.
    """
    # CHOICE: the field is each place's peak over the passage (the evidence's "maximum over
    # steps", taken continuously), not a snapshot at one instant (kept: decision 0012 addendum).
    safe = np.maximum(distance_km, radius_km)
    return np.where(distance_km <= radius_km, peak, peak * np.sqrt(radius_km / safe))


def _lee(track: Track, offset_km: NDArray[np.float64], ground: _Ground) -> NDArray[np.bool_]:
    """Land cells with the smooth spine line between them and the nearest point of the track.

    A cell's nearest point on the track is the foot of its perpendicular. The cell is in the
    lee if that segment crosses any segment of the spine line (decision 0005). A flat island
    has no lee.
    """
    lee = np.zeros(GRID_CELLS * GRID_CELLS, dtype=bool)
    spine = ground.terrain.spine_km
    if not ground.has_lee or len(spine) < 2:
        return lee.reshape(GRID_CELLS, GRID_CELLS)
    east, south = track.direction
    cells = ground.land_cells
    px, py = ground.x_km.ravel()[cells], ground.y_km.ravel()[cells]
    offset = offset_km.ravel()[cells]
    # The unit normal (-south, east) points to the right of travel, so the foot lies back
    # along it by the signed distance.
    fx, fy = px + offset * south, py - offset * east
    sheltered = np.zeros(cells.size, dtype=bool)
    for (ax, ay), (bx, by) in pairwise(spine):
        side_p = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        side_f = (bx - ax) * (fy - ay) - (by - ay) * (fx - ax)
        side_a = (fx - px) * (ay - py) - (fy - py) * (ax - px)
        side_b = (fx - px) * (by - py) - (fy - py) * (bx - px)
        sheltered |= (side_p * side_f < 0.0) & (side_a * side_b < 0.0)
    lee[cells] = sheltered
    return lee.reshape(GRID_CELLS, GRID_CELLS)


def _variation(
    ground: _Ground, correlation_km: float, stream: np.random.Generator
) -> NDArray[np.float64]:
    """Draw a smooth unit-variance field: a Wendland kernel sum over lattice normal values.

    CHOICE: a kernel sum rather than a Cholesky factor, since the grid has 65,536 cells. Each
    lattice value is an Irwin-Hall normal (twelve uniforms less 6), and the sum is divided by
    the square root of the summed squared weights so every cell has variance 1.
    """
    support_km = KERNEL_RADIUS_SHARE * correlation_km
    spacing_km = LATTICE_SPACING_SHARE * support_km
    side_km = GRID_CELLS * ground.cell_km
    count = int((side_km + 2 * support_km) / spacing_km) + 2
    reach = int(support_km / ground.cell_km) + 1
    total = np.zeros((GRID_CELLS, GRID_CELLS))
    weight2 = np.zeros((GRID_CELLS, GRID_CELLS))
    for i in range(count):
        for j in range(count):
            normal = _normal(stream)
            cx, cy = -support_km + j * spacing_km, -support_km + i * spacing_km
            column, row = int(cx / ground.cell_km), int(cy / ground.cell_km)
            rows = slice(max(row - reach, 0), min(row + reach + 1, GRID_CELLS))
            columns = slice(max(column - reach, 0), min(column + reach + 1, GRID_CELLS))
            if rows.start >= rows.stop or columns.start >= columns.stop:
                continue
            dx, dy = ground.x_km[rows, columns] - cx, ground.y_km[rows, columns] - cy
            weight = _wendland(np.sqrt(dx * dx + dy * dy) / support_km)
            total[rows, columns] += normal * weight
            weight2[rows, columns] += weight * weight
    field = np.zeros_like(total)
    np.divide(total, np.sqrt(weight2), out=field, where=weight2 > 0.0)
    return field


def _normal(stream: np.random.Generator) -> float:
    total = 0.0
    for _ in range(IRWIN_HALL_TERMS):
        total += float(stream.random())
    return total - IRWIN_HALL_TERMS / 2


def _wendland(t: NDArray[np.float64]) -> NDArray[np.float64]:
    """Wendland phi(3,1): (1 - t)^4 (1 + 4t) for t < 1, else 0. Valid in 2-D."""
    inside: NDArray[np.float64] = np.maximum(1.0 - t, 0.0)
    squared = inside * inside
    weight: NDArray[np.float64] = squared * squared * (1.0 + 4.0 * t)
    return weight


# --- Flood (B2) -----------------------------------------------------------------------------


def height_above_drainage_m(terrain: TerrainResult) -> NDArray[np.float64]:
    """Height of each land cell above the drainage its flow path first reaches (m; HAND).

    The flow path follows the terrain's D8 directions to the first river cell or the sea. Sea
    cells are 0.

    Parameters
    ----------
    terrain : TerrainResult
        The ground: elevation (dm), land, flow directions and rivers.

    Returns
    -------
    numpy.ndarray
        Height above the nearest drainage in m, per cell.

    Spec: structure v0.7 §4.3b (flood; Nobre 2011); Work Order 6, B2.
    """
    land = np.asarray(terrain.land).ravel()
    drain = np.asarray(terrain.river).ravel() | ~land
    direction = np.asarray(terrain.flow_direction).ravel()
    cells = np.arange(land.size)
    offsets = np.array([dr * GRID_CELLS + dc for dr, dc in D8_OFFSETS])
    step = np.where(drain | (direction < 0), cells, cells + offsets[np.maximum(direction, 0)])
    # Pointer doubling: each pass doubles how far along its path every cell has looked.
    while True:
        jumped = step[step]
        if np.array_equal(jumped, step):
            break
        step = jumped
    elevation = np.asarray(terrain.elevation_dm).ravel().astype(np.int64)
    height_dm = np.where(land, elevation - np.where(land[step], elevation[step], 0), 0)
    # CHOICE: a cell in a pit, below the drainage its path spills to, counts as height 0: it
    # floods to the stage like a drainage cell, since Phase 1 has no lakes (terrain, decision
    # 0005). Nobre's HAND works on a filled surface, where no cell lies below its drainage.
    return (np.maximum(height_dm, 0) / 10.0).reshape(GRID_CELLS, GRID_CELLS)


def flood_threshold_m(node_class: str, rules: Registry) -> float | None:
    """Return the water depth above grade at which a node of this class floods out.

    Parameters
    ----------
    node_class : str
        The node's class.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    float or None
        The Hazus functional depth plus any platform height (m); None for a class that is not
        flood-damaged in Phase 1. A threshold of 0 means any water.

    Spec: structure v0.7 §4.3b (flood); decision 0012 addendum.
    """
    depths = rules.value("storm.flood_functional_depth_m")
    if node_class not in depths:
        return None
    platform = rules.value("storm.power_platform_m").get(node_class, 0.0)
    return float(depths[node_class]) + float(platform)


def _floods_out(depth_m: float, threshold_m: float | None) -> bool:
    # A threshold of 0 ("any water") floods out at any depth above 0.
    return threshold_m is not None and depth_m > threshold_m


# --- Records ---------------------------------------------------------------------------------


def facility_exposure(
    result: StormResult, layers: LayersResult, rules: Registry
) -> list[FacilityExposure]:
    """Read every node's wind and flood per scenario, its height above drainage and threshold.

    Parameters
    ----------
    result : StormResult
        The storm stage's output.
    layers : LayersResult
        The layers: each node's cell.
    rules : Registry
        The modeling rules in force: flood thresholds and platforms.

    Returns
    -------
    list of FacilityExposure
        One record per node, in node order.

    Spec: Work Order 6, B2 (per facility: height above drainage, flood depth per scenario).
    """
    records = []
    for node in layers.nodes:
        cell = (node.row, node.column)
        threshold = flood_threshold_m(node.node_class.value, rules)
        depths = tuple(float(s.flood_depth_m[cell]) for s in result.scenarios)
        records.append(
            FacilityExposure(
                node_id=node.node_id,
                node_class=node.node_class.value,
                height_above_drainage_m=float(result.height_above_drainage_m[cell]),
                flood_threshold_m=threshold,
                wind_m_per_s=tuple(float(s.wind_m_per_s[cell]) for s in result.scenarios),
                flood_depth_m=depths,
                floods_out=tuple(_floods_out(depth, threshold) for depth in depths),
            )
        )
    return records


def storm_hashes(result: StormResult) -> list[tuple[str, str]]:
    """Return the SHA-256 of each scenario's fields, quantised to integers, in a fixed order.

    Parameters
    ----------
    result : StormResult
        The storm stage's output.

    Returns
    -------
    list of (str, str)
        (field name, hex digest): wind in cm/s, flood depth in cm, lee mask, and the height
        above drainage in cm, little-endian, C order.

    Spec: CLAUDE.md §7 (identity check); Work Order 6, tests.
    """
    arrays = [("height_above_drainage_cm", _centi(result.height_above_drainage_m))]
    for scenario in result.scenarios:
        arrays += [
            (f"scenario_{scenario.index}/wind_cm_per_s", _centi(scenario.wind_m_per_s)),
            (f"scenario_{scenario.index}/flood_depth_cm", _centi(scenario.flood_depth_m)),
            (f"scenario_{scenario.index}/lee", scenario.lee.astype("u1")),
        ]
    return [
        (name, hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest())
        for name, array in arrays
    ]


def statistics_record(
    result: StormResult, exposure: Sequence[FacilityExposure]
) -> dict[str, object]:
    """Return the severity, each scenario's track and field summary, and facility exposure.

    Parameters
    ----------
    result : StormResult
        The storm stage's output.
    exposure : sequence of FacilityExposure
        Each node's exposure.

    Returns
    -------
    dict
        Plain data ready for canonical YAML, numbers rounded.

    Spec: Work Order 6, Parts A-B.
    """
    scenarios = [_scenario_record(scenario, exposure) for scenario in result.scenarios]
    return {
        "severity": result.severity,
        "storm_class": result.storm_class,
        "anchor_m_per_s": round(result.anchor_m_per_s, 3),
        "rain_rung_mm": result.rain_rung_mm,
        "scenarios": scenarios,
    }


def _scenario_record(
    scenario: StormScenario, exposure: Sequence[FacilityExposure]
) -> dict[str, object]:
    index = scenario.index
    winds = [e.wind_m_per_s[index] for e in exposure]
    track = scenario.track

    def rounded(value: float | None, places: int = 3) -> float | None:
        return None if value is None else round(value, places)

    return {
        "index": index,
        "track_point_km": None if track is None else [round(v, 3) for v in track.point_km],
        "heading": None if track is None else [round(v, 6) for v in track.direction],
        "peak_wind_m_per_s": rounded(None if track is None else track.peak_wind_m_per_s),
        "closest_approach_km": rounded(None if track is None else track.closest_approach_km),
        "radius_max_wind_km": rounded(None if track is None else track.radius_max_wind_km),
        "land_inside_radius_share": round(scenario.inside_radius_share, 6),
        "lee_land_cells": int(np.count_nonzero(scenario.lee)),
        "rain_mm": round(scenario.rain_mm, 3),
        "flood_stage_m": round(scenario.flood_stage_m, 3),
        "facility_wind_m_per_s": {
            "least": round(min(winds), 3) if winds else None,
            "mean": round(math.fsum(winds) / len(winds), 3) if winds else None,
            "most": round(max(winds), 3) if winds else None,
        },
        "wet_facilities": sorted(e.node_id for e in exposure if e.flood_depth_m[index] > 0.0),
        "flooded_out_facilities": sorted(e.node_id for e in exposure if e.floods_out[index]),
    }


def exposure_table(exposure: Sequence[FacilityExposure]) -> list[dict[str, object]]:
    """Return each node's exposure as plain data, numbers rounded to 3 decimals.

    Parameters
    ----------
    exposure : sequence of FacilityExposure
        Each node's exposure.

    Returns
    -------
    list of dict
        One row per node.

    Spec: Work Order 6, B2.
    """
    return [
        {
            "node_id": e.node_id,
            "class": e.node_class,
            "height_above_drainage_m": round(e.height_above_drainage_m, 3),
            "flood_threshold_m": e.flood_threshold_m,
            "wind_m_per_s": [round(v, 3) for v in e.wind_m_per_s],
            "flood_depth_m": [round(v, 3) for v in e.flood_depth_m],
            "floods_out": list(e.floods_out),
        }
        for e in exposure
    ]


def _centi(array: NDArray[np.float64]) -> NDArray[np.int32]:
    return np.floor(np.asarray(array) * CM_PER_M + 0.5).astype("<i4")


def _frozen[T: np.generic](array: NDArray[T]) -> NDArray[T]:
    array = np.array(array, copy=True)
    array.flags.writeable = False
    return array
