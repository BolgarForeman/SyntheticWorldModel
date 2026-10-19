<!-- Trace game rule card 03. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 3. How supply passes along an arrow

## Front

Each arrow on the board has a form:
- **linear**: it passes κ (the *share*) × the supplier's level;
- **threshold**: it passes κ in full while the supplier is at or above θ (the *cut-off*), otherwise nothing.

κ is the share of the user's need that this supplier covers. Telecom arrows work differently: see card 5.

**Value:** threshold θ {rule:dynamics.threshold}

**Example:** A is at 0.8 and supplies B along a linear arrow with κ 0.5. B receives 0.4.

## Back

**Drill:** A is at 0.6 and supplies B along a threshold arrow with κ 1. What does B receive? What if A drops to 0.4?

**Answer:** At 0.6, **1** (A is at or above θ). At 0.4, **0**.

## Drill world (for the engine test, not printed)

A (own level set by a throttled supply of 0.6, then 0.4) → B fuel, κ 1, threshold. Expect B receives 1, then 0.
