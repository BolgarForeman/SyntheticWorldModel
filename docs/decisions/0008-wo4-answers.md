# 0008 — Answers to the PR 4a questions

- **Date:** 2026-09-29
- **Decided by:** the design side, confirmed by the author (Foreman)
- **Recorded by:** Work Order 4, PR 4b
- **Source:** `docs/work_orders/WO-04-answers.md`

## Context

PR 4a encoded structure v0.5 §4.3a as the dependency table and raised six questions: two on the table's rows, and four that decide which coupling edges exist. PR 4a merged as #5. These answers govern the couplings stage built in PR 4b.

## Decisions

1. **Supplier lists narrowed to what the research lanes found.** Merging consumers into shared rows of §4.3a gave some members the group's suppliers. That was a grouping error on the design side. The table now reads:
   - fuel → cable landing: depot only;
   - fuel → regional: depot only (tertiary keeps depot and tank farm);
   - telecom → transmission substation: exchange only;
   - telecom → blood bank: exchange and data centre;
   - telecom → refinery: exchange only.

   The design side corrects §4.3a to match in the next spec revision. The table still has 99 rows; only these supplier lists changed.
2. **The implied "none" rows are confirmed**, each citing its source:
   - a data centre with dry cooling;
   - a tank farm with neither a jetty nor a truck rack;
   - the bridge, road junction and rail node under power, telecom and fuel (rule 7).
3. **No standby generator, no buffer resupply.** A consumer whose `standby_fuel` is `none` gets no buffer-resupply edge, because there is no generator to refuel. The couplings stage records the dependency with feed configuration `none`, no edges and a note. This is not an error. It is not an optional dependency either, so coupling density does not count it.
4. **Rule 4 waits for Work Order 5.** Until node requirements exist, every consumer counts as below the transmission-connection threshold, so it is supplied from a distribution substation. Each dependency the rule would govern carries a note that rule 4 is deferred. Capacities are not converted into megawatts. Work Order 5 applies rule 4 once requirements are drawn.
5. **"Inland" in water → generation.** Generation is sited on the coast, so the raw-water reservoir row does not fire in Phase 1. That fits a Taiwan-like island, whose thermal fleet is coastal. The row stays for other map types.
6. **Outlying islands count a sea leg.** A consumer on an outlying island can be reached by coastal tanker or ferry from any seaport on the main island, provided that seaport is itself reachable over the transport links. Such an edge is recorded with `sea_leg = true`. This matches how Kinmen and Matsu are supplied. A main-island consumer still needs a road path.

## Consequences

- `swm.recipe.dependencies` narrows the five supplier lists, and its tests check them.
- The couplings stage (`swm.stages.couplings`) applies answers 3, 4 and 6 as stated. Answer 5 needs no code: the row's `inland` condition is tested against the consumer's cell.
