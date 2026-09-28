# Changelog

All notable changes to this project are recorded here. Each phase closes with a version tag (`v0.1.0` closes Phase 1).

## Unreleased

### Added

- Repository scaffold (Work Order 0): uv project with the `swm` package, stage package layout, `swm --version`, smoke test, CI on Linux and Windows, repository rules (`CLAUDE.md`), decision log, TRACE log and work-order records.
- Spawn tree (Work Order 1): `stable_id`, named streams off the root seed, the stream registry and the stream record.
- Recipe schema v1 (Work Order 1): the full recipe, validation notes, resolution of defaults, canonical YAML and `recipe_sha256`, and the buildability check.
- `swm resolve` and `swm check-recipe` (Work Order 1).
- The pilot recipe `tests/fixtures/pilot_hand_check.yaml` and its golden resolved recipe and stream record (Work Order 1).

### Changed

- CI runs on pushes to `main` and on pull requests only (Work Order 1).
