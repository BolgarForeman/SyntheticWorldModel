# 0017 — Phase 1 close: the trace game and its rulings

- **Date:** opened 2026-10-19; completed with PR 9c
- **Decided by:** the author (Foreman)
- **Recorded by:** Work Order 9 (PRs 9a, 9g, 9b, 9c). Further entries are added as each is ruled.

## Crew order among distribution substations (WO-09g answers, answer 1; structure v0.13 §4.5)

**Context.** Rule card 9 printed that the crew takes the substation feeding the hospital first. The engine ranked a distribution substation by its own Lifeline weight, which every distribution substation shares, so the nearer one went first.

**Decision.**
- **The ranking.** In group 2 of the default crew order, a distribution substation ranks by the highest Lifeline weight among the end uses it supplies, its own weight included. Ties go to the shortest trip, then the lowest id. Power feeds to end uses keep their key.
- **"Supplies."** It means the electricity couplings to end-use nodes that the engine plays, both switched on and hidden.
- **Registry.** The ranking is recorded as `dynamics.substation_crew_rank`: chosen "highest supplied weight"; alternatives "own weight only" and "sum of supplied weights"; grade J; ruled 2026-10-19. It appears in the Theta List.
- **Alternatives.** The engine reads the rule. The two alternatives are recorded, not yet selectable; naming one stops the run with a message.
- **Later.** Foreman's standing requirement: each dynamics rule with recorded alternatives becomes a recipe setting and an interface choice, built with the answer-key solver (Phase 2) or the interface (Phase 7), whichever comes first.

**Effect.** The 8 pilot reference runs are unchanged apart from the registry stamp. No pilot scenario gives a crew a distribution-substation job: every job is a line or a power feed. Rule card 9's printed answer now holds, and its drill checks the engine.

## Crew travel along a line (WO-09g answers 2; structure v0.14 §4.5)

**Context.** The design side's sealed hand trace of scenario 7 agreed with the engine everywhere except one point: how a crew travels from one failure point of a line to the next. The spec never said. The engine walked back to the nearest road, drove, and walked back in, which took 6.7 h for 2 km between two breaks on the same telecom line.

**Decision (option C).**
- **Between failure points of the same line:** the crew walks along the line, the distance between the two points, at the off-road speed, with no new preparation.
- **Between different jobs:** as before, via the road.
- **Registry.** The rule is recorded as `dynamics.line_point_travel`: chosen "along the line within a job; via the road between jobs"; alternatives "always via the road" and "whichever way is shorter"; grade J; ruled 2026-10-19.
- **Alternatives.** As for the substation ranking, an alternative named in the registry stops the run.

**Effect.** Only scenario 7 has a line job with more than one failure point, so only its run changes:
- TEL-L0002 done at 17.9986 h; TEL-0003 back at 18.00 h;
- crew 2 travels 8.245 h to TEL-L0001, which is done at 34.2437 h; TEL-0002 back at 34.25 h;
- 52.25 weighted service-hours lost.

This matches the design side's recomputed trace on every point. Rule card 10's drill now answers 18.8 h.

## Teaching text approved (REVIEW_LOG.md)

Foreman approved all twelve rule cards, the field manual and the debrief on 2026-10-19. The game prints them without DRAFT marks. Card 2's floor line still carries a CONFIRM marker; the engine's answer is reported for a ruling, and the card is unchanged.
