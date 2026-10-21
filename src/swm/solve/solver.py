"""The answer-key solver: requests in, stamped keys out, one per request.

Requests that differ only in their weights share one search (Work Order 10, B2). Every key
holds the stamp, the optimum with every tied answer, the measure and the spread, each rule of
thumb's distance, true criticality, the dose and the note (B3). Every answer and its objective
under each weighting is kept beside the key, compressed, so the spread can be recomputed.

Spec: structure v0.17 §5 and §7; Work Order 10, Parts B to E.
"""

import bz2
import csv
import io
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import yaml
from numpy.typing import NDArray

from swm.dynamics.world import Damage, EngineWorld
from swm.recipe.io import canonical_yaml
from swm.recipe.schema import (
    AnswerKeyRequest,
    Layer,
    ObserveUncertainCouplings,
    ProtectConditionAndAddReserve,
    Recipe,
    SequenceRepairCrews,
    StrikeNodes,
)
from swm.rules.registry import Registry
from swm.solve.ceiling import Budget
from swm.solve.defensive import (
    NO_ACTION,
    Defence,
    defence_of,
    defence_text,
    defences,
    reserves_of,
    scenario_actions,
)
from swm.solve.measure import Range, spread
from swm.solve.offensive import CALM, NO_STRIKE, strike, strike_sets, strike_text, targets
from swm.solve.requests import Search, searches, stamp
from swm.solve.restorative import plan_of, plan_text, plans, ranked_plan, repair_jobs
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
from swm.solve.weights import PLACES, node_weights
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
SOLVED_MODELS = (SequenceRepairCrews, StrikeNodes, ProtectConditionAndAddReserve)
Solved = SequenceRepairCrews | StrikeNodes | ProtectConditionAndAddReserve


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
    protectable: tuple[str, ...] = ()
    """Every element the storm can damage, which protection can target (Work Order 10, E1)."""
    ceiling_h: float | None = None
    """A ceiling below the registry's for this run, or None (Work Order 10, B5)."""


@dataclass(frozen=True)
class Weighting:
    """One request of a search: its index, its column name and its weights."""

    index: int
    position: int
    """Its place among the search's weightings, from 0."""
    column: str
    weights: NDArray[np.float64]
    """Weight per end use, in the runner's column order."""


@dataclass(frozen=True)
class Found:
    """A search's results, before any weighting: what every key of the search is built from."""

    texts: tuple[str, ...]
    """Every affordable answer, as the key prints it, in search order."""
    hours: NDArray[np.float64]
    """Each answer's hours out per end use (h); for the defensive model, the scenarios' mean."""
    no_action: str
    no_action_hours: NDArray[np.float64]
    mirrored: bool
    """True when the model maximizes (the offensive model)."""
    thumbs: dict[str, tuple[tuple[str, ...], list[str | None]]]
    """Each rule of thumb's ranking and its answer per weighting; None where it was not run."""
    criticality: dict[str, NDArray[np.float64]] | None
    """Each node's hours out with it alone completely damaged; None where it was not run."""
    criticality_base: NDArray[np.float64]


def solve(inputs: SolveInputs, only: Sequence[int] = ()) -> dict[str, bytes]:
    """Solve a recipe's requests and return the key files, by path under ``answer_keys``.

    Parameters
    ----------
    inputs : SolveInputs
        The true world and the recipe.
    only : sequence of int
        Request indices to solve; each brings its whole search. Empty: every request.

    Returns
    -------
    dict of str to bytes
        One key per solved request and one answers file per search; with every request
        solved, the index too.

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
    for search in searches(requests):
        if only and not set(only) & set(search.request_indices):
            continue
        if isinstance(requests[search.first], SOLVED_MODELS):
            files.update(_search(inputs, search))
    return files


def index_file(requests: Sequence[AnswerKeyRequest], keys: Mapping[str, bytes]) -> bytes:
    """Return the index of a recipe's keys, from the key files there are.

    Parameters
    ----------
    requests : sequence of request
        The recipe's requests.
    keys : Mapping[str, bytes]
        Key files by name, however many runs wrote them.

    Returns
    -------
    bytes
        Canonical YAML: every request, its status and its key.

    Spec: Work Order 10, B1.
    """
    rows = []
    for index, request in enumerate(requests):
        name = key_name(index, request)
        if name in keys:
            status = str(yaml.safe_load(keys[name].decode("utf-8"))["status"])
            rows.append(_index_row(index, request, status, name, None))
        else:
            note = "not solved yet" if isinstance(request, SOLVED_MODELS) else (
                f"no answer key for {request.model} in Phase 2")  # fmt: skip
            rows.append(_index_row(index, request, "not solved", None, note))
    return canonical_yaml({"answer_keys": rows})


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


def key_name(index: int, request: AnswerKeyRequest) -> str:
    """Return the file name of a request's key."""
    return f"request_{index:02d}_{request.model}_{request.service_weights}.yaml"


def answers_name(search: Search, model: str) -> str:
    """Return the file name of a search's answers file."""
    return f"search_{search.first:02d}_{model}_answers.csv.bz2"


def objective_of(row: NDArray[np.float64], weights: NDArray[np.float64]) -> float:
    """Return weighted service-hours lost for one row of hours out, at 6 decimals.

    The sum is exact before rounding (``math.fsum``), so it does not depend on term order.

    Spec: structure v0.17 §5 (what unserved demand-hours counts).
    """
    return round(math.fsum((row * weights).tolist()), PLACES)


def weightings_of(inputs: SolveInputs, search: Search, columns: Sequence[str]) -> list[Weighting]:
    """Return each request of a search with its weights, in the runner's column order."""
    result = []
    for position, index in enumerate(search.request_indices):
        request = inputs.recipe.answer_key_requests[index]
        assert isinstance(request, SOLVED_MODELS)
        by_node = node_weights(request, inputs.world.nodes)
        weights = np.array([by_node[node] for node in columns], dtype=np.float64)
        result.append(Weighting(index, position, f"request_{index:02d}_{request.service_weights}",
                                weights))  # fmt: skip
    return result


def _search(inputs: SolveInputs, search: Search) -> dict[str, bytes]:
    """Run one search, timed first and under the ceiling, and write its keys and answers."""
    requests = [inputs.recipe.answer_key_requests[i] for i in search.request_indices]
    first = requests[0]
    assert isinstance(first, SOLVED_MODELS)
    runner = Runner(inputs.world, float(first.window_h))
    weightings = weightings_of(inputs, search, runner.end_uses)
    ceiling = inputs.rules.number("solve.instance_bound_h")
    budget = Budget(ceiling if inputs.ceiling_h is None else min(ceiling, inputs.ceiling_h))
    found = MODELS[type(first)](inputs, search, first, runner, budget, weightings)
    if found is None:
        return _stopped(search, requests, inputs.recipe_sha256)
    bands = [float(b) for b in inputs.rules.value("solve.spread_bands_pct")]
    name = answers_name(search, first.model)
    files = {name: _answers_file(found, weightings)}
    for weighting, request in zip(weightings, requests, strict=True):
        assert isinstance(request, SOLVED_MODELS)
        files[key_name(weighting.index, request)] = _key(
            inputs, request, weighting, found, name, bands
        )
    return files


def _stopped(
    search: Search, requests: Sequence[AnswerKeyRequest], recipe_sha256: str
) -> dict[str, bytes]:
    files = {}
    for index, request in zip(search.request_indices, requests, strict=True):
        assert isinstance(request, SOLVED_MODELS)
        files[key_name(index, request)] = canonical_yaml({
            "assumes": stamp(request, recipe_sha256),
            "status": "stopped",
            "note": "the search projects past the instance bound (solve.instance_bound_h); its "
                    "answer count and projected time are printed when it runs",
        })  # fmt: skip
    return files


def _answers_file(found: Found, weightings: Sequence[Weighting]) -> bytes:
    """Every answer and its objective under each weighting, as bz2-compressed CSV.

    CHOICE: bz2, because its output carries no timestamp or file name and is the same bytes on
    every platform.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["answer", *(w.column for w in weightings)])
    for text, row in zip(found.texts, found.hours, strict=True):
        writer.writerow([text, *(f"{objective_of(row, w.weights):.6f}" for w in weightings)])
    return bz2.compress(buffer.getvalue().encode("utf-8"), compresslevel=9)


def _objectives(found_hours: NDArray[np.float64], weights: NDArray[np.float64]) -> list[float]:
    return [objective_of(row, weights) for row in found_hours]


def _best(texts: Sequence[str], values: Sequence[float], mirrored: bool) -> str:
    """Return the best answer; ties go to the first in search order.

    CHOICE: a rule of thumb takes the first of its tied best answers, in the order the search
    lists answers.
    """
    best = max(values) if mirrored else min(values)
    return texts[list(values).index(best)]


def _criticality(
    runner: Runner, budget: Budget, scenarios: Sequence[Damage], nodes: Sequence[str], what: str
) -> dict[str, NDArray[np.float64]] | None:
    """Return each node's hours out with it alone completely damaged on top of each scenario.

    The crews work in the default order, as for a strike (ruling Q4); over several scenarios,
    the mean (Work Order 10, B3).
    """
    runs = len(nodes) * len(scenarios)
    if not budget.allows(runs, f"{what}: true criticality"):
        return None
    rows = runner.rows([Job(with_node(s, node)) for node in nodes for s in scenarios])
    width = len(scenarios)
    return {node: mean_rows(rows[i * width : (i + 1) * width]) for i, node in enumerate(nodes)}


def mean_rows(rows: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the mean of rows of hours out, each column summed exactly (``math.fsum``)."""
    count = len(rows)
    return np.array([math.fsum(rows[:, c].tolist()) / count for c in range(rows.shape[1])])


def _nearest(
    inputs: SolveInputs,
    runner: Runner,
    budget: Budget,
    weightings: Sequence[Weighting],
    what: str,
    texts: Sequence[str],
    jobs: Sequence[Job],
    combine: Callable[[NDArray[np.float64]], NDArray[np.float64]],
    mirrored: bool,
) -> list[str | None]:
    """Solve on the nearest-supplier copy by the same search; return its answer per weighting."""
    if not budget.allows(len(jobs), f"{what}: {NEAREST_SUPPLIER} ({len(jobs)} runs on the copy)"):
        return [None for _ in weightings]
    copy = runner.on(nearest_supplier_world(inputs.world, inputs.eligible))
    hours = combine(copy.rows(jobs))
    return [_best(texts, _objectives(hours, w.weights), mirrored) for w in weightings]


def _ranked(
    texts: Sequence[str],
    hours: NDArray[np.float64],
    weightings: Sequence[Weighting],
    mirrored: bool,
    allowed: Callable[[str], bool],
) -> list[str | None]:
    """Return the best answer among those a ranking allows, per weighting (search order ties)."""
    chosen = [i for i, text in enumerate(texts) if allowed(text)]
    picks: list[str | None] = []
    for w in weightings:
        values = [objective_of(hours[i], w.weights) for i in chosen]
        picks.append(_best([texts[i] for i in chosen], values, mirrored))
    return picks


# --- The restorative search (Part C) --------------------------------------------------------


def _restorative(
    inputs: SolveInputs,
    search: Search,
    request: Solved,
    runner: Runner,
    budget: Budget,
    weightings: Sequence[Weighting],
) -> Found | None:
    """Search every crew plan of one scenario; None if the search would pass the ceiling."""
    assert isinstance(request, SequenceRepairCrews)
    damage = _scenario(inputs, search, request)
    crews = [c.crew_id for c in inputs.world.crews]
    jobs_ = repair_jobs(inputs.world, damage)
    every = list(plans(jobs_, crews))
    runs = [Job(damage, plan) for plan in every]
    what = f"request {search.first} (sequence_repair_crews, scenario {request.scenario})"
    hours = budget.search(runner, runs, f"{what}: {len(every)} plans")
    if hours is None:
        return None
    texts = tuple(plan_text(plan) for plan in every)
    default = runner.rows([Job(damage)])[0]
    thumbs: dict[str, tuple[tuple[str, ...], list[str | None]]] = {}
    shares = capacity_shares(inputs.layers)
    for rule, ranking in (
        (MOST_CONNECTIONS, rank_by_degree(jobs_, inputs.world)),
        (BIGGEST, rank_by_capacity(jobs_, shares)),
    ):
        answer = (
            plan_text(ranked_plan(runner, damage, ranking))
            if budget.allows(len(ranking), f"{what}: {rule}")
            else None
        )
        thumbs[rule] = (ranking, [answer for _ in weightings])
    nearest = _nearest(inputs, runner, budget, weightings, what, texts, runs, _same, False)
    thumbs[NEAREST_SUPPLIER] = ((), nearest)
    nodes = [n.node_id for n in inputs.world.nodes]
    return Found(texts, hours, NO_ACTION_RESTORATIVE, default, False, thumbs,
                 _criticality(runner, budget, [damage], nodes, what), default)  # fmt: skip


def _scenario(inputs: SolveInputs, search: Search, request: SequenceRepairCrews) -> Damage:
    if not 0 <= request.scenario < len(inputs.damage):
        raise SolveError(
            f"answer_key_requests[{search.first}].scenario {request.scenario} is not among the "
            f"{len(inputs.damage)} drawn"
        )
    return inputs.damage[request.scenario]


# --- The offensive search (Part D) ----------------------------------------------------------


def _offensive(
    inputs: SolveInputs,
    search: Search,
    request: Solved,
    runner: Runner,
    budget: Budget,
    weightings: Sequence[Weighting],
) -> Found | None:
    """Search every set of k nodes struck on the calm world; None if it would pass the ceiling."""
    assert isinstance(request, StrikeNodes)
    nodes = targets(inputs.world)
    sets = list(strike_sets(nodes, request.strikes_k))
    runs = [Job(strike(s)) for s in sets]
    what = f"request {search.first} (strike_nodes, k = {request.strikes_k})"
    hours = budget.search(runner, runs, f"{what}: {len(sets)} strikes")
    if hours is None:
        return None
    texts = tuple(strike_text(s) for s in sets)
    calm = runner.rows([Job(CALM)])[0]
    shares = capacity_shares(inputs.layers)
    thumbs: dict[str, tuple[tuple[str, ...], list[str | None]]] = {}
    for rule, ranking in (
        (MOST_CONNECTIONS, rank_by_degree(nodes, inputs.world)),
        (BIGGEST, rank_by_capacity(nodes, shares)),
    ):
        # Striking the top k is an answer the search already scored: no run is needed.
        answer = strike_text(ranking[: request.strikes_k])
        thumbs[rule] = (ranking, [answer for _ in weightings])
    nearest = _nearest(inputs, runner, budget, weightings, what, texts, runs, _same, True)
    thumbs[NEAREST_SUPPLIER] = ((), nearest)
    return Found(texts, hours, NO_STRIKE, calm, True, thumbs,
                 _criticality(runner, budget, [CALM], nodes, what), calm)  # fmt: skip


# --- The defensive search (Part E) ----------------------------------------------------------


@dataclass(frozen=True)
class _Plays:
    """The runs a defensive search makes, and which run each answer takes in each scenario."""

    jobs: list[Job]
    """Every distinct run, in the order first needed."""
    use: NDArray[np.int64]
    """Shape (answers, scenarios): the job each answer's scenario takes."""


def _defensive(
    inputs: SolveInputs,
    search: Search,
    request: Solved,
    runner: Runner,
    budget: Budget,
    weightings: Sequence[Weighting],
) -> Found | None:
    """Search every affordable defence over every scenario; None if it would pass the ceiling."""
    assert isinstance(request, ProtectConditionAndAddReserve)
    answers = list(_defences(inputs, request))
    plays = defensive_plays(inputs, answers, float(request.window_h))
    what = f"request {search.first} (protect_condition_and_add_reserve, budget " \
        f"{request.budget_cost_units})"  # fmt: skip
    rows = budget.search(runner, plays.jobs, f"{what}: {len(answers)} answers")
    if rows is None:
        return None
    hours = _means(rows, plays.use)
    texts = tuple(defence_text(a) for a in answers)
    none = hours[texts.index(NO_ACTION)]
    thumbs: dict[str, tuple[tuple[str, ...], list[str | None]]] = {}
    elements = sorted({*inputs.protectable, *(n.node_id for n in inputs.world.nodes)})
    shares = capacity_shares(inputs.layers)
    m = request.budget_cost_units
    for rule, ranking in (
        (MOST_CONNECTIONS, rank_by_degree(elements, inputs.world)),
        (BIGGEST, rank_by_capacity(elements, shares)),
    ):
        allowed = _within(set(ranking[:m]))
        thumbs[rule] = (ranking, _ranked(texts, hours, weightings, False, allowed))
    thumbs[NEAREST_SUPPLIER] = ((), _nearest(
        inputs, runner, budget, weightings, what, texts, plays.jobs,
        lambda copied: _means(copied, plays.use), mirrored=False))  # fmt: skip
    nodes = [n.node_id for n in inputs.world.nodes]
    return Found(texts, hours, NO_ACTION, none, False, thumbs,
                 _criticality(runner, budget, inputs.damage, nodes, what), none)  # fmt: skip


def _within(top: set[str]) -> Callable[[str], bool]:
    """Return whether an answer's actions target only the top-ranked elements (WO 10, B4)."""
    return lambda text: defence_of(text).targets() <= top


def _same(rows: NDArray[np.float64]) -> NDArray[np.float64]:
    return rows


def _defences(inputs: SolveInputs, request: ProtectConditionAndAddReserve) -> list[Defence]:
    return list(defences(
        inputs.protectable, reserves_of(inputs.world), request.budget_cost_units,
        request.protect_condition_cost_units, request.add_reserve_cost_units,
    ))  # fmt: skip


def defensive_plays(inputs: SolveInputs, answers: Sequence[Defence], window_h: float) -> _Plays:
    """Return the distinct runs a set of defences needs over every scenario, and their use.

    Two skips, each provably identical (Work Order 10, E4):
    - a scenario with no damage is run once, with no actions: with nothing damaged, nothing is
      short, so no reserve is drawn and no protection has an element to keep up;
    - in each scenario, a protection of an element that scenario did not damage is left out of
      the run (the engine protects only damaged elements), so answers that differ only in such
      protections share the run. An answer that protects an element no scenario damages
      therefore scores exactly what the same answer without it scores.

    Parameters
    ----------
    inputs : SolveInputs
        The true world and its scenarios.
    answers : sequence of Defence
        The defences.
    window_h : float
        The request's window, in h.

    Returns
    -------
    _Plays
        The runs and each answer's run per scenario.

    Spec: Work Order 10, E4 and E5 (reuse what repeats).
    """
    jobs: list[Job] = []
    seen: dict[Job, int] = {}
    use = np.empty((len(answers), len(inputs.damage)), dtype=np.int64)
    for a, defence in enumerate(answers):
        for s, damage in enumerate(inputs.damage):
            undamaged = not damage.nodes and not damage.lines
            actions = () if undamaged else scenario_actions(
                defence, damage, inputs.world.stocks, window_h)  # fmt: skip
            # Equal jobs are the same run, so each is played once.
            job = Job(damage, actions=actions)
            if job not in seen:
                seen[job] = len(jobs)
                jobs.append(job)
            use[a, s] = seen[job]
    return _Plays(jobs, use)


def _means(rows: NDArray[np.float64], use: NDArray[np.int64]) -> NDArray[np.float64]:
    """Return each answer's mean hours out over the scenarios (equally weighted; ruling Q7)."""
    return np.array([mean_rows(rows[use[a]]) for a in range(len(use))])


MODELS: dict[type, Callable[..., Found | None]] = {
    SequenceRepairCrews: _restorative,
    StrikeNodes: _offensive,
    ProtectConditionAndAddReserve: _defensive,
}


# --- Every affordable answer, and re-scoring (the CI checks) --------------------------------


def answer_texts(inputs: SolveInputs, search: Search) -> tuple[str, ...]:
    """Return every affordable answer of a search, in search order, without running anything.

    Spec: Work Order 10, B3 (the answers file lists every affordable answer).
    """
    request = inputs.recipe.answer_key_requests[search.first]
    if isinstance(request, SequenceRepairCrews):
        damage = _scenario(inputs, search, request)
        crews = [c.crew_id for c in inputs.world.crews]
        return tuple(plan_text(p) for p in plans(repair_jobs(inputs.world, damage), crews))
    if isinstance(request, StrikeNodes):
        return tuple(strike_text(s) for s in strike_sets(targets(inputs.world), request.strikes_k))
    assert isinstance(request, ProtectConditionAndAddReserve)
    return tuple(defence_text(a) for a in _defences(inputs, request))


def rescore(
    inputs: SolveInputs, search: Search, texts: Sequence[str]
) -> dict[str, tuple[str, ...]]:
    """Run chosen answers again and return each one's objectives as the answers file prints them.

    Parameters
    ----------
    inputs : SolveInputs
        The true world and the recipe.
    search : Search
        The search the answers belong to.
    texts : sequence of str
        Answers, as the key prints them.

    Returns
    -------
    dict of str to tuple of str
        Each answer's objective per weighting, at 6 decimals.

    Spec: Work Order 10, E6 as amended (CI re-scores chosen answers on both platforms).
    """
    request = inputs.recipe.answer_key_requests[search.first]
    assert isinstance(request, SOLVED_MODELS)
    runner = Runner(inputs.world, float(request.window_h))
    weightings = weightings_of(inputs, search, runner.end_uses)
    if isinstance(request, SequenceRepairCrews):
        damage = _scenario(inputs, search, request)
        hours = runner.rows([Job(damage, plan_of(t)) for t in texts])
    elif isinstance(request, StrikeNodes):
        hours = runner.rows([Job(strike(t.split(", "))) for t in texts])
    else:
        plays = defensive_plays(inputs, [defence_of(t) for t in texts], float(request.window_h))
        hours = _means(runner.rows(plays.jobs), plays.use)
    return {
        text: tuple(f"{objective_of(row, w.weights):.6f}" for w in weightings)
        for text, row in zip(texts, hours, strict=True)
    }


# --- The key (Part B) -----------------------------------------------------------------------


def _key(
    inputs: SolveInputs,
    request: Solved,
    weighting: Weighting,
    found: Found,
    answers_file: str,
    bands: Sequence[float],
) -> bytes:
    """One request's key (Work Order 10, B3)."""
    values = _objectives(found.hours, weighting.weights)
    best = max(values) if found.mirrored else min(values)
    tied = [text for text, value in zip(found.texts, values, strict=True) if value == best]
    measure = Range(best, objective_of(found.no_action_hours, weighting.weights), found.mirrored)
    by_text = dict(zip(found.texts, values, strict=True))
    return canonical_yaml({
        "assumes": stamp(request, inputs.recipe_sha256),
        "status": "solved",
        "optimum": {"objective": best, "answers": tied},
        "no_action": {"answer": found.no_action, "objective": measure.no_action},
        "measure": {
            "distance": DISTANCE_MIRRORED if found.mirrored else DISTANCE,
            "range": measure.width,
            "range_is_zero": measure.zero,
        },
        "spread": spread(values, measure, bands),
        "answers_file": answers_file,
        "rules_of_thumb": _thumb_rows(found, weighting, by_text, measure),
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
    base = objective_of(found.criticality_base, weighting.weights)
    rows: list[dict[str, object]] = []
    for node, hours in found.criticality.items():
        value = objective_of(hours, weighting.weights)
        rows.append({"node": node, "objective": value, "increase": round(value - base, 6)})
    return rows
