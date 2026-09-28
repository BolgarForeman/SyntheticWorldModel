from hypothesis import given
from hypothesis import strategies as st

from swm.rng import stream, stream_record

segment = st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=8)
path = st.lists(segment, min_size=1, max_size=3).map("/".join)
seed = st.integers(min_value=0, max_value=2**64 - 1)


@given(existing=st.sets(path, min_size=1, max_size=6), added=path, root_seed=seed)
def test_adding_a_path_never_moves_an_existing_stream(
    existing: set[str], added: str, root_seed: int
) -> None:
    before = {
        entry["path"]: entry
        for entry in stream_record(root_seed, 0, dict.fromkeys(existing, ""))["streams"]
    }
    registry = dict.fromkeys(existing | {added}, "")
    after = {entry["path"]: entry for entry in stream_record(root_seed, 0, registry)["streams"]}
    for name, entry in before.items():
        assert after[name] == entry


@given(name=path, root_seed=seed)
def test_same_path_and_seed_always_give_the_same_draws(name: str, root_seed: int) -> None:
    registry = {name: ""}
    first = stream(root_seed, name, registry=registry).bit_generator.random_raw(4)
    second = stream(root_seed, name, registry=registry).bit_generator.random_raw(4)
    assert list(first) == list(second)


@given(names=st.sets(path, min_size=2, max_size=2), root_seed=seed)
def test_different_paths_give_different_draws(names: set[str], root_seed: int) -> None:
    registry = dict.fromkeys(names, "")
    draws = [
        tuple(stream(root_seed, name, registry=registry).bit_generator.random_raw(4))
        for name in sorted(names)
    ]
    assert draws[0] != draws[1]
