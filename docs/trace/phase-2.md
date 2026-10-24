# Phase 2 — TRACE entry

*Phase 2 closes on recipe schema version 4 and structure spec v0.20, as `0.2.0` (Work Order 12, G3). The `v0.2.0` tag waits for Foreman's word after the Work Order 12 pull request merges. The closing summary comes first. The records kept while each work order was built follow it.*

## What Phase 2 built

Phase 2 builds the answer-key solver. For each request in a recipe, `swm solve` finds the best answer by brute force over every affordable answer, on the world's true dynamics, and writes a stamped key with its spread, rules of thumb and criticality. The generator never imports the solver, and the solver never imports error induction.

| Work order | Pull request | What it built |
|---|---|---|
| 10 (plan) | 25 | The Phase 2 ruling sheet's twelve rulings (decision 0018) and Work Order 10. |
| 10a | 26 | **The frame and the restorative model.** Recipe schema v4 and its migration. `swm solve`: one key per request, an index, and one bz2 answers file per search; requests that differ only in their weights share one search. Every key's stamp, optimum with ties, measure, spread, rules of thumb, true criticality, dose and sampled-storm note. Each search timed first and held under the 48-hour instance bound. The engine takes a crew plan beside the default order. The restorative model on scenario 7 (24 plans). |
| 10f | 27 | **Repair by damage state** (decision 0019): a damaged facility is repaired at the state its scenario drew; a strike names complete damage. `BUILT_FEATURES` brought up to date. |
| 10b | 28, then 29 | **The offensive model:** every set of k nodes struck on the calm world (276 at k = 2, 2,024 at k = 3), the mirrored measure, and batches of 64 runs or more spread across every core with results in order. |
| 10c | 30 | **The defensive model and CI's key checks.** Every affordable mix of protections (cost 2) and reserves (cost 1) up to the budget, scored as the mean over the 8 scenarios, skipping only what is provably identical. A new stock where a reserve has none to join. Reserves only on storable commodities (`solve.reservable_commodities`). CI checks every key without re-solving; the full re-solve is a `slow` test; the re-score runs as its own CI job. |
| 11 | 31 (design), 32 | **Repair timing and two engine fixes** (decision 0020): two repair paths, rebuild and service restored; a rebuild job opens only when its parts are ready; no parts wait at slight and moderate damage; quick paths at extensive and complete damage. A1, a stranded switching trip; A2, a stock that runs out mid-step. Every key re-solved. |
| 12 | 33 | **The close** (decision 0021): the MIP held, the documents amended, the black-start limitation stated, these records and `0.2.0`. |

**Recipe schema version 4.** An offensive request gains `world` (`calm`) and `strike_damage` (`complete`); a defensive request gains `reserve_hours` (`window`); a restorative request gains `scenario`, which is required. Version 1–3 recipes migrate, except a version 3 restorative request, which is refused with the field named.

**The ten pilot requests** (ruling Q12): defensive at budgets 3 and 4, offensive at k = 2 and 3, and restorative on scenario 7, each under the Lifeline and Equal weights, over a 72-hour window. They make five searches, since each pair differs only in its weights.

## How it was tested

### The key checks in CI

Since PR 30 (Foreman, 2026-10-21, for every model), CI checks every key on Windows and Linux without re-solving it (`tests/unit/test_answer_keys.py`):

| Check | How | Run |
|---|---|---|
| Hashes | every key and answers file against `SHA256SUMS` | main job |
| Enumeration | the answers file lists every affordable answer, counted by enumerating the action set | main job |
| Optima | the stored optimum is the best score in the file, with every tie listed | main job |
| Spread | recomputed from the file | main job |
| Re-scored samples | the optimum and every tie, the three rules of thumb, the 50 next-best answers and the 50 answers with the smallest SHA-256 of their text, re-scored by the engine byte-exact against the stored scores | its own job on both platforms (`-m keys`, without coverage) |

### The slow re-solves, and where they ran

The full re-solve of every key is `test_a_full_re_solve_reproduces_the_golden_keys`, marked `slow`. It is required on any pull request that touches `dynamics/`, `solve/` or a dynamics rule in the registry. It must reproduce every key and answers file byte for byte.

| Pull request | Machine | Keys | Result |
|---|---|---|---|
| 28/29 (PR 10b) | CI, Linux and Windows | every key then built: restorative and offensive | matched; the test step took 117 min on Linux and 80 min on Windows (PR 29 and PR 30 descriptions) |
| 30, first push | the developer's machine | every key then built | 4 passed in 6,060 s (PR 30 description) |
| 30, after the storable-reserve ruling | UA lab PC SH-2031-CBHPC (Core Ultra 9 285K, 24 cores, Windows 11) | budget 3, offensive, restorative | 4 passed in 1,002 s; budget 4 solved there in 5,535 s |
| 32 (Work Order 11) | the laptop (24 cores) | offensive and restorative | re-solved in 315 s (PR 32 description) |
| 32 (Work Order 11) | UA lab PC SH-2031-CBHPC | the four defensive keys | budget 3 in 819 s, budget 4 in 5,529 s; slow re-solve 2 passed in 6,330 s |

PR 10b's CI run is the full Linux re-solve: it re-solved every key then built, the restorative and offensive keys, on Linux as well as Windows, and matched them. From PR 30 on, CI checks keys without re-solving.

### The hand trace

The design side's sealed hand trace of scenario 7 (`test_hand_trace.py`, Phase 1) passed unchanged throughout Phase 2. The plan policy (PR 26), repair by damage state (PR 27) and the repair-timing changes (PR 32) each left the reference runs and the hand trace byte-identical.

**Whole suite at close:** 1,546 tests in the main selection and the 5 key re-score tests, all passing, with 96% line coverage of `src/` (on SH-2031-CBHPC before PR 33's push; CI runs both on Windows and Linux).

### Waiting for later phases

- The MIP cross-check: held for after the proposal (decision 0021).
- The informative answer key: Phase 4, against the pipeline's belief.
- The decision-relevant dose: zero in every key until error is planted (Phase 3).
- Realized error, quiet planting against planted error, and "zero error reproduces the clean emission": Phase 3.
- Realism ranges: Phase 5.

## What the keys say about the pilot

Current values from `tests/golden/pilot_answer_keys/`, in weighted service-hours. The restorative and defensive models minimize; the offensive model maximizes, against the calm world's 0.

| Model | Request | Optimum | Ties | Against | Best answer |
|---|---|---|---|---|---|
| Restorative, scenario 7 | Lifeline (4) and Equal (9) | 30.75 | 4 | the default crew order, 52.25 | crew 1: SWM-TEL-L0001, SWM-POW-L0004; crew 2: SWM-TEL-L0002 (the crews interchangeable) |
| Offensive, k = 2 | Lifeline (2) | 4,467.35 | 3 | no strike, 0 | SWM-FUE-0001 with SWM-HLT-0001 |
| Offensive, k = 2 | Equal (7) | 988.125 | 3 | no strike, 0 | SWM-FUE-0001 with SWM-TEL-0001 |
| Offensive, k = 3 | Lifeline (3) | 4,690.85 | 3 | no strike, 0 | SWM-FUE-0001, SWM-HLT-0001, SWM-HLT-0004 |
| Offensive, k = 3 | Equal (8) | 1,021.4 | 3 | no strike, 0 | SWM-FUE-0001, SWM-HLT-0004, SWM-TEL-0001 |
| Defensive, budget 3 | Lifeline (0) and Equal (5) | 2.625 | 32 | no action, 8.59375 | protect SWM-TEL-L0002, alone or with any one reserve |
| Defensive, budget 4 | Lifeline (1) and Equal (6) | 1.03125 | 1 | no action, 8.59375 | protect SWM-TEL-L0001 and SWM-TEL-L0002 |

- **Nearest supplier finds the optimum in every model** (distance 0 in all ten keys).
- **Most connections first and biggest first** miss it everywhere except one key: most connections first strikes an optimal pair at k = 2 under Equal. In the defensive keys they find nothing better than no action (distance 1); in the restorative keys they put a crew on SWM-POW-L0004 first (distance 1.30 Lifeline, 0.85 Equal).
- **No reserve changes any run.** In these storms only masts lose service, through cut telecom lines, and every power cut has a second feed. At budget 3 the 32 tied answers are the protection of SWM-TEL-L0002 alone or with any one of the 31 reservable dependencies; at budget 4 the only optimum spends all four units on two line protections.
- **Spread.** The defensive questions are sharp: at budget 4, 1 answer in 65,277 lies within 5% of the optimum. The offensive questions are flatter: at k = 2 under Equal, 24% of the 276 strikes lie within 5%.

## What departed from the design, each with its record

- **The informative key moved to Phase 4.** It needs the pipeline's belief, which Phase 2 does not have (ruling Q9; decision 0018; Build Game Plan, Phase 2).
- **The MIP is held.** Phase 2 closes on brute force; the cross-check waits for after the proposal, with the crew-rules sheet v0.2 as its formulation (decision 0021).
- **Telecom dependencies take no reserve.** The engine never draws a stock on a telecom dependency, so a telecom reserve could never drain. Reserves go only on power, water, fuel and transport (PR 30, question 1; WO-10c answers 1; decision 0018; structure v0.18 §5). The pilot's reservable dependencies fell from 47 to 31, and the defensive answers from 19,984 to 6,752 at budget 3 and from 259,289 to 65,277 at budget 4.
- **The uniqueness check is replaced by the spread.** A near-tie is information, not a failure: each key reports the share of answers within 1, 5 and 10% of the optimum and a random answer's mean distance (ruling Q11; decision 0018; structure v0.17 §5 and §7).
- **Stacked PR 28 and its repair, PR 29.** PR 28 (the offensive model) was opened against `wo10f/repair-state`, the branch of PR 27. PR 27 merged to main at 01:05:19 UTC on 2026-10-21, and PR 28 merged 23 seconds later into `wo10f/repair-state`, so the offensive model never reached main. PR 29 brought the same commit, `d39e727`, to main ("Bring PR 10b (the offensive model) to main"; merge `87058bb`).
- **The repair-state departure.** The engine looked repair records up by node alone, so every damaged facility took complete damage's repair. Fixed in its own pull request before PR 10b; no pilot golden moved (PR 26, question 5; WO-10a answers 5; decision 0019).
- **Two engine bugs found while writing the crew rules as equations** (decision 0020, E1 and E2): a cancelled switching trip could strand a newer one; a stock that ran out mid-step passed the full need to the next stock instead of the remainder.
- **The repair-timing rulings** (R1–R5 and MIP sheet item 11; decision 0020; structure v0.19): Hazus's time to rebuild is the wrong quantity for a 72-hour window. A facility has a rebuild and a service-restored path, and whichever finishes first sets its state; a rebuild job opens when its parts are ready; slight and moderate damage have no parts wait; at extensive and complete damage, service comes back inside the window only by a class's quick path. This reopened rulings T6 and T11 and decision 0011's split of the Hazus time.
- **The black-start limitation.** A completely collapsed loop with no outside supply stays down for the window; in the pilot, the power, fuel and water loop. No key's optimum depends on it, and a rule is to be ruled after the proposal (decision 0021; structure v0.20 §4.5).
- **`transfer_form:step` arrives in Phase 5.** The spec holds it for later worlds, and the engine refuses it (PR 27, question 1; decision 0018).
- **Placeholders.** The 48-hour instance bound (`solve.instance_bound_h`, open decision 6) and the quick-path table (`repair.service_restore.quick_paths`) stand until they are ruled.

# Records kept while Phase 2 was built

## The frame and the restorative model (Work Order 10, PR 10a, PR 26; decision 0018)

**What was built.**
- **Recipe schema version 4** and its migration, and the pilot's ten requests.
- **`swm solve <recipe> -o <dir>`** writes one key per request to `answer_keys/`, an index, and one bz2-compressed answers file per search holding every answer and its objective under each weighting. The informative model is refused (Q9).
- **Every key holds** the stamp, the optimum with every tie, the measure and its range, the spread, the three rules of thumb as distances, true criticality for every node, the dose (0 until Phase 3) and the note that the key is optimal against the named scenarios.
- **The ceiling.** Each search is timed on a sample first and held under `solve.instance_bound_h` (48 h, a placeholder). Times go to the console only, never into a key.
- **The engine** takes a crew plan as its crew policy beside the default order, which is unchanged. The three ruled dynamics rules are checked when a run starts.
- **The registry:** `solve.spread_bands_pct` and `solve.instance_bound_h`; the "acceptability threshold" objective retired.

**How it was tested.**
- Every reference run and the hand-trace test are byte-identical under the default order.
- The scenario 7 keys are golden: optimum 30.75, four plans tied (the crews interchangeable, and SWM-POW-L0004 costs no service-hours since its load has a second feed), against the default order's 52.25.

**PR 26 answers (WO-10a answers; decision 0018).**
- No action for the restorative measure is the default crew order.
- Biggest first ranks by each element's share of its layer's total in the same unit; the key states the basis.
- The nearest-supplier copy moves only couplings not already among the nearest, each to the next nearest unused eligible supplier, keeping κ and running on no line.
- A registry role, `theta_role: answer_key`, for the spread bands and the instance bound, outside Θ like the objectives.
- The stamp's `assumes` value no longer repeats its own label.

**Golden changes.** The world goldens moved only by the registry stamp and the resolved recipe's version and requests; after the answers, by the role edit's stamp, and the keys in the `assumes` line and the new basis line.

## Repair by damage state (WO-10a answers 5, PR 27; decision 0019)

**What was built.** Repair records are kept by (node, damage state). A storm-damaged facility takes the record for the state its scenario drew; a strike names complete damage; a node with several records and no named state stops the run. The trace pack's damaged-facility table reads the same records. `BUILT_FEATURES` lists everything built through Phase 1 and PR 26.

**How it was tested.** A facility damaged at each state takes that state's crew work and lead time; a strike takes complete.

**Golden changes.** None. No pilot scenario damages a facility. The severity-70 copy's one damaged facility, SWM-POW-0001 at slight in scenario 5, now takes 2.1 h of parts lead and 8 h of work instead of 1,428.4 h and 168 h, but its runs are byte-identical: both crews spend the window on two collapsed tower lines.

## The offensive model (Work Order 10, PR 10b, PRs 28 and 29; decision 0018)

**What was built.**
- Every set of k distinct nodes struck at hour 0 on the calm world, each with complete damage named explicitly and repaired by the crews in the default order. Lines are not targets.
- The mirrored measure: (optimum − objective) ÷ (optimum − no-strike objective), the no-strike objective being the calm world's 0.
- Rules of thumb: most connections first and biggest first strike the top k of their ranking; nearest supplier strikes the best set found on the copy, scored on the true world.
- A batch of 64 runs or more is spread across every core; results come back in the order asked, so no key depends on the core count.
- The key builder works on answers as text, shared by the restorative and offensive searches; the restorative keys stayed byte-identical.

**How it was tested.** CI re-solved every key on Linux and Windows and matched the goldens (117 min and 80 min in the test step).

**Golden changes.** The four offensive keys and their two answers files were added. Nothing else moved.

**The merge.** See "Stacked PR 28 and its repair, PR 29" above.

## The defensive model and CI's key checks (Work Order 10, PR 10c, PR 30; decision 0018)

**What was built.**
- **The search (E1–E4).** Up to the budget, a ceiling: protect condition (cost 2) on any element the storm can damage, or add a reserve (cost 1) on a reservable inbound dependency, at most one each. The objective is the mean of the 8 scenarios' weighted service-hours.
- **The reserve:** the window's hours at the node's full draw, added to the node's first stock for that commodity, or a new stock where it has none (E2, `AddStock`).
- **What is skipped, each provably identical:** an undamaged scenario is one run; a protection of an element a scenario did not damage is left out of that scenario's run; equal runs are played once.
- **`swm solve` options:** `--request` solves chosen searches, the index rebuilt from every key in the folder; `--ceiling-h` sets a lower ceiling for one run.
- **CI's checks** replace E6's sample rule for every model (above). The re-score runs as its own job without coverage, and the pilot's solver inputs are built once per session, after the first push took 56 and 59 minutes in its test step.

**The storable-reserve ruling (WO-10c answers 1).** `solve.reservable_commodities` = [power, water, fuel, transport], an answer-key setting, grade J, with the alternative "every dependency, telecom included". A test checks that no telecom dependency is offered a reserve.

**How it was tested.** Each skip holds on a sample when run in full; spending under the budget is searched; every key passed the CI checks and the slow re-solve.

**Golden changes.** The budget-3 keys were added first, then re-solved under the storable-reserve action set: 6,752 answers, optimum 2.625 under both weightings, losing only its telecom-reserve ties. The budget-4 keys were added: 65,277 answers, optimum 1.03125, no ties. The registry entry moved the resolved recipe's hash, so every offensive and restorative key was regenerated; each differed only in its `assumes` line, and their answers files were byte-identical.

## Repair timing and engine fixes (Work Order 11, PRs 31 and 32; decision 0020)

**What was built.**
- **A1:** a cancelled switching trip no longer strands a newer one; only an unassigned trip is cancelled, and the node-to-trip index stays consistent.
- **A2:** a stock that runs out mid-step passes on only the uncovered share of the need, at the next stock's own draw rate.
- **Repair timing:** a rebuild job opens at the first 15-minute step at or after its parts-ready hour, and no crew waits on site; slight and moderate damage have no parts wait; at extensive and complete damage, a node gives service inside the window only by its class's quick path (`repair.service_restore.quick_paths`). Crew quick paths (transmission substation, pumping station, water storage, airport) are crew jobs `quick:<node>`, open at hour 0 in the default order; the distribution substation and the mast keep their mobile units.
- **Rule card 8** reworded and approved by Foreman; its drill answers 16 h.

**How it was tested.** `test_engine_fixes.py` (A1, A2) and `test_repair_timing.py` (R1–R5, item 11); the reference runs and the hand trace byte-identical; every key re-solved and passing the slow re-solve.

**Golden changes.**
- **World goldens:** the registry stamp, the manifests' Theta entries of the three changed rules, and card 8's printed text.
- **Offensive keys:** a struck airport or water storage now comes back by its quick path, and A2 lets the exchange's generator run a step longer. Every optimum stands (4,467.35, 988.125, 4,690.85, 1,021.4).
- **Restorative keys:** answers byte-identical (optimum 30.75); only criticality moved, as no crew is now held on site.
- **Defensive keys:** every optimum, answers file, spread and rule of thumb unchanged; only criticality moved, most nodes' increase falling to their own hours out, with SWM-WAT-0004 and SWM-TRN-0004 coming back by their quick paths.

## The close (Work Order 12, PR 33; decision 0021)

**What was built.** Decision 0021; the MIP-agreement amendments to CLAUDE.md §7, the Build Game Plan, WO-10, structure v0.20 and Pilot Spec v0.9; the black-start line in structure §4.5; this entry; and the CHANGELOG's `0.2.0`.

**How it was tested.** Documents only: the main test selection and the key re-score checks pass, and no golden, answer key or reference run moved.
