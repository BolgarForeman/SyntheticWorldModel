# 0010 — Answers to the PR 5a questions

- **Date:** 2026-09-29
- **Decided by:** the design side, confirmed by the author (Foreman)
- **Recorded by:** the PR 5a follow-up, `wo5a/fixes` (PR 5a merged as #7 before its review was applied)
- **Source:** `docs/work_orders/WO-05a-review.md`

## Context

PR 5a built the modeling rules registry, the Modeling Rules page, the requirements stage and rule 4, and raised ten questions. Four of the answers change what a world contains: port and airport size, generation size, rule overrides and fuel draws.

## Decisions

0. **CI.** Lint failed on three docstring errors in `tools/build_quantile_table.py`, so CI never ran the tests. They are fixed, and the whole repository is linted, as CI does.
1. **Ports and airports are sized to the city they serve.** Their size class follows the served city's urban footprint, set against Taiwan anchors, not its rank among the world's cities. The mapping is in the registry (`layers.attributes.seaport_size_class` and `airport_size_class`, km² at or above), as a placeholder with its reasoning; the old share-based tables are in each entry's history. The pilot now has a small port (class S) and a small airport.
2. **Generation is sized to all load.**
   - Total generation capacity is the total peak load of every power consumer, distribution-fed and transmission-fed alike, times the reserve margin (1.3).
   - Each transmission substation carries at least the reserve margin times the distribution capacity it feeds, plus the transmission-fed peak load converted to MVA with the power factor.
   - Sizing needs the requirements, so it moves from the layers stage to the requirements stage. That stage returns the layers with generation and transmission sized, and every later stage and export uses them.
3. **Every rule is overridable.** The per-rule `overridable` flag is gone. A recipe may override any rule with a value of the same kind (a number for a number, a table for a table), and the entry is revalidated. The layers stage and the dependency table now read the registry passed to them, so overrides reach every stage. Overrides are listed beside the registry hash in the resolved recipe and stamped on the world.
4. **Placeholder fuel draws (grade J)** for the three transport consumers whose §4.3a fuel rows had no target. Each is converted to GJ/day with a placeholder energy content (jet fuel 34.7 GJ/m³, diesel 38.6 GJ/m³).
   - **Airports:** jet fuel at 50 L per passenger, scaled by passenger throughput.
   - **Seaports:** bunkers and cargo-handling diesel, at 50 and 5.4 L per box, scaled by container throughput.
   - **Freight yards:** diesel at 0.01 L per m² per day, scaled by area.
5. **Confirmed as reported:**
   - transport access is served or not, like telecom;
   - rows that name a transmission substation (refinery, LNG terminal) keep it below the threshold, because the table names it from evidence;
   - a tertiary hospital large enough for rule 4 stays single-fed when the world has one transmission substation, with a note;
   - the unsourced sizes (data centre IT load, refinery crude run, LNG send-out, water at fuel facilities) stay as placeholders marked open.
6. **Failure-mode heterogeneity** defaults to 10%, as §4.4a says. This is done here, not in PR 5b.
7. **The unused Work Order 1 stream `unobserved/requirements` is retired.** Requirements draw from `requirements/<layer>`. Streams are keyed by name, so no other stream moves.
8. **Interface mockup:** no change now. The new recipe fields, `distribution_voltage_kv` and `modeling_rules`, are logged for the Phase 7 interface.

## Addendum: answers to the PR 5a follow-up (#8)

- **Date:** 2026-09-29
- **Decided by:** the design side, confirmed by the author (Foreman)
- **Source:** `docs/work_orders/WO-05a-fixes-answers.md`
- **Recorded by:** PR 5b

1. **Port and airport sizing: confirmed.** The served city's absolute urban footprint in km² is compared with the Taiwan-anchored thresholds in the registry, not ranked among the world's cities.
2. **Power factor: confirmed.** It applies where MW becomes MVA, in transmission substation sizing. Generation stays in MW.
3. **The outlying-island count is exact.**
   - The terrain must deliver the requested number of outlying islands. Where it truly cannot, the build stops with a clear error naming the setting, never silently fewer islands.
   - This fixes the edge case the property test found (a 1 km² world asked for one outlying island produced none).
   - It is a small separate pull request, on `terrain/island-count` from main after PR 5b. It must not change the pilot, whose terrain golden files stay unchanged.
