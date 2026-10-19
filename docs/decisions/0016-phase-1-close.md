# 0016 — Phase 1 close: the trace game and its rulings

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
