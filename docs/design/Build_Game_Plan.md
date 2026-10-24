# World Generator — Build Game Plan

*v0.1 · 2026-09-28 · builds against World_Generator_Structure_v0_2 and interface mockup v0.5*

## 1. Where we are

The design is far enough along to start writing code. Nothing has been coded yet.

| Piece | State |
|---|---|
| Literature sweep on generator design | Done (v0.1) |
| Structure document | v0.2: stages, the three kinds of quantity, the answer-key split, checks, open decisions |
| Interface mockup | v0.5: nine steps plus the recipe panel and the full recipe screen. It serves as the spec for every control |
| Pilot spec | v0.3: the first job the generator has to do |
| Code | None |
| Recipe schema | Exists only as the mockup's file view. It has not been written as a schema |

**The main build decision:** build the engine first and the interface last. The recipe file is the contract between them. A working generator is a program that reads a recipe and writes a world. The clickable interface is a front end that writes recipes. That order means:

- the pilot can run long before any interface exists;
- every world stays reproducible from a text file;
- the interface can't hide a choice that isn't in the recipe.

**Phase 2 closes as 0.2.0** (Work Order 12): every pilot answer key is found by brute force, and the MIP cross-check is held for after the proposal (decision 0021; `docs/trace/phase-2.md`).

## 2. Decisions to close before the first line of code

| # | Decision | Recommendation | Why now |
|---|---|---|---|
| 1 | Language | Python. It has the geospatial stack (shapely, geopandas, pyosmium for PBF), the network stack (networkx), NumPy SeedSequence for the spawn tree, a MIP solver interface (PuLP or Pyomo with HiGHS), and it matches the Ch6 ingestion work | Everything else builds on it |
| 2 | Where the code lives | One Git repository, pushed to GitHub (private). Both machines clone it, and a small per-machine file points to local data. This also covers most of the Norns' Voice ↔ Strabo problem for this code | Needed from the first commit |
| 3 | Recipe schema v1 | Write it as a typed schema (pydantic) with the mockup's file view as the draft. Version the schema from day one | The contract between the engine and the interface |
| 4 | Buffer typology | Start stock-only (every buffer is a reserve). Add a tolerance buffer later if the ruling calls for one | Only matters from Phase 1 on; a default keeps it from blocking |

Several decisions can wait until the phase that needs them:

- anchors with citations: Phase 2, placeholders until then;
- realism ranges from the corpus: Phase 5;
- size of the overlap band: Phase 5;
- exact-tier instance bound: Phase 5;
- seeds per cell: Phase 4.

## 3. Phases

Each phase ends with a working generator that does more than the phase before. Phases 1–4 are the pilot path. Phases 5–8 grow the pilot generator into the study generator.

### Phase 1 — Walking skeleton (hand-check size)

A recipe goes in and a world comes out, end to end, at 24 nodes, with every stage present even when thin.

- **Recipe:** loading and validation; the root seed and the spawn tree.
- **Terrain:** one map type (spine island), with the character settings wired even if they're crude.
- **Layers:** siting rules for all six layers; intra-layer links with each layer's signature; hidden, off and nodes-only states.
- **Couplings:**
  - the 6×6 matrix;
  - supplier not nearest;
  - the feed mix;
  - concentration;
  - one storm corridor with scenarios.
- **What sources don't show:** coupling strength derived; reserves, requirements, repair rates and failure mode drawn from context, with the two levers; crews and depots.
- **Dynamics:** exact-tier forms only (linear, threshold, step); typed weakest link.
- **Emission:** one small file per layer in its real container. A layer with nodes-only sources gets no links.
- **Truth manifest and printable map.**

**Done when:**
- the same recipe and seed re-emit byte-identical files (the identity check);
- changing an error setting leaves terrain and infrastructure unchanged;
- the printed map and tables are enough to trace one scenario by hand.

### Phase 2 — Answer-key solver

- **Model requests:** class, model, objective, service weights, budget.
- **Three pilot models** (ruled 2026-10-20, Phase 2 ruling sheet; the informative model moves to Phase 4):
  - defensive: protect condition, add reserve;
  - offensive: strike k nodes;
  - restorative: sequence two crews.
- **Answer keys:** brute force over every affordable answer at hand-check size. The time-expanded MIP cross-check of the engine's dynamics is held for after the proposal (decision 0021).
- **Per request:** the spread of every answer's distance from the best; each rule of thumb's distance (most connections, biggest, nearest supplier); true criticality; the decision-relevant dose.
- **The "assumes:" stamp.**

**Done when:** every key is found by brute force over every affordable answer, with the MIP cross-check held under decision 0021. Every key reports; none is silently regenerated.

### Phase 3 — Error induction (parametric)

- **Error controls, per source:** coverage, snapshot age, and the seven error rates.
- **Denominator:** the two-level denominator (true elements in scope; scored attributes only). Context attributes are emitted but not scored.
- **Copy settings:** copy to the layer's other sources, or to all.
- **Overlap:** assets that appear in several sources, each copy with independent differences.
- **Record:** every corruption written to the truth manifest.

**Done when:** the realized error rates land within tolerance of the requested rates, and zero error reproduces the clean emission exactly.

### Phase 4 — Pilot runs

This phase connects the generator to the pipeline, runs the carried and flattened runs, and produces the Ch7 figures.

- **Dependency:** the pipeline stages (ingestion through the composed product) are separate work. The pilot needs a thin version of each. This phase is where the two tracks meet.
- **The informative answer key** (moved from Phase 2, ruled 2026-10-20): choose couplings to observe, at 1 unit each, to reduce uncertainty about the network, against the belief the pipeline produces. Its uncertainty measure is ruled on its own sheet first.
- **Done when:** the pilot spec's list is met:
  - at zero doubt, both runs return the same recommendation;
  - one hand trace matches the code;
  - the ledger walks one recommendation from each model back to its source records;
  - Figures 7.1, 7.2 and 7.4 are produced from real runs.

### Phase 5 — Real scale and realism

- **Realism ranges:** measure the per-layer reference statistics from the Ch6 corpus, and the real Taiwan-scale counts and area. This replaces the placeholders.
- **World checks:** the realism check runs against those ranges.
- **Size presets:** small, Taiwan-scale, very large.
- **Terrain:** all 11 map types; seismic zone and flood plain.
- **Dynamics:** the simulation tier. Fix the overlap band and the exact-tier instance bound.
- **Performance:** thousands of nodes per layer in minutes, not hours.

### Phase 6 — Source fidelity and richer error

- **Full real schemas:**
  - OSM PBF with real tag idioms;
  - WRI's CSV;
  - OurAirports' six linked tables;
  - World Port Index;
  - the others the mockup lists.
- **Power-plant correspondence:** match WRI, OpenInfraMap and OSM on real Taiwan data. This measures real overlap and disagreement, and it is the input to the replay mechanism. (It can start any time; it doesn't depend on Phases 1–5.)
- **Error mechanisms:** collection process, replay of measured error, fitted source model. Adversarial stays greyed out.

### Phase 7 — The interface

- **Build:** the mockup as a working front end that reads and writes recipes, with the side panel and the full recipe screen.
- **Actions:** Generate calls the engine. Review shows the printable map, the checks and the answer keys.
- **Framework:** decide at this point: a local web app (for example FastAPI with a small front end) or a Python-native one (for example Panel or Streamlit). Visual polish goes here.

### Phase 8 — Ensembles and documentation

- **Ensembles:** member count and which streams vary.
- **Documentation:** an ODD description of the generator, a TRACE record kept from Phase 1 onward (see §5), and one component docked against an independent minimal reimplementation.

## 4. The pilot path at a glance

| Phase | What the pilot gets from it |
|---|---|
| 1 | The 24-node world, its sources and its truth manifest |
| 2 | Answer keys for the defensive, offensive and restorative models (the informative key comes in Phase 4) |
| 3 | The doubt the carried run carries and the flattened run flattens |
| 4 | The runs, the figures and the run note |

Phases 1–3 need no corpus measurements and no anchors beyond placeholders. That's why they come first.

## 5. Working method

- **Tests from the start.** The five checks (identity, realism, realized error, spread, quiet planting) are written as automated tests as each stage lands. Each check is added in the phase whose stage it tests.
- **TRACE as you go.** Each phase closes with a short TRACE entry: what was built, how it was tested, and what changed from the design. This is much cheaper than writing it up at the end.
- **Recipe versions.** Any change to the recipe schema bumps its version, and old recipes either load or fail loudly.
- **Fixture worlds.** A handful of saved recipes (the pilot world, a hidden-layer world, a nodes-only world) rebuild on every change as a regression suite.
- **Design docs stay current.** Update the structure doc at each phase boundary, not per commit.

## 6. What is open against this plan

| Item | Needed by |
|---|---|
| Language, repository and schema decisions (§2) | Phase 1 |
| Design targets for drawn quantities, with citations | Phase 2 (placeholders until then) |
| Pipeline thin slice for each stage | Phase 4 |
| Seeds per cell | Phase 4 |
| Realism ranges and Taiwan-scale counts from the corpus | Phase 5 |
| Overlap band; exact-tier instance bound | Phase 5 |
| Magliocca consult | Alongside Phases 1–2, while the design is still cheap to change |
| Interface framework | Phase 7 |
