import numpy as np
import pytest

from swm.draws import DrawMethod, Levers, draw
from swm.rules.registry import load_registry

METHOD = DrawMethod.from_registry(load_registry())
SAMPLES = 40_000
TOLERANCE = 0.02
"""Realised median and spread must sit within 2% of the target at 40,000 draws."""


def realised(target: float, levers: Levers) -> np.ndarray:
    stream = np.random.default_rng(20260929)
    return np.array([draw(target, levers, METHOD, float(stream.random())) for _ in range(SAMPLES)])


@pytest.mark.parametrize(
    ("heterogeneity", "gap"), [(0.4, 0.0), (0.25, 0.2), (0.73, 0.0), (1.0, -0.5), (0.1, 0.5)]
)
def test_realised_median_and_spread_follow_the_levers(heterogeneity: float, gap: float) -> None:
    values = realised(10.0, Levers(heterogeneity, gap))
    assert float(np.median(values)) == pytest.approx(10.0 * (1 - gap), rel=TOLERANCE)
    assert float(values.std()) == pytest.approx(10.0 * heterogeneity, rel=TOLERANCE)


@pytest.mark.parametrize("spread", [0.05, 0.37, 1.24, 2.95])
def test_a_mixed_table_has_median_one_and_exactly_its_spread(spread: float) -> None:
    quantiles = METHOD.mixture(spread)
    assert quantiles[METHOD.knots.index(0.5)] == pytest.approx(1.0, abs=1e-12)
    mean, second = METHOD._moments(quantiles, quantiles)
    assert (second - mean * mean) ** 0.5 == pytest.approx(spread, abs=1e-9)


def test_zero_heterogeneity_puts_every_element_on_its_target() -> None:
    for u in (0.0, 0.3, 0.999):
        assert draw(7.5, Levers(0.0, 0.2), METHOD, u) == pytest.approx(6.0)


def test_values_are_positive_and_the_tails_are_clipped() -> None:
    values = realised(1.0, Levers(1.0, 0.0))
    top = METHOD.mixture(1.0)[-1]
    assert values.min() > 0
    assert values.max() <= top + 1e-12


def test_a_spread_beyond_the_tables_is_held_to_the_largest() -> None:
    levers = Levers(1.0, 0.9)
    assert levers.spread > METHOD.largest_spread
    assert METHOD.mixture(levers.spread) == METHOD.tables[-1].quantiles


def test_levers_read_the_recipe_percentages() -> None:
    levers = Levers.from_percent(40, 20)
    assert (levers.heterogeneity, levers.compliance_gap) == (0.4, 0.2)
    assert levers.spread == pytest.approx(0.5)
