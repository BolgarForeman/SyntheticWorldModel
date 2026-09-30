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

## Addendum: answers to PR 5c (#11)

- **Date:** 2026-09-30
- **Decided by:** the design side, confirmed by the author (Foreman)
- **Source:** `docs/work_orders/WO-05c-answers.md`

Every changed registry value keeps its old value in history, citing this decision.

1. **Repair gap defaults to 0.** Hazus restoration times already estimate typical restoration; they are not a standard that facilities fall short of. The old default of 20% came from Work Order 1 and was never ruled for repair.
   - A positive gap still means slower repair, as built.
   - The Hazus rule stays L (US). Its reasoning now notes that the MR4 restoration functions rest largely on expert judgment (ATC-13) and US earthquake experience, and that Taipower's typhoon record may be faster.
   - A sensitivity pair, the pilot at +20 and −20, is added as fixtures, not golden files.
2. **Spread comes from Hazus.** By default each class and damage state takes the spread σ ÷ mean. The recipe's `repair_rates.heterogeneity_pct` is an optional override: unset gives the Hazus spread, and a set value applies everywhere. One draw per node still serves every damage state, each at its own spread.
3. **Road speed** stays 40 km/h, grade J, as a placeholder.
4. **Extensive and complete damage** are recorded for every class with a Hazus row. Crew work is 72 h and 168 h, placeholders, grade J. The pilot's damage stays slight and moderate (ruling T6).
5. **Road junctions and rail nodes get no repair rows.** A new rule, `repair.no_repair_rows`, records why:
   - rail is out of Phase 1 (rule 7);
   - a junction is not a facility, and road damage will sit on road links in Work Order 6.
6. **The emergency pool is a recipe control:** `unobserved.mobile_substations` and `unobserved.mobile_cell_sites`, default 1 and 1 (ruling T11).
   - The registry rule `repair.emergency.pool` is removed, and `crews.pilot` notes where the pool went.
   - These defaulted fields are new; recipe version 2 is not yet released, so its number is unchanged.
   - The mockup label and the request name `stage_crews_at_depots` are left for the Phase 7 mockup update.
7. **Emergency timing is accepted as built:** set-up (mobile substation 12 h, mobile cell site 14 h) plus modelled travel. The registry reasoning records that the source's 12–24 h includes travel, and that pilot totals land at 12–15 h.

The coder's other PR 5c choices are accepted as marked.
