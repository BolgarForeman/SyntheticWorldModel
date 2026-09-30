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
  - coupling edges in `swm preview-world`, with `--no-couplings`;
  - `couplings_edges.csv` from `swm couplings`, and a printed edge table in the schematic (decision 0008).
- Two-way never leaves a core dependency without a supplier: the mutual pair is kept, with a note (decision 0008).
- The modeling rules registry (Work Order 5, Part A; decision 0009). It holds:
  - every §4.4a design target;
  - the dependency table, moved from code with its 99 rows;
  - the layers stage's shares, siting distances and weights, attribute ranges and subtype shares;
  - power sizing and the transmission threshold.

  Code reads rules by id. The registry's version and hash are stamped on the resolved recipe and on every stage's statistics; overridable rules take recipe overrides.
- `swm rules`: the Modeling Rules page (Work Order 5, A4).
- The requirements stage and `swm requirements` (Work Order 5, Part B). It draws electricity, water, fuel and access per node around the §4.4a targets, with the shared quantile-table draw method (`swm.draws`; offline builder in `tools/`).
- The buffers stage and `swm buffers` (Work Order 5, Parts D and F):
  - reserves at the expected draw;
  - backup presence from the subtype attributes, and generator availability (Marqusee & Jenket);
  - fuel resupply on buffer-resupply edges;
  - the telecom tolerance buffer;
  - failure modes.
- The strength stage and `swm strength` (Work Order 5, Part E): κ and headroom on every edge, and each dependency's supply ratio.
- `swm check`: the undisturbed-supply world check (Work Order 5, E2).
- The crews stage (Work Order 5, Part H): crew bases sited at town centres by road access, the crews in one pool, and the emergency pool from the registry.
- The repair stage and `swm repair` (Work Order 5, Part G). It records, per node:
  - permanent repair at all four damage states: drawn around the Hazus MR4 mean at the Hazus spread, then split into lead time and crew work (8, 24, 72 and 168 h);
  - the emergency mode: a mobile substation or a mobile cell site;
  - travel from the crew base over the roads, as its own term.
- Crew sensitivity recipes with 1, 2 and 3 crews (`tests/fixtures/crew_sensitivity/`); fixtures, not golden files (Work Order 5, H3).
- Rules `crews.road_speed_kmh` and `repair.no_repair_rows`.
- Recipe controls `unobserved.mobile_substations` and `unobserved.mobile_cell_sites` (default 1 and 1), the emergency pool (decision 0011, addendum).
- Repair sensitivity recipes at a repair gap of +20 and −20 (`tests/fixtures/repair_sensitivity/`); fixtures, not golden files.

### Changed

- Repair rates default to a gap of 0 and the Hazus spread; the recipe's repair heterogeneity is now an optional override (decision 0011, addendum).
- The recipe schema is version 2: `unobserved.depots` is renamed `unobserved.crew_base`. Version 1 recipes are migrated on loading (decision 0011). The pilot sets `crew_base: 1`.
- CI runs on pushes to `main` and on pull requests only (Work Order 1).
- Power is sized to load. Generation totals distribution × 1.3 × 0.9, and each transmission substation carries at least 1.3 × the distribution it feeds (Work Order 4, C).
- Generation's observed `fuel_type` now follows its true `fuel_kind`, and is no longer drawn on its own (Work Order 4, B).
- The pilot switches on its seven couplings, with density 0 and `two_way_pct` 0 (Work Order 4, A4).
- Ports and airports are sized by the urban footprint of the city they serve, not its rank (decision 0010).
- Power is sized to load in the requirements stage: generation to the total peak load of every power consumer × 1.3, and each transmission substation to at least what it feeds (decision 0010).
- Any modeling rule may be overridden by a recipe; the layers stage and the dependency table read the registry passed to them (decision 0010).
- Airports, seaports and freight yards draw placeholder fuel (decision 0010).
- The compliance gap is capped at 95 (Work Order 5, D2).
- Masts and clinics hold no diesel standby set; the national LNG, oil and coal stocks take a compliance gap of 0; non-towered airports and truck-fed tank farms get telecom tolerance rows (decision 0010, second addendum).
- Failure-mode heterogeneity defaults to 10%, as §4.4a says (decision 0010).
- Rule 4 applies by load: a consumer whose peak load is at or above 5 MW (10 MW with `distribution_voltage_kv: 22.8`) is supplied from a transmission substation (Work Order 5, C1).
- The recipe's couplings section replaces `tertiary_second_feed_pct` and `transmission_connection_threshold_mw` with `distribution_voltage_kv`. The tertiary second-feed share is now an overridable modeling rule, and the recipe gains a `modeling_rules` section.
- The schematic's mutual-pair rings sit on the pair's own arrows (Work Order 5, C3).
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

### Fixed

- The terrain now delivers exactly the requested number of outlying islands. An island placed near the grid edge could merge with the main island, because its clearance window was cut empty. If the count can't be met, the build stops with an error naming `terrain.character.outlying_islands` (decision 0010, item 3). The pilot terrain is unchanged.

### Removed

- The `healthcare_first` service-weight preset, replaced by `lifeline` (Work Order 2, B4).
- The `two_way` switch, replaced by `two_way_pct` (Work Order 4, A3).
- The unused Work Order 1 stream `unobserved/requirements` (decision 0010).
- The unused Work Order 1 streams `unobserved/reserves` and `unobserved/failure_mode`, superseded by `reserves/<layer>` and `failure_mode/<layer>`.
- The unused Work Order 1 streams `unobserved/repair_rates` and `unobserved/crews_and_depots`, superseded by `repair/<layer>` and an undrawn crew-base siting (decision 0011).
- The four unused Work Order 1 streams `couplings/edges`, `couplings/supplier_not_nearest`, `couplings/feed_configuration` and `couplings/two_way` (decision 0008).
