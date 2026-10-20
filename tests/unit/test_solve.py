"""The answer-key solver's frame and the restorative model (Work Order 10, PR 10a).

Spec: structure v0.17 §5 and §7; Phase 2 answer-key ruling sheet v0.2; Work Order 10, Parts A-C.
"""

import bz2
import csv
import functools
import hashlib
import io
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from swm.cli import _built, _engine, main
from swm.dynamics.engine import simulate
from swm.dynamics.records import RunRequest
from swm.recipe.io import RecipeVersionError, load_recipe, parse_recipe
from swm.recipe.resolve import Resolution, resolve
from swm.recipe.schema import (
    ProtectConditionAndAddReserve,
    SequenceRepairCrews,
    StrikeNodes,
    WeightPreset,
)
from swm.solve.measure import Range, spread
from swm.solve.requests import searches, stamp
from swm.solve.restorative import plan_count, plan_text, plans, repair_jobs
from swm.solve.runner import Runner
from swm.solve.thumbs import nearest_supplier_world, rank_by_capacity, rank_by_degree
from swm.solve.weights import node_weights, objective
from swm.stages import couplings as couplings_stage

TESTS = Path(__file__).resolve().parents[1]
PILOT = TESTS / "fixtures" / "pilot_hand_check.yaml"
GOLDEN = TESTS / "golden" / "pilot_answer_keys"
SRC = TESTS.parent / "src" / "swm"
RESTORATIVE = (4, 9)
"""The pilot's two restorative requests: Lifeline, then Equal (Work Order 10, A2)."""
SCENARIO = 7
DEFAULT_ORDER_LIFELINE = 52.25
"""Scenario 7 under the default crew order, Lifeline weights (the hand trace, decision 0017)."""


@functools.cache
def pilot() -> tuple[Resolution, Any]:
    resolution = resolve(load_recipe(PILOT))
    return resolution, _engine(resolution, _built(resolution))


@pytest.fixture(scope="module")
def solved(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out_dir = tmp_path_factory.mktemp("solve")
    assert main(["solve", str(PILOT), "-o", str(out_dir)]) == 0
    return out_dir / "answer_keys"


def key(folder: Path, index: int) -> dict[str, Any]:
    weights = "lifeline" if index == RESTORATIVE[0] else "equal"
    name = f"request_{index:02d}_sequence_repair_crews_{weights}.yaml"
    loaded: dict[str, Any] = yaml.safe_load((folder / name).read_text(encoding="utf-8"))
    return loaded


def answers(folder: Path) -> list[dict[str, str]]:
    body = bz2.decompress((folder / "search_04_sequence_repair_crews_answers.csv.bz2").read_bytes())
    return list(csv.DictReader(io.StringIO(body.decode("utf-8"))))


# --- Part A: schema version 4 ---------------------------------------------------------------


def test_a_version_3_recipe_migrates_with_the_new_fields_at_their_defaults() -> None:
    recipe = parse_recipe(
        "recipe_version: 3\nanswer_key_requests:\n"
        "  - {model: strike_nodes, member_class: offensive, strikes_k: 2}\n"
        "  - {model: protect_condition_and_add_reserve, member_class: defensive}\n"
    )
    assert recipe.recipe_version == 4
    strike, protect = recipe.answer_key_requests
    assert isinstance(strike, StrikeNodes)
    assert (strike.world, strike.strike_damage) == ("calm", "complete")
    assert isinstance(protect, ProtectConditionAndAddReserve)
    assert protect.reserve_hours == "window"


def test_a_version_3_restorative_request_fails_naming_the_field() -> None:
    text = (
        "recipe_version: 3\nanswer_key_requests:\n"
        "  - {model: strike_nodes, member_class: offensive}\n"
        "  - {model: sequence_repair_crews, member_class: restorative}\n"
    )
    with pytest.raises(RecipeVersionError, match=r"answer_key_requests\[1\]\.scenario"):
        parse_recipe(text)


def test_a_version_4_restorative_request_needs_its_scenario() -> None:
    text = "recipe_version: 4\nanswer_key_requests:\n  - {model: sequence_repair_crews}\n"
    with pytest.raises(ValidationError, match="scenario"):
        parse_recipe(text)


def test_the_pilot_carries_the_ten_ruled_requests() -> None:
    requests = load_recipe(PILOT).answer_key_requests
    assert len(requests) == 10
    assert [r.service_weights for r in requests] == [WeightPreset.LIFELINE] * 5 + [
        WeightPreset.EQUAL
    ] * 5
    assert all(r.window_h == 72 for r in requests)
    restorative = [requests[i] for i in RESTORATIVE]
    assert all(isinstance(r, SequenceRepairCrews) and r.scenario == SCENARIO for r in restorative)


def test_swm_solve_refuses_an_informative_request(tmp_path: Path, capsys: Any) -> None:
    recipe = tmp_path / "informative.yaml"
    text = PILOT.read_text(encoding="utf-8").split("answer_key_requests:")[0]
    recipe.write_text(
        text + "answer_key_requests:\n  - {model: observe_uncertain_couplings, "
        "member_class: informative}\n",
        encoding="utf-8",
        newline="\n",
    )
    assert main(["solve", str(recipe), "-o", str(tmp_path / "out")]) != 0
    assert "built in Phase 4, against the pipeline's belief" in capsys.readouterr().err


# --- Part B: the key ------------------------------------------------------------------------


def test_requests_differing_only_in_weights_share_one_search() -> None:
    requests = load_recipe(PILOT).answer_key_requests
    groups = [search.request_indices for search in searches(requests)]
    assert groups == [(0, 5), (1, 6), (2, 7), (3, 8), (4, 9)]


def test_each_weighting_is_arithmetic_on_one_run(solved: Path) -> None:
    resolution, engine = pilot()
    requests = resolution.recipe.answer_key_requests
    rows = answers(solved)
    damage = engine.damage[SCENARIO]
    for row in rows[:5]:
        plan = _plan_of(row["answer"])
        hours = simulate(engine.world, RunRequest(damage, plan=plan)).hours_out
        for index in RESTORATIVE:
            weights = node_weights(requests[index], engine.world.nodes)
            column = f"request_{index:02d}_{requests[index].service_weights}"
            assert float(row[column]) == objective(hours, weights)


def _plan_of(text: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    plan = []
    for part in text.split("; "):
        crew, _, jobs = part.partition(": ")
        plan.append((crew, () if jobs == "no jobs" else tuple(jobs.split(", "))))
    return tuple(plan)


def test_the_optimum_lists_every_tied_plan(solved: Path) -> None:
    for index, column in zip(RESTORATIVE, ("request_04_lifeline", "request_09_equal"), strict=True):
        values = {row["answer"]: float(row[column]) for row in answers(solved)}
        best = min(values.values())
        record = key(solved, index)
        assert record["optimum"]["objective"] == best
        assert sorted(record["optimum"]["answers"]) == sorted(
            a for a, v in values.items() if v == best
        )
    assert len(key(solved, RESTORATIVE[0])["optimum"]["answers"]) > 1


def test_the_key_holds_every_part_of_b3(solved: Path) -> None:
    record = key(solved, RESTORATIVE[0])
    resolution, _ = pilot()
    assert record["assumes"] == stamp(resolution.recipe.answer_key_requests[4], _sha(resolution))
    assert "scenario 7" in record["assumes"]
    assert record["spread"]["answers"] == 24
    assert set(record["spread"]) >= {
        "within_1_pct",
        "within_5_pct",
        "within_10_pct",
        "mean_distance",
    }
    assert [r["rule"] for r in record["rules_of_thumb"]] == [
        "most connections first", "biggest first", "nearest supplier"]  # fmt: skip
    assert len(record["true_criticality"]) == 24
    assert record["decision_relevant_dose"] == {
        "value": 0,
        "note": "no error planted until Phase 3",
    }
    assert "a sample of the storm, not the storm in general" in record["note"]


def _sha(resolution: Resolution) -> str:
    from swm.recipe.io import recipe_sha256

    return recipe_sha256(resolution.recipe)


def test_a_zero_range_is_reported_and_never_divided() -> None:
    measure = Range(optimum=30.0, no_action=30.0)
    assert measure.zero
    assert measure.distance(31.0) is None
    record = spread([30.0, 31.0], measure, [1.0, 5.0, 10.0])
    assert record["within_1_pct"] is None
    assert record["mean_distance"] is None
    assert "range is zero" in str(record["note"])


def test_the_measure_mirrors_for_the_offensive_model() -> None:
    measure = Range(optimum=100.0, no_action=20.0, mirrored=True)
    assert measure.distance(100.0) == 0.0
    assert measure.distance(20.0) == 1.0
    assert measure.distance(60.0) == 0.5


def test_the_spread_counts_bands_without_dividing() -> None:
    measure = Range(optimum=10.0, no_action=20.0)
    record = spread([10.0, 10.1, 10.5, 11.0, 20.0], measure, [1.0, 5.0, 10.0])
    assert record["within_1_pct"] == 0.4
    assert record["within_5_pct"] == 0.6
    assert record["within_10_pct"] == 0.8
    assert record["mean_distance"] == round((0 + 0.01 + 0.05 + 0.1 + 1.0) / 5, 6)


def test_the_restorative_rankings_tie_lines_by_id() -> None:
    _, engine = pilot()
    jobs = repair_jobs(engine.world, engine.damage[SCENARIO])
    assert rank_by_degree(jobs, engine.world) == jobs
    assert rank_by_capacity(jobs, {}) == jobs


def test_the_nearest_supplier_copy_moves_only_couplings_off_the_nearest() -> None:
    resolution, engine = pilot()
    built = _built(resolution)
    eligible = couplings_stage.eligible_suppliers(
        resolution.recipe.couplings, built.terrain, built.requirements.layers,
        built.requirements, built.rules,
    )  # fmt: skip
    copy = nearest_supplier_world(engine.world, eligible)
    assert copy.nodes == engine.world.nodes
    assert copy.links == engine.world.links
    moved = 0
    for true, near in zip(engine.world.dependencies, copy.dependencies, strict=True):
        before = {e.supplier_id: e for g in true.groups for e in g}
        after = {e.supplier_id: e for g in near.groups for e in g}
        for supplier, edge in after.items():
            if supplier in before:
                assert edge == before[supplier]
            else:
                moved += 1
                assert edge.line_id is None
                options = eligible[(true.consumer_id, true.supplier_layer)]
                assert supplier in options[: len(after)]
    assert moved > 0


def test_the_answers_file_is_bz2_with_no_timestamp(solved: Path) -> None:
    body = (solved / "search_04_sequence_repair_crews_answers.csv.bz2").read_bytes()
    assert body.startswith(b"BZh9")
    assert len(answers(solved)) == 24


# --- Part C: the restorative model ----------------------------------------------------------


def test_scenario_7_has_24_plans() -> None:
    _, engine = pilot()
    jobs = repair_jobs(engine.world, engine.damage[SCENARIO])
    crews = [c.crew_id for c in engine.world.crews]
    assert len(jobs) == 3
    assert plan_count(len(jobs), len(crews)) == 24
    every = list(plans(jobs, crews))
    assert len(every) == 24
    assert len(set(every)) == 24
    for plan in every:
        assert sorted(j for _, js in plan for j in js) == sorted(jobs)


@pytest.mark.parametrize(("jobs", "crews"), [(1, 2), (2, 2), (4, 2), (3, 3)])
def test_the_plan_count_is_every_split_in_every_order(jobs: int, crews: int) -> None:
    names = [f"J{i}" for i in range(jobs)]
    teams = [f"C{i}" for i in range(crews)]
    assert len(set(plans(names, teams))) == plan_count(jobs, crews)


def test_the_default_orders_own_plan_reproduces_it_step_for_step() -> None:
    _, engine = pilot()
    for scenario, damage in enumerate(engine.damage):
        default = simulate(engine.world, RunRequest(damage, scenario=scenario))
        plan = tuple(
            (crew, tuple(dict.fromkeys(
                e.job_id.removeprefix("repair:") for e in log if e.job_id.startswith("repair:"))))
            for crew, log in default.crews
        )  # fmt: skip
        planned = simulate(engine.world, RunRequest(damage, scenario=scenario, plan=plan))
        assert planned.states == default.states, scenario
        assert planned.levels == default.levels, scenario
        assert planned.crews == default.crews, scenario
        assert planned.completions == default.completions, scenario


def test_the_default_order_is_among_the_plans_and_the_optimum_no_worse(solved: Path) -> None:
    values = [float(row["request_04_lifeline"]) for row in answers(solved)]
    assert DEFAULT_ORDER_LIFELINE in values
    record = key(solved, RESTORATIVE[0])
    assert record["no_action"]["objective"] == DEFAULT_ORDER_LIFELINE
    assert record["optimum"]["objective"] <= DEFAULT_ORDER_LIFELINE


def test_a_plan_must_cover_every_job_once() -> None:
    _, engine = pilot()
    damage = engine.damage[SCENARIO]
    short = (("CRW-0001", ("SWM-TEL-L0001",)), ("CRW-0002", ()))
    with pytest.raises(ValueError, match="crew plan"):
        simulate(engine.world, RunRequest(damage, plan=short))


def test_a_ruled_alternative_stops_a_run_when_it_starts() -> None:
    _, engine = pilot()
    settings = replace(
        engine.world.settings, floor_after_generator_stops="throttle: runs at what arrives"
    )
    world = replace(engine.world, settings=settings)
    with pytest.raises(ValueError, match="floor_after_generator_stops"):
        simulate(world, RunRequest(engine.damage[3]))


def test_a_runner_counts_its_runs() -> None:
    _, engine = pilot()
    runner = Runner(engine.world, 72.0)
    runner.hours_out(engine.damage[3])
    assert runner.runs == 1


# --- The golden keys ------------------------------------------------------------------------


def recorded_hashes() -> dict[str, str]:
    lines = (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


def test_the_golden_keys_match_their_recorded_hashes() -> None:
    for name, digest in recorded_hashes().items():
        assert hashlib.sha256((GOLDEN / name).read_bytes()).hexdigest() == digest, name


def test_swm_solve_reproduces_the_golden_keys(solved: Path) -> None:
    written = sorted(p.name for p in solved.iterdir())
    assert written == sorted(recorded_hashes())
    for name in written:
        assert (solved / name).read_bytes() == (GOLDEN / name).read_bytes(), name


def test_a_second_solve_writes_the_same_bytes(solved: Path, tmp_path: Path) -> None:
    assert main(["solve", str(PILOT), "-o", str(tmp_path)]) == 0
    for path in sorted(solved.iterdir()):
        assert (tmp_path / "answer_keys" / path.name).read_bytes() == path.read_bytes()


def test_plan_text_names_a_crew_with_no_jobs() -> None:
    assert plan_text((("CRW-1", ()), ("CRW-2", ("A", "B")))) == "CRW-1: no jobs; CRW-2: A, B"


# --- Isolation (CLAUDE.md §3) ---------------------------------------------------------------


def _imported(path: Path) -> set[str]:
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_the_solver_never_imports_error_induction() -> None:
    for path in sorted((SRC / "solve").rglob("*.py")):
        assert not {n for n in _imported(path) if n.startswith("swm.errors")}, path


def test_nothing_in_the_generator_imports_the_solver() -> None:
    for path in sorted(SRC.rglob("*.py")):
        if path.is_relative_to(SRC / "solve") or path == SRC / "cli.py":
            continue
        assert not {n for n in _imported(path) if n.startswith("swm.solve")}, path


# --- The ceiling (Work Order 10, B5) --------------------------------------------------------


def _inputs(rules: Any) -> Any:
    from swm.recipe.io import recipe_sha256
    from swm.solve.solver import SolveInputs

    resolution, engine = pilot()
    built = _built(resolution)
    eligible = couplings_stage.eligible_suppliers(
        resolution.recipe.couplings, built.terrain, built.requirements.layers,
        built.requirements, built.rules,
    )  # fmt: skip
    return SolveInputs(resolution.recipe, recipe_sha256(resolution.recipe), rules, engine.world,
                       engine.damage, built.requirements.layers, eligible)  # fmt: skip


def test_a_search_projected_past_the_ceiling_stops_and_is_reported(capsys: Any) -> None:
    from swm.solve.solver import solve

    resolution, _ = pilot()
    rules = _built(resolution).rules.with_overrides({"solve.instance_bound_h": 1e-9})
    files = solve(_inputs(rules))
    record = yaml.safe_load(files["request_04_sequence_repair_crews_lifeline.yaml"])
    assert record["status"] == "stopped"
    assert "instance bound" in record["note"]
    index = yaml.safe_load(files["index.yaml"])["answer_keys"]
    assert [row["status"] for row in index if row["request"] in RESTORATIVE] == ["stopped"] * 2
    assert "24 plans: 24 runs, projected" in capsys.readouterr().out


def test_the_budget_counts_what_it_allows() -> None:
    from swm.solve.ceiling import Budget

    budget = Budget(ceiling_h=1.0, seconds_per_run=1800.0)
    assert budget.allows(1, "first")
    assert not budget.allows(2, "second")
    assert budget.spent_runs == 1
