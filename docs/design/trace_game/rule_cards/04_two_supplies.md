<!-- Trace game rule card 04. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 4. More than one supply

## Front

**Within its own network** (a substation fed by two lines), a facility takes the **largest** supply arriving, up to full. Losing one line costs nothing if another still carries full supply.

**From another network,** supplies come in feed groups (on the card: single, two half, two full). Each group passes what its arrows pass; the groups add up, to at most full.
- **two half:** each feed covers half, so losing one leaves 0.5.
- **two full:** either feed covers it all, so losing one leaves 1.

**Value:** none

**Example:** B is fed two-half by suppliers S1 and S2. S1 goes out. B receives 0.5.

## Back

**Drill:** Substation B is fed within its network by lines from A1 and A2. The line from A1 fails; A2 is intact. What does B receive? Then: a pump fed two-full by two substations loses one of them. What does it receive?

**Answer:** B receives **1** (the largest supply arriving). The pump receives **1** (the other group covers it all).

## Drill world (for the engine test, not printed)

Power: A1 → B and A2 → B, both own-layer lines; damage the A1 line at hour 0. Expect B receives 1. Second case: S1 → P and S2 → P electricity, two_full; damage S1. Expect P receives 1.
