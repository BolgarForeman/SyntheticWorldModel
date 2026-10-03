# Work Order 6c: answers to PR 14

*2026-10-03 · ruled by Foreman (the author) · applies to branch `wo6c/power-lines` · record as an addendum to decision 0013*

The PR stopped correctly at the PR 6b tower limit. The cause of questions 1, 2 and 5 is one thing: the ridge factor was read for the worst of 8 wind directions everywhere. That is the code's design envelope, not one storm. It put a speed-up on 55% of the pilot's land, and a 114.6 m/s gust on L0001, above the highest gust ever measured (113 m/s, Barrow Island, 1996). Answers 1–3 fix that, then the shares are re-measured.

Spec v0.8 §4.3b is corrected on this branch to match these answers (the Kzt form, the storm's own direction, the tower setting, and feeds on poles).

## Answers

**1. Read the ridge factor in the storm's own wind direction (questions 1 and 5).**
- Keep the 8 directional factors `topography` already computes, one grid per direction, per structure height. Stop taking their maximum for the storm.
- In each scenario, each place reads the factor for the direction its wind blows at its peak:
  - to the right of the track (signed distance > 0, as `_signed_distance_km` defines it), the wind travels along the track's direction of travel;
  - to the left, against it;
  - Northern Hemisphere, counterclockwise rotation. Record this as a registry rule, `storm.rotation: counterclockwise`, grade J, reason: every storm rule is taken from Taiwan. Headings are uniform over all directions, so the choice mirrors the field without changing its statistics.
- Snap the wind's travel direction to the grid direction with the largest dot product with it; ties go to the lowest D8 index. Use only the permitted arithmetic.
- **Inside the eyewall** (|signed distance| ≤ R_max) a place meets the wind from both sides as the storm passes, so it takes the larger of the two opposite directions' factors.
- **The inflow angle is neglected.** Mark it `# CHOICE:`.
- Isolation condition: use the code's own reach upwind, min(100H, 3.22 km), as quoted in `storm.topographic_factor`, in place of a flat 3.22 km.
- Towers read the directional factor at tower height, and poles at pole height, as now.

**2. Add a setting: towers designed for their site.**
- Add the registry rule `storm.towers_designed_for_site`: true or false, grade J, status placeholder. Default **false**, the current behaviour, until ruled.
- **When true:** each tower reads its gust divided by its site's design factor against the Fani curve. The design factor is the worst-direction factor at tower height at that tower point, the value the code requires a structure there to be designed for.
- **When false:** a tower reads its gust directly, as now.
- It must be overridable from a recipe by name, like every rule.
- Report the towered-line table both ways. The default is ruled after that.

**3. Recalibrate the pole-line median (question 2).**
- After answer 1, rerun `tools/calibrate_line_curve.py` at β 0.4 against the two targets: about 10% of pole-line length at the pilot's severity, and about 30% at severity 70.
- **Store the best single median that puts both within 5 points.**
  - Move 159.94 m/s into the rule's history, with the reason "recalibrated for routed lines and the directional ridge factor (PR 14 answers)".
  - Record the achieved shares in the rule.
- The median is a calibration parameter, not a physical gust, so tuning it to the ruled targets is the intended use.
- If the pole-line shares depend on answer 2's setting, calibrate with it false and report the shares with it true.
- If no single median meets both windows, store the closest, report it, and stop.

**4. Widen the pilot's edge range to 40–55 (question 3).**
- The ruled change to rule 4 (any substation may supply any consumer) added the feed.
- Change the range wherever it is held, with a history entry. Unpin the test from 51 to the range.

**5. The Kzt formula (question 4).** Your implementation is right: Kzt = (1 + K1K2K3)², so wind speed takes 1 + K1K2K3. The spec is corrected.

**6. Feeds from transmission substations run on poles (question 6).** As you built it. The spec is corrected.

**7. Circuits (question 7).** Keep 1 as a placeholder. In Phase 1 a failed line fails whole, so the number has no effect yet. It matters with partly failed lines and line capacity limits, both later.

**8. Long off-road legs (question 8).**
- Accept them for Phase 1, as a declared limitation of the pilot's sparse road layer.
- Add one line to decision 0013's addendum: "local road density below the mapped transport layer is not modelled; off-road legs are therefore long."

**9. No mutual pair in the pilot (question 9).**
- Accept it. The pilot's `two_way_pct` is 0. The old pair existed only because a substation's telecom control had no other possible supplier.
- The hand trace does not need a loop.
- Keep the generic tests of the "keep a mutual pair" rule.

**Audit A2 (mast-to-mast and reservoir-to-reservoir links).**
- These break the layer signatures, so they are generator bugs.
- Don't fix them in this PR. They become Part 0 of Work Order 7.

## Report back

**1. Towered lines, one table per setting of answer 2.** For each scenario:
- which towered lines fail;
- the peak gust on each line;
- the share of tower points where the ridge factor is above 1.

**2. Ridge-factor statistics, after answer 1.**
- The share of pilot land with a factor above 1, and the mean factor, in each scenario.
- The highest gust anywhere on the pilot.

**3. Line loss.**
- The new median.
- The pilot and severity-70 line-loss shares, with each window's result.

**4. The PR 6b tower limit:** whether it now holds under each setting of answer 2.

**5. Every golden change, explained.**

If the PR 6b tower limit still fails under both settings, report it and stop.
