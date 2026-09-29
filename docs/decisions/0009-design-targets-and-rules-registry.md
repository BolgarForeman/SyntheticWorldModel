# 0009 — Design targets and the modeling rules registry

- **Date:** 2026-09-29
- **Decided by:** the author (Foreman), T1–T11 as recommended on the ruling sheet, with T4 and T11 ruled by Foreman; the registry ruled with them
- **Recorded by:** Work Order 5, Part I (PR 5a)
- **Sources:**
  - `docs/design/evidence/Design_Targets_Ruling_Sheet_v0_2.md`;
  - `docs/design/evidence/Design_Targets_Evidence_v0_1.md` (four research lanes and an independent review);
  - structure v0.6 §4.4 and §4.4a.

## Context

Work Order 5 draws the quantities no source reports: requirements, reserves, coupling strength, failure mode, repair and crews. Each draw is centred on a design target, the value a code, standard or authoritative guidance sets for that kind of facility. Two levers, heterogeneity and the compliance gap, then move the truth away from it.

Four research lanes built the targets and an independent reviewer checked them. Of 22 sources re-checked, 17 were confirmed, 3 overstated, 2 unreachable, and none were wrong or fabricated. Eleven rulings were needed before the targets could shape a world.

## Decisions

- **T1. Taiwan first.** A Taiwan rule is used wherever one exists, and every target shows its grade and jurisdiction. The fallback order after Taiwan is to be decided.
- **T2. Hospitals.**
  - Tertiary and regional hospitals both hold 72 h of generator fuel.
  - Clinics hold none by default.
  - On generator power a hospital runs its essential load, about 60% of normal.
- **T3. Hospital water.**
  - Stock is 72 h at the emergency ration of 300 L per bed per day.
  - Normal draw is 1.0 (tertiary) and 0.5 (regional) m³ per bed per day.
  - In a water outage the hospital drops to the ration.
- **T4. Telecom loss is a tolerance buffer.** This closes open decision 7 for telecom.
  - A facility keeps full function on manual fallback for T hours, then steps to a degraded level d.
  - Only the public share κ counts: d_eff = 1 − κ(1 − d); T is not scaled.
  - When telecom and another supply fall short together, the facility takes the lowest level, not the product.
- **T5. Transmission connection at 5 MW** of peak load (Taipower's 11.4 kV areas), with a recipe switch to 10 MW (22.8 kV areas).
  - The same rule, not a fixed class list, decides every consumer's supplying substation.
  - Peak load is the requirement × a peak factor (placeholder 1.3).
- **T6. Repair.**
  - Repair splits into a lead time that holds no crew and crew work hours.
  - The pilot storm causes only slight and moderate damage at facilities.
  - The pilot's 2 crews in one pool are a declared scarcity, with a sensitivity test at 1, 2 and 3.
  - The repair base is renamed `crew_base`.
- **T7. Compliance gaps.**
  - Defaults: hospital backup 15%, water facilities 20%, exchanges and data centres 0%, masts 0% against the Taiwan 4 h rule.
  - Generator reliability is a separate per-generator availability draw (Marqusee & Jenket 2020), not part of the gap.
- **T8. Fuel resupply** on buffer-resupply edges: 12 h lead time, 24 h of fuel per delivery (placeholders).
- **T9. What the levers mean.**
  - Draws come from one skewed, positive quantile table.
  - The compliance gap shifts the median; a gap of 0 means centred on the target, not that every element complies.
  - The gap is capped at 95; absence of backup is carried by the presence attributes.
- **T10. Coupling strength.**
  - κ = min(1, available supply ÷ requirement); the uncapped ratio is recorded as headroom.
  - A telecom edge's κ is its public share.
  - A world check requires every consumer to be fully supplied before any disruption.
- **T11. Emergency repair** alongside permanent repair: a mobile substation (12–24 h, about 25 MVA) and a mobile cell site (about 14 h, capacity 0.5). The pilot's pool is 1 of each.
- **The modeling rules registry and page.** Every rule and number that shapes the world lives in one registry, `src/swm/rules/modeling_rules.yaml`. Each entry records:
  - its source, grade and jurisdiction;
  - its reasoning and status;
  - its ruling and its history.

  Code reads rules by id. `swm rules` renders the registry as the Modeling Rules page. The registry's version and SHA-256 are stamped on the resolved recipe and on every world. A recipe may override rules marked overridable, for sensitivity runs; overrides are listed beside the hash.

## How a rule changes

A rule changes only by a reviewed pull request that:
1. edits `modeling_rules.yaml`;
2. moves the old value into the entry's `history`, with the date and the decision that changed it;
3. cites the new source;
4. adds a decision record.

The registry hash then changes, and so does every golden file that records it.
