"""Changing any error setting, or the error streams' seed, moves nothing the world contains.

Error settings shape only what a source reports. No stage output (terrain through scenarios),
no reference run and no truth-manifest value other than the recorded settings may move when
they change (Work Order 9, C1; CLAUDE.md §7: changing the error seed never moves terrain or
infrastructure).
"""

import functools
import hashlib
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from swm import rng
from swm.cli import _built, _engine, _observed, _rules_stamp
from swm.dynamics.engine import simulate
from swm.dynamics.output import crew_rows, run_record, state_rows, stock_rows
from swm.dynamics.records import RunRequest
from swm.emit.sources import emit_sources
from swm.manifest.truth import TruthInputs, truth_manifest
from swm.recipe.io import load_recipe
from swm.recipe.resolve import Resolution, resolve
from swm.recipe.schema import RECORDED_NOT_APPLIED, ErrorMechanism, Recipe, Source

PILOT = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"
ERRORS_PREFIX = "errors/"


def pilot() -> Recipe:
    return load_recipe(PILOT)


def pilot_sources() -> tuple[Source, ...]:
    return tuple(sorted(resolve(pilot()).recipe.errors.sources))


percent = st.integers(min_value=0, max_value=100)
source_errors = st.fixed_dictionaries(
    {
        "coverage_pct": percent,
        "snapshot_age_y": st.integers(min_value=0, max_value=30),
        "phantom_pct": percent,
        "missing_pct": percent,
        "merged_pct": percent,
        "location_pct": percent,
        "attributes_pct": percent,
        "links_pct": percent,
        "labels_pct": percent,
    },
    optional={"mechanism": st.sampled_from(list(ErrorMechanism))},
)
error_section = st.fixed_dictionaries(
    {
        "default_mechanism": st.sampled_from(list(ErrorMechanism)),
        "sources": st.dictionaries(st.sampled_from(pilot_sources()), source_errors),
    }
)


def with_errors(errors: dict[str, Any]) -> Resolution:
    data = pilot().model_dump(mode="json")
    data["errors"] = errors
    return resolve(Recipe.model_validate(data))


def fingerprint(resolution: Resolution) -> tuple[str, list[bytes], dict[str, object]]:
    """The stage outputs' hash, every reference run's rows, and the truth manifest."""
    built = _built(resolution)
    stages = hashlib.sha256(pickle.dumps(built)).hexdigest()
    engine = _engine(resolution, built)
    runs = []
    for index, damage in enumerate(engine.damage):
        run = simulate(engine.world, RunRequest(damage, scenario=index))
        rows = (run_record(run, _rules_stamp(resolution)), state_rows(run), stock_rows(run),
                crew_rows(run))  # fmt: skip
        runs.append(yaml.safe_dump(rows, sort_keys=True).encode("utf-8"))
    observed = _observed(resolution, built)
    recipe = resolution.recipe
    manifest = truth_manifest(TruthInputs(
        recipe, built.rules, built.requirements.layers, built.requirements, built.couplings,
        built.strength, built.buffers, built.crews, built.repair, observed,
        emit_sources(observed), rng.stream_record(recipe.root_seed, recipe.terrain.terrain_seed),
    ))  # fmt: skip
    return stages, runs, without_recorded_settings(manifest)


def without_recorded_settings(manifest: dict[str, object]) -> dict[str, object]:
    """The manifest less the one value C1 lets move: the recorded settings' declaration."""
    departures = manifest["declared_departures"]
    assert isinstance(departures, list)
    notice = RECORDED_NOT_APPLIED[0].upper() + RECORDED_NOT_APPLIED[1:]
    kept = [line for line in departures if not str(line).startswith(notice)]
    return {**manifest, "declared_departures": kept}


@functools.cache
def pilot_fingerprint() -> tuple[str, list[bytes], dict[str, object]]:
    """The pilot as built, with its own error settings and every stream unpatched."""
    return fingerprint(resolve(pilot()))


@settings(max_examples=6, deadline=None)
@given(errors=error_section, error_seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_error_settings_and_the_error_seed_move_nothing_that_exists(
    errors: dict[str, Any], error_seed: int
) -> None:
    pilot_stages, pilot_runs, pilot_manifest = pilot_fingerprint()
    with pytest.MonkeyPatch.context() as patch:
        reseed_error_streams(patch, error_seed)
        stages, runs, manifest = fingerprint(with_errors(errors))
    assert stages == pilot_stages
    assert len(runs) == 8
    assert runs == pilot_runs
    assert manifest == pilot_manifest


def reseed_error_streams(monkeypatch: pytest.MonkeyPatch, error_seed: int) -> None:
    """Give every error stream a different seed, leaving every other stream as it is."""
    stream, element_stream = rng.stream, rng.element_stream

    def reseeded_stream(root_seed: int, path: str, *rest: Any) -> np.random.Generator:
        return stream(error_seed if path.startswith(ERRORS_PREFIX) else root_seed, path, *rest)

    def reseeded_element(root_seed: int, path: str, element_id: str) -> np.random.Generator:
        seed = error_seed if path.startswith(ERRORS_PREFIX) else root_seed
        return element_stream(seed, path, element_id)

    monkeypatch.setattr(rng, "stream", reseeded_stream)
    monkeypatch.setattr(rng, "element_stream", reseeded_element)
