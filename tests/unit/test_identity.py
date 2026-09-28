"""Identity check (golden): the pilot recipe reproduces the checked-in bytes on every platform."""

import hashlib
from pathlib import Path

import pytest

from swm.cli import main

GOLDEN_FILES = (
    "resolved_recipe.yaml",
    "stream_record.yaml",
    "terrain_stats.yaml",
    "terrain_sha256.txt",
)


def recorded_hashes(golden_dir: Path) -> dict[str, str]:
    lines = (golden_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


@pytest.fixture(scope="module")
def produced(tmp_path_factory: pytest.TempPathFactory) -> Path:
    pilot = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"
    out_dir = tmp_path_factory.mktemp("identity")
    assert main(["resolve", str(pilot), "-o", str(out_dir)]) == 0
    assert main(["terrain", str(pilot), "-o", str(out_dir)]) == 0
    return out_dir


def test_golden_files_match_their_recorded_hashes(golden_dir: Path) -> None:
    hashes = recorded_hashes(golden_dir)
    assert set(hashes) == set(GOLDEN_FILES)
    for name in GOLDEN_FILES:
        assert hashlib.sha256((golden_dir / name).read_bytes()).hexdigest() == hashes[name]


@pytest.mark.parametrize("name", GOLDEN_FILES)
def test_pilot_reproduces_the_golden_file(name: str, produced: Path, golden_dir: Path) -> None:
    content = (produced / name).read_bytes()
    assert hashlib.sha256(content).hexdigest() == recorded_hashes(golden_dir)[name]
    assert content == (golden_dir / name).read_bytes()
