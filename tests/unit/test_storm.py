import functools
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from couplings_helpers import World
from repair_helpers import pilot_world
from swm import rng
from swm.recipe.schema import HazardSettings, SharedCauses
from swm.rules.registry import Stage, ThetaRole, load_registry
from swm.stages import storm as stage
from swm.stages.storm import StormResult, Track, build_storm, storm_streams
from swm.stages.terrain import GRID_CELLS, CoverClass

RULES = load_registry()


def storm_of(world: World, severity: int = 50, scenarios: int = 8, **settings: Any) -> StormResult:
    recipe, terrain, _ = world
    storm = HazardSettings(switched_on=True, severity=severity, correlation_km=10, **settings)
    return build_storm(storm, scenarios, terrain, RULES, storm_streams(recipe.root_seed, scenarios))


@functools.cache
def pilot_storm() -> StormResult:
    return storm_of(pilot_world())


@pytest.fixture(scope="module")
def pilot() -> World:
    return pilot_world()


@pytest.fixture(scope="module")
def ground(pilot: World) -> Any:
    return stage._Ground(pilot[1], RULES)


# --- Severity (B1) --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("severity", "anchor", "storm_class", "rain"),
    [
        (1, 17.73, "mild", 300.0),
        (29, 32.57, "mild", 300.0),
        (30, 33.10, "moderate", 300.0),
        (33, 34.69, "moderate", 300.0),
        (34, 35.22, "moderate", 450.0),
        (50, 43.70, "moderate", 450.0),
        (63, 50.59, "moderate", 450.0),
        (64, 51.12, "strong", 450.0),
        (67, 52.71, "strong", 600.0),
        (100, 70.20, "strong", 600.0),
    ],
)
def test_severity_sets_the_anchor_class_and_rainfall(
    pilot: World, severity: int, anchor: float, storm_class: str, rain: float
) -> None:
    result = storm_of(pilot, severity=severity, scenarios=1)
    assert result.anchor_m_per_s == pytest.approx(anchor)
    assert result.storm_class == storm_class
    assert result.rain_mm == rain
    assert result.flood_stage_m == {300.0: 1.0, 450.0: 2.0, 600.0: 3.0}[rain]


def test_every_peak_wind_stays_in_the_class_band(pilot: World) -> None:
    bands = RULES.value("storm.cwa_classes")
    for severity in (10, 50, 90):
        result = storm_of(pilot, severity=severity, scenarios=8)
        low, high = bands[result.storm_class]
        for scenario in result.scenarios:
            assert scenario.track is not None
            assert low <= scenario.track.peak_wind_m_per_s <= high


@pytest.mark.parametrize("switched_on", [True, False])
def test_severity_0_or_a_switched_off_storm_brings_no_wind_and_no_flood(
    pilot: World, switched_on: bool
) -> None:
    recipe, terrain, _ = pilot
    storm = HazardSettings(switched_on=switched_on, severity=0 if switched_on else 50)
    result = build_storm(storm, 3, terrain, RULES, storm_streams(recipe.root_seed, 3))
    assert (result.storm_class, result.rain_mm, result.flood_stage_m) == (None, 0.0, 0.0)
    for scenario in result.scenarios:
        assert scenario.track is None
        assert not scenario.wind_m_per_s.any()
        assert not scenario.flood_depth_m.any()


@given(
    low=st.floats(0.0, 50.0), width=st.floats(0.1, 30.0), share=st.floats(0.0, 1.0),
    u=st.floats(0.0, 1.0),
)  # fmt: skip
def test_the_triangular_draw_stays_in_its_band(
    low: float, width: float, share: float, u: float
) -> None:
    high, mode = low + width, low + share * width
    value = stage._triangular(low, mode, high, u)
    assert low - 1e-9 <= value <= high + 1e-9
    assert stage._triangular(low, mode, high, 0.0) == pytest.approx(low)
    assert stage._triangular(low, mode, high, 1.0) == pytest.approx(high)


# --- Profile (A2 step 1, A3) ----------------------------------------------------------------


@settings(max_examples=50)
@given(peak=st.floats(17.2, 70.2), near=st.floats(0.0, 200.0), far=st.floats(0.0, 200.0))
def test_the_profile_is_the_peak_inside_the_radius_and_falls_beyond_it(
    peak: float, near: float, far: float
) -> None:
    radius = 47.5
    distances = np.array([min(near, far), max(near, far)])
    wind = stage._profile(peak, distances, radius)
    assert wind[0] >= wind[1]
    for distance, value in zip(distances, wind, strict=True):
        if distance <= radius:
            assert value == peak
        else:
            assert value == pytest.approx(peak * (radius / distance) ** 0.5)


def test_the_whole_pilot_lies_inside_the_radius_of_maximum_wind() -> None:
    assert RULES.number("storm.radius_max_wind_km") == 47.5
    assert all(s.inside_radius_share == 1.0 for s in pilot_storm().scenarios)


# --- Surface, coast and lee (A2 steps 2-4) --------------------------------------------------


def test_sea_keeps_the_open_wind_and_land_loses_17_percent_inland(
    ground: Any, pilot: World
) -> None:
    terrain = pilot[1]
    land = np.asarray(terrain.land)
    assert (ground.surface[~land] == 1.0).all()
    inland = stage._coast_distance_km(land, ground.cell_km, 1.0) >= 1.0
    open_ground = land & inland & (np.asarray(terrain.land_cover) != CoverClass.URBAN)
    assert open_ground.any()
    assert np.allclose(ground.surface[open_ground], 0.83)
    coastal = land & ~inland & (np.asarray(terrain.land_cover) != CoverClass.URBAN)
    assert ((ground.surface[coastal] > 0.83) & (ground.surface[coastal] < 1.0)).all()


def test_the_largest_city_is_the_core_and_other_cities_are_towns(ground: Any, pilot: World) -> None:
    terrain = pilot[1]
    urban = np.asarray(terrain.urban_id)
    inland = stage._coast_distance_km(np.asarray(terrain.land), ground.cell_km, 1.0) >= 1.0
    core = max(terrain.cities, key=lambda c: (c.cell_count, -c.city_id))
    in_core = inland & (urban == core.city_id)
    in_town = inland & (urban >= 0) & (urban != core.city_id)
    assert in_core.any()
    assert in_town.any()
    assert np.allclose(ground.surface[in_core], 0.83 * 0.476)
    assert np.allclose(ground.surface[in_town], 0.83 * 0.662)


def test_lee_cells_keep_0_6_of_the_wind(pilot: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stage, "_variation", lambda ground, length, stream: np.zeros((256, 256)))
    result = storm_of(pilot, scenarios=2)
    ground = stage._Ground(pilot[1], RULES)
    for scenario in result.scenarios:
        assert scenario.track is not None
        offset = stage._signed_distance_km(scenario.track, ground)
        profile = stage._profile(scenario.track.peak_wind_m_per_s, np.abs(offset), 47.5)
        factor = np.where(scenario.lee, 0.6, 1.0)
        assert scenario.lee.any()
        assert np.allclose(scenario.wind_m_per_s, profile * ground.surface * factor)


def test_the_lee_lies_across_the_spine_from_the_track(ground: Any) -> None:
    # A track far to the north-east, running along the spine: the north-east side of the crest
    # faces it, so only the south-west side can be sheltered.
    track = Track(point_km=(40.0, -10.0), direction=(0.7071, 0.7071), peak_wind_m_per_s=40.0)
    lee = stage._lee(track, stage._signed_distance_km(track, ground), ground)
    rows, columns = np.nonzero(lee)
    sides = ground.crest.side(rows.astype(np.int64), columns.astype(np.int64))
    assert lee.any()
    assert (sides == 1).all()
    far_side = ground.main_island & (
        ground.crest.side(*np.indices((GRID_CELLS, GRID_CELLS)).astype(np.int64)) == 1
    )
    assert np.count_nonzero(lee) > 0.5 * np.count_nonzero(far_side)


def test_the_crest_is_the_highest_main_island_cell_of_each_cross_section(ground: Any) -> None:
    elevation = np.asarray(ground.terrain.elevation_dm)
    crest = ground.crest
    for section in np.flatnonzero(crest.defined)[::25]:
        rows = np.arange(GRID_CELLS)
        columns = section - rows
        valid = (columns >= 0) & (columns < GRID_CELLS)
        rows, columns = rows[valid], columns[valid]
        on_island = ground.main_island[rows, columns]
        assert crest.elevation_dm[section] == elevation[rows[on_island], columns[on_island]].max()


# --- Random variation (A2 step 5, A4) -------------------------------------------------------


@functools.cache
def variation_fields() -> np.ndarray:
    ground = stage._Ground(pilot_world()[1], RULES)
    fields = [
        stage._variation(ground, 10.0, rng.stream(7, f"shared_causes/storm_corridor/{i}/variation"))
        for i in range(24)
    ]
    return np.stack(fields)


def test_the_variation_has_unit_spread_and_zero_mean() -> None:
    fields = variation_fields()
    assert abs(float(fields.mean())) < 0.1
    assert float(fields.std()) == pytest.approx(1.0, abs=0.15)


def test_the_variation_is_correlated_near_and_uncorrelated_beyond_the_length() -> None:
    fields = variation_fields()
    cell_km = pilot_world()[1].grid.cell_size_m / 1000

    def correlation(shift_km: float) -> float:
        shift = round(shift_km / cell_km)
        a, b = fields[:, :, :-shift].ravel(), fields[:, :, shift:].ravel()
        return float(np.corrcoef(a, b)[0, 1])

    assert correlation(0.5) > 0.85
    assert abs(correlation(10.5)) < 0.1


def test_the_kernel_is_wendland_and_zero_beyond_its_support() -> None:
    t = np.array([0.0, 0.25, 0.5, 1.0, 1.5])
    expected = np.array([1.0, 0.75**4 * 2.0, 0.5**4 * 3.0, 0.0, 0.0])
    assert np.allclose(stage._wendland(t), expected)


def test_the_wind_varies_by_about_ten_percent(pilot: World) -> None:
    assert RULES.value("storm.variation")["spread"] == 0.10
    plain = stage._Ground(pilot[1], RULES)
    result = pilot_storm()
    for scenario in result.scenarios[:3]:
        assert scenario.track is not None
        offset = stage._signed_distance_km(scenario.track, plain)
        base = stage._profile(scenario.track.peak_wind_m_per_s, np.abs(offset), 47.5)
        base = base * plain.surface * np.where(scenario.lee, 0.6, 1.0)
        ratio = scenario.wind_m_per_s / base
        assert float(ratio.std()) == pytest.approx(0.10, abs=0.04)


# --- Flood (B2) -----------------------------------------------------------------------------


def test_flood_depth_is_stage_less_height_above_drainage(pilot: World) -> None:
    result = pilot_storm()
    land = np.asarray(pilot[1].land)
    expected = np.where(land, np.maximum(2.0 - result.height_above_drainage_m, 0.0), 0.0)
    for scenario in result.scenarios:
        assert np.array_equal(scenario.flood_depth_m, expected)


def test_height_above_drainage_follows_the_flow_path(pilot: World) -> None:
    terrain = pilot[1]
    height = stage.height_above_drainage_m(terrain)
    river, land = np.asarray(terrain.river), np.asarray(terrain.land)
    assert (height[river] == 0.0).all()
    assert (height[~land] == 0.0).all()
    assert (height >= 0.0).all()
    elevation = np.asarray(terrain.elevation_dm)
    direction = np.asarray(terrain.flow_direction)
    rows, columns = np.nonzero(land & ~river)
    for row, column in list(zip(rows, columns, strict=True))[::997]:
        r, c = int(row), int(column)
        while land[r, c] and not river[r, c]:
            dr, dc = stage.D8_OFFSETS[int(direction[r, c])]
            r, c = r + dr, c + dc
        drain = int(elevation[r, c]) if land[r, c] else 0
        assert height[row, column] == max(int(elevation[row, column]) - drain, 0) / 10


def test_each_facility_reads_the_field_at_its_cell(pilot: World) -> None:
    result = pilot_storm()
    for record, node in zip(stage.facility_exposure(result, pilot[2]), pilot[2].nodes, strict=True):
        cell = (node.row, node.column)
        assert record.height_above_drainage_m == result.height_above_drainage_m[cell]
        assert record.wind_m_per_s == tuple(float(s.wind_m_per_s[cell]) for s in result.scenarios)
        assert record.flood_depth_m == tuple(
            max(0.0, 2.0 - record.height_above_drainage_m) for _ in result.scenarios
        )


# --- Streams and registry -------------------------------------------------------------------


def test_changing_the_scenario_count_moves_no_earlier_scenario(pilot: World) -> None:
    three = storm_of(pilot, scenarios=3)
    eight = pilot_storm()
    for a, b in zip(three.scenarios, eight.scenarios[:3], strict=True):
        assert a.track == b.track
        assert np.array_equal(a.wind_m_per_s, b.wind_m_per_s)


def test_the_stage_opens_only_its_own_scenario_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    original = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> Any:
        opened.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    storm_streams(3, 2)
    assert opened == [
        "shared_causes/storm_corridor/0/track", "shared_causes/storm_corridor/1/track",
        "shared_causes/storm_corridor/0/variation", "shared_causes/storm_corridor/1/variation",
    ]  # fmt: skip
    assert "shared_causes/storm_corridor/field" not in rng.STREAM_REGISTRY
    limit = SharedCauses.model_fields["scenarios"].metadata
    assert any(getattr(m, "le", None) == 200 for m in limit)
    assert "shared_causes/storm_corridor/199/variation" in rng.STREAM_REGISTRY


def test_every_storm_rule_is_a_dynamics_rule_in_the_storm_stage() -> None:
    storm_rules = [r for r in RULES.rules if r.id.startswith("storm.")]
    assert len(storm_rules) == 17
    assert all(r.stage == Stage.STORM for r in storm_rules)
    assert all(r.theta_role == ThetaRole.DYNAMICS for r in storm_rules)
    assert all(r.ruling is not None and r.ruling.decision == "0012" for r in storm_rules)
    assert all(r.theta_role is None for r in RULES.rules if not r.id.startswith("storm."))


def test_the_storm_defaults_follow_section_4_3b() -> None:
    storm = SharedCauses().hazards.storm_corridor
    assert storm.correlation_km == 10
    assert "17.2 + 0.53" in (HazardSettings.model_fields["severity"].description or "")


def test_the_hashes_cover_every_scenario_field() -> None:
    names = [name for name, _ in stage.storm_hashes(pilot_storm())]
    assert names[0] == "height_above_drainage_cm"
    assert len(names) == 1 + 3 * 8
