# Pilot Spec — The Full Chain on a Hand-Checkable Constructed World

*v0.8 · 2026-10-20 · feeds Ch7 §7.2 and Figures 7.1, 7.2 and 7.4 · aligned with World_Generator_Structure v0.17 and the pilot recipe in the SyntheticWorldModel repository*

## Purpose

Run the whole chain, every sheet of Appendix B from world supply to the composed product, on a constructed world small enough to check by hand. Pose all four optimization member-classes on that one network, one small model each. Run the chain twice, once carrying doubt across every handoff and once flattening it at each seam, and score both runs against the known optimum. The pilot is the first working build of the generator and pipeline, and the code carries forward into the January build.

## What the pilot claims, and what it does not

It is a Phase 0 run in the sense of the generator design (§1.7.6). The proposal reports it as preliminary results showing three things: the chain executes end to end with doubt carried, the four classes can be posed on one network, and the gap between the two runs has a visible shape on a toy world. It does not answer RQ1(b) or RQ2. It is not pre-registered, and nothing it tunes is locked by it.

## The world

- **Size.** About 24 nodes, four per layer across the full layer set (power, telecom, water, transport, fuel, healthcare), with 40–55 edges including the cross-layer couplings (widened from 35–45 on 2026-09-29, and from 40–50 on 2026-10-03 when rule 4 added a feed; decision 0013 addendum). It fits on one page and a cascade can be traced by hand.
- **Substrate.** A small island with a mountain spine and a coastal plain. Nodes are sited by layer rules from the generator design.
- **Topology.** Each layer keeps its own signature: power meshed, water dendritic, healthcare a referral tree. Healthcare is the pure sink.
- **Couplings switched on.** Seven of the 21, chosen so a cascade crosses every layer and can be traced by hand: fuel → power, power → telecom, telecom → power, power → water, water → healthcare, power → healthcare, transport → fuel. The rest are generated and hidden. Density 0 (core dependencies only), dependencies from the table in World_Generator_Structure §4.3a. If the realised edge count falls outside 40–55, the build reports it rather than tuning.
- **Coupling.** Cross-layer edges carry commodity, coupling strength κ and a failure mode (throttle or trip). Reserves are drawn per node from context like every other unobserved quantity, and each reserve sets its buffer time τ (reserve ÷ draw) during the run. The earlier single planted reserve on the fuel→power link is superseded.
- **Sources.** One small source file per layer in its real container. Power (OpenStreetMap and the WRI plant database) and healthcare (OpenStreetMap and the government facility register) each have two sources that deliberately disagree; the other four layers have one. Fuel and healthcare sources report nodes only.
- **Crews.** The world has two repair crews.
- **Disruption.** One storm corridor is drawn as a shared latent field (Structure §4.3b), and element damage is drawn conditionally on it. The storm is a moderate typhoon (severity 50). It cuts overhead power lines and aerial telecom links by wind and floods low-lying facilities; facility damage is slight or moderate only. The run uses 8 equally weighted scenarios so each can be traced; they are an illustrative set, not a probability estimate of real storms.
- **Dynamics.** Structure §4.5. Calibration-tier forms only (linear; threshold at 0.5 for logistic and control; discrete recovery), a declared restriction. A node's state is condition × supply level, and supply level is the lowest response across its commodities. Consumers throttle, trip (below 90% of supply) or step to a floor (hospitals on generator at 0.6). Stocks drain at the actual draw and refill as ruled. Two crews work through the repairs in the default order (towered lines and transmission substations first), moving job to job, with a 2 h crew-bound lead time per job and parts lead time running in parallel. A substation that has lost its telecom link is re-energized only after a crew switches it by hand. Steps of 15 minutes, settled within each step; 72 h window.
- **Reference runs.** All 8 scenarios run for 72 h with no actions and the default crew order, saved as golden files. They give the "no action" term of the measure and the starting point of the hand trace.
- **Sensitivity by relaxing limits.** Any limit (a stock, a lead time, the number of crews) can be relaxed to unlimited or zero by name, one at a time or all but one, to show how much the result rests on it. Relaxing a limit is kept distinct from removing a dependency.
- **Determinism.** One master seed with named substreams. The world holds fixed while the error varies.

## The doubt, and the two runs

The analyst works from a belief graph produced from the truth by simple parametric error. Three knobs are swept together as one doubt level:

1. **Dependency existence.** Each cross-layer edge carries a probability; some are phantom and some are missing.
2. **Coupling strength.** κ is held as an interval, not a point.
3. **Boundary.** At higher levels, one excluded coupling is present in the truth and absent from the belief.

**The carried run** optimizes over sampled realizations of the belief graph, so the existence probabilities and κ intervals reach every decision. **The flattened run** flattens at the seam: an edge exists if its probability is above 0.5, and κ takes its midpoint. It then works from that single graph. Nothing else differs.

## The four models, one per member-class

All four are posed on the same network, dynamics, criticality and ledger. The objective throughout is unserved demand-hours over a 72-hour window: the hours each end-use node is out of service (a fraction when supply is partial), times its class weight, summed. Each request is posed under both the Lifeline and Equal presets (ruled 2026-10-20). Structure v0.3 §5 gives the end-use classes and weights.

| Class | The toy model | Answer key |
|---|---|---|
| **Defensive (INROP-D)** | Spend up to a budget of 3 or 4 on protection actions (defined below) before the storm to minimize expected unserved demand-hours over the 8 scenarios, equally weighted | Brute force over every affordable action set, cross-checked against the MIP |
| **Offensive (INROP-O)** | Strike k nodes (k = 2, 3) on the calm island, with no storm, to maximize unserved demand-hours. A struck node takes complete damage and is repaired by the crews in the default order. The attack is posed on its own, not coupled to the defender | Brute force, cross-checked against the MIP |
| **Restorative (INROP-R)** | After one fixed storm scenario (scenario 7, the one with the most towered-line failures), sequence the world's two repair crews across the failed nodes and failed overhead lines to minimize unserved demand-hours during recovery. A plan gives each crew an ordered list of jobs; every failed element is repaired once, by one crew | Brute force over repair orders, cross-checked against the MIP |
| **Informative (INROP-I)** | Choose one or two cross-layer couplings to observe, at 1 unit each, to reduce uncertainty about the network. It is its own optimization, not observe-then-defend (ruled 2026-09-29) | Against the pipeline's belief, so its key is built in Phase 4 (ruled 2026-10-20); the uncertainty measure is ruled first |

The coupled attacker–defender formulation stays future research. Attack itself is in the family and is exercised here. Attacking a reserve directly, such as draining a tank without damaging the facility, is in scope for the full demonstration and is left out of the pilot only.

### The defensive model's actions

Node state is condition × supply level, with a reserve held against a dependency. Each protection action changes one part of that state. The pilot uses two actions:

| Action | Cost | What it changes | Real-world instance |
|---|---|---|---|
| **Protect condition** | 2 | The storm cannot damage the element: a protected facility or overhead line keeps condition 1 in every scenario. Its supply level can still fall through a cascade. This is the fortification convention, so it gives an upper bound on the value of real hardening | A flood wall or raised switchgear at a substation; a sealed pump station; a hardened pole line |
| **Add reserve** | 1 | The node gains a reserve on one inbound dependency whose commodity can be stored (power, water, fuel, transport as supplies; not telecom, ruled 2026-10-21): a new stock where it has none, otherwise hours added to the one it has. The reserve covers the whole window (72 h) at the node's full draw, so that supply cannot fail the node within the window: the counterpart of the fortification convention (ruled 2026-10-20) | A backup generator with 72 hours of fuel at a hospital; elevated storage above a water pump station; a battery bank at a telecom exchange |

At most one of each action per element (protection may target a facility or an overhead line; a reserve targets a node). A protected node can still go dark when the node feeding it fails, and a node with a reserve can still be destroyed by the storm. That separation is the point of the pair: the optimizer faces a real trade between one wall and two generators.

A third action, **add a redundant feed** (a new cross-layer edge with its own κ, such as a tie line from a second substation), is held out of the pilot so the topology stays fixed for the hand trace. It is the next action to add, since the design already carries the edge-addition variable.

## The whole stack, sheet by sheet

| Sheet | What it does in the pilot |
|---|---|
| **0 · Research paradigm and design** | The run's declared design, and what it may and may not claim |
| **1 · World-model supply** | Emits the constructed world and its truth manifest |
| **2 · Trust architecture, ingestion and pedigree** | Emits one small source file per layer in a real container format. The pipeline ingests them and stamps trust as received. Two layers carry deliberate source disagreement |
| **3 · Network construction** | Builds the uncertain graph, the layer set and the declared boundary |
| **4 · Cascade dynamics** | Trip and throttle propagation over the window |
| **5 · Buffer dynamics** | The stocks drawn per node (fuel, batteries, water, purified and make-up water) and any reserves the defensive model adds, drawing down and refilling |
| **6 · Recovery dynamics** | Crew-limited repair under the default crew order, including manual switching trips. The restorative model replaces that order with an optimized one |
| **7 · Convergence analysis** | Confirms each step settled within 100 passes, and each run inside the window; the calm-world check holds |
| **8 · Criticality computation** | Counterfactual criticality for all 24 nodes, checkable by hand |
| **9 · INROP formulation and optimization** | The defensive, offensive and restorative models |
| **10 · Value of information** | The informative model |
| **11 · Ensemble across the modeling envelope** | Two or three modeling compositions, carried as a set and never averaged |
| **12 · Provenance and the information-state ledger** | Every act written to the ledger, so any recommendation walks back to its sources |
| **13 · Verification and validation** | The zero-doubt identity test, brute-force optimum checks, and a hand trace of one scenario |
| **14 · Computational infrastructure** | Seeds, replay, and versioned rules |
| **Capstone · The composed system** | A one-page product per model: the recommendation, its stated confidence, and what it rests on |

## Measure

The measure is distance to the optimum, normalized as (objective of the recommendation − objective of the optimum) ÷ (objective with no action − objective of the optimum). The offensive model uses its mirror. The gap is the flattened run's distance minus the carried run's.

## Runs

- **Defensive model, full sweep:** 3 worlds × 5 doubt levels (zero to high) × 2 budgets × 10 seeds = 300 paired runs.
- **Offensive, restorative and informative models:** carried vs flattened at one middle doubt level on each world, 30 paired runs apiece.

## Done when

1. The generator emits the world, the source files and the truth manifest from a seed, and re-emits them identically.
2. Every answer key is found by brute force and agrees with the MIP on its score (the informative key from Phase 4).
3. **At zero doubt the two runs return the same recommendation** in every model. This is a built-in test. If it fails, the harness is wrong, not the method.
4. One storm scenario is traced by hand on the printed network and matches the code: cascade, criticality ranking and score.
5. The ledger walks one recommendation from each model back to its source records.
6. The following are produced from the runs: Figure 7.1 (distance to optimum, both runs), a data version of Figure 7.2 (gap against doubt level), and a filled toy version of Figure 7.4 (what each of the four models reused and what it added).
7. A short run note records what was tuned, what the gap looked like, and anything that surprised.

## Deliberately out of scope

The following are left out: a second model within any class, the coupled attacker–defender formulation, error mechanisms beyond simple parametric noise, the tempo and equity objectives, the simulation tier, layer-level generate-six-hide-one, and full source fidelity beyond one small file per layer.

## Changes from v0.7

Ruled by the author, 2026-10-20 (Phase 2 ruling sheet, `evidence/Phase2_Answer_Key_Ruling_Sheet_v0_2.md`):
- **Defensive:** the expected loss over the 8 scenarios, equally weighted; the budget is a ceiling. A reserve may go on any inbound dependency, new where none exists, and covers the whole window at full draw.
- **Offensive:** the calm island, no storm; a strike is complete damage, repaired by the crews in the default order.
- **Restorative:** each crew's ordered list of jobs; every failed element repaired once, by one crew.
- **Informative:** stated as ruled on 2026-09-29; its answer key moves to Phase 4, against the pipeline's belief.
- **Answer keys:** cross-checked by a time-expanded MIP for the three Phase 2 models, solved with HiGHS. Each request is posed under both the Lifeline and Equal weights.
- **The 8 scenarios are a sample.** The key is the best answer against them, not against the storm in general; the full study widens the sample.

## Changes from v0.6

Ruled by the author, 2026-10-02 to 2026-10-09 (decision 0014; Structure v0.9):
- The dynamics are specified (Structure §4.5): state and responses, stocks and refill, crews with a split lead time and job-to-job movement, manual switching after telecom loss, 15-minute steps.
- The 8 scenarios are run with no actions as saved reference runs.
- The restorative model uses scenario 7.
- Limits can be relaxed one at a time for sensitivity, distinct from removing a dependency.
- The edge range is 40–55 (decision 0013 addendum).

## Changes from v0.5

Ruled by the author, 2026-09-30 (decision 0012):
- The storm is specified (Structure §4.3b): overhead lines fail by wind, facilities by flood; severity 50; 8 equally weighted scenarios.
- The restorative model sequences crews across failed overhead lines as well as failed nodes.
- Protect condition can target an overhead line, and is stated as the fortification convention (an upper bound).

## Changes from v0.3

- The single planted reserve is replaced by reserves drawn per node from context (structure v0.3 §4.4).
- Sources stated: two disagreeing sources on power and healthcare, one on each other layer.
- Crews are a world quantity (two); the restorative model takes no budget.
- The objective is defined as weighted service-hours at end-use nodes under the Lifeline weights, over a 72-hour window.
- The closing section on steps before the generator runs is removed: the export ask is out of scope, and the Magliocca consult runs alongside the build.
