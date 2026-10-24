# The MIP cross-check: crew rules as equations, and the software: ruling sheet v0.2

*2026-10-22 · design side, for Foreman · to be ruled one item at a time · prerequisite for PR 10d (Work Order 10, Part F) · read against `src/swm/dynamics/` and `src/swm/solve/` on main at 5a94145*

*v0.2: an independent review against the code, which also ran the pilot's storm, strike and criticality runs, corrected about 25 details in v0.1. It also found three things in the engine itself, now in Part 3.*

## What this is for

Brute force has found every pilot answer key by trying every answer in the engine. The MIP (mixed-integer program) is a second, independent way to find the same keys: it writes the engine's rules as equations and lets a solver find the provable best answer (ruling Q10, 2026-10-20). It checks brute force, and it is the solver for worlds too large for brute force.

It is only a check if it plays the same world by the same rules. So every rule the engine applies must appear as an equation, exactly, with no slack. This sheet:
- inventories the crew rules (Part 1);
- inventories the rest of the dynamics (Part 2);
- reports what writing it turned up in the engine (Part 3);
- sets out the items to rule.

## The software

- **Solver: HiGHS** (ruled Q10). It is open-source under the MIT licence, maintained at the University of Edinburgh, and the strongest free MIP solver. It is called from Python through its own package, `highspy`, which builds models directly, so no modelling layer is needed.
- **Considered:**
  - **Gurobi** (your UA token): faster on hard MIPs, but proprietary. It can never be a dependency of the published code or run in CI (CLAUDE.md §9a). Item 9 asks about local comparison runs.
  - **OR-Tools CP-SAT** (Apache 2.0): handles scheduling rules naturally. It is the fallback if HiGHS cannot carry the crew-policy constraints at study scale.

## Notation

- **Steps** k = 0 … K, each Δ = 0.25 h long; K = 288 for 72 hours.
- **Crews** c ∈ C (2 in the pilot), each at its base b_c at hour 0.
- **Repair jobs** j ∈ J. Where the decision sets the damage (protect, strike), a binary u_j says whether job j exists.
- **Travel** τ(a, b) is data, computed before solving from the road legs, and keyed by **site**, not node, because how a site is reached matters:
  - **a facility:** the access leg from the road is driven at road speed;
  - **a failure point on a line:** the leg from the road is walked, at off-road speed;
  - **two sites no road joins:** straight-line km at road speed, plus the mobilisation delay.
- **A job's first site** is its lowest-km failure point for a line.

## Part 1. The crew rules, as equations

| # | Rule in the engine | Where | As equations |
|---|---|---|---|
| C1 | **The jobs.** A damaged facility takes the repair record for its drawn damage state; a strike names complete damage. A downed line is one job over its failure points in km order. No job for an unrepairable class, or for a node with no repair record. Parts lead = max(0, Hazus lead − 2 h), clocked from hour 0. **Pilot parts leads, measured from the built world (each node draws its own):** slight 0–106 h (median 9); moderate 0–445 h (median 64); extensive 0–2,837 h (median 486); complete 30–5,406 h (median 1,889). The pilot's storms damage lines only, so facility jobs come from strikes and criticality runs, at complete damage, and almost none finishes inside 72 h (see Part 3, E3, and the repair-timing sheet) | `_open_jobs`, `facility_repair`; world.py L399 | The job set and data per damage pattern; u_j where the decision sets the damage |
| C2 | **A job's timeline.** Travel to the first site; the 2 h crew-bound lead ("assess") at the first site only; wait there until the parts-ready hour if later; work. Later failure points: walk along the line, then work | `_work`, `_along_line_hours` | Arrival A = start + τ. Work starts at W = max(A + 2, P_j), written exactly with one binary. Finish = W + Σ work + Σ walks |
| C3 | **Sequence-dependent travel.** A crew's position jumps to its job's last site **at dispatch**; the next trip starts there; the first trip starts at the base | `_work` (crew.site) | Slots y[c,p,j]; travel into slot p = Σ τ(end_i, first_j)·z[c,p,i,j], with z the linearised product y[c,p−1,i]·y[c,p,j] |
| C4 | **When a crew is dispatched, and starts.** At each step, every crew whose free time is strictly before the step's end is dispatched, possibly more than once in a step, earliest free first, ties by crew id. It starts at max(free time, step start). Repair jobs are open from hour 0. **Dispatch happens before the crew's own previous repair takes effect**, if that repair finishes mid-step: dispatch tests "free < t + Δ" with no allowance, while completion tests "finish ≤ t + 1e−12". So a crew that finishes mid-step cannot take the switching trip its own repair opens; one that finishes exactly on a step boundary can. Decisions are never revised | `_assign`, `_complete` | Start S = max(F_prev, release step), written exactly. Dispatch-step integer d with Δ·d ≤ F_prev < Δ·(d+1). The asymmetry is copied, not smoothed |
| C5 | **The default crew order** (defensive and offensive models). The earliest-free crew takes the open job with the smallest key: tier (0 towered lines and transmission substations; 1 distribution substations and feeds to end uses; 2 the rest), then minus a weight, then travel hours from where it stands, then the job-id string. The weight is always the **Lifeline** weight, even in Equal-weight requests, because it is the world's crew policy, not the request's scoring. A distribution substation's weight is the highest of its own and its direct power consumers', read from the world's dependencies (removed edges still count). Job ids sort `repair:` before `switch:`, so at equal key a repair beats a switching trip | `_assign`, `crew_order`, `substation_weight` | Not optimised: a rule the schedule must obey. At each dispatch, the chosen job's key ≤ every other open job's, lexicographically (items 2, 3). "Open" and "earliest free" need order binaries between dispatches |
| C6 | **A plan** (restorative model). Each crew works its ordered list. Any open switching trip is weighed against its next planned job by the default key. A crew with an empty plan still takes trips. A crew with nothing to do sits out only the current step | `_assign_planned` | y is the decision; the switching comparison as C5 |
| C7 | **When a repair or mobile unit takes effect.** Completions apply at the first step with finish ≤ t + 1e−12, in (finish time, key) order | `_complete` | Integer k_j: Δ·k_j ≥ F_j − 1e−12 and Δ·(k_j − 1) < F_j − 1e−12; a flag r[j,k] = 1 exactly when k ≥ k_j |
| C8 | **De-energised substations and switching.** In its own layer, a substation whose raw power (computed with every de-energised mark ignored) falls to 0 is marked de-energised. Marking does not re-settle the step. When raw power returns: **if its telecom is up, or its condition is below full, the mark clears at once ("remote switching") and the step re-settles.** Otherwise a manual trip opens (on site 1 h; no lead; released at that step). Telecom "up" means the raw received share is 1, ignoring the tolerance. A trip's priority is the smallest key among the repair jobs completed in that step (mobile units and other trips don't count), else its own. An unassigned trip is cancelled if the mark clears first; an assigned one is still travelled and worked. A facility repair at a substation clears its mark on site | `_switching`, `_telecom_up`, `_open_switching`, `_cancel_switching`, `_finish` | Mark and trip slots per substation, capped (item 4); release, cancellation and clearing as indicator constraints on the world state of that step |
| C9 | **Mobile units.** At hour 0, each unit kind goes to the eligible nodes (damaged after protection) in (crew-order key, node id) order, with no travel term, up to the number of units. A unit arrives at a fixed hour, with the same 1e−12 allowance, and raises the node's condition to its restored share. It does not clear a de-energised mark, and does not set a trip's priority | `_dispatch_units`, `_complete` | Greedy allocation as prefix counts; condition = max(condition, share) from the arrival step (item 5) |
| C10 | **Unlimited crews** (relaxed limit): every job gets its own crew from the nearest base; a switching trip's crew starts at its release step | `_assign_unlimited` | Data. **Never used by answer keys**, which set no relaxed limits (runner.py) |
| C11 | **Other relaxed limits** (speeds, the 2 h lead, parts lead, switching time) become zero. Relaxing the lead does not move it into parts lead | `trip_hours`, `_open_jobs` | Data. Not used by answer keys |
| C12 | **What a completion does.** A line comes back; a facility returns to full condition and its mark clears; a trip clears its mark | `_finish` | Flags into Part 2 |

**Pilot size.** Storm scenarios damage lines only, 0–3 jobs. Strikes add up to 3 nodes; criticality runs reach 4 jobs. The slot formulation is small at pilot size and grows as |C|·|J|² (item 7).

## Part 2. The rest of the dynamics, as equations

| # | Rule | Where | As equations | Difficulty |
|---|---|---|---|---|
| D1 | State = condition × min(responses). A dependency's received share: groups summed, capped at 1; the weakest edge in a group; an edge delivers κ·g(supplier), **a telecom edge g alone**; a downed line 0 | `_states`, `_received` | Exact min, max and caps with binaries | Moderate |
| D2 | Transfer: linear, or threshold at θ = 0.5 (state ≥ θ) | `_transfer` | One binary per edge per step | Easy |
| D3 | Response: full if received = 1. Otherwise, if covered: **any cover that is not a generator gives full function in every mode**, and a running generator gives full function, or its floor on a floor dependency. Otherwise throttle (R) or trip (1 if R ≥ 0.9). "Covered" means the stock's level > 0 **at the start of the step**, so a stock that empties mid-step still covers that step | `_respond`, `_cover` | Binaries for trip and cover | Moderate |
| D4 | **Own layer.** Each non-source node's received share is the best in-link (a downed line gives 0; a de-energised substation receives 0). **Same-stage tie links run both ways, so this is not acyclic**: the engine takes the least fixed point, starting every node from 0, with up to N + 1 inner passes | `_own_levels`, `_delivered`; world.py L551–555 | Inner pass layers from 0 (item 6) | Hard |
| D5 | **Settling.** Each step repeats D1–D4 from the previous step's states, until nothing changes (cap 100). **Step 0 starts from every state at 1.** Then marks are checked, and the step re-settles if one cleared. Recorded passes reach **2 in storm runs and 6 in strike runs**, each holding a full inner D4 loop. A capped step records an unconverged state | `_settle`, `_settle_with_switching` | Outer pass layers (item 6) | Hard |
| D6 | **Telecom tolerance.** The applied share is R + (1 − R)·level, where the level is 1 while elapsed < T (strict), then an optional ramp, then d_eff. The clock advances after the step is recorded, on raw R < 1, and resets at R = 1 | `_response`, `_tolerance_level`, `_clocks` | Integer run-length counters | Moderate |
| D7 | **Stocks.** Draw at (1 − R) × rate, or the full rate for a generator on a floor, whatever the node's condition. Order: stocks that are not generators first, then by stock id. **A partial draw passes the full need, not the remainder, to the next stock** (Part 3, E2). Refill only for stocks not drawn this step and whose raw supply is full, by kind (battery over 12 h, main, spare pumping, none). **Added reserves never refill** | `_draw`, `_refill`, `_spare_pumping` | Continuous levels; binaries for empty and supplied | Moderate |
| D8 | Generators: fail to start; run hours accrue every step one is drawn on, even with an empty tank; it stops at its drawn run hours | `_draw`, `_generator_runs` | Counter | Easy |
| D9 | **Fuel deliveries.** Loss is stamped at the step of the recorded state; the first delivery is due 12 h later. The depot is "up" if g(depot state) > 0 on the first settled state. A missed delivery is retried every step, and the schedule re-anchors to the actual delivery, every 24 h. Amount = min(room, delivery·κ). Delivery stops when the tank is full and power is back, tested only when a delivery is made. A delivery re-settles the step | `_deliver`, `_losses` | Due-step integers and binaries per delivery edge | Moderate |
| D10 | **Actions.** Protect means no damage and no mobile unit. A reserve is a new stock, or hours added to the node's first stock in draw order. A generator tank that fails to start makes that reserve useless. Scenarios with no damage run with no actions | `_actions`, `_add_stock`, defensive.py L174–181, solver.py `defensive_plays` | First-stage binaries shared by every scenario | Easy |
| D11 | **Score.** Σ over steps k = 0 … K − 1 of (1 − x)·Δ at end uses (the state at step K excluded), times the request's weights; the defensive mean is taken per node with an exact sum, rounded to 6 decimals | records.py L132, `solve/weights.py` | Linear | Easy |

**The order of operations within a step, which the MIP must keep:**
1. apply completions, in (finish, key) order;
2. settle, with switching;
3. make deliveries, and settle again if fuel came;
4. record the state;
5. dispatch crews;
6. draw and refill stocks, advance the clocks, stamp losses.

**Exact comparisons to copy:** raw ≤ 0, received ≥ 1, elapsed < T, room > 0, state ≥ θ, R ≥ 0.9.

## Part 3. What writing this turned up in the engine

E1 and E2 are bugs; E3 is an ambiguity in the spec. The fixes change the engine, so they go in their own pull request before PR 10d. The MIP should copy the engine as fixed, not as it is today.

**E1. A cancelled switching trip can strand a newer one** (`_cancel_switching`). When a mark clears, the engine removes the node's trip from its index even if a newer trip for the same node is open, leaving that newer trip in the job list. A crew could later travel to switch a substation that no longer needs it. No pilot run produced a trip, so nothing has moved yet.
- **Ruling:** a fix. Only an unassigned trip for that episode is cancelled, and the index stays consistent.

**E2. A stock that runs out passes the full need to the next stock** (`_draw`). When a node's first stock covers only part of a step's draw, the next stock is charged the whole need again, not the remainder. The spec says stocks drain at the actual draw, so the second stock drains too fast.
- **Ruling:** a fix. Pass the remainder. The coder reports which reference runs and keys move, if any. Pilot nodes with two stocks on one supply would show it.

**E3. A crew waits on site for parts** (`_work`). The engine keeps the crew at the site from arrival until the parts are ready, logged as "wait for parts". The spec reads two ways (§4.5, "Repair and crews"):
- "Parts lead time … runs in parallel with no crew; in Phase 1 its clock starts at the end of the storm." Read alone, no crew is held for it.
- "A crew's sequence: assigned → travel → assess → repair once its parts are in → travel to the next job." Read alone, the crew waits after assessing, which is what the engine does.

So this is an ambiguity in the spec, not clearly a bug. It matters: a struck facility takes complete damage, whose parts lead in the pilot is 30–5,406 h (median 1,889), so a crew sent to it is nearly always held there for the rest of the 72-hour window and does no other work. That raises criticality and losses in any run with facility damage plus line damage. **Item 11.**

## Items to rule

**Q1. Exactness: every rule an equality, no slack anywhere.** An inequality like "work starts at or after arrival" lets the solver choose a later time, and the attacker's objective (maximising loss) would exploit it. So every max, min, trip, timer and dispatch is written exactly, with binaries, and the engine's own tolerances and comparisons are copied as Part 2 lists them. *Recommended.*

**Q2. The default crew order inside the MIP.**
- **A. As constraints:** at every dispatch, the chosen job's key is no larger than any other open job's. The schedule is then forced to be the engine's. *Recommended:* it is the only option that checks the same question.
- **B. Let the MIP optimise the crews.** It answers a different question (optimal crews), so it cannot agree with brute force.
- **C. Feed in the engine's schedule as data.** The crew logic is then no longer checked independently.

**Q3. Ties in the crew order.**
- **A. Lexicographic constraints with a data-derived margin.** Compare tier, then weight, then travel, then job id in turn. The margin is smaller than the smallest gap between distinct travel times, computed and reported before solving. *Recommended.*
- **B. One weighted key with small multipliers.** Shorter, but floating-point weights can misorder near-ties.

**Q4. Switching trips** (C8). No pilot run produced one (storms, strikes up to 2, criticality: all checked), but study worlds will.
- **A. Model them:** capped mark and trip slots per substation, with the cap a registry placeholder (2 per substation per window). The engine run of the MIP's optimum must show the cap never bound. *Recommended:* the MIP must scale.
- **B. Leave them out,** and accept a key only if the engine shows no trip in its optimum's runs; otherwise report "MIP not applicable".

**Q5. Mobile units** (C9): exact greedy allocation as prefix counts, with arrival hours as data. *Recommended*; there is no simpler exact form.

**Q6. Which settled state the MIP finds** (D4, D5).
- **Background.** Each step, the engine repeats the cascade from the previous step's states until nothing changes, and its own-layer supply from zero upwards. Where dependencies loop (power needs telecom control, telecom needs power; same-stage power ties run both ways), more than one settled state can be consistent. The engine's starting points pick one: all-up at step 0, then each step's history. A MIP asked only for "a consistent state" may pick another, usually the better one for whoever is optimising, and disagree with brute force for a reason that has nothing to do with the answer.
- **A. Encode the passes:** in each step, the outer settling passes (up to the most the data needs; 6 in the pilot's strike runs), each holding the inner own-layer passes from zero, with a check that the last pass changes nothing. It is exact, and costs size. *Recommended.*
- **B. Prove each world's settled state unique,** and refuse worlds where it isn't. It is smaller where it applies, but it doesn't hold for the pilot's loops.
- **C. Take the most favourable settled state,** declared as a departure. It is simple, but it can disagree with the engine, which defeats the check.

**Q7. Build order and measurement first.** Restorative first (one scenario; the plan is the decision), then offensive (calm world; the strike set), then defensive (all 8 scenarios in one MIP, sharing the first-stage actions). For each, the coder reports model size (variables, binaries, constraints) and a timed solve before the full set runs. *Recommended.*

**Q8. Independence from the engine.** The MIP reads the world's data (nodes, dependencies, stocks, repair records, settings, and the site-keyed travel matrix) and imports no engine function: not the crew order, not the trip hours, not the responses. Each rule is rewritten from the spec and this sheet. For each optimum, the coder also compares the MIP's schedule and completion steps with the engine's run of the same answer, as a diagnostic. *Recommended.*

**Q9. Solver settings, and Gurobi.**
- **HiGHS through `highspy`,** pinned in the lock file:
  - one thread and a fixed random seed;
  - relative gap 0;
  - feasibility tolerance 1e−9;
  - a per-key time limit from the registry (placeholder 4 h).
- The key records the solver name and version, the MIP objective to 6 decimals, and agreement. Times go in the report only, so key bytes stay identical across machines.
- **Gurobi:**
  - **A. Not used.**
  - **B. Allowed for local comparison runs only,** under your UA token. It is never a dependency, never in CI, and never written into a key. *Recommended:* extra assurance at no cost to the published code.

**Q10. A MIP that doesn't finish** is reported as "MIP unfinished", with its bound and gap, never counted as agreement. Phase 2 closes only when every key agrees, or when you rule on the rest. *Recommended.*

**Q11. A crew waiting for parts** (Part 3, E3). One spec line says the parts wait holds no crew; the next describes the crew repairing "once its parts are in"; the engine holds the crew on site.
- **A. The job opens when the parts arrive.** The job is not dispatchable until its parts-ready hour; then the crew travels, does the 2 h assessment and works. Crews spend the wait on other jobs. *Recommended:* the simplest reading of "in parallel with no crew", and one rule the MIP carries easily. **Ruled A by Foreman, 2026-10-22, "for now".** He also questioned the lead times themselves: no crew would stand 3,900 h (about 160 days) at one site, and that doesn't match how fast service comes back after major events. See the open item below.
- **B. Two visits:** a crew assesses early (2 h), leaves, and the job reopens for its work when the parts arrive. It is closer to field practice, but it is two jobs per repair and more crew logic to mirror.
- **C. As now:** the crew waits on site. It keeps today's results and every key; the spec's first line is reworded to match. But any facility repair in a 72-hour window locks up a crew for the rest of it.

## Open item raised with item 11: service restored versus rebuilt

Foreman, 2026-10-22: rebuilding a substation takes months, but getting one running again takes hours, or days when damage is widespread. The Hazus figures measure the rebuild. The world has no quantity for getting service back. This is taken up in its own sheet, `Repair_Timing_Ruling_Sheet_v0_1.md`. Item 11's ruling stands for whatever wait remains.

## After the rulings

- **A fix pull request first:** E1, E2 and the ruled Q11. It reports every reference run, answer key and golden that moves, with reasons.
- **Then Work Order 10, Part F,** written in full from these rulings: model blocks C1–C12 and D1–D11, the step order, the tests and the measurements.
- **The spec, §5 "How keys are found",** gains a paragraph on the MIP formulation and its exactness rule; §4.5 states the ruled parts-wait rule in one reading.
