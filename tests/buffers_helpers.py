"""Builders shared by the buffers and strength tests."""

from collections.abc import Mapping
from typing import Any

from couplings_helpers import World, couple, requirements_of
from swm.recipe.schema import CategoricalDrawnQuantity, ContinuousDrawnQuantity
from swm.rules.registry import load_registry
from swm.stages.buffers import BuffersResult, buffers_streams, build_buffers
from swm.stages.strength import StrengthResult, build_strength

NO_GAPS = {
    "reserves.compliance_gap.hospital_backup_pct": 0.0,
    "reserves.compliance_gap.water_facilities_pct": 0.0,
    "reserves.compliance_gap.exchange_data_centre_pct": 0.0,
    "reserves.compliance_gap.mast_pct": 0.0,
}
"""Rule overrides that put every §4.4a class gap at 0."""


def buffers_of(
    world: World,
    heterogeneity_pct: int = 0,
    gap_pct: int = 0,
    failure_heterogeneity_pct: int = 0,
    overrides: Mapping[str, Any] | None = None,
) -> BuffersResult:
    """Draw a world's buffers under the given levers and rule overrides."""
    recipe = world[0]
    rules = load_registry().with_overrides(overrides or {})
    requirements = requirements_of(world, overrides)
    couplings = couple(world, overrides)
    return build_buffers(
        ContinuousDrawnQuantity(heterogeneity_pct=heterogeneity_pct, compliance_gap_pct=gap_pct),
        CategoricalDrawnQuantity(heterogeneity_pct=failure_heterogeneity_pct),
        requirements.layers,
        requirements,
        couplings,
        rules,
        buffers_streams(recipe.root_seed),
    )


def strength_of(world: World, overrides: Mapping[str, Any] | None = None) -> StrengthResult:
    """Derive a world's coupling strength under the given rule overrides."""
    rules = load_registry().with_overrides(overrides or {})
    requirements = requirements_of(world, overrides)
    return build_strength(requirements.layers, requirements, couple(world, overrides), rules)
