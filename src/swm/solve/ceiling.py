"""Every search is timed first and held under one ceiling (ruling Q8).

Before a search starts, a fixed sample is run and the full time projected and printed. A main
search whose projection exceeds the ceiling stops before starting and is reported; a rule of
thumb that would push its request past the ceiling is reported as not run. Times go to the
console only, never into a key, so a key is the same bytes on every machine.

Spec: structure v0.17 §5 (the instance bound); Work Order 10, B5.
"""

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field

SAMPLE_RUNS = 2
"""CHOICE: runs timed before a search starts; the engine's time per run barely varies within
one world, so a small sample projects well."""
SECONDS_PER_HOUR = 3600.0


@dataclass
class Budget:
    """The time a request may spend, and how fast its runs go on this machine."""

    ceiling_h: float
    seconds_per_run: float = 0.0
    spent_runs: int = field(default=0)

    def time_sample(self, run: Callable[[], object]) -> None:
        """Time the fixed sample of runs, to project the rest."""
        start = time.perf_counter()
        for _ in range(SAMPLE_RUNS):
            run()
        self.seconds_per_run = (time.perf_counter() - start) / SAMPLE_RUNS

    def projected_h(self, runs: int) -> float:
        """Return the hours a number of runs would take on this machine."""
        return runs * self.seconds_per_run / SECONDS_PER_HOUR

    def allows(self, runs: int, what: str) -> bool:
        """Print a search's projection; return whether it fits under the ceiling with the rest.

        Parameters
        ----------
        runs : int
            The runs the search needs.
        what : str
            The search, as the console names it.

        Returns
        -------
        bool
            True if the runs already spent plus these stay within the ceiling; they are then
            counted as spent.

        Spec: Work Order 10, B5.
        """
        projected = self.projected_h(self.spent_runs + runs)
        sys.stdout.write(
            f"{what}: {runs} runs, projected {self.projected_h(runs):.4f} h "
            f"({projected:.4f} h for the request so far; ceiling {self.ceiling_h:g} h)\n"
        )
        if projected > self.ceiling_h:
            return False
        self.spent_runs += runs
        return True
