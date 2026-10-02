"""Build the storm's line and tower fragility tables (structure v0.7 §4.3b).

Offline only: this script uses log and the error function, which the generator itself may not
(CLAUDE.md §4). It prints the values of the registry entries ``storm.line_fragility_table`` and
``storm.tower_fragility_table``; paste them into ``src/swm/rules/modeling_rules.yaml``.

Both are lognormal fragilities against the 3-second gust, P(g) = Phi(ln(g / median) / beta),
tabulated on whole metres per second and interpolated linearly at runtime:
- overhead lines on poles: the chance of failing per km of line, with the ruled beta of
  ``LINE_BETA`` and the median ``LINE_MEDIAN`` found by ``tools/calibrate_line_curve.py``
  (a declared calibration, decision 0012 second addendum);
- transmission towers: the chance a towered line collapses, median 285 km/h, beta 0.10
  (Cyclone Fani and Quanta 2009 curves).

Run: ``uv run python tools/build_fragility_tables.py``.

Spec: structure v0.7 §4.3b (overhead lines); Work Order 6, D1; decision 0012.
"""

import math

GUSTS = tuple(range(0, 121))
"""Knots: 3-second gust in m/s, 0 to 120 in steps of 1."""

LINE_MEDIAN = 159.9394
"""Median of the pole-line curve (m/s): a calibration parameter, not a physical gust. The
best single median for both targets at beta 0.4 (``tools/calibrate_line_curve.py``)."""
LINE_BETA = 0.4
"""Lognormal dispersion of the pole-line curve: ruled 0.4 (J), decision 0012 second addendum."""

TOWER_MEDIAN_KM_PER_H = 285.0
TOWER_BETA = 0.10
DIGITS = 9


def normal_cdf(x: float) -> float:
    """Return the standard normal CDF at x."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def lognormal(gust: float, median: float, beta: float) -> float:
    """Lognormal fragility at a gust, rounded to the stored digits; 0 at no gust."""
    if gust <= 0.0:
        return 0.0
    return round(normal_cdf(math.log(gust / median) / beta), DIGITS)


def main() -> None:
    """Print both tables as registry YAML."""
    median = LINE_MEDIAN
    tower_median = TOWER_MEDIAN_KM_PER_H / 3.6
    lines = [
        "storm.line_fragility_table:",
        f"    median_m_per_s: {round(median, 6)}",
        f"    beta: {LINE_BETA}",
        "    gust_m_per_s: [" + ", ".join(str(float(g)) for g in GUSTS) + "]",
        "    failures_per_km: ["
        + ", ".join(repr(lognormal(g, median, LINE_BETA)) for g in GUSTS)
        + "]",
        "storm.tower_fragility_table:",
        f"    median_m_per_s: {round(tower_median, 6)}",
        f"    beta: {TOWER_BETA}",
        "    gust_m_per_s: [" + ", ".join(str(float(g)) for g in GUSTS) + "]",
        "    collapse: ["
        + ", ".join(repr(lognormal(g, tower_median, TOWER_BETA)) for g in GUSTS)
        + "]",
    ]
    print("\n".join(lines))  # noqa: T201 - the script's output is the tables


if __name__ == "__main__":
    main()
