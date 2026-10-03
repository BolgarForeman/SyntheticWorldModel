"""The ridge and hill speed-up: Taiwan's building wind code topographic factor on the grid.

On the upper half of an isolated hill, ridge or escarpment the wind speeds up. The code (建築物
耐風設計規範及解說 §2.6, Formula 2.8) gives Kzt = (1 + K1 K2 K3)^2 on wind pressure, so wind
speed takes 1 + K1 K2 K3 (structure v0.8 §4.3b):
- K1 from Table 2.3(a), by the feature's H/Lh (capped at 0.5) and the terrain class;
- K2 = 1 - |x| / (mu Lh), the decay with distance x from the crest (Table 2.3(b));
- K3 from Table 2.3(c), the decay with height z above the ground (it needs exp otherwise).

How H, Lh and x are read off the grid is this module's (CHOICE, stated in each function): the
code assumes the wind blows up the steepest slope, so every cell takes the worst of the eight
grid directions. Along each, the crest is the highest ground within 3.22 km either side, H its
height above the lowest ground upwind of it, and Lh the distance upwind from the crest to where
the ground is half that height. The factor applies only where the code's conditions hold.

Only +, -, x, / and sqrt; the stored tables are interpolated linearly.

Spec: structure v0.8 §4.3b (routes and ridges); Work Order 6c, C2.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from swm.rules.registry import Registry
from swm.stages.terrain import D8_OFFSETS, CoverClass, TerrainResult

M_PER_KM = 1000.0


@dataclass(frozen=True)
class _Feature:
    """The feature each cell sees along one wind direction."""

    height_m: NDArray[np.float64]
    """H: crest height above the lowest ground upwind of it."""
    half_length_km: NDArray[np.float64]
    """Lh: distance upwind from the crest to where the ground is half the height."""
    offset_km: NDArray[np.float64]
    """x: the cell's distance downwind of the crest (negative upwind)."""
    escarpment: NDArray[np.bool_]
    applies: NDArray[np.bool_]
    """The code's conditions hold."""


def speed_factor(terrain: TerrainResult, rules: Registry, height_m: float) -> NDArray[np.float64]:
    """Return 1 + K1 K2 K3 at each cell for a structure of the given height (1 off features).

    Parameters
    ----------
    terrain : TerrainResult
        The ground: elevation, land, land cover and cell size.
    rules : Registry
        The modeling rules in force (``storm.topographic_factor``).
    height_m : float
        The height above ground the wind is read at (z), in m.

    Returns
    -------
    numpy.ndarray
        The factor on wind speed, sqrt(Kzt), the worst over the eight grid directions.

    Spec: structure v0.8 §4.3b; Work Order 6c, C2.
    """
    table = rules.value("storm.topographic_factor")
    elevation = np.asarray(terrain.elevation_dm) / 10.0
    land = np.asarray(terrain.land)
    cover = np.asarray(terrain.land_cover)
    # CHOICE: the terrain class follows the surface factor's: towns, the city core and wooded
    # land are class A or B, all other ground class C.
    rough = (np.asarray(terrain.urban_id) >= 0) | (cover == CoverClass.FOREST)
    cell_km = terrain.grid.cell_size_m / M_PER_KM
    best = np.ones(elevation.shape)
    for dr, dc in D8_OFFSETS:
        feature = _feature(elevation, rough, cell_km, (dr, dc), table)
        factor = _factor(feature, rough, table, height_m)
        best = np.maximum(best, np.where(land & feature.applies, factor, 1.0))
    return best


def _profile(
    elevation: NDArray[np.float64], direction: tuple[int, int], steps: int
) -> NDArray[np.float64]:
    """Elevation at each cell + k x direction, for k = -steps .. steps (sea level off the grid)."""
    dr, dc = direction
    size = elevation.shape[0]
    pad = steps
    padded = np.pad(elevation, pad, constant_values=0.0)
    layers = []
    for k in range(-steps, steps + 1):
        r0, c0 = pad + k * dr, pad + k * dc
        layers.append(padded[r0 : r0 + size, c0 : c0 + size])
    return np.stack(layers)


def _feature(
    elevation: NDArray[np.float64],
    rough: NDArray[np.bool_],
    cell_km: float,
    direction: tuple[int, int],
    table: Mapping[str, Any],
) -> _Feature:
    """Read H, Lh, x and the feature type along one wind direction (the wind travels +k).

    CHOICE: the crest is the highest ground within the code's 3.22 km either side of the cell
    (ties to the most upwind); H is its height above the lowest ground upwind of it; Lh the
    distance upwind to the first ground at half that height or lower; an escarpment where the
    ground downwind of the crest never falls back to half height within the profile, otherwise
    a ridge (2-D: the spine island's features; isolated hills are not told apart).
    """
    upwind_km = float(table["upwind_km"])
    step_km = cell_km * (math.sqrt(2.0) if direction[0] and direction[1] else 1.0)
    steps = max(1, math.ceil(upwind_km / step_km))
    profile = _profile(elevation, direction, steps)
    index = np.arange(-steps, steps + 1)[:, None, None]
    crest_at = np.argmax(profile, axis=0)
    crest_k = crest_at - steps
    crest = np.take_along_axis(profile, crest_at[None], axis=0)[0]
    upwind_of_crest = index <= crest_k[None]
    base = np.where(upwind_of_crest, profile, np.inf).min(axis=0)
    height = crest - base
    half = base + height / 2.0
    # Lh: the first step upwind of the crest at or below half height.
    below = upwind_of_crest & (index < crest_k[None]) & (profile <= half[None])
    nearest_below = np.where(below, index, -steps - 1).max(axis=0)
    found = nearest_below >= -steps
    span = np.where(found, crest_k - nearest_below, crest_k + steps)
    half_length = np.maximum(span, 1) * step_km
    downwind = index > crest_k[None]
    falls_back = (downwind & (profile <= half[None])).any(axis=0)
    # The code's isolation conditions: within 3.22 km upwind nothing beyond the feature's own
    # foot rises above half its height.
    beyond_foot = index < nearest_below[None]
    isolated = ~(beyond_foot & (profile > half[None])).any(axis=0)
    ratio = height / (half_length * M_PER_KM)
    minimum = table["min_height_m"]
    tall = np.where(rough, height > float(minimum["ab"]), height > float(minimum["c"]))
    # The code's factor is for the upper half of a hill or ridge, or near an escarpment's top
    # (上半部 ... 近頂端處): the cell's own ground must stand at half the height or more.
    upper_half = elevation >= half
    applies = found & isolated & tall & upper_half & (ratio >= float(table["h_over_lh_min"]))
    offset = (-crest_k * step_km).astype(np.float64)
    return _Feature(height, half_length, offset, ~falls_back, applies)


def _factor(
    feature: _Feature, rough: NDArray[np.bool_], table: Mapping[str, Any], height_m: float
) -> NDArray[np.float64]:
    """1 + K1 K2 K3 from the feature, by the code's tables and decay formulas."""
    cap = float(table["h_over_lh_cap"])
    ratio = feature.height_m / (feature.half_length_km * M_PER_KM)
    capped = np.minimum(ratio, cap)
    # Above H/Lh 0.5 the code takes Lh = 2H for K2 and K3.
    half_length_km = np.where(
        ratio > cap, 2.0 * feature.height_m / M_PER_KM, feature.half_length_km
    )
    k1_table = table["k1_table"]
    knots = np.asarray(k1_table["h_over_lh"], dtype=np.float64)
    k1 = np.zeros(ratio.shape)
    for shape, escarpment in (("ridge", False), ("escarpment", True)):
        chosen = feature.escarpment == escarpment
        for terrain_class, mask in (("ab", rough), ("c", ~rough)):
            values = np.asarray(k1_table[f"{shape}_{terrain_class}"], dtype=np.float64)
            k1 = np.where(chosen & mask, np.interp(capped, knots, values), k1)
    mu = table["mu"]
    upwind = feature.offset_km < 0.0
    mu_ridge = np.where(upwind, float(mu["ridge"][0]), float(mu["ridge"][1]))
    mu_scarp = np.where(upwind, float(mu["escarpment"][0]), float(mu["escarpment"][1]))
    reach = np.where(feature.escarpment, mu_scarp, mu_ridge) * half_length_km
    k2 = np.maximum(0.0, 1.0 - np.abs(feature.offset_km) / reach)
    k3_table = table["k3_table"]
    z_over = (height_m / M_PER_KM) / half_length_km
    z_knots = np.asarray(k3_table["z_over_lh"], dtype=np.float64)
    k3 = np.where(
        feature.escarpment,
        np.interp(z_over, z_knots, np.asarray(k3_table["escarpment"], dtype=np.float64)),
        np.interp(z_over, z_knots, np.asarray(k3_table["ridge"], dtype=np.float64)),
    )
    factor: NDArray[np.float64] = 1.0 + k1 * k2 * k3
    return factor
