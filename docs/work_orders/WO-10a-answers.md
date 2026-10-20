# Work Order 10a: answers, PR 26 (apply on this branch before merge)

*2026-10-20 · design side; the answers below are within the rulings already made, so Foreman may overrule any · apply on `wo10a/frame`, push to PR 26, add to decision 0018*

## Review

- Accepted as built:
  - the frame;
  - schema version 4 and its migration;
  - the plan policy (byte-identical with the default order);
  - the start-of-run check;
  - the isolation test;
  - the golden keys.
- The scenario 7 key reads correctly. The optimum is 30.75, four plans tied: the two crews are interchangeable, and POW-L0004 costs no service-hours, since its load has the second feed. The default order scores 52.25. Most connections first and biggest first both put a crew on POW-L0004 first (distance 1.30). Nearest supplier finds the optimum.
- Every `CHOICE:` listed in the report stands.

## Answers

1. **No action for the restorative measure: yes, the default crew order.** The pilot spec says the reference runs, with no actions and the default order, give the "no action" term of the measure. The key says so already (`no_action: the default crew order`).

2. **Biggest first: per unit within a layer, as built.** A rule of thumb ranks by what a hurried planner can read off a source. Converting MVA to MW, or storage to flow, would need assumptions no such planner makes. Each element's share is taken against the total of its own unit within its own layer. State this in the key's rule-of-thumb entry ("share of its layer's total in the same unit").

3. **The nearest-supplier copy: as intended.**
   - Moving only the couplings that aren't already among the nearest is the right reading for consumers with more than one feed.
   - Each feed goes to the next nearest unused eligible supplier.
   - The moved coupling keeps its κ and runs on no line, so it takes no damage (WO-10 B4).

4. **A registry role for solver settings: add `answer_key`.** The spread bands and the instance bound are not choices about the world. They describe how keys are found and reported, like the objectives, and sit outside Θ.
   - Give both rules `theta_role: answer_key`.
   - `swm rules --theta` lists them with the objectives, outside the tuple.
   - The rules page badges them as answer-key settings.

5. **The repair-state problem: fix it, in its own PR, before PR 10c.** It is a departure from the spec, not a design question. Spec §4.4a sets crew work and lead time by damage state, and the engine must use the state each scenario drew.
   - **Branch:** `wo10f/repair-state`, cut from main after PR 26 merges, ahead of PR 10b.
   - **The fix:** the engine keeps repair records by (node, damage state). A storm-damaged facility takes the record for the state its scenario drew. A strike takes complete damage explicitly (ruling Q4), not by falling through to the last record.
   - **Tests:**
     - a facility damaged at each state takes that state's crew work and lead time;
     - a strike takes complete.
   - **Expected goldens:**
     - the pilot and its reference runs are unchanged, since no pilot scenario damages a facility;
     - the severity-70 fixture's reference runs move wherever floods damaged facilities. Explain each change, scenario by scenario, with the old and new repair hours.
   - **Records:** a decision record, as a fix of a departure (decided by the design side, applying spec §4.4a), and a CHANGELOG line.

## Also, small

- **The stamp repeats its own label.** The key reads `assumes: 'assumes: restorative; …'`. Keep the key `assumes`, and drop the word from the start of its value.
- **`BUILT_FEATURES`** is read by the buildability report, so a stale list reports built features as not built. In the repair-state PR, bring it up to date with everything built through Phase 1 and PR 26, and add a test that every feature a golden recipe uses and the build handles is listed.

## Apply here

Answers 2 (the wording in the key), 4 and the stamp fix, on this branch. Regenerate the goldens; the keys change only in those lines. Push, confirm CI green on both platforms, and report.
