from collections.abc import Callable
from itertools import pairwise
from typing import Any

import numpy as np
import pytest

from swm import rng
from swm.stages.terrain import (
    TERRAIN_STREAM_PATHS,
    CoverClass,
    TerrainResult,
    array_hashes,
    statistics_record,
)
from terrain_helpers import (
    area_tolerance_km2,
    build,
    downstream,
    drains_to_sea,
    elevation_bound_m,
)


@pytest.fixture(scope="module")
def pilot() -> TerrainResult:
    return build(map_type="spine_island", size_preset="hand_check")


def share(result: TerrainResult, cover: CoverClass) -> float:
    return result.statistics.cover_shares[cover.name.lower()]


# --- Streams --------------------------------------------------------------------------------


def test_changing_the_terrain_seed_changes_the_terrain(pilot: TerrainResult) -> None:
    other = build(terrain_seed=1)
    assert not np.array_equal(other.elevation_dm, pilot.elevation_dm)


def test_changing_the_root_seed_changes_the_terrain(pilot: TerrainResult) -> None:
    other = build(root_seed=91578)
    assert not np.array_equal(other.elevation_dm, pilot.elevation_dm)


def test_same_recipe_gives_the_same_terrain(pilot: TerrainResult) -> None:
    assert array_hashes(build()) == array_hashes(pilot)


def test_only_terrain_streams_are_drawn(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []
    original: Callable[..., np.random.Generator] = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> np.random.Generator:
        requested.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    build()
    assert requested == list(TERRAIN_STREAM_PATHS)
    assert all(path.startswith("terrain/") for path in requested)


# --- Area and elevation ---------------------------------------------------------------------


@pytest.mark.parametrize("area_km2", [1.0, 400.0, 1234.5, 2000.0])
def test_realised_land_area_matches_the_target(area_km2: float) -> None:
    result = build(area_km2=area_km2)
    assert abs(result.statistics.land_area_km2 - area_km2) <= area_tolerance_km2(result)


def test_sea_cells_are_zero_and_the_maximum_is_bounded(pilot: TerrainResult) -> None:
    assert not pilot.elevation_dm[~pilot.land].any()
    assert pilot.statistics.max_elevation_m <= elevation_bound_m(60)
    assert pilot.statistics.max_elevation_m > 0.5 * elevation_bound_m(60)


def test_mountainous_zero_gives_low_relief() -> None:
    flat = build(character={"mountainous": 0})
    low = build(character={"mountainous": 10})
    assert flat.statistics.max_elevation_m == 0
    assert low.statistics.max_elevation_m <= elevation_bound_m(10)


def test_other_map_types_are_refused() -> None:
    with pytest.raises(ValueError, match="archipelago is not built yet"):
        build(map_type="archipelago")


# --- Drainage -------------------------------------------------------------------------------


def test_every_land_cell_drains_to_the_sea(pilot: TerrainResult) -> None:
    assert (pilot.flow_direction[pilot.land] >= 0).all()
    assert (pilot.flow_direction[~pilot.land] == -1).all()
    assert drains_to_sea(pilot)


def test_rivers_run_on_to_the_sea(pilot: TerrainResult) -> None:
    rivers = np.flatnonzero(pilot.river.ravel())
    assert rivers.size > 0
    after = downstream(pilot)[rivers]
    assert (pilot.river.ravel()[after] | ~pilot.land.ravel()[after]).all()


def test_accumulation_counts_upstream_cells(pilot: TerrainResult) -> None:
    assert (pilot.flow_accumulation[pilot.land] >= 1).all()
    assert not pilot.flow_accumulation[~pilot.land].any()
    outlets = pilot.land.ravel() & ~pilot.land.ravel()[downstream(pilot)]
    assert int(pilot.flow_accumulation.ravel()[outlets].sum()) == int(pilot.land.sum())


def test_river_density_zero_gives_no_rivers() -> None:
    assert not build(character={"river_density": 0}).river.any()


# --- Monotonic responses --------------------------------------------------------------------


def rising(values: list[float]) -> bool:
    return all(a < b for a, b in pairwise(values))


def test_forested_raises_the_forest_share() -> None:
    shares = [share(build(character={"forested": f}), CoverClass.FOREST) for f in (10, 40, 80)]
    assert rising(shares)


def test_aridity_lowers_the_forest_share() -> None:
    shares = [share(build(character={"aridity": a}), CoverClass.FOREST) for a in (0, 40, 80)]
    assert rising(shares[::-1])


def test_lowland_and_wetland_raises_the_wetland_share() -> None:
    shares = [
        share(build(character={"lowland_and_wetland": w}), CoverClass.WETLAND) for w in (5, 20, 40)
    ]
    assert rising(shares)


def test_urban_density_raises_the_urban_share() -> None:
    shares = [share(build(character={"urban_density": u}), CoverClass.URBAN) for u in (10, 40, 80)]
    assert rising(shares)


def test_river_density_raises_river_length() -> None:
    lengths = [
        build(character={"river_density": r}).statistics.river_length_km for r in (20, 50, 90)
    ]
    assert rising(lengths)


# --- Islands, cover and cities --------------------------------------------------------------


@pytest.mark.parametrize("count", [0, 1, 4, 8])
def test_outlying_island_count_equals_the_setting(count: int) -> None:
    assert build(character={"outlying_islands": count}).statistics.island_count == count + 1


def test_every_land_cell_has_one_cover_class(pilot: TerrainResult) -> None:
    assert (pilot.land_cover[~pilot.land] == CoverClass.SEA).all()
    assert (pilot.land_cover[pilot.land] != CoverClass.SEA).all()
    assert np.array_equal(pilot.land_cover == CoverClass.URBAN, pilot.urban_id >= 0)
    assert sum(pilot.statistics.cover_shares.values()) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.parametrize(
    ("pattern", "counts"),
    [
        ("one_dominant_city", {1}),
        ("several_cities", {3, 4, 5}),
        ("dispersed_towns", {12}),
    ],
)
def test_city_count_follows_the_pattern(pattern: str, counts: set[int]) -> None:
    result = build(urban_pattern=pattern)
    assert result.statistics.city_count in counts
    for city in result.cities:
        footprint = result.urban_id == city.city_id
        assert city.cell_count == int(footprint.sum()) > 0
        assert result.land[city.centre_row, city.centre_column]


def test_urban_density_zero_gives_no_cities() -> None:
    result = build(character={"urban_density": 0})
    assert result.cities == ()
    assert not (result.urban_id >= 0).any()


def test_arrays_are_read_only(pilot: TerrainResult) -> None:
    with pytest.raises(ValueError, match="read-only"):
        pilot.elevation_dm[0, 0] = 1


def test_statistics_record_is_plain_data_in_a_fixed_order(pilot: TerrainResult) -> None:
    record = statistics_record(pilot)
    assert list(record) == [
        "grid_cells",
        "cell_size_m",
        "land_area_km2",
        "max_elevation_m",
        "river_length_km",
        "island_count",
        "city_count",
        "cover_shares",
    ]
    assert next(name for name, _ in array_hashes(pilot)) == "elevation_dm"
