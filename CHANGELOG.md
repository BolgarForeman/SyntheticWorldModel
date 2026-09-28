# Changelog

All notable changes to this project are recorded here. Each phase closes with a version tag (`v0.1.0` closes Phase 1).

## Unreleased

### Added

- Repository scaffold (Work Order 0): uv project with the `swm` package, stage package layout, `swm --version`, smoke test, CI on Linux and Windows, repository rules (`CLAUDE.md`), decision log, TRACE log and work-order records.
- Spawn tree (Work Order 1): `stable_id`, named streams off the root seed, the stream registry and the stream record.
- Recipe schema v1 (Work Order 1): the full recipe, validation notes, resolution of defaults, canonical YAML and `recipe_sha256`, and the buildability check.
- `swm resolve` and `swm check-recipe` (Work Order 1).
- The pilot recipe `tests/fixtures/pilot_hand_check.yaml` and its golden resolved recipe and stream record (Work Order 1).

- Terrain stage for the spine island (Work Order 2): elevation, coastline, drainage, land cover and urban extents, with `swm terrain` and `swm preview-terrain`, and the pilot's golden terrain hashes.
- Lifeline, Equal and Custom service weights over the end-use classes (Work Order 2, B4).

### Changed

- CI runs on pushes to `main` and on pull requests only (Work Order 1).
- Heterogeneity is `heterogeneity_pct` on every drawn quantity (Work Order 2, B1).
- Sizes up to 20 nodes per layer and 2,000 km² are Phase 1; concave transfer forms are refused until Phase 5 (Work Order 2, B2 and B3).
- Coverage runs 0-100% and snapshot age 0-30 years (Work Order 2, B5).
- The golden pilot resolved recipe changed with B1 and B4 (recipe schema v1 stays open until Phase 1 closes; decision 0004).
- CI installs the `preview` extra so the preview is linted, type-checked and tested.

### Removed

- The `healthcare_first` service-weight preset, replaced by `lifeline` (Work Order 2, B4).
