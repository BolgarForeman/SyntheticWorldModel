import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from swm.recipe.schema import FeedMix

share = st.integers(min_value=0, max_value=100)


@given(single=share, full=share, half=share)
def test_feed_mix_is_accepted_only_when_the_shares_total_100(
    single: int, full: int, half: int
) -> None:
    fields = {"single_feed_pct": single, "two_full_feeds_pct": full, "two_half_feeds_pct": half}
    if single + full + half == 100:
        mix = FeedMix(**fields)
        assert mix.single_feed_pct + mix.two_full_feeds_pct + mix.two_half_feeds_pct == 100
    else:
        with pytest.raises(ValidationError, match="must total exactly 100"):
            FeedMix(**fields)
