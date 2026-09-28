from pathlib import Path

import pytest

from swm.recipe.buildability import (
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
    "size:hand_check",
    "layer_siting_and_links",
    "nodes_only",
    "emission",
    "source_overlap",
    "couplings",
    "couplings_hidden",
    "couplings_two_way",
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
    "service_weights:healthcare_first",
}


def resolved(text: str) -> Recipe:
    return resolve(parse_recipe("recipe_version: 1\n" + text)).recipe


def arrivals(recipe: Recipe) -> dict[str, Arrival]:
    return {status.feature: status.arrival for status in unbuilt_features(recipe)}


def test_pilot_reports_exactly_its_features_in_phases_1_to_3(pilot_path: Path) -> None:
    recipe = resolve(load_recipe(pilot_path)).recipe
    reported = arrivals(recipe)
    assert set(reported) == PILOT_FEATURES
    assert set(reported.values()) == {Arrival.PHASE_1, Arrival.PHASE_2, Arrival.PHASE_3}


def test_every_map_type_and_mechanism_is_in_the_table() -> None:
    assert all(f"map_type:{map_type}" in FEATURE_ARRIVALS for map_type in MapType)
    assert all(f"error_mechanism:{m}" in FEATURE_ARRIVALS for m in ErrorMechanism)


@pytest.mark.parametrize(
    ("text", "feature", "arrival"),
    [
        ("terrain:\n  map_type: archipelago\n", "map_type:archipelago", Arrival.PHASE_5),
        ("terrain:\n  size_preset: huge\n", "size:huge", Arrival.PHASE_5),
        ("terrain:\n  area_km2: 900\n", "size:custom", Arrival.PHASE_5),
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
            Arrival.NOT_YET_SCHEDULED,
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
    used = features_used(resolved("couplings:\n  two_way: false\n  switched_on:\n" + pairs))
    assert "couplings_hidden" not in used
    assert "couplings_two_way" not in used
