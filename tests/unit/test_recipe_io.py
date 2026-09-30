from pathlib import Path

import pytest

from swm.recipe.io import (
    RecipeFormatError,
    RecipeVersionError,
    load_recipe,
    parse_recipe,
    recipe_bytes,
    recipe_sha256,
)
from swm.recipe.resolve import resolve
from swm.recipe.schema import Layer, LayerState, Recipe, Source


def resolved(text: str) -> Recipe:
    return resolve(parse_recipe(text)).recipe


def test_unknown_version_names_the_versions_this_code_reads() -> None:
    with pytest.raises(RecipeVersionError, match=r"recipe_version 3 is not supported.*1, 2"):
        parse_recipe("recipe_version: 3\n")


def test_a_version_1_recipe_loads_with_depots_read_as_crew_base() -> None:
    recipe = parse_recipe("recipe_version: 1\nunobserved:\n  crews: 3\n  depots: 4\n")
    assert recipe.recipe_version == 2
    assert (recipe.unobserved.crews, recipe.unobserved.crew_base) == (3, 4)
    assert parse_recipe("recipe_version: 1\n") == parse_recipe("recipe_version: 2\n")


def test_crew_base_under_version_1_or_depots_under_version_2_fail_clearly() -> None:
    with pytest.raises(RecipeVersionError, match="crew_base is a recipe_version 2 setting"):
        parse_recipe("recipe_version: 1\nunobserved:\n  crew_base: 1\n")
    with pytest.raises(RecipeVersionError, match=r"depots was renamed unobserved\.crew_base"):
        parse_recipe("recipe_version: 2\nunobserved:\n  depots: 1\n")


def test_missing_version_is_rejected() -> None:
    with pytest.raises(RecipeVersionError, match="does not state recipe_version"):
        parse_recipe("root_seed: 5\n")


def test_non_mapping_is_rejected() -> None:
    with pytest.raises(RecipeFormatError):
        parse_recipe("- a list\n")


def test_off_is_a_layer_state_not_a_boolean() -> None:
    recipe = parse_recipe("recipe_version: 1\nlayers:\n  water:\n    state: off\n")
    assert recipe.layers.water.state == LayerState.OFF


def test_round_trip_is_byte_identical(pilot_path: Path, tmp_path: Path) -> None:
    first = recipe_bytes(resolve(load_recipe(pilot_path)).recipe)
    rewritten = tmp_path / "again.yaml"
    rewritten.write_bytes(first)
    second = recipe_bytes(resolve(load_recipe(rewritten)).recipe)
    assert first == second
    assert b"\r" not in first


def test_resolving_twice_changes_nothing(pilot_path: Path) -> None:
    once = resolve(load_recipe(pilot_path)).recipe
    assert resolve(once).recipe == once


def test_recipe_sha256_is_over_the_canonical_bytes(pilot_path: Path) -> None:
    import hashlib

    recipe = resolve(load_recipe(pilot_path)).recipe
    assert recipe_sha256(recipe) == hashlib.sha256(recipe_bytes(recipe)).hexdigest()


def test_preset_fills_area_and_counts() -> None:
    recipe = resolved("recipe_version: 1\nterrain:\n  size_preset: small\n")
    assert recipe.terrain.area_km2 == 2000.0
    assert {recipe.layers.get(layer).node_count for layer in Layer} == {20}


def test_holding_density_scales_counts_with_the_area() -> None:
    recipe = resolved("recipe_version: 1\nterrain:\n  area_km2: 900\n")
    assert recipe.layers.power.node_count == 9


def test_holding_counts_keeps_the_preset_counts() -> None:
    text = "recipe_version: 1\nterrain:\n  area_km2: 900\n  hold_on_area_change: node_counts\n"
    assert resolved(text).layers.power.node_count == 4


def test_written_counts_win_over_the_preset() -> None:
    recipe = resolved("recipe_version: 1\nlayers:\n  water:\n    node_count: 7\n")
    assert recipe.layers.water.node_count == 7
    assert recipe.layers.power.node_count == 4


def test_every_emitted_source_gets_error_defaults_and_its_mechanism() -> None:
    recipe = resolved("recipe_version: 1\nerrors:\n  default_mechanism: replay\n")
    assert Source.OSM_WATER in recipe.errors.sources
    assert all(settings.mechanism == "replay" for settings in recipe.errors.sources.values())


def test_sources_and_couplings_are_sorted() -> None:
    text = (
        "recipe_version: 1\n"
        "layers:\n  power:\n    sources: [wri_gppd, osm_power]\n"
        "couplings:\n  switched_on:\n"
        "  - {supplier: water, consumer: power}\n"
        "  - {supplier: power, consumer: water}\n"
    )
    recipe = resolved(text)
    assert recipe.layers.power.sources == (Source.OSM_POWER, Source.WRI_GPPD)
    assert [pair.supplier for pair in recipe.couplings.switched_on] == [Layer.POWER, Layer.WATER]


def notes_for(text: str) -> tuple[str, ...]:
    return resolve(parse_recipe(text)).notes


def test_nodes_only_links_rate_is_a_note_not_an_error() -> None:
    notes = notes_for("recipe_version: 1\n")
    assert "errors.sources.osm_fuel.links_pct is ignored: fuel sources report nodes only" in notes


def test_categorical_compliance_gap_is_zeroed_with_a_note() -> None:
    text = "recipe_version: 1\nunobserved:\n  failure_mode:\n    compliance_gap_pct: 10\n"
    resolution = resolve(parse_recipe(text))
    assert resolution.recipe.unobserved.failure_mode.compliance_gap_pct == 0
    assert any(
        "failure_mode.compliance_gap_pct does not apply" in note for note in resolution.notes
    )


def test_zero_coverage_is_a_note() -> None:
    text = "recipe_version: 1\nerrors:\n  sources:\n    osm_water: {coverage_pct: 0}\n"
    note = "errors.sources.osm_water.coverage_pct is 0: the source carries nothing"
    assert note in notes_for(text)


def test_urban_density_zero_is_a_note() -> None:
    text = "recipe_version: 1\nterrain:\n  character:\n    urban_density: 0\n"
    note = "urban density 0: one minimum town placed so siting has an anchor"
    assert note in notes_for(text)


def test_healthcare_as_supplier_is_a_note() -> None:
    text = (
        "recipe_version: 1\ncouplings:\n  switched_on:\n"
        "  - {supplier: healthcare, consumer: water}\n"
    )
    assert any("pure sink" in note for note in notes_for(text))


def test_ignored_sources_and_empty_layers_are_notes() -> None:
    text = (
        "recipe_version: 1\n"
        "layers:\n  water:\n    state: hidden\n  telecom:\n    sources: []\n"
        "errors:\n  sources:\n    lng_register: {coverage_pct: 50}\n"
    )
    notes = notes_for(text)
    assert "layers.water.sources are ignored: the layer is hidden" in notes
    assert "layers.telecom is emitted but has no sources, so nothing is emitted" in notes
    assert "errors.sources.lng_register is ignored: the source is not emitted" in notes
