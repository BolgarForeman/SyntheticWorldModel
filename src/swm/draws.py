"""The draw method for every continuous unobserved quantity (structure v0.6 §4.4).

Each quantity has a design target T and two levers: heterogeneity h (the spread, as a standard
deviation relative to T) and the compliance gap g (which moves the median to T(1 - g)). A value
is T(1 - g) x Q(u), where Q is a right-skewed quantile table with median 1 and u is a uniform
draw on the element's own stream. The tables are built offline and stored in the modeling rules
registry (``draws.quantile_table``); here only +, -, x, / and sqrt are used (CLAUDE.md §4).

The spread of Q must be s = h / (1 - g), so that the value's standard deviation is h x T. Two
tabulated tables A and B bracket s; their mixture (1 - w)A + wB keeps median 1, and w solves
the exact quadratic for its variance, so the realised spread matches s exactly.

Spec: structure v0.6 §4.4 (levers, draw method); Work Order 5, B3; decision 0009.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from swm.rules.registry import Registry


@dataclass(frozen=True)
class QuantileTable:
    """One tabulated quantile function: knot values at the shared u-knots."""

    spread: float
    quantiles: tuple[float, ...]


@dataclass(frozen=True)
class DrawMethod:
    """The shared u-knots and the tables, in increasing spread."""

    knots: tuple[float, ...]
    tables: tuple[QuantileTable, ...]

    @classmethod
    def from_registry(cls, rules: Registry) -> "DrawMethod":
        """Read the tables from the registry entry ``draws.quantile_table``.

        Parameters
        ----------
        rules : Registry
            The modeling rules in force.

        Returns
        -------
        DrawMethod
            The knots and tables.

        Spec: Work Order 5, B3.
        """
        value: dict[str, Any] = rules.value("draws.quantile_table")
        return cls(
            knots=tuple(float(u) for u in value["knots"]),
            tables=tuple(
                QuantileTable(float(t["spread"]), tuple(float(q) for q in t["quantiles"]))
                for t in value["tables"]
            ),
        )

    @property
    def largest_spread(self) -> float:
        """The largest tabulated spread; larger requests are held to it."""
        return self.tables[-1].spread

    def mixture(self, spread: float) -> tuple[float, ...]:
        """Return the median-1 quantile knots whose spread is ``spread`` (held to the table).

        Parameters
        ----------
        spread : float
            The standard deviation wanted, relative to the median.

        Returns
        -------
        tuple of float
            Knot values of the mixed table.

        Spec: Work Order 5, B3.
        """
        spread = min(max(spread, 0.0), self.largest_spread)
        upper = next(i for i, t in enumerate(self.tables) if t.spread >= spread)
        if upper == 0 or self.tables[upper].spread == spread:
            return self.tables[upper].quantiles
        a, b = self.tables[upper - 1].quantiles, self.tables[upper].quantiles
        weight = self._weight(a, b, spread)
        return tuple((1.0 - weight) * x + weight * y for x, y in zip(a, b, strict=True))

    def _weight(self, a: Sequence[float], b: Sequence[float], spread: float) -> float:
        """Solve Var((1 - w)A + wB) = spread^2 for w in [0, 1]."""
        mean_a, second_a = self._moments(a, a)
        mean_b, second_b = self._moments(b, b)
        _, cross = self._moments(a, b)
        delta = mean_b - mean_a
        quadratic = second_a - 2.0 * cross + second_b - delta * delta
        linear = 2.0 * ((cross - second_a) - mean_a * delta)
        constant = second_a - mean_a * mean_a - spread * spread
        if quadratic == 0.0:
            return min(max(-constant / linear, 0.0), 1.0)
        root = math.sqrt(max(linear * linear - 4.0 * quadratic * constant, 0.0))
        for weight in ((-linear + root) / (2.0 * quadratic), (-linear - root) / (2.0 * quadratic)):
            if -1e-9 <= weight <= 1.0 + 1e-9:
                return min(max(weight, 0.0), 1.0)
        raise ValueError(f"no mixture of the bracketing tables has spread {spread}")

    def _moments(self, a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
        """Exact mean of A and cross-moment E[AB] of two piecewise-linear quantile functions."""
        mean = 0.0
        cross = 0.0
        for i in range(len(self.knots) - 1):
            width = self.knots[i + 1] - self.knots[i]
            mean += width * (a[i] + a[i + 1]) / 2.0
            cross += width * (2.0 * a[i] * b[i] + a[i] * b[i + 1] + a[i + 1] * b[i]
                              + 2.0 * a[i + 1] * b[i + 1]) / 6.0  # fmt: skip
        return mean, cross

    def quantile(self, quantiles: Sequence[float], u: float) -> float:
        """Interpolate a table's quantile function linearly at u in [0, 1)."""
        knots = self.knots
        for i in range(len(knots) - 1):
            if u <= knots[i + 1]:
                share = (u - knots[i]) / (knots[i + 1] - knots[i])
                return quantiles[i] + share * (quantiles[i + 1] - quantiles[i])
        return quantiles[-1]


@dataclass(frozen=True)
class Levers:
    """The two levers of a drawn quantity, as fractions (the recipe gives percent)."""

    heterogeneity: float
    compliance_gap: float

    @classmethod
    def from_percent(cls, heterogeneity_pct: int, compliance_gap_pct: int) -> "Levers":
        """Build levers from the recipe's percent settings."""
        return cls(heterogeneity_pct / 100.0, compliance_gap_pct / 100.0)

    @property
    def spread(self) -> float:
        """Spread of the quantile table: heterogeneity over (1 - gap), so SD = h x target."""
        return self.heterogeneity / (1.0 - self.compliance_gap)


def draw(target: float, levers: Levers, method: DrawMethod, u: float) -> float:
    """Draw one element's value around its design target.

    Parameters
    ----------
    target : float
        The design target, in the quantity's units.
    levers : Levers
        Heterogeneity and compliance gap.
    method : DrawMethod
        The quantile tables.
    u : float
        A uniform draw in [0, 1) from the element's own stream.

    Returns
    -------
    float
        target x (1 - gap) x Q(u): median target x (1 - gap), standard deviation
        heterogeneity x target (up to the largest tabulated spread).

    Spec: structure v0.6 §4.4; Work Order 5, B3.
    """
    quantiles = method.mixture(levers.spread)
    return target * (1.0 - levers.compliance_gap) * method.quantile(quantiles, u)
