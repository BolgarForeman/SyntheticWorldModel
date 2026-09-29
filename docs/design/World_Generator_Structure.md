# World Generator — Structure

*v0.4 · 2026-09-28 · companion to the World Generator Interface mockup v0.5 and recipe schema v1 · supersedes v0.3*

## 1. What this is

The world generator builds constructed worlds for the dissertation's constructed arm. Each world is a complete six-layer interdependent infrastructure system on synthetic terrain, emitted as source files in the same structure the real ingestion reads, with a truth manifest beside it. Answer keys are computed on that world by a separate solver, one per model request (§5). It is the generator for the whole study, not for the pilot. The pilot is its first run at hand-check size.

This document states how the generator is organized: the rule that governs what it produces, the stages it runs in, what each stage takes and emits, how answer keys are produced against it, the checks that apply, and the decisions still open. It builds on `Synthetic_World_and_Degradation_Generator_Design_v0_7` and `Target_State_Constructed_World_Verification_v0_8`. Where it departs from them, §11 says so.

## 2. The governing rule: three kinds of quantity

Every quantity in a constructed world is one of three kinds.

| Kind | What it is | Examples | Where its doubt comes from in the analysis |
|---|---|---|---|
| **Observed** | Exists in the world and is emitted to one or more sources, with source error | Node locations, capacities, type tags, links on layers whose sources carry links | Source error, set per source in the generator |
| **Real but unobserved** | Exists in the world and is never emitted, because no real source carries it | Reserves (which set buffer time), node requirements, coupling strength, failure modes, repair rates, crews and depots, links on nodes-only layers, couplings themselves | The analysis's own assumptions and inference, set separately in the analysis |
| **Rules** | The world's own dynamics: how failure spreads, reserves draw down and repair proceeds | The declared dynamics composition and tier | The analysis's choice of dynamics, set separately; model error is the gap |

Five commitments follow.

1. **The world is complete.** Answer keys are optima computed on the true world, so the generator decides every quantity an optimizer needs about the world, observed or not.
2. **Only observed quantities are emitted, and they are emitted in the real structure.** The constructed route and the real ingestion route produce the same object; the truth manifest is the only permitted difference.
3. **Unobserved quantities are generated per element from context, separately from the analysis's assumptions** (§4.4). They are not a standard value with noise on it. An analysis that assumes a single standard value is right only where the world happens to match it.
4. **The generator never induces model error.** It runs its own declared dynamics. The analysis chooses its dynamics separately, and model error is measured as the gap between the two.
5. **Couplings carry no source error.** No real source reports them. Their doubt comes from how the pipeline infers them, which is why supplier siting (§4.3) is a generator control and coupling error is not.

**What belongs to the world and what belongs to the question.** Service weights, the objective, the action budget and the time window are not facts about the world. They are choices made by whoever poses the question. They live in the model request (§5), not in the generator, and every answer key is stamped with them.

## 3. Principles

- **The recipe is the record.** Every interface choice is written to a recipe file, including the list of answer-key requests. The recipe plus the root seed rebuilds the world exactly. The interface is a front end on the recipe, never the only record of what was chosen.
- **Machine-agnostic.** A small per-machine file says where source data lives. The same recipe runs on either machine and produces the same world.
- **Independent random streams.** One root seed, with a child stream spawned for each stage, each source and each drawn quantity, keyed by a stable name (never seeds built by arithmetic). A separate terrain seed enters the terrain streams only, so the ground can be rerolled on its own. The spawn tree is stored with the world, so changing the errors never moves the terrain, and paired runs hold the world fixed.
- **The same world on every machine.** The recipe and seeds give the same bytes on Windows and Linux. World-building arithmetic therefore avoids operations whose last digit differs between platforms (transcendental functions, library reductions), or quantizes their results.
- **Plant quietly.** Nothing planted may be recoverable by a simple shortcut: highest degree, largest capacity, nearest supplier. The check runs per answer-key request (§7).
- **Synthetic identifiers.** Real code-list formats with synthetic values from a reserved range. No real place codes, airport codes, port codes or wiki identifiers.
- **Synthetic centroid.** Every constructed world is anchored at Point Nemo, the Pacific pole of inaccessibility (about 48.88°S, 123.39°W). It is the ocean point farthest from any land, so no synthetic asset can fall on or be mistaken for a real place, and it signals plainly that the world is fictional.
- **Scale-free realism.** Realism is set by per-layer statistics (degree, spacing, links per node, concentration), not by absolute counts, so the same targets hold from the hand-check world to the continental one.

## 4. Stages, in build order

Each stage reads the recipe and the outputs of earlier stages, draws from its own stream, and writes its part of the true world.

### 4.1 Terrain

- **Map types (eleven):** spine island, archipelago, continent, coastal strip, river delta, twin islands, mainland with islands, peninsula, mountain basin, arid plateau, landlocked.
- **Terrain seed:** rerolls the ground alone (§3).
- **Character settings:**
  - mountainous;
  - forested;
  - river density;
  - coastline complexity;
  - lowland and wetland share;
  - aridity;
  - outlying islands;
  - urban density, with an urban pattern (one dominant city, several cities, dispersed towns).

  Each setting is an index from 0 (none) to 100 (the most the map type allows). The numeric mapping is fixed in the work order that builds the terrain stage.
- **Size.** Area and density set the node count: nodes = area × density, per layer. A hold switch decides what gives when the area changes: hold density (counts grow with the area) or hold counts (density falls as the area grows). Node counts and density can also be typed directly per layer (§4.2).
- **Size presets:**

| Preset | Area (km²) | Nodes per layer | Use |
|---|---|---|---|
| Hand-check | 400 | 4 | The pilot; traced by hand |
| Small | 2,000 | 20 | Brute-force answer keys; the overlap band |
| Taiwan-scale | 36,000 | 300 (placeholder) | The real arm's scale; counts to be measured from the Ch6 corpus |
| Very large | 250,000 | 2,000 | Simulation tier only |
| Huge (continental) | 8,000,000 | 50,000 | Scaling tests only |

- **Produces:** elevation, coastline, drainage, land cover, and urban extents used for siting.
- **Note:** urban extents drive where nodes are sited; they are not a population or demand field. Real sources carry no demand, so a demand field would give the constructed world something the real route lacks. Requirements live at the nodes (§4.4). A population field remains a Chapter 9 item.

### 4.1a Coordinates

- **Working projection:** WGS 84 / UTM zone 10S (EPSG:32710). Point Nemo lies almost on the zone's central meridian (123°W), so distortion is minimal for every size up to Taiwan scale. The generator's local metres are placed at a fixed offset from the centroid, so they are real projected coordinates.
- **Emitted sources:** WGS 84 latitude and longitude (EPSG:4326), in each source's own format, exactly as real sources carry them. Emitted coordinates are rounded to 7 decimal places (about 1 cm, the precision OpenStreetMap stores), so the transform gives the same bytes on every platform.
- **Truth manifest:** EPSG:32710 metres, with latitude and longitude alongside.
- **Analysis:** the pipeline takes the analysis projection per world: EPSG:32710 for constructed worlds, EPSG:3826 (TWD97 / TM2) for Taiwan. Both are metric Transverse Mercator, so the analysis code is the same.
- **Very large and huge presets** outgrow one UTM zone and use a custom Lambert azimuthal equal-area projection centred on Point Nemo (Phase 5).
- **Inspection export:** a GeoPackage (cities, nodes, links) and GeoTIFFs (elevation, land cover, rivers), each with its projection embedded, marked as synthetic in their metadata. ArcGIS Pro and QGIS open them directly; PostGIS loads them with ogr2ogr at SRID 32710. They sit outside the identity check, because their containers embed timestamps and database internals.

### 4.2 Layers and sources

- **Controls, per layer:**
  - state: emitted, hidden, or off;
  - node count and density, linked through the area;
  - links per node;
  - sources report nodes only (a toggle on any layer, not a property of fuel);
  - the sources switched on;
  - the share of assets appearing in more than one source.
- **Controls, global:** whether assets may belong to two layers (hydro dams, a hospital with its own substation).
- **Produces:**
  - nodes, sited by layer rules driven by terrain, urban extents and other layers, with node classes per layer;
  - intra-layer links, each layer keeping its own structural signature;
  - dual-membership assets.
- **Hidden state.** A hidden layer is in the world and every answer key but reaches no source. Its true contribution is known, so the bias from leaving it out is measured rather than cited. This implements generate-six-hide-one.
- **Overlap.** Assets that appear in more than one source are not conveniently aligned: each source's copy takes its own independent differences in the error stage, and only the truth manifest records which records are the same asset.

### 4.3 Couplings and causes

- **Coupling controls:**
  - the 6×6 matrix of which layer supplies which, switchable cell by cell, defaulting to the 21 modeled;
  - whether switched-off couplings are generated and hidden;
  - coupling density and two-way dependencies;
  - the share of consumers whose true supplier is not the nearest one (quiet planting against the nearest-supplier shortcut);
  - **dependency concentration:** how many consumers draw on the same few suppliers, from spread evenly to concentrated on a few. It is a shape setting, not a count; the number of heavily shared suppliers follows from it and the layer sizes;
  - **feed configuration mix:** single feed, two full feeds (either covers the need), two half feeds (both needed). The three shares are coupled and always total 100%; moving one redistributes the other two in proportion.
- **Per dependency type:** the transfer form, from the four canon forms: linear, concave, threshold (the cliff), step. Defaults: physical flow linear, logistic threshold, control step, service linear. Concave arrives with the simulation tier; an exact-tier world that uses it is refused at build. Where a node has several inbound dependencies, the combining function is the typed weakest link.
- **Index meanings:** coupling density runs from 0 (each consumer has the minimum one supplier per coupled layer) to 100 (the most the matrix allows); concentration from 0 (supply spread evenly) to 100 (one supplier per layer carries every consumer).
- **Shared causes:** hazard fields (storm corridor, seismic zone, flood plain), each switchable with its own correlation length and its own severity (0 = no damage; 100 = every exposed element in the hazard core fails); the number of scenarios.
- **Produces:** cross-layer edges, each with its supplier, commodity, dependency type, feed configuration and transfer form; a latent field per active hazard with distance-decay correlation; the scenario set, with element failures drawn conditionally on the fields.
- **Note:** redundancy is planted as a configuration and recorded per edge, never as a total. Two full feeds and four half feeds carry the same total supply and fail differently.

### 4.4 What sources don't show

These are the real-but-unobserved quantities. They split into two groups by how they are made.

**Derived.** Computed from the world already built, never drawn on their own:

| Quantity | How it is derived |
|---|---|
| Coupling strength | Capacity of the supplying node and the line to the consumer, divided by the consumer's requirement. A consumer on a direct transmission line may have three times its need; one at the end of a long rural feeder may have barely enough |

**Buffer time is not a separate quantity.** It is the reserve expressed in hours: the reserve divided by the draw on it. The generator draws the reserve only. Buffer time is computed during the run, because the draw can change during an event (load shedding, conservation, a second feed carrying part of the load), and a fixed buffer time would miss that.

**Drawn per element from context.** Each element gets its own value, drawn from a distribution whose centre depends on that element's situation:

| Quantity | Context it depends on (examples) |
|---|---|
| Reserves | Node class, criticality of what it serves, remoteness, hazard exposure |
| Node requirements per commodity | Node class and size |
| Repair rates | Distance to the nearest depot, terrain, node class |
| Failure mode (throttle or trip) | Equipment class, dependency type |
| Crews and depots | Counts set in the interface; sited by urban extents and access |
| Links on node-only layers | The layer's structural signature and siting rules |

Each drawn quantity has:

- **a design target:** what the governing standard or code requires for that class of element (a hospital's required backup fuel hours, a pump station's required storage). The target is the anchor, and each needs a citation (§10, item 1);
- **context factors:** how the target shifts with the element's situation;
- **two levers:**
  - *heterogeneity (percent):* the spread of element values around their context-adjusted target, as a percentage of the target. At 0 every element sits on its target; at 100 the spread equals the target itself;
  - *compliance gap (percent, −50 to 100):* the mean departure from target as a percentage of the target. Positive is shortfall; negative means elements exceed their target.

Two drawn quantities are categorical or structural and read the levers differently. For failure mode, heterogeneity is the share of elements whose mode departs from their dependency type's canon default. For links on nodes-only layers, it is the share of links that depart from the shortest road route. The compliance gap does not apply to either.

At zero heterogeneity and zero compliance gap, every element sits exactly on its design target, and an analysis that assumes the standard is right for free, and the world flatters it. Both levers are recorded per quantity in the truth manifest.

### 4.5 Dynamics and difficulty

- **Tier:** exact, simulation, or both. The exact tier is restricted to forms that admit a provable optimum, declared as a simplification. Both runs worlds sized to fit both tiers (the overlap band), so the two can be compared directly.
- **No time window here.** The world's dynamics are defined for any horizon; the window over which an objective is scored belongs to the request (§5).
- **Difficulty readout:** computed from the world alone (feed mix, concentration, hazard severity, coupling density), never set by hand. There is no installed-redundancy total: redundancy is planted as configuration (§4.3). How the score is measured is open (§10, item 3).
- **Produces:** the world's declared dynamics composition.

### 4.6 Emission

- **Produces:** one set of files per source switched on, for emitted layers only, in the source's real container, schema and idioms.
  - On node-only layers, links are withheld.
  - Hidden layers and switched-off couplings are withheld.
  - Overlapping assets appear in each of their sources.
  - All attributes the real source carries are emitted, scored or not (§4.7).
  - The true correspondence across sources is written to the truth manifest.

### 4.7 Error induction

- **Controls, per source:**
  - coverage (0–100%);
  - snapshot age (0–30 years);
  - rates for phantom, missing and merged assets, location, attributes, links within the layer (unless node-only), and type and tag labels;
  - copy to the layer's other sources or to all;
  - the mechanism: parametric noise, collection process, replay of measured error, or fitted source model, set per source with a recipe-wide default. An adversarial mechanism is carried in the schema and always refused at build.
- **Denominator, two levels:**
  - *elements:* all true elements in the source's scope. A 5% missing rate means 5% of the true assets that source should carry are absent;
  - *attributes:* only the decision-relevant attributes count. Each layer marks which attributes are **scored** (location, capacity, type, voltage class and similar) and which are **context** (the long tail of tags a source such as OpenStreetMap carries). Context attributes are emitted and may be corrupted, but they are not counted in the rate and not scored. A 5% attribute error rate means 5% of scored attribute values are wrong.
- **Produces:** the corrupted source files and a record of every corruption.
- **Scope:** only observed quantities carry error here.

The denominator no longer depends on any model. It is fixed by the world and the source's scope, so rates stay comparable across sources, settings and answer-key requests.

### 4.8 Truth manifest

- **Produces:**
  - every planted error, with target, observability, source and mechanism;
  - every unobserved value, with its design target, context factors, heterogeneity and compliance gap;
  - every hidden layer and hidden coupling;
  - the cross-source correspondence;
  - the scored and context attribute lists per layer;
  - the dynamics composition;
  - the seeds and spawn tree.

### 4.9 Ensembles (later)

- **Controls:** member count; which streams vary between members (terrain, infrastructure, unobserved quantities, errors).
- **Produces:** a set of worlds from one recipe.

## 5. Answer keys: a separate solver

The generator builds the world. The answer-key solver asks questions of it. They are separate because one world must serve every optimization model: defending, attacking, restoring and choosing what to observe, each with its own objective.

**A model request** names:

| Field | Examples |
|---|---|
| Member-class | Defensive, offensive, restorative, informative |
| Model | The specific model within the class |
| Objective | Unserved demand-hours; time to restore 80%; worst single layer |
| Service weights | How much an hour of outage counts at each end-use class |
| Budget | The model's own parameter: cost units for protection, nodes struck for attack, couplings observed for observation. Sequencing repair crews takes none; crews come from the world |
| Window | The horizon the objective is scored over (default 72 hours) |

A recipe carries any number of requests. Each is solved on the true world.

**What unserved demand-hours counts.** The objective is weighted service-hours at end-use nodes: for each end-use node, the hours it is out of service, counted as a fraction when supply is partial, times its class weight, summed over the window. Units cannot be mixed across layers (megawatts, cubic metres, calls, litres), so demand is not multiplied in; a size factor may be added to the weights later. Only end-use nodes are scored. Every other node matters through what it feeds, and counting it too would count one outage twice.

**End-use classes and the service-weight presets.** A weight measures the consequence of an hour of outage, not how likely the node is to fail; redundancy is already in the world, and weighting for it would count it twice.

| End-use class | Lifeline (default) | Equal |
|---|---|---|
| Tertiary hospital | 10 | 1 |
| Regional hospital | 7 | 1 |
| Seaport | 7 | 1 |
| Blood bank | 6 | 1 |
| Airport | 6 | 1 |
| Power distribution substation | 5 | 1 |
| Water storage | 5 | 1 |
| Fuel depot | 4 | 1 |
| Freight yard (truck warehouse and yard) | 4 | 1 |
| Clinic | 3 | 1 |
| Telecom mast | 1 | 1 |

A third preset, **Custom**, sets any class to any weight from 0 to 100. The end-use categories follow FEMA's Community Lifelines (health and medical, energy, communications, transportation, food and water); the numbers are the author's judgment and are stated as such. Running the same world under Lifeline and Equal is a planned sensitivity test: if the carried run's advantage holds under both, the result does not rest on the weights.

**Each answer key produces:**

- the optimum;
- the margin to the second-best answer;
- the acceptability threshold;
- true criticality under that request's objective and weights;
- the shortcut test result (§7);
- the decision-relevant dose: how much of the planted error touches elements that matter to this request's answer.

**The stamp.** Every answer key is stamped "assumes:" followed by the class, model, objective, service weights, budget and window it was solved under, and the SHA-256 of the resolved recipe. A key is only valid against a result that was posed the same way. Swapping models means adding a request, not rebuilding the world.

## 6. Outputs

| Output | Contents |
|---|---|
| True world | Everything that exists, observed and unobserved |
| Truth manifest | §4.8 |
| Source files | One set per source switched on, in its real structure |
| Answer keys | One per request, stamped with its assumptions (§5) |
| Printable map and tables | For tracing a scenario by hand at hand-check size |
| Recipe file | Every choice, the answer-key requests, the root seed and the spawn tree |

## 7. Checks

**World checks** — every world must pass:

1. **Identity.** The world re-emits identically from the recipe and root seed.
2. **Realism.** Each layer falls inside reference ranges measured from the Taiwan data, such as degree, spacing, links per node and concentration.
3. **Realized error.** Measured error rates fall within a stated tolerance of the requested rates, against the two-level denominator.

**Request checks** — every answer key must pass:

4. **Uniqueness.** The optimum is unique, with the second-best answer worse by a stated margin.
5. **Quiet planting.** Simple shortcuts do not recover the optimum: highest degree, largest capacity, nearest supplier.

A world or key that fails a check is reported, not silently regenerated.

## 8. Documentation

The generator is described in the ODD protocol (overview, design concepts, details), with data pedigree under Initialization and Input data. Its development and testing record is kept in TRACE form. One component is docked against an independent minimal reimplementation at a declared level of equivalence.

## 9. Interface

The mockup (v0.5) runs the stages as nine steps (Terrain; Layers and sources; Couplings and causes; What sources don't show; Dynamics and difficulty; Error induction; Ensembles; Generate and review; Answer keys), with a recipe-at-a-glance side panel and a full recipe screen (readable and file views). Every control carries an info note on hover. The interface is built last, as a front end that reads and writes recipes; the recipe schema (v1) is the contract. Visual polish is deferred. The mockup predates several v0.3 rulings (time window on the request, severity per hazard, no redundancy total, the weight presets) and will be brought into line when the interface is built.

## 10. Open decisions

| # | Decision | Why it matters |
|---|---|---|
| 1 | The design target anchoring each drawn quantity, with citations | Heterogeneity and compliance gap are measured from the target |
| 2 | The form of each context factor and the distributions behind the two levers | Sets what "drawn from context" means numerically |
| 3 | The difficulty measure behind the readout | The readout is a placeholder; the sweep literature points to a measured transition |
| 4 | Reference statistics and ranges for the realism check, per layer, and the Taiwan-scale counts and area | Must be measured from the Ch6 corpus before the first full-size world |
| 5 | Size of the overlap band | Cannot be retrofitted once the sweeps are sized |
| 6 | The instance bound for the exact tier against the larger model set | Sets the ceiling on brute-force answer keys |
| 7 | The buffer typology ruling | Decides whether every buffer is a stock (fuel, stored water, battery charge) or whether some are tolerance with no stock behind it (a hospital working on paper while telecom is down). A tolerance buffer would need its own drawn quantity |
| 8 | Seeds per cell | Sets run counts for every sweep |
| 9 | The Magliocca consult on generator design, run alongside the build | Generator design is his field |
| 10 | A size factor in the service weights | Weighted node-hours count a large and a small substation the same; a size factor would fix that without mixing units |

The UA Research Security export ask carried over from an earlier problem set and is not in scope (ruled 2026-09-28). The language (Python) and code location (the SyntheticWorldModel repository) are decided; see its decision records 0001–0003.

## 11. Departures from the generator design (v0.7)

- **Population and demand field removed.** Requirements are declared at the nodes. Siting is driven by terrain, urban extents and other layers.
- **Node-only is a per-layer toggle,** not a property of fuel. It means sources report nodes only; the links still exist in the truth.
- **Coupling error removed from error induction.** It moved to the analysis side as inference doubt.
- **Model error removed from the generator.** It is measured as the gap between the world's declared dynamics and the analysis's chosen dynamics.
- **Unobserved quantities made explicit** as derived or drawn from context, with design targets and two levers. This extends the design's two-composition requirement from the dynamics to every unobserved value.
- **Answer keys split from the generator.** Objective, service weights and budget move to the model request; each key is stamped with them.
- **Denominator made model-independent:** all true elements in scope, scored attributes only.
- **Hidden state added for layers.** This implements generate-six-hide-one as a control.
- **Supplier siting, dependency concentration and the coupled feed mix added** as coupling controls. Concentration replaces the hub count.
- **Size set by area and density,** with a hold switch and presets from hand-check to continental.

## Changes from v0.3

- Freight yard added as a transport end-use class, Lifeline weight 4; bridges are transport nodes but not end uses (§5).
- OpenStreetMap is the backbone source on every layer; specialised sources (WRI, OurAirports, World Port Index, facility register) cross it and carry only the classes they really contain. OpenInfraMap derives from OpenStreetMap and its errors are correlated with it.
- Coordinates settled (§3, new §4.1a): Point Nemo as the synthetic centroid; EPSG:32710 as the working projection; WGS 84 latitude and longitude in emitted sources, rounded to 7 decimals; per-world analysis projection; GeoPackage and GeoTIFF inspection export. Ruled by the author, 2026-09-28. Open decision on the coordinate anchor closed.

## Changes from v0.2

All from the Work Order 1 rulings and the service-weight rulings of 2026-09-28 (repository decision records 0002 and 0003):

- Terrain seed added; it enters the terrain streams only (§3, §4.1).
- Cross-platform byte identity stated as a principle (§3).
- Map types and urban patterns now follow the mockup's lists (§4.1).
- Per-dependency-type controls reduced to the transfer form, with defaults; concave refused on the exact tier until Phase 5 (§4.3).
- Hazard severity set per hazard; the 0–100 index meanings anchored (§4.1, §4.3).
- Heterogeneity defined as a percent spread; compliance gap signed, −50 to 100; categorical cases stated (§4.4).
- The time window moved from the world to the request; the installed-redundancy total dropped (§4.5, §5).
- Error mechanism per source with a recipe-wide default; coverage and snapshot-age ranges widened (§4.7).
- Budget typed per model (§5).
- The objective defined as weighted service-hours at end-use nodes; Lifeline, Equal and Custom weight presets replace "healthcare first" (§5).
- Answer keys also stamped with the window and the recipe hash (§5).
- Open decisions: language and code location closed; synthetic coordinate anchor and a weight size factor added (§10).

## Changes from v0.1

- Answer-key solver made a separate stage (§5); service weights, objective and budget moved to the model request.
- §4.4 rewritten: derived vs drawn per element from context, with design targets and the heterogeneity and compliance-gap levers. "Departure setting" retired.
- Two-level denominator with scored and context attributes (§4.7).
- Area × density sizing with the hold switch and five presets (§4.1).
- New map types and character settings, including urban density and pattern.
- Dependency concentration replaces shared upstream hubs; feed mix coupled to 100%.
- Canon four transfer forms named; typed weakest link as the default combination.
- Adversarial mechanism shown greyed.
- Checks split into world checks and request checks.
- Buffer time folded into reserves: the reserve is drawn, buffer time is computed in the run.
- Export ask removed from open decisions; buffer typology, instance bound and seeds per cell added.
