WORK ORDER 5, PR 5c (#11) — ANSWERS (design side, 2026-09-30, confirmed by Foreman)

Apply these as one follow-up commit on wo5c/repair, before merge. Record them as an addendum to docs/decisions/0011. Every changed registry value moves its old value into history, citing decision 0011.

1. Repair shortfall (compliance gap): default 0 for repair_rates.
   - Hazus restoration times are an estimate of what restoration actually takes, not a standard facilities fall short of; a 20% gap on top counts typical slowness twice. The 20% was a Work Order 1 recipe default, never ruled for repair.
   - A positive gap still means slower repair, as built.
   - Grade the Hazus repair rules L (US), noting in their reasoning that the MR4 restoration functions rest largely on expert judgment (ATC-13) and US earthquake experience, not Taiwan typhoon restoration. Taipower's typhoon record may be faster.
   - Add a sensitivity pair to the fixtures (not golden files): the pilot with the repair gap at +20 and at −20.

2. Spread: by default the Hazus standard deviation for each class and damage state sets the spread (σ ÷ mean). The recipe's heterogeneity lever for repair_rates becomes an optional override: unset means Hazus spread; set means that value. One draw per node still serves every damage state, each scaled by its own spread.

3. Road speed: 40 km/h stays a placeholder, grade J, with that reasoning.

4. Extensive and complete damage: record them for every class with a Hazus row. Crew work 72 h for extensive and 168 h for complete, placeholders, grade J. The pilot's damage stays slight and moderate (ruling T6).

5. Road junctions and rail nodes: no repair rows. Rail is out of Phase 1 (rule 7). A junction is not a facility; road damage will sit on road links in Work Order 6. Record this in the registry as a rule with that reasoning.

6. Emergency pool: make it a recipe control (unobserved section, beside crews and crew_base): mobile_substations and mobile_cell_sites, default 1 and 1 (ruling T11). Remove repair.emergency.pool from the registry (history note). The mockup label and the request name "stage_crews_at_depots" are left for the Phase 7 mockup update; do not rename them here.

7. Emergency timing: accepted as built — set-up time (mobile substation 12 h, mobile cell site 14 h) plus modelled travel. Record in the registry reasoning that the source's 12–24 h includes travel, and that pilot totals land at 12–15 h.

The coder's other choices in the PR 5c report are accepted as marked (CHOICE: comments stay).

After this commit: explain every golden change (repair times will shift with answers 1 and 2), CI green on both platforms, then Foreman merges PR #11. That closes Work Order 5.
