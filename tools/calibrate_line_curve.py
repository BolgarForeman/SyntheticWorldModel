"""Calibrate the median of the pole-line fragility curve (structure v0.7 §4.3b).

Offline only. A declared calibration (decision 0012, second addendum): with the curve's beta held
at its placeholder, find the median gust at which the pilot (severity 50) loses about 10% of its
overhead line length and the severity-70 copy about 30%, each averaged over the recipe's
scenarios. Line length lost is the length of every line that is down (any kilometre failed, or
its towers collapsed), over the length of all overhead lines.

For each target the script bisects on the median, rebuilding the stored table from
``build_fragility_tables`` so the runtime path is exactly the generator's. It then checks
whether one median puts both recipes within 5 percentage points of their targets. If none
does, it reports, without applying it, the smallest beta at which one median would.

Run: ``uv run python tools/calibrate_line_curve.py`` (from the repository root).

Spec: structure v0.7 §4.3b (overhead lines: calibration); Work Order 6, PR 6b answer 2.
"""

import math
from pathlib import Path
from typing import Any

import build_fragility_tables as tables

from swm.cli import _couplings, _requirements, _rules, _storm, _terrain
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.stages.scenarios import ScenariosResult, build_scenarios, scenarios_streams

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
RECIPES = {
    "severity_50": (FIXTURES / "pilot_hand_check.yaml", 0.10),
    "severity_70": (FIXTURES / "storm_sensitivity" / "pilot_severity_70.yaml", 0.30),
}
TOLERANCE = 0.05
"""Both recipes must land within 5 percentage points of their targets."""
SEARCH_STEPS = 200
"""Medians tried between the two single-target medians."""
BETAS = tuple(round(0.30 + 0.05 * i, 2) for i in range(35))
"""Spreads scanned, for the report only, when beta 0.3 cannot meet both targets."""


def prepared(path: Path) -> dict[str, Any]:
    """Return everything the scenarios stage reads, built once per recipe."""
    resolution = resolve(load_recipe(path))
    terrain = _terrain(resolution)
    requirements = _requirements(resolution, terrain)
    return {
        "resolution": resolution,
        "terrain": terrain,
        "requirements": requirements,
        "couplings": _couplings(resolution, terrain, requirements),
        "storm": _storm(resolution, terrain),
    }


def length_share(world: dict[str, Any], median: float, beta: float = tables.LINE_BETA) -> float:
    """Return the mean share of overhead line length down across the recipe's scenarios."""
    gusts = [float(g) for g in tables.GUSTS]
    table = {
        "median_m_per_s": median,
        "beta": beta,
        "gust_m_per_s": gusts,
        "failures_per_km": [tables.lognormal(g, median, beta) for g in gusts],
    }
    resolution = world["resolution"]
    rules = _rules(resolution).with_overrides({"storm.line_fragility_table": table})
    recipe = resolution.recipe
    result: ScenariosResult = build_scenarios(
        recipe.shared_causes.facility_damage_cap,
        world["storm"],
        world["terrain"],
        world["requirements"].layers,
        world["couplings"],
        rules,
        scenarios_streams(recipe.root_seed, recipe.shared_causes.scenarios),
    )
    lengths = {line.line_id: line.length_km for line in result.lines}
    total = math.fsum(lengths.values())
    shares = [
        math.fsum(lengths[line.line_id] for line in scenario.failed_lines) / total
        for scenario in result.scenarios
    ]
    return math.fsum(shares) / len(shares)


def bisect(world: dict[str, Any], target: float, beta: float) -> float:
    """Return the median at which the share falls to the target (it falls as the median rises)."""
    low, high = 30.0, 2000.0
    for _ in range(40):
        middle = (low + high) / 2
        if length_share(world, middle, beta) > target:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def best_single(worlds: dict[str, Any], beta: float) -> tuple[float, float, dict[str, float]]:
    """Return the median between the two single-target medians best on the worse recipe."""
    medians = [bisect(worlds[name], target, beta) for name, (_, target) in RECIPES.items()]
    # Each share falls as the median rises, so the best single median lies between the two.
    low, high = min(medians), max(medians)
    best: tuple[float, float, dict[str, float]] | None = None
    for step in range(SEARCH_STEPS + 1):
        median = low + (high - low) * step / SEARCH_STEPS
        shares = {n: length_share(w, median, beta) for n, w in worlds.items()}
        worst = max(abs(shares[n] - RECIPES[n][1]) for n in RECIPES)
        if best is None or worst < best[0]:
            best = (worst, median, shares)
    assert best is not None
    return best


def main() -> None:
    """Report each target's median, the best single median, and a spread that would serve."""
    worlds = {name: prepared(path) for name, (path, _) in RECIPES.items()}
    beta = tables.LINE_BETA
    for name, (_, target) in RECIPES.items():
        median = bisect(worlds[name], target, beta)
        others = {n: round(length_share(w, median, beta), 4) for n, w in worlds.items()}
        _say(f"beta {beta}: {name} target {target}: median {median:.4f}; shares {others}")
    worst = _report_best(worlds, beta)
    if worst <= TOLERANCE:
        return
    for candidate in BETAS[1:]:
        if _report_best(worlds, candidate) <= TOLERANCE:
            _say(f"smallest beta meeting both targets within 5 points: {candidate}")
            return
    _say("no beta up to the scan's end meets both targets within 5 points")


def _report_best(worlds: dict[str, Any], beta: float) -> float:
    worst, median, shares = best_single(worlds, beta)
    rounded = {n: round(v, 4) for n, v in shares.items()}
    within = "within" if worst <= TOLERANCE else "NOT within"
    _say(f"beta {beta}: best single median {median:.4f}: shares {rounded}")
    _say(f"    worst miss {worst:.4f}, {within} 5 points")
    return worst


def _say(line: str) -> None:
    print(line)  # noqa: T201 - the script's output is its report


if __name__ == "__main__":
    main()
