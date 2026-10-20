"""The answer-key solver: requests in, stamped keys out, one per request.

Requests that differ only in their weights share one search (Work Order 10, B2). Every key
holds the stamp, the optimum with every tied answer, the measure and the spread, each rule of
thumb's distance, true criticality, the dose and the note (B3). Every answer and its objective
under each weighting is kept beside the key, compressed, so the spread can be recomputed.

Spec: structure v0.17 §5 and §7; Work Order 10, Parts B, C and D.
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
    StrikeNodes,
)
from swm.rules.registry import Registry
from swm.solve.ceiling import Budget
from swm.solve.measure import Range, spread
from swm.solve.offensive import CALM, NO_STRIKE, strike, strike_sets, strike_text, targets
from swm.solve.requests import Search, searches, stamp
from swm.solve.restorative import plan_text, plans, ranked_plan, repair_jobs
from swm.solve.runner import Job, Runner, with_node
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
DISTANCE = "(objective - optimum) / (no-action objective - optimum)"
DISTANCE_MIRRORED = "(optimum - objective) / (optimum - no-strike objective)"
"""The offensive model maximizes, so its measure mirrors (Work Order 10, D3)."""
NOT_RUN = "not run: it would pass the instance bound (solve.instance_bound_h)"
NOT_YET_BUILT = {
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


@dataclass(frozen=True)
class Found:
    """A search's results, before any weighting: what every key of the search is built from."""

    answers: list[tuple[str, Mapping[str, float]]]
    """Every affordable answer, as the key prints it, and its run's hours out."""
    no_action: tuple[str, Mapping[str, float]]
    mirrored: bool
    """True when the model maximizes (the offensive model)."""
    thumbs: dict[str, tuple[tuple[str, ...], list[str | None]]]
    """Each rule of thumb's ranking and its answer per weighting; None where it was not run."""
    criticality: Mapping[str, Mapping[str, float]] | None
    """Each node's hours out with it alone completely damaged; None where it was not run."""
    criticality_base: Mapping[str, float]


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
        if not isinstance(first, SequenceRepairCrews | StrikeNodes):
            note = NOT_YET_BUILT.get(first.model, f"no answer key for {first.model} in Phase 2")
            index_rows += [
                _index_row(i, requests[i], "not solved", None, note) for i in search.request_indices
            ]
            continue
        written = _search(inputs, search)
        files.update(written)
        for i in search.request_indices:
            name = _key_name(i, requests[i])
            key = yaml.safe_load(written[name].decode("utf-8"))
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


def _search(inputs: SolveInputs, search: Search) -> dict[str, bytes]:
    """Run one search, timed first and under the ceiling, and write its keys and answers."""
    requests = [inputs.recipe.answer_key_requests[i] for i in search.request_indices]
    first = requests[0]
    assert isinstance(first, SequenceRepairCrews | StrikeNodes)
    weightings = []
    for position, (i, r) in enumerate(zip(search.request_indices, requests, strict=True)):
        assert isinstance(r, SequenceRepairCrews | StrikeNodes)
        weights = node_weights(r, inputs.world.nodes)
        weightings.append(Weighting(i, position, f"request_{i:02d}_{r.service_weights}", weights))
    runner = Runner(inputs.world, float(first.window_h))
    budget = Budget(inputs.rules.number("solve.instance_bound_h"))
    if isinstance(first, SequenceRepairCrews):
        found = _restorative(inputs, search, first, runner, budget, weightings)
    else:
        found = _offensive(inputs, search, first, runner, budget, weightings)
    if found is None:
        return _stopped(search, requests, inputs.recipe_sha256)
    bands = [float(b) for b in inputs.rules.value("solve.spread_bands_pct")]
    name = _answers_name(search, first.model)
    files = {name: _answers_file(found.answers, weightings)}
    for weighting, request in zip(weightings, requests, strict=True):
        assert isinstance(request, SequenceRepairCrews | StrikeNodes)
        files[_key_name(weighting.index, request)] = _key(
            inputs, request, weighting, found, name, bands
        )
    return files


def _stopped(
    search: Search, requests: Sequence[AnswerKeyRequest], recipe_sha256: str
) -> dict[str, bytes]:
    files = {}
    for index, request in zip(search.request_indices, requests, strict=True):
        assert isinstance(request, SequenceRepairCrews | StrikeNodes)
        files[_key_name(index, request)] = canonical_yaml({
            "assumes": stamp(request, recipe_sha256),
            "status": "stopped",
            "note": "the search projects past the instance bound (solve.instance_bound_h); its "
                    "answer count and projected time are printed when it runs",
        })  # fmt: skip
    return files


def _answers_file(
    answers: Sequence[tuple[str, Mapping[str, float]]], weightings: Sequence[Weighting]
) -> bytes:
    """Every answer and its objective under each weighting, as bz2-compressed CSV.

    CHOICE: bz2, because its output carries no timestamp or file name and is the same bytes on
    every platform.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["answer", *(w.column for w in weightings)])
    for text, hours in answers:
        writer.writerow([text, *(f"{objective(hours, w.weights):.6f}" for w in weightings)])
    return bz2.compress(buffer.getvalue().encode("utf-8"), compresslevel=9)


def _best(
    answers: Sequence[tuple[str, Mapping[str, float]]], weights: Mapping[str, float], mirrored: bool
) -> str:
    """Return the best answer under one weighting; ties go to the first in search order.

    CHOICE: a rule of thumb solved on the nearest-supplier copy takes the first of its tied
    optima, in the order the search lists answers.
    """
    values = [objective(hours, weights) for _, hours in answers]
    best = max(values) if mirrored else min(values)
    return answers[values.index(best)][0]


def _criticality(
    runner: Runner, budget: Budget, base: Damage, nodes: Sequence[str], what: str
) -> Mapping[str, Mapping[str, float]] | None:
    """Return each node's hours out with it alone completely damaged on top of ``base``.

    The crews work in the default order, as for a strike (ruling Q4; Work Order 10, B3).
    """
    if not budget.allows(len(nodes), f"{what}: true criticality"):
        return None
    struck = runner.hours_out_all([(with_node(base, node), None) for node in nodes])
    return dict(zip(nodes, struck, strict=True))


# --- The restorative search (Part C) --------------------------------------------------------


def _restorative(
    inputs: SolveInputs,
    search: Search,
    request: SequenceRepairCrews,
    runner: Runner,
    budget: Budget,
    weightings: Sequence[Weighting],
) -> Found | None:
    """Search every crew plan of one scenario; None if the search would pass the ceiling."""
    if not 0 <= request.scenario < len(inputs.damage):
        raise SolveError(
            f"answer_key_requests[{search.first}].scenario {request.scenario} is not among the "
            f"{len(inputs.damage)} drawn"
        )
    damage = inputs.damage[request.scenario]
    crews = [c.crew_id for c in inputs.world.crews]
    jobs = repair_jobs(inputs.world, damage)
    every = list(plans(jobs, crews))
    budget.time_sample(lambda: runner.hours_out(damage))
    what = f"request {search.first} (sequence_repair_crews, scenario {request.scenario})"
    if not budget.allows(len(every), f"{what}: {len(every)} plans"):
        return None
    hours = runner.hours_out_all([(damage, plan) for plan in every])
    answers = [(plan_text(plan), h) for plan, h in zip(every, hours, strict=True)]
    default = runner.hours_out(damage)
    thumbs: dict[str, tuple[tuple[str, ...], list[str | None]]] = {}
    shares = capacity_shares(inputs.layers)
    for rule, ranking in (
        (MOST_CONNECTIONS, rank_by_degree(jobs, inputs.world)),
        (BIGGEST, rank_by_capacity(jobs, shares)),
    ):
        answer = (
            plan_text(ranked_plan(runner, damage, ranking))
            if budget.allows(len(ranking), f"{what}: {rule}")
            else None
        )
        thumbs[rule] = (ranking, [answer for _ in weightings])
    thumbs[NEAREST_SUPPLIER] = ((), _nearest(inputs, runner, budget, weightings, what, [
        (plan_text(plan), (damage, plan)) for plan in every], mirrored=False))  # fmt: skip
    nodes = [n.node_id for n in inputs.world.nodes]
    return Found(answers, (NO_ACTION_RESTORATIVE, default), False, thumbs,
                 _criticality(runner, budget, damage, nodes, what), default)  # fmt: skip


def _nearest(
    inputs: SolveInputs,
    runner: Runner,
    budget: Budget,
    weightings: Sequence[Weighting],
    what: str,
    answers: Sequence[tuple[str, Job]],
    mirrored: bool,
) -> list[str | None]:
    """Solve on the nearest-supplier copy by the same search; return its answer per weighting."""
    if not budget.allows(
        len(answers), f"{what}: {NEAREST_SUPPLIER} ({len(answers)} runs on the copy)"
    ):
        return [None for _ in weightings]
    copy = runner.on(nearest_supplier_world(inputs.world, inputs.eligible))
    hours = copy.hours_out_all([job for _, job in answers])
    on_copy = [(text, h) for (text, _), h in zip(answers, hours, strict=True)]
    return [_best(on_copy, w.weights, mirrored) for w in weightings]


# --- The offensive search (Part D) ----------------------------------------------------------


def _offensive(
    inputs: SolveInputs,
    search: Search,
    request: StrikeNodes,
    runner: Runner,
    budget: Budget,
    weightings: Sequence[Weighting],
) -> Found | None:
    """Search every set of k nodes struck on the calm world; None if it would pass the ceiling."""
    nodes = targets(inputs.world)
    sets = list(strike_sets(nodes, request.strikes_k))
    budget.time_sample(lambda: runner.hours_out(strike(sets[0])))
    what = f"request {search.first} (strike_nodes, k = {request.strikes_k})"
    if not budget.allows(len(sets), f"{what}: {len(sets)} strikes"):
        return None
    hours = runner.hours_out_all([(strike(s), None) for s in sets])
    answers = [(strike_text(s), h) for s, h in zip(sets, hours, strict=True)]
    calm = runner.hours_out(CALM)
    shares = capacity_shares(inputs.layers)
    thumbs: dict[str, tuple[tuple[str, ...], list[str | None]]] = {}
    for rule, ranking in (
        (MOST_CONNECTIONS, rank_by_degree(nodes, inputs.world)),
        (BIGGEST, rank_by_capacity(nodes, shares)),
    ):
        # Striking the top k is an answer the search already scored: no run is needed.
        answer = strike_text(ranking[: request.strikes_k])
        thumbs[rule] = (ranking, [answer for _ in weightings])
    thumbs[NEAREST_SUPPLIER] = ((), _nearest(inputs, runner, budget, weightings, what, [
        (strike_text(s), (strike(s), None)) for s in sets], mirrored=True))  # fmt: skip
    return Found(answers, (NO_STRIKE, calm), True, thumbs,
                 _criticality(runner, budget, CALM, nodes, what), calm)  # fmt: skip


# --- The key (Part B) -----------------------------------------------------------------------


def _key(
    inputs: SolveInputs,
    request: SequenceRepairCrews | StrikeNodes,
    weighting: Weighting,
    found: Found,
    answers_name: str,
    bands: Sequence[float],
) -> bytes:
    """One request's key (Work Order 10, B3)."""
    objectives = {text: objective(hours, weighting.weights) for text, hours in found.answers}
    best = max(objectives.values()) if found.mirrored else min(objectives.values())
    tied = [text for text, value in objectives.items() if value == best]
    no_action_text, no_action_hours = found.no_action
    measure = Range(best, objective(no_action_hours, weighting.weights), found.mirrored)
    return canonical_yaml({
        "assumes": stamp(request, inputs.recipe_sha256),
        "status": "solved",
        "optimum": {"objective": best, "answers": tied},
        "no_action": {"answer": no_action_text, "objective": measure.no_action},
        "measure": {
            "distance": DISTANCE_MIRRORED if found.mirrored else DISTANCE,
            "range": measure.width,
            "range_is_zero": measure.zero,
        },
        "spread": spread(list(objectives.values()), measure, bands),
        "answers_file": answers_name,
        "rules_of_thumb": _thumb_rows(found, weighting, objectives, measure),
        "true_criticality": _criticality_rows(found, weighting),
        "decision_relevant_dose": {"value": 0, "note": DOSE_NOTE},
        "note": SAMPLE_NOTE,
    })  # fmt: skip


def _thumb_rows(
    found: Found, weighting: Weighting, objectives: Mapping[str, float], measure: Range
) -> list[dict[str, object]]:
    rows = []
    for rule, (ranking, answers) in found.thumbs.items():
        row: dict[str, object] = {"rule": rule}
        if rule == BIGGEST:
            row["basis"] = BIGGEST_BASIS
        if ranking:
            row["ranking"] = list(ranking)
        answer = answers[weighting.position]
        if answer is None:
            row["status"] = NOT_RUN
        else:
            value = objectives[answer]
            row.update({"answer": answer, "objective": value,
                        "distance": measure.distance(value)})  # fmt: skip
        rows.append(row)
    return rows


def _criticality_rows(found: Found, weighting: Weighting) -> list[dict[str, object]] | str:
    if found.criticality is None:
        return NOT_RUN
    base = objective(found.criticality_base, weighting.weights)
    rows: list[dict[str, object]] = []
    for node, hours in found.criticality.items():
        value = objective(hours, weighting.weights)
        rows.append({"node": node, "objective": value, "increase": round(value - base, 6)})
    return rows
