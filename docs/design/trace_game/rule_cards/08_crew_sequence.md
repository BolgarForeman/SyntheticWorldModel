<!-- Trace game rule card 08. Drafted by the design side, 2026-10-11; approved by Foreman, 2026-10-19 (REVIEW_LOG.md). {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 8. A crew's job

## Front

For each job a crew:
1. travels: by road at {rule:crews.road_speed_kmh} km/h, then off road at {rule:crews.offroad_speed_kmh} km/h to a line;
2. prepares on site for {rule:repair.crew_bound_lead_h} h (every job);
3. repairs once the parts are in. Parts lead time runs from hour 0, in parallel, with no crew.

A line is one job; its failure points are worked in turn, {rule:storm.line_crew_work_h} h each, or {rule:storm.tower_crew_work_h} h at a collapsed tower. A repaired element is back in full.

**Value:** preparation {rule:repair.crew_bound_lead_h} h; {rule:storm.line_crew_work_h} h per failure point; {rule:storm.tower_crew_work_h} h per tower

**Example:** A crew leaves at hour 0, travels 1.5 h, prepares 2 h, and repairs a line with one failure point in 6 h. The line is back at hour 9.5.

## Back

**Drill:** A crew is assigned at hour 0 to a facility 1 h away. Its parts lead time is 5 h and the crew work is 8 h. When is the facility back?

**Answer:** Arrives at hour 1, prepared at hour 3, parts in at hour 5, so work runs 5–13. Back at hour **13**.

## Drill world (for the engine test, not printed)

One crew; facility F damaged, parts lead 5 h, crew work 8 h, travel 1 h. Expect F restored at 13 (before step rounding; see time card).
