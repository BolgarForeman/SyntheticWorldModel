"""Hand trace: the engine's scenario 7 run matches the design side's sealed hand trace.

The expected values in ``tests/fixtures/hand_trace_scenario_7.yaml`` were written by hand,
before any engine result was seen, and recomputed under Foreman's travel ruling of 2026-10-19.
They are never regenerated from the engine; a mismatch is reported, not fixed in the fixture
(CLAUDE.md §10).

The trace worked at the engine's 15-minute step, so every hour is compared at the step, exactly:
an event's step hour is the first step at or after it, where the engine applies its effect.
``null`` means not within the horizon.

Spec: Work Order 9, F1 and F2, as changed by the WO-09c answers (F0: this is the Phase 1
hand-trace acceptance test); structure v0.15 §4.5.
"""

import functools
import math
from pathlib import Path

import pytest
import yaml

from swm.cli import _engine
from swm.dynamics.engine import simulate
from swm.dynamics.records import CrewEntry, Run, RunRequest
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.trace_game.content import answer_score

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PILOT = FIXTURES / "pilot_hand_check.yaml"
TRACE = FIXTURES / "hand_trace_scenario_7.yaml"
PREFIX = "SWM-"
"""The trace names elements without the synthetic-identifier prefix."""
REPAIR_JOB = "repair:"
SWITCHING = "switching"


@functools.cache
def expected() -> dict[str, object]:
    loaded: dict[str, object] = yaml.safe_load(TRACE.read_text(encoding="utf-8"))
    return loaded


@functools.cache
def scenario_run() -> tuple[Run, tuple[str, ...], tuple[str, ...], float]:
    """The engine's run of the trace's scenario: the run, its damage, end uses and score."""
    engine = _engine(resolve(load_recipe(PILOT)))
    scenario = int(str(expected()["scenario"]))
    damage = engine.damage[scenario]
    run = simulate(engine.world, RunRequest(damage, scenario=scenario))
    score = answer_score(run, engine.world)["weighted_service_hours_lost"]
    return run, damage.lines + damage.nodes, engine.end_use, score


def step_hour(hour_h: float, run: Run) -> float | None:
    """Return the step at which an event at this hour takes effect, or None past the horizon."""
    step = run.step_h * math.ceil(hour_h / run.step_h - 1e-9)
    return None if step > run.horizon_h else step


def ours(element: str) -> str:
    return PREFIX + element


def entries(run: Run, crew: str) -> tuple[CrewEntry, ...]:
    return dict(run.crews)[crew]


# --- The world and the scenario -------------------------------------------------------------


def test_the_trace_is_of_the_pilot_scenario_and_horizon_the_engine_ran() -> None:
    run, damage, _, _ = scenario_run()
    assert expected()["world"] == "pilot"
    assert run.horizon_h == expected()["horizon_h"]
    assert run.step_h == 0.25
    assert sorted(damage) == sorted(ours(e) for e in expected()["damage"])  # type: ignore[attr-defined]


# --- Crews ----------------------------------------------------------------------------------


def crew_jobs() -> list[tuple[str, dict[str, object]]]:
    crews = expected()["crews"]
    assert isinstance(crews, dict)
    return [(crew, job) for crew, jobs in sorted(crews.items()) for job in jobs]


def test_each_crew_takes_the_traced_jobs_in_order() -> None:
    run, _, _, _ = scenario_run()
    crews = expected()["crews"]
    assert isinstance(crews, dict)
    for crew, jobs in crews.items():
        taken = list(dict.fromkeys(e.job_id for e in entries(run, crew)))
        assert taken == [REPAIR_JOB + ours(job["job"]) for job in jobs], crew


@pytest.mark.parametrize(
    ("crew", "job"), crew_jobs(), ids=lambda v: v if isinstance(v, str) else v["job"]
)
def test_each_crew_arrives_prepares_and_finishes_at_the_traced_step(
    crew: str, job: dict[str, object]
) -> None:
    run, _, _, _ = scenario_run()
    stretches = [e for e in entries(run, crew) if e.job_id == REPAIR_JOB + ours(str(job["job"]))]
    activities = [e.activity for e in stretches]
    assert activities[0] == "travel"
    assert activities[1] == "assess"
    repairs = [e for e in stretches if e.activity == "repair"]
    assert step_hour(stretches[0].end_h, run) == job["arrives_h"]
    assert step_hour(stretches[1].end_h, run) == job["prepared_h"]
    assert step_hour(repairs[-1].end_h, run) == job["done_h"]
    if "failure_points_done_h" in job:
        assert [step_hour(e.end_h, run) for e in repairs] == job["failure_points_done_h"]
    else:
        assert len(repairs) == 1


# --- Repairs, hours out and the score -------------------------------------------------------


def test_each_repair_is_back_in_service_at_the_traced_step() -> None:
    run, _, _, _ = scenario_run()
    back = {c.element_id: c.time_h for c in run.completions if c.kind in ("line", "facility")}
    traced = expected()["repairs_back_in_service_h"]
    assert isinstance(traced, dict)
    assert set(back) <= {ours(element) for element in traced}
    for element, hour in traced.items():
        assert back.get(ours(element)) == hour, element


def test_hours_out_match_for_every_end_use_node() -> None:
    run, _, end_use, _ = scenario_run()
    traced = expected()["hours_out"]
    assert isinstance(traced, dict)
    assert sorted(ours(node) for node in traced) == sorted(end_use)
    assert {ours(node): hours for node, hours in traced.items()} == dict(run.hours_out)


def test_the_score_matches() -> None:
    run, _, _, weighted = scenario_run()
    score = expected()["score"]
    assert isinstance(score, dict)
    assert weighted == score["weighted_service_hours_lost"]
    assert math.fsum(run.hours_out.values()) == score["hours_out"]


def test_named_nodes_hold_the_traced_state_at_the_named_steps() -> None:
    run, _, _, _ = scenario_run()
    states = expected()["states"]
    assert isinstance(states, list)
    for row in states:
        assert run.at(ours(row["node"]), row["hour_h"]) == row["state"], row


# --- What did not happen --------------------------------------------------------------------


def test_no_stock_is_drawn() -> None:
    run, _, _, _ = scenario_run()
    assert expected()["no_stock_drawn"] is True
    for stock_id in run.stock_ids:
        assert len(set(run.level(stock_id))) == 1, stock_id


def test_no_fuel_is_delivered() -> None:
    run, _, _, _ = scenario_run()
    assert expected()["no_fuel_delivery"] is True
    assert run.deliveries == ()


def test_no_crew_switches_anything_by_hand() -> None:
    run, _, _, _ = scenario_run()
    assert expected()["no_manual_switching"] is True
    assert not [c for c in run.completions if c.kind == SWITCHING]
    assert not [e for _, crew in run.crews for e in crew if e.activity == "switch"]
