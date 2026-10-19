# Hand trace against the engine: scenario 7

*v0.1 · 2026-10-19 · design side · compares the sealed design-side trace (v0.1, 2026-10-11, written before any engine result was seen) with the engine's reference run 7*

## Result

**The trace and the engine agree on everything but one rule the spec left open.**

**Agree:**
- **The damage:** POW-L0004, TEL-L0001, TEL-L0002.
- **What it cuts.** Only masts TEL-0002 and TEL-0003 lose service. The power loss is covered by the second feed. No substation or plant is affected, no stock is drawn, no delivery or switching trip happens, and the hidden couplings change nothing in this storm.
- **Crew assignment and order:**
  - crew 1 takes POW-L0004, which finishes past the 72-hour horizon;
  - crew 2 takes TEL-L0002, then TEL-L0001.
- **Crew 2's first job,** to the step: arrives 2.999 h, prepared 4.999 h, first failure point done 10.999 h.
- **Rounding to the 15-minute step** (card 12).

**Differ:** travel between failure points, and between jobs.

| | Trace | Engine |
|---|---|---|
| TEL-L0002, 2nd failure point → done | 17.999 h | 23.724 h |
| TEL-0003 back | 18.00 h | 23.75 h |
| TEL-L0001 done / TEL-0002 back | 26.57 h / 26.75 h | 39.97 h / 40.00 h |
| Hours out (TEL-0003 + TEL-0002) | 18.00 + 26.75 = **44.75** | 23.75 + 40.00 = **63.75** |
| Weighted service-hours lost (mast weight 1) | 44.75 | 63.75 |

## Cause

The spec says crews move job to job (v0.12 §4.5) but gives no rule for a trip that starts at a failure point.
- **The trace walked straight across country:**
  - 2 km along the line to the next failure point, 1.0 h;
  - 1.13 km across to the next line, 0.57 h.

  It named the other reading (back to the road and along it, about 8 h) as judgment call 1.
- **The engine walks back to the nearest road, drives, and walks back in** (now stated on rule card 10):
  - 6.725 h between the two points of TEL-L0002;
  - 8.245 h to TEL-L0001.

Recomputed under the engine's rule, the trace reproduces every engine time exactly. Judgment calls 2–4 did not bite in this storm:
- preparation counted once per job;
- telecom fallback with d = 1;
- a node's largest in-feed taken.

A small difference in crew 1's travel (1.798 h against the engine's 1.749 h) comes from the travel table the trace used, which lists a failure point's kilometre segment rather than its exact position. It falls outside the horizon and changes nothing.

## What this shows

- **The hand-trace check passes.** A person working from the world's data and the spec reaches the engine's answer once the one open rule is settled. The one difference is a genuine spec gap, not an engine error, and the trace found it.
- **The open rule is now a modelling choice for a ruling.** Should a crew working along a line walk directly between failure points, or go back to the road? The two readings move scenario 7's score from 44.75 to 63.75 weighted service-hours lost.
