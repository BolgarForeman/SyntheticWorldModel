<!-- Trace game rule card 05. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 5. When telecom is lost

## Front

Facilities can work for a while without telecom, by phone, paper and hand. Each card shows ⏳ **T** (hours of full function) and **d_eff** (the level the missing telecom counts as afterwards).
- Telecom arrows pass the supplier's level without κ. On a telecom arrow, κ is the share of the facility's telecom that runs over the public network; it is built into d_eff = 1 − κ(1 − d).
- When telecom falls short, the facility runs fully for **T** hours.
- After T hours, the telecom it receives counts as **r + (1 − r) × d_eff**, where r is the share still arriving. Its telecom response then acts on that: **throttle** runs at it; **trip** runs only if it is at least the trip point ({rule:dynamics.trip_point}), and otherwise stops.
- The T-hour clock starts again from zero each time telecom is fully back.

**Value:** T, d and κ from each facility's card

**Example:** C loses all telecom at hour 0; T = 6 h, d_eff = 0.7. If C throttles on telecom, it runs at 1 until hour 6, then at 0.7. If C trips on telecom, it runs at 1 until hour 6, then stops (0.7 is below the trip point).

## Back

**Drill:** B throttles on telecom and loses it at hour 0. Its card shows T = 12 h and d_eff = 0.9. Telecom returns at hour 20. What is B's level at hours 6, 15 and 21?

**Answer:** **1** at hour 6; **0.9** at hour 15; **1** at hour 21.

## Drill world (for the engine test, not printed)

T → B communications, linear; B tolerance T 12 h, d 0.9, κ 1; damage T's supply so telecom is 0 from hour 0, restored at hour 20. Expect B 1 at 6, 0.9 at 15, 1 at 21.
