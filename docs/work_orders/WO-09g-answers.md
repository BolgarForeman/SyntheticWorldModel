# Work Order 9g: answers to PR 19 (apply on this branch before merge)

*2026-10-19 · ruled by Foreman (the author) · apply on `wo9g/trace-game`, push to PR 19 · record in decision 0017 · spec now v0.13*

## Answer 1: crew order among distribution substations (your report on card 9)

- **The ruling.** In group 2 of the default crew order, a distribution substation ranks by the **highest Lifeline weight among the end uses it supplies, its own weight included**. A substation that feeds the tertiary hospital (10) outranks one that feeds a clinic (3). Ties still go to the shortest trip, then the lowest id. Spec v0.13 §4.5.
- **Engine.** Change the group-2 key for distribution substations to that rule.
  - "Supplies" means its switched-on and hidden electricity couplings to end-use nodes, as the engine plays them. Report which you used.
  - Power feeds to end uses keep their current key.
- **Registry and Theta List.** Record the crew-order ranking as a dynamics entry:
  - chosen: highest supplied weight;
  - alternatives: own weight only; the sum of supplied weights;
  - grade J, ruled 2026-10-19.
- **Card 9.** The printed answer now holds. Keep its drill world, and make the drill check the engine under the new rule.
- **Goldens.** Rerun the 8 reference runs. Report every run whose crew order, timeline or hours out changed, with the reason. Scenario 7's mission must still be sealed: report its change only as "changed" or "unchanged", not the numbers.

## Recorded for later (no work now)

Foreman's standing requirement:
- Each dynamics rule with recorded alternatives becomes a selectable option (a recipe setting, and a drop-down in the interface).
- The same world can then be run under alternative A, B or C and the results compared.

Build it with the answer-key solver (Phase 2) or the interface (Phase 7), whichever comes first. The registry entry above is its first case.

## Then

Push to PR 19 and report in the §11 format. PR 19 stays open for the play-test fixes and the rule-card rulings that follow.
