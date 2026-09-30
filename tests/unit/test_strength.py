import math
from typing import Any

import pytest

from buffers_helpers import strength_of
from couplings_helpers import World, couple, rich_world
from layers_helpers import build_world
from swm.checks.undisturbed import undisturbed_supply_check
from swm.recipe.schema import Layer

SHORT = {"layers.attributes.distribution_substation": {"capacity_mva": [0.0, 0.0]}}
"""Distribution substations of no capacity: every consumer they feed is short."""


@pytest.fixture(scope="module")
def rich() -> World:
    return rich_world()


@pytest.fixture(scope="module")
def strength(rich: World) -> Any:
    return strength_of(rich)


def test_kappa_lies_in_0_to_1_and_headroom_is_recorded(strength: Any) -> None:
    assert strength.edges
    for edge in strength.edges:
        assert 0.0 <= edge.kappa <= 1.0
        if edge.headroom is not None:
            assert edge.kappa == pytest.approx(min(1.0, edge.headroom))
            assert edge.available == pytest.approx(edge.headroom * edge.requirement)


def test_a_telecom_edges_kappa_is_its_public_share(rich: World, strength: Any) -> None:
    edges = {e.edge_id: e for e in couple(rich).edges}
    for record in strength.edges:
        edge = edges[record.edge_id]
        if edge.supplier_layer == Layer.TELECOM:
            share = edge.public_share_pct
            assert record.kappa == pytest.approx(1.0 if share is None else share / 100)
        if edge.supplier_layer == Layer.TRANSPORT:
            assert record.kappa == 1.0


def test_capacity_is_shared_pro_rata(rich: World, strength: Any) -> None:
    edges = {e.edge_id: e for e in couple(rich).edges}
    by_supplier: dict[str, list[Any]] = {}
    for record in strength.edges:
        edge = edges[record.edge_id]
        if record.requirement is not None and edge.role == "primary_supply":
            by_supplier.setdefault(edge.supplier_id, []).append(record)
    assert by_supplier
    for records in by_supplier.values():
        headrooms = {round(r.headroom, 9) for r in records if not math.isinf(r.headroom)}
        assert len(headrooms) <= 1  # every consumer of a supplier gets the same share


def test_the_undisturbed_supply_check_passes_on_the_rich_world(strength: Any) -> None:
    result = undisturbed_supply_check(strength)
    assert result.passed, result.report()
    assert result.report() == "undisturbed supply: every consumer is fully supplied\n"


def test_the_check_fails_on_a_short_world_and_names_who_is_short() -> None:
    from swm.recipe.resolve import resolve
    from swm.recipe.schema import Recipe
    from swm.rules.registry import load_registry
    from swm.stages.layers import build_layers, layers_streams
    from swm.stages.terrain import build_terrain, terrain_streams

    recipe = resolve(Recipe()).recipe
    terrain = build_terrain(
        recipe.terrain, terrain_streams(recipe.root_seed, recipe.terrain.terrain_seed)
    )
    rules = load_registry().with_overrides(SHORT)
    layers = build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed), rules)
    result = undisturbed_supply_check(strength_of((recipe, terrain, layers), SHORT))
    assert not result.passed
    assert all(s.supplier_layer == Layer.POWER for s in result.shortfalls)
    report = result.report()
    assert "shortfalls" in report
    first = result.shortfalls[0]
    assert f"{first.consumer_id} power: R = 0.0000" in report


def test_the_pilot_passes_the_undisturbed_supply_check() -> None:
    from pathlib import Path

    from swm.recipe.io import load_recipe
    from swm.recipe.resolve import resolve
    from swm.stages.layers import build_layers, layers_streams
    from swm.stages.terrain import build_terrain, terrain_streams

    pilot = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"
    recipe = resolve(load_recipe(pilot)).recipe
    terrain = build_terrain(
        recipe.terrain, terrain_streams(recipe.root_seed, recipe.terrain.terrain_seed)
    )
    layers = build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed))
    assert undisturbed_supply_check(strength_of((recipe, terrain, layers))).passed


def test_supply_ratios_add_full_feeds_and_take_the_least_of_half_feeds(
    rich: World, strength: Any
) -> None:
    couplings = couple(rich)
    headroom = {s.edge_id: s.headroom for s in strength.edges}
    ratios = {r.dependency_id: r for r in strength.ratios}
    checked = set()
    for dependency in couplings.dependencies:
        if dependency.role != "primary_supply" or dependency.supplier_layer in (
            Layer.TELECOM,
            Layer.TRANSPORT,
        ):
            continue
        values = [headroom[e] for e in dependency.edge_ids]
        half = dependency.feed_configuration == "two_half"
        expected = min(values) if half else sum(values)
        assert ratios[dependency.dependency_id].uncapped == pytest.approx(expected)
        checked.add(dependency.feed_configuration)
    assert {"single", "two_full", "two_half"} <= checked


def test_a_world_without_power_has_no_power_ratios() -> None:
    world = build_world(layers={"power": {"state": "off"}})
    result = strength_of(world)
    assert all(r.supplier_layer != Layer.POWER for r in result.ratios)
