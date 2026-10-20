# Phase 1 — TRACE entry

*Phase 1 closes on recipe schema version 3 and structure spec v0.15, as `0.1.0` (Work Order 9, G1). The `v0.1.0` tag waits for Foreman's word after PR 9c merges. The closing summary comes first. The records kept while each work order was built follow it, unchanged apart from their heading level.*

## What Phase 1 built

Phase 1 builds a small constructed world end to end, from one recipe and one root seed:
- the terrain;
- six interdependent infrastructure layers and their couplings;
- the storm, and the engine that plays each storm out;
- the sources, written in their real formats with zero error, beside a truth manifest and a hand-trace game.

| Work order | What it built |
|---|---|
| 0 | The scaffold: the uv project and `swm` package, the CLI, CI on Windows and Linux, `CLAUDE.md`, the decision log and the TRACE log. |
| 1 | The spawn tree (`stable_id`, named streams off one root seed, the stream record). Recipe schema v1: validation, resolution of defaults, canonical YAML, `swm resolve` and `swm check-recipe`. The pilot recipe and its goldens. |
| 2 | The terrain: a spine island with elevation, coastline, drainage, land cover and towns (`swm terrain`, `swm preview-terrain`). Service weights. |
| 3 | The layers: all six sited, classed and linked by signature on Point Nemo coordinates (EPSG:32710). `swm layers`, `swm export-gis` and `swm preview-world`. |
| 4 | The dependency table, subtype attributes and the couplings stage (`swm couplings`, `swm preview-couplings`). Power is sized to load. |
| 5 | The modeling rules registry (decision 0009), from which every rule is read. The requirements, buffers, strength, crews and repair stages, and the undisturbed-supply check. Recipe schema v2 (decision 0011). |
| 6 | The storm (wind field and flood depth; decision 0012) and the scenarios (line and facility damage). Mapped power lines on terrain routes (decision 0013). |
| 7 | The dynamics engine and `swm simulate`; the calm-world and link-signature checks; the pilot's 8 reference runs. Recipe schema v3 (decision 0014). |
| 8 | Emission from an observed-only world into seven source formats. The truth manifest, `swm emit` and `swm build`. The pilot's whole build as goldens (decision 0015). |
| 9 | The hand-trace pack (9a) and the trace game (9g). Two more golden worlds, the Phase 1 error-settings notice and property tests (9b). The hand-trace acceptance test and these records (9c). Decision 0017. |

## How it was tested

### Golden worlds

Each golden world is a recipe with checked-in output and hashes. CI rebuilds each one on Windows and on Linux, and the output must match byte for byte.

| Golden | Recipe | What is golden |
|---|---|---|
| `pilot_hand_check` | the pilot | resolved recipe, stream record, and every stage's statistics and hashes (terrain to scenarios) |
| `pilot_reference_runs` | the pilot | the 8 storm scenarios played for 72 h: states, stocks, crews and the run record |
| `pilot_build` | the pilot | the whole `swm build` tree: sources, truth manifest and trace pack (139 files) |
| `pilot_board_sizes` | the pilot | the trace game's board at every print size |
| `pilot_hidden_telecom_build` | the pilot, telecom hidden | the whole build tree |
| `pilot_power_nodes_only_build` | the pilot, power reporting nodes only | the whole build tree |

The crew, repair and storm sensitivity copies of the pilot are fixtures, not goldens. They exercise paths the pilot does not reach, such as flood damage at severity 70.

### Checks, and where they ran

| Check | Proven by | Result |
|---|---|---|
| Identity: same recipe, same bytes, every platform | every golden above, on Windows and Linux CI; `test_same_bytes_properties.py` for any seed | pass |
| Hiding or thinning a source changes what is emitted, never what exists | `test_fixture_worlds.py`: for both fixture worlds, the stage hashes, the manifest's true world and all 8 reference runs equal the pilot's, and every differing file has a stated reason | pass |
| No unobserved field reaches an emitted file; emission never imports the dynamics or error induction | `test_emission.py` (separation and import tests) | pass |
| Error settings move nothing that exists | `test_error_settings_properties.py` (holds trivially in Phase 1; bites from Phase 3) | pass |
| Error settings recorded, not applied (C2) | `test_error_settings.py`: one warning, the declared departure, the recipe note, sources byte-equal to a zero-rate build | pass |
| Feed shares total 100% | `test_feed_mix.py`; `test_couplings_properties.py` (realised) | pass |
| Nodes = area × density within rounding | `test_node_density_properties.py` | pass |
| Adding a stream moves no existing stream | `test_rng_properties.py` | pass |
| Terrain, layers and couplings invariants for any valid section | `test_terrain_properties.py`, `test_layers_properties.py`, `test_couplings_properties.py` | pass |
| World checks: undisturbed supply, link signature, calm world, calm run | `swm check`, `test_strength.py`, `test_signature.py` and `test_dynamics.py`, on the pilot and the severity-70 copy | pass |
| Degradation profiles v0.3 | `test_degradation_profiles.py`: one test per profile, each limit also at its relaxed value | pass |
| The rule cards' drills | `test_trace_game.py`: each of the 12 drills is played by the engine at build | pass |
| **Hand-trace acceptance (F0, as changed):** the design side's sealed trace of scenario 7 | `test_hand_trace.py` against `tests/fixtures/hand_trace_scenario_7.yaml`, compared exactly at the 15-minute step | pass (see below) |

The hand-trace test compares every value in the trace: crew arrivals, preparation and completions; back-in-service hours; hours out for all 15 end-use nodes; the score (52.25); the named states; and the three things that did not happen.

**Whole suite at close:** 1,448 tests, all passing on Windows and Linux CI (PR 9c), with 97% line coverage of `src/`.

### Waiting for later phases

- Realized error, uniqueness and quiet planting: Phase 3, when errors are applied.
- "Zero error reproduces the clean emission": Phase 3.
- Answer keys found by brute force and checked against the MIP: Phase 2.
- Realism ranges: Phase 5.

### Validation

- **Face validity.** The author reviewed the terrain, layer, storm, extract and trace-pack previews (figures below).
- **Teaching text.** Foreman approved the rule cards, field manual and debrief (`docs/design/trace_game/REVIEW_LOG.md`).
- **Not yet done.** Expert review and the docking reimplementation.

## Departures from the design

Each departure is recorded with its reason in the decision named, or in the records below.

- **Error settings are recorded, not applied.** Phase 1 emits every source with zero error.
  - A recipe's error settings are kept in the resolved recipe, which notes beside its errors section that they are not applied.
  - `swm build` and `swm emit` print a warning naming each source above zero.
  - The manifest declares the departure (WO-09 C2, ruled 2026-10-11; decision 0017).
- **The manifest's declared departures** (decision 0015):
  - the register's coordinates stand in the address column;
  - names are in English only;
  - footprints are rectangles;
  - PBF blobs are uncompressed;
  - register coordinates are at 6 decimals;
  - WRI columns the world does not hold are left empty;
  - three Overpass queries are inferred from landed tags;
  - the register's file is named in ASCII;
  - there is no source overlap until Phase 3.
- **Telecom fallback and travel.** The engine's telecom fallback and travel legs went beyond what spec v0.12 §4.5 said. Both were reported in PR 19. Travel along a line was then ruled (decision 0017), and v0.14 records the rest.
- **The hand-trace acceptance test.** Work Order 9 named Foreman's son's play-test as the test. Foreman ruled the play-test a nice-to-have; the test is the design side's sealed trace of scenario 7 against the engine (WO-09c answers, F0; decision 0017).
- **The engine's calibration and timing:**
  - the line-loss calibration targets the expected share, not one realized draw (PR 7b answers);
  - Degradation Profiles v0.3 corrects v0.2 to the world as built;
  - a fuel delivery waits for the depot's settled state within its step (decision 0014).
- **The stated area of an extract** is the world's whole map area, not the extent of what was emitted (spec v0.15 §4.6; decision 0017).
- **Rule card 2's floor line** still carries a CONFIRM marker. When a generator's fuel runs out, the engine trips, rather than taking what arrives. This is reported for a ruling, and the card is unchanged.
- **Placeholders.** Values marked `placeholder (open decision: …)` in the registry, among them the Taiwan-scale counts, stand until they are ruled. The Modeling Rules page (`swm rules`) lists every one.

# Records kept while Phase 1 was built

## The dynamics engine (Work Order 7, PRs 7a and 7b; decision 0014)

**What was built.**
- **Engine:** `src/swm/dynamics/` plays one storm scenario out over time.
  - A node's state is its condition × the lowest of its responses across its commodities.
  - Edges deliver κ × g_δ(supplier state), linear or at the threshold θ.
  - Links inside power, telecom, water and fuel carry their layer's commodity from the signature's first stage down.
  - Stocks cover their own commodity, refill as ruled, and take fuel deliveries.
  - Telecom tolerance acts first.
  - Crews work through repairs in the default order, with a 2 h crew-bound lead per job and parts lead time running in parallel.
  - A substation whose telecom is down needs a manual switching trip.
  - Steps are 15 minutes, settled within each step up to 100 passes.
- **Commands:** `swm simulate` prints the hourly trajectory and plots a timeline. `swm check` runs the calm-world run on every world.
- **Isolation:** the engine is pure. It never imports error induction or emission, and the generator never imports it.

**How it was tested.**
- **Degradation profiles:** one test per profile in Degradation Profiles v0.3, each limit also at its relaxed value. All pass.
- **Calm world:** with no damage, every node holds 1 and nothing moves on the pilot and the severity-70 copy.
- **Properties on the pilot:** relaxing any single limit, or protecting any damaged element, never raises any node's hours out.
- **Constructed cases:**
  - removal versus relaxing;
  - crew-bound lead per job, parallel parts and the crew order;
  - manual switching only when telecom is down and the repair is elsewhere;
  - a step that hits the settling cap is reported;
  - a ring of links cannot keep itself supplied;
  - pump capacity pro rata by demand;
  - a missed delivery made when the depot returns;
  - hospital water refilled from the main.
- **Reference runs:** the pilot's 8 scenarios are saved as goldens (`tests/golden/pilot_reference_runs/`) and must reproduce byte for byte on Windows and Linux.

**Departures from the design.**
- **Line-loss calibration:** the targets were moved from one realized draw to the expected share. The realized share depended on the draws, which changed when storm damage moved to one stream per element (PR 15 answers; PR 7b answers).
- **Degradation profiles:** v0.2 said LNG and oil plants ride out a fuel cut on their own stocks. The world holds those stocks upstream, so v0.3 corrects the profile to the world as built.
- **Delivery timing:** a fuel delivery waits for the depot's settled state within its step.

## Emission (Work Order 8; decision 0015)

**What was built.**
- **Projection:** the emission stage projects the world onto an observed-only world, which is all the writers ever see.
- **Writers:** they write the OpenStreetMap extract and its two views (Geofabrik shapefiles and Overpass responses), WRI, OurAirports and the three register file types.
- **Truth manifest:** it holds:
  - every record's true element;
  - the true geometry and every unobserved value;
  - the hidden items and the declared departures;
  - θ\* by registry fingerprint, and the seeds.
- **Commands:** `swm build` writes the whole tree, with a hand-trace pack for scenario 7.

**How it was tested.**
- **Identity:** the pilot's 115 built files are golden.
- **OpenStreetMap geometry:** each feature is in its source's scope, outlines are closed and centred, lines pass through their towers in order, ids are reserved, unique and sorted, and nodes-only layers have no ways.
- **Identifiers and names:** identifiers are reserved, and names are deterministic and screened.
- **Headers:** they match exactly, and were checked once against the real files through `machine.toml`.
- **Correspondence:** each record maps to exactly one true element, and every in-scope element is listed.
- **Separation:** no writer reaches unobserved fields, the dynamics or error induction, and no source file carries a manifest-only id or value.
- **Hand trace:** the timeline equals reference run 7.

**Departures from the design.** These are the declared departures in the manifest (as amended by the PR 17 answers):
- the register's stand-in coordinates at 6 decimals, a choice;
- WRI's commissioning year and owner left empty, because the world does not hold them;
- three Overpass queries inferred from landed tags, query text not saved;
- an ASCII register file name;
- uncompressed PBF blobs.

**Rounding is part of the clean emission (PR 17 answers; structure v0.11 §4.1a).** Each source is written at its real file's precision:

| Source | Decimals |
|---|---|
| OpenStreetMap | 7 |
| WRI | 4 |
| OurAirports | 6, measured as the most common count |
| Facility register | 6, a choice |

The tests compare each emitted location with the true one within half a unit in that source's last decimal place. The Phase 3 realized-error check must therefore measure planted error against the clean, rounded file, never against the true location.

**Names (PR 17 answers 2).** Every class is unique by name within its town except six shared-name classes. A repeat takes a direction word, then a number. The unnamed share stays on three classes.

**Correction found in testing.** The manifest's view matching treated OpenStreetMap node and way ids as one space. A test that read names across views hit the same overlap, which exposed the mistake. Matching is now on type and id, and a regression test checks every listed shapefile class against the element's own tags.

**Figures.**
- `figures/wo8_pilot_extract_qgis.png`: the pilot's `island.osm.pbf` rendered by QGIS 3.40.14, with its multipolygons, lines and points, and points labelled by name.
- `figures/wo8_hand_trace_map_scenario_7.png`: the trace pack's `map.pdf` rasterized by GDAL.

## The hand-trace pack (Work Order 9, PR 9a)

**What was built.**
- The pack is split into a blind part (`trace_pack/`: map, rules sheet, tables) and the answer (`trace_pack/answer/`: the reference run's timeline).
- The new tables give a tracer what the design side's first trace had to take from the truth manifest and the stage outputs: link lengths and flow, stocks, generator draws, tolerance rows, failure points with travel, crews, travel times, the crew order and the engine's numbers with their registry ids.
- The map is framed on the island. It carries a storm-track inset, larger-scale insets where labels crowd, and line ids and failure points.

**How it was tested.**
- Every table value is compared with the engine's world or the registry.
- The travel to a failure point equals the reference run's first trip.
- The blind pack is byte-identical whether the run is the reference run or one with a protected line, so it holds nothing from the run.
- The golden pack changes only under `trace_pack/`.

**Figure.** `figures/wo9a_hand_trace_map_scenario_7.png`.

## The trace game (Work Order 9, PR 9g)

**What was built.** The hand-trace pack became a print-and-play game: node cards, rule cards with drills, the board, the briefing, log sheets and tokens in `game/`, and the sealed answer in `answer/`. PR 9a's tables moved to `data/`. The rule cards, field manual and debrief are typeset from the design side's draft text (v0.1), awaiting Foreman's ruling.

**How it was tested.**
- Every number on the cards, the briefing and the sheets is compared with the engine's world, the scenario's damage or the registry.
- The player's `game/` is byte-identical whether the run is the reference run or another.
- No teaching text names a node, line or crew of the world.
- Each of the 12 drills is a constructed world played by the engine, and its printed answer must match.
- The sealed score equals the reference run's.
- The board is golden at every size.

**Departures from the design.**
- The fallback symbol is ◷, because the bundled font has no ⏳; the design text's ⏳ prints as ◷.
- Rule card 9's printed answer gives crew 1 the substation feeding the hospital. The engine ranks a distribution substation by its own Lifeline weight; both weigh the same, so the nearer one goes to crew 1. The drill world's expectation (both substations first, the pump waiting) holds. Reported for a ruling.
- The node cards' needs include the hidden couplings the engine plays (marked "(hidden)"); supplies and the board show switched-on couplings only, as the work order says. This is a question for the design side.

**Rule cards 5, 10 and 12 read from the engine (PR 19 follow-up).** Their "[CONFIRM WITH ENGINE]" markers now state what the engine does. Card 10 has a worked example and an engine-verified drill: the crew finishes the line at 18.85 h.

Where the engine departs from structure v0.12 §4.5 (reported, not changed):
- **Telecom fallback.** §4.5 says "then d_eff". In the engine, the received share is raised to r + (1 − r) × d_eff and the facility's telecom response acts on it. A tripping facility whose d_eff is below the trip point goes to 0: the pilot's tertiary hospital trips on telecom with d_eff 0.85.
- **Travel.** §4.5 names only the off-road walk to a line. The engine also drives a facility's access leg to the nearest road, walks off a line when leaving it, and crosses where no road joins at road speed plus the mobilisation delay. Preparation comes once per job.

**Figures.** `figures/wo9g_*.png`.

## Crew order among distribution substations (WO-09g answers; decision 0017)

**What changed.** A distribution substation in crew-order group 2 now ranks by the highest Lifeline weight among the end uses it supplies through the electricity couplings the engine plays, switched on or hidden. The engine reads `dynamics.substation_crew_rank`.

**How it was tested.**
- The ranking is checked node by node on the pilot.
- An alternative named in the registry stops the run.
- Rule card 9's drill now checks the printed crew assignment.

**Golden changes.** The reference runs, stage stats, resolved recipes and manifest change only in the registry stamp; the manifest also gains the new Theta List entry. No pilot run has a distribution-substation job, so no crew order, timeline or hours out moved.

## Crew travel along a line, and the approved teaching text (WO-09g answers 2)

**The hand trace.** The design side's sealed trace of scenario 7 found one point the spec had not settled: travel between failure points of one line. Under Foreman's ruling (walk along the line), the engine's scenario 7 matches the design side's recomputed trace exactly: TEL-0003 back at 18.00 h, TEL-0002 at 34.25 h, 52.25 service-hours lost.

**Golden changes.** Scenario 7's run changes: crew 2's second walk on TEL-L0002 takes 1.0 h instead of 6.7 h, and everything after it moves 5.725 h earlier. The other seven runs change only in the registry stamp.

**Teaching text.** The rule cards, field manual and debrief are approved and print without DRAFT marks. Card 2's floor line is reported against the engine: when the generator's fuel runs out, the engine trips, rather than taking what arrives.

## Golden worlds, error settings and property tests (Work Order 9, PR 9b)

**What was built.**
- Two fixture worlds, each the pilot with one change: telecom hidden, and power reporting nodes only. Both have golden builds.
- The manifest lists a hidden layer's couplings as hidden and records the links nodes-only sources withhold.
- The Phase 1 error-settings notice (C2).
- Property tests for the error seed, nodes = area × density, and same bytes for any seed.
- Under spec v0.15 §4.6, every extract's bounds and Overpass search area are the world's whole map area.

**How it was tested.** The fixture worlds equal the pilot in every stage hash, the manifest's true world and all 8 reference runs. Every file that differs from the pilot's goldens is listed with its reason, and the bounds and search areas equal the pilot's.

**Golden changes.**
- The pilot's resolved recipes gain the C2 note, and its manifest gains `withheld_links` and the C2 departure.
- The pilot's bounds and query areas changed once, to the map area. Nothing in the world moved.

## Hand-trace values and the Phase 1 records (Work Order 9, PR 9c)

**What was built.**
- `test_hand_trace.py` checks the engine's scenario 7 run against the design side's hand-written fixture, at the 15-minute step and exactly.
- An event's step hour is the first step at or after it, where the engine applies its effect.

**How it was tested.**
- All 12 comparisons pass with the fixture as sent. It was not edited or regenerated.
- No golden changed.
