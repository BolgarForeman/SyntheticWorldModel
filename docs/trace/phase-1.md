# Phase 1 — notes toward the TRACE entry

*Notes kept as Phase 1 is built; the entry is completed when the phase closes (`v0.1.0`).*

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

## Crew order among distribution substations (WO-09g answers; decision 0016)

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
