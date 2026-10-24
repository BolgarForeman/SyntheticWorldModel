<!-- Trace game rule card 08. Drafted by the design side, 2026-10-11; approved by Foreman, 2026-10-19 (REVIEW_LOG.md). {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 8. A crew's job

## Front

For each job a crew:
1. travels: by road at {rule:crews.road_speed_kmh} km/h, then off road at {rule:crews.offroad_speed_kmh} km/h to a line;
2. prepares on site for {rule:repair.crew_bound_lead_h} h (every job);
3. works. At slight or moderate damage the parts are on hand, so work starts after preparation. A heavier rebuild needs parts, which take their lead time from hour 0, with no crew. The job opens only when they arrive; then the crew travels, prepares and works.

A line is one job; its failure points are worked in turn, {rule:storm.line_crew_work_h} h each, or {rule:storm.tower_crew_work_h} h at a collapsed tower. A repaired element is back in full.

**Value:** preparation {rule:repair.crew_bound_lead_h} h; {rule:storm.line_crew_work_h} h per failure point; {rule:storm.tower_crew_work_h} h per tower

**Example:** A crew leaves at hour 0, travels 1.5 h, prepares 2 h, and repairs a line with one failure point in 6 h. The line is back at hour 9.5.

## Back

**Drill:** A crew is free at hour 0, 1 h from a facility being rebuilt. Its parts arrive at hour 5, and the crew work is 8 h. When is the facility back?

**Answer:** The job opens at hour 5. The crew arrives at 6, is prepared at 8, and works 8–16. Back at hour **16**.

## Drill world (for the engine test, not printed)

One crew; facility F being rebuilt, parts lead 5 h, crew work 8 h, travel 1 h. Expect F restored at 16 (before step rounding; see time card).
