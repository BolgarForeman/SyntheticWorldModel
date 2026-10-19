# Work Order 9g: answers 2, crew travel along a line (apply on this branch before merge)

*2026-10-19 · ruled by Foreman (the author) · apply on `wo9g/trace-game`, push to PR 19 · add to decision 0017 · spec now v0.14*

## Why

The design side's sealed hand trace of scenario 7 has been compared with the engine (`docs/design/evidence/Hand_Trace_Comparison_Scenario_7_v0_1.md`).
- **Agreement:** every point, except how a crew travels from one failure point to the next. The spec never said.
- **The engine's rule:** walk back to the nearest road, drive, walk back in. That takes 6.7 h for 2 km between two breaks on the same telecom line.
- **Foreman ruled option C.**

## The ruling (spec v0.14 §4.5)

- **Between failure points of the same line:** the crew walks along the line, the distance between the two points along the line, at `crews.offroad_speed_kmh`. No new preparation.
- **Between different jobs:** as now. Walk or drive to the nearest road, drive, walk or drive back in.
- **Registry and Theta List.** Record the rule as a dynamics entry:
  - chosen: "along the line within a job; via the road between jobs";
  - alternatives: "always via the road" (the engine's earlier rule) and "whichever way is shorter";
  - grade J, ruled 2026-10-19.
- **Selection.** Naming an alternative stops the run, as for `dynamics.substation_crew_rank`.

## Apply

1. **Engine:** change the trip between failure points of one line to the ruled rule.
2. **Card 10:** the design side has updated the wording and the drill's printed answer (now 18.8 h). Update the drill world's expectation so the engine checks it.
3. **Reference runs.** Rerun all 8 and report every change with its reason. Scenario 7 is now unsealed, so report its numbers in full. The design side's trace, recomputed under this rule, expects:
   - TEL-L0002 done at 17.999 h; TEL-0003 back at **18.00 h**;
   - crew 2 to TEL-L0001 via the road (8.245 h), prepared 2 h, work 6 h, so TEL-L0001 done at 34.244 h; TEL-0002 back at **34.25 h**;
   - total **52.25** weighted service-hours lost (masts, weight 1).

   If the engine gives anything else, report it and stop; don't adjust to match.
4. **Goldens:** regenerate them, including the trace-game answer pack. Explain every change.

Then push to PR 19 with the final-pass items (no DRAFT marking, the card 2 floor check), and report in §11 format.
