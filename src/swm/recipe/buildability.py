"""Buildability: which features a recipe uses, and which of them are not yet built.

The whole recipe is accepted (ruling of 2026-09-28, decision 0002). ``swm build`` refuses a
recipe that uses a feature not yet built, naming the phase it arrives in.
"""

from dataclasses import dataclass
from enum import StrEnum

from swm.recipe.resolve import active_sources
from swm.recipe.schema import (
    SIZE_PRESETS,
    Hazard,
    Layer,
    LayerState,
    Recipe,
    SizePreset,
    SwitchedOffHandling,
    TransferForm,
)


class Arrival(StrEnum):
    """When a feature is built. Source: Build Game Plan v0.1 §3; rulings A4, A6 (decision 0003)."""

    PHASE_1 = "Phase 1"
    PHASE_2 = "Phase 2"
    PHASE_3 = "Phase 3"
    PHASE_5 = "Phase 5"
    PHASE_6 = "Phase 6"
    PHASE_8 = "Phase 8"
    NOT_YET_SCHEDULED = "not yet scheduled"
    NEVER = "never: carried in the schema, not exercised"


FEATURE_ARRIVALS: dict[str, Arrival] = {
    "map_type:spine_island": Arrival.PHASE_1,
    "map_type:archipelago": Arrival.PHASE_5,
    "map_type:continent": Arrival.PHASE_5,
    "map_type:coastal_strip": Arrival.PHASE_5,
    "map_type:river_delta": Arrival.PHASE_5,
    "map_type:twin_islands": Arrival.PHASE_5,
    "map_type:mainland_and_islands": Arrival.PHASE_5,
    "map_type:peninsula": Arrival.PHASE_5,
    "map_type:mountain_basin": Arrival.PHASE_5,
    "map_type:arid_plateau": Arrival.PHASE_5,
    "map_type:landlocked": Arrival.PHASE_5,
    "terrain_character": Arrival.PHASE_1,
    "size:up_to_small": Arrival.PHASE_1,
    "size:larger_than_small": Arrival.PHASE_5,
    "layer_siting_and_links": Arrival.PHASE_1,
    "layer_state:hidden": Arrival.PHASE_1,
    "layer_state:off": Arrival.PHASE_1,
    "nodes_only": Arrival.PHASE_1,
    "dual_membership": Arrival.PHASE_1,
    "emission": Arrival.PHASE_1,
    "source_overlap": Arrival.PHASE_3,
    "couplings": Arrival.PHASE_1,
    "couplings_hidden": Arrival.PHASE_1,
    "couplings_two_way": Arrival.PHASE_1,
    "hazard:storm_corridor": Arrival.PHASE_1,
    "hazard:seismic_zone": Arrival.PHASE_5,
    "hazard:flood_plain": Arrival.PHASE_5,
    "unobserved_quantities": Arrival.PHASE_1,
    "crews_and_depots": Arrival.PHASE_1,
    "tier:exact": Arrival.PHASE_1,
    "tier:simulation": Arrival.PHASE_5,
    "tier:both": Arrival.PHASE_5,
    "transfer_form:linear": Arrival.PHASE_1,
    "transfer_form:threshold": Arrival.PHASE_1,
    "transfer_form:step": Arrival.PHASE_1,
    "transfer_form:concave": Arrival.PHASE_5,
    "error_mechanism:parametric": Arrival.PHASE_3,
    "error_mechanism:process": Arrival.PHASE_6,
    "error_mechanism:replay": Arrival.PHASE_6,
    "error_mechanism:generative": Arrival.PHASE_6,
    "error_mechanism:adversarial": Arrival.NEVER,
    "ensemble_members": Arrival.PHASE_8,
    "model:protect_condition_and_add_reserve": Arrival.PHASE_2,
    "model:strike_nodes": Arrival.PHASE_2,
    "model:sequence_repair_crews": Arrival.PHASE_2,
    "model:observe_uncertain_couplings": Arrival.PHASE_2,
    "model:add_redundant_feeds": Arrival.NOT_YET_SCHEDULED,
    "model:drain_reserves": Arrival.NOT_YET_SCHEDULED,
    "model:stage_crews_at_depots": Arrival.NOT_YET_SCHEDULED,
    "model:verify_source_records": Arrival.NOT_YET_SCHEDULED,
    "objective:unserved_demand_hours": Arrival.PHASE_2,
    "objective:time_to_restore_80_pct": Arrival.NOT_YET_SCHEDULED,
    "objective:worst_single_layer": Arrival.NOT_YET_SCHEDULED,
    "service_weights:lifeline": Arrival.PHASE_2,
    # CHOICE: equal weights arrive with the request stage, as lifeline weights do.
    "service_weights:equal": Arrival.PHASE_2,
    "service_weights:custom": Arrival.NOT_YET_SCHEDULED,
}
"""Every feature a recipe can use, and when it arrives. The single table the check reads."""

FEATURE_NOTES: dict[str, str] = {
    "size:larger_than_small": "Phase 1 builds up to 20 nodes per layer and 2,000 km² of land",
    "transfer_form:concave": "concave arrives with the simulation tier; an exact-tier or "
    "both-tier world that uses it is refused until then",
}
"""Why a feature is refused, where the phase alone does not say (decision 0004, B2 and B3)."""

BUILT_FEATURES: frozenset[str] = frozenset({"map_type:spine_island", "terrain_character"})
"""Features the generator builds today: the spine-island terrain stage (Work Order 2)."""


@dataclass(frozen=True)
class FeatureStatus:
    """A feature a recipe uses and when it arrives."""

    feature: str
    arrival: Arrival
    note: str


def features_used(recipe: Recipe) -> tuple[str, ...]:
    """Return every feature a resolved recipe uses, in table order.

    Parameters
    ----------
    recipe : Recipe
        A resolved recipe.

    Returns
    -------
    tuple of str
        Feature names, each a key of ``FEATURE_ARRIVALS``.

    Spec: Work Order 1, item 2 (buildability check).
    """
    used = (
        _terrain_features(recipe)
        | _layer_features(recipe)
        | _coupling_features(recipe)
        | _dynamics_features(recipe)
        | _error_features(recipe)
        | _request_features(recipe)
    )
    if recipe.ensemble.members > 1:
        used.add("ensemble_members")
    return tuple(feature for feature in FEATURE_ARRIVALS if feature in used)


def unbuilt_features(recipe: Recipe) -> tuple[FeatureStatus, ...]:
    """Return the features a resolved recipe uses that are not yet built, with their arrival.

    Adversarial error is always among them: it is carried in the schema and never exercised.

    Parameters
    ----------
    recipe : Recipe
        A resolved recipe.

    Returns
    -------
    tuple of FeatureStatus
        One entry per unbuilt feature, in table order. Empty if the recipe is buildable.

    Spec: Work Order 1, item 2 (buildability check).
    """
    return tuple(
        FeatureStatus(feature, FEATURE_ARRIVALS[feature], FEATURE_NOTES.get(feature, ""))
        for feature in features_used(recipe)
        if feature not in BUILT_FEATURES or FEATURE_ARRIVALS[feature] == Arrival.NEVER
    )


def _terrain_features(recipe: Recipe) -> set[str]:
    return {f"map_type:{recipe.terrain.map_type}", "terrain_character", _size_feature(recipe)}


def _size_feature(recipe: Recipe) -> str:
    small = SIZE_PRESETS[SizePreset.SMALL]
    counts = [
        recipe.layers.get(layer).node_count or 0
        for layer in Layer
        if recipe.layers.get(layer).state != LayerState.OFF
    ]
    area_km2 = recipe.terrain.area_km2 or 0.0
    if area_km2 <= small.area_km2 and all(count <= small.nodes_per_layer for count in counts):
        return "size:up_to_small"
    return "size:larger_than_small"


def _layer_features(recipe: Recipe) -> set[str]:
    layers = recipe.layers
    present = [layers.get(layer) for layer in Layer if layers.get(layer).state != LayerState.OFF]
    features: set[str] = set()
    if present:
        features |= {"layer_siting_and_links", "unobserved_quantities", "crews_and_depots"}
    for settings in (layers.get(layer) for layer in Layer):
        if settings.state != LayerState.EMITTED:
            features.add(f"layer_state:{settings.state}")
        elif len(settings.sources) > 1:
            features.add("source_overlap")
    if any(settings.nodes_only for settings in present):
        features.add("nodes_only")
    if layers.dual_membership:
        features.add("dual_membership")
    if active_sources(layers):
        features.add("emission")
    return features


def _coupling_features(recipe: Recipe) -> set[str]:
    couplings = recipe.couplings
    features: set[str] = set()
    if couplings.switched_on:
        features.add("couplings")
    all_pairs = len(Layer) * (len(Layer) - 1)
    some_switched_off = len(couplings.switched_on) < all_pairs
    if (
        some_switched_off
        and couplings.switched_off_handling == SwitchedOffHandling.GENERATE_AND_HIDE
    ):
        features.add("couplings_hidden")
    if couplings.two_way:
        features.add("couplings_two_way")
    hazards = recipe.shared_causes.hazards
    features |= {f"hazard:{hazard}" for hazard in Hazard if hazards.get(hazard).switched_on}
    return features


def _dynamics_features(recipe: Recipe) -> set[str]:
    forms = recipe.dynamics.transfer_forms
    used_forms: set[TransferForm] = {
        forms.physical_flow,
        forms.logistic,
        forms.control,
        forms.service,
    }
    return {f"tier:{recipe.dynamics.tier}"} | {f"transfer_form:{form}" for form in used_forms}


def _error_features(recipe: Recipe) -> set[str]:
    features = set()
    for source in active_sources(recipe.layers):
        settings = recipe.errors.sources.get(source)
        mechanism = settings.mechanism if settings and settings.mechanism else None
        features.add(f"error_mechanism:{mechanism or recipe.errors.default_mechanism}")
    return features


def _request_features(recipe: Recipe) -> set[str]:
    features = set()
    for request in recipe.answer_key_requests:
        features |= {
            f"model:{request.model}",
            f"objective:{request.objective}",
            f"service_weights:{request.service_weights}",
        }
    return features
