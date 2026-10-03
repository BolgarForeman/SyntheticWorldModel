"""Coordinates: the world anchored at Point Nemo, in WGS 84 / UTM zone 10S (EPSG:32710).

The generator's local metres become EPSG:32710 metres by a fixed offset, which is pure addition,
so world-building arithmetic stays exact. Latitude and longitude come from one quantised
projection transform. Spec: structure v0.4 §3 (synthetic centroid) and §4.1a.
"""

import math
from functools import cache

from pyproj import Transformer

from swm.stages.terrain import Grid

POINT_NEMO_LATITUDE = -48.8767
"""Latitude of Point Nemo, the synthetic centroid, in degrees (south negative).

Source: the Pacific pole of inaccessibility, 48.8767° S, 123.3933° W (structure v0.4 §3).
"""

POINT_NEMO_LONGITUDE = -123.3933
"""Longitude of Point Nemo, in degrees (west negative). Source: as above."""

WORKING_CRS = "EPSG:32710"
"""The working projection: WGS 84 / UTM zone 10S (structure v0.4 §4.1a)."""

GEOGRAPHIC_CRS = "EPSG:4326"
"""WGS 84 latitude and longitude, as emitted sources carry them (structure v0.4 §4.1a)."""

POINT_NEMO_EASTING_M = 471_162.13
"""Point Nemo's easting in EPSG:32710, in m, quantised to the centimetre.

Computed once with pyproj 3.8 from the latitude and longitude above and fixed here, so the
offset is a constant on every platform; a test checks pyproj still reproduces it.
"""

POINT_NEMO_NORTHING_M = 4_586_176.19
"""Point Nemo's northing in EPSG:32710 (false northing applied), in m. Source: as above."""

LATLON_DECIMALS = 7
"""Decimal places kept in latitude and longitude: about 1 cm (structure v0.4 §4.1a)."""


def domain_origin_m(grid: Grid) -> tuple[float, float]:
    """Return the EPSG:32710 coordinates of the domain's south-west corner.

    Parameters
    ----------
    grid : Grid
        The terrain grid.

    Returns
    -------
    tuple of float
        (easting, northing) in m, placing the domain's centre on Point Nemo.

    Spec: structure v0.4 §4.1a; Work Order 3, A1.
    """
    half_side_m = grid.cells * grid.cell_size_m / 2
    return POINT_NEMO_EASTING_M - half_side_m, POINT_NEMO_NORTHING_M - half_side_m


def cell_centre_m(row: int, column: int, grid: Grid) -> tuple[float, float]:
    """Return a cell centre's EPSG:32710 coordinates. Row 0 is the northern edge.

    Parameters
    ----------
    row, column : int
        The cell.
    grid : Grid
        The terrain grid.

    Returns
    -------
    tuple of float
        (easting, northing) in m.

    Spec: structure v0.4 §4.1a; Work Order 3, A1.
    """
    west_m, south_m = domain_origin_m(grid)
    return (
        west_m + (column + 0.5) * grid.cell_size_m,
        south_m + (grid.cells - row - 0.5) * grid.cell_size_m,
    )


def cell_of(x_m: float, y_m: float, grid: Grid) -> tuple[int, int]:
    """Return the (row, column) of the grid cell holding a point; row 0 is the northern edge.

    Parameters
    ----------
    x_m, y_m : float
        EPSG:32710 easting and northing, in m.
    grid : Grid
        The terrain grid.

    Returns
    -------
    tuple of int
        The cell, held inside the grid.

    Spec: structure v0.4 §4.1a (coordinates).
    """
    west_m, south_m = domain_origin_m(grid)
    cells = grid.cells
    column = math.floor((x_m - west_m) / grid.cell_size_m)
    row = cells - 1 - math.floor((y_m - south_m) / grid.cell_size_m)
    return min(max(row, 0), cells - 1), min(max(column, 0), cells - 1)


def to_lonlat(easting_m: float, northing_m: float) -> tuple[float, float]:
    """Convert EPSG:32710 metres to WGS 84 longitude and latitude, rounded to 7 decimals.

    The projection transform is the one sanctioned use of transcendental arithmetic; its result
    is quantised to 7 decimal places so it is the same bytes on every platform.

    Parameters
    ----------
    easting_m, northing_m : float
        EPSG:32710 coordinates, in m.

    Returns
    -------
    tuple of float
        (longitude, latitude) in degrees.

    Spec: structure v0.4 §4.1a; Work Order 3, A2.
    """
    longitude, latitude = _to_geographic().transform(easting_m, northing_m)
    return round(longitude, LATLON_DECIMALS), round(latitude, LATLON_DECIMALS)


def from_lonlat(longitude: float, latitude: float) -> tuple[float, float]:
    """Convert WGS 84 longitude and latitude to EPSG:32710 metres.

    Parameters
    ----------
    longitude, latitude : float
        Degrees.

    Returns
    -------
    tuple of float
        (easting, northing) in m.

    Spec: structure v0.4 §4.1a.
    """
    easting_m, northing_m = _to_geographic().transform(longitude, latitude, direction="INVERSE")
    return float(easting_m), float(northing_m)


@cache
def _to_geographic() -> Transformer:
    return Transformer.from_crs(WORKING_CRS, GEOGRAPHIC_CRS, always_xy=True)
