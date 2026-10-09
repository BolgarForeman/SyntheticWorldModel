"""Calibrate the ceiling on the ridge speed-up (structure v0.8 §4.3b).

Offline only. A declared calibration (decision 0013, second addendum): find the ceiling at which
the pilot's highest 3-second gust at pole height, over its scenarios and its land, equals
Taiwan's highest measured gust, 95.2 m/s (Lanyu, Typhoon Koinu 2023). The gust is the one the
scenarios stage reads: 10-minute wind x gust factor x min(ridge factor, ceiling).

The highest gust rises with the ceiling, so the script bisects on it between 1 (no speed-up)
and the largest uncapped factor. If even a ceiling of 1 gives a higher gust, the target cannot
be met and the script says so.

Run: ``uv run python tools/calibrate_ridge_ceiling.py`` (from the repository root).

Spec: structure v0.8 §4.3b (ceiling on the speed-up); PR 14 second answers, 1.
"""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from swm.cli import _rules, _storm, _terrain
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.stages.scenarios import Structure, _LineReader

PILOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pilot_hand_check.yaml"
TARGET_GUST_M_PER_S = 95.2
"""Taiwan's highest measured gust: Lanyu, Typhoon Koinu, 2023-10-05 (CNA)."""
UNCAPPED = 1.0e9
"""A ceiling that never binds, to read the uncapped factor."""


def highest_gust(
    flat: list[NDArray[np.float64]], ridge: list[NDArray[np.float64]], ceiling: float
) -> float:
    """Return the highest gust on land over the scenarios with the factor held to the ceiling."""
    return max(float((f * np.minimum(r, ceiling)).max()) for f, r in zip(flat, ridge, strict=True))


def main() -> None:
    """Report the ceiling that puts the pilot's highest pole-height gust at the record."""
    resolution = resolve(load_recipe(PILOT))
    terrain = _terrain(resolution)
    storm = _storm(resolution, terrain)
    rules = _rules(resolution).with_overrides({"storm.ridge_factor_ceiling": UNCAPPED})
    reader = _LineReader(terrain, rules)
    land = np.asarray(terrain.land)
    flat = [(s.wind_m_per_s * reader.factor)[land] for s in storm.scenarios]
    ridge = [reader.ridge(s, Structure.POLE)[land] for s in storm.scenarios]
    low, high = 1.0, max(float(r.max()) for r in ridge)
    if highest_gust(flat, ridge, low) > TARGET_GUST_M_PER_S:
        _say(f"even a ceiling of 1 gives {highest_gust(flat, ridge, low):.2f} m/s: target unmet")
        return
    for _ in range(60):
        middle = (low + high) / 2
        if highest_gust(flat, ridge, middle) > TARGET_GUST_M_PER_S:
            high = middle
        else:
            low = middle
    ceiling = round(low, 2)
    _say(f"ceiling {low:.6f}; stored to 2 decimals: {ceiling:.2f}")
    _say(f"highest pole-height gust at {ceiling:.2f}: {highest_gust(flat, ridge, ceiling):.2f} m/s")


def _say(line: str) -> None:
    print(line)  # noqa: T201 - the script's output is its report


if __name__ == "__main__":
    main()
