WORK ORDER 4 — ANSWERS TO THE PR 4a QUESTIONS (design side, 2026-09-29, confirmed by Foreman)

PR 4a (#5) is merged. Build PR 4b on this branch (wo4b/couplings-stage, cut from main after the merge). Record these answers in docs/decisions/0008-wo4-answers.md in PR 4b.

1. Rows naming more suppliers than their evidence found. This was a grouping error on the design side, when consumers were merged into shared rows of spec §4.3a. Narrow the supplier lists to what the research lanes found:
   - fuel → cable_landing: depot only;
   - fuel → regional: depot only (tertiary keeps depot and tank farm);
   - telecom → transmission_substation: exchange only;
   - telecom → blood_bank: exchange and data_centre;
   - telecom → refinery: exchange only.
   The design side will correct §4.3a to match in the next spec revision. Update the table and its tests in PR 4b, and explain the change in the pull request.

2. The implied "none" rows are confirmed, each citing its source:
   - data_centre with dry cooling;
   - tank_farm with neither a jetty nor a truck rack;
   - bridge, road_junction and rail_node under power, telecom and fuel (rule 7).

3. A consumer whose standby_fuel is none gets no buffer-resupply edge. There is no generator to refuel. Record the absence in the dependency table with a note, not as an error.

4. Rule 4 (large loads) waits for Work Order 5. Until node requirements exist, treat every consumer as below the transmission-connection threshold: supplied from a distribution substation. Record a note that rule 4 is deferred. Do not convert capacities into megawatts. Work Order 5 applies rule 4 once requirements are drawn.

5. "Inland" in water → generation: your reading is confirmed. Generation is sited on the coast, so the raw-water reservoir row does not fire in Phase 1. That fits a Taiwan-like island, whose thermal fleet is coastal. Keep the row for other map types.

6. Outlying islands: count a sea leg. A consumer on an outlying island is reachable from any seaport on the main island by coastal tanker or ferry, provided that seaport is itself reachable over the transport links. Record the edge with sea_leg = true. This matches how Kinmen and Matsu are supplied. A main-island consumer still needs a road path.
