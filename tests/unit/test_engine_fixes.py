"""The two engine bugs writing the crew rules as equations found (Work Order 11, Part A).

Each case fails on main and passes once fixed. The file imports only what main has, so it runs
on both.

Spec: MIP crew-rules sheet v0.2, Part 3 (E1, E2); structure v0.19 §4.5; Work Order 11, A1-A2.
"""

import pytest

from dynamics_helpers import TARGET, OneNode
from swm.dynamics.engine import _Engine, simulate
from swm.dynamics.records import RunRequest
from swm.dynamics.world import Damage
from swm.recipe.schema import Layer, NodeClass

STEP_H = 0.25
CALM = Damage((), (), ())


# --- A1: a cancelled switching trip never strands a newer one -------------------------------


def test_a_mark_that_clears_reopens_and_clears_again_leaves_no_trip_behind() -> None:
    node = OneNode(NodeClass.DISTRIBUTION_SUBSTATION, Layer.POWER)
    engine = _Engine(node.world(), RunRequest(CALM))
    # main names the clearing step _cancel_switching; the branch, _clear_mark.
    clear = getattr(engine, "_clear_mark", None) or engine._cancel_switching
    engine._open_switching(TARGET, 0.0)
    first = engine.switching[TARGET]
    first.crew_id = "crew 1"  # assigned: it will still be travelled and worked
    clear(TARGET)  # the mark clears
    engine._open_switching(TARGET, 1.0)  # and comes back: a newer trip
    newer = engine.switching[TARGET]
    engine.jobs.pop(first.job_id)
    engine._finish(first, 2.0)  # the assigned trip arrives and switches
    clear(TARGET)  # the mark clears again
    assert newer.job_id not in engine.jobs
    assert TARGET not in engine.switching


# --- A2: a stock that runs out passes on the remainder --------------------------------------


def test_a_node_whose_first_stock_empties_mid_step_charges_the_next_only_the_rest() -> None:
    node = OneNode(NodeClass.EXCHANGE, Layer.TELECOM, end_use=False)
    node.stock("a_battery", Layer.POWER, 0.1, "reserves.exchange.battery_h", draw_per_h=10.0)
    node.stock("b_battery", Layer.POWER, 10.0, "reserves.exchange.battery_h", draw_per_h=10.0)
    node.needs(Layer.POWER)
    run = simulate(node.world(), RunRequest(Damage(("SUP-power",), (), ()), horizon_h=1.0))
    first, second = f"{TARGET}:a_battery", f"{TARGET}:b_battery"
    step = run.times.index(STEP_H)
    # A step needs 10 x 0.25 = 2.5; the first stock holds 1.0, so the second gives 1.5.
    assert run.level(first)[step] == 0.0
    assert run.level(second)[step] == pytest.approx(100.0 - 1.5)
