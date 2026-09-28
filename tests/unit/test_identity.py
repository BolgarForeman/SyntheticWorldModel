"""Identity check (golden): the pilot recipe resolves to the checked-in bytes on every platform."""

import hashlib
from pathlib import Path

from swm.recipe.io import canonical_yaml, load_recipe, recipe_bytes
from swm.recipe.resolve import resolve
from swm.rng import stream_record

GOLDEN_FILES = ("resolved_recipe.yaml", "stream_record.yaml")


def recorded_hashes(golden_dir: Path) -> dict[str, str]:
    lines = (golden_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


def test_golden_files_match_their_recorded_hashes(golden_dir: Path) -> None:
    hashes = recorded_hashes(golden_dir)
    assert set(hashes) == set(GOLDEN_FILES)
    for name in GOLDEN_FILES:
        assert hashlib.sha256((golden_dir / name).read_bytes()).hexdigest() == hashes[name]


def test_pilot_reproduces_the_golden_resolved_recipe(pilot_path: Path, golden_dir: Path) -> None:
    recipe = resolve(load_recipe(pilot_path)).recipe
    produced = recipe_bytes(recipe)
    assert hashlib.sha256(produced).hexdigest() == recorded_hashes(golden_dir)[GOLDEN_FILES[0]]
    assert produced == (golden_dir / GOLDEN_FILES[0]).read_bytes()


def test_pilot_reproduces_the_golden_stream_record(pilot_path: Path, golden_dir: Path) -> None:
    recipe = resolve(load_recipe(pilot_path)).recipe
    produced = canonical_yaml(stream_record(recipe.root_seed, recipe.terrain.terrain_seed))
    assert hashlib.sha256(produced).hexdigest() == recorded_hashes(golden_dir)[GOLDEN_FILES[1]]
    assert produced == (golden_dir / GOLDEN_FILES[1]).read_bytes()
