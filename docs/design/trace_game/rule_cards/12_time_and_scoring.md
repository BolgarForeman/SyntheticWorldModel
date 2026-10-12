<!-- Trace game rule card 12. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 12. Time, steps and hours out

## Front

The model moves in steps of {rule:dynamics.step_min} minutes. Log every event at its exact time. Then note that the model applies it at the end of the step it falls in. [CONFIRM WITH ENGINE.]

**Hours out:** a facility at level s for h hours counts (1 − s) × h hours out. Only end-use facilities are scored; their weights are on their cards. The horizon is {rule:dynamics.horizon_h} h.

**Value:** step {rule:dynamics.step_min} min; horizon {rule:dynamics.horizon_h} h

**Example:** A repair finishes at hour 9.40. The model applies it at hour 9.50.

## Back

**Drill:** An end-use facility is out (level 0) from hour 0 to 6, then at 0.5 until hour 10, then fully back. How many hours out?

**Answer:** 6 × 1 + 4 × 0.5 = **8 hours out.**

## Drill world (for the engine test, not printed)

Constructed node with level 0 for 0–6 h, 0.5 for 6–10 h; expect 8 unweighted hours out.
