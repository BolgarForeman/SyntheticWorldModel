"""Resolution: fill every default, expand the size preset, and collect validation notes."""

import math
from dataclasses import dataclass

from swm.recipe.schema import (
    LAYER_SOURCES,
    SIZE_PRESETS,
    CategoricalDrawnQuantity,
    Couplings,
    Errors,
    HoldOnAreaChange,
    Layer,
    Layers,
    LayerState,
    ModelingRules,
    Recipe,
    SizePreset,
    Source,
    SourceErrors,
    Terrain,
    Unobserved,
)
from swm.rules.registry import load_registry

LAYER_ORDER = tuple(Layer)
SOURCE_ORDER = tuple(Source)


@dataclass(frozen=True)
class Resolution:
    """A resolved recipe and the notes raised while resolving it."""

    recipe: Recipe
    notes: tuple[str, ...]


def resolve(recipe: Recipe) -> Resolution:
    """Fill every default and expand the size preset, so the recipe states every choice.

    Resolving a resolved recipe changes nothing.

    Parameters
    ----------
    recipe : Recipe
        A validated recipe.

    Returns
    -------
    Resolution
        The resolved recipe, and validation notes: settings that are accepted but ignored.

    Spec: CLAUDE.md §4 (the resolved recipe is written beside every world); Work Order 1,
    item 3.
    """
    notes: list[str] = []
    terrain, layers = _resolve_size(recipe.terrain, recipe.layers)
    layers = _sort_sources(layers)
    couplings = _sort_couplings(recipe.couplings)
    unobserved = _resolve_categorical_gaps(recipe.unobserved, notes)
    errors = _resolve_errors(recipe.errors, layers)
    resolved = recipe.model_copy(
        update={
            "modeling_rules": _stamp_rules(recipe.modeling_rules),
            "terrain": terrain,
            "layers": layers,
            "couplings": couplings,
            "unobserved": unobserved,
            "errors": errors,
        }
    )
    if terrain.character.urban_density == 0:
        notes.append("urban density 0: one minimum town placed so siting has an anchor")
    notes.extend(_layer_notes(layers))
    notes.extend(_coupling_notes(couplings))
    notes.extend(_error_notes(errors, layers))
    # Revalidate so the resolved recipe is held to every rule a written one is.
    return Resolution(Recipe.model_validate(resolved.model_dump()), tuple(notes))


def _stamp_rules(rules: ModelingRules) -> ModelingRules:
    """Stamp the registry's version and hash, and check the overrides (Work Order 5, A3)."""
    registry = load_registry()
    if rules.registry_sha256 not in (None, registry.sha256):
        raise ValueError(
            f"modeling_rules: the recipe was resolved against registry {rules.registry_sha256}, "
            f"but this code carries {registry.sha256}"
        )
    registry.with_overrides(rules.overrides)
    for rule_id in rules.relaxed_limits:
        if not registry.rule(rule_id).is_limit:
            raise ValueError(
                f"modeling_rules.relaxed_limits: {rule_id} is not a limit; it has no relaxed value"
            )
    return rules.model_copy(
        update={
            "registry_version": registry.version,
            "registry_sha256": registry.sha256,
            "overrides": dict(sorted(rules.overrides.items())),
            "relaxed_limits": tuple(sorted(rules.relaxed_limits)),
        }
    )


def active_sources(layers: Layers) -> tuple[Source, ...]:
    """Return the sources switched on for emitted layers, in schema order.

    Parameters
    ----------
    layers : Layers
        The layer settings.

    Returns
    -------
    tuple of Source
        Sources that will be emitted.

    Spec: structure v0.2 §4.6.
    """
    emitted = {
        source
        for layer in LAYER_ORDER
        if layers.get(layer).state == LayerState.EMITTED
        for source in layers.get(layer).sources
    }
    return tuple(source for source in SOURCE_ORDER if source in emitted)


def layer_of(source: Source) -> Layer:
    """Return the layer a source belongs to.

    Parameters
    ----------
    source : Source
        A source.

    Returns
    -------
    Layer
        Its layer.

    Spec: structure v0.2 §4.2.
    """
    return next(layer for layer in LAYER_ORDER if source in LAYER_SOURCES[layer])


def _resolve_size(terrain: Terrain, layers: Layers) -> tuple[Terrain, Layers]:
    if terrain.size_preset == SizePreset.CUSTOM:
        return terrain, layers
    preset = SIZE_PRESETS[terrain.size_preset]
    area_km2 = preset.area_km2 if terrain.area_km2 is None else terrain.area_km2
    nodes_per_layer = preset.nodes_per_layer
    if terrain.hold_on_area_change == HoldOnAreaChange.DENSITY:
        # CHOICE: round half up, as the interface does, with a floor of one node.
        scaled = math.floor(preset.nodes_per_layer * area_km2 / preset.area_km2 + 0.5)
        nodes_per_layer = max(1, scaled)
    filled = {
        layer.value: layers.get(layer).model_copy(update={"node_count": nodes_per_layer})
        for layer in LAYER_ORDER
        if layers.get(layer).node_count is None
    }
    return terrain.model_copy(update={"area_km2": area_km2}), layers.model_copy(update=filled)


def _sort_sources(layers: Layers) -> Layers:
    update = {}
    for layer in LAYER_ORDER:
        settings = layers.get(layer)
        ordered = tuple(source for source in LAYER_SOURCES[layer] if source in settings.sources)
        update[layer.value] = settings.model_copy(update={"sources": ordered})
    return layers.model_copy(update=update)


def _sort_couplings(couplings: Couplings) -> Couplings:
    ordered = sorted(
        couplings.switched_on,
        key=lambda pair: (LAYER_ORDER.index(pair.supplier), LAYER_ORDER.index(pair.consumer)),
    )
    return couplings.model_copy(update={"switched_on": tuple(ordered)})


def _resolve_categorical_gaps(unobserved: Unobserved, notes: list[str]) -> Unobserved:
    update: dict[str, CategoricalDrawnQuantity] = {}
    for name in ("failure_mode", "links_on_nodes_only_layers"):
        quantity: CategoricalDrawnQuantity = getattr(unobserved, name)
        if quantity.compliance_gap_pct != 0:
            notes.append(
                f"unobserved.{name}.compliance_gap_pct does not apply and is set to 0 "
                f"(was {quantity.compliance_gap_pct})"
            )
            update[name] = quantity.model_copy(update={"compliance_gap_pct": 0})
    return unobserved.model_copy(update=update)


def _resolve_errors(errors: Errors, layers: Layers) -> Errors:
    listed = set(errors.sources) | set(active_sources(layers))
    resolved: dict[Source, SourceErrors] = {}
    for source in SOURCE_ORDER:
        if source not in listed:
            continue
        settings = errors.sources.get(source, SourceErrors())
        if settings.mechanism is None:
            settings = settings.model_copy(update={"mechanism": errors.default_mechanism})
        resolved[source] = settings
    return errors.model_copy(update={"sources": resolved})


def _layer_notes(layers: Layers) -> list[str]:
    notes = []
    for layer in LAYER_ORDER:
        settings = layers.get(layer)
        if settings.state == LayerState.EMITTED and not settings.sources:
            notes.append(f"layers.{layer} is emitted but has no sources, so nothing is emitted")
        if settings.state != LayerState.EMITTED and settings.sources:
            notes.append(f"layers.{layer}.sources are ignored: the layer is {settings.state}")
    return notes


def _coupling_notes(couplings: Couplings) -> list[str]:
    suppliers = sorted(
        {pair.consumer.value for pair in couplings.switched_on if pair.supplier == Layer.HEALTHCARE}
    )
    if not suppliers:
        return []
    return [
        "couplings.switched_on has healthcare supplying "
        + ", ".join(suppliers)
        + "; the spec models healthcare as a pure sink"
    ]


def _error_notes(errors: Errors, layers: Layers) -> list[str]:
    notes = []
    active = active_sources(layers)
    for source in errors.sources:
        layer = layer_of(source)
        if source not in active:
            notes.append(f"errors.sources.{source} is ignored: the source is not emitted")
            continue
        if errors.sources[source].coverage_pct == 0:
            notes.append(f"errors.sources.{source}.coverage_pct is 0: the source carries nothing")
        if layers.get(layer).nodes_only:
            notes.append(
                f"errors.sources.{source}.links_pct is ignored: {layer} sources report nodes only"
            )
    return notes
