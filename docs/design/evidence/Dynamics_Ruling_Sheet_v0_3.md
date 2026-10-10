# Dynamics: ruling sheet v0.3 (ruled)

*2026-10-09 · ruled by Foreman in discussion, one item at a time · prerequisite to SyntheticWorldModel Work Order 7 · supersedes v0.2 (adds D11 and the ruled degradation-profile gaps)*

Every setting below is a rules-registry entry that a recipe can override by name, and the Phase 7 interface will expose it. Nothing here is hard-coded. Placeholders are graded J.

## The rulings

**D1. Where the engine lives.**
- A pure engine in `src/swm/dynamics/`. It takes (world, scenario, actions, crew policy, horizon) and returns trajectories.
- The generator records θ\* but never runs the solver. The solver, the checks and `swm simulate` call the engine.
- The engine never sees error induction.

**D2. How a node responds to a shortfall.** Both mechanisms are kept:
- the transfer form on the edge decides what is delivered;
- the failure mode on the consumer decides how it copes with its received share R:
  - **throttle:** R;
  - **trip:** 1 while R ≥ 0.9, else 0 (placeholder; to be tested in rollout);
  - **step to a floor:** hospitals on generator at 0.6.
- Supply level = the minimum across commodities (typed weakest link), not the product.
- The full class-by-class table is reviewed and accepted (degradation profiles v0.1).
- Telecom tolerance acts first wherever a class has a tolerance row.

**D3. Pilot transfer forms.**
- Calibration tier only: linear, threshold, discrete recovery.
- Control dependencies take the threshold form, θ = 0.5, as do logistic ones.
- The step form is held for later worlds.

**D4. Lines and links.**
- Links inside power, water, fuel and telecom carry that layer's commodity: physical flow, linear, shared pro rata.
- Roads give reachability and crew travel; healthcare referral links carry nothing in Phase 1.
- A failed line passes nothing until repaired.
- No power-flow model.
- Mapped power lines are routed elements (Work Order 6c).

**D5. Buffers.**
- Stocks cover their own commodity's shortfall at the actual draw (hospitals at essential load).
- Generators fail to start or stop at their drawn fail-to-run time.
- Fuel deliveries arrive 12 h after power loss, then every 24 h, while the depot is up and a road links them.
- **Refill** (changed from v0.1):
  - batteries recharge, empty to full in 12 h (placeholder);
  - water storage refills from the pumps' spare capacity;
  - generator tanks refill only by delivery, continuing every 24 h until full;
  - national LNG, oil and coal stocks do not refill inside the window.

**D6. Repair and crews.**
- **Recovery is all or nothing** in Phase 1.
- **Lead time is split** (changed from v0.1):
  - **crew-bound lead time:** mobilize, travel, assess, stage. It starts when a crew is assigned and repeats at every job. Placeholder: 2 h plus travel.
  - **parts lead time:** the rest of the Hazus lead time. It runs in parallel with no crew. In Phase 1 its clock starts at the end of the storm; starting at first assessment is a selectable setting later.
- A crew's sequence: assigned → mobilize and travel → assess → repair once parts are in → travel to the next job.
- Crews move job to job.
- **Default crew order:**
  1. towered lines and transmission substations;
  2. distribution substations and feeds to end uses, highest Lifeline weight first;
  3. everything else.

  Ties go to the shortest travel, then the lowest id.
- Emergency units go to eligible damaged nodes in the same order.

**D7. Time.**
- The storm acts at hour 0.
- Steps of 15 minutes.
- Within each step the cascade settles, up to 100 passes; a run that hits the cap is reported.
- The horizon comes from the request (default 72 h).

**D8. The calm-world check.** With no damage, every node holds state 1, every buffer stays full, and no crew, delivery or tolerance clock moves, for the whole horizon. Any deviation fails the build.

**D9. Saved reference runs.**
- The pilot's 8 storms are run for 72 h with no actions and the default crew order.
- Each run is saved as golden files, stamped with the horizon and the policy.
- Each records every node state, buffer level, crew position and job, and repair completion, plus unweighted hours out per end-use node.
- `swm simulate --scenario N` prints and plots any run.

**D10. The Theta List.**
- **Every choice is tracked in the tuple under Θ**, so a decision maker can be told every choice behind a result. It spans four domains:
  1. **the constructed world's truth, θ\*:** every rule in the registry, including values like the 72 h hospital fuel, and every dynamics choice above;
  2. **the constructed world's error model:** how sources are corrupted (Phase 3);
  3. **the real-world chain:** the Chapter 5 pipeline's choices, in the MCIN_Pipeline repository, recorded in the same format;
  4. **each analysis run's declared θ̂.**
- Each entry carries:
  - its framework sub-type (construction, dynamics, analysis, stopping) and symbol;
  - the θ\* value and each run's θ̂ value;
  - its alternatives;
  - what a flattened run does with it;
  - its sensitivity status;
  - its ruling.
- The 72 h window is a stopping entry.
- **Objectives are outside the tuple:** the metric, the acceptability threshold and the service weights are the questions being answered, recorded with each request.
- It is built into the registry now, in Work Order 7. `swm rules --theta` prints it, and the dissertation appendix prints from the same source.

**D11. Relaxed values** (ruled 2026-10-09).
- Every limit declares a relaxed value: unlimited for stocks and capacities, zero for delays and losses.
- A recipe can relax any limit by name: one alone, all but one, or any named mix. Stored as a flag, not a large number.
- Relaxing a limit is distinct from removing a dependency; the two are separate switches, and a result says which was used.
- Every run records its relaxed limits in the Theta List (a "relaxed value" field on each entry).
- Built into Work Order 7 as a standing engine feature. A test proves relaxing a limit never worsens the outcome.

**Degradation-profile gaps** (ruled 2026-10-09; Degradation Profiles v0.2): generation keeps 24 h of purified boiler water (6–48 h); substation telecom loss costs a manual switching trip (1 h on site, 0.5–2 h, plus calculated travel, using a crew); data centres keep 12 h of make-up water (0–48 h); seaports have 0 h of backup power for cargo (0–48 h).

## Later phases (recorded at Foreman's direction)

Each becomes a selectable setting when built:
- **Sharing when a supplier is short:** pro rata (Phase 1), priority lines first, full support until exhausted, others.
- **Recovery form:** all or nothing (Phase 1), piecewise, gradual.
- **Degradation forms:** the step form and concave forms beyond the pilot.
- **Partly failed lines**, and line capacity limits (required after Phase 1).
- **Power flow** in Phase 5.
- **Parts lead time** clock starting at first assessment.
- **Step size** toggleable, plus event-driven timing.
- **Damage timed to the storm's passage,** with crews held until the winds drop.
- **Timed exogenous events in a scenario**, e.g. a substation attacked at hour 5 after the storm at hour 0.
- **A scenario and run library:** named scenarios and runs, saved, reloaded, compared, shared, stamped with the recipe and rules fingerprints.
- **Routing of water mains, pipelines and fibre** if the data supports it; otherwise they stay inferred.
- **Per-class degradation profiles** kept as living tests (v0.2 ruled).
- **Seaport terminal types:** crane-dependent versus roll-on/roll-off terminals.
- **Data centre cooling types:** air-cooled data centres with no water dependency.
