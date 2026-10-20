"""Nodes = area times density within rounding (CLAUDE.md §7; structure v0.2 §4.1).

When a recipe changes a size preset's area and holds density, each layer's node count is the
preset's density times the area, rounded to the nearest node (at least one), and the layers stage
splits exactly that many nodes across the layer's classes.
"""

from hypothesis import given
from hypothesis import strategies as st

from swm.recipe.io import parse_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import SIZE_PRESETS, Layer, SizePreset
from swm.stages.layers import class_counts

presets = st.sampled_from(sorted(SIZE_PRESETS))
area_scale = st.floats(min_value=0.0, max_value=4.0, allow_nan=False, allow_infinity=False)


@given(preset=presets, scale=area_scale)
def test_node_counts_are_area_times_density_within_rounding(
    preset: SizePreset, scale: float
) -> None:
    values = SIZE_PRESETS[preset]
    area_km2 = max(1.0, round(values.area_km2 * scale, 3))
    text = f"recipe_version: 1\nterrain:\n  size_preset: {preset.value}\n  area_km2: {area_km2}\n"
    recipe = resolve(parse_recipe(text)).recipe
    density_per_km2 = values.nodes_per_layer / values.area_km2
    expected = density_per_km2 * area_km2
    for layer in Layer:
        count = recipe.layers.get(layer).node_count
        assert count is not None
        assert abs(count - expected) <= 0.5 or (count == 1 and expected < 0.5), (layer, count)
        if count <= 2_000:  # the composition split is checked at the sizes worlds are built
            assert sum(class_counts(layer, count).values()) == count, layer
