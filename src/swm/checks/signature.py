"""The link-signature world check: every link joins classes its layer's signature allows.

A world that fails it is reported, and the build stops; it is never silently regenerated.

Spec: structure v0.9 §4.2 (each layer keeping its own structural signature); Work Order 7,
Part 0.
"""

from swm.stages.layers import LayersResult, signature_allows


def link_signature_problems(layers: LayersResult) -> list[str]:
    """Return one line per link that joins classes its layer's signature does not allow.

    Parameters
    ----------
    layers : LayersResult
        The layers stage's output.

    Returns
    -------
    list of str
        The offending links, in link order; empty when every link obeys its signature.

    Spec: Work Order 7, 0.1.
    """
    classes = {node.node_id: node.node_class for node in layers.nodes}
    present = {
        layer: frozenset(node.node_class for node in layers.nodes if node.layer == layer)
        for layer in layers.states
    }
    return [
        f"{link.link_id}: {classes[link.from_id].value} to {classes[link.to_id].value} is "
        f"outside the {link.layer.value} signature"
        for link in layers.links
        if not signature_allows(
            link.layer, classes[link.from_id], classes[link.to_id], present[link.layer]
        )
    ]
