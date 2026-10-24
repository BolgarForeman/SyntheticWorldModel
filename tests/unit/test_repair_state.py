"""A damaged facility is repaired at the damage state it was given (decision 0019).

A storm-damaged facility takes the repair record for the state its scenario drew; a strike takes
complete damage, named explicitly (ruling Q4). Nothing falls through to the last record listed.

Spec: structure v0.7 §4.4a (repair by damage state); WO-10a answers, 5.
"""

import functools
from pathlib import Path
from typing import Any

import pytest

from swm.cli import _built, _engine
from swm.dynamics.engine import facility_repair, simulate
from swm.dynamics.records import RunRequest
from swm.dynamics.world import Damage
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import DamageState
from swm.solve.runner import with_node

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PILOT = FIXTURES / "pilot_hand_check.yaml"
SEVERITY_70 = FIXTURES / "storm_sensitivity" / "pilot_severity_70.yaml"
NODE = "SWM-POW-0002"
WINDOW_H = 72.0
"""A transmission substation: repairable, with a record at every damage state."""


@functools.cache
def world_of(path: Path) -> tuple[Any, Any]:
    resolution = resolve(load_recipe(path))
    built = _built(resolution)
    return built, _engine(resolution, built)


def stage_record(state: DamageState) -> Any:
    built, _ = world_of(PILOT)
    return next(p for p in built.repair.permanent if p.node_id == NODE and p.damage_state == state)


@pytest.mark.parametrize("state", list(DamageState))
def test_a_facility_takes_the_crew_work_and_lead_time_of_its_damage_state(
    state: DamageState,
) -> None:
    _, engine = world_of(PILOT)
    damage = Damage((NODE,), (), (), states=((NODE, state.value),))
    record = facility_repair(engine.world, damage, NODE)
    assert record is not None
    assert record.damage_state == state.value
    stage = stage_record(state)
    assert record.crew_work_h == stage.crew_work_h
    lead = engine.world.settings.crew_bound_lead_h
    # Slight and moderate repairs use stocked spares: no parts wait (ruling R2).
    no_wait = state in (DamageState.SLIGHT, DamageState.MODERATE)
    expected_parts = 0.0 if no_wait else max(0.0, stage.lead_time_h - lead)
    assert record.parts_lead_h == pytest.approx(expected_parts)
    run = simulate(engine.world, RunRequest(damage))
    work = [e for _, log in run.crews for e in log if e.job_id == f"repair:{NODE}"]
    if record.parts_lead_h >= WINDOW_H:
        # The rebuild does not open inside the window; the quick path does (ruling R3).
        assert not work
        assert [e for _, log in run.crews for e in log if e.job_id == f"quick:{NODE}"]
        return
    repair = next(e for e in work if e.activity == "repair")
    assert repair.end_h - repair.start_h == pytest.approx(stage.crew_work_h)
    assert work[0].start_h >= record.parts_lead_h


def test_the_four_states_take_four_different_repairs() -> None:
    _, engine = world_of(PILOT)
    hours = {
        state: facility_repair(engine.world, Damage((NODE,), (), (), ((NODE, state.value),)), NODE)
        for state in DamageState
    }
    assert len({(r.crew_work_h, r.parts_lead_h) for r in hours.values() if r is not None}) == 4


def test_a_strike_takes_complete_damage_explicitly() -> None:
    _, engine = world_of(PILOT)
    struck = with_node(Damage((), (), ()), NODE)
    assert struck.state_of(NODE) == DamageState.COMPLETE.value
    record = facility_repair(engine.world, struck, NODE)
    assert record is not None
    assert record.crew_work_h == stage_record(DamageState.COMPLETE).crew_work_h


def test_a_strike_on_a_flood_damaged_node_raises_it_to_complete() -> None:
    flooded = Damage((NODE,), (), (), ((NODE, DamageState.SLIGHT.value),))
    assert with_node(flooded, NODE).state_of(NODE) == DamageState.COMPLETE.value


def test_a_node_with_several_records_and_no_state_is_refused() -> None:
    _, engine = world_of(PILOT)
    with pytest.raises(ValueError, match="names no damage state"):
        facility_repair(engine.world, Damage((NODE,), (), ()), NODE)


def test_the_storm_damage_carries_each_facilitys_drawn_state() -> None:
    built, engine = world_of(SEVERITY_70)
    for scenario, damage in zip(built.scenarios.scenarios, engine.damage, strict=True):
        drawn = {f.node_id: f.damage_state.value for f in scenario.facilities}
        assert dict(damage.states) == drawn
    assert engine.damage[5].state_of("SWM-POW-0001") == DamageState.SLIGHT.value
