# 0014 — The dynamics: engine rulings, relaxed values and the Theta List

- **Date:** 2026-10-09
- **Decided by:** the author (Foreman), D1–D11 and the four degradation-profile gaps, one item at a time
- **Recorded by:** Work Order 7, PR 7a (foundations); PR 7b adds the engine's own records
- **Sources:**
  - `docs/design/evidence/Dynamics_Ruling_Sheet_v0_3.md`;
  - `docs/design/evidence/Degradation_Profiles_v0_2.md`;
  - structure v0.9 §4.4a and §4.5; Pilot Spec v0.7.

## Context

The world can be built and stormed, but nothing plays a storm out over time. The engine that does is the world's true dynamics, θ\*, and every answer key in Phase 2 calls it. Every setting is a registry rule a recipe overrides by name; nothing is hard-coded.

## Decisions

- **D1. Where the engine lives.** A pure engine in `src/swm/dynamics/`: (world, scenario, actions, crew policy, horizon) to trajectories. The generator records θ\* and never runs the solver; the engine never sees error induction.
- **D2. Responses.** The edge's transfer form decides what is delivered; the consumer's failure mode decides how it copes with its received share R: throttle (R), trip (1 while R ≥ 0.9, else 0) or step to a floor (hospitals on generator at 0.6). Supply level is the minimum across commodities. Telecom tolerance acts first where a class has a row.
- **D3. Pilot transfer forms.** Linear for physical flow and service; threshold at θ = 0.5 for logistic and control; discrete recovery. The step form is held for later worlds.
- **D4. Lines and links.** Links inside power, water, fuel and telecom carry that layer's commodity: physical flow, linear, shared pro rata. Roads give reachability and crew travel; healthcare referral links carry nothing in Phase 1. A failed line passes nothing until repaired. No power-flow model.
- **D5. Buffers.** Stocks cover their own commodity at the actual draw. Generators fail to start or stop at their drawn time. Fuel deliveries arrive 12 h after power loss, then every 24 h, while the depot is up and a road links them. Refill:
  - batteries recharge empty to full in 12 h;
  - water storage refills from the pumps' spare capacity;
  - generator tanks refill only by delivery;
  - national LNG, oil and coal stocks do not refill inside the window.
- **D6. Repair and crews.** Recovery is all or nothing.
  - **Lead time is split:** a crew-bound lead time of 2 h plus travel, repeating at every job; and the parts lead time, max(0, Hazus lead time − 2 h), running in parallel from the end of the storm.
  - **Crews** move job to job and never return to base.
  - **The default crew order** is towered lines and transmission substations; then distribution substations and feeds to end uses by Lifeline weight; then everything else. Ties go to the shortest travel, then the lowest id.
- **D7. Time.** The storm acts at hour 0. Steps are 15 minutes, settled within each step up to 100 passes; a step that hits the cap is reported. The horizon comes from the request, 72 h by default.
- **D8. The calm-world check.** With no damage, every node holds state 1, every buffer stays full, and no clock moves for the whole horizon.
- **D9. Saved reference runs.** The pilot's 8 scenarios are run for 72 h with no actions and the default crew order, saved as golden files.
- **D10. The Theta List.** Every choice is tracked under Θ, across four domains: truth θ\*, error model, real-world chain and each run's θ̂.
  - Each entry carries its sub-type and symbol, alternatives, relaxed value, what a flattened run does with it, its sensitivity and its ruling.
  - The 72 h window is a stopping entry.
  - The objectives are outside the tuple.
- **D11. Relaxed values.** Every limit declares a relaxed value: unlimited for stocks and capacities, zero for delays and losses.
  - A recipe relaxes limits by name, stored as a flag, never as a large number.
  - Relaxing a limit is distinct from removing a dependency.
  - Relaxing never worsens the outcome.

**The four degradation-profile gaps, as ruled:**
1. Generation keeps 24 h of purified boiler water (range 6–48 h).
2. Substation telecom loss costs a manual switching trip: 1 h on site (0.5–2 h) plus travel, using a crew. This replaces "slows switching and repair".
3. Evaporative data centres keep 12 h of make-up water (0–48 h).
4. Seaports keep 0 h of backup power for cargo (0–48 h).

**The Work Order 6c audit:** mast-to-mast and reservoir-to-reservoir links break their layer signatures. The link builder now obeys each signature, and a world check proves it.

## How PR 7a builds it

- **Registry:** `range`, `range_open` and `relaxed` on every limit, and a Theta sub-type, domain and symbol on every rule.
- **Theta List:** the standalone entries for the minimum rule, the transfer forms, the recovery form, pro rata sharing, the crew order, the time step and settling, and the window. `swm rules --theta` prints it.
- **Recipe version 3:** adds `modeling_rules.relaxed_limits` and `dynamics.removed_dependencies`. Control dependencies now default to the threshold form (D3).

## Later phases (structure v0.9, "Changes from v0.8")

Each becomes a selectable setting when built:
- sharing rules beyond pro rata;
- recovery forms beyond all or nothing;
- step and concave degradation forms;
- partly failed lines and line capacity limits;
- power flow (Phase 5);
- the parts clock starting at first assessment;
- toggleable step size and event-driven timing;
- damage timed to the storm's passage;
- timed exogenous events in a scenario;
- a saved scenario and run library;
- crane versus roll-on/roll-off seaport terminals;
- air-cooled data centres.

## Addendum: answers to PR 15 (2026-10-09)

- **Decided by:** the author (Foreman)
- **Source:** `docs/work_orders/WO-07a-answers.md`

1. **Sources.** The three new stocks cite verified sources, each read on 2026-10-09:
   - **Make-up water:** Uptime Institute Journal, "Implications of economizers in Tier Certified data centers".
   - **Purified boiler water:** IS 13268:1992 §4.2.3, archived copy. It is withdrawn and superseded by the 2023 edition; the 1992 text is the one cited. The rule stays a placeholder until Taiwan's environmental impact statements are read.
   - **Seaport backup power:** Emerging Risks (29 January 2026), a secondary report of TT Club's guidance.
2. **One storm-damage stream per element.** Each line's damage draws come from its own child stream, keyed by the scenario and the element's stable id, so adding or removing an element moves no other element's draws (CLAUDE.md §4).
   - **No median meets both windows.** Re-measured after the change, the pole-line curve at β 0.4 has no single median that puts both recipes within 5 points of their targets. The best single median, 163.7317 m/s, gives the pilot 4.1% (window 5–15%) and severity 70 35.1% (window 25–35%), a worst miss of 5.9 points.
   - **Closest stored.** As the answers instruct, the closest is stored, with 163.6914 in history, and the rule is open for a ruling. The work stopped there (Work Order 7b not opened).
3. **Mast-to-mast links.** Work Order 3 B5's allowance is superseded by the ruling of 2026-10-09 (the decision 0013 audit; Work Order 7 Part 0).
4. **Theta symbols** follow Appendix A v1.7, Definition 2.7:
   - **F:** the combining function;
   - **g_δ:** the degradation transfer function: the transfer forms, the failure modes, the trip point, the floor and the telecom tolerance form;
   - **h_φ:** the reserve dynamics: stocks, refill and resupply;
   - **R:** recovery;
   - **γ:** convergence;
   - **χ:** the performance function, one analysis entry: weighted service-hours at end-use nodes, counted as a fraction when supply is partial.

   The storm rules carry no symbol.
5. **Pump capacity** is the registry limit `reserves.pumping.capacity` (relaxed value unlimited, range open). It is each pumping node's `capacity_m3_per_day` attribute, drawn in the layers stage (`layers.attributes.pumping`) and read by the requirements stage. It is not sized to load, and no new number is introduced.
6. **Overrides outside a ruled range** are allowed. The resolved recipe and every run record a note naming the rule, the value and the range (`modeling_rules.out_of_range`).
