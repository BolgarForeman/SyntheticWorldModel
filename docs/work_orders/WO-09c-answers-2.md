# Work Order 9c: answers 2, PR 24 (apply on this branch before merge)

*2026-10-19 · ruled by Foreman (the author), option A · apply on `wo9c/close`, push to PR 24 · add to decision 0017 · spec now v0.16*

## Review

- F2, G1–G3: accepted. The engine matches the hand-trace fixture on every value; the fixture is untouched.
- The two test globs narrowed to recipes: accepted.

## The ruling: a hospital after its generator stops (rule card 2's open note)

The spec said a hospital on generator runs at its essential fraction, but not what it does once the generator stops. The engine treats it as a trip; card 2's draft said it runs at what arrives. Foreman ruled **option A, the engine as built**.

- **Rule:** once the generator stops (no fuel, or it fails to run), a hospital responds as a trip on the power that arrives: fully while it receives at least the trip point, otherwise out.
- **Registry and Theta List.** Record it as a dynamics entry, in the form of `dynamics.substation_crew_rank`:
  - id `dynamics.floor_after_generator_stops`;
  - chosen: "trip on what arrives";
  - alternatives: "throttle: runs at what arrives" (card 2's draft), and "the essential fraction while at least that share arrives, else out";
  - grade J, ruled by the author 2026-10-19, decision 0017.
- **Selection.** Naming an alternative stops the run, as for the other two dynamics entries.
- **Engine:** no change.
- **Card 2:** the design side has reworded the line and removed the CONFIRM note (committed on this branch; REVIEW_LOG updated). Remove `throttle_trip_floor` from `AWAITING_RULING`; no card should now print a CONFIRM note.
- **Spec v0.16** §4.5 carries the ruling (committed on this branch).

## Apply

1. The registry entry, as above.
2. The test change for card 2.
3. TRACE entry: replace the open card-2 departure with the ruling. Decision 0017: add the ruling. CHANGELOG 0.1.0: one line, and spec v0.16.
4. Regenerate the goldens. Expected: the registry stamp moves everywhere; card 2's printed text changes; no run, score or other file moves. Explain any other change, or stop.
5. Push, confirm CI green on both platforms, report.
