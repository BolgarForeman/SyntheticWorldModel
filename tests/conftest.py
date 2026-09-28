from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent


@pytest.fixture
def pilot_path() -> Path:
    return TESTS / "fixtures" / "pilot_hand_check.yaml"


@pytest.fixture
def golden_dir() -> Path:
    return TESTS / "golden" / "pilot_hand_check"
