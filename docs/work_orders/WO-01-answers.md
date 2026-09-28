WORK ORDER 1 — ANSWERS FROM THE DESIGN SIDE (2026-09-28, confirmed by Foreman)

Build to these. Record them in docs/decisions/0003-wo1-rulings.md (0002 stays the scaffold-review rulings). Where a ruling changes the spec, the design side will issue structure document v0.3; do not edit docs/design/ yourself.

A. BLOCKING

A1 Terrain seed: option (b). Add terrain.terrain_seed (integer ≥ 0, default 0). It is added as an extra spawn-key element on every terrain/* stream only. That lets the author reroll the ground alone, which the interface requires. Infrastructure is sited from the terrain, so it follows any terrain change, but its own streams never move. The ensemble "vary terrain" option later varies terrain_seed.

A2 Two repair crews: option (c). The world has 2 crews: unobserved.crews = 2 in the pilot fixture. Crews and depots are world quantities. The restorative model sequences whatever crews the world has, so it takes no budget (see A5).

A3 Sources in the pilot. Correction to the work order: the pilot spec requires "two layers carry deliberate source disagreement", so "one source each" was wrong. Use:
  - power: osm_power and wri_gppd (overlap on);
  - healthcare: osm_health and facility_register (overlap on);
  - telecom: osm_telecom;
  - water: osm_water;
  - transport: ourairports;
  - fuel: osm_fuel.
This also exercises the PBF and CSV containers.

A4 Dual membership: option (a). Off in the pilot; the feature maps to Phase 1 (layers stage).

A5 Budget: typed per model, not one integer. Each request carries the parameter its model uses:
  - defensive "protect condition and add reserve": budget_cost_units (protect costs 2, add reserve costs 1; costs recorded in the schema as the pilot's values);
  - offensive "strike nodes": strikes_k;
  - restorative "sequence repair crews": no budget parameter (crews come from the world);
  - informative "observe uncertain couplings": observations_n.
The second model in each class has no parameters yet (not yet scheduled).

A6 Phases: accept the proposal.
  - "Huge" is Phase 5.
  - Hidden couplings, coupling density and two-way dependencies are Phase 1.
  - The second models, the two extra objectives and custom weights are reported as "not yet scheduled".

B. SPEC AND MOCKUP DISAGREE

B1 Map types: the mockup's eleven. The spec will be updated.

B2 Urban patterns: the mockup's three. The spec will be updated.

B3 Error mechanism: per source, with a recipe-level default. errors.default_mechanism applies to every source that does not set its own mechanism. The spec's per-source rule stands; the mockup's single control becomes the default.

B4 Hazard severity: per hazard (severity 0–100 on each hazard), as the spec says. Remove the global severity from difficulty.

B5 Installed redundancy total: drop it from the recipe. Redundancy is planted by the feed mix and dependency concentration, never as a total (spec §4.3). The difficulty readout is computed from the world, not set.

B6 Per-dependency-type controls: carry transfer_form per dependency type, restricted to the four canon forms (linear, concave, threshold, step). Defaults:
  - physical flow: linear;
  - logistic: threshold;
  - control: step;
  - service: linear.
Tier and time handling stay global. Combining stays fixed at typed_weakest_link.

B7 The pilot's single reserve: the drawn-reserves defaults stand. The pilot spec's "one reserve on the fuel→power link" predates drawn reserves and is superseded; the pilot spec will be updated.

C. RANGES AND MEANINGS

C1 Compliance gap: compliance_gap_pct is the mean departure from the design target, as a percent of the target. Positive means shortfall and negative means the element exceeds its target. Range −50 to 100. Special cases:
  - Failure mode (a category): heterogeneity_pct is the share of elements whose failure mode departs from their type's canon default. Compliance gap does not apply: fixed at 0, with a validation note if set.
  - Links on node-only layers: heterogeneity_pct is the share of links that depart from the shortest road route. Compliance gap does not apply: same treatment.

C2 The 0–100 controls are dimensionless indices. Each field's description states what 0 and 100 mean, using these anchors:
  - coupling density: 0 = each consumer has the minimum one supplier per coupled layer; 100 = the maximum the matrix allows;
  - concentration: 0 = supply spread evenly across suppliers; 100 = one supplier per layer carries every consumer;
  - hazard severity: 0 = no damage; 100 = every exposed element in the hazard core fails;
  - terrain character indices: 0 = none; 100 = the most the map type allows.
The exact numeric mapping is set in the work order that builds each stage.

C3 Error-rate caps: 0–100 in the schema. The mockup's slider limit is an interface choice.

C4 Bounds: accept your defaults: node count ≥ 1, area ≥ 1 km², no upper bounds, root seed 0 to 2⁶⁴ − 1.

C5 Time window: it belongs to the request, not the world. The objective is scored over a horizon, and the horizon is part of the question. Move window_h to each answer-key request (default 72). The world's dynamics are defined for any horizon. The spec will be updated.

C6 Custom service weights:
  - node classes are the mockup's per-layer class strings;
  - weights are non-negative numbers, 0–100;
  - "Healthcare first" gives blood banks 5, the same as regional hospitals (author's ruling). The preset is: tertiary 10, regional 5, blood bank 5, clinic 1, other end uses 1.

D. IMPLEMENTATION CHOICES: accept all three, with one change. A healthcare layer switched on as a supplier gets a validation note ("the spec models healthcare as a pure sink"), not silence.

Proceed to the pull request.
