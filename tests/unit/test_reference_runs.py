"""Identity check (golden): the pilot's 8 reference runs reproduce the saved bytes (E2, F7).

Each run plays one storm scenario for 72 h with no actions and the default crew order. Its
files record every node's state, every stock's level, every crew's jobs, every repair and
delivery, the passes each step took and the hours out, stamped with the horizon, the policy
and the registry hash.
"""

import hashlib
from pathlib import Path

import pytest
import yaml

from swm.cli import main

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "pilot_reference_runs"
PILOT = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"
SCENARIOS = range(8)
SUFFIXES = (".yaml", "_states.csv", "_stocks.csv", "_crews.csv")
FILES = tuple(f"run_{n}{suffix}" for n in SCENARIOS for suffix in SUFFIXES)


def recorded_hashes() -> dict[str, str]:
    lines = (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


@pytest.fixture(scope="module")
def produced(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out_dir = tmp_path_factory.mktemp("reference_runs")
    assert main(["simulate", str(PILOT), "-o", str(out_dir)]) == 0
    return out_dir


def test_the_saved_runs_match_their_recorded_hashes() -> None:
    hashes = recorded_hashes()
    assert set(hashes) == set(FILES)
    for name in FILES:
        assert hashlib.sha256((GOLDEN / name).read_bytes()).hexdigest() == hashes[name]


@pytest.mark.parametrize("name", FILES)
def test_the_pilot_reproduces_each_reference_run(name: str, produced: Path) -> None:
    assert (produced / name).read_bytes() == (GOLDEN / name).read_bytes()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_each_run_is_stamped_with_its_horizon_policy_and_registry(scenario: int) -> None:
    record = yaml.safe_load((GOLDEN / f"run_{scenario}.yaml").read_text(encoding="utf-8"))
    assert record["scenario"] == scenario
    assert record["horizon_h"] == 72.0
    assert record["policy"] == "default crew order"
    assert record["actions"] == []
    assert record["modeling_rules"]["registry_sha256"]
    assert record["passes"]["capped_steps"] == []
