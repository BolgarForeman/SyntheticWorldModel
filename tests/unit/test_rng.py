import numpy as np
import pytest

from swm.rng import STREAM_REGISTRY, spawn_key, stable_id, stream, stream_record

# First 8 bytes of SHA-256, checked independently with sha256sum.
GOLDEN_STABLE_IDS = {
    "terrain": int("84088805e145b555", 16),
    "layers": int("e3b816898ca5ba5f", 16),
    "power": int("07d715edb696fb5f", 16),
    "errors": int("be4bd56772770471", 16),
    "osm_power": int("4820ed11f8831a76", 16),
}


@pytest.mark.parametrize(("name", "expected"), GOLDEN_STABLE_IDS.items())
def test_stable_id_is_fixed(name: str, expected: int) -> None:
    assert stable_id(name) == expected


def test_spawn_key_is_one_stable_id_per_segment() -> None:
    assert spawn_key("errors/osm_power") == (
        GOLDEN_STABLE_IDS["errors"],
        GOLDEN_STABLE_IDS["osm_power"],
    )


def test_terrain_seed_extends_terrain_keys_only() -> None:
    assert spawn_key("terrain/elevation", terrain_seed=7)[-1] == 7
    assert spawn_key("layers/power/siting", terrain_seed=7) == spawn_key("layers/power/siting")


def test_terrain_seed_moves_terrain_streams_and_nothing_else() -> None:
    def first(path: str, terrain_seed: int) -> int:
        return int(stream(91577, path, terrain_seed).bit_generator.random_raw())

    assert first("terrain/elevation", 0) != first("terrain/elevation", 1)
    assert first("layers/power/siting", 0) == first("layers/power/siting", 1)
    assert first("errors/osm_power", 0) == first("errors/osm_power", 1)


def test_same_path_and_seed_give_the_same_draws() -> None:
    a = stream(91577, "layers/water/links").integers(0, 1000, size=10)
    b = stream(91577, "layers/water/links").integers(0, 1000, size=10)
    np.testing.assert_array_equal(a, b)


def test_different_paths_give_different_streams() -> None:
    firsts = {int(stream(91577, path).bit_generator.random_raw()) for path in STREAM_REGISTRY}
    assert len(firsts) == len(STREAM_REGISTRY)


def test_generator_is_pcg64() -> None:
    assert isinstance(stream(1, "couplings/edges").bit_generator, np.random.PCG64)


def test_unregistered_path_is_refused() -> None:
    with pytest.raises(ValueError, match="not in the stream registry"):
        stream(1, "terrain/volcanoes")


@pytest.mark.parametrize("seed", [-1, 2**64])
def test_seed_out_of_range_is_refused(seed: int) -> None:
    with pytest.raises(ValueError, match="2\\*\\*64"):
        stream(seed, "couplings/edges")


def test_empty_segment_is_refused() -> None:
    with pytest.raises(ValueError, match="empty segment"):
        spawn_key("layers//siting")


def test_registry_covers_every_stage() -> None:
    roots = {path.split("/")[0] for path in STREAM_REGISTRY}
    assert roots == {"terrain", "layers", "couplings", "shared_causes", "unobserved", "errors"}
    assert all(purpose for purpose in STREAM_REGISTRY.values())


def test_stream_record_is_sorted_and_complete() -> None:
    record = stream_record(91577, terrain_seed=3)
    paths = [entry["path"] for entry in record["streams"]]
    assert paths == sorted(STREAM_REGISTRY)
    assert (record["root_seed"], record["terrain_seed"]) == (91577, 3)
    for entry in record["streams"]:
        assert len(entry["first_draws"]) == 4
        assert entry["spawn_key"] == list(spawn_key(entry["path"], 3))
