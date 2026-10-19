<!-- Trace game rule card 10. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 10. Travel between jobs

## Front

A crew that finishes a job goes straight to its next job from where it stands. It does not return to base.

A crew's next trip starts where it stands: between a facility and the nearest road it drives, between a point on a line and the nearest road it walks at {rule:crews.offroad_speed_kmh} km/h, and in between it drives the roads at {rule:crews.road_speed_kmh} km/h; if no road joins the two places, it crosses straight at road speed and adds {rule:crews.outlying_island_mobilisation_h} h. Preparation ({rule:repair.crew_bound_lead_h} h) comes once per job, at its first site: a crew working a line's failure points in turn walks off, drives and walks back on between them without preparing again.

**Value:** road {rule:crews.road_speed_kmh} km/h; off road {rule:crews.offroad_speed_kmh} km/h

**Example:** A crew finishes a job at a facility on the road at hour 5. Its next job is a line whose first failure point lies 4 km farther along the road and 1 km off it. The crew drives 4 km (0.1 h), walks 1 km (0.5 h), arrives at hour 5.6, prepares until hour 7.6, and starts the work.

## Back

**Drill:** One crew sets out from the base, on a straight road. Facility B, on the road 8 km east, needs 1 h of work. Line L has two failure points, each 1 km off the road, at 12 km and 14 km east, each needing {rule:storm.line_crew_work_h} h. Both jobs are in the same priority group. When does the crew finish line L?

**Answer:** B first, the shorter trip: done at hour 3.2. To L's first point: 4 km by road and 1 km on foot, 0.6 h, so there at 3.8; prepared at 5.8; done at 11.8. To the second point: 1 km off, 2 km by road, 1 km back on, 1.05 h, so there at 12.85; no new preparation; done at **18.85**.

## Drill world (for the engine test, not printed)

One crew at the base, on a straight road along y = 0. B, a clinic on the road 8 km east, 1 h of work. Line L down, with failure points 1 km north of the road at 12 km and 14 km east, {rule:storm.line_crew_work_h} h each. The drill's leg finder follows the engine's road rule: a facility's access to the road is driven, a line point's is walked. Expect line L done at 18.85 (exact, before step rounding).
