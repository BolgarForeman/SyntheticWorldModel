from hypothesis import given, settings
from hypothesis import strategies as st

from couplings_helpers import couple, rich_world, touched_by_two_way
from swm.recipe.dependencies import Role
from swm.recipe.schema import Layer
from swm.stages import couplings as stage
from swm.stages.couplings import FeedConfiguration

shares = (
    st.tuples(st.integers(0, 100), st.integers(0, 100))
    .filter(lambda pair: pair[0] + pair[1] <= 100)
    .map(lambda pair: (pair[0], pair[1], 100 - pair[0] - pair[1]))
)


@settings(max_examples=25, deadline=None)
@given(count=st.integers(0, 60), mix=shares)
def test_largest_remainder_counts_total_the_count_and_stay_within_one(
    count: int, mix: tuple[int, int, int]
) -> None:
    counts = stage._largest_remainder(count, mix)
    assert sum(counts) == count
    for realised, share in zip(counts, mix, strict=True):
        assert abs(realised - count * share / 100) < 1


@settings(max_examples=10, deadline=None)
@given(mix=shares, density=st.integers(0, 100))
def test_any_feed_mix_is_realised_by_largest_remainder(
    mix: tuple[int, int, int], density: int
) -> None:
    feed_mix = dict(zip(("single_feed_pct", "two_full_feeds_pct", "two_half_feeds_pct"), mix,
                        strict=True))  # fmt: skip
    result = couple(rich_world(), feed_mix=feed_mix, density=density, two_way_pct=100)
    touched = touched_by_two_way(result)
    for stats in result.pairs:
        if stats.supplier == Layer.TRANSPORT:
            continue
        mixed = [
            d
            for d in result.dependencies
            if (d.supplier_layer, d.consumer_layer) == (stats.supplier, stats.consumer)
            and d.role == Role.PRIMARY_SUPPLY
            and not d.row_key.startswith("power>tertiary")
        ]
        if any(d.notes or d.dependency_id in touched for d in mixed):
            continue
        realised = [
            sum(d.feed_configuration == c for d in mixed)
            for c in (FeedConfiguration.SINGLE, FeedConfiguration.TWO_FULL,
                      FeedConfiguration.TWO_HALF)
        ]  # fmt: skip
        assert realised == stage._largest_remainder(len(mixed), mix)
