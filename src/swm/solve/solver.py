"""The answer-key solver: requests in, stamped keys out, one per request.

Requests that differ only in their weights share one search (Work Order 10, B2). Every key
holds the stamp, the optimum with every tied answer, the measure and the spread, each rule of
thumb's distance, true criticality, the dose and the note (B3). Every answer and its objective
under each weighting is kept beside the key, compressed, so the spread can be recomputed.

Spec: structure v0.17 §5 and §7; Work Order 10, Parts B and C.
"""

import bz2
import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import yaml

from swm.dynamics.world import Damage, EngineWorld
from swm.recipe.io import canonical_yaml
from swm.recipe.schema import (
    AnswerKeyRequest,
    Layer,
    ObserveUncertainCouplings,
    Recipe,
    SequenceRepairCrews,
)
from swm.rules.registry import Registry
from swm.solve.ceiling import Budget
from swm.solve.measure import Range, spread
from swm.solve.requests import Search, searches, stamp
from swm.solve.restorative import plan_count, plan_text, plans, ranked_plan, repair_jobs
from swm.solve.runner import Plan, Runner, with_node
from swm.solve.thumbs import (
    BIGGEST,
    BIGGEST_BASIS,
    MOST_CONNECTIONS,
    NEAREST_SUPPLIER,
    capacity_shares,
    nearest_supplier_world,
    rank_by_capacity,
    rank_by_degree,
)
from swm.solve.weights import node_weights, objective
from swm.stages.layers import LayersResult

KEY_DIR = "answer_keys"
INFORMATIVE_REFUSAL = (
    "the informative answer key is built in Phase 4, against the pipeline's belief"
)
DOSE_NOTE = "no error planted until Phase 3"
SAMPLE_NOTE = (
    "optimal against the scenarios named in the stamp, a sample of the storm, not the storm in "
    "general"
)
NO_ACTION_RESTORATIVE = "the default crew order"
"""CHOICE: the restorative model's no-action answer is the default crew order: what the crews
do when no plan is given. Every plan repairs every job, so no plan repairs nothing."""
NOT_YET_BUILT = {
    "strike_nodes": "not built in this release: the offensive model arrives with PR 10b",
    "protect_condition_and_add_reserve": (
        "not built in this release: the defensive model arrives with PR 10c"
    ),
}
"""CHOICE: requests whose model a later pull request builds are listed in the index, unsolved,
so that ``swm solve`` runs on a recipe that carries them."""


class SolveError(ValueError):
    """A request the solver refuses."""


@dataclass(frozen=True)
class SolveInputs:
    """The true world, as the solver reads it."""

    recipe: Recipe
    recipe_sha256: str
    rules: Registry
    world: EngineWorld
    damage: tuple[Damage, ...]
    """Each storm scenario's damage at hour 0."""
    layers: LayersResult
    """The sized layers, for capacity."""
    eligible: Mapping[tuple[str, Layer], Sequence[str]]
    """Each consumer's eligible suppliers, nearest first."""


@dataclass(frozen=True)
class Weighting:
    """One request of a search: its index, its column name and its weights."""

    index: int
    position: int
    """Its place among the search's weightings, from 0."""
    column: str
    weights: Mapping[str, float]


def solve(inputs: SolveInputs) -> dict[str, bytes]:
    """Solve every request of a recipe and return the key files, by path under ``answer_keys``.

    Parameters
    ----------
    inputs : SolveInputs
        The true world and the recipe.

    Returns
    -------
    dict of str to bytes
        The index, one key per solved request, and one answers file per search.

    Raises
    ------
    SolveError
        If a request is informative (ruling Q9).

    Spec: structure v0.17 §5; Work Order 10, B1-B5.
    """
    requests = inputs.recipe.answer_key_requests
    for index, request in enumerate(requests):
        if isinstance(request, ObserveUncertainCouplings):
            raise SolveError(f"answer_key_requests[{index}]: {INFORMATIVE_REFUSAL}")
    files: dict[str, bytes] = {}
    index_rows = []
    for search in searches(requests):
        first = requests[search.first]
        if not isinstance(first, SequenceRepairCrews):
            note = NOT_YET_BUILT.get(first.model, f"no answer key for {first.model} in Phase 2")
            index_rows += [
                _index_row(i, requests[i], "not solved", None, note) for i in search.request_indices
            ]
            continue
        found = _restorative(inputs, search)
        files.update(found)
        for i in search.request_indices:
            name = _key_name(i, requests[i])
            key = yaml.safe_load(found[name].decode("utf-8"))
            index_rows.append(_index_row(i, requests[i], str(key["status"]), name, None))
    index_rows.sort(key=lambda row: int(str(row["request"])))
    files["index.yaml"] = canonical_yaml({"answer_keys": index_rows})
    return files


def _index_row(
    index: int, request: AnswerKeyRequest, status: str, key: str | None, note: str | None
) -> dict[str, object]:
    return {
        "request": index,
        "model": request.model,
        "service_weights": str(request.service_weights),
        "status": status,
        "key": key,
        "note": note,
    }


def _key_name(index: int, request: AnswerKeyRequest) -> str:
    return f"request_{index:02d}_{request.model}_{request.service_weights}.yaml"


def _answers_name(search: Search, model: str) -> str:
    return f"search_{search.first:02d}_{model}_answers.csv.bz2"


# --- The restorative search (Part C) --------------------------------------------------------


def _restorative(inputs: SolveInputs, search: Search) -> dict[str, bytes]:
    """Search every plan of one scenario and write one key per request of the search."""
    requests = [inputs.recipe.answer_key_requests[i] for i in search.request_indices]
    first = requests[0]
    assert isinstance(first, SequenceRepairCrews)
    if not 0 <= first.scenario < len(inputs.damage):
        raise SolveError(
            f"answer_key_requests[{search.first}].scenario {first.scenario} is not among the "
            f"{len(inputs.damage)} drawn"
        )
    damage = inputs.damage[first.scenario]
    runner = Runner(inputs.world, float(first.window_h))
    weightings = [
        Weighting(i, position, f"request_{i:02d}_{r.service_weights}",
                  node_weights(r, inputs.world.nodes))
        for position, (i, r) in enumerate(zip(search.request_indices, requests, strict=True))
        if isinstance(r, SequenceRepairCrews)
    ]  # fmt: skip
    crews = [c.crew_id for c in inputs.world.crews]
    jobs = repair_jobs(inputs.world, damage)
    count = plan_count(len(jobs), len(crews))
    budget = Budget(inputs.rules.number("solve.instance_bound_h"))
    budget.time_sample(lambda: runner.hours_out(damage))
    what = f"request {search.first} (sequence_repair_crews, scenario {first.scenario})"
    if not budget.allows(count, f"{what}: {count} plans"):
        return _stopped(search, requests, inputs.recipe_sha256, count)
    scored = [(plan, runner.hours_out(damage, plan)) for plan in plans(jobs, crews)]
    default = runner.hours_out(damage)
    answers = _answers_file(scored, weightings)
    thumbs = _restorative_thumbs(inputs, runner, budget, damage, jobs, scored, weightings, what)
    critical = _criticality(inputs, runner, budget, damage, default, weightings, what)
    files = {_answers_name(search, first.model): answers}
    for weighting, request in zip(weightings, requests, strict=True):
        assert isinstance(request, SequenceRepairCrews)
        files[_key_name(weighting.index, request)] = _key(
            inputs, request, weighting, scored, default, thumbs, critical,
            _answers_name(search, first.model),
        )  # fmt: skip
    return files


def _stopped(
    search: Search, requests: Sequence[object], recipe_sha256: str, count: int
) -> dict[str, bytes]:
    files = {}
    for index, request in zip(search.request_indices, requests, strict=True):
        assert isinstance(request, SequenceRepairCrews)
        files[_key_name(index, request)] = canonical_yaml({
            "assumes": stamp(request, recipe_sha256),
            "status": "stopped",
            "note": f"the search's {count} answers project past the instance bound "
                    "(solve.instance_bound_h); the projection is printed when it runs",
        })  # fmt: skip
    return files


def _answers_file(
    scored: Sequence[tuple[Plan, Mapping[str, float]]], weightings: Sequence[Weighting]
) -> bytes:
    """Every answer and its objective under each weighting, as bz2-compressed CSV.

    CHOICE: bz2, because its output carries no timestamp or file name and is the same bytes on
    every platform.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["answer", *(w.column for w in weightings)])
    for plan, hours in scored:
        writer.writerow(
            [plan_text(plan), *(f"{objective(hours, w.weights):.6f}" for w in weightings)]
        )
    return bz2.compress(buffer.getvalue().encode("utf-8"), compresslevel=9)


def _restorative_thumbs(
    inputs: SolveInputs,
    runner: Runner,
    budget: Budget,
    damage: Damage,
    jobs: Sequence[str],
    scored: Sequence[tuple[Plan, Mapping[str, float]]],
    weightings: Sequence[Weighting],
    what: str,
) -> dict[str, list[tuple[tuple[str, ...], Plan | None]]]:
    """Each rule of thumb's ranking and answer, per weighting; None where it was not run."""
    thumbs: dict[str, list[tuple[tuple[str, ...], Plan | None]]] = {}
    shares = capacity_shares(inputs.layers)
    for rule, ranking in (
        (MOST_CONNECTIONS, rank_by_degree(jobs, inputs.world)),
        (BIGGEST, rank_by_capacity(jobs, shares)),
    ):
        if budget.allows(len(ranking), f"{what}: {rule}"):
            plan = ranked_plan(runner, damage, ranking)
            thumbs[rule] = [(ranking, plan) for _ in weightings]
        else:
            thumbs[rule] = [(ranking, None) for _ in weightings]
    copy = runner.on(nearest_supplier_world(inputs.world, inputs.eligible))
    count = len(scored)
    if budget.allows(count, f"{what}: {NEAREST_SUPPLIER} ({count} plans on the copy)"):
        on_copy = [(plan, copy.hours_out(damage, plan)) for plan, _ in scored]
        thumbs[NEAREST_SUPPLIER] = [
            ((), min(on_copy, key=lambda item: objective(item[1], w.weights))[0])
            for w in weightings
        ]
    else:
        thumbs[NEAREST_SUPPLIER] = [((), None) for _ in weightings]
    return thumbs


def _criticality(
    inputs: SolveInputs,
    runner: Runner,
    budget: Budget,
    damage: Damage,
    default: Mapping[str, float],
    weightings: Sequence[Weighting],
    what: str,
) -> list[list[dict[str, object]]] | None:
    """Return each node's true criticality per weighting, or None where it was not run.

    A node's criticality is the objective with it alone completely damaged on top of the
    scenario, crews in the default order, less the objective without it (Work Order 10, B3).
    """
    nodes = [n.node_id for n in inputs.world.nodes]
    if not budget.allows(len(nodes), f"{what}: true criticality"):
        return None
    struck = {node: runner.hours_out(with_node(damage, node)) for node in nodes}
    rows = []
    for w in weightings:
        base = objective(default, w.weights)
        rows.append([
            {"node": node, "objective": objective(struck[node], w.weights),
             "increase": round(objective(struck[node], w.weights) - base, 6)}
            for node in nodes
        ])  # fmt: skip
    return rows


def _key(
    inputs: SolveInputs,
    request: SequenceRepairCrews,
    weighting: Weighting,
    scored: Sequence[tuple[Plan, Mapping[str, float]]],
    default: Mapping[str, float],
    thumbs: Mapping[str, list[tuple[tuple[str, ...], Plan | None]]],
    critical: list[list[dict[str, object]]] | None,
    answers_name: str,
) -> bytes:
    """One request's key (Work Order 10, B3)."""
    objectives = {plan: objective(hours, weighting.weights) for plan, hours in scored}
    best = min(objectives.values())
    tied = [plan_text(plan) for plan, value in objectives.items() if value == best]
    measure = Range(best, objective(default, weighting.weights))
    bands = [float(b) for b in inputs.rules.value("solve.spread_bands_pct")]
    column = weighting.position
    rules = []
    for rule, per_weighting in thumbs.items():
        ranking, plan = per_weighting[column]
        row: dict[str, object] = {"rule": rule}
        if rule == BIGGEST:
            row["basis"] = BIGGEST_BASIS
        if ranking:
            row["ranking"] = list(ranking)
        if plan is None:
            row["status"] = "not run: it would pass the instance bound (solve.instance_bound_h)"
        else:
            value = objectives[plan]
            row.update({"answer": plan_text(plan), "objective": value,
                        "distance": measure.distance(value)})  # fmt: skip
        rules.append(row)
    return canonical_yaml({
        "assumes": stamp(request, inputs.recipe_sha256),
        "status": "solved",
        "optimum": {"objective": best, "answers": tied},
        "no_action": {"answer": NO_ACTION_RESTORATIVE, "objective": measure.no_action},
        "measure": {
            "distance": "(objective - optimum) / (no-action objective - optimum)",
            "range": measure.width,
            "range_is_zero": measure.zero,
        },
        "spread": spread(list(objectives.values()), measure, bands),
        "answers_file": answers_name,
        "rules_of_thumb": rules,
        "true_criticality": (
            critical[column] if critical is not None
            else "not run: it would pass the instance bound (solve.instance_bound_h)"
        ),
        "decision_relevant_dose": {"value": 0, "note": DOSE_NOTE},
        "note": SAMPLE_NOTE,
    })  # fmt: skip
