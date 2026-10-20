"""Answer-key requests as the solver reads them: grouped into searches, and stamped.

Spec: structure v0.17 §5 (a model request; the stamp); Work Order 10, B2 and B3.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from swm.recipe.schema import (
    ObserveUncertainCouplings,
    ProtectConditionAndAddReserve,
    SequenceRepairCrews,
    StrikeNodes,
)

SolvedRequest = (
    ProtectConditionAndAddReserve | StrikeNodes | SequenceRepairCrews | ObserveUncertainCouplings
)
"""The request models the solver knows. The others carry no parameters yet."""

WEIGHT_FIELDS = ("service_weights", "custom_weights")
"""The fields a weighting changes; requests equal in every other field share one search."""


@dataclass(frozen=True)
class Search:
    """One search, and the requests that share it (they differ only in their weights)."""

    request_indices: tuple[int, ...]
    """Each request's place in the recipe's list, from 0."""

    @property
    def first(self) -> int:
        """The first request's index, which names the search's files."""
        return self.request_indices[0]


def searches(requests: Sequence[object]) -> tuple[Search, ...]:
    """Group a recipe's requests into searches: requests that differ only in their weights.

    Parameters
    ----------
    requests : sequence of request
        The recipe's answer-key requests, in order.

    Returns
    -------
    tuple of Search
        In the order of each search's first request.

    Spec: Work Order 10, B2.
    """
    groups: dict[str, list[int]] = {}
    for index, request in enumerate(requests):
        groups.setdefault(search_key(request), []).append(index)
    return tuple(Search(tuple(indices)) for indices in groups.values())


def search_key(request: object) -> str:
    """Return a request's fields less its weights, as canonical text."""
    assert hasattr(request, "model_dump")
    fields = {k: v for k, v in request.model_dump(mode="json").items() if k not in WEIGHT_FIELDS}
    return json.dumps(fields, sort_keys=True)


def budget_text(request: SolvedRequest) -> str:
    """Return a request's budget as the stamp names it (structure v0.17 §5, the budget row)."""
    if isinstance(request, ProtectConditionAndAddReserve):
        return f"{request.budget_cost_units} cost units"
    if isinstance(request, StrikeNodes):
        return f"{request.strikes_k} nodes struck"
    if isinstance(request, ObserveUncertainCouplings):
        return f"{request.observations_n} couplings observed"
    return "none (the world's crews)"


def scenarios_text(request: SolvedRequest) -> str:
    """Return the scenarios a request is solved over, as the stamp names them."""
    if isinstance(request, SequenceRepairCrews):
        return f"scenario {request.scenario}"
    if isinstance(request, StrikeNodes):
        return "the calm world"
    return "every scenario, equally weighted"


def weights_text(request: SolvedRequest) -> str:
    """Return a request's service weights as the stamp names them."""
    if request.custom_weights is None:
        return str(request.service_weights)
    pairs = ", ".join(f"{k} {v}" for k, v in sorted(request.custom_weights.items()))
    return f"custom ({pairs})"


def stamp(request: SolvedRequest, recipe_sha256: str) -> str:
    """Return the key's stamp: "assumes:" and every field the key is valid for.

    Parameters
    ----------
    request : SolvedRequest
        The request.
    recipe_sha256 : str
        The resolved recipe's SHA-256.

    Returns
    -------
    str
        The stamp.

    Spec: structure v0.17 §5 (the stamp); Work Order 10, B3.
    """
    return (
        f"assumes: {request.member_class}; {request.model}; {request.objective}; "
        f"service weights {weights_text(request)}; budget {budget_text(request)}; "
        f"window {request.window_h} h; {scenarios_text(request)}; "
        f"resolved recipe sha256 {recipe_sha256}"
    )
