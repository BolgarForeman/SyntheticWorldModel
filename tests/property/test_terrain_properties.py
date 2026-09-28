from hypothesis import given, settings
from hypothesis import strategies as st

from swm.stages.terrain import CoverClass
from terrain_helpers import area_tolerance_km2, build, drains_to_sea, elevation_bound_m

index = st.integers(min_value=0, max_value=100)
character = st.fixed_dictionaries(
    {
        "mountainous": index,
        "forested": index,
        "river_density": index,
        "urban_density": index,
        "coastline_complexity": index,
        "lowland_and_wetland": index,
        "aridity": index,
        "outlying_islands": st.integers(min_value=0, max_value=8),
    }
)


@settings(max_examples=12, deadline=None)
@given(
    character=character,
    pattern=st.sampled_from(["one_dominant_city", "several_cities", "dispersed_towns"]),
    terrain_seed=st.integers(min_value=0, max_value=2**64 - 1),
    area_km2=st.floats(min_value=1.0, max_value=2000.0),
)
def test_any_valid_terrain_section_builds_and_keeps_its_invariants(
    character: dict[str, int], pattern: str, terrain_seed: int, area_km2: float
) -> None:
    result = build(
        character=character, urban_pattern=pattern, terrain_seed=terrain_seed, area_km2=area_km2
    )
    assert not result.elevation_dm[~result.land].any()
    assert result.statistics.max_elevation_m <= elevation_bound_m(character["mountainous"])
    assert drains_to_sea(result)
    assert result.statistics.island_count == character["outlying_islands"] + 1
    assert abs(result.statistics.land_area_km2 - area_km2) <= area_tolerance_km2(result)
    assert (result.land_cover[result.land] != CoverClass.SEA).all()
