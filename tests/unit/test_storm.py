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
from swm.stages.terrain import CoverClass

RULES = load_registry()


def storm_of(
    world: World, severity: int = 50, scenarios: int = 8, mountainous: int | None = None
) -> StormResult:
    recipe, terrain, _ = world
    storm = HazardSettings(switched_on=True, severity=severity, correlation_km=10)
    relief = recipe.terrain.character.mountainous if mountainous is None else mountainous
    streams = storm_streams(recipe.root_seed, scenarios)
    return build_storm(storm, scenarios, relief, terrain, RULES, streams)


@functools.cache
def pilot_storm() -> StormResult:
    return storm_of(pilot_world())


@pytest.fixture(scope="module")
def pilot() -> World:
    return pilot_world()


@pytest.fixture(scope="module")
def ground(pilot: World) -> Any:
    return stage._Ground(pilot[1], RULES, has_lee=True)


def track_of(scenario: Any) -> Track:
    assert scenario.track is not None
    track: Track = scenario.track
    return track


# --- Severity and rainfall (B1) -------------------------------------------------------------


@pytest.mark.parametrize(
    ("severity", "anchor", "storm_class", "rung"),
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
def test_severity_sets_the_anchor_class_and_rainfall_rung(
    pilot: World, severity: int, anchor: float, storm_class: str, rung: float
) -> None:
    result = storm_of(pilot, severity=severity, scenarios=2)
    assert result.anchor_m_per_s == pytest.approx(anchor)
    assert result.storm_class == storm_class
    assert result.rain_rung_mm == rung
    for scenario in result.scenarios:
        assert rung - 75.0 <= scenario.rain_mm <= rung + 75.0
        assert scenario.flood_stage_m == pytest.approx((scenario.rain_mm - 150.0) / 150.0)


@pytest.mark.parametrize(
    ("rain", "stage_m"), [(100.0, 0.0), (150.0, 0.0), (300.0, 1.0), (450.0, 2.0), (600.0, 3.0)]
)
def test_flood_stage_rises_1_m_per_150_mm_above_150_mm(rain: float, stage_m: float) -> None:
    assert stage.flood_stage_m(rain, RULES) == pytest.approx(stage_m)


def test_every_scenario_draws_its_storm_within_the_ruled_ranges(pilot: World) -> None:
    bands = RULES.value("storm.cwa_classes")
    for severity in (10, 50, 90):
        result = storm_of(pilot, severity=severity, scenarios=8)
        low, high = bands[result.storm_class]
        for scenario in result.scenarios:
            track = track_of(scenario)
            assert low <= track.peak_wind_m_per_s <= high
            assert 0.0 <= track.closest_approach_km <= 40.0
            assert 20.0 <= track.radius_max_wind_km <= 60.0
    rains = {round(s.rain_mm, 6) for s in pilot_storm().scenarios}
    assert len(rains) == 8


@pytest.mark.parametrize("switched_on", [True, False])
def test_severity_0_or_a_switched_off_storm_brings_no_wind_and_no_flood(
    pilot: World, switched_on: bool
) -> None:
    recipe, terrain, _ = pilot
    storm = HazardSettings(switched_on=switched_on, severity=0 if switched_on else 50)
    result = build_storm(storm, 3, 50, terrain, RULES, storm_streams(recipe.root_seed, 3))
    assert (result.storm_class, result.rain_rung_mm) == (None, 0.0)
    for scenario in result.scenarios:
        assert scenario.track is None
        assert (scenario.rain_mm, scenario.flood_stage_m) == (0.0, 0.0)
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


# --- Track and profile (A2 step 1, A3) ------------------------------------------------------


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


def test_the_track_passes_its_closest_approach_from_the_island_centre(ground: Any) -> None:
    cx, cy = ground.centre_km
    for scenario in pilot_storm().scenarios:
        track = track_of(scenario)
        east, south = track.direction
        px, py = track.point_km
        distance = abs((cx - px) * (-south) + (cy - py) * east)
        assert distance == pytest.approx(track.closest_approach_km)


def test_the_share_inside_the_radius_follows_each_scenarios_track(ground: Any) -> None:
    land = ground.land
    shares = []
    for scenario in pilot_storm().scenarios:
        track = track_of(scenario)
        distance = np.abs(stage._signed_distance_km(track, ground))
        expected = np.count_nonzero(land & (distance <= track.radius_max_wind_km))
        assert scenario.inside_radius_share == pytest.approx(expected / np.count_nonzero(land))
        shares.append(scenario.inside_radius_share)
    assert min(shares) < 1.0


# --- Surface, coast and lee (A2 steps 2-4) --------------------------------------------------


def test_sea_keeps_the_open_wind_and_land_loses_17_percent_inland(
    ground: Any, pilot: World
) -> None:
    terrain = pilot[1]
    land, cover = np.asarray(terrain.land), np.asarray(terrain.land_cover)
    assert (ground.surface[~land] == 1.0).all()
    inland = stage._coast_distance_km(land, ground.cell_km, 1.0) >= 1.0
    plain = (cover != CoverClass.URBAN) & (cover != CoverClass.FOREST)
    open_ground = land & inland & plain
    assert open_ground.any()
    assert np.allclose(ground.surface[open_ground], 0.83)
    coastal = land & ~inland & plain
    assert ((ground.surface[coastal] > 0.83) & (ground.surface[coastal] < 1.0)).all()


def test_wooded_land_takes_the_town_factor(ground: Any, pilot: World) -> None:
    terrain = pilot[1]
    land, cover = np.asarray(terrain.land), np.asarray(terrain.land_cover)
    inland = stage._coast_distance_km(land, ground.cell_km, 1.0) >= 1.0
    wooded = land & inland & (cover == CoverClass.FOREST)
    assert wooded.any()
    assert np.allclose(ground.surface[wooded], 0.83 * 0.662)
    for bare in (CoverClass.WETLAND, CoverClass.BARREN):
        cells = land & inland & (cover == bare)
        assert np.allclose(ground.surface[cells], 0.83)


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
    ground = stage._Ground(pilot[1], RULES, has_lee=True)
    for scenario in result.scenarios:
        track = track_of(scenario)
        offset = stage._signed_distance_km(track, ground)
        profile = stage._profile(track.peak_wind_m_per_s, np.abs(offset), track.radius_max_wind_km)
        factor = np.where(scenario.lee, 0.6, 1.0)
        assert scenario.lee.any()
        assert np.allclose(scenario.wind_m_per_s, profile * ground.surface * factor)


def _side_of_spine(spine: Any, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Side of the spine's overall line (first to last point) each place lies on."""
    (ax, ay), (bx, by) = spine[0], spine[-1]
    return np.sign((bx - ax) * (y - ay) - (by - ay) * (x - ax))


def test_the_lee_lies_across_the_spine_line_from_the_track(ground: Any) -> None:
    # A track far to the north-east, running along the spine: only the south-west side of the
    # spine line has the line between it and the track.
    track = Track((40.0, -10.0), (0.7071, 0.7071), 40.0, 30.0, 40.0)
    lee = stage._lee(track, stage._signed_distance_km(track, ground), ground)
    spine = ground.terrain.spine_km
    side = _side_of_spine(spine, ground.x_km, ground.y_km)
    track_side = _side_of_spine(spine, np.array([40.0]), np.array([-10.0]))[0]
    assert lee.any()
    # The chord stands in for the curved spine, so a few cells near the bends fall either side.
    assert np.count_nonzero(side[lee] == -track_side) >= 0.99 * np.count_nonzero(lee)
    far = ground.land & (side == -track_side)
    assert np.count_nonzero(lee) > 0.8 * np.count_nonzero(far)


def test_a_flat_island_has_no_lee(pilot: World) -> None:
    result = storm_of(pilot, scenarios=2, mountainous=0)
    assert not any(scenario.lee.any() for scenario in result.scenarios)


# --- Random variation (A2 step 5, A4) -------------------------------------------------------


@functools.cache
def variation_fields() -> np.ndarray:
    ground = stage._Ground(pilot_world()[1], RULES, has_lee=True)
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


def test_the_wind_varies_by_about_ten_percent(ground: Any) -> None:
    assert RULES.value("storm.variation")["spread"] == 0.10
    for scenario in pilot_storm().scenarios[:3]:
        track = track_of(scenario)
        offset = stage._signed_distance_km(track, ground)
        base = stage._profile(track.peak_wind_m_per_s, np.abs(offset), track.radius_max_wind_km)
        base = base * ground.surface * np.where(scenario.lee, 0.6, 1.0)
        ratio = scenario.wind_m_per_s / base
        assert float(ratio.std()) == pytest.approx(0.10, abs=0.04)


# --- Flood (B2) -----------------------------------------------------------------------------


def test_flood_depth_is_each_scenarios_stage_less_height_above_drainage(pilot: World) -> None:
    result = pilot_storm()
    land = np.asarray(pilot[1].land)
    for scenario in result.scenarios:
        stage_m = scenario.flood_stage_m
        expected = np.where(land, np.maximum(stage_m - result.height_above_drainage_m, 0.0), 0.0)
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


@pytest.mark.parametrize(
    ("node_class", "threshold"),
    [
        ("generation", 3.2),
        ("transmission_substation", 3.2),
        ("distribution_substation", 1.2),
        ("refinery", 1.2),
        ("import_terminal", 1.2),
        ("tank_farm", 0.0),
        ("tertiary", 0.15),
        ("storage", 7.3),
        ("mast", 1.2),
        ("bridge", None),
        ("freight_yard", None),
        ("road_junction", None),
        ("seaport", None),
    ],
)
def test_flood_thresholds_follow_section_4_3b(node_class: str, threshold: float | None) -> None:
    value = stage.flood_threshold_m(node_class, RULES)
    assert value == (None if threshold is None else pytest.approx(threshold))


@pytest.mark.parametrize(
    ("depth", "threshold", "out"),
    [(0.0, 0.0, False), (0.01, 0.0, True), (1.2, 1.2, False), (1.21, 1.2, True),
     (3.1, 3.2, False), (5.0, None, False)],
)  # fmt: skip
def test_a_facility_floods_out_above_its_threshold(
    depth: float, threshold: float | None, out: bool
) -> None:
    assert stage._floods_out(depth, threshold) is out


def test_each_facility_reads_the_field_at_its_cell(pilot: World) -> None:
    result = pilot_storm()
    records = stage.facility_exposure(result, pilot[2], RULES)
    for record, node in zip(records, pilot[2].nodes, strict=True):
        cell = (node.row, node.column)
        assert record.height_above_drainage_m == result.height_above_drainage_m[cell]
        assert record.wind_m_per_s == tuple(float(s.wind_m_per_s[cell]) for s in result.scenarios)
        assert record.flood_depth_m == tuple(
            max(0.0, s.flood_stage_m - record.height_above_drainage_m) for s in result.scenarios
        )
        assert record.flood_threshold_m == stage.flood_threshold_m(node.node_class.value, RULES)
        assert record.floods_out == tuple(
            stage._floods_out(depth, record.flood_threshold_m) for depth in record.flood_depth_m
        )


# --- Streams and registry -------------------------------------------------------------------


def test_changing_the_scenario_count_moves_no_earlier_scenario(pilot: World) -> None:
    three = storm_of(pilot, scenarios=3)
    eight = pilot_storm()
    for a, b in zip(three.scenarios, eight.scenarios[:3], strict=True):
        assert a.track == b.track
        assert a.rain_mm == b.rain_mm
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
    assert len(storm_rules) == 28
    assert all(r.stage == Stage.STORM for r in storm_rules)
    assert all(r.theta_role == ThetaRole.DYNAMICS for r in storm_rules)
    assert all(r.ruling is not None and r.ruling.decision in ("0012", "0013") for r in storm_rules)
    assert all(r.theta_role is None for r in RULES.rules if not r.id.startswith("storm."))


def test_changed_storm_rules_keep_their_old_values_in_history() -> None:
    for rule_id in (
        "storm.radius_max_wind_km", "storm.flood_stage_m", "storm.surface_factors",
        "storm.flood_functional_depth_m", "storm.flood_not_damaged",
    ):  # fmt: skip
        history = RULES.rule(rule_id).history
        assert len(history) == 1
        assert history[0].decision == "0012"
    assert RULES.rule("storm.radius_max_wind_km").history[0].value == 47.5


def test_the_storm_defaults_follow_section_4_3b() -> None:
    storm = SharedCauses().hazards.storm_corridor
    assert storm.correlation_km == 10
    assert "17.2 + 0.53" in (HazardSettings.model_fields["severity"].description or "")


def test_the_hashes_cover_every_scenario_field() -> None:
    names = [name for name, _ in stage.storm_hashes(pilot_storm())]
    assert names[0] == "height_above_drainage_cm"
    assert len(names) == 1 + 3 * 8


def test_the_spine_line_runs_north_west_to_south_east(pilot: World) -> None:
    spine = pilot[1].spine_km
    (x0, y0), (x1, y1) = spine[0], spine[-1]
    assert len(spine) > 2
    assert x1 > x0
    assert y1 > y0
