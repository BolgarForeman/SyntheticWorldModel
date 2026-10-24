"""Repair timing and the engine fixes (Work Order 11).

B1-B5: the two repair paths, the rebuild, opened only when its parts are ready, and the quick
path that gives a heavily damaged node service back inside the window. The two bug fixes, A1
and A2, are in ``test_engine_fixes.py``.

Spec: structure v0.19 §4.4a and §4.5 (repair and crews); repair timing rulings R1-R5; MIP sheet
Part 3 (E1, E2) and item 11; Work Order 11, Parts A and B.
"""

from dataclasses import replace
from typing import Any

import pytest

from dynamics_helpers import RULES, TARGET, OneNode
from solve_helpers import pilot_inputs
from swm.dynamics.engine import QUICK, simulate
from swm.dynamics.records import CrewEntry, Run, RunRequest
from swm.dynamics.world import CrewStart, Damage, FacilityRepair, QuickPath
from swm.recipe.schema import Layer, NodeClass
from swm.solve.restorative import repair_jobs
from swm.solve.runner import with_node

STEP_H = 0.25
LEAD_H = 2.0
WINDOW_H = 72.0
CALM = Damage((), (), ())


def world() -> Any:
    return pilot_inputs().world


def entries(run: Run, job_id: str) -> list[CrewEntry]:
    return [e for _, log in run.crews for e in log if e.job_id == job_id]


def damaged(node: str, state: str) -> Damage:
    return Damage((node,), (), (), ((node, state),))


# --- B1, B2: the rebuild path ---------------------------------------------------------------


def test_a_rebuild_job_never_dispatches_before_its_parts_are_ready() -> None:
    node = OneNode(NodeClass.CLINIC, Layer.HEALTHCARE)
    node.repairs.append(FacilityRepair(TARGET, 5.0, 8.0))
    test_world = replace(node.world(), crews=(CrewStart("crew 1", (0.0, 0.0)),))
    run = simulate(test_world, RunRequest(Damage((TARGET,), (), ())))
    work = entries(run, f"repair:{TARGET}")
    assert work[0].start_h == 5.0
    assert [e.activity for e in work] == ["travel", "assess", "repair"]
    assert not [e for _, log in run.crews for e in log if e.activity == "wait for parts"]


@pytest.mark.parametrize(("state", "work_h"), [("slight", 8.0), ("moderate", 24.0)])
def test_slight_and_moderate_damage_come_back_after_travel_assessment_and_work(
    state: str, work_h: float
) -> None:
    node = "SWM-HLT-0002"
    run = simulate(world(), RunRequest(damaged(node, state)))
    travel, assess, repair = entries(run, f"repair:{node}")
    assert travel.start_h == 0.0
    assert assess.end_h - assess.start_h == pytest.approx(LEAD_H)
    assert repair.end_h - repair.start_h == pytest.approx(work_h)
    assert repair.start_h == travel.end_h + LEAD_H
    done = next(c.time_h for c in run.completions if c.element_id == node)
    assert repair.end_h <= done < repair.end_h + STEP_H


# --- B3, B4: the quick path -----------------------------------------------------------------

QUICK_CLASSES = {
    NodeClass.TRANSMISSION_SUBSTATION: Layer.POWER,
    NodeClass.PUMPING: Layer.WATER,
    NodeClass.STORAGE: Layer.WATER,
    NodeClass.AIRPORT: Layer.TRANSPORT,
}


def one_struck_node(node_class: NodeClass, layer: Layer) -> tuple[Run, float, float]:
    """A node of the class, struck at complete damage in a world where nothing else fails."""
    row = RULES.value("repair.service_restore.quick_paths")[node_class.value]
    work_h, share = float(row["crew_work_h"]), float(row["restored_share"])
    node = OneNode(node_class, layer)
    node.repairs.append(FacilityRepair(TARGET, 1000.0, 168.0, "complete"))
    test_world = replace(node.world(), crews=(CrewStart("crew 1", (0.0, 0.0)),),
                         quick_paths=(QuickPath(TARGET, work_h, share),))  # fmt: skip
    return simulate(test_world, RunRequest(with_node(CALM, TARGET))), work_h, share


@pytest.mark.parametrize(("node_class", "layer"), list(QUICK_CLASSES.items()))
def test_each_quick_path_class_comes_back_at_its_share_after_travel_assessment_and_work(
    node_class: NodeClass, layer: Layer
) -> None:
    run, work_h, share = one_struck_node(node_class, layer)
    travel, assess, work = entries(run, f"{QUICK}:{TARGET}")
    assert travel.start_h == 0.0
    assert assess.end_h - assess.start_h == pytest.approx(LEAD_H)
    assert work.end_h - work.start_h == pytest.approx(work_h)
    done = next(c.time_h for c in run.completions if c.kind == QUICK)
    assert work.end_h <= done < work.end_h + STEP_H
    assert run.at(TARGET, done) == share
    assert run.at(TARGET, done - STEP_H) == 0.0
    assert not entries(run, f"repair:{TARGET}")  # the rebuild's parts are not in


@pytest.mark.parametrize(("node", "share"), [("SWM-WAT-0004", 1.0), ("SWM-TRN-0002", 0.5)])
def test_a_struck_pilot_node_with_a_quick_path_serves_again_at_its_share(
    node: str, share: float
) -> None:
    run = simulate(world(), RunRequest(with_node(CALM, node)))
    done = next(c.time_h for c in run.completions if c.element_id == node and c.kind == QUICK)
    assert run.at(node, done) == share
    assert set(run.state(node)[: run.times.index(done)]) == {0.0}


@pytest.mark.parametrize("node", ["SWM-POW-0001", "SWM-FUE-0001", "SWM-HLT-0001", "SWM-TRN-0004"])
def test_a_class_with_no_quick_path_stays_out_for_the_window(node: str) -> None:
    run = simulate(world(), RunRequest(with_node(CALM, node)))
    assert not entries(run, f"{QUICK}:{node}")
    assert set(run.state(node)[:-1]) == {0.0}


def test_a_struck_transmission_substation_comes_back_and_a_struck_plant_does_not() -> None:
    substation, _, share = one_struck_node(NodeClass.TRANSMISSION_SUBSTATION, Layer.POWER)
    assert substation.state(TARGET)[-1] == share == 1.0
    plant = simulate(world(), RunRequest(with_node(CALM, "SWM-POW-0001")))
    assert not entries(plant, f"{QUICK}:SWM-POW-0001")
    assert set(plant.state("SWM-POW-0001")[:-1]) == {0.0}


def test_in_the_pilot_a_struck_substation_regains_condition_but_its_loop_stays_down() -> None:
    """The pilot's power, fuel and water form a closed loop: the import terminal needs power,
    and the plant needs the terminal's LNG and pumped water. Struck, the transmission substation
    takes the loop down at once, and a loop with no outside supply cannot restart (spec §4.5),
    so its quick path restores its condition but not its service."""
    run = simulate(world(), RunRequest(with_node(CALM, "SWM-POW-0002")))
    done = next(c.time_h for c in run.completions if c.element_id == "SWM-POW-0002")
    assert run.at("SWM-POW-0001", 0.0) == 0.0
    assert run.at("SWM-POW-0002", done) == 0.0


def test_slight_and_moderate_damage_open_no_quick_path() -> None:
    for state in ("slight", "moderate"):
        run = simulate(world(), RunRequest(damaged("SWM-POW-0002", state)))
        assert not entries(run, f"{QUICK}:SWM-POW-0002")


def test_a_plan_lists_quick_path_jobs_and_a_crew_waits_for_an_unopened_one() -> None:
    struck = with_node(pilot_inputs().damage[7], "SWM-TRN-0002")
    jobs = repair_jobs(world(), struck)
    assert jobs == ("SWM-POW-L0004", "SWM-TEL-L0001", "SWM-TEL-L0002", "SWM-TRN-0002",
                    f"{QUICK}:SWM-TRN-0002")  # fmt: skip
    plan = (("CRW-0001", (f"{QUICK}:SWM-TRN-0002", "SWM-TRN-0002")),
            ("CRW-0002", ("SWM-TEL-L0002", "SWM-TEL-L0001", "SWM-POW-L0004")))  # fmt: skip
    run = simulate(world(), RunRequest(struck, plan=plan))
    assert entries(run, f"{QUICK}:SWM-TRN-0002")
    # The rebuild's parts are not in inside the window, so crew 1 waits and never starts it.
    assert not entries(run, "repair:SWM-TRN-0002")


# --- The relaxed limits still zero what they zeroed -----------------------------------------


def test_relaxing_the_parts_lead_opens_a_rebuild_at_hour_0() -> None:
    node = "SWM-POW-0001"
    held = simulate(world(), RunRequest(with_node(CALM, node)))
    parts = frozenset({"repair.parts_lead_time"})
    relaxed = simulate(world(), RunRequest(with_node(CALM, node), relaxed=parts))
    assert not entries(held, f"repair:{node}")
    assert entries(relaxed, f"repair:{node}")[0].start_h == 0.0


def test_relaxing_the_crew_lead_and_the_speeds_zeroes_them() -> None:
    node = "SWM-WAT-0004"
    relaxed = frozenset({"repair.crew_bound_lead_h", "crews.road_speed_kmh",
                         "crews.offroad_speed_kmh"})  # fmt: skip
    run = simulate(world(), RunRequest(with_node(CALM, node), relaxed=relaxed))
    work = entries(run, f"{QUICK}:{node}")
    assert [e.activity for e in work] == ["travel", "repair"]
    assert work[0].end_h == work[0].start_h == 0.0
