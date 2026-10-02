"""Spawn tree: every random stream the generator uses, fixed by name off the root seed."""

import hashlib
from collections.abc import Mapping
from typing import TypedDict

import numpy as np

from swm.recipe.schema import DEFAULT_COUPLINGS, MAX_SCENARIOS, Hazard, Layer, Source

STABLE_ID_BYTES = 8
"""Bytes of the SHA-256 digest kept by ``stable_id`` (Work Order 1, item 1)."""

SEED_UPPER_BOUND = 2**64
"""Seeds lie in ``0 <= seed < 2**64`` (ruling C4, decision 0003)."""

RECORD_DRAW_COUNT = 4
"""Raw 64-bit draws kept per stream in the stream record (Work Order 1, item 1)."""

TERRAIN_ROOT = "terrain"
"""Top-level path segment whose streams also take the terrain seed (ruling A1, decision 0003)."""


def _registry() -> dict[str, str]:
    paths = {
        "terrain/elevation": "Elevation, including the mountain spine.",
        "terrain/coastline": "Coastline and outlying islands.",
        "terrain/drainage": "Rivers and drainage.",
        "terrain/land_cover": "Land cover: forest, wetland, aridity.",
        "terrain/urban_extents": "Urban extents used for siting.",
        "layers/dual_membership": "Which assets belong to two layers.",
    }
    for layer in Layer:
        paths[f"layers/{layer}/siting"] = f"Siting and node classes of {layer} nodes."
        paths[f"layers/{layer}/attributes"] = f"Observed attributes of {layer} nodes."
        paths[f"layers/{layer}/links"] = f"Intra-layer links of the {layer} layer."
        paths[f"layers/{layer}/overlap"] = f"Which {layer} assets appear in more than one source."
        paths[f"layers/{layer}/subtype"] = f"Subtype attributes of {layer} nodes (unobserved)."
    paths |= {
        "unobserved/links_on_nodes_only_layers": "Links on layers whose sources report nodes only.",
    }
    for layer in Layer:
        paths[f"requirements/{layer}"] = f"Requirements of {layer} nodes, per commodity."
        paths[f"reserves/{layer}"] = f"Reserves of {layer} nodes, in hours around their targets."
        paths[f"availability/{layer}"] = f"Backup generator availability at {layer} nodes."
        paths[f"failure_mode/{layer}"] = f"Which {layer} failure modes depart from the default."
        paths[f"repair/{layer}"] = f"Repair rates of {layer} nodes, one draw per node."
    paths |= _coupling_paths()
    for hazard in Hazard:
        if hazard != Hazard.STORM_CORRIDOR:
            paths[f"shared_causes/{hazard}/field"] = f"Latent {hazard} field with distance decay."
    paths |= _storm_paths()
    for source in Source:
        paths[f"errors/{source}"] = f"Error induction on the {source} source."
    return paths


COUPLING_PURPOSES: Mapping[str, str] = {
    "density": "Which optional dependencies are taken",
    "feed_configuration": "Which dependencies are fed single, two full or two half",
    "hub": "The hub supplier",
    "concentration": "Which dependencies the hub carries",
    "supplier_not_nearest": "Which dependencies take a supplier other than the nearest",
}
"""Per-pair coupling streams, so switching one pair never moves another (Work Order 4, E2)."""


def pair_label(supplier: Layer, consumer: Layer) -> str:
    """Return a coupling pair's path segment, such as ``power-telecom``.

    Parameters
    ----------
    supplier : Layer
        The supplier layer.
    consumer : Layer
        The consumer layer.

    Returns
    -------
    str
        The segment.

    Spec: Work Order 4, E2.
    """
    return f"{supplier}-{consumer}"


def mutual_couples() -> tuple[tuple[Layer, Layer], ...]:
    """Return each modeled pair whose reverse is also modeled, earlier of the two first.

    Returns
    -------
    tuple of (Layer, Layer)
        One entry per couple of layers that can depend on each other, in the order of the 21.

    Spec: structure v0.5 §4.3 (two-way); Work Order 4, E9.
    """
    pairs = list(DEFAULT_COUPLINGS)
    return tuple(
        (supplier, consumer)
        for index, (supplier, consumer) in enumerate(pairs)
        if (consumer, supplier) in pairs[index + 1 :]
    )


def _coupling_paths() -> dict[str, str]:
    paths = {}
    for supplier, consumer in DEFAULT_COUPLINGS:
        label = pair_label(supplier, consumer)
        for purpose, description in COUPLING_PURPOSES.items():
            paths[f"couplings/{purpose}/{label}"] = f"{description}: {supplier} to {consumer}."
    paths["couplings/tertiary_second_feed/power-healthcare"] = (
        "Which tertiary hospitals take a second distribution substation (§4.3a rule 5)."
    )
    for supplier, consumer in mutual_couples():
        paths[f"couplings/two_way/{pair_label(supplier, consumer)}"] = (
            f"Which node pairs of {supplier} and {consumer} depend on each other."
        )
    return paths


def _storm_paths() -> dict[str, str]:
    """Each scenario's own storm streams, so a scenario count never moves another scenario."""
    paths = {}
    for index in range(MAX_SCENARIOS):
        base = f"shared_causes/{Hazard.STORM_CORRIDOR}/{index}"
        paths[f"{base}/track"] = f"Storm track and peak wind of scenario {index}."
        paths[f"{base}/variation"] = f"Random variation of the wind field in scenario {index}."
        paths[f"{base}/damage"] = f"Overhead-line failures given the field in scenario {index}."
    return paths


STREAM_REGISTRY: Mapping[str, str] = _registry()
"""Every stream path the generator uses, with its purpose. Spec: structure v0.2 §3, §4."""


class StreamRecordEntry(TypedDict):
    """One stream in the stream record."""

    path: str
    spawn_key: list[int]
    first_draws: list[int]


class StreamRecord(TypedDict):
    """The spawn tree as the identity check compares it."""

    root_seed: int
    terrain_seed: int
    streams: list[StreamRecordEntry]


def stable_id(name: str) -> int:
    """Return a fixed integer for a stream-path segment.

    Parameters
    ----------
    name : str
        One segment of a stream path.

    Returns
    -------
    int
        The first 8 bytes of SHA-256 of the UTF-8 name, as a big-endian unsigned integer.

    Spec: CLAUDE.md §4; Work Order 1, item 1.
    """
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:STABLE_ID_BYTES], "big")


def spawn_key(path: str, terrain_seed: int = 0) -> tuple[int, ...]:
    """Return the spawn key for a stream path.

    Parameters
    ----------
    path : str
        Slash-separated hierarchical stream path, such as ``"layers/power/siting"``.
    terrain_seed : int
        The recipe's terrain seed. Appended to the key of ``terrain/*`` paths only.

    Returns
    -------
    tuple of int
        ``stable_id`` of each path segment, then the terrain seed for terrain paths.

    Spec: CLAUDE.md §4; Work Order 1, item 1; ruling A1 (decision 0003).
    """
    parts = path.split("/")
    if any(part == "" for part in parts):
        raise ValueError(f"stream path {path!r} has an empty segment")
    _check_seed("terrain_seed", terrain_seed)
    key = tuple(stable_id(part) for part in parts)
    if parts[0] == TERRAIN_ROOT:
        return (*key, terrain_seed)
    return key


def stream(
    root_seed: int,
    path: str,
    terrain_seed: int = 0,
    registry: Mapping[str, str] = STREAM_REGISTRY,
) -> np.random.Generator:
    """Return the random stream for a registered path.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed, ``0 <= root_seed < 2**64``.
    path : str
        A path in ``registry``.
    terrain_seed : int
        The recipe's terrain seed; used by ``terrain/*`` paths only.
    registry : Mapping[str, str]
        The registered stream paths. Unregistered paths are refused so every stream is recorded.

    Returns
    -------
    numpy.random.Generator
        A PCG64 generator seeded by ``SeedSequence(root_seed, spawn_key=spawn_key(path))``.

    Spec: CLAUDE.md §4; Work Order 1, item 1.
    """
    if path not in registry:
        raise ValueError(f"stream path {path!r} is not in the stream registry")
    _check_seed("root_seed", root_seed)
    sequence = np.random.SeedSequence(root_seed, spawn_key=spawn_key(path, terrain_seed))
    return np.random.Generator(np.random.PCG64(sequence))


def stream_record(
    root_seed: int,
    terrain_seed: int = 0,
    registry: Mapping[str, str] = STREAM_REGISTRY,
) -> StreamRecord:
    """Return every registered stream's spawn key and first raw draws, sorted by path.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.
    terrain_seed : int
        The recipe's terrain seed.
    registry : Mapping[str, str]
        The registered stream paths.

    Returns
    -------
    StreamRecord
        The seeds and, per path, its spawn key and its first four raw 64-bit outputs.

    Spec: CLAUDE.md §7 (identity check); Work Order 1, item 1.
    """
    entries: list[StreamRecordEntry] = []
    for path in sorted(registry):
        generator = stream(root_seed, path, terrain_seed, registry)
        # Raw bit-generator output does not depend on numpy's sampling algorithms.
        draws = generator.bit_generator.random_raw(RECORD_DRAW_COUNT)
        entries.append(
            {
                "path": path,
                "spawn_key": list(spawn_key(path, terrain_seed)),
                "first_draws": [int(value) for value in draws],
            }
        )
    return {"root_seed": root_seed, "terrain_seed": terrain_seed, "streams": entries}


def _check_seed(name: str, value: int) -> None:
    if not 0 <= value < SEED_UPPER_BOUND:
        raise ValueError(f"{name} must satisfy 0 <= {name} < 2**64, got {value}")
