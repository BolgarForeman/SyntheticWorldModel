"""Service weights and the objective: weighted service-hours lost at end-use nodes.

Requests that differ only in their weights share one search: a run records each end use's
hours out, and each weighting is arithmetic on them (Work Order 10, B2).

Spec: structure v0.17 §5 (what unserved demand-hours counts); Work Order 10, B2.
"""

import math
from collections.abc import Mapping, Sequence

from swm.dynamics.world import EngineNode
from swm.recipe.schema import (
    EQUAL_WEIGHTS,
    LIFELINE_WEIGHTS,
    EndUseClass,
    WeightPreset,
)
from swm.solve.requests import SolvedRequest

PLACES = 6
"""Decimal places an objective is kept to: the run files' precision (Work Order 7, E2)."""


def node_weights(request: SolvedRequest, nodes: Sequence[EngineNode]) -> dict[str, float]:
    """Return each end-use node's weight under a request's service weights.

    Parameters
    ----------
    request : SolvedRequest
        The request, whose service weights (and custom weights) are read.
    nodes : sequence of EngineNode
        The engine's nodes; only end uses are weighted.

    Returns
    -------
    dict of str to float
        Weight per end-use node id.

    Spec: structure v0.17 §5 (end-use classes and the service-weight presets).
    """
    if request.service_weights == WeightPreset.LIFELINE:
        table: Mapping[EndUseClass, float] = LIFELINE_WEIGHTS
    elif request.service_weights == WeightPreset.EQUAL:
        table = EQUAL_WEIGHTS
    else:
        assert request.custom_weights is not None
        table = {end_use: float(weight) for end_use, weight in request.custom_weights.items()}
    return {
        node.node_id: table[EndUseClass(node.node_class.value)]
        for node in nodes
        if node.end_use_weight is not None
    }


def objective(hours_out: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Return weighted service-hours lost: hours out times weight, summed over end uses.

    Parameters
    ----------
    hours_out : Mapping[str, float]
        A run's hours out per end-use node, in h.
    weights : Mapping[str, float]
        Weight per end-use node.

    Returns
    -------
    float
        Weighted service-hours, at 6 decimals.

    Spec: structure v0.17 §5.
    """
    return round(math.fsum(weights[n] * hours_out[n] for n in sorted(weights)), PLACES)
