"""Build the lognormal-shaped quantile tables of the draw method (structure v0.6 §4.4).

Offline only: this script uses log, exp and the error function, which the generator itself
may not (CLAUDE.md §4). It prints the tables as the YAML value of the registry entry
``draws.quantile_table``; paste that value into ``src/swm/rules/modeling_rules.yaml``.

Each table is a piecewise-linear quantile function Q(u) on fixed u-knots:
- lognormal-shaped with log-scale parameter sigma;
- scaled so that Q(0.5) = 1 (the median);
- clipped at the 0.5% and 99.5% quantiles (the end knots repeat those values);
- sigma is chosen by bisection so that the piecewise-linear table itself has standard
  deviation exactly equal to the grid value s, relative to its median.

Run: ``uv run python tools/build_quantile_table.py``.

Spec: structure v0.6 §4.4 (draw method); Work Order 5, B3; review F4 and F8 of the design
targets evidence.
"""

import math

KNOTS = (
    0.0, 0.005, 0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
    0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.975, 0.99, 0.995, 1.0,
)  # fmt: skip
"""u-knots. The ends repeat the 0.5% and 99.5% quantiles: the clip."""

CLIP = 0.005
GRID = tuple(round(0.1 * i, 1) for i in range(31))
"""Spreads tabulated: standard deviation relative to the median, 0 to 3 in steps of 0.1."""
DIGITS = 9


def normal_quantile(p: float) -> float:
    """Inverse standard normal CDF by bisection on erf (offline, so any precision will do)."""
    low, high = -10.0, 10.0
    for _ in range(200):
        middle = (low + high) / 2
        if 0.5 * (1 + math.erf(middle / math.sqrt(2))) < p:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def table(sigma: float) -> list[float]:
    """Knot values for one sigma: median 1, clipped at the 0.5% and 99.5% quantiles."""
    values = []
    for u in KNOTS:
        clipped = min(max(u, CLIP), 1 - CLIP)
        values.append(math.exp(sigma * normal_quantile(clipped)))
    return values


def moments(values: list[float]) -> tuple[float, float]:
    """Exact mean and second moment of a piecewise-linear quantile function."""
    mean = second = 0.0
    for i in range(len(KNOTS) - 1):
        width = KNOTS[i + 1] - KNOTS[i]
        a, b = values[i], values[i + 1]
        mean += width * (a + b) / 2
        second += width * (a * a + a * b + b * b) / 3
    return mean, second


def spread(values: list[float]) -> float:
    mean, second = moments(values)
    return math.sqrt(max(0.0, second - mean * mean))


def solve(target: float) -> list[float]:
    """The table whose own standard deviation (median 1) equals target."""
    if target == 0:
        return [1.0] * len(KNOTS)
    low, high = 0.0, 5.0
    for _ in range(200):
        middle = (low + high) / 2
        if spread(table(middle)) < target:
            low = middle
        else:
            high = middle
    return table((low + high) / 2)


def main() -> None:
    lines = ["    knots: [" + ", ".join(repr(u) for u in KNOTS) + "]", "    tables:"]
    for s in GRID:
        values = [round(v, DIGITS) for v in solve(s)]
        values[KNOTS.index(0.5)] = 1.0
        lines.append(f"      - spread: {s}")
        lines.append("        quantiles: [" + ", ".join(repr(v) for v in values) + "]")
    print("\n".join(lines))  # noqa: T201 - the script's output is the table


if __name__ == "__main__":
    main()
