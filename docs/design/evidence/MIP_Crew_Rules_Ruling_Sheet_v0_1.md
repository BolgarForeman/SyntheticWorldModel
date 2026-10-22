# The MIP cross-check: crew rules as equations, and the software: ruling sheet v0.1

*2026-10-22 · design side, for Foreman · to be ruled one item at a time · prerequisite for PR 10d (Work Order 10, Part F) · read against `src/swm/dynamics/engine.py` and `travel.py` on main at 5a94145*

## What this is for

Brute force has found every pilot answer key by trying every answer in the engine. The MIP (mixed-integer program) is a second, independent way to find the same keys. It writes the engine's rules as equations and lets a solver find the provable best answer. Two reasons it matters (ruling Q10, 2026-10-20):
- **It checks brute force.** The MIP must agree with brute force on every key's score.
- **It is the solver for larger worlds,** where brute force cannot reach.

The MIP is only a check if it plays the same world by the same rules. So every rule the engine applies must appear as an equation, exactly, with no slack. This sheet inventories those rules, starting with the crews, the hardest part; Part 2 lists the rest of the dynamics. It ends with the items to rule.

## The software

- **Solver: HiGHS** (ruled Q10). It is open-source under the MIT licence, maintained at the University of Edinburgh, and the strongest free MIP solver. It is called from Python through its own package, `highspy`.
- **Alternatives considered:**
  - **Gurobi:** you hold a UA licence token. It is faster on hard MIPs but proprietary, so it can never be a dependency of the published code or run in CI (CLAUDE.md §9a). Item 9 asks whether to allow it for local comparison runs only.
  - **OR-Tools CP-SAT** (Apache 2.0): a constraint solver that handles scheduling rules naturally. It is the fallback if HiGHS cannot carry the crew-policy constraints at study scale.
  - **Modelling layers** (Pyomo, PuLP): not needed. `highspy` builds models directly, which keeps the dependency list to one.

## Notation

- **Steps** k = 0 … K, of length Δ = 0.25 h; K = 288 for the 72-hour window.
- **Crews** c ∈ C, each starting at its base b_c at hour 0. The pilot has 2.
- **Repair jobs** j ∈ J: one per damaged facility and one per downed line, after protection. Where damage depends on the decision (protect, strike), a binary u_j says whether job j exists.
- **Travel** τ(a, b), in hours:
  - road km ÷ road speed, plus off-road km ÷ off-road speed, plus the mobilisation delay for a sea trip;
  - computed from the world's road legs before solving, so it is data, not a variable.

## Part 1. Every crew rule the engine plays, as an equation

| # | Rule in the engine | Where | As equations |
|---|---|---|---|
| C1 | **The jobs.** A damaged facility takes the repair record for its drawn damage state (a strike: complete). A downed line is one job over all its failure points, in km order along the line. An unrepairable class makes no job | `_open_jobs`, `facility_repair` | The job set and each job's data are fixed per damage pattern. u_j switches a job on where protection or a strike decides the damage |
| C2 | **A job's timeline.** Travel to the first site; crew-bound lead (2 h, "assess") at the first site only; wait until the parts-ready hour P_j if later; work. A line's later points: walk along the line (km ÷ off-road speed), then work each | `_work`, `_along_line_hours` | Arrival A = start + travel. Work starts at W = max(A + 2, P_j), written exactly with one binary. Finish F = W + Σ work + Σ walks; the walks are data |
| C3 | **Sequence-dependent travel.** A crew goes from where its last job ended (the last failure point of a line) to the next job's first site; its first trip is from its base | `_work` (crew.site) | Slots: y[c,p,j] = 1 if job j is crew c's p-th job. Travel into slot p = Σ τ(end_i, s_j)·z[c,p,i,j], with z = y[c,p−1,i]·y[c,p,j] linearised; slot 1 travels from b_c |
| C4 | **When a crew starts.** A crew free before a step ends is dispatched in that step and starts at its free time; if no job is open it waits for the first step one opens | `_assign` | Start S[c,p] = F[c,p−1] for repair jobs (open from hour 0). A job released later (switching, C8) starts at max(F, release step), written exactly with one binary |
| C5 | **The default crew order** (defensive and offensive models). The crew that comes free first (ties: crew id) takes the open job with the smallest key: tier (towered lines and transmission substations; then distribution substations and feeds to end uses by the highest Lifeline weight supplied; then the rest), then travel hours from where it stands, then job id | `_assign`, `crew_order`, `substation_weight` | The policy is not optimised; it is a rule the schedule must obey. For each dispatch (c, p) and every other job j′ still open at that moment: if y[c,p,j] = 1, then key(c,p,j) ≤ key(c,p,j′), lexicographically. "Still open" and "first free" need order binaries between dispatches. This is the hardest block; see items 2 and 3 |
| C6 | **A plan** (restorative model). Each crew works its ordered list. A switching trip that opens is weighed against the crew's next planned job by the default key | `_assign_planned` | y is the decision, free apart from the switching comparison, which uses C5's lexicographic constraint over {next planned job} ∪ {open trips} |
| C7 | **When a repair takes effect.** At the first step at or after the finish time (with the engine's 1e−12 allowance) | `_complete` | An integer k_j with Δ·k_j ≥ F_j − 1e−12 and Δ·k_j < F_j + Δ − 1e−12. A state flag r[j,k] = 1 exactly when k ≥ k_j |
| C8 | **Manual switching trips.** A substation that loses all power in its own layer is marked de-energised. When its power returns while its telecom is down and its condition is full, a switching trip opens at that step: on-site 1 h, no lead, priority inherited from the job that completed in that step (else its own). It is cancelled if telecom returns first. A facility repair at a substation switches it on site | `_switching`, `_open_switching`, `_cancel_switching`, `_finish` | Potential trips: one slot per substation per de-energised episode, capped (item 4). Each slot's release step is bound to the world-state conditions by indicator constraints; its priority is the inherited key; a cancelled slot frees its crew slot |
| C9 | **Mobile units** (mobile substations, mobile cell sites). At hour 0 each unit kind goes to eligible damaged nodes in crew order, up to the number of units. A unit arrives at a fixed hour and raises the node's condition to its restored share | `_dispatch_units`, `_complete` | Greedy allocation as prefix counts: node n of kind m gets a unit if it is damaged and fewer than U_m higher-ranked damaged nodes of kind m exist. Condition = max(condition, share) from the arrival step on (item 5) |
| C10 | **Unlimited crews** (a relaxed limit). Every job gets its own crew at once, from the nearest base | `_assign_unlimited` | Start 0 from argmin τ(b, s_j), which is data; no sequencing |
| C11 | **Other relaxed limits.** Speeds, crew-bound lead, parts lead and switching time can each be set to zero | `trip_hours`, `_open_jobs` | Data: the constants become zero |
| C12 | **What a completion does.** A line comes back; a facility's condition returns to full and its de-energised mark clears; a switching trip clears the mark | `_finish` | r[j,k] enters the dynamics of Part 2: line availability, condition, de-energised flag |

**Pilot size.** The pilot has 2 crews and 0–4 jobs per scenario (at most 3 lines plus any struck nodes), so the slot formulation is small. At study scale it grows as |C|·|J|²; item 7 asks for size and time to be measured first.

## Part 2. The rest of the dynamics the MIP must also carry

These are not crew rules, but the crews' finish times only matter through them. Each must also be exact.

| # | Rule | Where | As equations | Difficulty |
|---|---|---|---|---|
| D1 | A node's state = condition × min(its responses), each dependency's received share: groups summed, capped at 1; within a group the weakest edge; each edge κ × g(supplier state), with a downed line giving 0 | `_states`, `_received` | min, max and caps as exact linearisations, each with binaries | Moderate |
| D2 | Transfer forms: linear, or threshold at θ = 0.5 | `_transfer` | Threshold: one binary per edge per step | Easy |
| D3 | Responses: throttle; trip at 0.9; step to a floor on a running generator with fuel, else trip | `_respond`, `_cover` | Binaries for trip, and for cover (a stock above 0, a generator running) | Moderate |
| D4 | Own-layer supply from the sources down, best in-link, a downed line giving 0, a de-energised substation receiving 0 | `_own_levels`, `_delivered` | max over in-links; layered passes from the sources (acyclic within a layer) | Moderate |
| D5 | **Settling.** Each step repeats D1–D4 from the previous step's states until nothing changes; then switching is checked and the step settles again | `_settle`, `_settle_with_switching` | **Item 6: where couplings form loops (power ↔ telecom control in the pilot), more than one settled state can exist, and the engine's history picks one** | **Hard** |
| D6 | Telecom tolerance: full function for T hours after loss, an optional ramp, then d_eff; the clock resets when service returns | `_tolerance_level`, `_clocks` | Run-length counters as integer variables per dependency per step | Moderate |
| D7 | Stocks drain at the actual draw (a generator on floor draws its full rate), in order (battery before generator); refill by kind (battery 12 h, main, spare pumping, none) when supplied | `_draw`, `_refill`, `_spare_pumping` | Continuous levels with binaries for empty, full and supplied | Moderate |
| D8 | Generators: fail-to-start; stop after their drawn run hours | `_generator_runs`, `_draw` | Data plus a run-hours counter | Easy |
| D9 | Fuel deliveries: a schedule starts when a consumer first loses power (12 h lead), then every 24 h while the depot is up; they stop when the tank is full and power is back | `_deliver`, `_losses` | Event logic: due-time integers and binaries per delivery edge | Moderate |
| D10 | Actions: protect (no damage); a reserve (a new stock, or hours added) | `_actions`, `_add_stock` | First-stage binaries shared by every scenario | Easy |
| D11 | The score: weighted service-hours lost, summed over steps, averaged over the scenarios | `Run`, `solve/weights.py` | Linear in the states | Easy |

## Items to rule

**Q1. Exactness: every rule an equality, no slack anywhere.**
- An inequality like "work starts at or after arrival" lets the solver pick a later time. The attacker's objective, maximising loss, would exploit that: the MIP would find a "better" attack the engine could never play.
- So every max, min, trip and timer is written exactly, with binaries.
- The engine's own tolerances are copied: the 1e−12 allowance on a completion's step, exact comparisons on states.
- *Recommended.*

**Q2. The default crew order inside the MIP.** For the defensive and offensive models, the crews follow the engine's dispatch rule; nobody optimises them.
- **A. Write the rule as constraints** (C5): at every dispatch, the chosen job's key is no larger than any other open job's. The schedule is then forced to be exactly the engine's. *Recommended:* it is the only option that checks the same question.
- **B. Let the MIP optimise the crews too.** Simpler, but it answers a different question (what if crews were sent optimally?), so it cannot agree with brute force.
- **C. Precompute the crew schedule with the engine for each damage pattern and feed it in as data.** Simple, but then the MIP no longer checks the crew logic independently.

**Q3. Ties in the crew order.** The key compares tier and weight, then travel hours (real numbers), then job id.
- **A. Lexicographic constraints with a data-derived margin.** Compare each part in turn, with a margin smaller than the smallest gap between any two distinct travel times in the world, computed and reported before solving. That decides ties exactly as the engine does. *Recommended.*
- **B. One weighted key with small multipliers.** Shorter, but floating-point weights can misorder near-ties.

**Q4. Manual switching trips** (C8). These are crew jobs that appear during a run, so they can't be listed beforehand. No pilot reference run produced one, but other worlds will.
- **A. Model them:** a capped number of trip slots per substation, released by indicator constraints on the world state. After solving, the engine run of the MIP's optimum must show the cap never bound. The cap is a registry placeholder: 2 per substation per window. *Recommended:* the MIP is meant to scale to study worlds.
- **B. Leave them out,** and accept a key only if the engine shows no switching trip in the optimum's runs; otherwise report "MIP not applicable". It is smaller now, but the gap must be closed later.

**Q5. Mobile units** (C9). Exact greedy allocation by crew order, as prefix-count constraints, with arrival hours as data. *Recommended.* There is no simpler exact form.

**Q6. Which settled state the MIP finds** (D5, the largest risk outside the crews).
- **Background.** Each step, the engine repeats the cascade from the previous step's states until nothing changes. Where dependencies form a loop, more than one settled state can be consistent. For example, power needs telecom control and telecom needs power: both up is consistent, and so is both down. The engine's history picks which.
- A MIP asked only for "a consistent state" could pick the other one, usually the better one for whoever is optimising. It would then disagree with brute force for a reason that has nothing to do with the answer.
- **A. Encode the settling passes.** In each step, a fixed number of pass layers, each computed from the one before, starting from the previous step's states, with a check that the last pass changes nothing. The number of passes is set from the data: the pilot's reference runs never needed more than 2 outer passes. It is exact, and costs size. *Recommended.*
- **B. Prove each world's settled state unique** (every loop broken within a step, for example by a tolerance timer), and refuse worlds where it isn't. It is smaller where it applies, but it doesn't hold for the pilot's power and telecom loop once the tolerance has run out.
- **C. Take the most favourable settled state, declared as a departure.** It is simple, but it can disagree with the engine, which defeats the check.

**Q7. Build order and measurement first.**
- Restorative first: one scenario, the plan is the decision, and it has the fewest binaries. Then offensive (calm world, the strike set as the decision). Then defensive: all 8 scenarios in one MIP sharing the first-stage actions.
- For each, the coder reports the model's size (variables, binaries, constraints) and a timed solve before the full set runs.
- *Recommended.*

**Q8. Independence from the engine.**
- The MIP reads the world's data: nodes, dependencies, stocks, repair records, settings, and the travel matrix built from the road legs.
- It imports no engine function: not the crew order, not the trip hours, not the responses. Each rule is rewritten from the spec and this sheet.
- For the optimum, the coder also compares the MIP's implied schedule and completion steps with the engine's run of the same answer, as a diagnostic.
- *Recommended.*

**Q9. Solver settings, and Gurobi.**
- **HiGHS through `highspy`,** pinned in the lock file:
  - one thread and a fixed random seed, for repeatable results;
  - relative gap 0, so the optimum is proven, not approximate;
  - feasibility tolerance 1e−9;
  - a per-key time limit from the registry (placeholder 4 h).
- The key records the solver's name and version, the MIP's objective to 6 decimals, and agreement with brute force. Times and node counts go in the report, never the key, so key bytes stay identical across machines.
- **Gurobi:**
  - **A. Not used.**
  - **B. Allowed for local comparison runs only,** under your UA token. It is never a dependency, never in CI, and its results are never written into a key. *Recommended:* a second commercial solver agreeing is extra assurance at no cost to the published code.

**Q10. A MIP that doesn't finish.**
- A key whose MIP hits its time limit is reported as "MIP unfinished", with its best bound and gap. It is never counted as agreement.
- Phase 2 closes only when every key agrees, or when you rule on the ones that don't.
- *Recommended.*

## After the rulings

- Work Order 10, Part F, is written in full from these rulings: model blocks C1–C12 and D1–D11, the tests, and the measurements.
- The spec, §5 "How keys are found", gains a short paragraph on the MIP formulation and its exactness rule.
