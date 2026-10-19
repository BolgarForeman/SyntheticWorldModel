# World Generator — Structure

*v0.13 · 2026-10-19 · companion to the World Generator Interface mockup v0.5 and recipe schema v3 · supersedes v0.12*

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
- **Emitted sources:** WGS 84 latitude and longitude (EPSG:4326), in each source's own format, exactly as real sources carry them. Each source is written at the precision its real file carries, so the transform gives the same bytes on every platform and the clean emission looks like the real source: OpenStreetMap at 7 decimal places (about 1 cm, the precision it stores); WRI at 4 (about 11 m); OurAirports and the facility register at the precision measured from the real files and recorded beside each header. The rounding is part of the clean emission, not error: the realized-error check (§7) measures planted error against the clean, rounded file, never against the true location. (Ruled 2026-10-10, PR 17 answers.)
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
- **Mapped power lines** (ruled 2026-10-02, decision 0013). Power lines are elements in their own right, as OpenStreetMap maps them (power=line), not straight links:
  - **What they join.** Mapped lines join plants and substations of any class: plant to transmission substation, plant to distribution substation, substation to substation. A facility in another layer never draws from a plant or a line directly; it draws from a substation (§4.3a).
  - **Route.** Each line follows a least-cost path over the terrain. Steep slope, high ground and river crossings cost more, the sea cannot be crossed, so lines follow valleys and go around mountains unless the detour costs more than the crossing. A line that crosses the spine is recorded as a ridge crossing. The cost weights are registry placeholders (J).
  - **Attributes.** Voltage class (161 kV from a plant and between substations; 69 or 161 kV to a distribution substation), circuits, and structure: towers for every mapped line, with tower points along the route at a placeholder spacing (J).
  - **Below the distribution substations nothing is mapped.** The feeds to facilities exist in the true world and run along the road network (distribution lines follow roads), on poles; they are never emitted. The analyst must infer them.
  - **Other layers.** Water mains, fuel pipelines and telecom fibre stay straight logical links in Phase 1; they may be routed later if the data supports it, or remain inferred.
  - This replaces Work Order 3's "straight segments in Phase 1, terrain routes in Phase 5" for power lines only.
- **Capacities hang together.** Total generation capacity is total distribution capacity times a reserve margin, and a transmission substation carries at least what it feeds (placeholders: margin 1.3, power factor 0.9).
- **Hidden state.** A hidden layer is in the world and every answer key but reaches no source. Its true contribution is known, so the bias from leaving it out is measured rather than cited. This implements generate-six-hide-one.
- **Overlap.** Assets that appear in more than one source are not conveniently aligned: each source's copy takes its own independent differences in the error stage, and only the truth manifest records which records are the same asset.

### 4.3 Couplings and causes

- **Coupling controls:**
  - the 6×6 matrix of which layer supplies which, switchable cell by cell, defaulting to the 21 modeled;
  - whether switched-off couplings are generated and hidden;
  - **coupling density**, 0–100. At 0, each consumer takes only its core dependencies (§4.3a). At 100, it takes every dependency the table allows;
  - **two-way dependency**, 0–100: the share of possible mutual node pairs that are built. A mutual pair is two nodes that each depend on the other, such as a substation feeding an exchange that controls it. At 0 there are none; at 100, every mutual pair the table allows;
  - the share of consumers whose true supplier is not the nearest one (quiet planting against the nearest-supplier shortcut);
  - **dependency concentration**, 0–100: how strongly consumers are pulled toward one hub supplier per coupling. At 0 each consumer takes its nearest eligible supplier, with no pull toward a hub. At 100 the hub carries every consumer it is eligible for. When concentration and supplier-not-nearest conflict, concentration wins and a note records it;
  - **feed configuration mix:** single feed, two full feeds (either covers the need), two half feeds (both needed). The three shares are coupled and always total 100%; moving one redistributes the other two in proportion;
  - **public telecom share** for control dependencies on power, water and pipelines (§4.3a, rule 1).
- **Per dependency type:** the transfer form, from the four canon forms: linear, concave, threshold (the cliff), step. Defaults: physical flow linear, logistic threshold, control step, service linear. Concave arrives with the simulation tier; an exact-tier world that uses it is refused at build. Where a node has several inbound dependencies, the combining function is the typed weakest link.
- **Shared causes:** hazard fields (storm corridor, seismic zone, flood plain), each switchable with its own correlation length and its own severity; the number of scenarios. The storm corridor is specified in §4.3b. Severity is anchored to Taiwan's typhoon classes (§4.3b); the seismic zone and flood plain stay switched off and unbuilt in Phase 1.
- **Produces:** cross-layer edges, each with its supplier, commodity, dependency type, role, feed configuration and transfer form; a latent field per active hazard with distance-decay correlation; the scenario set, with element damage drawn conditionally on the fields (§4.3b).
- **Note:** redundancy is planted as a configuration and recorded per edge, never as a total. Two full feeds and four half feeds carry the same total supply and fail differently.

### 4.3a The dependency table

The table below says, for every one of the 21 couplings, which consumer node classes depend on the supplier layer, on which supplier classes, and how. It is the core truth of every constructed world. It was built from sources by five research lanes and checked by an independent reviewer. Every row's source, quote and evidence grade is in `evidence/Dependency_Table_Evidence_v0_1.md`, and the author's rulings are in decision record 0007. Grades:
- **S**: a standard or regulation (US standards are marked US where they stand in for Taiwan practice);
- **L**: literature or a government report;
- **J**: judgment.

Every row is a CHOICE-level placeholder until the realism ranges are measured (§10, item 4).

**Rules that apply across the table.**

1. **Public telecom share.** Control dependencies of power, water and pipeline facilities (fuel tank farms and import terminals) ride partly on the utility's own private network and partly on the public telecom layer. Each such edge carries a public share (0–100%), drawn from a recipe setting per consumer layer. Only the public share is exposed to the telecom layer. Defaults (placeholder): generation and transmission 20%, distribution 50%, water and pipelines 50%. Source: DOE (2023); Taipower's more than 10,000 km of company fibre (台電月刊 Vol. 700).
2. **Buffer resupply.** Fuel edges to backup-generator consumers have the role `buffer_resupply`. They do nothing while the consumer's power supply is up. When it is lost, they extend the generator's runtime; they never fail the consumer on their own. All other edges have the role `primary_supply`. This is Appendix B's "the buffer has a buffer".
3. **Road reachability.** Transport edges run from origins (seaport, airport, freight yard) of the eligible kinds. A consumer is supplied if any eligible origin reaches it over the road network, so its transport dependency lists every such origin with feed configuration `any_reachable`. Roads carry; they are not suppliers. A depot's function is delivered fuel, so the depot's road leg plus the fuel edge from the depot carries trucked delivery to backup consumers. The excluded couplings transport → telecom and transport → water stay excluded.
4. **Large loads.** A consumer whose load exceeds a threshold (placeholder) is supplied from a transmission substation. Any substation can supply any power consumer, since every substation can step down (ruled 2026-10-02, decision 0013): smaller consumers take the nearest eligible substation of either class, subject to the concentration and supplier-not-nearest controls.
5. **Tertiary second feed.** A tertiary hospital takes a second distribution substation with a recipe probability (placeholder 50%). It is not a rule for the class.
6. **Water storage** consumes nothing. Its volume is the buffer on downstream water edges.
7. **Phase 1 transport nodes.** Bridges, road junctions and rail nodes consume nothing in Phase 1. There is no rail in Phase 1.
8. **Out of scope in Phase 1:** staff access to hospitals over roads (a service dependency; later it rides rule 3).

**Subtype attributes.** Some rows depend on what kind of node it is. These are generated with the node (layers stage), as real-but-unobserved truth unless a source carries them:

| Class | Attribute | Values |
|---|---|---|
| Generation | fuel_kind | lng, oil, coal, hydro |
| Generation | makeup_water | municipal, own_intake |
| Import terminal | product | oil, lng, coal |
| Airport | towered; fuel_receipt | yes/no; pipeline, truck |
| Data centre | cooling | evaporative (default, per Appendix B), dry |
| Refinery | crude_receipt | marine, pipeline |
| Tank farm | pipeline_connected; has_jetty; has_truck_rack | yes/no each |
| Healthcare | records_hosted | yes/no |
| Backup consumers | standby_fuel | diesel, none |

**The table.** Key:
- **Dep.:** C core, O optional, — none.
- **Type:** PF physical flow, L logistic, Ctl control, Svc service.
- **Role:** P primary supply, B buffer resupply.

*power → (electricity, PF, P)*

| Consumer | Dep. | Suppliers | Grade |
|---|---|---|---|
| exchange, mast, cable_landing | C | distribution substation | L (J for cable landing) |
| data_centre | C | distribution; transmission if large | L |
| treatment | C | distribution; transmission if large | S (US) |
| pumping | C | distribution | S (US) |
| reservoir, storage | — | | J |
| seaport | C | distribution; transmission if large | L |
| airport | C | distribution | S (US) |
| freight_yard | O | distribution | J |
| refinery | C | transmission | L |
| tank_farm, depot | C | distribution | L |
| import_terminal | C | distribution (oil, coal); transmission (lng) | L |
| tertiary | C | distribution (second feed by rule 5) | S (US) |
| regional, clinic, blood_bank | C | distribution | S (US) / L |

*telecom → (communications, P)*

| Consumer | Dep. | Type | Suppliers | Grade |
|---|---|---|---|---|
| generation, distribution substation | C | Ctl (rule 1) | exchange; mast | L |
| transmission substation | C | Ctl (rule 1) | exchange | L |
| treatment, pumping | C | Ctl (rule 1) | exchange; mast | L |
| reservoir | O | Ctl (rule 1) | mast; exchange | J |
| storage | — | | | J |
| airport, towered | C | Ctl | exchange | L |
| airport, not towered | O | Svc | exchange; mast | J |
| seaport, freight_yard | C | Svc | exchange; mast; data_centre | L / J |
| refinery | C | Svc | exchange | J |
| depot | C | Svc | exchange; mast; data_centre | J |
| tank_farm, pipeline-connected | C | Ctl (rule 1) | exchange; mast | S (US) |
| tank_farm, not connected | O | Svc | exchange; mast | J |
| import_terminal | C | Ctl (rule 1) | exchange; mast | S (US) |
| tertiary, regional, clinic | C | Svc (tolerance buffer, §4.4a) | exchange; mast; data_centre | L / J |
| blood_bank | C | Svc (tolerance buffer, §4.4a) | exchange; data_centre | J |

cable_landing supplies no consumer directly. It feeds the exchange and data centre within telecom.

*water → (water, PF, P)*

| Consumer | Dep. | Suppliers | Grade |
|---|---|---|---|
| generation (fuel-fired, municipal make-up) | C | storage; pumping; reservoir as raw water if inland | L / J (Taiwan) |
| generation (own intake) or hydro | — | | L |
| substations, exchange, mast, cable_landing | — | | J |
| data_centre (evaporative) | C | storage; pumping | L |
| refinery | C | storage; pumping; reservoir (raw) | L |
| tank_farm, import_terminal, depot | O | storage; pumping | J |
| tertiary, regional, clinic | C | storage; pumping | S (US) / L |
| blood_bank | O | storage; pumping | J |

*transport → (transport access, L, P, rule 3)*

| Consumer | Dep. | Origins | Grade |
|---|---|---|---|
| import_terminal | C | seaport | L |
| refinery (marine crude) | C | seaport | L |
| refinery (pipeline crude) | — | | J |
| tank_farm (jetty or truck rack) | O | seaport (jetty); freight_yard (rack) | L |
| depot | C | freight_yard; seaport if on an outlying island | L |
| tertiary, regional | C | freight_yard; seaport; airport | L |
| clinic | C | freight_yard | L / J |
| blood_bank | C | freight_yard; airport | L |

The airport supplies no fuel class.

*fuel → (fuel)*

| Consumer | Dep. | Type | Role | Suppliers | Grade |
|---|---|---|---|---|---|
| generation, lng | C | PF | P | import_terminal (lng) | L |
| generation, oil | C | PF | P | tank_farm; refinery | J |
| generation, coal | C | L | P | import_terminal (coal) | L |
| generation, hydro; substations | — | | | | J |
| exchange, data_centre | C | L | B | depot; tank_farm | L / J |
| cable_landing | C | L | B | depot | J |
| mast | O | L | B | depot | L |
| treatment | C | L | B | depot; tank_farm | S (US) |
| pumping | O | L | B | depot | L |
| reservoir, storage | — | | | | J |
| seaport | C | L | P | tank_farm; import_terminal (oil); refinery; depot | L |
| airport, pipeline receipt | C | PF | P | refinery; tank_farm; import_terminal (oil) | L |
| airport, truck receipt | C | L | P | depot | L |
| freight_yard | C | L | P | depot; tank_farm | L |
| tertiary | C | L | B | depot; tank_farm | S (US) |
| regional | C | L | B | depot | S (US) |
| clinic | O | L | B | depot | J |
| blood_bank | C | L | B | depot | L |

An LNG or coal import terminal never supplies bunkers, jet fuel or diesel.

### 4.3b Shared causes: the storm

Ruled by the author, 2026-09-30 (decision 0012). Evidence: `evidence/Hazards_Evidence_v0_1.md`, three research lanes and an independent review (23 load-bearing claims: 15 confirmed, 6 overstated, 2 unreachable, none wrong). Ruling sheet: `evidence/Hazards_Ruling_Sheet_v0_1.md`. Every value is placeholder-grade until the realism ranges are measured (§10, item 4).

**What the storm damages.** Real typhoon outages come mostly from poles and overhead lines, and from facilities losing grid power or telecom backhaul, not from damaged facilities (Faxai 2019: about 2,000 poles broken and no mast collapsed from wind; Hurricane Ian 2022: 2.3% of cell sites out were physically damaged; Hazus Hurricane has no wind model for lifelines). So:
- **Overhead power lines** fail by wind: the power layer's links, and the power feeds from a substation to its consumers.
- **Aerial telecom links** fail by wind with the same pole-line fragility, since aerial fibre rides the same poles · J.
- **Facilities** fail by flood only. None fails from wind in Phase 1.
- **Not damaged in Phase 1:** buried water mains, roads and bridges. Roads stay open; road blockage and bridge scour come later (declared restriction).

**The wind field.** A typhoon moves on a straight track that passes over or near the island: each scenario draws its closest approach to the island's centre between 0 and 40 km offshore, and its radius of maximum wind between 20 and 60 km (geometric mean in the literature 47.5 km, Willoughby & Rahn 2004) · J for both ranges (2026-10-02, PR 6a answers). Each place takes the peak wind over the storm's passage. Wind is a 10-minute sustained speed in m/s, as Taiwan's Central Weather Administration (CWA) reports it. At each place it is built in order:
1. **Profile.** Modified Rankine: inside the radius of maximum wind, speed rises linearly to the peak; beyond it, V = V_max × sqrt(R_max ÷ r). Exponent 0.5, literature range 0.4–0.6 (Geoscience Australia TCRM) · L.
2. **Sea to land.** Land keeps 0.83 of the sea wind, most of the drop within 1 km of the coast (Vickery et al. 2009) · L (US).
3. **Local surface.** Taiwan building wind code terrain classes: 0.476 of open-ground wind in a city core (the largest city), 0.662 in a town or wooded land, 1.0 in the open, on wetland or bare ground, or on the coast · S (TW) for the factors, J for their use in a hazard field.
4. **Mountain lee.** Places in the lee of the spine keep 0.6. The lee is measured against the smooth spine line (decision 0005), not the crest cells: a place is in the lee when the spine line lies between it and the nearest point of the track. A flat island (mountainous 0) has no lee. Factor 0.6 · J, bounded by the >40% weakening of typhoons crossing the Central Mountain Range (Brand & Blelloch, as quoted in Wu & Kuo 1999; whether wind or pressure is unconfirmed).
5. **Random variation.** A smooth random field from a Wendland kernel, (1 − t)⁴(1 + 4t), valid in 2-D (Bevilacqua et al. 2019), with normal values built from uniform draws. Correlation length 10 km, spread 10% · J (placeholders).

For line fragility the 10-minute wind converts to a 3-second gust: ×1.66 inland, ×1.38 at the coast (Harper, Kepert & Ginger 2010, WMO guidelines, Table 1.1: "in-land" and "off-sea") · L. Corrected 2026-10-02 from 1.75 and 1.30, which mixed averaging conventions (PR 6b answers).

**Severity.** 0 means no storm. Otherwise the peak 10-minute wind at sea is V_max = 17.2 + 0.53 × severity m/s, so mild typhoons (17.2–32.6 m/s) fall at 1–29, moderate (32.7–50.9) at 29–64 and strong (≥ 51) at 64–100, topping out near 70 m/s. The CWA classes are S (TW); the linear map is J. Severity also sets 24-hour rainfall on the Water Resources Agency flood-map ladder: 300 mm up to 33, 450 mm up to 66, 600 mm above. Each scenario draws its rainfall within ±75 mm of its rung (moderate: 375–525 mm), and the flood stage follows linearly at 1 m per 150 mm above 150 mm · J (2026-10-02). **Pilot: severity 50**, a moderate typhoon near 44 m/s at sea, with 450 mm.

**Flood.**
- Flood depth at a facility = the scenario's flood stage − the site's height above the nearest drainage, the standard single flood index (Nobre 2011) · L.
- Flood stage: 1 m at 300 mm, 2 m at 450 mm, 3 m at 600 mm · J (placeholders; next source: the NCDR flood map handbook).
- A facility floods out at its Hazus functional depth (Hazus 6.1 Inventory Technical Manual) · L (US):
  - substations, power plants, water treatment and pumping, and refineries: 1.2 m (4 ft), measured from the platform for power plants and transmission substations, which stand on platforms raised 2 m above grade (real plants are built above the design flood; Hazus assumes slab on grade) · J for the platform (2026-10-02);
  - import terminals: 1.2 m (raised quays) · J;
  - tank farms and depots: any water;
  - hospitals, clinics and blood banks: 0.15 m (0.5 ft), measured from grade;
  - telecom facilities: 1.2 m, borrowing the substation value (Hazus maps them without a damage rule) · J;
  - water storage: on-ground tanks 7.3 m (24 ft);
  - reservoirs, ports, airports, freight yards, bridges, road junctions and rail nodes: not flood-damaged in Phase 1.
- Damage state by depth over the threshold: up to 0.5 m slight; above 0.5 m moderate; above 1.5 m extensive; above 3 m complete · J. The pilot caps facility damage at moderate (§4.4a).

**Routes and ridges** (ruled 2026-10-02, decision 0013; corrected 2026-10-03, PR 14 answers). Every line reads the wind along its true route: mapped lines along their terrain route, feeds along their road route. On isolated hills, ridges and escarpments the wind is raised by Taiwan's building wind code topographic factor, Kzt = (1 + K1·K2·K3)² (建築物耐風設計規範與解說 §2.6, Formula 2.8; K1 from the feature's steepness by Table 2.3(a), K2 and K3 the horizontal and vertical decay by Tables 2.3(b) and (c)), applied where the code's conditions hold (two separate tests: the feature stands more than twice the terrain within 3.22 km upwind; and nothing of similar height lies within 100H or 3.22 km upwind, whichever is less (as H is measured from the lowest ground upwind, the second test never fails without the first; kept as the code writes it, ruled 2026-10-09); and further H/Lh ≥ 0.2, and the point is on the feature's upper half). Kzt multiplies wind pressure, so wind speed is multiplied by √Kzt = 1 + K1·K2·K3 · S (TW) for the factor, J for its use on power lines. K3 needs exp, so its values come from the code's own table.
- **The storm's own direction.** The code designs for the worst wind direction; a simulated storm has one. Each place reads the factor for the wind direction it sees at its peak: along the track's direction of travel to the right of the track and against it to the left (Northern Hemisphere, counterclockwise rotation, as every storm rule is taken from Taiwan), snapped to the nearest of the 8 grid directions. A place within the radius of maximum wind meets the eyewall from both sides and takes the worse of the two. The inflow angle is neglected · J.
- **Ceiling on the speed-up** (ruled 2026-10-09, PR 14 second answers). The code's factor is a design envelope for isolated hills; on every crest of a spine it overshoots (the uncapped factor gave the pilot a 135.7 m/s gust). The factor applied to the wind is therefore min(1 + K1·K2·K3, ceiling). The ceiling is calibrated so the pilot's highest gust at pole height, over its 8 scenarios, equals Taiwan's highest measured gust: 95.2 m/s at the Lanyu weather station in Typhoon Koinu (2023), a moderate typhoon by the weather agency's class, the pilot's class · L for the record, J for the calibration. It is a selectable registry setting; its calibrated value is 1.17, stored to 2 decimals (the pilot's highest gust is 95.27 m/s).
- **Towers designed for their site** (selectable; default on, ruled 2026-10-09). A tower's strength scales with its site's design speed-up: the code's own worst-direction factor, without the ceiling, since a structure there is designed to the code. The tower reads its gust divided by that factor against the Fani curve. With the setting off, a ridge tower is a flat-ground tower in a stronger wind · J.

**Overhead lines.** Corrected 2026-10-02 (PR 6b answers):
- **By the kilometre.** Each km of a pole line fails or survives at its own local 3-second gust, from a stored per-km table; a line is down if any of its kilometres fails. Each failed kilometre is one failure point.
- **Calibration.** The per-km pole curve is calibrated so a moderate typhoon (severity 50, the pilot) takes down about 10% of overhead line length on average across scenarios, and a strong one (severity 70) about 30% · J. The targets apply to the **expected** share, computed from each kilometre's failure probability at its gust (a line is down if any kilometre fails, weighted by line length, averaged over the scenarios), not to one realized draw; the realized share is reported beside it (ruled 2026-10-10, PR 7b answers). The targets sit below observed outage shares (about a third of Taipower customers in Soudelor 2015, a strong typhoon), because many outages are trips cleared without a crew. One spread cannot meet both targets at 0.3, so the curve takes spread 0.4 with the median that meets both (ruled 2026-10-02; recalibrated 2026-10-09 for routed lines, the directional ridge factor, its ceiling of 1.17 and towers designed for their site: median 163.69 m/s, pilot 7.8%, severity 70 32.1%) · J. The median is a calibration parameter, not a physical gust; the targets, the achieved shares and the alternatives are recorded in the registry. The earlier anchor (0.05 per km at a 45 m/s gust, from US wood-pole fragility of 0.02–0.12 per pole at a 100 mph gust) is kept in the rule's history.
- **Towers.** Every mapped power line runs on towers (§4.2); feeds, including those from transmission substations, run on poles (corrected 2026-10-03, PR 14 answers). Towers read the line's peak gust against the Cyclone Fani collapse curve (median about 285 km/h) · L; tower placement is J.
- **Repair.** Crew work is 6 h per failure point, no lead time, plus road travel from the crew base to the road point nearest the failure, then the distance off-road to the line at a placeholder walking-and-carrying speed (J; ruled 2026-10-02, decision 0013) · J, anchored on Taipower's typical restoration within 1–3 days of large typhoons. A line with three failed kilometres needs 18 h of crew work. A collapsed tower needs 72 h of crew work (placeholder · J; emergency tower restoration takes days, permanent rebuilds after Faxai took weeks). In Phase 1 one line is one job for one crew; splitting a line across crews comes later.

**Damage and function.** A damaged element is off (condition 0) from the storm until its repair completes, then fully back (condition 1). This is the failed-or-working convention of most interdependent-infrastructure models (Dueñas-Osorio 2007; Ouyang & Dueñas-Osorio 2014; Lee, Mitchell & Wallace 2007) · L. Slight damage repairs within about a day, which reproduces Hazus's near-full function one day after slight damage. Partial capacity by damage state comes later (declared).

**Hospitals** are damaged by flood only. Hazus's hurricane evidence is that most hospitals stay open on backup power; their storm outages come through the cascade, cushioned by their reserves (§4.4a) · L (US).

**Scenarios.**
- Each scenario draws its track position and angle, its peak wind within the severity's CWA class band, and its random-variation field, from its own stream.
- Each element then fails independently given the field. This is the Hazus structure, and the shared field carries the spatial correlation (Adachi & Ellingwood 2009; Jayaram & Baker 2010) · L. Correlation beyond the field is left out (declared).
- Scenarios are equally weighted. The pilot keeps 8. Published studies use 30–200, so the pilot's expected values are over an illustrative set, not a probability estimate of real storms; the run note says so.

**Protection.** A protected element cannot be damaged in any scenario: the fortification convention of defender–attacker models (Brown et al. 2006: a defended asset "becomes invulnerable") · L. Real hardening lowers the failure chance rather than removing it, so defensive answers are an upper bound on the value of protection (declared). Protection can target a facility or an overhead line.

**Arithmetic.** Every curve that needs exp or erf (line fragility, any lognormal) is built offline into a stored table in the rules registry. At runtime only +, −, ×, ÷ and sqrt are used (§3). Each hazard rule goes in the registry with its source, grade and Theta role (θ\*-dynamics).

**Damage-state names.** Slight, moderate, extensive and complete, the Hazus lifeline names the repair times use.

### 4.4 What sources don't show

These are the real-but-unobserved quantities. They split into two groups by how they are made, and their design targets are set in §4.4a. Stage order: **layers → requirements → couplings → reserves, strength, modes and repair.** Requirements are drawn before couplings because they decide which substation supplies a consumer (§4.3a, rule 4).

**Derived.** Computed from the world already built, never drawn on their own:

| Quantity | How it is derived |
|---|---|
| Coupling strength κ | κ = min(1, available supply ÷ requirement). Available supply is the supplier's capacity shared pro rata among its consumers. It is κ ∈ [0, 1] as the dissertation defines it (Appendix A, Def. 2.5). The uncapped ratio is recorded in the truth manifest as headroom. Telecom requirements are binary (served or not), and a telecom edge's κ is its public-network share (§4.3a, rule 1) |

**World check (undisturbed supply):** in the world before any disruption, every consumer is fully supplied: R_φ(v) ≥ 1 for every node and commodity. A world that fails this is reported and not used; it is never silently regenerated.

**Buffers.** Two kinds, ruled 2026-09-29, closing open decision 7:
- **Stock buffers** (reserves). Fuel, stored water, batteries, supplies. Buffer time = stock ÷ draw, computed in the run at expected load, because the draw changes during an event. On generator power a hospital runs its essential load (§4.4a).
- **Tolerance buffers** (telecom only). With no stock behind them, a facility keeps full function on manual fallback for T hours, then steps to a degraded level d. The public share κ scales the depth: d_eff = 1 − κ(1 − d); T is not scaled. When telecom and another supply fall short together, the facility takes the lowest level, not the product.

**Drawn per element from context.** Each element gets its own value, drawn from a distribution whose centre depends on that element's situation:

| Quantity | Context it depends on |
|---|---|
| Requirements per commodity | Node class and its size attribute (beds, capacity, throughput class) |
| Reserves (stock) | Node class and subtype; designated critical sites take a fixed higher target |
| Presence of backup (generator, battery) | Node class (§4.3a subtypes) |
| Generator availability | Per generator: fails to start, or fails to run |
| Tolerance T and level d | Node class and subtype (§4.4a) |
| Failure mode (throttle, trip, or step to a floor) | Dependency type × node class |
| Repair (lead time, crew work, emergency option) | Node class, damage state, travel time from the crew base over roads |
| Crews and crew bases | Counts set in the recipe; bases sited by urban extents and road access |

**Levers.** Each continuous drawn quantity has a design target (§4.4a) and two levers:
- *heterogeneity (percent):* the spread of element values, as a standard deviation expressed as a percentage of the target;
- *compliance gap (percent, −50 to 95):* shifts the **median** below the target (positive) or above it (negative). A gap of 0 means centred on the target, not that every element complies. The gap is capped at 95; a missing generator or battery is carried by the presence attribute, not by a gap of 100.

Draws use one method for every quantity: a right-skewed quantile table, interpolated linearly, built offline and stored as decimal constants with their provenance. The shape is lognormal, because it is the standard shape for maintainability and repair data. Tables are scaled to median 1 and clipped at the 0.5% and 99.5% quantiles so tails stay plausible. At runtime only +, −, ×, ÷ and sqrt are used (§3).

For categorical quantities the levers read differently:
- **Failure mode:** heterogeneity is the share of elements whose mode departs from the class default.
- **Links on nodes-only layers:** it is the share of links that depart from the shortest road route.
- The compliance gap applies to neither.

At zero heterogeneity and zero gap every element sits on its target, and an analysis that assumes the standard is right for free. Both levers are recorded per quantity in the truth manifest.

### 4.4a Design targets

Ruled by the author, 2026-09-29. Every target is placeholder-grade until the realism ranges are measured (§10, item 4). Anchoring order: **Taiwan first**. The fallback order after Taiwan is to be decided; where no Taiwan rule exists, the source used is named. The full evidence, with sources and quotes, is in `evidence/Design_Targets_Evidence_v0_1.md`, and the ruling sheet is `evidence/Design_Targets_Ruling_Sheet_v0_2.md`.

Grades: S = standard or regulation · L = literature or government report · J = judgment. Jurisdiction: TW, JP or US.

**Requirements** (normal-operation draw):

| Element | Target | Grade |
|---|---|---|
| Tertiary hospital electricity | 2.5 kW per bed | L/J (TW bound) |
| Regional hospital electricity | 2.0 kW per bed | L/J |
| Hospital water | tertiary 1.0, regional 0.5 m³ per bed per day | S (TW plumbing code) |
| Clinic | 27 kW | L (US) |
| Mast | 6 kW | L |
| Water treatment | 0.37 kWh per m³ treated | L |
| Refinery | 7.0 kWh per barrel of crude | L (US) |
| Data centre | IT load × 1.57 | L |
| Thermal generation fuel | LNG combined cycle 8.0 GJ/MWh, oil 11.8, coal 11.4 | L (US 2024 heat rates) |
| Telecom | binary (served or not) | ruling |
| Other classes | placeholders named in the evidence | J |

**Rule 4 of §4.3a (large loads).** A consumer whose peak load is 5 MW or more is supplied from a transmission substation; below that, from a distribution substation. A recipe switch sets 10 MW (22.8 kV areas). Source: Taipower Business Regulations, Art. 46 · S (TW). Peak load is the requirement × a peak factor (placeholder 1.3).

**Stock buffers (reserves):**

| Element | Target | Grade |
|---|---|---|
| Tertiary and regional hospital, generator fuel | 72 h at essential load (60% of normal) | L (TW accreditation; JP rule) |
| Clinic | no generator by default | S (US) |
| Hospital water | 72 h at the emergency ration of 300 L per bed per day; in a water outage the hospital drops to the ration | L (TW guideline) |
| Hospital supplies | 72 h | J/L (JP) |
| Blood bank | generator fuel 72 h; blood stock 7 days | L (TW) |
| Mast battery | 4 h; 72 h at designated disaster-response sites | S (TW, base-station regulations Art. 22) |
| Exchange | battery plus 24 h fuel | L (US) |
| Data centre | 72 h fuel | L |
| Cable landing, water treatment | 48 h fuel | J |
| Generation with municipal make-up water | 24 h of purified (demineralized) boiler water; range 6–48 h. Taiwan's large thermal plants cool with seawater, so the main supplies boiler and process water, not cooling | L (IS 13268:1992 §4.2.3, 16–24 h; India); Taiwan environmental impact statements to replace it |
| Data centre, evaporative cooling | 12 h of make-up water; range 0–48 h | S (Uptime Institute Tier III minimum; US) |
| Seaport | backup power for cargo handling 0 h; range 0–48 h (48 h = a highly reinforced port that still works cargo); no power, no cargo | J; dependence on power: TT Club (2026) |
| Pump station | pre-positioned portable generator at a recipe share of stations, 24 h fuel | L (TW practice) / J |
| Distribution water storage | 12 h of peak-day demand | L (JP) |
| LNG at the import terminal | 11 days | S (TW) |
| Oil | 60 days held by industry plus 30 held by government, pro rata by tank capacity | S (TW) |
| Coal at coal plants | 30 days | S (TW) |
| Against telecom loss | none (tolerance buffer instead) | — |

Battery and generator hours add. Fire-reserve water does not count toward the potable buffer.

**Fuel resupply** on buffer-resupply edges: lead time 12 h from the depot; each delivery carries 24 h of fuel. Placeholder, J.

**Compliance gaps (defaults):**
- hospital backup 15%;
- water facilities 20%;
- exchanges and data centres 0%;
- masts 0% against the TW 4 h rule.

**Generator availability:** a separate per-generator draw of fail-to-start and fail-to-run, from military generator reliability data (Marqusee & Jenket 2020) · L (US).

**Tolerance buffers (telecom loss):**

| Class | T (hours) | d after T | Grade |
|---|---|---|---|
| Towered airport | 0 | 0.2 | L (US) / J |
| Tank farm, pipeline-connected | 1 | 0.5 | S (US) / J |
| Generation | 12 | 0.95 | L (US) |
| Import terminal | 12 | 0.8 | J |
| Transmission and distribution substations | 12 | 1.0; no supply effect. Remote switching is lost: re-energizing waits for a crew to travel there and switch by hand, 1 h on site (0.5–2 h) plus travel (§4.5) | L (US) / J |
| Pumping | 12 | 0.8 | J |
| Water treatment | 24 | 0.9 | J |
| Reservoir | 72 | 0.95 | J |
| Seaport, freight yard | 24 | 0.5 | L (IT-outage analogue) / J |
| Depot | 12 | 0.6 | J |
| Refinery | 72 | 0.8 | J |
| Hospital, records on site | 24 | 0.85 | S (TW NHI fallback) / L |
| Hospital, records hosted off site | 0.5, ramping linearly to d by 4 h | 0.65 | L (US) |
| Clinic | 24 | 0.8 | S (TW) / J |
| Blood bank | 24 | 0.7 | J |
| Airport, not towered | 24 | 0.8 | J |
| Tank farm, not pipeline-connected (truck-fed) | 12 | 0.6 | J |

The last two rows were added on 2026-09-29 under decision 0010: a non-towered airport's flights run on radio, so telecom loss mainly hits bookings and fuel orders; a truck-fed tank farm works like a fuel depot and takes its values.

**Failure mode** (the consumer's response to a shortfall on one commodity, drawn per node and commodity):
- **Defaults:** physical flow → trip; logistic, control and service → throttle.
- **Class departures:**
  - to throttle: substations, water treatment, multi-pump stations;
  - to step-to-floor: hospitals on generator, at the essential fraction;
  - to trip: towered airport on telecom.
- Heterogeneity default 10%. J with L support (US: NERC load modelling; Lee, Mitchell & Wallace 2007).

**Repair.** Two alternative modes per eligible damaged node:
- **Permanent:** a lead time that holds no crew (assessment and parts), then crew work hours, restoring full capacity. The centre is the Hazus restoration mean by class and damage state (Hazus MR4 technical manual; 6.1 values unverified) · L (US). Crew work hours are 8 h at slight damage, 24 h at moderate, 72 h at extensive and 168 h at complete (placeholders; the last two ruled 2026-09-30, decision 0011 addendum); lead time is the Hazus mean less the crew work, floored at 0. The centre is not shifted by default (repair compliance gap 0) and the spread is Hazus's own standard deviation ÷ mean; the recipe's heterogeneity lever for repair is an optional override (decision 0011 addendum).
- **Overhead lines:** 6 h crew work per failure point, no lead time (§4.3b).
- **Emergency:** travel over roads from the crew base plus set-up, using one unit from a finite pool. It restores reduced capacity for the rest of the event.
  - Distribution substation: mobile substation, 12–24 h including travel, about 25 MVA against the node's normal peak load (L, US DOE).
  - Mast: mobile cell site, about 14 h, capacity 0.5 (L, US; capacity J).
  - No other class has an emergency mode inside a 72 h window. Hazus substation restoration already includes temporary measures at extensive and complete damage.
- **Travel:** road travel time from the crew base is its own term, not a multiplier on repair time.
- **Unrepairable in the window:** reservoirs.
- **Pilot:**
  - 2 crews in one pool, a declared scarcity (sensitivity test at 1, 2 and 3);
  - one crew base (`crew_base`);
  - an emergency pool of 1 mobile substation and 1 mobile cell site, set in the recipe (`mobile_substations`, `mobile_cell_sites`);
  - the storm causes slight and moderate damage only at facilities, plus overhead-line failures (§4.3b).

**Crews:**
- Crews are counted in the recipe.
- Crew bases (`crew_base`, distinct from the fuel depot class) are sited in towns by road access.
- Taiwan reference: 24 Taipower district offices, about 1,500 km² each; crews of 5 to 7 people · L (TW).

### 4.5 Dynamics and difficulty

Ruled by the author, 2026-10-02 to 2026-10-09 (decision 0014). The ruling sheet is `evidence/Dynamics_Ruling_Sheet_v0_3.md`; the per-class behaviour is `evidence/Degradation_Profiles_v0_2.md`, and each profile is a test. Every setting below is a registry rule that a recipe overrides by name and the interface will expose; nothing is hard-coded.

**What the dynamics are.** The engine plays a scenario out over time: damaged elements stay off until repaired, shortfalls cascade through the dependencies, stocks drain and refill, and crews work through the repairs. It is the world's true dynamics, θ\*. The answer-key solver (§5), the checks and `swm simulate` call it; the generator records θ\* but never runs the solver. The engine never sees error induction.

**The frame** (Appendix A, Definitions 3.3–3.7; Chapter 4 §4.2):
- A node's state is its condition × its supply level.
- **Condition** is 1 or 0 in Phase 1: a damaged element is off from the storm until its repair completes, then fully back (discrete recovery).
- **Supply level** is the lowest of the node's responses across the commodities it needs (typed weakest link), not their product.
- An edge delivers κ × g_δ(supplier's state), with the transfer form g_δ set by the dependency type.

**Transfer forms (pilot: calibration tier only).** Physical flow and service: linear. Logistic and control: threshold at θ = 0.5 (J). The step form is held for later worlds.

**Response to a shortfall** (the consumer's failure mode on each commodity, §4.4a), on the received share R:
- **throttle:** R;
- **trip:** 1 while R ≥ 0.9, else 0 (the trip point is a placeholder, J);
- **step to a floor:** hospitals on generator run at the essential fraction, 0.6.

Where a class has a telecom tolerance row, the tolerance acts first: full function for T hours, then d_eff = 1 − κ(1 − d).

**Links and lines.**
- Links inside power, water, fuel and telecom carry that layer's commodity: physical flow, linear, shared pro rata when the supplier is short.
- Roads give reachability and crew travel; healthcare referral links carry nothing in Phase 1.
- A failed line passes nothing until repaired. No power-flow model (declared).

**Stocks.**
- A stock covers its own commodity's shortfall while it lasts, drawn down at the actual draw (a hospital on generator draws its essential load).
- A generator that fails to start never covers; one that fails to run stops at its drawn time.
- **Fuel deliveries** arrive 12 h after the consumer loses power, then every 24 h, while the depot is up and a road links them.
- **Refill:** batteries recharge from empty to full in 12 h (J); water storage refills from the pumps' spare capacity while still serving demand; purified and make-up water stocks refill from the main once it returns, as does hospital water, at the rate they drained (range half that rate to the same rate; relaxed value instant refill; ruled 2026-10-10); generator tanks refill only by delivery, every 24 h until full; national LNG, oil and coal stocks do not refill inside the window.

**Repair and crews.**
- Recovery is all or nothing in Phase 1.
- **Crew-bound lead time** (mobilize, assess, stage): 2 h (J) plus travel, starting when a crew is assigned and repeating at every job.
- **Parts lead time:** the rest of the Hazus lead time, max(0, lead time − 2 h). It runs in parallel with no crew; in Phase 1 its clock starts at the end of the storm.
- **A crew's sequence:** assigned → travel → assess → repair once its parts are in → travel to the next job. Crews move job to job; they do not return to base.
- **Travel** uses the road network, then off road at 2 km/h to a line's failure point (§4.3b). In Phase 1 one line is one job for one crew.
- **Default crew order** (the restorative model replaces it): (1) towered lines and transmission substations; (2) distribution substations and feeds to end uses, highest Lifeline weight first, where a distribution substation ranks by the highest Lifeline weight among the end uses it supplies, its own weight included (ruled 2026-10-19; alternatives: its own weight only, or the sum over what it supplies); (3) everything else. Ties go to the shortest travel, then the lowest id. Emergency units go to eligible damaged nodes in the same order.
- **Manual switching:** when a repair should re-energize a substation whose telecom is down, power returns only after a crew travels there and switches by hand: 1 h on site (range 0.5–2 h, J) plus travel as for repairs. The trip uses a crew like any job. It does not apply when the repair is at the substation itself.

**Time.**
- The storm acts at hour 0; all its damage is applied then.
- Steps of 15 minutes. Within each step the cascade settles: states are recomputed until they stop changing, up to 100 passes (the convergence parameter γ). A run that hits the cap is reported, never hidden.
- The horizon comes from the request (default 72 h); the engine has no fixed window.
- Arithmetic is + − × ÷ and sqrt only, so runs are identical on every platform.

**Ranges and relaxed values** (D11).
- Every limit carries a default, a range and a **relaxed value**: unlimited for stocks and capacities (fuel, batteries, water, backup power, crews, pump capacity), zero for delays and losses (lead times, travel, switching time, telecom tolerance loss).
- A recipe relaxes any limit by name: one alone, all but one, or any named mix. Relaxing is stored as a flag, never as a large number.
- Relaxing a limit is distinct from removing a dependency. An unlimited water stock keeps the plant dependent on the main, but the dependency never bites; removing the coupling deletes it. They are separate switches, and a result says which it used.
- Relaxing a limit never makes the outcome worse (a test).

**The calm-world check.** With no damage, every node holds state 1, every stock stays full, and no crew, delivery or tolerance clock moves, for the whole horizon. Any deviation fails the build.

**Saved reference runs.** The pilot's 8 scenarios run for 72 h with no actions and the default crew order. Each is saved as golden files, stamped with the horizon and the policy, recording every node state, stock level, crew position and job, and repair completion, plus unweighted hours out per end-use node. `swm simulate --scenario N` prints and plots any run.

**The Theta List.** Every modelling choice is tracked in the tuple under Θ, so a decision maker can be told every choice behind a result. It spans four domains: the constructed world's truth θ\* (every registry rule and every dynamics choice above); the constructed world's error model (Phase 3); the real-world chain (the Chapter 5 pipeline, recorded in the same format in its own repository); and each analysis run's declared θ̂. Each entry carries its framework sub-type (construction, dynamics, analysis, stopping) and symbol, the θ\* value and each run's θ̂ value, its alternatives, its relaxed value, what a flattened run does with it, its sensitivity status and its ruling. The 72 h window is a stopping entry. Objectives (the metric, the acceptability threshold, the service weights) are outside the tuple: they are the questions being answered, recorded with each request. The list is built into the rules registry; `swm rules --theta` prints it, and the dissertation appendix prints from the same source.

**Difficulty and tiers** (unchanged):
- **Tier:** exact, simulation, or both. The exact tier is restricted to forms that admit a provable optimum, declared as a simplification. Both runs worlds sized to fit both tiers (the overlap band), so the two can be compared directly.
- **Difficulty readout:** computed from the world alone (feed mix, concentration, hazard severity, coupling density), never set by hand. There is no installed-redundancy total: redundancy is planted as configuration (§4.3). How the score is measured is open (§10, item 3).
- **Produces:** the world's declared dynamics composition, θ\*.

### 4.6 Emission

- **Produces:** one set of files per source switched on, for emitted layers only, in the source's real container, schema and idioms.
  - On node-only layers, links are withheld.
  - Hidden layers and switched-off couplings are withheld. Couplings (edges between layers) and the feeds below the substations are never emitted.
  - Overlapping assets appear in each of their sources.
  - All attributes the real source carries are emitted, scored or not (§4.7).
  - The true correspondence across sources is written to the truth manifest.
- **How each source is written** (ruled 2026-10-10, decision 0015; `evidence/Emission_Ruling_Sheet_v0_2.md`):
  - **OpenStreetMap in three forms, built from the same features** (corrected 2026-10-10, PR 8 answers): the canonical `.osm.pbf` extract for the island (with a plain-text `.osm` copy); Geofabrik-style free shapefiles for the classes those carry; and Overpass-style GeoJSON for each query the pipeline runs. The last two are how the pipeline ingests Taiwan today. Each source's scope decides which features it contributes, and its own error settings apply to those features in Phase 3. The manifest records which records in each form are the same element.
  - **Outlines where real mapping uses them.** Classes usually mapped as areas (plants, substations, hospitals, water works, reservoirs, ports, airports, tank farms, refineries) are closed outlines with a rectangular footprint sized by class (J); the rest are points. The true location is the outline's centre. Lines on emitted layers are ways: power lines through their tower points, pipelines, mains and communication lines.
  - **Identifiers from reserved ranges.** Country `XS` / `XSW` ("Synthetic World", ISO 3166 user-assigned); OpenStreetMap ids from 900,000,000,000 (12 digits, so they fit Geofabrik's 12-character `osm_id` field; still far above any real id; amended 2026-10-10, PR 17 answers); WRI `XSW0000001…`; OurAirports `XS-0001…` with no ICAO or IATA codes; register codes with an `XS` prefix.
  - **Names.** Plain, pronounceable invented town names from a fixed syllable list in the registry, in English only (Phase 1); facilities named by town and class in each source's own style; a share of minor elements unnamed (J). Every facility is unique by name within its town unless its class is on the shared-name list (masts, pumping stations, distribution substations, water storage tanks, road junctions, fuel depots; registry placeholder, J). A repeat takes a direction word from its position relative to the town centre, found by comparing east and north offsets, and a number if two share a direction; the lowest world id keeps the plain name. Shared-name classes may repeat a name, as real ones do. The unnamed share applies only to masts, pumping stations and distribution substations (ruled 2026-10-10 and 2026-10-11, PR 17 answers). A test screens names against common words and well-known places. Leaks are flagged by the identifiers, not the names.
  - **The facility register is three real-style file types, joined on the institution code** (corrected 2026-10-10, PR 8 answers): the health ministry's institution register (every facility; code, name, county and district), the national health insurance hospital lists (one file per level), and the beds table by code. Column headers as in the real files; values in English; coordinates in place of addresses in Phase 1 (declared departure). The emergency-hospitals PDF, synthetic addresses, a gazetteer and the pipeline's geocoder come in Phase 6. Every hospital-level file is written in every world; a level with no hospitals is a file holding only its header.
  - **Columns the world does not hold** are left empty, as the real file leaves them: in Phase 1, WRI's commissioning year and owner. Phase 6 draws them at fill rates measured from the real file. The manifest declares the empty columns.
  - **Scored attributes:** location; class; capacity where the source carries it (MW, voltage); line end points (OpenStreetMap); capacity and primary fuel (WRI); type and scheduled service (OurAirports); register level and beds (register). Everything else, names included, is context.
- **Printable hand-trace pack:** a one-page map (nodes, lines and towers, links, the seven couplings switched on, the crew base, the storm track and damage) and tables (nodes and stocks, dependencies, the scenario's damage, the reference-run timeline), as a PDF with fixed metadata and as CSV. Scenario 7 by default.

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

- **Produces** (one YAML file per world, beside the GeoPackage inspection export, in its own folder; the pipeline is never pointed at it):
  - every planted error, with target, observability, source and mechanism (empty in Phase 1, and stated as a zero-error emission);
  - every unobserved value, with its design target, context factors, heterogeneity and compliance gap;
  - every hidden layer and hidden coupling, and the feeds with their routes;
  - the cross-source correspondence: every true element's record in each file, by id;
  - the true geometry: each location, each outline's corners and centre, each line's route and tower points;
  - the scored and context attribute lists per source;
  - the declared departures from the real sources;
  - the dynamics composition, θ\*, by registry fingerprint, with the Theta List;
  - the seeds and spawn tree.
- A test proves no source file holds anything found only in the manifest.

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
| 7 | ~~The buffer typology ruling~~ Closed 2026-09-29: stock buffers plus a telecom tolerance buffer (§4.4) | Decides whether every buffer is a stock (fuel, stored water, battery charge) or whether some are tolerance with no stock behind it (a hospital working on paper while telecom is down). A tolerance buffer would need its own drawn quantity |
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

## Changes from v0.12

Ruled by the author, 2026-10-19 (PR 19 answers):
- §4.5 default crew order: a distribution substation ranks by the highest Lifeline weight among the end uses it supplies, its own included. Alternatives recorded: its own weight only; the sum over what it supplies.
- Standing requirement (later phase): each dynamics rule with recorded alternatives becomes a selectable option in the recipe and the interface, so the same world can be run under each alternative and the results compared.

## Changes from v0.11

Ruled by the author, 2026-10-11 (PR 17 answers 2; addendum to decision 0015):
- §4.6: name uniqueness within a town is the default for every class; only six shared-name classes may repeat a name. The unnamed share still applies only to masts, pumping stations and distribution substations.

## Changes from v0.10

All ruled by the author, 2026-10-10 (PR 17 answers; addendum to decision 0015):
- §4.1a: each source is written at its real coordinate precision (OpenStreetMap 7 decimals, WRI 4, the others as measured); rounding is part of the clean emission, not error.
- §4.6: OpenStreetMap ids start at 900,000,000,000 (12 digits), amending ruling E3, so they fit Geofabrik's `osm_id` field without a departure.
- §4.6: major facilities have unique names within their town (direction word, then number); minor ones may share a name.
- §4.6: every hospital-level file is written, header-only when empty; columns the world does not hold (WRI commissioning year and owner) stay empty until Phase 6.

## Changes from v0.9

All ruled by the author, 2026-10-10 (decision 0015; Emission Ruling Sheet v0.2):
- §4.6 specifies how each source is written: one OpenStreetMap extract; outlines where real mapping uses them; reserved identifiers (XS / XSW); plain invented names in English; coordinates in the facility register for Phase 1; scored and context attributes; the printable hand-trace pack.
- §4.8 adds the true geometry (outlines, routes, towers), the feed routes and the declared departures to the truth manifest.
- §4.5: water stocks refill from the main at the rate they drained (range half to the same rate; relaxed value instant).
- Later phases, recorded at the author's request: bilingual names (Chinese and English); synthetic addresses with a gazetteer and the pipeline's geocoder (Phase 6).

## Changes from v0.8

All ruled by the author, 2026-10-02 to 2026-10-09 (decision 0014; Dynamics Ruling Sheet v0.3; Degradation Profiles v0.2):
- §4.5 rewritten: the dynamics engine (state, transfer forms, responses, links, stocks and refill, repair with split lead time and crews moving job to job, manual switching, 15-minute steps with settling, the calm-world check, saved reference runs, the Theta List).
- Ranges and relaxed values for every limit, with relaxing kept distinct from removing a dependency (§4.5).
- New stocks: purified boiler water at generation (24 h), make-up water at evaporative data centres (12 h), backup power for cargo at seaports (0 h) (§4.4a).
- Substation telecom loss costs a manual switching trip instead of slowing repair (§4.4a, §4.5).
- Storm corrections of 2026-10-03 and 2026-10-09 (PR 14 answers): the ridge factor read in the storm's own direction, capped at 1.17 against Taiwan's 95.2 m/s gust record; towers designed for their site; the pole-line median recalibrated to 163.69 m/s (§4.3b).
- Later phases, recorded at the author's request: sharing rules when a supplier is short beyond pro rata; recovery forms beyond all or nothing; step and concave degradation forms; partly failed lines and line capacity limits; power flow (Phase 5); the parts clock starting at first assessment; toggleable step size and event-driven timing; damage timed to the storm's passage; timed exogenous events in a scenario; a saved scenario and run library; crane versus roll-on/roll-off seaport terminals; air-cooled data centres.

## Changes from v0.7

All ruled by the author, 2026-10-02 (decision 0013):
- Power lines are mapped elements with terrain routes, voltage and towers, joining plants and substations of any class (§4.2). Feeds below distribution substations run along roads and are never emitted.
- Any substation can supply any power consumer; rule 4 still sends large loads to a transmission substation (§4.3a).
- Lines read the wind along their true route, raised on ridges and hills by Taiwan's building wind code topographic factor (§4.3b). Crews reach a failure point by road, then off road.
- Later phases, recorded at the author's request: per-scenario sharing rules when a supplier is short (pro rata, priority lines, full support until exhausted, others); partly failed lines; line capacity limits after Phase 1; a power-flow model in Phase 5; routing of water mains, pipelines and fibre if the data supports it.

## Changes from v0.6

All ruled by the author, 2026-09-30 (decision 0012, and the decision 0011 addendum for repair), with the PR 6a answers of 2026-10-02 folded into §4.3b (track offset and radius drawn per scenario; lee against the smooth spine line; wooded land as town; rainfall drawn per scenario; 2 m platforms for power plants and transmission substations; thresholds for refineries and import terminals):

- New §4.3b, the storm: overhead lines fail by wind and facilities by flood; a modified Rankine wind field with sea-to-land, Taiwan wind-code, mountain-lee and random-variation factors; flood depth from height above drainage; equally weighted scenarios; protection as immunity, for facilities and overhead lines.
- Severity re-anchored to Taiwan's typhoon classes (peak wind and rainfall), replacing "100 = every exposed element in the hazard core fails" (§4.3, §4.3b). Pilot severity 50.
- Repair: crew work for extensive (72 h) and complete (168 h) damage; repair centred on Hazus (gap 0) with Hazus spread; the emergency pool moved to the recipe; overhead-line repair added (§4.4a).

## Changes from v0.5

All ruled by the author, 2026-09-29:

- §4.4 rewritten and §4.4a added: design targets for requirements, reserves, tolerance buffers, failure modes, repair and crews, with grades and sources. Taiwan is the first anchor.
- Buffers are of two kinds: stock (reserves) and tolerance (telecom only). This closes open decision 7.
- Levers: the compliance gap shifts the median, is capped at 95, and 0 means centred, not compliant. Heterogeneity is a standard deviation. One skewed quantile-table method is used for every draw.
- κ stays capped at 1, with headroom recorded. A telecom κ is the public share. New world check: every consumer is fully supplied before any disruption.
- Rule 4 of §4.3a: 5 MW peak load (Taipower Art. 46), with a switch to 10 MW. Requirements are drawn before couplings.
- Repair: permanent (lead time plus crew work) or emergency (mobile substation, mobile cell site). The pilot pool is one of each.
- §4.3a: five supplier lists narrowed to the evidence (Work Order 4 answers, question 1).

## Changes from v0.4

All ruled by the author, 2026-09-29 (repository decision record 0007):

- New §4.3a: the dependency table for the 21 couplings, built from sources and checked independently, with its cross-table rules (public telecom share, buffer resupply, road reachability, large loads, the tertiary second feed) and subtype attributes.
- Concentration 0 now means nearest supplier with no pull toward a hub, not "spread evenly".
- Two-way dependency is a 0–100 setting over node-level mutual pairs, not an on/off switch.
- The airport is a transport origin (blood products and urgent supplies by air).
- Coal is carried by the import terminal, so coal generation has a fuel supplier inside the 21 couplings.
- Telecom → healthcare is typed service, not control.
- Power capacities are sized to load (§4.2).

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
