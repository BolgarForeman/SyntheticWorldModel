"""Every search is timed first and held under one ceiling (ruling Q8).

Before a search starts, a fixed sample of its runs is played, through the same batch path as
the rest, and the full time projected and printed. A main search whose projection exceeds the
ceiling stops there and is reported; a rule of thumb that would push its request past the
ceiling is reported as not run. Times go to the console only, never into a key, so a key is the
same bytes on every machine.

Spec: structure v0.17 §5 (the instance bound); Work Order 10, B5.
"""

import os
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from swm.solve.runner import Job, Runner

SAMPLE_RUNS_PER_CORE = 100
"""CHOICE: a search's timed sample is a hundred runs per core (or the whole search, if smaller),
so the sample goes through the same pool as the search and the pool's start-up is a small part of
it."""
SECONDS_PER_HOUR = 3600.0


@dataclass
class Budget:
    """The time a request may spend, and how fast its runs go on this machine."""

    ceiling_h: float
    seconds_per_run: float = 0.0
    spent_runs: int = field(default=0)

    def search(self, runner: Runner, jobs: Sequence[Job], what: str) -> NDArray[np.float64] | None:
        """Time a sample of a search, project it, and play the rest if it fits the ceiling.

        Parameters
        ----------
        runner : Runner
            Plays the world.
        jobs : sequence of Job
            Every run of the search.
        what : str
            The search, as the console names it.

        Returns
        -------
        numpy.ndarray or None
            Every run's hours out, in order; None if the projection passes the ceiling.

        Spec: Work Order 10, B5.
        """
        size = min(len(jobs), SAMPLE_RUNS_PER_CORE * (os.cpu_count() or 1))
        start = time.perf_counter()
        sample = runner.rows(jobs[:size])
        self.seconds_per_run = (time.perf_counter() - start) / max(size, 1)
        if not self.allows(len(jobs), what):
            return None
        rest = runner.rows(jobs[size:]) if len(jobs) > size else sample[:0]
        return np.concatenate([sample, rest])

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
        sys.stdout.flush()
        if projected > self.ceiling_h:
            return False
        self.spent_runs += runs
        return True
