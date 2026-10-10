"""Builders and invariant checks shared by the layers tests."""

from typing import Any

import numpy as np

from swm.recipe.resolve import resolve
from swm.recipe.schema import Layer, Recipe
from swm.stages.layers import (
    TREE_LAYERS,
    LayersResult,
    Link,
    Node,
    build_layers,
    layers_streams,
    signature_allows,
)
from swm.stages.terrain import GRID_CELLS, CoverClass, TerrainResult, build_terrain, terrain_streams


def build_world(**sections: Any) -> tuple[Recipe, TerrainResult, LayersResult]:
    """Resolve a recipe given in part and build its terrain and layers."""
    recipe = resolve(Recipe.model_validate(sections)).recipe
    terrain = build_terrain(
        recipe.terrain, terrain_streams(recipe.root_seed, recipe.terrain.terrain_seed)
    )
    return recipe, terrain, build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed))


def cell(node: Node) -> int:
    return node.row * GRID_CELLS + node.column


def nodes_of(result: LayersResult, layer: Layer) -> list[Node]:
    return [node for node in result.nodes if node.layer == layer]


def links_of(result: LayersResult, layer: Layer) -> list[Link]:
    return [link for link in result.links if link.layer == layer]


def is_connected(nodes: list[Node], links: list[Link]) -> bool:
    if not nodes:
        return True
    neighbours: dict[str, set[str]] = {node.node_id: set() for node in nodes}
    for link in links:
        neighbours[link.from_id].add(link.to_id)
        neighbours[link.to_id].add(link.from_id)
    seen = {nodes[0].node_id}
    frontier = [nodes[0].node_id]
    while frontier:
        for other in neighbours[frontier.pop()]:
            if other not in seen:
                seen.add(other)
                frontier.append(other)
    return len(seen) == len(nodes)


def feasible_links_per_node(recipe_value: float, nodes: list[Node], layer: Layer) -> float:
    """The recipe value held within what a connected layer of these nodes can realise.

    A tree layer holds n - 1 links; any other layer at most every pair its signature allows
    (Work Order 7, Part 0).
    """
    count = len(nodes)
    if count < 2:
        return 0.0
    least = 2 * (count - 1) / count
    if layer in TREE_LAYERS:
        return least
    present = frozenset(node.node_class for node in nodes)
    pairs = sum(
        1
        for i, a in enumerate(nodes)
        for b in nodes[i + 1 :]
        if signature_allows(layer, a.node_class, b.node_class, present)
    )
    most = max(least, 2 * pairs / count)
    return min(max(recipe_value, least), most)


def sited_on_bad_ground(terrain: TerrainResult, result: LayersResult) -> list[str]:
    """Nodes on sea, river or wetland; a bridge may sit on a river (decision 0006)."""
    land = np.asarray(terrain.land).ravel()
    river = np.asarray(terrain.river).ravel()
    wetland = (np.asarray(terrain.land_cover) == CoverClass.WETLAND).ravel()
    bad = []
    for node in result.nodes:
        index = cell(node)
        on_river = river[index] and node.node_class.value != "bridge"
        if not land[index] or on_river or wetland[index]:
            bad.append(node.node_id)
    return bad
