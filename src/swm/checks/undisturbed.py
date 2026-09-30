"""The undisturbed-supply world check: before any disruption, every consumer is fully supplied.

A world that fails it is reported, and the build stops; it is never silently regenerated.

Spec: structure v0.6 §4.4 (world check); Work Order 5, E2; ruling T10 (decision 0009).
"""

from dataclasses import dataclass

from swm.stages.strength import StrengthResult, SupplyRatio

TOLERANCE = 1e-9
"""Rounding allowance on R_φ ≥ 1."""


@dataclass(frozen=True)
class CheckResult:
    """The check's verdict and every shortfall."""

    passed: bool
    shortfalls: tuple[SupplyRatio, ...]

    def report(self) -> str:
        """Return the verdict and one line per short consumer and commodity."""
        if self.passed:
            return "undisturbed supply: every consumer is fully supplied\n"
        lines = [f"undisturbed supply: {len(self.shortfalls)} shortfalls"]
        lines += [
            f"  {s.consumer_id} {s.supplier_layer.value}: R = {s.uncapped:.4f} ({s.dependency_id})"
            for s in self.shortfalls
        ]
        return "\n".join(lines) + "\n"


def undisturbed_supply_check(strength: StrengthResult) -> CheckResult:
    """Check that every consumer has R_φ ≥ 1 for every commodity in the undisturbed world.

    Parameters
    ----------
    strength : StrengthResult
        The strength stage's output.

    Returns
    -------
    CheckResult
        Passed, or the consumers and commodities that fall short.

    Spec: structure v0.6 §4.4; Work Order 5, E2.
    """
    short = tuple(r for r in strength.ratios if r.uncapped < 1.0 - TOLERANCE)
    return CheckResult(not short, short)
