import os
from pathlib import Path

import pytest
from hypothesis import settings

# Issue #21: a property test must pass or fail the same way on every CI run. The "ci" profile
# derandomizes Hypothesis (examples are fixed by each test's code) and keeps no example
# database; GitHub Actions sets CI. Locally, HYPOTHESIS_PROFILE=ci reproduces a CI run.
settings.register_profile("ci", derandomize=True, database=None, print_blob=True)
settings.load_profile(
    os.environ.get("HYPOTHESIS_PROFILE", "ci" if os.environ.get("CI") else "default")
)

TESTS = Path(__file__).resolve().parent


@pytest.fixture
def pilot_path() -> Path:
    return TESTS / "fixtures" / "pilot_hand_check.yaml"


@pytest.fixture
def golden_dir() -> Path:
    return TESTS / "golden" / "pilot_hand_check"
