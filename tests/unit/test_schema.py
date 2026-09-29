import typing
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from swm.recipe.schema import (
    DEFAULT_COUPLINGS,
    EQUAL_WEIGHTS,
    LIFELINE_WEIGHTS,
    EndUseClass,
    Layer,
    LayerState,
    NodeClass,
    Recipe,
    Source,
    TransferForm,
    WeightPreset,
)


def recipe(**sections: Any) -> Recipe:
    return Recipe.model_validate(sections)


def test_every_default_validates() -> None:
    default = Recipe()
    assert Recipe.model_validate(default.model_dump()) == default


def models_in(annotation: Any) -> list[type[BaseModel]]:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]
    return [model for arg in typing.get_args(annotation) for model in models_in(arg)]


def test_every_field_says_what_it_controls() -> None:
    pending: list[type[BaseModel]] = [Recipe]
    seen: set[type[BaseModel]] = set()
    undescribed = []
    while pending:
        model = pending.pop()
        if model in seen:
            continue
        seen.add(model)
        for name, field in model.model_fields.items():
            if not field.description:
                undescribed.append(f"{model.__name__}.{name}")
            pending.extend(models_in(field.annotation))
    assert len(seen) > 20
    assert undescribed == []


def test_defaults_follow_the_mockup_and_rulings() -> None:
    default = Recipe()
    assert len(default.couplings.switched_on) == 21
    assert all(pair.supplier != Layer.HEALTHCARE for pair in default.couplings.switched_on)
    assert default.layers.fuel.nodes_only
    assert default.layers.healthcare.nodes_only
    assert default.dynamics.transfer_forms.logistic == TransferForm.THRESHOLD
    assert default.shared_causes.hazards.storm_corridor.switched_on
    assert default.answer_key_requests[0].window_h == 72


def test_default_couplings_are_the_21_modeled() -> None:
    assert len(set(DEFAULT_COUPLINGS)) == 21
    assert not any(supplier == Layer.HEALTHCARE for supplier, _ in DEFAULT_COUPLINGS)


@pytest.mark.parametrize(
    ("sections", "field"),
    [
        ({"root_seed": -1}, "root_seed"),
        ({"root_seed": 2**64}, "root_seed"),
        ({"terrain": {"area_km2": 0.5}}, "area_km2"),
        ({"terrain": {"character": {"outlying_islands": 9}}}, "outlying_islands"),
        ({"layers": {"power": {"node_count": 0}}}, "node_count"),
        ({"layers": {"power": {"links_per_node": 4.5}}}, "links_per_node"),
        ({"couplings": {"supplier_not_nearest_pct": 101}}, "supplier_not_nearest_pct"),
        ({"shared_causes": {"hazards": {"flood_plain": {"correlation_km": 4}}}}, "correlation_km"),
        ({"shared_causes": {"hazards": {"flood_plain": {"severity": 101}}}}, "severity"),
        ({"unobserved": {"reserves": {"compliance_gap_pct": -51}}}, "compliance_gap_pct"),
        ({"unobserved": {"crews": 0}}, "crews"),
        ({"errors": {"sources": {"osm_power": {"missing_pct": 101}}}}, "missing_pct"),
        ({"answer_key_requests": [{"model": "strike_nodes", "window_h": 5}]}, "window_h"),
        ({"answer_key_requests": [{"model": "strike_nodes", "strikes_k": 0}]}, "strikes_k"),
    ],
)
def test_out_of_range_values_are_rejected(sections: dict[str, Any], field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        recipe(**sections)


def test_error_rates_run_to_100() -> None:
    accepted = recipe(errors={"sources": {"osm_power": {"phantom_pct": 100}}})
    assert accepted.errors.sources[Source.OSM_POWER].phantom_pct == 100


def test_feed_mix_not_totalling_100_is_rejected() -> None:
    with pytest.raises(ValidationError, match="feed_mix shares must total exactly 100, got 90"):
        recipe(couplings={"feed_mix": {"single_feed_pct": 50}})


def test_source_on_the_wrong_layer_is_rejected() -> None:
    with pytest.raises(ValidationError, match="osm_health is not a power source"):
        recipe(layers={"power": {"sources": ["osm_health"]}})


def test_source_listed_twice_is_rejected() -> None:
    with pytest.raises(ValidationError, match="listed twice"):
        recipe(layers={"water": {"sources": ["osm_water", "osm_water"]}})


def test_coupling_needs_two_layers() -> None:
    with pytest.raises(ValidationError, match="needs two layers"):
        recipe(couplings={"switched_on": [{"supplier": "water", "consumer": "water"}]})


def test_coupling_pair_listed_twice_is_rejected() -> None:
    pair = {"supplier": "water", "consumer": "power"}
    with pytest.raises(ValidationError, match="listed twice"):
        recipe(couplings={"switched_on": [pair, pair]})


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="redundancy"):
        recipe(dynamics={"redundancy": 40})


def test_partial_layer_keeps_its_own_defaults() -> None:
    fuel = recipe(layers={"fuel": {"state": "hidden"}}).layers.fuel
    assert fuel.state == LayerState.HIDDEN
    assert fuel.nodes_only
    assert fuel.links_per_node == 1.4
    assert fuel.sources == (Source.OSM_FUEL,)


def test_partial_hazard_keeps_its_own_defaults() -> None:
    seismic = recipe(shared_causes={"hazards": {"seismic_zone": {"switched_on": True}}})
    assert seismic.shared_causes.hazards.seismic_zone.correlation_km == 60


def test_model_must_match_its_member_class() -> None:
    with pytest.raises(ValidationError, match="strike_nodes belongs to offensive"):
        recipe(answer_key_requests=[{"model": "strike_nodes", "member_class": "defensive"}])


def test_unknown_model_is_rejected() -> None:
    with pytest.raises(ValidationError, match="model"):
        recipe(answer_key_requests=[{"model": "flood_the_basin"}])


def test_restorative_model_takes_no_budget() -> None:
    with pytest.raises(ValidationError, match="budget_cost_units"):
        recipe(answer_key_requests=[{"model": "sequence_repair_crews", "budget_cost_units": 2}])


def test_custom_weights_need_every_node_class() -> None:
    with pytest.raises(ValidationError, match="custom_weights is missing"):
        recipe(
            answer_key_requests=[
                {
                    "model": "strike_nodes",
                    "service_weights": "custom",
                    "custom_weights": {"clinic": 1},
                }
            ]
        )


def test_custom_weights_only_with_custom_preset() -> None:
    with pytest.raises(ValidationError, match="only with service_weights: custom"):
        recipe(answer_key_requests=[{"model": "strike_nodes", "custom_weights": {"clinic": 1}}])


def test_complete_custom_weights_are_accepted() -> None:
    weights = {end_use.value: 1.0 for end_use in EndUseClass}
    accepted = recipe(
        answer_key_requests=[
            {"model": "strike_nodes", "service_weights": "custom", "custom_weights": weights}
        ]
    )
    assert accepted.answer_key_requests[0].custom_weights is not None


def test_custom_weight_out_of_range_is_rejected() -> None:
    weights = {end_use.value: 1.0 for end_use in EndUseClass} | {"clinic": 101.0}
    with pytest.raises(ValidationError, match="custom_weights"):
        recipe(
            answer_key_requests=[
                {"model": "strike_nodes", "service_weights": "custom", "custom_weights": weights}
            ]
        )


def test_only_end_use_classes_take_weights() -> None:
    weights = {end_use.value: 1.0 for end_use in EndUseClass} | {"generation": 1.0}
    with pytest.raises(ValidationError, match="generation"):
        recipe(
            answer_key_requests=[
                {"model": "strike_nodes", "service_weights": "custom", "custom_weights": weights}
            ]
        )


def test_weight_presets_follow_the_spec() -> None:
    assert set(EndUseClass) <= set(NodeClass)
    assert set(LIFELINE_WEIGHTS) == set(EQUAL_WEIGHTS) == set(EndUseClass)
    assert LIFELINE_WEIGHTS[EndUseClass.TERTIARY] == 10
    assert LIFELINE_WEIGHTS[EndUseClass.REGIONAL] == LIFELINE_WEIGHTS[EndUseClass.SEAPORT] == 7
    assert LIFELINE_WEIGHTS[EndUseClass.MAST] == 1
    assert set(EQUAL_WEIGHTS.values()) == {1.0}
    assert Recipe().answer_key_requests[0].service_weights == WeightPreset.LIFELINE


def test_heterogeneity_is_a_percentage_everywhere() -> None:
    reserves = recipe(unobserved={"reserves": {"heterogeneity_pct": 80}}).unobserved.reserves
    assert reserves.heterogeneity_pct == 80
    with pytest.raises(ValidationError, match="heterogeneity"):
        recipe(unobserved={"reserves": {"heterogeneity": 80}})


def test_snapshot_age_runs_to_30_years() -> None:
    accepted = recipe(errors={"sources": {"osm_power": {"snapshot_age_y": 30}}})
    assert accepted.errors.sources[Source.OSM_POWER].snapshot_age_y == 30
    with pytest.raises(ValidationError, match="snapshot_age_y"):
        recipe(errors={"sources": {"osm_power": {"snapshot_age_y": 31}}})


def test_custom_size_needs_area_and_every_count() -> None:
    with pytest.raises(ValidationError, match=r"missing: terrain.area_km2, power"):
        recipe(
            terrain={"size_preset": "custom"},
            layers={layer.value: {"node_count": 5} for layer in Layer if layer != Layer.POWER},
        )


# --- Couplings settings (Work Order 4, A3) --------------------------------------------------


def test_couplings_settings_have_their_defaults() -> None:
    couplings = Recipe().couplings
    assert couplings.two_way_pct == 50
    assert couplings.distribution_voltage_kv == 11.4
    share = couplings.public_telecom_share
    assert (share.generation_pct, share.transmission_pct) == (20, 20)
    assert (share.distribution_pct, share.water_pct, share.pipelines_pct) == (50, 50, 50)


@pytest.mark.parametrize(
    ("couplings", "field"),
    [
        ({"two_way_pct": 101}, "two_way_pct"),
        ({"distribution_voltage_kv": 13.2}, "distribution_voltage_kv"),
        ({"public_telecom_share": {"water_pct": 120}}, "water_pct"),
    ],
)
def test_couplings_settings_are_bounded(couplings: dict[str, Any], field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        recipe(couplings=couplings)


def test_the_old_two_way_switch_is_gone() -> None:
    with pytest.raises(ValidationError, match="two_way"):
        recipe(couplings={"two_way": True})


def test_the_pilot_switches_on_its_seven_couplings(pilot_path: Any) -> None:
    from swm.recipe.io import load_recipe

    couplings = load_recipe(pilot_path).couplings
    pairs = {(p.supplier.value, p.consumer.value) for p in couplings.switched_on}
    assert pairs == {
        ("fuel", "power"),
        ("power", "telecom"),
        ("telecom", "power"),
        ("power", "water"),
        ("water", "healthcare"),
        ("power", "healthcare"),
        ("transport", "fuel"),
    }
    assert couplings.switched_off_handling == "generate_and_hide"
    assert couplings.density == 0
    assert couplings.two_way_pct == 0
