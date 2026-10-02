WORK ORDER 6, PR 6b (#13) follow-up — ANSWERS (design side, 2026-10-02, confirmed by Foreman)

Apply as one more small commit on wo6b/scenarios, before merge. Spec §4.3b on the branch is updated to match. Add to the second addendum of decision 0012; changed registry values keep their old values in history.

1. Spread and median: rule β 0.4 with the median your scan found (159.9 m/s, or whatever the tool returns at β 0.4 after recomputation), giving the pilot about 6% and severity 70 about 34% of line length down. Record in the registry: β 0.4 (J, ruled), the median as a calibration parameter rather than a physical gust, the targets, the achieved shares, and the β 0.3 fits as alternatives in history.

2. Tower repair: a collapsed tower needs 72 h of crew work, no lead time, plus travel (placeholder, J; emergency tower restoration takes days, permanent rebuilds after Faxai took weeks). It remains one failure point.

3. A scenario with no damage is acceptable; keep it.

4. The towered-line stop limit applies at pilot severity only. At severity 70 report the counts; the design side logs the scenario where all 5 towered lines collapse as an open item for the realism checks. No change.

Report the new per-scenario tables for both recipes. Explain every golden change. CI green on both platforms, then Foreman merges PR #13, closing Work Order 6.
