from typing import Any

import pytest

from buffers_helpers import NO_GAPS, buffers_of
from couplings_helpers import World, requirements_of, rich_world
from swm import rng
from swm.recipe.schema import Layer, NodeClass
from swm.rules.registry import load_registry
from swm.stages.buffers import buffers_streams

RULES = load_registry()
C = NodeClass


@pytest.fixture(scope="module")
def rich() -> World:
    return rich_world()


@pytest.fixture(scope="module")
def exact(rich: World) -> Any:
    """Every lever at 0 and every class gap at 0: each reserve sits on its §4.4a target."""
    return buffers_of(rich, overrides=NO_GAPS)


def nodes(world: World) -> dict[str, Any]:
    return {n.node_id: n for n in requirements_of(world).layers.nodes}


# --- Reserves (D1) --------------------------------------------------------------------------

TARGET_HOURS = {
    (C.EXCHANGE, "generator_fuel"): 24.0,
    (C.DATA_CENTRE, "generator_fuel"): 72.0,
    (C.CABLE_LANDING, "generator_fuel"): 48.0,
    (C.TREATMENT, "generator_fuel"): 48.0,
    (C.PUMPING, "generator_fuel"): 24.0,
    (C.TERTIARY, "generator_fuel"): 72.0,
    (C.REGIONAL, "generator_fuel"): 72.0,
    (C.BLOOD_BANK, "generator_fuel"): 72.0,
    (C.MAST, "battery"): 4.0,
    (C.EXCHANGE, "battery"): 4.0,
    (C.TERTIARY, "water"): 72.0,
    (C.REGIONAL, "water"): 72.0,
    (C.TERTIARY, "supplies"): 72.0,
    (C.REGIONAL, "supplies"): 72.0,
    (C.BLOOD_BANK, "blood"): 7 * 24.0,
    (C.STORAGE, "distribution_water"): 12.0,
    (C.IMPORT_TERMINAL, "lng"): 11 * 24.0,
    (C.GENERATION, "coal"): 30 * 24.0,
}
"""Structure v0.6 §4.4a, in buffer hours at the expected draw."""


def test_at_zero_levers_buffer_hours_are_the_section_4_4a_targets(exact: Any, rich: World) -> None:
    by_id = nodes(rich)
    seen = set()
    for reserve in exact.reserves:
        key = (by_id[reserve.node_id].node_class, reserve.kind)
        if reserve.kind in ("oil_industry", "oil_government"):
            expected = 60 * 24.0 if reserve.kind == "oil_industry" else 30 * 24.0
        else:
            expected = TARGET_HOURS[key]
        assert reserve.hours == pytest.approx(expected), key
        assert reserve.stock == pytest.approx(reserve.hours * reserve.draw_per_h)
        seen.add(reserve.kind)
    assert {"generator_fuel", "battery", "water", "supplies", "blood", "oil_industry"} <= seen


def test_hospital_generators_burn_at_the_essential_load(exact: Any, rich: World) -> None:
    requirements = {r.node_id: r for r in requirements_of(rich).nodes}
    by_id = nodes(rich)
    hospital_fuel = [
        r for r in exact.reserves
        if r.kind == "generator_fuel" and by_id[r.node_id].node_class in (C.TERTIARY, C.REGIONAL)
    ]  # fmt: skip
    assert hospital_fuel
    for reserve in hospital_fuel:
        load = requirements[reserve.node_id].electricity_mw * 0.6
        assert reserve.draw_per_h == pytest.approx(load * 269.0)


def test_hospital_water_is_held_at_the_emergency_ration(exact: Any, rich: World) -> None:
    by_id = nodes(rich)
    for reserve in (r for r in exact.reserves if r.kind == "water"):
        beds = float(dict(by_id[reserve.node_id].attributes)["bed_count"])
        assert reserve.draw_per_h == pytest.approx(beds * 300 / 1000 / 24)
        assert reserve.stock == pytest.approx(beds * 0.3 * 3)


def test_the_section_4_4a_gaps_move_the_median(rich: World) -> None:
    result = buffers_of(rich)
    by_id = nodes(rich)
    for reserve in result.reserves:
        node_class = by_id[reserve.node_id].node_class
        if node_class in (C.TERTIARY, C.REGIONAL):
            assert reserve.compliance_gap == pytest.approx(0.15)
            assert reserve.hours == pytest.approx(reserve.target_hours * 0.85)
        if node_class in (C.TREATMENT, C.PUMPING, C.STORAGE):
            assert reserve.compliance_gap == pytest.approx(0.2)


def test_other_classes_take_the_recipes_gap(rich: World) -> None:
    result = buffers_of(rich, gap_pct=40)
    blood = [r for r in result.reserves if r.kind == "blood"]
    assert blood
    assert all(r.compliance_gap == pytest.approx(0.4) for r in blood)


def test_oil_stocks_are_shared_by_tank_capacity(exact: Any, rich: World) -> None:
    by_id = nodes(rich)
    industry = [r for r in exact.reserves if r.kind == "oil_industry"]
    assert industry
    storage = {r.node_id: float(dict(by_id[r.node_id].attributes)["storage_m3"]) for r in industry}
    total = sum(storage.values())
    draw = sum(r.draw_per_h for r in industry)
    for reserve in industry:
        assert reserve.draw_per_h == pytest.approx(draw * storage[reserve.node_id] / total)
    government = [r for r in exact.reserves if r.kind == "oil_government"]
    assert {by_id[r.node_id].node_class for r in government} == {C.TANK_FARM}


def test_heterogeneity_spreads_the_hours(rich: World) -> None:
    spread = buffers_of(rich, heterogeneity_pct=50, overrides=NO_GAPS)
    ratios = [r.hours / r.target_hours for r in spread.reserves]
    assert min(ratios) < 1.0 < max(ratios)
    assert all(r > 0 for r in ratios)


# --- Presence and availability (D2, D3) -----------------------------------------------------


def test_backup_presence_comes_from_the_subtype_attributes(exact: Any, rich: World) -> None:
    by_id = nodes(rich)
    for backup in exact.backups:
        node = by_id[backup.node_id]
        assert backup.has_generator == (dict(node.subtype).get("standby_fuel") == "diesel")
        assert backup.has_battery == (node.node_class in (C.MAST, C.EXCHANGE))
    fuelled = {r.node_id for r in exact.reserves if r.kind == "generator_fuel"}
    generators = {b.node_id for b in exact.backups if b.has_generator}
    assert fuelled <= generators


def test_a_gap_of_95_is_the_most_the_recipe_allows() -> None:
    from pydantic import ValidationError

    from swm.recipe.schema import ContinuousDrawnQuantity

    ContinuousDrawnQuantity(compliance_gap_pct=95)
    with pytest.raises(ValidationError, match="compliance_gap_pct"):
        ContinuousDrawnQuantity(compliance_gap_pct=96)


def test_generators_draw_their_availability_from_marqusee_and_jenket(rich: World) -> None:
    well = buffers_of(rich)
    generators = [b for b in well.backups if b.has_generator]
    assert generators
    assert all(b.well_maintained for b in generators)
    top = 1662.0 * RULES.value("draws.exponential_table")["quantiles"][-1]
    assert all(0 < (b.run_hours_to_failure or 0) <= top for b in generators)
    poor = buffers_of(
        rich, overrides={"reserves.generator_availability.well_maintained_share": 0.0}
    )
    assert not any(b.well_maintained for b in poor.backups if b.has_generator)
    certain = {"well_maintained": {"fail_to_start": 1.0, "mttf_h": 1662.0},
               "poorly_maintained": {"fail_to_start": 1.0, "mttf_h": 61.0}}  # fmt: skip
    failing = buffers_of(rich, overrides={"reserves.generator_availability": certain})
    assert all(b.fails_to_start for b in failing.backups if b.has_generator)
    assert all(b.fails_to_start is None for b in well.backups if not b.has_generator)


# --- Resupply (D4) --------------------------------------------------------------------------


def test_buffer_edges_carry_the_resupply_parameters(exact: Any, rich: World) -> None:
    requirements = {r.node_id: r for r in requirements_of(rich).nodes}
    by_id = nodes(rich)
    assert exact.resupply
    for record in exact.resupply:
        assert record.lead_time_h == 12.0
        assert record.delivery_h == 24.0
        load = requirements[record.consumer_id].electricity_mw
        if by_id[record.consumer_id].node_class in (C.TERTIARY, C.REGIONAL):
            load *= 0.6
        assert record.delivery_l == pytest.approx(24.0 * load * 269.0)


# --- Tolerance (F1) -------------------------------------------------------------------------


def test_the_tolerance_buffer_takes_the_public_share(exact: Any, rich: World) -> None:
    by_id = nodes(rich)
    assert exact.tolerance
    for record in exact.tolerance:
        assert record.d_eff == pytest.approx(1 - record.public_share * (1 - record.d))
        node = by_id[record.consumer_id]
        if node.node_class == C.GENERATION:
            assert (record.t_h, record.d, record.public_share) == (12.0, 0.95, 0.2)
        if node.node_class in (C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION):
            assert record.slows_switching
            assert record.d == 1.0
        if node.node_class in (C.TERTIARY, C.REGIONAL):
            hosted = dict(node.subtype)["records_hosted"] is True
            expected = (0.5, 4.0, 0.65) if hosted else (24.0, None, 0.85)
            assert (record.t_h, record.ramp_to_h, record.d) == expected
            assert record.public_share == 1.0


# --- Failure modes (F2) ---------------------------------------------------------------------


def test_failure_modes_follow_the_defaults_and_the_class_departures(
    exact: Any, rich: World
) -> None:
    by_id = nodes(rich)
    generators = {b.node_id for b in exact.backups if b.has_generator}
    assert exact.failure_modes
    for mode in exact.failure_modes:
        node = by_id[mode.node_id]
        assert not mode.departed
        if node.node_class in (C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION,
                               C.TREATMENT, C.PUMPING):  # fmt: skip
            expected = "throttle"
        elif node.node_class in (C.TERTIARY, C.REGIONAL) and mode.supplier_layer == Layer.POWER:
            expected = "step_to_floor" if node.node_id in generators else "trip"
        elif (node.node_class == C.AIRPORT and mode.supplier_layer == Layer.TELECOM
              and dict(node.subtype)["towered"] is True):  # fmt: skip
            expected = "trip"
        else:
            expected = "trip" if mode.dependency_type == "physical_flow" else "throttle"
        assert mode.mode == expected, (mode.node_id, mode.supplier_layer)
        assert (mode.floor == 0.6) == (mode.mode == "step_to_floor")


def test_heterogeneity_is_the_share_departing_per_layer(rich: World) -> None:
    from swm.stages.couplings import _percent_of

    base = buffers_of(rich)
    mixed = buffers_of(rich, failure_heterogeneity_pct=10)
    by_id = nodes(rich)
    expected = 0
    for layer in Layer:
        count = sum(by_id[m.node_id].layer == layer for m in mixed.failure_modes)
        expected += _percent_of(10, count)
    assert sum(m.departed for m in mixed.failure_modes) == expected
    for before, after in zip(base.failure_modes, mixed.failure_modes, strict=True):
        assert (before.mode != after.mode) == after.departed


# --- Streams --------------------------------------------------------------------------------


def test_the_stage_opens_only_its_own_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    original = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> Any:
        opened.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    buffers_streams(3)
    roots = {path.split("/")[0] for path in opened}
    assert roots == {"reserves", "availability", "failure_mode"}
    assert "unobserved/reserves" not in rng.STREAM_REGISTRY
    assert "unobserved/failure_mode" not in rng.STREAM_REGISTRY
