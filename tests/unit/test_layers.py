from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from layers_helpers import (
    build_world,
    cell,
    feasible_links_per_node,
    is_connected,
    links_of,
    nodes_of,
    sited_on_bad_ground,
)
from swm import rng
from swm.recipe.schema import SOURCE_SCOPES, Layer, LayerState, NodeClass, Recipe
from swm.stages import layers as layers_stage
from swm.stages.layers import (
    TELECOM_OPERATORS,
    TREE_LAYERS,
    LayersResult,
    class_counts,
    layer_rules,
    link_table,
    node_table,
)
from swm.stages.terrain import GRID_CELLS, TerrainResult, array_hashes

ATTRIBUTE_RANGES = layer_rules().attribute_ranges
COMPOSITION = layer_rules().composition
SITING = layer_rules().siting

PILOT_COMPOSITION = {
    Layer.POWER: {"generation": 1, "transmission_substation": 1, "distribution_substation": 2},
    Layer.TELECOM: {"exchange": 1, "mast": 3},
    Layer.WATER: {"reservoir": 1, "treatment": 1, "pumping": 1, "storage": 1},
    Layer.TRANSPORT: {"seaport": 1, "airport": 1, "freight_yard": 1, "bridge": 1},
    Layer.FUEL: {"import_terminal": 1, "tank_farm": 1, "depot": 2},
    Layer.HEALTHCARE: {"tertiary": 1, "regional": 1, "clinic": 1, "blood_bank": 1},
}

PILOT_SECTIONS: dict[str, Any] = {
    "layers": {
        "dual_membership": False,
        "power": {"sources": ["osm_power", "wri_gppd"]},
        "transport": {"sources": ["osm_transport", "ourairports"]},
        "healthcare": {"sources": ["osm_health", "facility_register"]},
    }
}


@pytest.fixture(scope="module")
def pilot() -> tuple[Recipe, TerrainResult, LayersResult]:
    return build_world(**PILOT_SECTIONS)


def notes(result: LayersResult) -> list[str]:
    return [f"{s.layer}: {note}" for s in result.statistics for note in s.notes]


# --- Composition ----------------------------------------------------------------------------


def test_pilot_composition_is_the_ruled_one(pilot: Any) -> None:
    _, _, result = pilot
    for layer, expected in PILOT_COMPOSITION.items():
        stats = next(s for s in result.statistics if s.layer == layer)
        assert {k: v for k, v in stats.class_counts.items() if v} == expected


@pytest.mark.parametrize("layer", list(Layer))
@pytest.mark.parametrize("count", [1, 2, 3, 4, 7, 12, 20])
def test_class_counts_total_and_keep_the_backbone(layer: Layer, count: int) -> None:
    counts = class_counts(layer, count)
    assert sum(counts.values()) == count
    backbone = [share.node_class for share in COMPOSITION[layer] if share.backbone]
    for node_class in backbone[:count]:
        assert counts[node_class] >= 1


def test_freight_yard_is_an_end_use_and_the_bridge_is_not() -> None:
    from swm.recipe.schema import LIFELINE_WEIGHTS, EndUseClass

    assert LIFELINE_WEIGHTS[EndUseClass.FREIGHT_YARD] == 4
    assert "bridge" not in {e.value for e in EndUseClass}


# --- Siting ---------------------------------------------------------------------------------


def test_no_node_on_sea_river_or_wetland(pilot: Any) -> None:
    _, terrain, result = pilot
    assert sited_on_bad_ground(terrain, result) == []
    assert len({cell(n) for n in result.nodes}) == len(result.nodes)


def test_seaport_and_import_terminal_are_on_the_coast(pilot: Any) -> None:
    _, terrain, result = pilot
    land = np.asarray(terrain.land)
    padded = np.pad(land, 1)
    for node in result.nodes:
        if node.node_class in (NodeClass.SEAPORT, NodeClass.IMPORT_TERMINAL):
            window = padded[node.row : node.row + 3, node.column : node.column + 3]
            assert not window.all(), node.node_id


def test_the_bridge_sits_on_a_river(pilot: Any) -> None:
    _, terrain, result = pilot
    bridge = next(n for n in result.nodes if n.node_class == NodeClass.BRIDGE)
    assert terrain.river[bridge.row, bridge.column]


def test_the_airport_has_its_flat_run(pilot: Any) -> None:
    _, terrain, result = pilot
    airport = next(n for n in result.nodes if n.node_class == NodeClass.AIRPORT)
    assert airport.runway is not None
    from swm.coordinates import domain_origin_m

    (x0, y0), (x1, y1) = airport.runway
    length_m = float(np.hypot(x1 - x0, y1 - y0))
    assert length_m >= SITING.runway_km * 1000
    west, south = domain_origin_m(terrain.grid)
    cell_m = terrain.grid.cell_size_m

    def to_cell(x: float, y: float) -> tuple[int, int]:
        return round(GRID_CELLS - (y - south) / cell_m - 0.5), round((x - west) / cell_m - 0.5)

    (r0, c0), (r1, c1) = to_cell(x0, y0), to_cell(x1, y1)
    steps = max(abs(r1 - r0), abs(c1 - c0))
    dr, dc = int(np.sign(r1 - r0)), int(np.sign(c1 - c0))
    heights = [terrain.elevation_dm[r0 + k * dr, c0 + k * dc] / 10 for k in range(steps + 1)]
    assert max(heights) - min(heights) <= SITING.runway_grade * length_m + 1e-6
    assert all(terrain.land[r0 + k * dr, c0 + k * dc] for k in range(steps + 1))


def test_exchange_and_tertiary_hospital_are_in_the_largest_city(pilot: Any) -> None:
    _, terrain, result = pilot
    largest = max(terrain.cities, key=lambda c: (c.cell_count, -c.city_id))
    for node in result.nodes:
        if node.node_class in (NodeClass.EXCHANGE, NodeClass.TERTIARY):
            assert terrain.urban_id[node.row, node.column] == largest.city_id


def test_the_reservoir_is_on_a_river_above_the_treatment_plant(pilot: Any) -> None:
    _, terrain, result = pilot
    reservoir = next(n for n in result.nodes if n.node_class == NodeClass.RESERVOIR)
    treatment = next(n for n in result.nodes if n.node_class == NodeClass.TREATMENT)
    window = terrain.river[
        reservoir.row - 1 : reservoir.row + 2, reservoir.column - 1 : reservoir.column + 2
    ]
    assert window.any()
    assert (
        terrain.elevation_dm[reservoir.row, reservoir.column]
        > terrain.elevation_dm[treatment.row, treatment.column]
    )


# --- Links ----------------------------------------------------------------------------------


def test_every_layer_is_one_component_with_its_signature(pilot: Any) -> None:
    _, _, result = pilot
    for layer in Layer:
        nodes = nodes_of(result, layer)
        links = links_of(result, layer)
        assert is_connected(nodes, links), layer
        if layer in TREE_LAYERS:
            assert len(links) == len(nodes) - 1, layer
    assert len(links_of(result, Layer.POWER)) > len(nodes_of(result, Layer.POWER)) - 1


def test_realised_links_per_node_is_near_the_recipe(pilot: Any) -> None:
    recipe, _, result = pilot
    for stats in result.statistics:
        wanted = recipe.layers.get(stats.layer).links_per_node
        count = sum(stats.class_counts.values())
        expected = feasible_links_per_node(wanted, count, stats.layer in TREE_LAYERS)
        assert abs(stats.mean_links_per_node - expected) <= 0.5, stats.layer


def test_roads_never_cross_the_sea_and_other_links_say_when_they_do(pilot: Any) -> None:
    _, _, result = pilot
    for link in result.links:
        if link.layer == Layer.TRANSPORT:
            assert not link.crosses_sea
    flagged = [link for link in result.links if link.crosses_sea]
    assert all(link.layer != Layer.TRANSPORT for link in flagged)


def test_links_record_length_and_river_crossings(pilot: Any) -> None:
    _, _, result = pilot
    for link in result.links:
        assert link.length_km > 0
        assert link.river_crossings >= 0
        assert len(link.points) >= 2


def test_tree_layers_keep_their_signature_with_a_note() -> None:
    _, _, result = build_world(layers={"water": {"links_per_node": 3.0}})
    water = links_of(result, Layer.WATER)
    assert len(water) == len(nodes_of(result, Layer.WATER)) - 1
    assert any("water: links per node" in note and "tree" in note for note in notes(result))


def test_a_small_layer_notes_it_cannot_hold_more_links() -> None:
    _, _, result = build_world(layers={"healthcare": {"links_per_node": 4.0}})
    assert any("cannot hold more links" in note for note in notes(result))


# --- States, streams and sources ------------------------------------------------------------


def test_hidden_layer_is_generated_in_full_and_off_layer_is_absent() -> None:
    _, _, result = build_world(layers={"water": {"state": "hidden"}, "fuel": {"state": "off"}})
    assert len(nodes_of(result, Layer.WATER)) == 4
    assert result.states[Layer.WATER] == LayerState.HIDDEN
    assert nodes_of(result, Layer.FUEL) == []
    assert all(s.layer != Layer.FUEL for s in result.statistics)


def test_nodes_only_changes_nothing_here() -> None:
    _, _, plain = build_world(layers={"power": {"nodes_only": False}})
    _, _, flagged = build_world(layers={"power": {"nodes_only": True}})
    assert node_table(plain) == node_table(flagged)
    assert link_table(plain) == link_table(flagged)


def test_only_layer_streams_are_drawn(monkeypatch: pytest.MonkeyPatch) -> None:
    from swm.recipe.resolve import resolve
    from swm.stages.layers import build_layers, layers_streams
    from swm.stages.terrain import build_terrain, terrain_streams

    recipe = resolve(Recipe()).recipe
    terrain = build_terrain(recipe.terrain, terrain_streams(recipe.root_seed, 0))
    requested: list[str] = []
    original: Callable[..., np.random.Generator] = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> np.random.Generator:
        requested.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed))
    assert requested
    assert all(path.startswith("layers/") for path in requested)


def test_the_terrain_does_not_depend_on_any_layer_setting() -> None:
    _, plain, _ = build_world()
    _, changed, _ = build_world(
        layers={"power": {"node_count": 9, "links_per_node": 3.0}, "water": {"state": "off"}}
    )
    assert array_hashes(plain) == array_hashes(changed)


def test_classes_no_switched_on_source_covers_are_reported() -> None:
    _, _, result = build_world(layers={"transport": {"sources": ["ourairports"]}})
    transport = next(s for s in result.statistics if s.layer == Layer.TRANSPORT)
    assert set(transport.classes_without_source) == {"seaport", "freight_yard", "bridge"}


def test_every_source_scope_stays_in_its_layer() -> None:
    from swm.recipe.resolve import layer_of
    from swm.recipe.schema import LAYER_NODE_CLASSES

    for source, scope in SOURCE_SCOPES.items():
        assert set(scope.classes) <= set(LAYER_NODE_CLASSES[layer_of(source)]), source
        assert scope.note


# --- Rulings on relaxed rules (decision 0006) ------------------------------------------------


def test_a_mountainous_river_free_island_builds_with_its_notes() -> None:
    _, terrain, result = build_world(
        terrain={"character": {"mountainous": 100, "river_density": 0}}
    )
    assert not terrain.river.any()
    text = " | ".join(notes(result))
    assert "reservoir: on a river in the uplands could not be met" in text
    assert "viaduct" in text
    assert sum(1 for n in result.nodes if n.node_class == NodeClass.BRIDGE) == 1


def test_a_one_city_island_still_gets_its_bridge() -> None:
    _, terrain, result = build_world(terrain={"urban_pattern": "one_dominant_city"})
    assert len(terrain.cities) == 1
    bridge = next(n for n in result.nodes if n.node_class == NodeClass.BRIDGE)
    assert terrain.river[bridge.row, bridge.column]


def test_dual_membership_makes_one_reservoir_a_hydro_dam() -> None:
    _, _, result = build_world(layers={"dual_membership": True})
    reservoir = next(n for n in result.nodes if n.node_class == NodeClass.RESERVOIR)
    generation = next(n for n in result.nodes if n.node_class == NodeClass.GENERATION)
    assert (generation.row, generation.column) == (reservoir.row, reservoir.column)
    assert dict(generation.attributes)["fuel_type"] == "hydro"


def test_an_airport_far_from_every_city_is_noted() -> None:
    _, _, result = build_world(terrain={"character": {"urban_density": 0}})
    assert any("airport:" in note for note in notes(result))


def test_a_class_with_no_eligible_land_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    original = layers_stage._Ground.from_terrain

    def no_land(terrain: TerrainResult, rules: Any) -> Any:
        ground = original(terrain, rules)
        ground.buildable = np.zeros_like(ground.buildable)
        return ground

    monkeypatch.setattr(layers_stage._Ground, "from_terrain", staticmethod(no_land))
    with pytest.raises(ValueError, match="no eligible land cell for transport seaport"):
        build_world()


# --- Attributes and identifiers -------------------------------------------------------------


def test_attributes_are_in_range_and_in_their_code_lists(pilot: Any) -> None:
    _, _, result = pilot
    for node in result.nodes:
        attributes = dict(node.attributes)
        assert attributes["status"] == "operational"
        sized_to_load = (NodeClass.GENERATION, NodeClass.TRANSMISSION_SUBSTATION)
        for name, (low, high) in ATTRIBUTE_RANGES.get(node.node_class, {}).items():
            if node.node_class in sized_to_load:
                continue  # sized to the load (decision 0007); tested below
            assert low <= float(attributes[name]) <= high, (node.node_id, name)
        if node.node_class == NodeClass.TRANSMISSION_SUBSTATION:
            assert attributes["voltage_kv"] in (345.0, 161.0, 69.0)
        if node.node_class == NodeClass.DISTRIBUTION_SUBSTATION:
            assert attributes["voltage_kv"] in (22.8, 11.4)
        if node.node_class == NodeClass.AIRPORT:
            assert attributes["size_class"] in ("small_airport", "medium_airport", "large_airport")
        if node.node_class == NodeClass.SEAPORT:
            assert attributes["size_class"] in ("V", "S", "M", "L")
        if node.node_class == NodeClass.BRIDGE:
            assert attributes["deck_class"] == "road"
        if node.layer == Layer.TELECOM:
            assert attributes["operator"] in TELECOM_OPERATORS
        else:
            assert "operator" not in attributes


def test_identifiers_are_synthetic_and_stable(pilot: Any) -> None:
    _, _, result = pilot
    ids = [n.node_id for n in result.nodes] + [link.link_id for link in result.links]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("SWM-") for i in ids)
    assert result.nodes[0].node_id == "SWM-POW-0001"


def test_same_recipe_gives_the_same_tables(pilot: Any) -> None:
    _, _, again = build_world(**PILOT_SECTIONS)
    assert node_table(again) == node_table(pilot[2])
    assert link_table(again) == link_table(pilot[2])


def test_nodes_carry_projected_and_geographic_coordinates(pilot: Any) -> None:
    _, terrain, result = pilot
    from swm.coordinates import cell_centre_m, to_lonlat

    for node in result.nodes:
        assert (node.x_m, node.y_m) == cell_centre_m(node.row, node.column, terrain.grid)
        assert (node.longitude, node.latitude) == to_lonlat(node.x_m, node.y_m)
    assert GRID_CELLS == 256


# --- Subtype attributes and power sizing (Work Order 4, Parts B and C) -----------------------


def test_subtype_attributes_are_drawn_within_their_values(pilot: Any) -> None:
    from swm.recipe.dependencies import SUBTYPE_VALUES

    _, _, result = pilot
    for node in result.nodes:
        subtype = dict(node.subtype)
        domains = SUBTYPE_VALUES.get(node.node_class, {})
        expected = set(domains)
        if subtype.get("fuel_kind") == "hydro":
            expected.discard("makeup_water")
        assert set(subtype) == expected, node.node_id
        for name, value in subtype.items():
            assert value in domains[name], (node.node_id, name)


def test_subtype_attributes_are_not_observed_attributes(pilot: Any) -> None:
    from swm.recipe.dependencies import SUBTYPE_VALUES

    _, _, result = pilot
    names = {name for domains in SUBTYPE_VALUES.values() for name in domains}
    for node in result.nodes:
        assert not names & {name for name, _ in node.attributes}, node.node_id


def test_pilot_generation_burns_lng_from_an_lng_terminal(pilot: Any) -> None:
    _, _, result = pilot
    plant = next(n for n in result.nodes if n.node_class == NodeClass.GENERATION)
    terminal = next(n for n in result.nodes if n.node_class == NodeClass.IMPORT_TERMINAL)
    assert dict(plant.subtype)["fuel_kind"] == "lng"
    assert dict(plant.attributes)["fuel_type"] == "gas"
    assert dict(terminal.subtype)["product"] == "lng"


def test_the_hydro_dam_is_hydro_in_truth_and_in_its_sources() -> None:
    _, _, result = build_world(layers={"dual_membership": True})
    dam = next(n for n in result.nodes if n.node_class == NodeClass.GENERATION)
    assert dict(dam.subtype)["fuel_kind"] == "hydro"
    assert dict(dam.attributes)["fuel_type"] == "hydro"


def test_the_largest_airport_is_towered_and_pipeline_fed() -> None:
    _, terrain, result = build_world(layers={"transport": {"node_count": 20}})
    airports = [n for n in result.nodes if n.node_class == NodeClass.AIRPORT]
    assert len(airports) >= 2
    sizes = {c.city_id: c.cell_count for c in terrain.cities}
    largest = max(airports, key=lambda n: (sizes[n.city_id], -airports.index(n)))
    assert dict(largest.subtype) == {"towered": True, "fuel_receipt": "pipeline"}


def test_data_centres_cool_by_evaporation() -> None:
    _, _, result = build_world(layers={"telecom": {"node_count": 20}})
    centres = [n for n in result.nodes if n.node_class == NodeClass.DATA_CENTRE]
    assert centres
    assert all(dict(n.subtype)["cooling"] == "evaporative" for n in centres)


def test_generation_is_served_by_an_import_terminal_or_bulk_storage() -> None:
    for seed in range(4):
        _, _, result = build_world(
            root_seed=seed,
            layers={"power": {"node_count": 20}, "fuel": {"node_count": 7}},
        )
        products = {
            dict(n.subtype)["product"]
            for n in result.nodes
            if n.node_class == NodeClass.IMPORT_TERMINAL
        }
        bulk = any(n.node_class in (NodeClass.TANK_FARM, NodeClass.REFINERY) for n in result.nodes)
        for plant in (n for n in result.nodes if n.node_class == NodeClass.GENERATION):
            kind = dict(plant.subtype)["fuel_kind"]
            if kind in ("lng", "coal"):
                assert kind in products, (seed, plant.node_id)
            if kind == "oil":
                assert bulk


def test_the_layers_stage_leaves_power_at_its_drawn_size(pilot: Any) -> None:
    # Power is sized to load by the requirements stage (decision 0010).
    _, _, result = pilot
    plant = next(n for n in result.nodes if n.node_class == NodeClass.GENERATION)
    low, high = ATTRIBUTE_RANGES[NodeClass.GENERATION]["capacity_mw"]
    assert low <= float(dict(plant.attributes)["capacity_mw"]) <= high


def test_ports_and_airports_are_sized_by_the_city_they_serve(pilot: Any) -> None:
    _, _, result = pilot
    classes = {
        n.node_class: dict(n.attributes).get("size_class")
        for n in result.nodes
        if n.node_class in (NodeClass.SEAPORT, NodeClass.AIRPORT)
    }
    assert classes[NodeClass.SEAPORT] == "S"
    assert classes[NodeClass.AIRPORT] == "small_airport"
