# Phase 2, the answer-key solver: ruling sheet v0.2

*2026-10-20 · design side, for Foreman · all 12 items ruled 2026-10-19 and 2026-10-20 (rulings first, the items as put below) · follows Phase 1's close (tag v0.1.0)*

## What Phase 2 is for

The generator builds a world in which every quantity is known. The answer-key solver asks that world a question and finds the true best answer. The four pilot models each ask a different question:
- **Defensive:** what to protect before the storm.
- **Offensive:** which nodes to strike.
- **Restorative:** how to sequence the two crews after the storm.
- **Informative:** which couplings to observe.

Later, the pipeline answers the same questions from the emitted sources alone, once carrying doubt and once flattening it. Each answer is scored by its distance from the key. So the key is the yardstick for every result in the pilot.

**Done when** (Build Game Plan, Phase 2): every key is found by brute force and agrees with the MIP; the uniqueness and shortcut checks report, and never silently regenerate.

**What Phase 2 starts from:**
- The recipe already carries model requests (schema v3): member-class, model, objective, service weights, budget, window.
- The engine already takes protect and add-reserve actions.
- One engine run of the pilot takes about 0.65 s on one core (measured 2026-10-19): 8 scenarios is about 5 s per candidate answer.

**Standing rules that bear on it:**
- The solver reads the true world only; it never imports error induction, and the generator never imports it (CLAUDE.md §3).
- Every number that shapes a key lives in the registry with its source.
- A key that fails a check is reported, never silently regenerated.
- Informative (ruled 2026-09-29): its own optimization, spending a limited resource on network elements to reduce uncertainty about the network; not "observe, then defend"; collection costs 1 unit per task.

## Rulings (Foreman, 2026-10-19 and 2026-10-20)

| Item | Ruling |
|---|---|
| Q1 Order of build | **A.** One pull request per model, the MIP last. With Q9, the PRs are 10a frame and restorative, 10b offensive, 10c defensive, 10d the MIP and the reports across all keys |
| Q2 Restorative plan | **A.** Each crew an ordered list of jobs; every failed element once, by one crew; both from the base at hour 0; the engine's rules |
| Q3 Offensive world | **A.** The calm world, no storm |
| Q4 What a strike does | **B.** Complete damage, repaired by the crews in the default order. Lines are not targets |
| Q5 Add reserve | **A.** Any one inbound dependency of any node: a new stock where none exists, otherwise hours added |
| Q6 Reserve size | **A.** The whole window (72 h) at the node's full draw |
| Q7 Defensive scoring | **A.** Expected loss over the 8 scenarios, equally weighted; the budget a ceiling |
| Q8 Search size | **A.** Both budgets in full, on every core, reusing what repeats; timed first and reported before budget 4; a 48-hour ceiling per request (placeholder for the instance bound). Asked on the way: the 8 scenarios stay; the pilot is illustrative and the full study widens the sample, and the write-up says the key is optimal against the sampled storms |
| Q9 Informative | **C.** Out of Phase 2: on the true world nothing is uncertain, so a key would be "purely performance". Built in Phase 4 against the pipeline's belief, as ruled 2026-09-29; the pilot spec's line corrected |
| Q10 MIP | **A.** A time-expanded MIP of the engine's dynamics for the three models, solved with HiGHS; agreement on the optimum's objective. The crew constraints get their own short sheet before that PR |
| Q11 What a key reports | Ruled part by part, after Foreman's challenge: distance from the optimum is the only measure. **Spread** of every answer (share within 1, 5 and 10% of the optimum; a random answer's mean distance) replaces the second-best margin. **No acceptability band** in the key (A). **Rules of thumb** reported as distances, not pass/fail (A). **True criticality** under each request's own scenarios (A). **Dose** zero with a note until Phase 3, and the **stamp** as the spec plus the scenarios (A) |
| Q12 Pilot requests | **B.** Ten requests: defensive at budgets 3 and 4, offensive at k = 2 and 3, restorative on scenario 7, each under both Lifeline and Equal weights; 72-hour window; recipe schema version 4 |

**Amended by these rulings:** structure v0.17 §5 and §7; Pilot Spec v0.8; Build Game Plan Phase 2 and Phase 4.

## Items as put to Foreman (v0.1)

**Q1. Order of build: one pull request per model, the MIP last.**
- 10a: the solver's frame (requests in, stamped keys out, `swm solve`) with the restorative model, the smallest search.
- 10b: offensive. 10c: defensive. 10d: informative.
- 10e: the MIP cross-check, with the uniqueness and shortcut checks across all keys.
- Recommended: each model is checkable alone, and the frame is proven on the easiest search first.

**Q2. Restorative: what the crews are sequencing.**
- Scenario 7 only, as the pilot spec says. A plan gives each of the two crews an ordered list of jobs; every failed element is done once, by one crew. Both start at the base at hour 0, and travel, preparation and switching follow the engine's rules.
- Search: every split of the jobs between the crews, in every order.
- Recommended.

**Q3. Offensive: the world it strikes.**
- A. The calm world, with no storm: the attack alone, as the pilot spec poses it. *Recommended.*
- B. On top of each storm scenario, averaged over the 8.
- C. Both, as two requests.

**Q4. Offensive: what a strike does, and to what.**
- **Targets:** any of the 24 nodes; lines are not targets in the pilot.
- **A. Destroyed for the window:** condition 0, never repaired. Simplest; an upper bound.
- **B. Complete damage, repaired by the crews under the default order.** Complete damage needs 168 crew hours, so the node stays out for the 72-hour window, but the crews' time is spent on it as in a real response. *Recommended:* it uses the engine's own repair rules and adds no new rule.
- C. Extensive damage (72 crew hours): repairable inside a longer window.

**Q5. Defensive: what "add reserve" means.**
- The engine's present action adds hours to an existing stock. The pilot spec says a node "gains a reserve on one inbound dependency", which can be where it has none.
- A. A reserve on any one inbound dependency of a node: a new stock where there is none, otherwise hours added to the one there. *Recommended:* it is the pilot spec's action, and a stockless node is where a reserve matters most.
- B. Existing stocks only.

**Q6. Defensive: how big a reserve is.**
- A. The whole window (72 h) at the node's full draw: the counterpart of protecting condition, which is also a complete bound (the fortification convention). *Recommended.*
- B. The class's design target from the registry (for example 72 h of hospital generator fuel at essential load).
- C. A fixed 24 h.

**Q7. Defensive: scoring and the budget.**
- The objective is the expected weighted service-hours lost over the 8 scenarios, equally weighted.
- The budget is a ceiling: an answer may leave units unspent. Budgets 3 and 4, as the pilot sweep uses.
- Recommended.

**Q8. How large the defensive search is, and how it is run.**
- Brute force must try every affordable answer. The pilot has 47 dependencies a reserve could go on, and 7 elements any scenario damages.
- **Skipped only where provably identical, never on a guess:**
  - protecting an element no scenario damages changes no run;
  - a scenario with no damage (3 of the 8) is the same with or without any action.
- **What is left:**
  - budget 3: about 17,700 answers, about 16 hours on one core;
  - budget 4: about 204,000 answers, about 184 hours on one core.
  
  The reserve combinations are nearly all of it.
- A. **Run both,** spread across every core, and cache what repeats. The coder measures first and reports the time before starting budget 4. A ceiling of 48 hours per request (placeholder for the exact-tier instance bound, open decision 6) stops a run and reports it. *Recommended.*
- B. Brute force at budget 3 only. Budget 4 is solved by the MIP alone, so it is not cross-checked.
- C. Narrow where a reserve may go (for example end-use nodes and their direct suppliers), declared as part of the pilot's model.

**Q9. Informative: how it is posed.**
- An observation choice can only be judged against what is uncertain, and the uncertainty comes from the pipeline. The generator makes no beliefs, and doubt is never a dial (ruled 2026-09-29).
- A. **Its own optimization, as ruled 2026-09-29:** choose n couplings to observe, at 1 unit each, to reduce uncertainty about the network. The belief to reduce is an input file the pipeline will produce. Phase 2 builds the solver and tests it against a hand-written belief; live keys come in Phase 4. The exact measure of uncertainty gets its own short sheet before 10d. *Recommended.*
  - Amends the pilot spec, which still says "to maximize the improvement in the defensive decision".
  - Amends CLAUDE.md's "reads the true world only": the informative solver also reads a belief file.
- B. The pilot spec's wording: value of information for the defensive decision, from a belief the solver makes itself. This conflicts with both 2026-09-29 rulings.
- C. Leave informative out of Phase 2; build it in Phase 4 with the pipeline.

**Q10. The MIP cross-check.**
- Why a MIP: brute force is exact only at hand-check size. The MIP is the solver that scales; brute force proves it right where both can run.
- A. **A time-expanded MIP of the engine's dynamics** for the defensive, offensive and restorative models (15-minute steps, trips as binaries, stocks, crews), solved with HiGHS (MIT licence). It must match brute force on the answer and on its score. Writing the default crew order as constraints is the hardest part; it gets its own sheet before 10e. *Recommended.*
- B. A MIP for the restorative model only (a standard scheduling problem); the others rest on brute force.
- C. No MIP: brute force alone at hand-check size, with docking as the independent check. Amends the pilot spec and Chapter 7's wording.

**Q11. What a key reports, and the thresholds the checks use.**
- **Uniqueness:** passes when the second-best answer is worse by at least 5% of the range from no action to the optimum (placeholder, J, in the registry). A tie fails, and is reported.
- **Acceptability threshold:** an answer within 10% of that range counts as acceptable (placeholder, J).
- **Shortcut test:** three shortcuts per model (highest degree, largest capacity, nearest supplier), each written out in the work order; the check passes when none recovers the optimum.
- **True criticality:** for each node, the objective when that node alone is struck (as Q4), less the objective with no strike, under the request's own scenarios and weights.
- **Decision-relevant dose:** zero in Phase 2, since no error is planted; reported and declared until Phase 3.
- **The stamp:** "assumes:" with class, model, objective, weights, budget, window and the resolved recipe's SHA-256, as spec §5 says.
- Recommended.

**Q12. The pilot's requests.**
- The pilot recipe carries seven requests:
  - defensive at budgets 3 and 4;
  - offensive at k = 2 and 3;
  - restorative on scenario 7;
  - informative at n = 1 and 2.
- All use the Lifeline weights, with a 72-hour window.
- The recipe schema moves to version 4 for the new fields (offensive world, strike damage, restorative scenario); a version 3 recipe still loads.
- Recommended.

## After the rulings

- Spec v0.17 §5 records the rulings. The pilot spec and Chapter 7 wording follow any amendment.
- Work Order 10 is written from them, one part per pull request.
