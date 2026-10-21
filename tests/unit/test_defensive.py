"""The defensive model: protect condition and add reserve (Work Order 10, Part E).

Spec: structure v0.17 §5; Phase 2 rulings Q5-Q8; Work Order 10, E1-E5.
"""

import math
from typing import Any

import pytest

from dynamics_helpers import RULES, TARGET, OneNode, supplier_id
from solve_helpers import pilot_inputs
from swm.dynamics.engine import simulate
from swm.dynamics.records import AddReserve, AddStock, Protect, RunRequest
from swm.dynamics.world import Damage
from swm.recipe.schema import Layer, NodeClass
from swm.solve.defensive import (
    NO_ACTION,
    Defence,
    Reserve,
    defence_of,
    defence_text,
    defences,
    reserves_of,
    scenario_actions,
)
from swm.solve.runner import Job, Runner
from swm.solve.solver import defensive_plays, mean_rows

P = Layer.POWER
W = Layer.WATER
WINDOW_H = 72.0


def inputs() -> Any:
    return pilot_inputs()


# --- The actions (E1, E2) -------------------------------------------------------------------


def test_a_protected_element_is_undamaged_in_every_scenario() -> None:
    world = inputs()
    calm = simulate(world.world, RunRequest(Damage((), (), ()))).hours_out
    for damage in world.damage:
        damaged = (*damage.nodes, *damage.lines)
        protected = tuple(Protect(e) for e in damaged)
        run = simulate(world.world, RunRequest(damage, actions=protected))
        assert run.hours_out == calm
        assert not [c for c in run.completions if c.kind in ("line", "facility")]


def test_a_reserve_on_a_stockless_dependency_keeps_the_node_up_through_a_72_hour_cut() -> None:
    node = OneNode(NodeClass.MAST, Layer.TELECOM).needs(P)
    world = node.world()
    assert not world.stocks
    cut = RunRequest(Damage((supplier_id(P),), (), ()), horizon_h=WINDOW_H)
    without = simulate(world, cut)
    assert min(without.state(TARGET)) < 1.0
    held = simulate(world, RunRequest(cut.damage, actions=(AddStock(TARGET, P, WINDOW_H),),
                                      horizon_h=WINDOW_H))  # fmt: skip
    # The stock is the window's hours at full draw: it empties exactly at the horizon, so the
    # node serves at every step of the window and loses no service-hour.
    within = {x for t, x in zip(held.times, held.state(TARGET), strict=True) if t < WINDOW_H}
    assert within == {1.0}
    assert held.hours_out[TARGET] == 0.0


def test_a_reserve_on_an_existing_stock_adds_the_windows_hours_to_it() -> None:
    hospital = {"records_hosted": False, "standby_fuel": "diesel"}
    node = OneNode(NodeClass.TERTIARY, Layer.HEALTHCARE, hospital)
    node.stock("water", W, 72.0, "reserves.hospital.water_h").needs(W)
    world = node.world()
    stock = world.stocks[0]
    cut = Damage((supplier_id(W),), (), ())
    without = simulate(world, RunRequest(cut, horizon_h=100.0))
    added = simulate(world, RunRequest(cut, actions=(AddReserve(stock.stock_id, WINDOW_H),),
                                       horizon_h=100.0))  # fmt: skip
    assert without.at(TARGET, 90.0) < 1.0
    assert added.at(TARGET, 90.0) == 1.0
    assert added.level(stock.stock_id)[0] == stock.capacity + WINDOW_H * stock.draw_per_h


def test_an_added_stock_is_refused_where_the_node_already_holds_one() -> None:
    hospital = {"records_hosted": False, "standby_fuel": "diesel"}
    node = OneNode(NodeClass.TERTIARY, Layer.HEALTHCARE, hospital)
    node.stock("water", W, 72.0, "reserves.hospital.water_h").needs(W)
    with pytest.raises(ValueError, match="already holds"):
        simulate(node.world(), RunRequest(Damage((), (), ()),
                                          actions=(AddStock(TARGET, W, WINDOW_H),)))  # fmt: skip


def test_a_reserve_goes_to_the_stock_the_engine_draws_first_or_creates_one() -> None:
    world = inputs()
    damage = world.damage[7]
    for reserve in reserves_of(world.world):
        (action,) = scenario_actions(Defence((), (reserve,)), damage, world.world.stocks, WINDOW_H)
        held = [s for s in world.world.stocks
                if s.node_id == reserve.node_id and s.covers == reserve.covers]  # fmt: skip
        if held:
            first = min(held, key=lambda s: (s.generator, s.stock_id))
            assert action == AddReserve(first.stock_id, WINDOW_H)
        else:
            assert action == AddStock(reserve.node_id, reserve.covers, WINDOW_H)


# --- The search (E1, E4) --------------------------------------------------------------------


def test_the_pilot_has_47_dependencies_and_55_protectable_elements() -> None:
    world = inputs()
    assert len(reserves_of(world.world)) == 47
    assert len(world.protectable) == 55


@pytest.mark.parametrize(("budget", "count"), [(3, 19_984), (4, 259_289)])
def test_every_affordable_answer_is_searched_spending_under_the_budget_included(
    budget: int, count: int
) -> None:
    world = inputs()
    reserves = reserves_of(world.world)
    every = list(defences(world.protectable, reserves, budget, 2, 1))
    assert len(every) == count
    assert len(set(every)) == count
    costs = {a.cost(2, 1) for a in every}
    assert costs == set(range(budget + 1))
    protects, deps = len(world.protectable), len(reserves)
    expected = sum(
        math.comb(protects, p) * math.comb(deps, r)
        for p in range(budget // 2 + 1)
        for r in range(budget - 2 * p + 1)
    )
    assert count == expected


def test_an_answer_reads_back_from_its_text() -> None:
    world = inputs()
    for answer in list(defences(world.protectable, reserves_of(world.world), 2, 2, 1))[::37]:
        assert defence_of(defence_text(answer)) == answer
    assert defence_text(Defence()) == NO_ACTION


def _full(world: Any, answer: Defence) -> Any:
    """Every scenario run in full, every action applied where the engine accepts it."""
    rows = []
    runner = Runner(world.world, WINDOW_H)
    for damage in world.damage:
        damaged = {*damage.nodes, *damage.lines}
        protects = tuple(
            Protect(e) for e in answer.protects
            if e in damaged or e in {n.node_id for n in world.world.nodes}
        )  # fmt: skip
        reserves = scenario_actions(Defence((), answer.reserves), damage, world.world.stocks,
                                    WINDOW_H)  # fmt: skip
        rows.append(runner.rows([Job(damage, actions=protects + reserves)])[0])
    import numpy as np

    return mean_rows(np.array(rows))


def test_each_skip_scores_exactly_what_it_assumes() -> None:
    """E4, on a sample: an undamaged scenario run with every action, and a protection of a node
    no scenario damages, run in full, score exactly what the skips assume."""
    world = inputs()
    damaged = {e for d in world.damage for e in (*d.nodes, *d.lines)}
    candidates = [n.node_id for n in world.world.nodes if n.node_id in world.protectable]
    undamaged_node = next(n for n in candidates if n not in damaged)
    reserves = reserves_of(world.world)
    sample = [
        Defence((undamaged_node,), (reserves[0],)),
        Defence(("SWM-TEL-L0002",), (reserves[5],)),
        Defence((), (reserves[3], reserves[11], reserves[40])),
        Defence((undamaged_node,), ()),
    ]
    plays = defensive_plays(world, sample, WINDOW_H)
    assumed = Runner(world.world, WINDOW_H).rows(plays.jobs)
    for index, answer in enumerate(sample):
        expected = mean_rows(assumed[plays.use[index]])
        assert _full(world, answer).tobytes() == expected.tobytes(), defence_text(answer)
    alone = defensive_plays(world, [Defence((), (reserves[0],))], WINDOW_H)
    first = defensive_plays(world, [sample[0]], WINDOW_H)
    assert [alone.jobs[i] for i in alone.use[0]] == [first.jobs[i] for i in first.use[0]]


def test_runs_are_shared_between_answers_only_when_they_are_the_same_run() -> None:
    world = inputs()
    answers = list(defences(world.protectable, reserves_of(world.world), 2, 2, 1))
    plays = defensive_plays(world, answers, WINDOW_H)
    assert len(set(plays.jobs)) == len(plays.jobs)
    undamaged = [s for s, d in enumerate(world.damage) if not d.nodes and not d.lines]
    assert undamaged == [3, 5, 6]
    assert len({j for s in undamaged for j in plays.use[:, s].tolist()}) == 1


def test_a_reserve_label_names_its_node_and_commodity() -> None:
    text = defence_text(Defence(("SWM-CPL-0007",), (Reserve("SWM-HLT-0001", P),)))
    assert text == "protect SWM-CPL-0007; reserve SWM-HLT-0001 power"
    assert RULES.number("solve.instance_bound_h") == 48.0
