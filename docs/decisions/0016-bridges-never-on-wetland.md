# 0016 — Bridges never sit on wetland

- **Date:** 2026-10-19
- **Decided by:** the author (Foreman)
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
