# 0018 — Phase 2: the answer keys

- **Date:** opened 2026-10-20; each Phase 2 pull request adds its part
- **Decided by:** the author (Foreman), on 2026-10-19 and 2026-10-20
- **Source:** `docs/design/evidence/Phase2_Answer_Key_Ruling_Sheet_v0_2.md`; Work Order 10
- **Spec:** structure v0.17 §5 and §7; Pilot Spec v0.8; Build Game Plan, Phase 2 and Phase 4

## The twelve rulings

| Item | Ruling |
|---|---|
| Q1 Order of build | One pull request per model, the MIP last: 10a the frame and the restorative model, 10b offensive, 10c defensive, 10d the MIP. The reports every key carries are built with the frame in 10a. |
| Q2 Restorative plan | Each crew an ordered list of jobs; every failed element once, by one crew; both from the base at hour 0; the engine's rules. |
| Q3 Offensive world | The calm world, no storm. |
| Q4 What a strike does | Complete damage, repaired by the crews in the default order. Lines are not targets. |
| Q5 Add reserve | Any one inbound dependency of any node: a new stock where none exists, otherwise hours added. |
| Q6 Reserve size | The whole window (72 h) at the node's full draw. |
| Q7 Defensive scoring | Expected loss over the 8 scenarios, equally weighted; the budget is a ceiling. |
| Q8 Search size | Both budgets in full, on every core, reusing what repeats; timed first; a 48-hour ceiling per request (placeholder for the instance bound). The key is optimal against the sampled storms. |
| Q9 Informative | Out of Phase 2: built in Phase 4 against the pipeline's belief. |
| Q10 MIP | A time-expanded MIP of the engine's dynamics for the three models, solved with HiGHS; agreement on the optimum's objective. |
| Q11 What a key reports | Distance from the optimum is the only measure. The spread of every answer replaces the second-best margin. No acceptability band. Rules of thumb reported as distances. True criticality under each request's own scenarios. Dose zero until Phase 3. The stamp names the scenarios. |
| Q12 Pilot requests | Ten requests: defensive at budgets 3 and 4, offensive at k = 2 and 3, restorative on scenario 7, each under Lifeline and Equal weights; 72-hour window; recipe schema version 4. |

## PR 10a: the frame and the restorative model

- **Recipe schema version 4.** An offensive request gains `world` (`calm`) and `strike_damage` (`complete`); a defensive request gains `reserve_hours` (`window`); a restorative request gains `scenario`, which is required. A version 3 recipe migrates with those defaults; a version 3 restorative request names no scenario, so it is refused with the field named.
- **`swm solve`** writes one key per request, an index and one compressed answers file per search to `answer_keys/`. Requests that differ only in their weights share one search. The informative model is refused (Q9). In 10a the offensive and defensive requests are listed in the index, unsolved, until PRs 10b and 10c build them.
- **The registry:**
  - `solve.spread_bands_pct` (1, 5, 10; grade J; ruled, Q11);
  - `solve.instance_bound_h` (48 h; placeholder, open decision 6; Q8);
  - the objective "acceptability threshold" is retired, its text moved to its history (Q11).
- **The engine** takes a crew plan as its crew policy, beside the default order (Work Order 10, C2). With the default order it is unchanged: every reference run and the hand-trace test are byte-identical. The three ruled dynamics rules are now checked when a run starts (C4).
- **Scenario 7** has 24 plans. The optimum is 30.75 weighted service-hours (Lifeline), tied four ways; the default crew order scores 52.25.

## PR 26 answers (WO-10a answers; design side, within the rulings)

- **No action for the restorative measure** is the default crew order, as the pilot spec's reference runs give it.
- **Biggest first** ranks by each element's share of its layer's total in the same unit, with no conversion between units. The key states the basis.
- **The nearest-supplier copy** is as built: only couplings not already among the nearest move, each to the next nearest unused eligible supplier, keeping κ and running on no line.
- **A registry role for answer-key settings.** `theta_role: answer_key` marks rules that say how keys are found and reported. They sit outside Θ, like the objectives, and `swm rules --theta` lists them beside the objectives. The spread bands and the instance bound take it.
- **The stamp.** The key's `assumes` value no longer repeats its own label.
- **The repair-state departure** is fixed in its own pull request, `wo10f/repair-state`, before PR 10b.

## PR 10b: the offensive model

- **The search:** every set of k distinct nodes is struck at hour 0 on the calm world (Q3), with complete damage named explicitly and repaired by the crews in the default order (Q4; decision 0019). Lines are not targets. There are 276 sets at k = 2 and 2,024 at k = 3.
- **The measure** mirrors: (optimum − objective) ÷ (optimum − no-strike objective). The no-strike objective is the calm world's, 0.
- **The rules of thumb:**
  - most connections first and biggest first strike the top k of their ranking;
  - nearest supplier strikes the best set found on the copy, scored on the true world.
- **Every core.** A batch of 64 runs or more is spread across every core; results come back in the order asked, so no key depends on the core count.
- **The pilot's offensive keys (Lifeline):**
  - **k = 2:** optimum 4,467.35, tied three ways (the tertiary hospital with the LNG terminal, the plant or the transmission substation).
  - **k = 3:** optimum 4,690.85, tied three ways (the same, with HLT-0004).

## PR 10c: the defensive model, and CI's checks on every key

- **The search (E1–E4).**
  - **Actions:** up to the budget, a ceiling, protect condition (cost 2) on any of the 55 elements the storm can damage, or add a reserve (cost 1) on any of the 47 inbound dependencies, at most one each.
  - **The reserve:** the window's hours at the node's full draw. It is added to the node's first stock for that commodity, in the order the engine draws them, or it is a new stock where the node has none (E2).
  - **The objective:** the mean of the 8 scenarios' weighted service-hours.
  - **Answers:** 19,984 at budget 3 and 259,289 at budget 4.
- **What is skipped, each provably identical (E4).**
  - A scenario with no damage is one run, since no action changes it.
  - In each scenario, a protection of an element that scenario did not damage is left out of the run. The engine protects only damaged elements, so answers that differ only in such protections share the run.
  - Equal runs are played once (E5).
- **CI's checks replace E6's sample rule, for every model (Foreman, 2026-10-21).**
  - **Without a run:** CI verifies each key's and answers file's hash; that the answers file lists every affordable answer, by enumeration; that the stored optimum is the best score in it, ties listed; and the spread, recomputed from the file.
  - **Re-scored byte-exact on both platforms:** the optimum and every tie, the three rules of thumb, the 50 next-best answers, and the 50 answers with the smallest SHA-256 of their text.
  - **The full re-solve** is marked `slow`. It is required on any pull request that touches `dynamics/`, `solve/` or a dynamics rule in the registry.
- **Buildability.** `transfer_form:step` arrives in Phase 5: the spec holds it for later worlds, and the engine refuses it (PR 27, question 1).
- **The pilot's budget-3 keys.**
  - **Optimum:** 2.625 weighted service-hours under both weightings, against 8.59375 with no action. It is tied 48 ways: protect SWM-TEL-L0002, alone or with any one reserve, since no reserve changes anything.
  - **Why only that line:** it falls in both telecom-damaging scenarios (0 and 7). The telecom nodes it serves lose their own layer's link, which no reserve covers.
  - **The rules of thumb:** most connections first and biggest first find nothing better than no action among their top three elements (distance 1). Nearest supplier finds the optimum.

## PR 30 answers: no reserve on telecom (WO-10c answers, 1; ruled by Foreman 2026-10-21, option A)

- **Context.** The engine never draws a stock on a telecom dependency, which has its own tolerance rule instead, so a telecom reserve could never drain (PR 30, question 1).
- **Decision.** A reserve goes only on a dependency whose commodity can be stored: power, water, fuel, and transport as stockpiled supplies.
  - Telecom cannot be stored. A telecom site's battery is a reserve on its power, which stays allowed.
  - Telecom outages keep their own fallback rule (rule card 5).
- **Registry.** `solve.reservable_commodities`: [power, water, fuel, transport]. It is an answer-key setting, grade J, with the alternative "every dependency, telecom included" (the earlier build).
- **Effect.** The pilot has 31 reservable dependencies of its 47 (16 were telecom). The defensive answers fall to 6,752 at budget 3 (from 19,984) and 65,277 at budget 4 (from 259,289). Spec v0.18 §5 and Pilot Spec v0.8 carry it.
