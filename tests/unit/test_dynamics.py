import ast
import functools
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dynamics_helpers import RULES, TARGET, OneNode, cut, supplier_id
from swm.checks.dynamics import calm_run_problems
from swm.cli import _engine
from swm.dynamics.engine import simulate
from swm.dynamics.records import AddReserve, Protect, RunRequest
from swm.dynamics.world import (
    CrewStart,
    Damage,
    EngineDependency,
    EngineEdge,
    EngineNode,
    FacilityRepair,
    IntraLink,
)
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import Layer, NodeClass

SRC = Path(__file__).resolve().parents[2] / "src" / "swm"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
C = NodeClass


@functools.cache
def pilot() -> Any:
    return _engine(resolve(load_recipe(FIXTURES / "pilot_hand_check.yaml")))


@functools.cache
def pilot_run(scenario: int, relaxed: frozenset[str] = frozenset()) -> Any:
    engine = pilot()
    return simulate(engine.world, RunRequest(engine.damage[scenario], relaxed=relaxed,
                                             scenario=scenario))  # fmt: skip


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


# --- Separation (D1) ------------------------------------------------------------------------


def test_the_engine_never_reaches_error_induction_or_emission() -> None:
    for path in (SRC / "dynamics").rglob("*.py"):
        assert not {n for n in _imports(path) if n.startswith(("swm.errors", "swm.emit"))}, path


def test_the_generator_never_imports_the_engine() -> None:
    for folder in ("stages", "emit", "errors", "manifest", "recipe", "rules"):
        for path in (SRC / folder).rglob("*.py"):
            assert not {n for n in _imports(path) if n.startswith("swm.dynamics")}, path


# --- The calm world (F1) --------------------------------------------------------------------


def test_the_pilot_stays_calm_with_no_damage() -> None:
    assert calm_run_problems(pilot().world) == []


def test_the_rich_world_stays_calm_with_no_damage() -> None:
    from couplings_helpers import rich_world

    recipe, terrain, _ = rich_world()
    del recipe, terrain
    rich = _engine(resolve(load_recipe(FIXTURES / "storm_sensitivity" / "pilot_severity_70.yaml")))
    assert calm_run_problems(rich.world) == []


def test_a_calm_run_reports_a_node_that_moves() -> None:
    node = OneNode(C.MAST, Layer.TELECOM).needs(Layer.POWER)
    world = node.world()
    source = supplier_id(Layer.POWER)
    nodes = tuple(
        replace(n, source=False, own_mode="trip") if n.node_id == source else n for n in world.nodes
    )
    broken = replace(world, nodes=nodes)
    problems = calm_run_problems(broken)
    assert any(p.startswith(TARGET) for p in problems)


# --- Determinism (D7) -----------------------------------------------------------------------


def test_a_run_is_the_same_twice() -> None:
    engine = pilot()
    first = simulate(engine.world, RunRequest(engine.damage[7], scenario=7))
    again = simulate(engine.world, RunRequest(engine.damage[7], scenario=7))
    assert first == again


# --- Monotonicity (F3) ----------------------------------------------------------------------

LIMITS = sorted(rule.id for rule in RULES.rules if rule.is_limit)


@settings(max_examples=16, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(rule_id=st.sampled_from(LIMITS), scenario=st.integers(0, 7))
def test_relaxing_a_limit_never_raises_any_nodes_hours_out(rule_id: str, scenario: int) -> None:
    base = pilot_run(scenario)
    relaxed = pilot_run(scenario, frozenset({rule_id}))
    for node_id, hours in relaxed.hours_out.items():
        assert hours <= base.hours_out[node_id] + 1e-9, (rule_id, node_id)


@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(scenario=st.integers(0, 7), pick=st.integers(0, 50))
def test_protecting_an_element_never_raises_any_nodes_hours_out(scenario: int, pick: int) -> None:
    engine = pilot()
    damage = engine.damage[scenario]
    elements = sorted(damage.nodes) + sorted(damage.lines)
    if not elements:
        return
    element = elements[pick % len(elements)]
    base = pilot_run(scenario)
    protected = simulate(engine.world, RunRequest(damage, actions=(Protect(element),),
                                                  scenario=scenario))  # fmt: skip
    for node_id, hours in protected.hours_out.items():
        assert hours <= base.hours_out[node_id] + 1e-9, (element, node_id)


def test_adding_a_reserve_lengthens_the_hold() -> None:
    node = OneNode(C.MAST, Layer.TELECOM)
    node.stock("battery", Layer.POWER, 4.0, "reserves.mast.battery_h", "battery").needs(Layer.POWER)
    world = node.world()
    damage = Damage((supplier_id(Layer.POWER),), (), ())
    longer = simulate(world, RunRequest(damage, actions=(AddReserve(f"{TARGET}:battery", 6.0),)))
    assert longer.at(TARGET, 9.75) == 1.0
    assert longer.at(TARGET, 10.0) == 0.0


# --- Removal versus relaxing (F4) -----------------------------------------------------------


def test_an_unlimited_stock_and_a_removed_dependency_give_the_same_supply_but_record_apart() -> (
    None
):
    node = OneNode(C.DATA_CENTRE, Layer.TELECOM, {"cooling": "evaporative"}, end_use=True)
    node.stock("makeup_water", Layer.WATER, 12.0, "reserves.data_centre.makeup_water_h", "main")
    node.needs(Layer.WATER)
    world = node.world()
    damage = Damage((supplier_id(Layer.WATER),), (), ())
    relaxed = simulate(
        world, RunRequest(damage, relaxed=frozenset({"reserves.data_centre.makeup_water_h"}))
    )
    removed = simulate(world, RunRequest(damage, removed=(f"E-{supplier_id(Layer.WATER)}",)))
    assert relaxed.state(TARGET) == removed.state(TARGET)
    assert set(relaxed.state(TARGET)) == {1.0}
    assert relaxed.request.relaxed != removed.request.relaxed
    assert relaxed.request.removed != removed.request.removed
    # The relaxed stock is still being drawn on; the removed dependency draws nothing.
    assert relaxed.level(f"{TARGET}:makeup_water")[-1] == float("inf")
    assert removed.level(f"{TARGET}:makeup_water")[-1] == removed.level(f"{TARGET}:makeup_water")[0]


def test_removing_an_unknown_edge_is_refused() -> None:
    world = OneNode(C.MAST, Layer.TELECOM).needs(Layer.POWER).world()
    with pytest.raises(ValueError, match="name no coupling edge"):
        simulate(world, RunRequest(Damage((), (), ()), removed=("SWM-CPL-9999",)))


# --- Crews (F5) -----------------------------------------------------------------------------


def crew_world(parts_h: float = 0.0, work_h: float = 4.0, count: int = 2, **settings: Any) -> Any:
    """Damaged nodes A1..An at one site, each needing a crew; one crew stands there."""
    node = OneNode(C.MAST, Layer.TELECOM).needs(Layer.POWER)
    world = node.world(**settings)
    nodes = list(world.nodes)
    repairs = []
    for index in range(1, count + 1):
        node_id = f"A{index}"
        nodes.append(EngineNode(node_id, Layer.HEALTHCARE, C.CLINIC, (0.0, 0.0), True, None, 3.0))
        repairs.append(FacilityRepair(node_id, parts_h, work_h))
    return replace(world, nodes=tuple(nodes), repairs=tuple(repairs),
                   crews=(CrewStart("CREW", (0.0, 0.0)),))  # fmt: skip


def test_the_crew_bound_lead_time_repeats_at_every_job() -> None:
    run = simulate(crew_world(), RunRequest(Damage(("A1", "A2"), (), ())))
    entries = dict(run.crews)["CREW"]
    assess = [e for e in entries if e.activity == "assess"]
    assert [(e.start_h, e.end_h) for e in assess] == [(0.0, 2.0), (6.0, 8.0)]
    assert [(c.element_id, c.time_h) for c in run.completions] == [("A1", 6.0), ("A2", 12.0)]


def test_parts_lead_times_run_in_parallel_from_the_end_of_the_storm() -> None:
    run = simulate(crew_world(parts_h=10.0), RunRequest(Damage(("A1", "A2"), (), ())))
    entries = dict(run.crews)["CREW"]
    # Both jobs' parts run from hour 0, together, so both open at hour 10. No crew waits on
    # site: the crew starts the first at 10 and goes straight on to the second (Work Order 11,
    # B1; MIP sheet item 11).
    assert entries[0].start_h == 10.0
    assert "wait for parts" not in {e.activity for e in entries}
    assert [c.time_h for c in run.completions] == [16.0, 22.0]


def test_relaxing_the_crews_gives_every_job_its_own_crew_at_once() -> None:
    run = simulate(crew_world(), RunRequest(Damage(("A1", "A2"), (), ()),
                                            relaxed=frozenset({"crews.pilot"})))  # fmt: skip
    assert [c.time_h for c in run.completions] == [6.0, 6.0]


def test_crews_take_jobs_in_the_default_order() -> None:
    world = crew_world(count=1)
    far = EngineNode(
        "DSUB", Layer.POWER, C.DISTRIBUTION_SUBSTATION, (40_000.0, 0.0), True, None, 5.0
    )
    world = replace(world, nodes=(*world.nodes, far),
                    repairs=(*world.repairs, FacilityRepair("DSUB", 0.0, 4.0)))  # fmt: skip
    run = simulate(world, RunRequest(Damage(("A1", "DSUB"), (), ())))
    # The distribution substation is tier 2 and goes first, though it is 1 h away.
    assert [c.element_id for c in run.completions] == ["DSUB", "A1"]


def switching_world(telecom_up: bool) -> tuple[Any, Damage]:
    """A distribution substation fed by one line, and a telecom source that may be down."""
    node = OneNode(C.DISTRIBUTION_SUBSTATION, Layer.POWER).fed_by_own_layer(line=True)
    node.needs(Layer.TELECOM, kappa=0.2, form="threshold", tolerance="tolerance.substation")
    world = replace(node.world(), crews=(CrewStart("CREW", (0.0, 0.0)),))
    from swm.dynamics.world import FailurePoint

    damaged = () if telecom_up else (supplier_id(Layer.TELECOM),)
    damage = Damage(damaged, ("L-0",), (FailurePoint("L-0", 0.5, (0.0, 0.0), 6.0),))
    return world, damage


def test_a_manual_switching_trip_follows_a_line_repair_when_telecom_is_down() -> None:
    world, damage = switching_world(telecom_up=False)
    run = simulate(world, RunRequest(damage))
    kinds = [(c.kind, c.time_h) for c in run.completions]
    # The line is repaired at hour 8 (2 h lead, 6 h work); power returns only after the
    # crew switches by hand, 1 h on site.
    assert kinds == [("line", 8.0), ("switching", 9.0)]
    assert run.at(TARGET, 8.75) == 0.0
    assert run.at(TARGET, 9.0) == 1.0


def test_no_switching_trip_while_telecom_is_up() -> None:
    world, damage = switching_world(telecom_up=True)
    run = simulate(world, RunRequest(damage))
    assert [c.kind for c in run.completions] == ["line"]
    assert run.at(TARGET, 8.0) == 1.0


def test_no_switching_trip_when_the_repair_is_at_the_substation_itself() -> None:
    node = OneNode(C.DISTRIBUTION_SUBSTATION, Layer.POWER).fed_by_own_layer(line=False)
    node.needs(Layer.TELECOM, kappa=0.2, form="threshold", tolerance="tolerance.substation")
    node.repairs.append(FacilityRepair(TARGET, 0.0, 6.0))
    world = replace(node.world(), crews=(CrewStart("CREW", (0.0, 0.0)),))
    run = simulate(world, RunRequest(Damage((TARGET, supplier_id(Layer.TELECOM)), (), ())))
    assert [c.kind for c in run.completions] == ["facility"]
    assert run.at(TARGET, 8.0) == 1.0


def test_relaxing_the_switching_time_leaves_only_the_travel() -> None:
    world, damage = switching_world(telecom_up=False)
    run = simulate(world, RunRequest(damage, relaxed=frozenset({"repair.manual_switching_h"})))
    # The trip opens when power returns at hour 8 and takes no time; like every job, its
    # effect lands on the next step.
    assert [(c.kind, c.time_h) for c in run.completions] == [("line", 8.0), ("switching", 8.25)]


# --- Convergence (F6) -----------------------------------------------------------------------


def chain_world(length: int, cap: int) -> Any:
    """A chain of nodes each tripping when the one before it fails."""
    nodes, dependencies = [], []
    for index in range(length):
        node_id = f"N{index:03d}"
        nodes.append(EngineNode(node_id, Layer.HEALTHCARE, C.CLINIC, (0.0, 0.0), True, None, None))
        if index:
            edge = EngineEdge(f"E{index:03d}", f"N{index - 1:03d}", 1.0, "linear", None)
            dependencies.append(EngineDependency(f"D{index:03d}", node_id, Layer.POWER,
                                                 ((edge,),), "trip", None))  # fmt: skip
    base = OneNode(C.CLINIC, Layer.HEALTHCARE).world(settling_cap=cap)
    return replace(base, nodes=tuple(nodes), dependencies=tuple(dependencies))


def test_a_cascade_that_cannot_settle_within_the_cap_is_reported() -> None:
    # Eight nodes need nine passes; with a cap of 5 the first step stops short.
    run = simulate(chain_world(8, cap=5), RunRequest(Damage(("N000",), (), ()), horizon_h=1.0))
    assert run.capped == (0.0,)
    assert run.summary()["capped_steps"] == 1
    assert run.passes[0] == 5
    # The next step finishes settling, so nothing is hidden: the whole chain is out.
    assert set(run.states[1]) == {0.0}


def test_a_cascade_within_the_cap_settles_and_reports_its_passes() -> None:
    run = simulate(chain_world(12, cap=100), RunRequest(Damage(("N000",), (), ()), horizon_h=1.0))
    assert run.capped == ()
    assert run.passes[0] == 13
    assert set(run.states[0]) == {0.0}


def test_a_ring_of_links_cannot_keep_itself_supplied() -> None:
    node = OneNode(C.TRANSMISSION_SUBSTATION, Layer.POWER).fed_by_own_layer(line=False)
    world = node.world()
    ring = EngineNode(
        "T2", Layer.POWER, C.TRANSMISSION_SUBSTATION, (0.0, 0.0), False, "throttle", None
    )
    links = (
        *world.links,
        IntraLink("TIE", TARGET, "T2", False),
        IntraLink("TIE", "T2", TARGET, False),
    )
    world = replace(world, nodes=(*world.nodes, ring), links=links)
    run = simulate(world, RunRequest(Damage(("UP-0",), (), ()), horizon_h=1.0))
    assert run.at(TARGET, 0.0) == 0.0
    assert run.at("T2", 0.0) == 0.0


def test_an_unknown_transfer_form_is_refused() -> None:
    node = OneNode(C.MAST, Layer.TELECOM).needs(Layer.POWER, form="step")
    with pytest.raises(ValueError, match="step transfer form"):
        cut(node.world(), [supplier_id(Layer.POWER)])


# --- PR 7b answers: the three corrections ---------------------------------------------------


def with_crew(world: Any) -> Any:
    return replace(world, crews=(CrewStart("CREW", (0.0, 0.0)),))


def test_a_missed_delivery_goes_out_when_the_depot_comes_back() -> None:
    node = OneNode(C.EXCHANGE, Layer.TELECOM, end_use=False)
    node.stock("battery", Layer.POWER, 4.0, "reserves.exchange.battery_h", "battery")
    node.generator(24.0, "reserves.exchange.fuel_h").needs(Layer.POWER).deliveries_from()
    # The depot is repaired at hour 20 (2 h crew-bound lead, 18 h of work).
    node.repairs.append(FacilityRepair("DEPOT", 0.0, 18.0))
    run = cut(with_crew(node.world()), [supplier_id(Layer.POWER), "DEPOT"])
    assert [d.time_h for d in run.deliveries] == [20.0, 44.0, 68.0]
    assert set(run.state(TARGET)) == {1.0}


def test_hospital_water_refills_from_the_main_once_supply_returns() -> None:
    node = OneNode(
        C.TERTIARY, Layer.HEALTHCARE, {"records_hosted": False, "standby_fuel": "diesel"}
    )
    node.stock("water", Layer.WATER, 72.0, "reserves.hospital.water_h", "main").needs(Layer.WATER)
    node.repairs.append(FacilityRepair(supplier_id(Layer.WATER), 0.0, 4.0))
    run = cut(with_crew(node.world()), [supplier_id(Layer.WATER)])
    level = run.level(f"{TARGET}:water")
    full = level[0]
    # Out for 6 h (2 h lead, 4 h work), then refilled at its draw: 6 h back in 6 h.
    assert level[24] == pytest.approx(full - 60.0)
    assert level[25] == pytest.approx(full - 57.5)
    assert level[48] == pytest.approx(full)


def test_pump_capacity_is_shared_pro_rata_by_demand() -> None:
    world = OneNode(C.STORAGE, Layer.WATER).world()
    pump = EngineNode("PUMP", Layer.WATER, C.PUMPING, (0.0, 0.0), True, None, None)
    stores = [EngineNode(s, Layer.WATER, C.STORAGE, (0.0, 0.0), False, "throttle", 5.0)
              for s in ("S1", "S2")]  # fmt: skip
    from swm.dynamics.world import Stock

    stocks = (Stock("S1:distribution_water", "S1", "distribution_water", Layer.WATER, 120.0,
                    10.0, "pumps", "reserves.storage.peak_day_h"),
              Stock("S2:distribution_water", "S2", "distribution_water", Layer.WATER, 360.0,
                    30.0, "pumps", "reserves.storage.peak_day_h"))  # fmt: skip
    links = (IntraLink("L1", "PUMP", "S1", False), IntraLink("L2", "PUMP", "S2", False))
    world = replace(
        world, nodes=(pump, *stores), dependencies=(), links=links, stocks=stocks,
        repairs=(FacilityRepair("PUMP", 0.0, 2.0),), pump_capacity_m3_per_h={"PUMP": 80.0},
        crews=(CrewStart("CREW", (0.0, 0.0)),),
    )  # fmt: skip
    run = simulate(world, RunRequest(Damage(("PUMP",), (), ()), horizon_h=12.0))
    # Down 4 h; then 80 m³/h shared 1:3 by demand leaves 10 and 30 m³/h spare.
    s1, s2 = run.level("S1:distribution_water"), run.level("S2:distribution_water")
    assert s1[16] == pytest.approx(80.0)
    assert s2[16] == pytest.approx(240.0)
    assert s1[17] - s1[16] == pytest.approx(2.5)
    assert s2[17] - s2[16] == pytest.approx(7.5)


# --- Work Order 8, Part 0: the main refill rate ---------------------------------------------


@pytest.mark.parametrize(("fraction", "relaxed", "per_step"),
                         [(1.0, False, 2.5), (0.5, False, 1.25), (1.0, True, None)])  # fmt: skip
def test_water_from_the_main_refills_at_the_ruled_fraction_of_its_drain(
    fraction: float, relaxed: bool, per_step: float | None
) -> None:
    node = OneNode(
        C.TERTIARY, Layer.HEALTHCARE, {"records_hosted": False, "standby_fuel": "diesel"}
    )
    node.stock("water", Layer.WATER, 72.0, "reserves.hospital.water_h", "main").needs(Layer.WATER)
    node.repairs.append(FacilityRepair(supplier_id(Layer.WATER), 0.0, 4.0))
    world = with_crew(node.world(main_refill_fraction=fraction))
    damage = Damage((supplier_id(Layer.WATER),), (), ())
    flag = frozenset({"reserves.main_refill_rate_fraction"}) if relaxed else frozenset()
    run = simulate(world, RunRequest(damage, relaxed=flag))
    level = run.level(f"{TARGET}:water")
    # Down 6 h at 10 m³/h: 60 m³ short when the main returns at hour 6.
    assert level[24] == pytest.approx(level[0] - 60.0)
    if per_step is None:
        assert level[25] == pytest.approx(level[0])
    else:
        assert level[25] - level[24] == pytest.approx(per_step)


def test_the_main_refill_rule_is_ruled_with_its_range() -> None:
    rule = RULES.rule("reserves.main_refill_rate_fraction")
    assert rule.value == 1.0
    assert rule.range == [0.5, 1.0]
    assert rule.relaxed == "unlimited"


# --- Crew order among distribution substations (WO-09g answers, 1) -------------------------


def test_a_distribution_substation_ranks_by_the_highest_weight_it_supplies() -> None:
    from swm.dynamics.engine import crew_order, substation_weight

    world = pilot().world
    substations = [n for n in world.nodes if n.node_class == C.DISTRIBUTION_SUBSTATION]
    assert substations
    weights = {n.node_id: n.end_use_weight for n in world.nodes}
    for node in substations:
        supplied = {
            d.consumer_id for d in world.dependencies if d.supplier_layer == Layer.POWER
            and any(e.supplier_id == node.node_id for g in d.groups for e in g)
        }  # fmt: skip
        expected = max(w for w in (weights[node.node_id], *(weights[s] for s in supplied))
                       if w is not None)  # fmt: skip
        assert substation_weight(world, node.node_id) == expected
        assert crew_order(world, node.node_id) == (1, -expected)


def test_the_substation_ranking_is_ruled_with_its_two_alternatives() -> None:
    rule = RULES.rule("dynamics.substation_crew_rank")
    assert rule.value == "highest supplied weight"
    assert rule.theta_alternatives == ("own weight only", "sum of supplied weights")
    assert rule.grade == "J"
    assert rule.ruling is not None
    assert rule.ruling.date == "2026-10-19"


def test_an_alternative_ranking_is_not_yet_selectable() -> None:
    from swm.dynamics.engine import substation_weight

    world = pilot().world
    other = replace(world, settings=replace(world.settings, substation_rank="own weight only"))
    node = next(n for n in world.nodes if n.node_class == C.DISTRIBUTION_SUBSTATION)
    with pytest.raises(ValueError, match="selectable only in a later phase"):
        substation_weight(other, node.node_id)


# --- Travel between failure points of one line (WO-09g answers 2) --------------------------


def _two_point_line(rules_overrides: dict[str, object] | None = None) -> Any:
    from swm.dynamics.travel import Legs, Site
    from swm.dynamics.world import FailurePoint

    def far_road(start: Site, end: Site) -> Legs:
        # Any road trip is long, so a walk along the line is clearly the shorter way.
        return Legs(100.0, 1.0, False)

    node = OneNode(C.MAST, Layer.TELECOM).needs(Layer.POWER)
    world = replace(node.world(**(rules_overrides or {})), legs=far_road,
                    crews=(CrewStart("CRW-1", (0.0, 0.0)),))  # fmt: skip
    points = (
        FailurePoint("L", 3.0, (0.0, 1000.0), 6.0),
        FailurePoint("L", 5.5, (0.0, 3500.0), 6.0),
    )
    return simulate(world, RunRequest(Damage((), ("L",), points)))


def test_a_crew_walks_along_the_line_between_its_failure_points() -> None:
    run = _two_point_line()
    travel = [e for _, log in run.crews for e in log if e.activity == "travel"]
    walk = travel[1].end_h - travel[1].start_h
    assert walk == pytest.approx(2.5 / RULES.number("crews.offroad_speed_kmh"))
    assert [e.activity for _, log in run.crews for e in log].count("assess") == 1


def test_the_line_travel_rule_is_ruled_with_its_two_alternatives() -> None:
    rule = RULES.rule("dynamics.line_point_travel")
    assert rule.value == "along the line within a job; via the road between jobs"
    assert rule.theta_alternatives == ("always via the road", "whichever way is shorter")
    assert rule.ruling is not None
    assert rule.ruling.date == "2026-10-19"


def test_an_alternative_line_travel_is_not_yet_selectable() -> None:
    with pytest.raises(ValueError, match="selectable only in a later phase"):
        _two_point_line({"line_point_travel": "always via the road"})
