<!-- Trace game rule card 12. Drafted by the design side, 2026-10-11; approved by Foreman, 2026-10-19 (REVIEW_LOG.md). {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 12. Time, steps and hours out

## Front

The model moves in steps of {rule:dynamics.step_min} minutes. Log every event at its exact time. A repair, a switching trip or a fuel delivery takes effect at the first step boundary at or after its exact time: one finished at hour 9.40 counts from 9.50; one finished at exactly 9.50 counts from 9.50. Crews are not rounded: a crew starts its next trip the moment it finishes. A facility's level holds for the whole step it is set in.

**Hours out:** a facility at level s for h hours counts (1 − s) × h hours out. Only end-use facilities are scored; their weights are on their cards. The horizon is {rule:dynamics.horizon_h} h.

**Value:** step {rule:dynamics.step_min} min; horizon {rule:dynamics.horizon_h} h

**Example:** A repair finishes at hour 9.40. The model applies it at hour 9.50.

## Back

**Drill:** An end-use facility is out (level 0) from hour 0 to 6, then at 0.5 until hour 10, then fully back. How many hours out?

**Answer:** 6 × 1 + 4 × 0.5 = **8 hours out.**

## Drill world (for the engine test, not printed)

Constructed node with level 0 for 0–6 h, 0.5 for 6–10 h; expect 8 unweighted hours out.
