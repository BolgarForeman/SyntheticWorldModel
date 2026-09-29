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
- Layers stage (Work Order 3). All six layers are sited with siting notes, given classes and attributes, and linked with each layer's signature:
  - roads route around the sea;
  - the runway is recorded as a line.
- Coordinates at Point Nemo in EPSG:32710, with latitude and longitude to 7 decimals (Work Order 3, Part A).
- New commands (Work Order 3):
  - `swm layers`;
  - `swm export-gis` (world.gpkg and GeoTIFFs; optional `export` extra);
  - `swm preview-world`.
- Source scopes with the OpenStreetMap backbone; freight yard and bridge transport classes; the freight yard as an end use with Lifeline weight 4 (Work Order 3, B2 and E2).
- The dependency table of structure v0.5 §4.3a as one immutable table in `swm.recipe.dependencies` (Work Order 4, A1–A2; decision 0007).
- New couplings settings: `two_way_pct`, `public_telecom_share`, `tertiary_second_feed_pct` and `transmission_connection_threshold_mw` (Work Order 4, A3).
- Subtype attributes on every node, drawn from new `layers/<layer>/subtype` streams, as unobserved truth (Work Order 4, B).
- Typed GeoPackage tables: `nodes` plus one `nodes_<layer>` per layer, with typed columns and nulls (Work Order 4, D).
- The couplings stage (Work Order 4, E; decision 0008). It builds every dependency and coupling edge from the dependency table, handling:
  - density, the feed mix, the hub and not-nearest suppliers;
  - two-way pairs;
  - road reachability, with a sea leg to outlying islands;
  - buffer resupply and the public telecom share.

  Each pair draws from its own `couplings/<purpose>/<supplier>-<consumer>` streams.
- New commands (Work Order 4, F):
  - `swm couplings`;
  - `swm preview-couplings`, a schematic for the hand trace;
  - a `couplings` table in world.gpkg;
  - coupling edges in `swm preview-world`, with `--no-couplings`.

### Changed

- CI runs on pushes to `main` and on pull requests only (Work Order 1).
- Power is sized to load. Generation totals distribution × 1.3 × 0.9, and each transmission substation carries at least 1.3 × the distribution it feeds (Work Order 4, C).
- Generation's observed `fuel_type` now follows its true `fuel_kind`, and is no longer drawn on its own (Work Order 4, B).
- The pilot switches on its seven couplings, with density 0 and `two_way_pct` 0 (Work Order 4, A4).
- Five supplier lists of the dependency table are narrowed to what the research lanes found (decision 0008, answer 1):
  - fuel → cable landing and fuel → regional;
  - telecom → transmission substation, blood bank and refinery.
- Heterogeneity is `heterogeneity_pct` on every drawn quantity (Work Order 2, B1).
- Sizes up to 20 nodes per layer and 2,000 km² are Phase 1; concave transfer forms are refused until Phase 5 (Work Order 2, B2 and B3).
- Coverage runs 0-100% and snapshot age 0-30 years (Work Order 2, B5).
- The golden pilot resolved recipe changed with B1 and B4 (recipe schema v1 stays open until Phase 1 closes; decision 0004).
- CI installs the `preview` extra so the preview is linted, type-checked and tested.
- Terrain revised to the Work Order 2 review (decision 0005):
  - a diagonal 3 : 1 spine island filling about a third of the domain;
  - dendritic rivers from finer relief and an epsilon fill;
  - patchy wetland near river mouths;
  - indented coastlines;
  - a 100 m base relief;
  - a minimum town at urban density 0;
  - the preview legend outside the map, with rivers drawn above the cover.

- The terrain peak is rescaled to its bound after carving (Work Order 3, E1).
- `osm_roads_rail` is renamed `osm_transport` (Work Order 3, E2).

### Removed

- The `healthcare_first` service-weight preset, replaced by `lifeline` (Work Order 2, B4).
- The `two_way` switch, replaced by `two_way_pct` (Work Order 4, A3).
