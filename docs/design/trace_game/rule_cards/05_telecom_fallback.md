<!-- Trace game rule card 05. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 5. When telecom is lost

## Front

Many facilities can work for a while without telecom, by phone, paper and hand. The card shows ⏳ **T** (hours of full function) and **d_eff** (the level afterwards).
- From the moment its telecom falls short, the facility runs fully for T hours.
- After that it runs at d_eff = 1 − κ(1 − d), where d is the level without any telecom and κ the share of its telecom that comes over the public network.
- When telecom returns, the facility returns to full.

After T hours of shortfall, counted in {rule:dynamics.step_min}-minute steps, the telecom the facility receives is raised to r + (1 − r) × d_eff, where r is the share that still arrives, and the facility's telecom response on its card acts on that level: throttle runs at it; trip runs fully only if it is at least the trip point ({rule:dynamics.trip_point}), and otherwise stops. The T-hour clock starts again from zero each time its telecom is fully back.

**Value:** T and d from the tolerance rules on each card

**Example:** Facility C, with T = 6 h and d_eff = 0.7, loses telecom at hour 0. It runs at 1 until hour 6, then at 0.7.

## Back

**Drill:** B loses telecom at hour 0. Its card shows T = 12 h and d_eff = 0.9. Telecom returns at hour 20. What is B's level at hours 6, 15 and 21?

**Answer:** **1** at hour 6; **0.9** at hour 15; **1** at hour 21.

## Drill world (for the engine test, not printed)

T → B communications, linear; B tolerance T 12 h, d 0.9, κ 1; damage T's supply so telecom is 0 from hour 0, restored at hour 20. Expect B 1 at 6, 0.9 at 15, 1 at 21.
