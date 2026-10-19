from hypothesis import example, given, settings
from hypothesis import strategies as st

from layers_helpers import (
    build_world,
    feasible_links_per_node,
    is_connected,
    links_of,
    nodes_of,
    sited_on_bad_ground,
)
from swm.recipe.schema import Layer
from swm.stages.layers import TREE_LAYERS, class_counts

layer_settings = st.fixed_dictionaries(
    {
        "state": st.sampled_from(["emitted", "hidden", "off"]),
        "node_count": st.integers(min_value=1, max_value=20),
        "links_per_node": st.floats(min_value=1.0, max_value=4.0).map(lambda v: round(v, 1)),
    }
)


def _emitted(node_count: int, links_per_node: float) -> dict[str, object]:
    return {"state": "emitted", "node_count": node_count, "links_per_node": links_per_node}


@settings(max_examples=8, deadline=None)
@given(
    sections=st.fixed_dictionaries({layer.value: layer_settings for layer in Layer}),
    dual=st.booleans(),
    terrain_seed=st.integers(min_value=0, max_value=2**32),
)
# Issue #21: Hypothesis found a bridge sited on a wetland river cell with terrain seed 15746
# (decision 0016, addendum).
@example(
    sections={
        "power": _emitted(12, 1.1),
        "telecom": _emitted(10, 2.4),
        "water": _emitted(18, 1.1),
        "transport": _emitted(18, 2.0),
        "fuel": _emitted(4, 1.1),
        "healthcare": _emitted(3, 2.9),
    },
    dual=False,
    terrain_seed=15746,
)
def test_any_valid_layers_section_keeps_the_invariants(
    sections: dict[str, dict[str, object]], dual: bool, terrain_seed: int
) -> None:
    _, terrain, result = build_world(
        terrain={"terrain_seed": terrain_seed, "area_km2": 1500},
        layers={"dual_membership": dual, **sections},
    )
    assert sited_on_bad_ground(terrain, result) == []
    for layer in Layer:
        settings_ = sections[layer.value]
        nodes = nodes_of(result, layer)
        if settings_["state"] == "off":
            assert nodes == []
            continue
        count = int(str(settings_["node_count"]))
        expected = {c.value: n for c, n in class_counts(layer, count).items() if n}
        realised: dict[str, int] = {}
        for node in nodes:
            realised[node.node_class.value] = realised.get(node.node_class.value, 0) + 1
        assert realised == expected, layer
        links = links_of(result, layer)
        assert is_connected(nodes, links), layer
        if layer in TREE_LAYERS:
            assert len(links) == count - 1, layer
        if layer == Layer.TRANSPORT:
            assert not any(link.crosses_sea for link in links)
        realised_lpn = 2 * len(links) / count
        wanted = float(str(settings_["links_per_node"]))
        feasible = feasible_links_per_node(wanted, nodes, layer)
        assert abs(realised_lpn - feasible) <= 0.5 + 1 / count, layer
