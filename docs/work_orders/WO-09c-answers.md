# Work Order 9c: design-side inputs and one change (apply on wo9c/close)

*2026-10-19 · design side; the F0 change ruled by Foreman (the author) · branch `wo9c/close` · rebase onto main after PR 23 merges*

## F0, changed (ruled by Foreman, 2026-10-19)

Work Order 9 named Foreman's son's play-test as the Phase 1 hand-trace acceptance test. Foreman has since ruled the play-test a nice-to-have, not needed before the proposal: "having the hand drawn test available is the thing to show".

- **The acceptance test is the design side's sealed hand trace of scenario 7 against the engine.** It was written before any engine result was seen, compared on 2026-10-19, and agrees on every point once the one open rule (travel along a line) was ruled. The engine then matched the recomputed trace exactly.
- The play-test and a clean-agent trace stay optional. If either is run later, its differences are logged and ruled like any other.
- Record this in decision 0017 and the TRACE entry.

## F1, sent

`tests/fixtures/hand_trace_scenario_7.yaml`, committed on this branch: each crew's arrivals, preparation and completions, each repair's back-in-service hour, hours out for every end-use node, the score, the state of named nodes at named hours, and the three things that did not happen.

## F2

- Compare at the engine's 15-minute step: every fixture hour is a step hour; compare those exactly against the engine's step hours, nothing finer.
- `null` means not within the horizon.
- The fixture is hand-written. Never regenerate it from the engine. If the test can't pass without changing what it tests, stop and report (CLAUDE.md §10).

## G

- **G1, G3** as in Work Order 9. Phase 1 closes on recipe schema version 3 and spec v0.15.
- **G2:** decision 0017 already exists (PR 19, PR 23). Add to it: the F0 change, the fixture, and its test.
- **G4:** the `v0.1.0` tag waits for Foreman's word after this PR merges.
