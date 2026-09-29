# Pilot Spec — The Full Chain on a Hand-Checkable Constructed World

*v0.5 · 2026-09-29 · feeds Ch7 §7.2 and Figures 7.1, 7.2 and 7.4 · aligned with World_Generator_Structure v0.5 and the pilot recipe in the SyntheticWorldModel repository*

## Purpose

Run the whole chain, every sheet of Appendix B from world supply to the composed product, on a constructed world small enough to check by hand. Pose all four optimization member-classes on that one network, one small model each. Run the chain twice, once carrying doubt across every handoff and once flattening it at each seam, and score both runs against the known optimum. The pilot is the first working build of the generator and pipeline, and the code carries forward into the January build.

## What the pilot claims, and what it does not

It is a Phase 0 run in the sense of the generator design (§1.7.6). The proposal reports it as preliminary results showing three things: the chain executes end to end with doubt carried, the four classes can be posed on one network, and the gap between the two runs has a visible shape on a toy world. It does not answer RQ1(b) or RQ2. It is not pre-registered, and nothing it tunes is locked by it.

## The world

- **Size.** About 24 nodes, four per layer across the full layer set (power, telecom, water, transport, fuel, healthcare), with 40–50 edges including the cross-layer couplings (widened from 35–45 on 2026-09-29). It fits on one page and a cascade can be traced by hand.
- **Substrate.** A small island with a mountain spine and a coastal plain. Nodes are sited by layer rules from the generator design.
- **Topology.** Each layer keeps its own signature: power meshed, water dendritic, healthcare a referral tree. Healthcare is the pure sink.
- **Couplings switched on.** Seven of the 21, chosen so a cascade crosses every layer and can be traced by hand: fuel → power, power → telecom, telecom → power, power → water, water → healthcare, power → healthcare, transport → fuel. The rest are generated and hidden. Density 0 (core dependencies only), dependencies from the table in World_Generator_Structure §4.3a. If the realised edge count falls outside 40–50, the build reports it rather than tuning.
- **Coupling.** Cross-layer edges carry commodity, coupling strength κ and a failure mode (throttle or trip). Reserves are drawn per node from context like every other unobserved quantity, and each reserve sets its buffer time τ (reserve ÷ draw) during the run. The earlier single planted reserve on the fuel→power link is superseded.
- **Sources.** One small source file per layer in its real container. Power (OpenStreetMap and the WRI plant database) and healthcare (OpenStreetMap and the government facility register) each have two sources that deliberately disagree; the other four layers have one. Fuel and healthcare sources report nodes only.
- **Crews.** The world has two repair crews.
- **Disruption.** One storm corridor is drawn as a shared latent field, and element failures are drawn conditionally on it. The run uses 5–8 scenarios so each can be traced.
- **Dynamics.** Calibration-tier forms only (linear, threshold, discrete recovery), over a short window. This is a declared restriction.
- **Determinism.** One master seed with named substreams. The world holds fixed while the error varies.

## The doubt, and the two runs

The analyst works from a belief graph produced from the truth by simple parametric error. Three knobs are swept together as one doubt level:

1. **Dependency existence.** Each cross-layer edge carries a probability; some are phantom and some are missing.
2. **Coupling strength.** κ is held as an interval, not a point.
3. **Boundary.** At higher levels, one excluded coupling is present in the truth and absent from the belief.

**The carried run** optimizes over sampled realizations of the belief graph, so the existence probabilities and κ intervals reach every decision. **The flattened run** flattens at the seam: an edge exists if its probability is above 0.5, and κ takes its midpoint. It then works from that single graph. Nothing else differs.

## The four models, one per member-class

All four are posed on the same network, dynamics, criticality and ledger. The objective throughout is unserved demand-hours over a 72-hour window: the hours each end-use node is out of service (a fraction when supply is partial), times its class weight under the Lifeline preset, summed. Structure v0.3 §5 gives the end-use classes and weights.

| Class | The toy model | Answer key |
|---|---|---|
| **Defensive (INROP-D)** | Spend a budget of 3–4 on protection actions (defined below) before the storm to minimize expected unserved demand-hours | Brute force over every affordable action set, cross-checked against the MIP |
| **Offensive (INROP-O)** | Strike k nodes (k = 2, 3), degrading their condition, to maximize unserved demand-hours. The attack is posed on its own, not coupled to the defender | Brute force |
| **Restorative (INROP-R)** | After one fixed storm scenario, sequence the world's two repair crews across the failed nodes to minimize unserved demand-hours during recovery | Brute force over repair orders |
| **Informative (INROP-I)** | Choose one or two uncertain cross-layer edges to observe before hardening, to maximize the improvement in the defensive decision | Enumeration over the observation choices and their outcomes |

The coupled attacker–defender formulation stays future research. Attack itself is in the family and is exercised here. Attacking a reserve directly, such as draining a tank without damaging the facility, is in scope for the full demonstration and is left out of the pilot only.

### The defensive model's actions

Node state is condition × supply level, with a reserve held against a dependency. Each protection action changes one part of that state. The pilot uses two actions:

| Action | Cost | What it changes | Real-world instance |
|---|---|---|---|
| **Protect condition** | 2 | The storm cannot damage the node's own equipment: its condition stays at 1 in every scenario. Its supply level can still fall through a cascade | A flood wall or raised switchgear at a substation; a sealed pump station; a hardened pole line |
| **Add reserve** | 1 | The node gains a reserve on one inbound dependency, which extends τ on that edge. The node keeps operating on the reserve and fails only if supply has not returned when the reserve runs out | A backup generator with 72 hours of fuel at a hospital; elevated storage above a water pump station; a battery bank at a telecom exchange |

At most one of each action per node. A protected node can still go dark when the node feeding it fails, and a node with a reserve can still be destroyed by the storm. That separation is the point of the pair: the optimizer faces a real trade between one wall and two generators.

A third action, **add a redundant feed** (a new cross-layer edge with its own κ, such as a tie line from a second substation), is held out of the pilot so the topology stays fixed for the hand trace. It is the next action to add, since the design already carries the edge-addition variable.

## The whole stack, sheet by sheet

| Sheet | What it does in the pilot |
|---|---|
| **0 · Research paradigm and design** | The run's declared design, and what it may and may not claim |
| **1 · World-model supply** | Emits the constructed world and its truth manifest |
| **2 · Trust architecture, ingestion and pedigree** | Emits one small source file per layer in a real container format. The pipeline ingests them and stamps trust as received. Two layers carry deliberate source disagreement |
| **3 · Network construction** | Builds the uncertain graph, the layer set and the declared boundary |
| **4 · Cascade dynamics** | Trip and throttle propagation over the window |
| **5 · Buffer dynamics** | The planted fuel→power reserve and any reserves the defensive model adds, drawing down |
| **6 · Recovery dynamics** | Crew-limited repair under a default allocation policy. The restorative model replaces that policy with an optimized one |
| **7 · Convergence analysis** | Confirms each run settled inside the window |
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
2. Every answer key is found by brute force and agrees with the solver.
3. **At zero doubt the two runs return the same recommendation** in every model. This is a built-in test. If it fails, the harness is wrong, not the method.
4. One storm scenario is traced by hand on the printed network and matches the code: cascade, criticality ranking and score.
5. The ledger walks one recommendation from each model back to its source records.
6. The following are produced from the runs: Figure 7.1 (distance to optimum, both runs), a data version of Figure 7.2 (gap against doubt level), and a filled toy version of Figure 7.4 (what each of the four models reused and what it added).
7. A short run note records what was tuned, what the gap looked like, and anything that surprised.

## Deliberately out of scope

The following are left out: a second model within any class, the coupled attacker–defender formulation, error mechanisms beyond simple parametric noise, the tempo and equity objectives, the simulation tier, layer-level generate-six-hide-one, and full source fidelity beyond one small file per layer.

## Changes from v0.3

- The single planted reserve is replaced by reserves drawn per node from context (structure v0.3 §4.4).
- Sources stated: two disagreeing sources on power and healthcare, one on each other layer.
- Crews are a world quantity (two); the restorative model takes no budget.
- The objective is defined as weighted service-hours at end-use nodes under the Lifeline weights, over a 72-hour window.
- The closing section on steps before the generator runs is removed: the export ask is out of scope, and the Magliocca consult runs alongside the build.
