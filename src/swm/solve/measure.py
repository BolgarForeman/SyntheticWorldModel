"""How an answer is measured: its distance from the optimum, and the spread of every answer.

Distance = (objective - optimum) / (no-action objective - optimum), mirrored for the
offensive model. Zero is the optimum. Where no action already equals the optimum the range is
zero: it is reported, and every distance is undefined; nothing is divided (Work Order 10, B3).

Spec: structure v0.17 §5 (how an answer is measured; the spread); Work Order 10, B3.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from swm.solve.weights import PLACES


@dataclass(frozen=True)
class Range:
    """The measure's range: the optimum and the no-action objective."""

    optimum: float
    no_action: float
    mirrored: bool = False
    """True for the offensive model, which maximizes."""

    @property
    def width(self) -> float:
        """Return how far no action lies from the optimum (never negative)."""
        gap = self.optimum - self.no_action if self.mirrored else self.no_action - self.optimum
        return round(gap, PLACES)

    @property
    def zero(self) -> bool:
        """Return whether no action already equals the optimum."""
        return self.width == 0.0

    def gap(self, objective: float) -> float:
        """Return how far an objective lies from the optimum (never negative)."""
        return round(self.optimum - objective if self.mirrored else objective - self.optimum, 9)

    def distance(self, objective: float) -> float | None:
        """Return an objective's distance from the optimum, or None when the range is zero."""
        if self.zero:
            return None
        return round(self.gap(objective) / self.width, PLACES)

    def within(self, objective: float, band_pct: float) -> bool:
        """Return whether an objective lies within a band of the optimum, without dividing."""
        return self.gap(objective) * 100.0 <= band_pct * self.width


def spread(
    objectives: Sequence[float], measure: Range, bands_pct: Sequence[float]
) -> dict[str, object]:
    """Return the spread of every answer: the share within each band, and the mean distance.

    Parameters
    ----------
    objectives : sequence of float
        Every affordable answer's objective.
    measure : Range
        The optimum and the no-action objective.
    bands_pct : sequence of float
        The bands, in percent of the range (registry ``solve.spread_bands_pct``).

    Returns
    -------
    dict
        The answer count, each band's share and a random answer's mean distance; with a zero
        range, the shares and mean are reported as undefined.

    Spec: structure v0.17 §5 (the spread); Work Order 10, B3.
    """
    count = len(objectives)
    record: dict[str, object] = {"answers": count}
    if measure.zero:
        for band in bands_pct:
            record[f"within_{band:g}_pct"] = None
        record["mean_distance"] = None
        record["note"] = (
            "the range is zero: no action equals the optimum, so no distance is defined"
        )
        return record
    for band in bands_pct:
        inside = sum(1 for value in objectives if measure.within(value, band))
        record[f"within_{band:g}_pct"] = round(inside / count, PLACES)
    distances = [measure.gap(value) / measure.width for value in objectives]
    record["mean_distance"] = round(math.fsum(distances) / count, PLACES)
    return record
