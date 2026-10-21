"""CI's checks on every answer key, for every model (Work Order 10, E6 as amended).

A key can take a day to find, so CI does not re-solve it. It checks, without a search:
- each key's and answers file's hash;
- that the answers file lists every affordable answer, counted by enumeration;
- that the stored optimum is the best score in the file, with every tie listed;
- the spread, recomputed from the file.

And it re-scores, on both platforms and byte-exact against the stored scores: the optimum and
every tie, the three rules of thumb, the 50 next-best answers, and 50 answers chosen by a fixed
stable-hash rule.

The full re-solve is the test marked ``slow``. It is required on any pull request that touches
``dynamics/``, ``solve/`` or a dynamics rule in the registry: ``uv run pytest -m slow``.

Spec: structure v0.17 §5; Work Order 10, B3 and E6 (amended for every model, 2026-10-21).
"""

import bz2
import csv
import functools
import hashlib
import io
from pathlib import Path
from typing import Any

import pytest
import yaml

from swm.cli import solve_inputs
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import StrikeNodes
from swm.solve.measure import Range, spread
from swm.solve.requests import Search, searches
from swm.solve.solver import answer_texts, answers_name, rescore, solve

TESTS = Path(__file__).resolve().parents[1]
PILOT = TESTS / "fixtures" / "pilot_hand_check.yaml"
GOLDEN = TESTS / "golden" / "pilot_answer_keys"
NEXT_BEST = 50
STABLE_HASH_SAMPLE = 50
"""The re-scored samples (Work Order 10, E6 as amended): the 50 answers after the ties, by
objective, and the 50 answers whose SHA-256 of their text is smallest."""


@functools.cache
def inputs() -> Any:
    return solve_inputs(resolve(load_recipe(PILOT)))


def golden_searches() -> list[Search]:
    """The searches whose keys the golden folder holds."""
    requests = load_recipe(PILOT).answer_key_requests
    index = yaml.safe_load((GOLDEN / "index.yaml").read_text(encoding="utf-8"))["answer_keys"]
    solved = {row["request"] for row in index if row["status"] == "solved"}
    return [s for s in searches(requests) if s.first in solved]


SEARCHES = {f"search_{s.first:02d}": s for s in golden_searches()}


def answers_rows(search: Search) -> list[dict[str, str]]:
    model = load_recipe(PILOT).answer_key_requests[search.first].model
    body = bz2.decompress((GOLDEN / answers_name(search, model)).read_bytes())
    return list(csv.DictReader(io.StringIO(body.decode("utf-8"))))


def keys_of(search: Search) -> list[tuple[str, dict[str, Any]]]:
    """Each request of the search: its answers-file column and its key."""
    requests = load_recipe(PILOT).answer_key_requests
    result = []
    for index in search.request_indices:
        request = requests[index]
        name = f"request_{index:02d}_{request.model}_{request.service_weights}.yaml"
        key = yaml.safe_load((GOLDEN / name).read_text(encoding="utf-8"))
        result.append((f"request_{index:02d}_{request.service_weights}", key))
    return result


def mirrored(search: Search) -> bool:
    return isinstance(load_recipe(PILOT).answer_key_requests[search.first], StrikeNodes)


def recorded_hashes() -> dict[str, str]:
    lines = (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


def test_every_golden_file_matches_its_recorded_hash() -> None:
    written = sorted(p.name for p in GOLDEN.iterdir() if p.name != "SHA256SUMS")
    assert written == sorted(recorded_hashes())
    for name, digest in recorded_hashes().items():
        assert hashlib.sha256((GOLDEN / name).read_bytes()).hexdigest() == digest, name


@pytest.mark.parametrize("name", sorted(SEARCHES))
def test_the_answers_file_lists_every_affordable_answer(name: str) -> None:
    search = SEARCHES[name]
    assert [row["answer"] for row in answers_rows(search)] == list(answer_texts(inputs(), search))


@pytest.mark.parametrize("name", sorted(SEARCHES))
def test_the_optimum_is_the_best_score_and_the_spread_recomputes(name: str) -> None:
    search = SEARCHES[name]
    rows = answers_rows(search)
    bands = [float(b) for b in inputs().rules.value("solve.spread_bands_pct")]
    for column, key in keys_of(search):
        values = [float(row[column]) for row in rows]
        best = max(values) if mirrored(search) else min(values)
        assert key["optimum"]["objective"] == best
        assert key["optimum"]["answers"] == [r["answer"] for r in rows if float(r[column]) == best]
        measure = Range(best, key["no_action"]["objective"], mirrored(search))
        assert key["spread"] == spread(values, measure, bands)
        assert key["answers_file"] == answers_name(search, _model(search))


def _model(search: Search) -> str:
    return load_recipe(PILOT).answer_key_requests[search.first].model


def chosen(search: Search) -> list[str]:
    """The answers CI re-scores: ties, rules of thumb, the next best, a stable-hash sample."""
    rows = answers_rows(search)
    picked: dict[str, None] = {}
    for column, key in keys_of(search):
        for answer in key["optimum"]["answers"]:
            picked[answer] = None
        for rule in key["rules_of_thumb"]:
            if "answer" in rule:
                picked[rule["answer"]] = None
        order = sorted(rows, key=lambda r: float(r[column]), reverse=mirrored(search))
        rest = [r["answer"] for r in order if r["answer"] not in picked]
        for answer in rest[:NEXT_BEST]:
            picked[answer] = None
    by_hash = sorted(rows, key=lambda r: hashlib.sha256(r["answer"].encode("utf-8")).hexdigest())
    for row in by_hash[:STABLE_HASH_SAMPLE]:
        picked[row["answer"]] = None
    return list(picked)


@pytest.mark.parametrize("name", sorted(SEARCHES))
def test_chosen_answers_rescore_byte_exact_against_the_stored_scores(name: str) -> None:
    search = SEARCHES[name]
    rows = {row["answer"]: row for row in answers_rows(search)}
    columns = [column for column, _ in keys_of(search)]
    texts = chosen(search)
    scored = rescore(inputs(), search, texts)
    for text in texts:
        assert scored[text] == tuple(rows[text][c] for c in columns), text


@pytest.mark.slow
@pytest.mark.parametrize("name", sorted(SEARCHES))
def test_a_full_re_solve_reproduces_the_golden_keys(name: str) -> None:
    """The full search, every key and answers file of it byte-identical (slow)."""
    search = SEARCHES[name]
    files = solve(inputs(), only=[search.first])
    assert files
    for file_name, body in sorted(files.items()):
        assert body == (GOLDEN / file_name).read_bytes(), file_name
