from pathlib import Path

import pytest

from swm.recipe.buildability import (
    BUILT_FEATURES,
    FEATURE_ARRIVALS,
    Arrival,
    features_used,
    unbuilt_features,
)
from swm.recipe.io import load_recipe, parse_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import ErrorMechanism, MapType, Recipe

PILOT_FEATURES = {
    "map_type:spine_island",
    "terrain_character",
    "size:up_to_small",
    "layer_siting_and_links",
    "nodes_only",
    "emission",
    "source_overlap",
    "couplings",
    "couplings_hidden",
    "hazard:storm_corridor",
    "unobserved_quantities",
    "crews_and_depots",
    "tier:exact",
    "transfer_form:linear",
    "transfer_form:threshold",
    "transfer_form:step",
    "error_mechanism:parametric",
    "model:protect_condition_and_add_reserve",
    "model:strike_nodes",
    "model:sequence_repair_crews",
    "model:observe_uncertain_couplings",
    "objective:unserved_demand_hours",
    "service_weights:lifeline",
}


def resolved(text: str) -> Recipe:
    return resolve(parse_recipe("recipe_version: 1\n" + text)).recipe


def arrivals(recipe: Recipe) -> dict[str, Arrival]:
    return {status.feature: status.arrival for status in unbuilt_features(recipe)}


def test_pilot_uses_exactly_its_features_in_phases_1_to_3(pilot_path: Path) -> None:
    recipe = resolve(load_recipe(pilot_path)).recipe
    assert set(features_used(recipe)) == PILOT_FEATURES
    phases = {FEATURE_ARRIVALS[feature] for feature in PILOT_FEATURES}
    assert phases == {Arrival.PHASE_1, Arrival.PHASE_2, Arrival.PHASE_3}


def test_pilot_reports_every_feature_not_yet_built(pilot_path: Path) -> None:
    reported = arrivals(resolve(load_recipe(pilot_path)).recipe)
    assert set(reported) == PILOT_FEATURES - BUILT_FEATURES
    assert {"map_type:spine_island", "terrain_character"} <= BUILT_FEATURES


def test_every_map_type_and_mechanism_is_in_the_table() -> None:
    assert all(f"map_type:{map_type}" in FEATURE_ARRIVALS for map_type in MapType)
    assert all(f"error_mechanism:{m}" in FEATURE_ARRIVALS for m in ErrorMechanism)


@pytest.mark.parametrize(
    ("text", "feature", "arrival"),
    [
        ("terrain:\n  map_type: archipelago\n", "map_type:archipelago", Arrival.PHASE_5),
        ("terrain:\n  size_preset: huge\n", "size:larger_than_small", Arrival.PHASE_5),
        ("terrain:\n  area_km2: 2500\n", "size:larger_than_small", Arrival.PHASE_5),
        ("dynamics:\n  tier: simulation\n", "tier:simulation", Arrival.PHASE_5),
        (
            "shared_causes:\n  hazards:\n    flood_plain:\n      switched_on: true\n",
            "hazard:flood_plain",
            Arrival.PHASE_5,
        ),
        ("errors:\n  default_mechanism: process\n", "error_mechanism:process", Arrival.PHASE_6),
        ("ensemble:\n  members: 3\n", "ensemble_members", Arrival.PHASE_8),
        (
            "dynamics:\n  transfer_forms:\n    service: concave\n",
            "transfer_form:concave",
            Arrival.PHASE_5,
        ),
        (
            "answer_key_requests:\n  - model: drain_reserves\n",
            "model:drain_reserves",
            Arrival.NOT_YET_SCHEDULED,
        ),
        (
            "answer_key_requests:\n  - model: strike_nodes\n    objective: worst_single_layer\n",
            "objective:worst_single_layer",
            Arrival.NOT_YET_SCHEDULED,
        ),
    ],
)
def test_later_phase_feature_is_reported_with_its_phase(
    text: str, feature: str, arrival: Arrival
) -> None:
    assert arrivals(resolved(text))[feature] == arrival


@pytest.mark.parametrize(
    "text",
    [
        "terrain:\n  area_km2: 900\n",
        "terrain:\n  size_preset: small\n",
        "terrain:\n  size_preset: custom\n  area_km2: 1500\nlayers:\n"
        + "".join(
            f"  {layer}:\n    node_count: 17\n"
            for layer in ("power", "telecom", "water", "transport", "fuel", "healthcare")
        ),
    ],
)
def test_sizes_up_to_small_are_phase_1(text: str) -> None:
    assert FEATURE_ARRIVALS["size:up_to_small"] == Arrival.PHASE_1
    assert "size:up_to_small" in features_used(resolved(text))


def test_concave_on_the_exact_tier_is_valid_but_refused_with_a_reason() -> None:
    recipe = resolved("dynamics:\n  tier: exact\n  transfer_forms:\n    control: concave\n")
    status = next(s for s in unbuilt_features(recipe) if s.feature == "transfer_form:concave")
    assert status.arrival == Arrival.PHASE_5
    assert "simulation tier" in status.note


def test_adversarial_error_is_always_refused() -> None:
    reported = arrivals(resolved("errors:\n  default_mechanism: adversarial\n"))
    assert reported["error_mechanism:adversarial"] == Arrival.NEVER


def test_a_per_source_mechanism_overrides_the_default() -> None:
    recipe = resolved("errors:\n  sources:\n    osm_water: {mechanism: replay}\n")
    used = features_used(recipe)
    assert "error_mechanism:replay" in used
    assert "error_mechanism:parametric" in used


def test_all_layers_off_uses_no_layer_features() -> None:
    text = "layers:\n" + "".join(
        f"  {layer}:\n    state: off\n"
        for layer in ("power", "telecom", "water", "transport", "fuel", "healthcare")
    )
    used = features_used(resolved(text))
    assert "layer_siting_and_links" not in used
    assert "emission" not in used
    assert "layer_state:off" in used


def test_features_with_no_switched_off_pairs_are_not_hidden() -> None:
    pairs = "".join(
        f"  - {{supplier: {s}, consumer: {c}}}\n"
        for s in ("power", "telecom", "water", "transport", "fuel", "healthcare")
        for c in ("power", "telecom", "water", "transport", "fuel", "healthcare")
        if s != c
    )
    used = features_used(resolved("couplings:\n  two_way_pct: 0\n  switched_on:\n" + pairs))
    assert "couplings_hidden" not in used
    assert "couplings_two_way" not in used
