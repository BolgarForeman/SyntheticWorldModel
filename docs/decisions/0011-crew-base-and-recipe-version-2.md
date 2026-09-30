# 0011 — `crew_base` replaces `depots`; recipe version 2

- **Date:** 2026-09-29
- **Decided by:** the design side (Work Order 5, H1), confirmed by the author (Foreman)
- **Recorded by:** Work Order 5, PR 5c

## Context

The recipe's `unobserved.depots` counted the bases repair crews deploy from. The same word names a fuel-layer node class (the depot, §4.3a), so the two were easy to confuse. Structure v0.6 §4.4a names the crew base `crew_base`, and Work Order 5 H1 asks for the rename with a schema migration.

## Decision

1. **The setting is `unobserved.crew_base`** (count, 1 to 10, default 2). It is distinct from the fuel depot class.
2. **The recipe schema moves to version 2.** Version 2 differs from version 1 only in this rename.
3. **Old recipes still load.**
   - A version 1 recipe is migrated on loading: its `unobserved.depots` is read as `crew_base`, and the resolved recipe records version 2.
   - A version 1 recipe that names `crew_base`, or a version 2 recipe that names `depots`, fails with a message saying which name belongs to which version.
4. **The pilot sets `crew_base: 1`**, as §4.4a rules. It had taken the default of 2 while nothing used the setting.
5. **Two Work Order 1 streams are retired:** `unobserved/crews_and_depots` and `unobserved/repair_rates`. Neither was ever drawn.
   - Crew bases are sited without a draw.
   - Repair rates draw from the new per-layer `repair/<layer>` streams, as decision 0008 did for couplings and PR 5b for reserves.
   - No other stream moves.

The interface mockup still labels the control "Depots they deploy from". It should read "Crew bases they deploy from" in its next revision.
