"""Builders and checks shared by the couplings tests."""

import functools
from collections.abc import Mapping
from typing import Any

from layers_helpers import build_world
from swm.recipe.schema import Couplings, Layer, NodeClass, Recipe
from swm.rules.registry import load_registry
from swm.stages.couplings import CouplingsResult, build_couplings, couplings_streams
from swm.stages.layers import LayersResult, Node
from swm.stages.requirements import build_requirements, requirements_streams
from swm.stages.terrain import TerrainResult

World = tuple[Recipe, TerrainResult, LayersResult]

RICH_LAYERS = {
    "power": {"node_count": 10},
    "telecom": {"node_count": 12},
    "water": {"node_count": 10},
    "transport": {"node_count": 10},
    "fuel": {"node_count": 12},
    "healthcare": {"node_count": 12},
}
"""A world large enough that every pair has several consumers and suppliers."""


@functools.cache
def rich_world() -> World:
    """Build (once) the rich world: default terrain, a dozen nodes per layer."""
    return build_world(terrain={"area_km2": 1500}, layers=RICH_LAYERS)


def requirements_of(world: World, overrides: Mapping[str, float] | None = None) -> Any:
    """Draw a world's requirements under the recipe's levers and the given rule overrides."""
    recipe, _, layers = world
    return build_requirements(
        recipe.unobserved.requirements,
        layers,
        load_registry().with_overrides(overrides or {}),
        requirements_streams(recipe.root_seed),
    )


def couple(
    world: World, overrides: Mapping[str, float] | None = None, **settings: Any
) -> CouplingsResult:
    """Build a world's couplings under couplings settings given in part."""
    recipe, terrain, layers = world
    return build_couplings(
        Couplings.model_validate(settings),
        recipe.dynamics.transfer_forms,
        terrain,
        layers,
        requirements_of(world, overrides),
        load_registry().with_overrides(overrides or {}),
        couplings_streams(recipe.root_seed),
    )


def nodes_by_id(layers: LayersResult) -> dict[str, Node]:
    return {node.node_id: node for node in layers.nodes}


def pair_edges(result: CouplingsResult, supplier: Layer, consumer: Layer) -> list[Any]:
    return [
        e for e in result.edges if e.supplier_layer == supplier and e.consumer_layer == consumer
    ]


def first_feeds(result: CouplingsResult) -> Mapping[str, Any]:
    """The first edge of every dependency that has one, by dependency id."""
    edges = {edge.edge_id: edge for edge in result.edges}
    return {d.dependency_id: edges[d.edge_ids[0]] for d in result.dependencies if d.edge_ids}


def touched_by_two_way(result: CouplingsResult) -> set[str]:
    """Dependencies whose suppliers the two-way step changed."""
    return {
        d.dependency_id
        for d in result.dependencies
        if any(note.startswith("two-way") for note in d.notes)
    }


def is_class(node: Node, *classes: NodeClass) -> bool:
    return node.node_class in classes
