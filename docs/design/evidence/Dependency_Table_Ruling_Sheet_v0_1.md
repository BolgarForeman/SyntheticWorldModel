# Dependency table: ruling sheet v0.1

*2026-09-29 · for Foreman · SyntheticWorldModel, Work Order 4 prerequisite*

## What this is

The table says which node classes depend on which other layers in every constructed world. It is the core truth the study tests against, so it was built from sources and then checked independently:

- **Five research lanes**, one per supplier layer, each producing one row per consumer class. Every source was fetched, and quotes were taken from the fetched text.
- **An independent reviewer** that did not build the table. It re-fetched 27 sources: 12 confirmed, 14 overstated, 1 wrong, none fabricated. It raised 19 findings and checked the table against Appendix B's own wording.

Evidence files (in the project beside this sheet): `SWM_Dependency_Table_Evidence_v0_1_CAO_2026-09-29.md`, which holds the five lanes and the review in full.

The 21 couplings from Appendix B are unchanged. Everything below works inside them.

## What held up

These rows are sound and well sourced:

- power supplying everything with a motor or a server;
- water supplying hospitals;
- the LNG import terminal supplying gas-fired generation;
- the seaport supplying the import terminal;
- telecom supplying water and pipeline control (SCADA).

## Rulings needed (these change what the world contains)

**R1. Telecom → power runs mostly on the utility's own network.** Taipower runs more than 10,000 km of its own fibre linking its plants and substations for dispatch (台電月刊 Vol. 700). DOE (2023) says grid communications are "a mixture of private, utility-owned infrastructure and commercial leased infrastructure". As drafted, striking a public telephone exchange would black out grid control, which is false for Taiwan.

- (a) **Recommended.** Give each power, water and pipeline control dependency a share carried on the public telecom layer, set in the recipe. It defaults low for generation and transmission and medium for distribution and water, and is a placeholder until the realism ranges are measured. The private part is treated as part of the consumer's own layer.
- (b) Put utility private networks into the telecom layer as their own node class.
- (c) Keep the rows as drafted and declare the overstatement.

**R2. Backup-generator fuel is a buffer's buffer, not a supply.** Fuel → exchange, masts, data centres, treatment, pumping and healthcare is resupply for generators that only run when grid power is lost. As drafted, striking a fuel depot would fail a hospital that still has grid power, and depots would show up as false high-value targets.

- **Recommended:** mark these edges as buffer resupply. They do nothing while power is up. When power is lost, they extend the generator's runtime. This is Appendix B's "the buffer has a buffer" put into code.

**R3. One freight yard must not stand in for the whole road network.** Hospital resupply, blood couriers and tank trucks travel over roads from many places. With one yard as the only supplier, losing that yard would starve every hospital attached to it.

- (a) **Recommended.** A consumer is resupplied if any seaport, airport or freight yard reaches it over the road network. Roads carry; ports, airports and yards are the origins. This also gives the airport the supplier role you asked for: blood products and urgent supplies by air.
- (b) Require at least two freight-yard suppliers per consumer.

**R4. Tertiary hospitals on two substations.** The only source is one Taiwan hospital's own account (NTUH). No code requires two utility feeds, and as a class-wide rule it would make every tertiary hospital immune to losing one substation.

- **Recommended:** make it a recipe probability per class. The placeholder share is to be set from the realism ranges.

**R5. Coal has no supplier.** Coal was 40% of Taiwan's 2024 generation (EIA 2026). Without a supplier, two-fifths of generation is immune to every port and fuel strike.

- (a) **Recommended.** Let the import terminal carry coal (a coal pier and yard). Coal plants then depend on it through fuel → power, with a long stockpile buffer. No new coupling is needed.
- (b) Leave coal out and state it as a scope limit.

**R6. Telecom → healthcare is service, not control.** The evidence is electronic-health-record downtime and emergency-planning rules, not a command signal. The dissertation's control examples are SCADA, dispatch and air traffic control.

- **Recommended:** type it as service. A hospital whose records are hosted off site gets a shorter buffer.

**R7. Rail.** Appendix B says telecom loss leaves "ports and rail on manual fallback", but Phase 1 has no rail.

- **Recommended:** amend Appendix B to "rail from a later phase". Transport nodes other than ports, airports and yards still consume nothing in Phase 1.

**R8. Staff access to hospitals** is real (Qureshi 2005: transport problems were the top barrier to staff reporting to work), but it is a service dependency over roads.

- **Recommended:** declare it out of scope for Phase 1 in Appendix B. If added later, it rides the same road-reachability mechanism as R3.

**R9. Subtype attributes.** Some rows depend on what kind of node it is. Recommended set, each with a default, all placeholders:

| Class | Attribute | Values (default first) |
|---|---|---|
| Generation | fuel kind | LNG, oil, coal, hydro (shares drawn per world) |
| Generation | make-up water source | municipal, own intake/desalination |
| Import terminal | product | oil, LNG, coal (at least one per world where fuel-fired generation exists) |
| Airport | towered | yes for the largest airport, otherwise drawn |
| Airport | fuel receipt | pipeline for the largest airport, truck otherwise |
| Data centre | cooling | evaporative (Appendix B says "heavy … water couplings") |
| Refinery | crude receipt | marine, pipeline |
| Tank farm | pipeline-connected, jetty, truck rack | drawn |
| Healthcare | records hosted off site | drawn, rising down the tiers |
| Backup consumers | standby fuel | diesel, none |
| Large loads | supplied at transmission level | above a load threshold (placeholder) |

## Corrections I will make without a ruling

- Re-grade the 14 overstated rows. Examples:
  - the FCC backup rule never took effect;
  - NFPA 110 "Class 96" is accreditation practice, not code;
  - the OSHA fire rule is met by extinguishers;
  - the airport's second feed applies only to CAT II lights, not the whole airport;
  - US standards are marked as US wherever they stand in for Taiwan practice.
- Fix the factual slips:
  - no Generator Operator backup-path requirement in NERC COM-001;
  - the ADCC note was wrong;
  - the Taoyuan pipeline was inferred, not sourced;
  - the 62% figure is from Larsen 2019;
  - the Kramek quote is corrected to its real wording.
- Split rows that carried two dependency types (airport telecom, airport fuel) into subtype rows.
- Water storage consumes nothing; its volume is the buffer on downstream water edges.
- The LNG terminal can never supply bunker oil, diesel or jet fuel.

## Then

Once R1–R9 are ruled, the table becomes v0.2: spec §4.3a in World_Generator_Structure v0.5, with the evidence files cited. Work Order 4 builds from it. R1, R2 and R3 add machinery to Work Order 4 (a public-share setting, buffer-resupply edges, road reachability), so I will re-scope the work order after the rulings rather than send it as drafted.

## Also confirmed today

- The airport is a transport supplier (carried by R3a).
- Two-way dependency becomes a 0–100 setting: 0 means no mutual pairs; 100 means every mutual pair the table allows.
- The pilot's edge range is widened to 40–50.
