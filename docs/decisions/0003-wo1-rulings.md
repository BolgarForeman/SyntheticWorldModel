# 0003 — Work Order 1 rulings

- **Date:** 2026-09-28
- **Decided by:** the design conversation, confirmed by Foreman
- **Recorded by:** Work Order 1
- **Full text:** `docs/work_orders/WO-01-answers.md`

## Context

Before building Work Order 1, the code side raised questions where the work order, the structure document (v0.2) and the interface mockup (v0.5) were silent or disagreed. Where a ruling changes the specification, the design side will issue structure document v0.3.

## Decisions

**Blocking**

- **A1 Terrain seed.** `terrain.terrain_seed` (integer ≥ 0, default 0) is an extra spawn-key element on every `terrain/*` stream, and on no other stream. It rerolls the ground alone. Infrastructure follows the terrain, but its own streams never move. The ensemble option "vary terrain" will vary it.
- **A2 Repair crews.** Crews and depots are world quantities. The pilot world has 2 crews. The restorative model sequences the crews the world has, so it takes no budget.
- **A3 Pilot sources.** "One source each" was wrong. The pilot spec needs two layers with deliberate source disagreement:
  - power: `osm_power` and `wri_gppd`, with overlap;
  - healthcare: `osm_health` and `facility_register`, with overlap;
  - `osm_telecom`, `osm_water`, `ourairports` and `osm_fuel` for the other four layers.
- **A4 Dual membership.** It is off in the pilot and arrives in Phase 1, with the layers stage.
- **A5 Budget.** The budget is typed per model:
  - protect condition and add reserve: `budget_cost_units`, with protect costing 2 and add reserve 1 (the pilot's values);
  - strike nodes: `strikes_k`;
  - sequence repair crews: no budget;
  - observe uncertain couplings: `observations_n`;
  - the second model in each class has no parameters yet.
- **A6 Phases.** "Huge" is Phase 5. Hidden couplings, coupling density and two-way dependencies are Phase 1. The second models, the two extra objectives and custom weights are "not yet scheduled".

**Where the specification and the mockup disagree**

- **B1 Map types.** The mockup's eleven.
- **B2 Urban patterns.** The mockup's three.
- **B3 Error mechanism.** Set per source. `errors.default_mechanism` applies to any source without its own.
- **B4 Hazard severity.** Set per hazard, 0–100. The global severity is removed.
- **B5 Installed redundancy.** Dropped from the recipe. Redundancy is planted by the feed mix and dependency concentration, never as a total.
- **B6 Transfer forms.** One per dependency type, from the four canon forms. The defaults are:
  - physical flow: linear;
  - logistic: threshold;
  - control: step;
  - service: linear.

  Tier stays global, and combining stays fixed at typed weakest link.
- **B7 The pilot's single reserve.** Superseded: the drawn-reserves defaults stand.

**Ranges and meanings**

- **C1 Compliance gap.** `compliance_gap_pct` is the mean departure from the design target, as a percent of the target: positive is a shortfall, negative an excess. Its range is −50 to 100. For failure mode and for links on nodes-only layers:
  - heterogeneity is a share of elements (`heterogeneity_pct`);
  - the compliance gap does not apply: it is fixed at 0, with a validation note if set.
- **C2 The 0–100 controls** are dimensionless indices. Each field states what 0 and 100 mean. The numeric mapping is set by the work order that builds each stage.
- **C3 Error rates** run 0–100.
- **C4 Bounds.** Node count ≥ 1 and area ≥ 1 km², with no upper bounds. Seeds run from 0 to 2⁶⁴ − 1.
- **C5 Time window.** It belongs to the request: `window_h` on each answer-key request, default 72.
- **C6 Custom service weights.**
  - They use the mockup's node classes, each weighted 0–100.
  - The "healthcare first" preset is: tertiary 10, regional 5, blood bank 5, clinic 1, other end uses 1.

**Implementation choices**

- **D. All three accepted, with one change.** A healthcare layer switched on as a supplier gets a validation note. The three choices were:
  - size presets and the hold switch;
  - notes on inactive sources;
  - sorted coupling pairs.
