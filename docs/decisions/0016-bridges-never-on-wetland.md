# 0016 — Bridges never sit on wetland

- **Date:** 2026-10-19
- **Decided by:** the coder, applying decision 0006 (WO-03 B3); accepted by Foreman on merging PR 20, 2026-10-19
- **Recorded by:** branch `fix/layers-bad-ground-siting`
- **Sources:** decision 0006 (answers 1–3 and the 2026-09-29 follow-up); the layers property test failure of 2026-10-19

## Context

Decision 0006 forbids nodes on sea, river or wetland, and lets a bridge sit on a river. It said nothing about a river cell whose land cover is wetland. The bridge siting rule drew from every free river cell where a road crosses a river, so a bridge could land on wetland. The layers property test caught it: terrain seed 3220 put the second transport bridge (`SWM-TRN-0008`) on a wetland river cell. Decision 0006's exemption covers river only, so the test was right.

## Decision

- **A bridge may sit on a river, but never on wetland.**
- This applies on every path that sites a bridge:
  - the road's river crossing;
  - the relaxed rule: the river cell nearest the road network;
  - the viaduct on an island with no river.
- If every crossing on every road is wetland, the relaxed rule applies, and its siting note says "off wetland".

## Effect on worlds

- A world changes only where a candidate crossing cell is wetland.
- The pilot's three bridge roads cross 22 river cells, none of them wetland. The pilot and the golden hashes are unchanged.

## Addendum, 2026-10-19: a second case, and Hypothesis made deterministic in CI

- **Recorded by:** branch `wo9f/layers-siting` (PR 22), issue #21.
- **A second case.** Hypothesis found the same failure with terrain seed 15746: the second transport bridge, `SWM-TRN-0008`, sat on the wetland river cell (198, 165). Under this decision's fix it moves to the river cell (185, 160).
  - The case is an explicit `@example` on the layers property test.
  - A unit test checks that both bridges sit on river and neither on wetland.
- **Hypothesis in CI.** `tests/conftest.py` registers a `ci` profile: derandomized, with no example database and `print_blob` on. It loads whenever `CI` is set, as GitHub Actions does, so a CI pass is reproducible. `HYPOTHESIS_PROFILE=ci` reproduces a CI run locally.
- **Effect.** No world changes beyond this decision's: the pilot, every fixture world and the couplings tests' rich world are unchanged.
