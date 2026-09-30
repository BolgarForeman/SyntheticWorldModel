"""Builders shared by the crews and repair tests."""

import functools
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from couplings_helpers import World, couple, requirements_of
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import ContinuousDrawnQuantity
from swm.rules.registry import load_registry
from swm.stages.crews import CrewsResult, build_crews
from swm.stages.layers import build_layers, layers_streams
from swm.stages.repair import RepairResult, build_repair, repair_streams
from swm.stages.terrain import build_terrain, terrain_streams

PILOT = Path(__file__).resolve().parent / "fixtures" / "pilot_hand_check.yaml"


@functools.cache
def pilot_world() -> World:
    """Build (once) the pilot's terrain and layers."""
    recipe = resolve(load_recipe(PILOT)).recipe
    terrain = build_terrain(
        recipe.terrain, terrain_streams(recipe.root_seed, recipe.terrain.terrain_seed)
    )
    return recipe, terrain, build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed))


def crews_of(
    world: World, crews: int = 2, crew_base: int = 1, overrides: Mapping[str, Any] | None = None
) -> CrewsResult:
    """Site a world's crew bases and deal its crews under the given rule overrides."""
    _, terrain, _ = world
    layers = requirements_of(world, overrides).layers
    rules = load_registry().with_overrides(overrides or {})
    return build_crews(crews, crew_base, terrain, layers, rules)


def repair_of(
    world: World,
    heterogeneity_pct: int = 0,
    gap_pct: int = 0,
    crews: int = 2,
    crew_base: int = 1,
    overrides: Mapping[str, Any] | None = None,
) -> RepairResult:
    """Record a world's repair under the given levers, crews and rule overrides."""
    recipe, terrain, _ = world
    rules = load_registry().with_overrides(overrides or {})
    requirements = requirements_of(world, overrides)
    return build_repair(
        ContinuousDrawnQuantity(heterogeneity_pct=heterogeneity_pct, compliance_gap_pct=gap_pct),
        crews_of(world, crews, crew_base, overrides),
        terrain,
        requirements.layers,
        requirements,
        couple(world, overrides),
        rules,
        repair_streams(recipe.root_seed),
    )
