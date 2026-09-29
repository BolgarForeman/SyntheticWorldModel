import itertools

import pytest

from swm.coordinates import (
    POINT_NEMO_EASTING_M,
    POINT_NEMO_LATITUDE,
    POINT_NEMO_LONGITUDE,
    POINT_NEMO_NORTHING_M,
    cell_centre_m,
    domain_origin_m,
    from_lonlat,
    to_lonlat,
)
from swm.stages.terrain import Grid

PILOT_GRID = Grid(cells=256, cell_size_m=133.0, origin_m=(0.0, 0.0))


def test_the_centroid_reproduces_exactly() -> None:
    assert to_lonlat(POINT_NEMO_EASTING_M, POINT_NEMO_NORTHING_M) == (
        POINT_NEMO_LONGITUDE,
        POINT_NEMO_LATITUDE,
    )
    easting, northing = from_lonlat(POINT_NEMO_LONGITUDE, POINT_NEMO_LATITUDE)
    assert round(easting, 2) == POINT_NEMO_EASTING_M
    assert round(northing, 2) == POINT_NEMO_NORTHING_M


def test_the_domain_centre_sits_on_the_centroid() -> None:
    west, south = domain_origin_m(PILOT_GRID)
    half = PILOT_GRID.cells * PILOT_GRID.cell_size_m / 2
    assert (west + half, south + half) == pytest.approx(
        (POINT_NEMO_EASTING_M, POINT_NEMO_NORTHING_M), abs=1e-6
    )


def test_row_zero_is_north() -> None:
    _, north = cell_centre_m(0, 0, PILOT_GRID)
    _, south = cell_centre_m(255, 0, PILOT_GRID)
    assert north > south


@pytest.mark.parametrize(("row", "column"), list(itertools.product((0, 128, 255), repeat=2)))
def test_round_trip_within_one_centimetre(row: int, column: int) -> None:
    easting, northing = cell_centre_m(row, column, PILOT_GRID)
    back = from_lonlat(*to_lonlat(easting, northing))
    assert back == pytest.approx((easting, northing), abs=0.01)


def test_latitude_and_longitude_have_seven_decimals() -> None:
    longitude, latitude = to_lonlat(*cell_centre_m(17, 203, PILOT_GRID))
    assert round(longitude, 7) == longitude
    assert round(latitude, 7) == latitude
    assert -49.5 < latitude < -48.2
    assert -124.2 < longitude < -122.6
