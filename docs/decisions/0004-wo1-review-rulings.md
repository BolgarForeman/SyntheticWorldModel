# 0004 — Work Order 1 review rulings

- **Date:** 2026-09-28
- **Decided by:** the design conversation, confirmed by Foreman
- **Recorded by:** Work Order 2 (Part B)

## Context

The report on Work Order 1 (pull request #2) raised five questions. The design side answered them in Work Order 2, Part B, and issued structure document v0.3 and pilot spec v0.4 to match.

## Decisions

- **B1 Heterogeneity.** Every heterogeneity field is `heterogeneity_pct`: the spread of element values around their context-adjusted target, as a percent of the target (structure v0.3 §4.4).
- **B2 Sizes.** Any size with at most 20 nodes per layer and at most 2,000 km² of land is Phase 1, whether or not it matches a named preset. Only larger sizes are Phase 5.
- **B3 Concave transfer form.** An exact-tier or both-tier recipe that uses concave is valid. The buildability check refuses it until Phase 5, with a clear message.
- **B4 Service weights.**
  - "Lifeline" replaces "healthcare first".
  - Only end-use classes take weights: tertiary, regional, blood bank, clinic, distribution substation, mast, storage, airport, seaport and depot.
  - **Lifeline:** tertiary 10, regional 7, seaport 7, blood bank 6, airport 6, distribution substation 5, water storage 5, fuel depot 4, clinic 3, mast 1.
  - **Equal:** every class 1.
  - **Custom:** each class 0–100.
  - Source: structure v0.3 §5, and the author's judgment on FEMA Community Lifelines categories.
  - The objective is weighted service-hours at end-use nodes. The pilot uses Lifeline.
- **B5 Error-source ranges.** Coverage runs 0–100%, with a validation note at 0. Snapshot age runs 0–30 years.
- **B6 `CLAUDE.md`.**
  - Only `emit/`, `manifest/` and `recipe/io` write files; stages never do.
  - The §5 CLI line lists `resolve`, `check-recipe`, `terrain` and `preview-terrain`.
  - §4 gains the cross-platform arithmetic rule.
- **B7 Schema versioning.** Recipe schema version 1 stays open to change until Phase 1 closes (tag `v0.1.0`), then freezes. Changes before then do not bump the version. The golden pilot files change in Work Order 2 because of B1 and B4.
- **B8 Design README.** The version column now reads structure v0.3 and pilot spec v0.4. The design documents themselves are edited only by the design side.
