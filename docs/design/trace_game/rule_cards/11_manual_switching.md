<!-- Trace game rule card 11. Drafted by the design side, 2026-10-11; approved by Foreman, 2026-10-19 (REVIEW_LOG.md). {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 11. Re-energizing by hand

## Front

Substations are switched remotely over telecom. If a repair should bring power back to a substation whose telecom is down, the power stays off until a crew travels there and switches it by hand: {rule:repair.manual_switching_h} h on site. The trip is a job like any other, at the same priority as the repair that triggered it. It is not needed when the repair is at the substation itself.

**Value:** {rule:repair.manual_switching_h} h on site

**Example:** A line into substation S is repaired at hour 10, but S's telecom is out. A crew 0.5 h away goes there; power returns at hour 11.5.

## Back

**Drill:** The only line into substation S is repaired at hour 20. S's telecom is working. When does S get power back? And if S's telecom were down, with a free crew 1 h away?

**Answer:** With telecom working: hour **20**. With telecom down: hour **22** (20 + 1 h travel + {rule:repair.manual_switching_h} h on site).

## Drill world (for the engine test, not printed)

Line L → substation S, damaged, restored at 20 by crew 1; case 2: S's telecom supplier damaged throughout; crew 2 free, 1 h from S. Expect S re-energized at 20, then at 22.
