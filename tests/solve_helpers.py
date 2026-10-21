"""The pilot's solver inputs, built once per test session (each build plays every stage)."""

import functools
from pathlib import Path
from typing import Any

from swm.cli import solve_inputs
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve

PILOT = Path(__file__).resolve().parent / "fixtures" / "pilot_hand_check.yaml"


@functools.cache
def pilot_inputs() -> Any:
    """Return the pilot's ``SolveInputs``."""
    return solve_inputs(resolve(load_recipe(PILOT)))
