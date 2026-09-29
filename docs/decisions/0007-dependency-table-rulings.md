# 0007 — Dependency table rulings

- **Date:** 2026-09-29
- **Decided by:** the author (Foreman), all as recommended on the ruling sheet
- **Recorded by:** Work Order 4, Part H (PR 4a)
- **Sources:** `docs/design/evidence/Dependency_Table_Ruling_Sheet_v0_1.md` and `docs/design/evidence/Dependency_Table_Evidence_v0_1.md` (the five research lanes and the independent review)

## Context

Structure v0.5 §4.3a adds the dependency table: for each of the 21 couplings, which consumer classes depend on the supplier layer, on which supplier classes, and how. Five research lanes built it from sources and an independent reviewer checked it: of 27 sources re-fetched, 12 were confirmed, 14 overstated, 1 wrong and none fabricated, and the review raised 19 findings. Nine rulings were needed before the table could serve as ground truth. The table is the authority for which nodes depend on which; the code encodes it and does not add, drop or retype a row.

## Decisions

- **R1 Public telecom share.** Control dependencies of power, water and pipeline facilities (tank farms and import terminals) ride partly on the utility's own network. Each such edge carries a public share from a recipe setting per consumer. Only the public share is exposed to the telecom layer. The defaults are placeholders: generation and transmission 20%, distribution 50%, water 50%, pipelines 50%. Source: DOE (2023); Taipower's more than 10,000 km of company fibre (台電月刊 Vol. 700).
- **R2 Buffer resupply.** Fuel edges to backup-generator consumers have the role `buffer_resupply`. They do nothing while the consumer's power is up; once it is lost, they extend the generator's runtime and never fail the consumer on their own. All other edges are `primary_supply` ("the buffer has a buffer").
- **R3 Road reachability.** Transport edges run from origins: seaports, airports and freight yards of the eligible kinds. A consumer is supplied if any eligible origin reaches it over the road network, so its dependency lists every such origin with feed configuration `any_reachable`. Roads carry; they are not suppliers. Airports are transport origins (blood products and urgent supplies by air).
- **R4 Tertiary second feed.** A tertiary hospital takes a second distribution substation with a recipe probability (placeholder 50%). It is not a rule for the class.
- **R5 Coal.** The import terminal carries coal (a coal pier and yard), so coal generation has a fuel supplier inside the 21 couplings.
- **R6 Telecom → healthcare** is typed service, not control. A hospital whose records are hosted off site gets a shorter buffer.
- **R7 Rail.** There is no rail in Phase 1. The design side will amend the Appendix B wording ("rail from a later phase").
- **R8 Staff access** to hospitals over roads is out of scope for Phase 1.
- **R9 Subtype attributes** are adopted as §4.3a lists them:
  - generation `fuel_kind` and `makeup_water`;
  - import terminal `product`;
  - airport `towered` and `fuel_receipt`;
  - data centre `cooling`;
  - refinery `crude_receipt`;
  - tank farm `pipeline_connected`, `has_jetty` and `has_truck_rack`;
  - healthcare `records_hosted`;
  - backup consumers `standby_fuel`.

  They are real but unobserved: drawn in the layers stage and never emitted. Where a real source does carry one (WRI's `primary_fuel` for `fuel_kind`), the emission work order handles it.

**Also recorded:**
- **Two-way dependency** is a 0–100 setting (`two_way_pct`): the share of allowed mutual node pairs that are built. At 0 there are none; at 100, every mutual pair the table allows.
- **The pilot's edge range** is 40–50, widened from 35–45. If the realised count falls outside it, the build reports it rather than tuning.
- **Concentration 0** means each consumer takes its nearest eligible supplier, with no pull toward a hub. At 100, the hub carries every consumer it is eligible for.
- **Power sizing** (structure v0.5 §4.2):
  - distribution substations keep their footprint-based size;
  - a transmission substation's capacity is at least the total of the distribution substations it feeds in the power links, times the reserve margin;
  - total generation is total distribution times the reserve margin, converted with the power factor and split across plants by draw;
  - margin 1.3 and power factor 0.9, both placeholders.
