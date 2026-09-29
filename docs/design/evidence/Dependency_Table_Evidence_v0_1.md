# Dependency table: evidence bundle v0.1 (2026-09-29)

Contains: the brief, the merged draft, five research lanes, and the independent review. The companion ruling sheet is SWM_Dependency_Table_Ruling_Sheet_v0_1.

---

<!-- file: BRIEF.md -->
# Brief: the node-class dependency table for a synthetic interdependent-infrastructure world

## What this is for
A generator builds synthetic six-layer infrastructure worlds (power, telecom, water, transport, fuel, healthcare) for a PhD dissertation. It uses them as a known truth, and optimization answer keys are computed against them. The generator needs a table saying, for each cross-layer coupling (supplier layer → consumer layer), which consumer node classes depend on the supplier layer, and on which supplier node classes. The table is the core truth the whole study rests on. A wrong row corrupts everything downstream, so every row must be defensible against a real source.

## Node classes per layer
- Power: generation (thermal/LNG plant, or hydro dam), transmission_substation, distribution_substation
- Telecom: exchange (central office / switching centre), mast (cellular base station), data_centre, cable_landing (submarine cable landing station)
- Water: reservoir (upland raw-water impoundment), treatment (drinking-water treatment plant), pumping (booster pump station), storage (treated-water tank or elevated tower)
- Transport: seaport, airport, freight_yard (truck warehouse and yard), bridge, road_junction, rail_node. Bridges, road junctions and rail nodes consume nothing in Phase 1.
- Fuel: refinery, tank_farm (bulk storage), import_terminal (marine import, including LNG), depot (distribution depot / large filling point)
- Healthcare: tertiary (tertiary-care hospital, trauma centre), regional (regional hospital), clinic, blood_bank

## The 21 modeled couplings (fixed by the dissertation's Appendix B; do not add or remove any)
- power → telecom, water, transport, fuel, healthcare
- telecom → power, water, transport, fuel, healthcare
- water → power, telecom (data-centre subset only), fuel, healthcare
- transport → fuel, healthcare
- fuel → power, telecom, water, transport, healthcare

The dissertation's own rationale (Appendix B, verbatim):
> Power, the energy hub, reaches all five other layers on a short buffer: the dependent stops fast on power loss, except where a generator or battery buffers it. Telecom, the control and coordination hub, reaches all five others on a long, node-heterogeneous buffer: the dependent runs degraded, losing visibility and coordination first and failing only as unhandled faults accumulate — near-zero at air traffic control, long at ports and rail on manual fallback. Supply cross-feeds add fuel to power and fuel to transport, and water to power, to fuel, to healthcare, and to telecom at the data-center subset. The backup-generator chain adds fuel to telecom, fuel to water, and fuel to healthcare, since the generators that buffer a power loss themselves run on fuel — the buffer has a buffer. Transport logistics adds transport to fuel and transport to healthcare. Compute data centers are carried as a telecom node class with heavy inbound power and water couplings.
>
> Excluded: healthcare's five outbound edges (pure sink); water → transport; transport → telecom; transport → power (coal delivery); transport → water (treatment chemicals).

## Dependency types (the dissertation's four; each row gets exactly one)
- physical_flow: substance or energy through a fixed conduit (wire, pipe, fibre). Lowest substitutability; failure is felt immediately to within hours.
- logistic: movement over the transport network (fuel trucks, supplies, crews). Moderate substitutability; hours to days.
- control: a monitoring or command signal, with no substance flowing (SCADA, dispatch, ATC communications). Variable; immediate to hours.
- service: workforce continuity, access, institutional support. Highest substitutability; days to weeks.

## What each row must say
For each coupling, and each consumer class in the consumer layer, one row:

| field | meaning |
|---|---|
| coupling | e.g. power → healthcare |
| consumer_class | e.g. tertiary |
| depends | core / optional / none |
| supplier_classes | which node classes of the supplier layer can serve it (e.g. distribution_substation; transmission_substation for very large loads) |
| commodity | electricity, communications, water, transport access, fuel |
| dependency_type | one of the four |
| rationale | one or two sentences on the real-world mechanism |
| source | a real, checkable source: standard or code (e.g. NFPA 99/110, NERC, FAA orders, AWWA/EPA guidance, ITU/TIA), a government sector plan (CISA/DHS sector-specific plans, FEMA Community Lifelines), or peer-reviewed literature. Give the title, the issuing body or authors, the year and a URL. Quote the key sentence where you can. |
| evidence_grade | standard (a code or regulation requires or describes it) / literature (peer-reviewed or government report) / judgment (reasoned, no source found; say so plainly) |
| buffer_note | the typical on-site buffer against loss of this supply, if any (e.g. hospitals: emergency generators, NFPA 110 Level 1; masts: batteries of a few hours). This is noted for the next stage, not used in this table |
| taiwan_note | anything Taiwan-specific (Taipower, Taiwan Water Corporation, CPC, MOHW rules), if found |

Definitions:
- **core**: essentially every real facility of this class depends on this supplier layer. Omitting it would be wrong for a typical facility.
- **optional**: common but not universal, or present only in some configurations. The generator adds these as a density setting rises.
- **none**: this class does not meaningfully depend on the supplier layer. Say why.

## Rules
- Use real sources only, verified by fetching them. Never invent a citation, a standard number or a quote. If you can't verify a source, grade the row as judgment and say what you'd look for.
- Where the dissertation's rationale and the evidence disagree (for example, the evidence says a class depends on a layer the 21 exclude, or a listed coupling has no consumer that really depends), flag it in a "Disagreements" section. Do not change the 21.
- Also flag any consumer class whose dependency is conditional on its subtype (hydro vs thermal generation, LNG vs oil terminal, airport size), and say how the condition should be expressed.
- Be concise. Write your output as Markdown to the file path you are given, then reply with a 5-line summary.

---

<!-- file: MERGED_DRAFT.md -->
# Node-class dependency table: merged draft v0.1 (for independent review)

This table merges five research lanes, one per supplier layer. The full rows, sources and verified quotes are in lane_power.md, lane_telecom.md, lane_water.md, lane_transport.md and lane_fuel.md in this folder.

Key to columns:
- **Dep.**: C = core, O = optional, — = none.
- **Type**: PF = physical_flow, L = logistic, Ctl = control, Svc = service.
- **Grade**: Std = standard or regulation, Lit = literature or government report, Jdg = judgment.

## power → (electricity, PF throughout)

| Consumer | Dep. | Supplier classes | Grade | Key source |
|---|---|---|---|---|
| exchange | C | distribution substation | Std/Lit | CPUC D.21-02-029; FCC 07-177 (never in force); DOE CESER 2022 |
| mast | C | distribution substation | Lit | GAO-21-297 (Maria: 49% of cell outages from power loss) |
| data_centre | C | distribution; transmission if large | Lit | NERC Large Loads 2025 |
| cable_landing | C | distribution substation | Jdg | NEC PFE paper (mechanism only) |
| reservoir | — | | Jdg | gravity |
| treatment | C | distribution; transmission if large | Std | Ten States §2.6; EPA 800-R-19-001 |
| pumping | C | distribution substation | Std | Ten States §6.3.4–6.3.5 |
| storage | — | | Jdg | gravity; storage is the buffer |
| seaport | C | distribution; transmission if large container terminal | Lit | EPRI (electric STS cranes) |
| airport | C | distribution (a second feed under FAA configuration B) | Std | FAA AC 150/5340-30J; JO 6950.2F |
| freight_yard | O (C if cold storage) | distribution substation | Jdg | — |
| bridge, road_junction, rail_node | — (Phase 1 rule) | | | The evidence says these consume power (movable spans, signals, traction) |
| refinery | C | transmission substation | Lit (1966) | NPC 1966; needs a modern source |
| tank_farm | C | distribution substation | Std | FL §526.143; NPC 1966 |
| import_terminal | C | distribution (oil); transmission (LNG) | Lit | LNG technical paper |
| depot | C | distribution substation | Std | FL §526.143 |
| tertiary | C | distribution, two feeds from two substations | Std | 42 CFR 482.15(e); NFPA 99/110; Sci. Monthly (TW) |
| regional | C | distribution substation | Std | 42 CFR 482.15(e) |
| clinic | C | distribution substation | Lit | DOE CESER |
| blood_bank | C | distribution substation | Lit | ACHC |

## telecom → (communications)

| Consumer | Dep. | Type | Supplier classes | Grade | Key source |
|---|---|---|---|---|---|
| generation | C | Ctl | exchange; mast (backup path) | Std | NERC COM-001-3; NERC EMS-loss reference |
| transmission_substation | C | Ctl | exchange | Std/Lit | NERC EMS reference; DOE 2023 |
| distribution_substation | C | Ctl | exchange; mast | Lit | DOE 2023; Taipower DDCC |
| treatment | C | Ctl | exchange; mast | Lit | EPA 2016 comms guidance; Water SSP 2015 |
| pumping | C | Ctl | mast; exchange | Lit | EPA 2016 |
| storage | O | Ctl | mast; exchange | Jdg | the level-telemetry point |
| reservoir | O | Ctl | mast; exchange | Jdg | — |
| airport | C (towered) / O Svc (untowered) | Ctl | exchange | Lit | DOT OIG AV2017020; FAA Newark 2025 |
| seaport | C | Svc | exchange; data_centre; mast | Lit | Kramek/Brookings 2013 |
| freight_yard | C | Svc | exchange; mast; data_centre | Jdg | — |
| bridge, road_junction, rail_node | — (Phase 1) | | | | Appendix B mentions "rail on manual fallback" |
| refinery | C | Svc | exchange | Jdg | API 1164 scope only |
| tank_farm | C (pipeline-connected) / O Svc (truck-fed) | Ctl | exchange; mast | Std | 49 CFR 195.446 |
| import_terminal | C | Ctl | exchange; mast | Std | 49 CFR 195.446; 193.2519 |
| depot | C | Svc | exchange; mast; data_centre | Jdg | — |
| tertiary | C | Ctl | exchange; mast; data_centre | Std/Lit | 42 CFR 482.15(c)(3); Larsen JAMIA 2018 |
| regional | C | Ctl | exchange; mast; data_centre | Std/Lit | same |
| clinic | C | Ctl | exchange; mast; data_centre | Jdg (US) / Lit (TW) | NHI MediCloud VPN |
| blood_bank | C | Ctl | exchange; data_centre | Jdg | OneBlood 2024 (an IT outage, not telecom) |

cable_landing supplies no consumer directly. It feeds the exchange and data centre within telecom.

## water → (water, PF throughout)

| Consumer | Dep. | Supplier classes | Grade | Key source |
|---|---|---|---|---|
| generation, thermal, inland | C | reservoir (raw); storage/pumping | Lit | Energy SSP 2015 Table 4-1; EIA 2011 |
| generation, thermal, coastal once-through | C (small volume) | storage/pumping | Lit | SDG&E Encina 1995; USGS 2019 |
| generation, hydro | — (unless it shares a water-supply reservoir) | reservoir | Lit | Feitsui Reservoir |
| transmission / distribution substations | — | | Jdg | |
| data_centre | C (evaporative cooling) / — (dry or liquid) | storage/pumping | Lit | ELI 2026; LBNL 2024 |
| exchange, mast, cable_landing | — | | Jdg | outside the data-centre subset |
| refinery | C | storage/pumping; reservoir (raw) | Std/Lit | DOE refinery water study 2016; 29 CFR 1910.106(i) |
| tank_farm | O | storage/pumping (fire water) | Std | 29 CFR 1910.106(f)(8) |
| import_terminal | O | storage/pumping (fire and potable) | Std/Lit | 33 CFR 127.607; UT BEG 2006 (LNG uses seawater) |
| depot | O | storage/pumping | Std | 1910.106(f)(8) |
| tertiary | C | storage/pumping | Std | CDC/AWWA 2019 guide; 42 CFR 482.15(b)(1); TWC rationing priority |
| regional | C | storage/pumping | Std | same |
| clinic | C | storage/pumping | Lit | CDC/AWWA (dialysis) |
| blood_bank | O | storage/pumping | Jdg | |

Treatment is upstream of storage and pumping. It is not a direct supplier except on its own outlet main.

## transport → (transport access, L throughout). Suppliers: seaport, airport, freight_yard

| Consumer | Dep. | Supplier classes | Grade | Key source |
|---|---|---|---|---|
| import_terminal | C | seaport | Lit | EIA Taiwan brief 2026 (three crude ports) |
| refinery | C (marine crude receipt) / — (pipeline-fed) | seaport | Lit | EIA; Global Taiwan Brief (Taoyuan fed from Shalun) |
| tank_farm | O (has a jetty or truck rack) | seaport; freight_yard | Lit | EIA diesel ("most … moves by pipeline") |
| depot | C | freight_yard; + seaport on an offshore island | Lit | EIA diesel ("Trucks transport … to retail") |
| tertiary | C | freight_yard; + airport and seaport on an offshore island | Lit | FEMA Lifelines toolkit; NASEM 2020 (Maria); Kim & Bui 2019 |
| regional | C | same | Lit | same |
| clinic | C | freight_yard | Lit/Jdg | FEMA; Wassmer 2025 |
| blood_bank | C | freight_yard; airport (islands) | Lit | FEMA (blood products); Civil Beat 2019 (Hawaii) |

The airport supplies no fuel class. Airports consume fuel (fuel → transport).

## fuel → (fuel)

| Consumer | Dep. | Type | Supplier classes | Grade | Key source |
|---|---|---|---|---|---|
| generation, LNG | C | PF | import_terminal (LNG) via gas pipeline | Lit | EIA Taiwan 2026; CPC; Taipower Taichung |
| generation, oil | C | PF | tank_farm; refinery | Lit | |
| generation, hydro | — | | | Jdg | |
| generation, coal | no fuel-layer supplier | | | | coal is 40% of TW 2024 generation (see issue D) |
| transmission / distribution substations | — | | | Jdg | station batteries |
| exchange | C (backup) | L | depot; tank_farm | Std/Lit | DHS Comms SSP 2015; FCC 07-177 |
| mast | O (backup) | L | depot | Lit | FCC CSRIC IV WG9; Maria FCC hearing; NCC Danas 2025 |
| data_centre | C (backup) | L | depot; tank_farm | Std | Uptime Tier (12 h minimum fuel) |
| cable_landing | C (backup) | L | depot | Jdg | Equinix 2024 |
| reservoir, storage | — | | | Jdg | |
| treatment | C (backup) | L | depot; tank_farm | Std | Ten States §2.6; EPA 2019 |
| pumping | O (backup) | L | depot | Std/Lit | Ten States §6.3.4 vs EPA portable rotation |
| seaport | C | L | tank_farm; import_terminal; refinery; depot | Lit | CPC bunkering ports; RMI 2024 |
| airport | C | PF (pipeline) / L (truck) | refinery, tank_farm, import_terminal / depot | Lit | CPC Taoyuan pipeline; CNBC Colonial 2021 |
| freight_yard | C | L | depot; tank_farm | Lit | EIA diesel |
| bridge, road_junction, rail_node | — | | | | Phase 1 |
| tertiary | C (backup) | L | depot; tank_farm | Std | 42 CFR 482.15(e)(3); NFPA 110 Class 96 |
| regional | C (backup) | L | depot | Std | same |
| clinic | O (backup) | L | depot | Std (by absence) | 42 CFR 491.12 |
| blood_bank | C (backup) | L | depot | Lit | WHO 2005 cold chain §4.7.2 |

## Subtype attributes the table needs

1. generation `fuel_kind` ∈ {lng, oil, coal, hydro} and `cooling` ∈ {coastal once-through, inland recirculating}
2. import_terminal `product` ∈ {lng, oil}
3. airport `towered` and `fuel_receipt` ∈ {pipeline, truck}
4. data_centre `cooling_type` ∈ {evaporative, dry/liquid}
5. refinery `crude_receipt` ∈ {marine, pipeline}
6. tank_farm `pipeline_connected`, `has_jetty`, `has_truck_rack`
7. depot and healthcare `on_offshore_island`
8. healthcare `ehr_hosted`
9. backup consumers `standby_fuel` ∈ {diesel, natural_gas, none}
10. load size decides whether a transmission or distribution substation supplies the consumer (threshold: open)

## Design issues raised by the lanes

- **A. Backup-fuel edges are second-order.** They bind only after the consumer's power supply is lost and its on-site tank runs down. Should they be gated on power loss in the dynamics?
- **B. Trucked fuel travels over roads.** transport → telecom and transport → water are excluded, but the delivery path is real. Options: route logistic fuel edges over transport, or declare the gap.
- **C. The Phase 1 "consume nothing" rule for rail, junctions and bridges contradicts the evidence** (power, telecom), and contradicts Appendix B's "rail on manual fallback".
- **D. Coal generation has no supplier in the modeled layers.**
- **E. Utility private telecom networks.** Much of telecom → power and telecom → water runs on utility-owned fibre and microwave, not the public telecom layer.
- **F. Staff access to hospitals** is a service dependency over roads, which the transport supplier classes don't carry.
- **G. Clinical IT typed control** (hours) vs ports, refineries and depots typed service (days).
- **H. Water storage and reservoirs are buffers, not consumers**, in several rows.
- **I. Coastal thermal plants** depend on municipal water only thinly.

---

<!-- file: lane_power.md -->
# Lane: POWER as supplier layer

Five couplings: power → telecom, water, transport, fuel, healthcare. 22 rows. Every source below was fetched on 2026-09-29, unless a row says otherwise. A quote is given only where the fetched text contained it.

## Verified sources (keys used in the rows)

| key | source | what was verified |
|---|---|---|
| **S-DOE** | US DOE CESER, *State Energy Security Plan: Optional Drop-In: Cross-Sector Interdependency Diagrams*, May 2022. https://www.energy.gov/sites/default/files/2022-06/DOE%20CESER%20SESP%20Drop-In_Cross-Sector%20Interdependency%20Diagrams_FINAL_508.pdf | "All of the other critical infrastructure sectors depend on power and/or fuel to operate." |
| **S-FCC07** | FCC, *Katrina Panel Order*, FCC 07-177 (June 2007), https://docs.fcc.gov/public/attachments/FCC-07-177A1.pdf. The FCC PDF returned 403, so this was verified through CPUC D.08-09-014 (2008), https://docs.cpuc.ca.gov/published/FINAL_DECISION/87681-06.htm, and Lexology, https://www.lexology.com/library/detail.aspx?g=c7e48731-8049-4ca5-943f-9a9def04951d | CPUC: the FCC order "requires LECs and CMRS providers to have 24 hours of emergency backup power for central offices and eight hours for cell sites, remote switches and digital loop carrier system remote terminals… it is not yet in effect and is on appeal." Lexology: the FCC abandoned the rule after OMB rejected it. **The rule never took effect.** |
| **S-CPUC** | California PUC, *Communications Network Resiliency*: D.20-07-011 (wireless, 16 Jul 2020) and D.21-02-029 (wireline, 18 Feb 2021). https://www.cpuc.ca.gov/industries-and-topics/internet-and-phone/network-performance-and-public-safety/communications-network-resiliency | "deployment of back-up power duration of at least 72 hours in Tier 2 and Tier 3 High Fire-Threat Districts"; wireline providers must deploy 72 hours "in locations with insufficient mobile wireless coverage." |
| **S-GAO** | US GAO, *FCC Assisted in Hurricane Maria Network Restoration, but…*, GAO-21-297, April 2021. https://www.gao.gov/assets/720/714079.pdf | "96 percent of telecommunications cell sites were out of service" in Puerto Rico. Of those, "49 percent were not operational because of the power outage", rising to 79% in October 2017. Backup at sites gave "only a limited level of service, ranging from several hours to one day." |
| **S-NERC** | NERC Large Loads Task Force, *Characteristics and Risks of Emerging Large Loads* (white paper), July 2025. https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/3_doc_white-paper-characteristics-and-risks-of-emerging-large-loads.pdf | Large loads "must be served by the transmission system and may require new transmission facilities"; they "range in size from several megawatts to several gigawatts"; "multiple data centers decreased consumption, switching some of their facility power to backup systems." |
| **S-UPTIME** | Uptime Institute Journal, *Myths and Misconceptions Regarding the Uptime Institute's Tier Certification System*. https://journal.uptimeinstitute.com/myths-and-misconceptions-regarding-the-uptime-institutes-tier-certification-system/ | "Utility power is not even required for Tiers. Most Tier Certified data centers use utility power for main operations as an economic alternative." |
| **S-NECPFE** | Kaneko, Chiba, Kunimi and Nakamura, *Power Feeding Equipment for Optical Submarine Cable Systems*, NEC Technical Journal, 2010. https://www.nec.com/en/global/techrep/journal/g10/n01/pdf/100107.pdf | "The power feeding equipment supplies constant DC current to the submarine repeaters", converted from the 48 V DC station plant. The paper does not say where the station plant's power comes from. |
| **S-10SS** | Great Lakes–Upper Mississippi River Board, *Recommended Standards for Water Works* ("Ten States Standards"), 2022 ed. (PA DEP copy). https://files.dep.state.pa.us/Water/BSDW/Public_Water_Supply_Permits/2022_Recommended_Standards_for_Water_Works.pdf | §2.6: "Dedicated standby power shall be provided so that water may be treated and/or pumped to the distribution system during power outages to meet the average day demand." §6.3.4: "To ensure continuous service when the primary power has been interrupted, a power supply shall be provided from a standby or auxiliary source." §6.3.5: "Where independent substations are used for emergency power, each separate substation and its associate transmission lines must be capable of starting and operating the pump station at its rated capacity." |
| **S-EPAPWR** | US EPA Office of Water, *Power Resilience: Guide for Water and Wastewater Utilities*, EPA 800-R-19-001, June 2019. https://www.epa.gov/sites/default/files/2016-03/documents/160212-powerresilienceguide508.pdf | Critical components "usually include treatment processes and key pumping stations"; utilities may have "different distribution feeders or substations for the treatment facility and individual pumping stations." |
| **S-AWWA** | AWWA, policy statement *Electric Power Reliability for Public Water Supply and Wastewater Utilities* (revised March 2025). https://www.awwa.org/policy-statement/electric-power-reliability-for-public-water-supply-and-wastewater-utilities/ | "Redundancy of supply and/or backup generating capacity has in the past provided a reasonable level of energy reliability"; plans should cover "power disruptions that last for several days to weeks." |
| **S-FAA30J** | FAA, AC 150/5340-30J, *Design and Installation Details for Airport Visual Aids*, 12 Feb 2018, Ch. 9. https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-30J.pdf | §9.4.2.1: second source "within 15 seconds after interruption of the prime power, except that the essential visual aids for CAT II operations require a one-second changeover time." Configuration "B" uses "an alternate prime power source." Configuration "C" is a single source, and "standby power is not required". |
| **S-FAA6950** | FAA, Order JO 6950.2F, *Electrical Power Policy Implementation at National Airspace System Facilities*, effective 03 Apr 2024. https://www.faa.gov/documentLibrary/media/Order/JO_6950_2F.pdf | "Facilities that use one or more engine generators as a standby power system shall start at least one standby engine generator… and begin providing standby power within 15 seconds of a failure of the prime power source." Commercial power is the prime source in its power-source codes. |
| **S-EPRIPORT** | EPRI Journal, *Port of Entry for Electrification*. https://eprijournal.com/port-of-entry-for-electrification/ | "Since the 1970s, many ports around the country have converted the large ship-to-shore cranes used to load and unload cargo from diesel to electric power from the grid." |
| **S-NPC66** | National Petroleum Council, *Impact of Electric Power Outages on Petroleum Industry Facilities*, 19 July 1966. https://www.energy.gov/sites/default/files/2021-09/1966%20-%20Impact_of_Electric_Power_Outages_on_Petroleum_Industry_Facilities.pdf | Refinery power: "70.8% was found to be purchased from utilities and 29.2% self-supplied"; newer plants "essentially all electric". Removal from storage "is primarily dependent on electric pumps"; "gasoline pumps were dependent upon the system power supply." **This source is old.** Keep it as the mechanism source and look for a modern one. |
| **S-FL526** | Florida Statutes §526.143, *Alternate generated power capacity for motor fuel dispensing facilities* (2022). https://www.flsenate.gov/Laws/Statutes/2022/0526.143 | Terminals "must be capable of operating its distribution loading racks using an alternate generated power source for a minimum of 72 hours". Retail outlets must be "prewired with an appropriate transfer switch". |
| **S-LNG** | *LNG Import Terminals*, technical paper hosted by Cheresources (not peer-reviewed). https://www.cheresources.com/lng_terminals.pdf | "many facilities import power from the local grid to reduce capital cost expenditure"; "LNG terminals have small emergency generators to enable orderly shutdown in the event of a power supply failure." |
| **S-CMS** | 42 CFR §482.15(e), CMS Hospital Condition of Participation: Emergency preparedness (2016 rule). https://www.law.cornell.edu/cfr/text/42/482.15 | Generators must follow NFPA 99, NFPA 101 and NFPA 110 for location and for testing and maintenance. Hospitals with onsite fuel "must have a plan for how it will keep emergency power systems operational during the emergency, unless it evacuates." |
| **S-NFPA** | NFPA 110 (2019) and NFPA 99, as summarised in CSE Magazine, *The role of NFPA 110 and its interaction with other codes*. https://www.csemag.com/role-of-nfpa-110-and-interaction-with-other-codes/ | Level 1: "failure to perform could result in the loss of human life or serious injury"; "NFPA 99 requirement for Type 10 (10 seconds) systems for health care essential systems". Class X is "usually between 48 and 96 hours". The NFPA texts are paywalled and were read only through this secondary source. |
| **S-ACHC** | ACHC, *Ensuring Proper Storage and Temperatures for the Blood Bank*. https://achc.org/ensuring-proper-storage-and-temperatures-for-the-blood-bank/ | "Plan appropriately for a power outage or equipment downtime: An emergency generator, a continuously monitored unit, or validated coolers." |
| **S-TW-TP** | Taipower, *營業規章* (Business Regulations), Art. 46, via rootlaw. https://www.rootlaw.com.tw/LawArticle.aspx?LawID=A040100050007900-1110907 | Supply method is set by contract capacity ("用戶供電方式，按下表視其契約容量而定"). Voltage classes: low voltage 110/220/380 V; high voltage 3.3/11.4/22.8 kV; extra-high voltage 69/161/345 kV. **The capacity thresholds in Attachment 6 were not retrieved** (the Taipower PDFs were blocked). |
| **S-TW-HOSP** | 王榮坤, 〈停電時醫院該怎麼辦？〉, 科學月刊 no. 630, June 2022. https://www.scimonth.com.tw/archives/5737 | "院區的供電分別來自兩個不同的高壓電變電站" (the campus is fed from two different high-voltage substations); multiple 1,500 kW generators run in parallel; day tanks hold ≥12 h. |

## Rows

### power → telecom

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| exchange | core | distribution_substation | electricity | physical_flow | Switching, transmission and DC plant run on commercial AC. Loss is buffered, not avoided. | S-FCC07 (24 h central office rule, never in force); S-CPUC D.21-02-029; S-DOE | standard (a rule described it, but it never took effect; CPUC's rule is state-level) | Batteries plus a fixed generator. 24 h was the Katrina-panel target; 72 h under the CPUC rule in designated areas. | none found |
| mast | core | distribution_substation | electricity | physical_flow | A cell site has no generation of its own. In Hurricane Maria, power loss was the leading cause of cell-site outage. | S-GAO; S-FCC07 (8 h rule, never in force); S-CPUC D.20-07-011 | literature (GAO) + standard (CPUC, state-level) | Batteries for a few hours; some sites have generators. "several hours to one day" (GAO). 72 h in CA fire districts. | NCC funds backup power at remote base stations (news report; the page returned 403, so not verified) |
| data_centre | core | distribution_substation (enterprise/colo); **transmission_substation** (hyperscale/AI) | electricity | physical_flow | Runs on utility power in practice. Large facilities connect at transmission level. | S-NERC; S-UPTIME | literature (NERC white paper) | UPS (minutes) plus on-site gensets. Uptime treats gensets as the only reliable source, so the grid is an "economic alternative". | none found |
| cable_landing | core | distribution_substation | electricity | physical_flow | The landing station's DC plant feeds both its terminal gear and the power feeding equipment that drives the submerged repeaters. Losing the station takes the cable down. | S-NECPFE (mechanism only; grid supply not stated) | judgment (the dependence of the landing station on the grid is inferred; look for ICPC or an operator's landing-station design standard) | Battery plant plus a generator (judgment) | none found |

### power → water

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| reservoir | none | — | — | — | An upland impoundment delivers raw water by gravity. Outlet works do not need grid power for the water to flow. | none (reasoned) | judgment | n/a | Taiwan Water's upland dams (e.g. Feitsui, Shihmen) are gravity-fed to intakes (not verified) |
| treatment | core | distribution_substation; **transmission_substation** for large plants | electricity | physical_flow | Treatment processes, chemical dosing and high-lift pumps are all electric. The design standard requires standby power so treatment continues through an outage. | S-10SS §2.6; S-EPAPWR; S-AWWA | standard | A dedicated standby generator sized to average-day demand (10SS §2.6); plans for outages lasting "days to weeks" (AWWA) | none found. The 2025 Taoyuan water cut was maintenance, not power, so it is not usable here. |
| pumping | core | distribution_substation | electricity | physical_flow | Booster pumps are motor-driven; a pump station stops when it loses power. | S-10SS §6.3.4–6.3.5; S-EPAPWR | standard | Standby generator, or **a second independent substation** (10SS §6.3.5). The generator should pick one or the other. | none found |
| storage | none | — | — | — | Tanks and towers float on the system by gravity. They are the buffer against pump loss (10SS lets storage be reduced where standby power exists), not a power consumer. Telemetry loads are negligible. | S-10SS (storage and standby-power trade-off) | judgment | n/a (storage is the buffer) | none |

### power → transport

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| seaport | core | distribution_substation; **transmission_substation** for large container terminals | electricity | physical_flow | Ship-to-shore cranes are grid-electric, so cargo handling stops on power loss. Terminal operating systems and reefer yards also need power. | S-EPRIPORT | literature (trade journal; judgment on the transmission threshold) | Little: reefer and IT loads may have gensets; cranes generally do not (judgment) | Kaohsiung/Keelung/Taichung use electric cranes (not verified) |
| airport | core | distribution_substation; alternate prime feed (a second substation) for Configuration B | electricity | physical_flow | Airfield lighting, navaids and ATC run on commercial prime power, with a required second source. | S-FAA30J §9.4; S-FAA6950 | standard | Engine generator within 15 s (FAA); 1 s changeover for CAT II visual aids; Configuration C (small airports) has no standby | none found |
| freight_yard | optional | distribution_substation | electricity | physical_flow | Trucks move without grid power, but gates, lighting, warehouse systems and cold storage need it. The dependence is real only for mechanised or refrigerated yards. | none found | judgment | Gensets at cold stores (judgment) | none |
| bridge | none (Phase 1) | — | — | — | The Phase 1 rule says bridges consume nothing. That holds for fixed spans; movable spans need power (see Disagreements). | brief rule | judgment | — | — |
| road_junction | none (Phase 1) | — | — | — | Phase 1 rule. In reality, signalised junctions lose their signals (see Disagreements). | brief rule | judgment | Battery backup at some signals (judgment) | — |
| rail_node | none (Phase 1) | — | — | — | Phase 1 rule. In reality, electrified rail depends on traction power (see Disagreements). | brief rule | judgment | — | TRA trunk lines and HSR are electrified (not verified this session) |

### power → fuel

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| refinery | core | **transmission_substation** | electricity | physical_flow | Process units are "essentially all electric". Most power was purchased from the utility, with the rest self-generated. | S-NPC66 | literature (1966; needs a modern corroborating source such as a DOE/EIA refinery energy study) | Cogeneration or steam gives a partial buffer; emergency power allows an orderly shutdown | CPC Talin and Formosa Mailiao have large on-site generation (not verified) |
| tank_farm | core | distribution_substation | electricity | physical_flow | Moving product out of the tanks depends on electric pumps. | S-NPC66; S-FL526 (loading racks on alternate power for 72 h) | standard (FL statute) + literature | Loading racks on alternate power for 72 h, available within 36 h (FL) | none found |
| import_terminal | core | distribution_substation (oil); **transmission_substation** (LNG) | electricity | physical_flow | Unloading and send-out pumps are electric. LNG terminals use in-tank, send-out and seawater pumps, and "many" take their power from the grid. | S-LNG; S-NPC66 | literature (technical paper, not peer-reviewed) | LNG: "small emergency generators to enable orderly shutdown" only, so operations stop | CPC Yung-An and Taichung LNG (supply arrangement not verified) |
| depot | core | distribution_substation | electricity | physical_flow | Dispensing and loading pumps are electric. | S-NPC66; S-FL526 | standard (FL statute) | A transfer switch and generator where required (FL); otherwise none | none found |

### power → healthcare

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| tertiary | core | distribution_substation (two feeders from **two different substations**); transmission_substation possible for the largest campuses (not verified) | electricity | physical_flow | Life support, ORs, ICUs and imaging all run on grid power. Codes require an essential electrical system because of that dependence. | S-CMS; S-NFPA; S-TW-HOSP | standard | NFPA 110 Level 1, Type 10 (10 s), Class X (48–96 h typical); UPS for critical care; fuel plan (CMS) | Fed from two separate substations; 1,500 kW gensets in parallel; ≥12 h day tank (S-TW-HOSP) |
| regional | core | distribution_substation | electricity | physical_flow | Same mechanism at smaller scale. | S-CMS; S-NFPA | standard | Same Level 1 / Type 10 regime | none found |
| clinic | core | distribution_substation | electricity | physical_flow | Every clinic runs on grid power, but most have no life-support loads and can close when power is lost. | S-DOE | literature (sector level) | Often none. An essential electrical system is required only where patient-care spaces need one (e.g. general anaesthesia). | none found |
| blood_bank | core | distribution_substation | electricity | physical_flow | Refrigerated storage holds products in a narrow temperature band, and power loss threatens the inventory. | S-ACHC | literature (accreditor guidance) | Generator, a monitored unit or validated coolers (ACHC). Inside a hospital, blood refrigeration is on the critical branch (secondary source). | none found |

## Disagreements

1. **Phase 1 zero-consumption classes vs evidence.** The evidence says these three classes do consume power, which contradicts the brief's Phase 1 rule. The 21 couplings are unaffected because power → transport stays in, carried by the seaport and airport rows:
   - **rail_node:** electrified rail stops without traction power.
   - **road_junction:** signalised junctions go dark.
   - **bridge:** movable bridges cannot open.

   This is a scoping decision for the design side. I entered `none (Phase 1)` and did not change the rule.
2. **Power → water has two of four classes at `none`** (reservoir, storage). That is consistent with the coupling: it is carried by treatment and pumping. Storage is better modelled as the **buffer** on pumping loss than as a consumer.
3. **Backup-power "standards" for telecom are weak.** The FCC Katrina rule (24 h central offices, 8 h cell sites) **never took effect**. The only binding durations found are state-level (CPUC 72 h), so the buffer calibration should not cite FCC 07-177 as a requirement.
4. **Data centres.** Uptime says utility power is not required for a Tier rating. In practice the grid is the operating supply, so `core` stands. The buffer (UPS plus multi-day gensets) is the longest in the telecom layer.
5. No evidence was found for an excluded power edge. Power reaches all five layers as Appendix B says.

## Conditional on subtype (how to express it)

- **Supplier class by load size** (data_centre, treatment, seaport, refinery, import_terminal, tertiary): give each consumer node a `load_mw` attribute and the rule `load_mw ≥ threshold → transmission_substation, else distribution_substation`.
  - The threshold is a `placeholder (open decision: transmission_connection_threshold_mw)`.
  - Taiwan anchor: Taipower Art. 46 sets the supply voltage by contract capacity, with extra-high voltage at 69/161/345 kV. The Attachment 6 kW thresholds still need to be retrieved.
- **Self-generation share** (refinery, LNG import_terminal, data_centre): add a consumer attribute `self_generation_share ∈ [0,1]`. The dependency stays `core`, but a share above 0 lengthens the buffer or means only part of the load is lost. **Do not** make `generation` a supplier class for these; on-site generation belongs to the consumer, not the power layer.
- **import_terminal: LNG vs oil.** Both are `core`. LNG has the larger load (possibly transmission-connected) and only shutdown-grade emergency power.
- **airport: size and approach category.** Configuration C (single source, no standby) for small fields; A/B with 15 s standby for most; 1 s for CAT II aids. Express this as `airport_power_configuration ∈ {A, B, C}`.
- **freight_yard: refrigerated or mechanised.** Make it `core` if `cold_storage = true`; otherwise `optional`, driven by density.
- **clinic: essential electrical system.** The dependency is always `core`. Only the buffer varies: `has_essential_electrical_system: bool`.
- **seaport: container vs bulk.** Electric ship-to-shore cranes are specific to container terminals, so a bulk-only port could be `optional` (judgment).

## Open questions for the design side

1. Should Phase 1 add electrified `rail_node` and signalised `road_junction` as power consumers (Disagreement 1)?
2. What value should the transmission-connection threshold take, and should it be anchored to the Taipower Attachment 6 thresholds?
3. Should water `storage` be recorded as a buffer attribute of the pumping dependency instead of a `none` row?
4. Modern source still needed for refinery and terminal grid dependence to replace or corroborate NPC 1966.

---

<!-- file: lane_telecom.md -->
# Lane: TELECOM supplier layer (telecom → power, water, transport, fuel, healthcare)

21 rows (3 + 4 + 6 + 4 + 4). Sources are keyed S1–S18 and listed in full at the end; every one was fetched on 2026-09-29. Quotes are verbatim from the fetched page. Where the fetch returned a paraphrase, no quote is given.

**Supplier-class shorthand used below:**
- **exchange**: the central office or switching centre, and the fixed-line, leased-circuit and fibre services behind it.
- **mast**: cellular base stations (wireless primary or backup).
- **data_centre**: hosted applications (cloud EHR, port community systems, national insurance cloud).
- **cable_landing** serves no consumer class directly in any row. It reaches consumers only through exchange and data_centre, so it is left out of every supplier_classes cell. (Question Q1 below.)

**Typing convention used (see Q2):**
- **control**: loss removes a monitoring or command signal the facility's operation is steered by (SCADA, EMS, AGC, ATC voice and radar feeds, clinical information systems).
- **service**: loss removes coordination, documentation or commercial links, and the facility keeps running on a manual or paper fallback for days.

---

## telecom → power

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| generation | core | exchange; mast (backup path) | communications | control | The Generator Operator must hold voice communication with its Balancing Authority and Transmission Operator. Setpoints reach the plant as AGC signals over telemetry links. With the link lost, the plant keeps running but cannot be dispatched automatically. | S1 (COM-001-3 R8: the Generator Operator "shall have Interpersonal Communication capability with" its BA and TOP); S2 ("The loss of AGC prevents the system operator from automatically maintaining system frequency… and optimal generation levels.") | standard | No supply buffer. The plant runs at its last setpoint under local control. NERC reports EMS-loss events averaging ~73 min (S2), and COM-001 requires an alternative communication path. | Taipower dispatch runs through its central and area dispatch control centres (S13). Much of the path is likely on Taipower's own network; see D1. |
| transmission_substation | core | exchange | communications | control | RTUs send breaker status and analog telemetry to the control centre and receive open/close commands. Protection signalling (teleprotection) also rides on communications links. Without them the substation still operates, but it is invisible and can only be operated by staff sent to the site. | S2 ("SCADA sends and receives telemetered data between the RTU or ICCP link and the control center"; mitigation: "Manning substations during EMS events"); S3 (communications support "energy management, substation alarms… distribution automation, protection, and fault recording") | standard (S2 is a NERC reliability reference) + literature (S3) | Minutes to hours before faults pile up. The fallback is staff at the substation. | Taipower ADCC covers the 161/69 kV substations (S13). |
| distribution_substation | core | exchange; mast | communications | control | Distribution SCADA and distribution automation monitor the substation and its feeders and switch them remotely. Without it, fault isolation and restoration become manual truck rolls. | S3 (distribution automation listed among grid telecom functions); S13 (Taipower DDCC: "Monitor and control of automated switches, and devices within substation") | literature | Hours. Crews switch by hand. | Taipower's DDCS covers the 22 kV / 11 kV "second substations" island-wide (21 Siemens systems plus 1 SNC-Lavalin), so the row is core in a Taiwan-calibrated world. Small rural US co-ops may lack SCADA at every substation, but that is not the Taiwan case. |

## telecom → water

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| treatment | core | exchange (leased T1/MPLS, fibre); mast | communications | control | A treatment plant's SCADA links to the central control room and to the remote sites it feeds or draws from. Process control inside the plant is local. What loss of telecom removes is coordination with the system: set-points, levels and alarms. | S4 ("Wired technologies such as T1, TLS, MPLS, and utility-owned fiber optic are often used for data communications between major utility facilities"); S5 ("These networks can link monitoring and control systems for the treatment and distribution to a central display in the operations/control room") | literature (EPA guidance and the sector plan) | Long. The plant runs on local control with staff on site. Degradation is gradual. | Not found. Taiwan Water Corporation's SCADA arrangements were not verified. |
| pumping | core | mast; exchange | communications | control | Booster stations are usually unmanned and start and stop on telemetered tank levels. Without telemetry they fall back to local float or pressure logic, or to an operator sent to the site. | S4 ("wireless technologies are typically used for communicating with facilities where wired communication is not available or practical"; a case study found "cellular communications experienced considerably less downtime" after fibre cuts) | literature | Hours. Local automatic control continues, but the station is invisible to the control room. | — |
| storage | optional | mast; exchange | communications | control | A tank or tower consumes nothing. It only reports its level, which pumping control uses. Losing that signal degrades the pumps upstream, not the tank. Treat it as optional: it is the level telemetry point. | S4; S5 ("Some utilities have electronic networks") | judgment (mechanism from S4; no source states the level-reporting dependence as such) | The tank's own volume is the buffer. | — |
| reservoir | optional | mast; exchange | communications | control | Larger impoundments have remote gate and level monitoring and dam-safety telemetry. Small ones are run by hand. | S5 (only "some" utilities have networked monitoring; 83% of US community water systems are small or very small) | judgment | Very long. Gravity storage keeps flowing regardless. | — |

## telecom → transport

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| airport | core (towered and radar-served airports; see C1) | exchange (leased lines carrying radar data and radio to control positions); mast (none of the safety path) | communications | control | ATC voice frequencies and surveillance radar data reach the control positions over terrestrial telecom circuits. When those circuits are lost, traffic is ground-stopped or cut back at once. | S6 (FAA OIG AV2017020: the Chicago fire "destroyed critical FAA Telecommunications Infrastructure (FTI) equipment"; it "took… several days to complete the complicated task of re-routing Austin's surveillance radar data and radio frequencies"); S7 (FAA, 28 Apr 2025: "telecommunications and equipment issues at Philadelphia TRACON" led to "slowing arrivals and departures at Newark"); S8 (communications support monitoring and control of transportation infrastructure, e.g. ATC) | literature (government audit plus FAA statement) | Near zero, as the dissertation says. Recovery takes hours to days (S6). | Not verified. Taiwan's ANWS/CAA arrangements were not found. |
| seaport | core | exchange; data_centre (port community and terminal operating systems); mast | communications | service | Terminal operating systems, gate processing, cargo tracking and customs messaging all run over networks. Vessel traffic and pilotage use the port's own VHF radio, not the public telecom layer. Losing telecom pushes the port into manual gate processing and slows it over days rather than stopping it. | S9 (Kramek 2013: "Today, ports rely as much on computer networks as on human stevedores."; just-in-time flow "would grind to a halt in days") | literature | Long (days), on manual or paper fallback. This matches the dissertation. | — |
| freight_yard | core | exchange; mast; data_centre | communications | service | Truck dispatch, warehouse management and electronic documents need connectivity. Yards keep moving on phone and paper at reduced throughput. | S9 (by analogy: gate and cargo systems); no yard-specific source found | judgment | Long (days). | — |
| bridge | none | — | — | — | Phase 1 rule: consumes nothing. Movable bridges and toll/ITS equipment do use telecom (see D2). | brief | — | — | — |
| road_junction | none | — | — | — | Phase 1 rule. Signal coordination does use telecom, but signals fall back to local timing plans. | brief | — | — | — |
| rail_node | none | — | — | — | Phase 1 rule. **See D2**: rail signalling and dispatch are telecom-dependent, and the dissertation's own rationale names "rail on manual fallback". | brief | — | — | — |

## telecom → fuel

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| refinery | core | exchange | communications | service | The process is run by an on-site distributed control system, so loss of external telecom does not trip the plant. What is lost is pipeline nominations, remote pipeline SCADA hand-offs, and commercial scheduling of crude and product movements. | S10 (API 1164 3rd ed. covers "all control system cybersecurity" with protections "at pipelines, terminals, and refineries"): this establishes that the refinery control systems are networked, not that they depend on outside carriers | judgment (mechanism) + standard (scope only) | Long. Tank inventory absorbs the loss for days. | CPC refineries: not verified. |
| tank_farm | core (pipeline-connected); optional (truck- or rail-fed only) | exchange; mast | communications | control | Pipeline-connected bulk terminals are watched and valved from the pipeline control room over SCADA. When SCADA is lost the pipeline must run by hand, which the regulation requires to be planned and tested. | S11 (49 CFR 195.446 applies to "each operator of a pipeline facility with a controller… who monitors and controls… through a SCADA system"; operators must "Test and verify an internal communication plan to provide adequate means for manual operation of the pipeline safely"); S10 | standard | Hours. The pipeline slows or shuts in, with manual gauging as fallback. | — |
| import_terminal | core | exchange; mast | communications | control | Marine import terminals feed pipelines, or the gas grid for LNG send-out, under SCADA from the pipeline or grid control room. Their own safety communications are on-site and self-powered by rule, so they sit inside the facility and are not part of the telecom layer. | S11; S10; S12 (49 CFR 193.2519: the LNG plant "must have a primary communication system" and each system "must have an auxiliary source of power"; this is internal) | standard | Hours for send-out control. Storage on site buffers the supply. | CPC LNG terminals (Yong-An, Taichung) not verified. |
| depot | core | exchange; mast; data_centre | communications | service | Loading authorisation in terminal automation, order intake, card and fleet authorisation, and remote tank gauging all use connectivity. Depots keep loading on manual bills of lading. | S10 (terminals in scope of API 1164); no depot-specific source found | judgment | Long (days). | — |

## telecom → healthcare

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| tertiary | core | exchange; mast; data_centre (hosted EHR, HIE, imaging) | communications | control | Hospitals must hold primary and alternate communication paths to staff and emergency agencies. Clinical ordering, lab, pharmacy and imaging run on networked systems. A downtime disrupts care within hours, and lab results are delayed by 62%. | S14 (42 CFR 482.15(c)(3): "Primary and alternate means for communicating with…" staff and emergency agencies); S15 (Larsen et al. 2018: lab issues were 48.7% of downtime safety events; downtime procedures were absent or not followed in 46%); S16 (ASPR TRACIE: results "delayed by an average of 62%") | standard + literature | Hours. Paper downtime procedures, with degradation growing over time. An on-premise EHR survives a loss of outside telecom; a hosted EHR does not (C3). | NHI VPN: hospitals query patients' medication records "in realtime… via the NHI VPN system" (S17). A national cloud (data_centre) dependence is specific to Taiwan. |
| regional | core | exchange; mast; data_centre | communications | control | Same mechanism as tertiary. More likely to have a hosted EHR, which makes it more exposed to outside telecom. | S14; S15; S16 | standard + literature | Hours. | Same as tertiary (S17). |
| clinic | core | exchange; mast; data_centre | communications | control | Outpatient ordering, e-prescribing and insurance verification go through hosted services. Clinics can see walk-ins without connectivity but at reduced function. | S14 applies only to hospitals; the clinic analogue (CMS rules for other provider types) was not fetched. S17 | judgment (US); literature (Taiwan, S17) | Hours to days. | In Taiwan, NHI card verification, upload and MediCloud queries all run over the NHI VPN, so clinics depend on it by default (S17). |
| blood_bank | core | exchange; data_centre | communications | control | Blood centres run donor, labelling and distribution systems, and hospitals order by network or phone. A 2024 IT outage (not a telecom outage) forced manual labelling, caused shipping delays, and triggered shortage protocols at client hospitals. | S18 (AHA/Health-ISAC 2024: "forced the organization to resort to manual labeling of blood samples"; "causing major shipping delays") | judgment (the analogue is an IT failure, not a telecom one) | Days. Inventory on the shelf covers the gap. | — |

---

## Disagreements with the dissertation's rationale

- **D1: private utility networks.** Much of telecom → power, and some of telecom → water, rides on utility-owned fibre and microwave, not the public telecom layer. DOE says grid communications use "a mixture of private, utility-owned infrastructure and commercial leased infrastructure" (S3). The same report notes that utility devices fail "if any node in the communications path is left unpowered". Modelling every power and water class as served by the public exchange or mast overstates how much a public-telecom strike cuts off grid control. **Suggest** either a per-node share of the path that is leased (a recipe parameter), or accepting that the telecom layer includes utility private networks. This is a design decision; the 21 are unchanged.
- **D2: transport classes marked none.** rail_node, bridge (movable) and road_junction (signals) do depend on telecom in reality. Rail dispatch and signalling are the strongest case, and Appendix B itself says "long at ports and rail on manual fallback". Setting rail_node to none in Phase 1 contradicts that sentence. Either rail_node gets an optional telecom → transport row in a later phase, or the Appendix B wording drops "rail".
- **D3: where the dependence really comes from.** For refinery, and for hospitals with an on-premise EHR, the critical control system is local. The outside-telecom dependence is service or coordination, not control. The coupling itself holds, but its type differs by class, as set in the tables.
- No listed coupling lacks a real dependent. All five telecom couplings have core classes.

## Conditional on subtype

- **C1: airport.** Core only where there is ATC service (a towered airport or radar approach). An untowered airfield depends on telecom as optional service. Express it as the airport's size or tier attribute: `tower == true` → control/core, otherwise service/optional.
- **C2: tank_farm.** Pipeline-connected → control/core. Truck- or rail-fed only → service/optional. Express it with the node's pipeline_connected flag.
- **C3: tertiary, regional and clinic.** The EHR is hosted or on-premise. Hosted adds data_centre as a supplier and shortens the buffer. Express it as a hosted-EHR probability that rises down the tiers.
- **C4: generation.** The hydro and thermal subtypes do not change the dependency. Unmanned remote-operated hydro is, if anything, more dependent (judgment).

## Questions for the design side

- **Q1:** Is cable_landing ever a direct supplier in Phase 1? Or does it only feed exchange and data_centre within telecom? Every row here assumes the latter.
- **Q2:** The four types do not cleanly fit clinical IT. This lane typed healthcare as control, because the signal steers care within hours. Ports, freight yards, refineries and depots are typed as service, because they run on manual fallback for days. Please confirm.

## Sources (all fetched 2026-09-29)

- **S1** NERC, *COM-001-3 Communications* (Project 2015-07, 2016). https://www.nerc.com/pa/Stand/Reliability%20Standards/COM-001-3.pdf
- **S2** NERC RSTC, *Risks and Mitigations for Losing EMS Functions Reference Document*, Version 4, Sep 2024. https://www.nerc.com/comm/RSTC_Reliability_Guidelines/Risks_Mitigations_Losing_EMS_Functions_RefDoc.pdf
- **S3** US DOE Office of Electricity, *Power Grid and Communications Interdependencies: Key Challenges for Reliable, Resilient Operations*, Sep 2023. https://www.energy.gov/sites/default/files/2023-09/Electric%20Power%20Telecommunications%20Interdependencies.pdf
- **S4** US EPA, *Guidance for Designing Communications Systems for Water Quality Surveillance and Response Systems*, 2016. https://www.epa.gov/sites/default/files/2017-04/documents/srs_communications_guidance_081016.pdf
- **S5** DHS/EPA, *Water and Wastewater Systems Sector-Specific Plan*, 2015. https://www.cisa.gov/sites/default/files/publications/nipp-ssp-water-2015-508.pdf
- **S6** DOT Office of Inspector General, *FAA Responses to Major ATC System Disruptions*, AV2017020, 11 Jan 2017. https://www.oig.dot.gov/sites/default/files/FAA%20Responses%20to%20Major%20ATC%20System%20Disruptions%20Final%20Report%5E1-11-17.pdf
- **S7** FAA, *FAA Statements on Newark Liberty International Airport*, 2025. https://www.faa.gov/newsroom/faa-statements-newark-liberty-international-airport
- **S8** DHS, *Communications Sector-Specific Plan*, 2015 ("the Communications Sector is one of the few sectors that can affect all other sectors"). https://www.cisa.gov/sites/default/files/publications/nipp-ssp-communications-2015-508.pdf
- **S9** Kramek, J. (USCG), *The Critical Infrastructure Gap: U.S. Port Facilities and Cyber Vulnerabilities*, Brookings, 2013. https://www.brookings.edu/wp-content/uploads/2016/06/03-cyber-port-security-kramek.pdf
- **S10** American Petroleum Institute, *API Standard 1164, 3rd ed. (Pipeline Control Systems Cybersecurity)*, announcement 18 Aug 2021. https://www.api.org/news-policy-and-issues/news/2021/08/18/third-edition-of-api-standard-1164. The standard's text is paywalled; only the scope was verified.
- **S11** 49 CFR 195.446, *Control room management* (eCFR, current). https://www.ecfr.gov/current/title-49/subtitle-B/chapter-I/subchapter-D/part-195/subpart-F/section-195.446
- **S12** 49 CFR 193.2519, *Communication systems* (LNG facilities; eCFR, current). https://www.ecfr.gov/current/title-49/subtitle-B/chapter-I/subchapter-D/part-193/subpart-F/section-193.2519
- **S13** Taipower, *Smart Grid: Monitoring & Control, Distribution Dispatch Control Center (DDCC)*. https://smartgrid.taipower.com.tw/en/page.aspx?mid=57
- **S14** 42 CFR 482.15, *Condition of participation: Emergency preparedness* (hospitals; eCFR, current). https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482/subpart-B/section-482.15
- **S15** Larsen E., Fong A., Wernz C., Ratwani R.M., "Implications of electronic health record downtime: an analysis of patient safety event reports," *JAMIA* 25(2):187, 2018. https://academic.oup.com/jamia/article-abstract/25/2/187/3858892
- **S16** HHS ASPR TRACIE, *Electronic Health Records and Downtime Procedures* (resource collection). https://asprtracie.hhs.gov/technical-resources/66/electronic-health-records-and-downtime-procedures/0
- **S17** Taiwan National Health Insurance Administration, *NHI MediCloud System*. https://www.nhi.gov.tw/en/cp-1061-26881-124-2.html
- **S18** American Hospital Association and Health-ISAC, *Joint Threat Bulletin* (OneBlood ransomware), 1 Aug 2024. https://www.aha.org/advisory/2024-08-01-american-hospital-association-and-health-isac-joint-threat-bulletin-tlp-white

**Not verified; would look for:**
- Taiwan Water Corporation SCADA documents.
- CPC terminal automation.
- The Taiwan CAA/ANWS telecom arrangements for ATC.
- The text of AWWA J100 / G430.
- CMS emergency-preparedness rules for clinics (42 CFR 491.12).
- A yard- or depot-specific source.

---

<!-- file: lane_water.md -->
# Lane: WATER supplier layer

Four couplings: water → power, water → telecom (data-centre subset), water → fuel, water → healthcare. Every water row is `physical_flow` (water through a pipe). Source keys [S1]–[S18] resolve in the Sources section at the end, which gives the verified quote for each. Every source was fetched on 2026-09-29 unless marked *not fetched*.

## Which water node classes serve a consumer (applies to all rows)

- **Treated (potable) water** reaches consumers through the distribution network. The last named node upstream of a consumer is a **storage** tank or tower, or a **pumping** station. **Treatment** is upstream of both and serves a consumer directly only when the consumer sits on the plant's outlet main. Recommendation: attach each consumer to its nearest `storage` or `pumping` node, and carry `treatment` as the upstream path, not as a direct edge.
- **Raw water** runs from a **reservoir** to large industrial users (inland thermal plants, refineries) that treat their own water. It does not pass through `treatment`.
- **Seawater**, and private river or groundwater intakes, are outside the modeled water layer. Any consumer that takes its water from these has no edge for that flow.

## water → power

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| generation — thermal/LNG, **inland** | core | reservoir (raw water for cooling-tower make-up); storage/pumping (potable and service water) | water | physical_flow | Steam-cycle plants need cooling and boiler "production" water. Inland plants take cooling-tower make-up from fresh surface water, and the largest loss point is evaporation. | [S1] Table 4-1 ("Cooling and production water"); [S2] | literature | Raw-water pond and demineralized-water tanks; typically hours to days (judgment; no source verified) | Taipower's large thermal fleet is coastal (see next row), so inland thermal plants are rare |
| generation — thermal/LNG, **coastal (once-through seawater)** | core (low volume) | storage/pumping (potable); **not** reservoir | water | physical_flow | Cooling comes from the sea, outside the layer. The municipal feed still supplies boiler-feed make-up, pump seals, fire protection, potable use and sanitation. SDG&E's Encina plant cooled on ocean water but bought its fresh water from the local water district, and designed on-site desalination because that supply was unreliable in drought. | [S3] (Encina); [S4] (once-through saline systems withdrew ~22% of US thermoelectric water in 2015) | literature | Demineralized-water storage; some plants run on-site desalination, which removes the edge (see condition C1) | Taichung plant: "Cooling: Seawater" [S5]. Other Taipower coastal plants (Hsinta, Talin, Tunghsiao, Datan) are assumed similar; not verified |
| generation — **hydro** | none (conditional) | reservoir, only if co-sited | water | physical_flow | A hydro dam's head water is its own impoundment. It takes nothing from the treated-water system. Where one reservoir serves both water supply and hydro, the two share it, and water supply has priority. | [S6] (Feicui/Feitsui: "operated for water supply, with flood control and hydro power generation as secondary purposes") | literature | Reservoir storage itself | Feitsui Reservoir (Taipei water supply) hosts the 70 MW Gueishan hydro unit [S6][S7] |
| transmission_substation | none | — | — | — | Substations are air- or oil-cooled and use no process water. Some large substations have transformer deluge systems, but these are fire-protection-only and usually fed from on-site tanks. | none found | judgment | — | — |
| distribution_substation | none | — | — | — | No water in operation. | none found | judgment | — | — |

## water → telecom (data-centre subset only)

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| data_centre | core (conditional on cooling type; see C2) | storage/pumping (potable) | water | physical_flow | Evaporative cooling towers and water-cooled chillers consume water continuously. "The majority of data centers today use potable sources for onsite cooling, primarily from municipal utilities." Direct-to-chip, immersion and air cooling use "low to none". | [S8]; [S9] (cooling-system typology: water-cooled chillers and cooling towers vs dry coolers) | literature | On-site make-up water tanks; duration not verified (judgment: roughly 1–2 days) | None found |
| exchange | none | — | — | — | Mostly air-cooled equipment rooms, excluded by the coupling definition. Some large exchanges use water-cooled chillers. | none found | judgment | — | — |
| mast | none | — | — | — | No water use. | none found | judgment | — | — |
| cable_landing | none | — | — | — | A small powered building with air-cooled equipment. | none found | judgment | — | — |

## water → fuel

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| refinery | core | storage/pumping (potable, the typical case); reservoir (raw water) | water | physical_flow | A refinery uses about 1.5 bbl of water per bbl of crude, for cooling-tower make-up, boiler feed and process (desalter) water. About 60% of US refineries use municipal water, 15% groundwater, 10% river and 5% seawater once-through cooling. OSHA requires refineries to have water "available in volume and at adequate pressure" for fire control. | [S10]; [S11] 29 CFR 1910.106(i)(5)(ii) | standard (fire water) + literature (process water) | Raw-water and fire-water tanks or ponds; not quantified | None found (CPC refineries are coastal; water source not verified) |
| tank_farm | optional | storage/pumping (hydrant and fire water) | water | physical_flow | There is no process water. Fire water is the only need. OSHA bulk-plant rules require only "suitable fire-control devices", with more required for large tanks. Many tank farms use their own fire-water tanks or seawater. | [S11] 29 CFR 1910.106(f)(8) | standard | On-site fire-water tank | None found |
| import_terminal | optional (conditional on subtype; see C3) | storage/pumping (potable, fire water) | water | physical_flow | LNG terminals regasify with seawater (open-rack vaporizers draw 90,000–125,000 gpm), which is outside the layer. Their fire mains are required, but the source is not specified. Oil import terminals need fire water and potable water only. | [S12]; [S13] 33 CFR 127.607 | standard + literature | Fire-water tanks; seawater fire pumps at marine sites | CPC Yung-An and Taichung LNG terminals are coastal; details not verified |
| depot | optional | storage/pumping (hydrant) | water | physical_flow | A bulk plant with no process water. Fire-fighting relies on extinguishers and hydrants where available. | [S11] 1910.106(f)(8) | standard | None | — |

## water → healthcare

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| tertiary | core | storage/pumping (potable); treatment where on the main | water | physical_flow | Hospitals use water for drinking, hand hygiene, food, patient care, fire sprinklers, dialysis, reprocessing of medical equipment, water-cooled medical-gas and suction compressors, HVAC and IT cooling. CMS requires planning for water as a subsistence need. Loss "could lead to healthcare facility evacuation". | [S14]; [S15] 42 CFR 482.15(b)(1)(i); [S16] | standard | Little on-site storage is typical. Planning relies on restricted use plus trucked water or bulk storage (the guide's case study: 7.2 days on 2 Mgal under restriction) | During TWC rationing, "inpatient hospitals recognized by the MOHW" can apply for medical water withdrawal stations [S17] |
| regional | core | storage/pumping | water | physical_flow | Same mechanism as tertiary. | [S14]; [S15] | standard | As tertiary | As tertiary |
| clinic | core | storage/pumping | water | physical_flow | Hand hygiene, instrument reprocessing and sanitation stop without water. Outpatient dialysis clinics are named as water-critical. A water main break has shut a dialysis centre. | [S14] (scope "Hospitals and Healthcare Facilities"; Appendix F, Dialysis); [S18] *(news, not fetched)* | literature | Minimal; clinics close | — |
| blood_bank | optional | storage/pumping | water | physical_flow | Stored blood depends on power (refrigeration), not water. Collection and component processing need sanitation and laboratory water, so they stop, but issue from inventory continues for days. | none found | judgment | Inventory buffer (days) | — |

## Conditions to express (subtype-dependent rows)

- **C1. Thermal generation cooling mode.** Add a node attribute `cooling_source ∈ {sea_once_through, fresh_recirculating}`. Set it to `sea_once_through` when the plant is coastal.
  - `fresh_recirculating`: edges from `reservoir` (raw) and from `storage`/`pumping`, with a large requirement.
  - `sea_once_through`: an edge from `storage`/`pumping` only, with a small requirement (make-up, potable and fire water) and a longer buffer.
  - A third value, `on_site_desalination`, would remove the edge entirely. Flagged for the design side, not proposed as a default.
- **C2. Data-centre cooling.** Add `cooling_type ∈ {evaporative, dry_or_liquid}`. The dissertation's "compute data centers … with heavy inbound … water couplings" implies `evaporative`, so treat that as the default. With `dry_or_liquid` the edge drops to none.
- **C3. Import terminal fuel.** For `lng` terminals, vaporization water comes from the sea, so the edge is fire and potable water only. For `oil` terminals the edge is the same. Both are optional. The *magnitude* is small either way.
- **C4. Hydro.** A water edge exists only when the hydro node is co-sited with a water-layer `reservoir`. The shared reservoir should be modeled as one node with an allocation priority: water supply first, per [S6].

## Disagreements

1. **Water → power at coastal plants is real but thin.** The dissertation's "water to power" supply cross-feed reads as bulk cooling water. For once-through seawater plants, which include Taiwan's largest (Taichung [S5]), the bulk flow is outside the water layer. What remains is a low-volume dependency on municipal water for make-up, potable and fire use [S3]. Keep the coupling, but for coastal plants the requirement should be small and the buffer long. If the world treats every thermal plant as a heavy water consumer, it overstates the coupling for Taiwan.
2. **Water → fuel is concentrated at refineries.** Tank farms, depots and LNG terminals need water mainly for fire protection. LNG vaporization water is seawater [S12]. About a quarter to a third of refineries self-supply from wells, rivers or the sea [S10], which the modeled layer cannot represent.
3. **Water → transport is excluded, but a weak dependency exists.** Airports and seaports need potable water, fire-fighting hydrant water and, at ports, ship water supply. This is not sourced (judgment). The exclusion is defensible as low criticality, but it is not "no dependency".
4. **Exchanges with water-cooled chillers** would break the data-centre-only rule. This is judgment only, and the rule is left unchanged.

## Sources (verified quotes)

- [S1] U.S. DOE, *Energy Sector-Specific Plan 2015* (DHS/CISA NIPP series). https://www.cisa.gov/sites/default/files/publications/nipp-ssp-energy-2015-508.pdf. Table 4-1 lists Water → Electricity as "Cooling and production water". The plan also says the sector "depends on many other critical infrastructure sectors, such as transportation, … communications, water …".
- [S2] U.S. EIA, "Over half the cooling systems at U.S. electric power plants reuse water", *Today in Energy*, 17 Nov 2011. https://www.eia.gov/todayinEnergy/detail.php?id=3950. "In a once-through system, intake structures withdraw water, which is then run through the power plant for cooling … discharged back into the body of water." "Evaporation from a nearby cooling tower removes heat from the power plant."
- [S3] Boyle Engineering Corp. for San Diego Gas & Electric, *Drought-Proofing Through Desalting: The San Diego Gas & Electric Approach*, June 1995 (Appendix S, San Diego Regional Water Quality Control Board). https://www.waterboards.ca.gov/sandiego/water_issues/programs/regulatory/docs/appendices/Appendix_S.pdf. "Ocean water via the Agua Hedionda Lagoon is used for cycle cooling." "Fresh water needs are purchased from the local water district and potable uses include drinking; landscape irrigation, fire protection, and sanitation. Non-potable uses include boiler feed make up, condenser cleaning, pump sealing …"
- [S4] Harris, M.A. & Diehl, T.H., *Withdrawal and Consumption of Water by Thermoelectric Power Plants in the United States, 2015*, USGS SIR 2019-5103, 2019. https://pubs.usgs.gov/sir/2019/5103/sir20195103.pdf. "Once-through saline-water systems withdrew about 23 Bgal/d", out of about 103 Bgal/d total.
- [S5] Power Technology, "Taichung Coal-Fired Power Plant" (project profile). https://www.power-technology.com/projects/taichung/. "Cooling: Seawater". Trade press, not primary. The Taipower primary pages (taipower.com.tw) returned 403 and could not be verified.
- [S6] Wikipedia, "Feicui Dam". https://en.wikipedia.org/wiki/Feicui_Dam. "The reservoir is operated for water supply, with flood control and hydro power generation as secondary purposes." Tertiary source; see [S7] for the primary.
- [S7] Taipei Feitsui Reservoir Administration, "Profile". https://english.fra.gov.taipei/cp.aspx?n=C4C00243F04D1C41. "Installed Capacity: 70,000 kW".
- [S8] Environmental Law Institute (with the Tulane Institute on Water Resources Law & Policy), *Data Centers and Water Fact Sheet*, Jan 2026. https://www.eli.org/sites/default/files/files-pdf/Data%20Centers%20and%20Water%20Fact%20Sheet%20ELI%20January%202026%20(1).pdf. "The majority of data centers today use potable sources for onsite cooling, primarily from municipal utilities." Direct-to-chip, immersion and air cooling are listed as "Low to none" water use.
- [S9] Shehabi, A. et al., *2024 United States Data Center Energy Usage Report*, LBNL-2001637, Lawrence Berkeley National Laboratory, Dec 2024. https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf. Covers water-cooled chillers, cooling towers and waterside economizers, against "dry coolers [that] reject heat to the ambient air". It does not state the water's source. The peer-reviewed Siddik, Shehabi & Marston (2021), *Environ. Res. Lett.* 16:064017, is a stronger citation but was not fetched (robots-blocked).
- [S10] Weaver, L.E., Henderson, R. & Blieszner, J. (Jacobs Consultancy) for U.S. DOE, *Potential Vulnerability of US Petroleum Refineries to Increasing Water Temperature and/or Reduced Water Availability*, Jan 2016. https://www.energy.gov/sites/prod/files/2016/03/f30/US%20DOE%20Refinery%20Water%20Study.pdf. "A typical refinery will use about 1.5 barrels of water to process 1 barrel of crude oil." Water sources: about 60% municipal, 15% groundwater, 10% river, 5% seawater once-through, under 5% lake (multiple sources allowed). "Water evaporation from the cooling towers is the primary loss point inside a plant."
- [S11] OSHA, 29 CFR 1910.106, *Flammable liquids* (eCFR, current). https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1910/subpart-H/section-1910.106.
  - Refineries, (i)(5)(ii): "Water shall be available in volume and at adequate pressure to supply water hose streams, foam producing equipment, automatic sprinklers, or water spray systems as the need is indicated by the special hazards of operation and storage."
  - Bulk plants, (f)(8): "Suitable fire-control devices, such as small hose or portable fire extinguishers, shall be available … Additional fire-control equipment may be required where a tank of more than 50,000 gallons …"
- [S12] Center for Energy Economics, Bureau of Economic Geology, UT Austin, *Offshore LNG Receiving Terminals* (briefing paper), 2006. https://www.beg.utexas.edu/files/cee/legacy/CEE_offshore_LNG.pdf. "… heat exchange between the LNG … and a falling film of seawater …" "ORVs use approximately 90,000 to 125,000 gpm …"
- [S13] U.S. Coast Guard, 33 CFR 127.607, *Fire main systems* (Waterfront Facilities Handling LNG). https://www.ecfr.gov/current/title-33/chapter-I/subchapter-L/part-127/subpart-B. "Each marine transfer area for LNG must have a fire main system that provides at least two water streams to each part of the LNG transfer piping and connections." The water source is not specified.
- [S14] CDC & AWWA, *Emergency Water Supply Planning Guide for Hospitals and Healthcare Facilities*, 2012, updated 2019. https://www.cdc.gov/water-emergency/media/pdfs/2024/07/emergency-water-supply-planning-guide-2019-508.pdf.
  - Water uses listed include drinking, hand hygiene, food preparation, patient care, fire suppression sprinkler systems, dialysis, reprocessing of medical equipment, "water-cooled medical gas and suction compressors", HVAC and IT cooling.
  - It cites Joint Commission Standard EM.02.02.09, which "requires hospitals to identify alternative means of providing water needed for consumption and essential care activities, and water needed for equipment and sanitary purposes."
  - Appendix F covers dialysis.
  - The standard number is as cited in the 2019 guide. The Joint Commission has since renumbered its emergency-management chapter; the current number was not verified.
- [S15] CMS, 42 CFR 482.15(b)(1), *Condition of participation: Emergency preparedness* (hospitals). https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482/subpart-B/section-482.15. "The provision of subsistence needs for staff and patients, whether they evacuate or shelter in place, including … (i) Food, water, medical, and pharmaceutical supplies."
- [S16] HHS ASPR TRACIE, *Utility Failures* topic collection. https://asprtracie.hhs.gov/technical-resources/35/utility-failures/0. "Losing power or water can have serious effects on communities, healthcare facilities, staff, and patients. Either situation could lead to healthcare facility evacuation." It lists case studies: MedStar Washington Hospital Center (2018), Jackson MS (2022), and HCA Houston Tomball (Winter Storm Uri).
- [S17] Taiwan Water Corporation, news item on district intermittent supply (Miaoli, Taichung, northern Changhua), 3 Jul 2025. https://www.water.gov.tw/en/Subject/Detail/55185?nodeId=5888.
  - "Inpatient hospitals recognized by the Ministry of Health and Welfare (MOHW) can download" applications for medical water withdrawal stations.
  - The "5-day supply and 2-day cut-off" schedule lets most homes and factories "rely on storage tanks". This supports on-premises storage as the typical Taiwan buffer.
- [S18] Eagle-Tribune, "Water main break shuts down dialysis center in Methuen". https://www.eagletribune.com/news/merrimack_valley/water-main-break-shuts-down-dialysis-center-in-methuen/article_71386acd-8738-5263-b6f3-8325665456c9.html. *Found by search, not fetched*; cite only after checking.

### What was looked for and not verified

- Taipower's own statement on seawater cooling and on the source of boiler make-up water at its coastal plants (taipower.com.tw returned 403). A Taipower plant environmental page or EIA report (環評) would settle C1 for Taiwan.
- The NFPA 30 / NFPA 59A fire-water supply clauses: the full text is paywalled, so OSHA and USCG were used instead.
- A source for data-centre on-site water storage duration.
- Any Taiwan data-centre water-sourcing source.

---

<!-- file: lane_transport.md -->
# Lane: TRANSPORT supplier layer (transport → fuel, transport → healthcare)

Supplier classes available (author's ruling): seaport, airport, freight_yard. Bridges, road junctions and rail nodes are not supplier classes here. freight_yard stands for road haulage (tank trucks, supply trucks).

All sources below were fetched and read in this session unless marked otherwise. Quotes are verbatim from the fetched text.

## Sources used (key)

- **[S1]** U.S. EIA, *Taiwan Country Analysis Brief*, last updated April 2026. https://www.eia.gov/international/content/analysis/countries_short/Taiwan/Taiwan.pdf. Quotes: "Taiwan's crude oil imports come in through three ports: Mai Liao (55% in 2025), Kaohsiung (30% in 2025), and Shalung (15% in 2025)." "Taiwan has three liquefied natural gas (LNG) regasification terminals…". Refinery capacities: Kaohsiung 270,000 b/d; Taoyuan 200,000; Dalin 400,000; Mailiao 540,000.
- **[S2]** Boone, M., "Securing Taiwan's Black Gold: A Crude Analysis," *Global Taiwan Brief*, Global Taiwan Institute, 6 Sep 2023. https://globaltaiwan.org/2023/09/securing-taiwans-black-gold-a-crude-analysis/. Quotes: "Taiwan is 99.75 percent reliant on imported petroleum"; the Taoyuan Refinery "sources its crude oil from the Shalun fuel depot."
- **[S3]** CPC Corporation, Taiwan, *Downstream Operations* (web page, 2021 data). https://www.cpc.com.tw/en/cp.aspx?n=2610. Quotes: "approximately 2,221 kilometers of terrestrial trunk pipeline, extending from Pingtung in the south to Keelung in the north"; "14 product distribution centers located country-wide at Keelung, Shimen, Hsinchu, Taichung, Taichung Harbor, Wangtian, Minxiong, Tainan, Fengde, Qiaotou, Suao, Hualien, Huxi, Kinmen and Matsu."
- **[S4]** U.S. EIA, *Diesel fuel explained: Where our diesel comes from* (web page, current). https://www.eia.gov/energyexplained/diesel-fuel/where-our-diesel-comes-from.php. Quotes: "Most diesel fuel moves by pipeline from refineries and ports to terminals near major consuming areas. Barges and trains also move diesel fuel to terminals." "Trucks transport the diesel fuel from the terminals to retail service stations and to large-volume consumers such as vehicle-fleet operators."
- **[S5]** Petroleum Administration Act (Taiwan), Art. 24, English text, Laws & Regulations Database of the ROC. https://law.moj.gov.tw/ENG/LawClass/LawAll.aspx?pcode=J0020019. Quote: "Oil refinery operators and importers are required to maintain an oil security stockpile of no less than sixty days of supply."
- **[S6]** McGillis & Yu, "Assessing Taiwan's Strategic Energy Stockpiles," *Global Taiwan Brief*, 4 May 2022. https://globaltaiwan.org/2022/05/assessing-taiwans-strategic-energy-stockpiles/. Quote: LNG terminals "at the moment have the ability to store less than two weeks' worth of reserve supply."
- **[S7]** FEMA, *Community Lifelines Implementation Toolkit* v2.0, 2020 (fetched from mirror https://ruraltraining.org/wp-content/uploads/2020/06/CommunityLifelinesToolkit2.0v2.pdf; FEMA original https://www.fema.gov/sites/default/files/2020-05/CommunityLifelinesToolkit2.0v2.pdf returned 403). Health and Medical lifeline component "Medical Supply Chain (Blood/Blood Products, … Pharmaceutical, Device, Medical Gases, Distribution …)"; Energy lifeline Fuel component "Refineries/Fuel Processing, Fuel Storage, Pipelines, Fuel Distribution". Quotes: "Medical supply chain capable of adequately resupplying medical care providers." "Multimodal routes (air, rail, road, port) are clear of debris and accessible by normal or alternate means."
- **[S8]** National Academies of Sciences, Engineering, and Medicine, *Strengthening Post-Hurricane Supply Chain Resilience: Observations from Hurricanes Harvey, Irma, and Maria*, NAP, 2020, ch. "Overview of Supply Chain Impacts from the 2017 Hurricanes." https://www.ncbi.nlm.nih.gov/books/NBK556352/. Quotes: "Cargo was able to make it to the port, but due to the sustained power outage, goods coming in could not be processed effectively, and due to blocked roads and shortages of trucks and drivers, many goods could not be removed from the port area." Also notes "problems with supply and distribution of medical oxygen, which could not be produced locally due to lack of power and which faced many barriers in being shipped to the island."
- **[S9]** Kim, K. & Bui, L., "Learning from Hurricane Maria: Island ports and supply chain resilience," *International Journal of Disaster Risk Reduction* 39 (2019) 101244. https://doi.org/10.1016/j.ijdrr.2019.101244. Quote: "Isolation, limited port capacity, lack of alternative facilities and dependence on imports increase the vulnerability of island communities."
- **[S10]** Qureshi, K., Gershon, R.R., Sherman, M.F., et al., "Health care workers' ability and willingness to report to duty during catastrophic disasters," *Journal of Urban Health* 82(3) (2005). https://doi.org/10.1093/jurban/jti086 (PMID 16000654; abstract read via Europe PMC). Quote: "Barriers to ability included transportation problems, child care, eldercare, and pet care obligations." Ability to report in a severe snow storm: 49%.
- **[S11]** Wassmer, J., Bryant, S., Schimansky, P., et al., "Unveiling hidden risks in healthcare from flood-induced transportation disruption in Germany," *Communications Earth & Environment* (2025). https://www.nature.com/articles/s43247-025-02645-y. Quote: "flood-induced road damage can cause widespread supply chain disruptions, delayed medical evacuations, and overwhelm hospitals."
- **[S12]** DeMasters, T., "Big Island: Volunteers Work To Shore Up Blood Supply," *Honolulu Civil Beat*, 27 Sep 2019. https://www.civilbeat.org/2019/09/big-island-volunteers-work-to-shore-up-blood-supply/. Quotes: "A supply of these products is flown to the neighbor islands almost daily." "It could take up to 24 hours to get blood products to the Big Island in those circumstances." (News report, not peer-reviewed.)
- **[S13]** Wu, M.Y., Li, C.J., Hou, Y.T., et al., "Analysis of emergency air medical services over 9 years in the Penghu archipelago of Taiwan," *Tzu Chi Medical Journal* (2020). https://doi.org/10.4103/tcmj.tcmj_216_18 (abstract read via Europe PMC). 1,228 patients were moved from Penghu to Taiwan by helicopter and C-130 in 2009–2017.
- **[S14]** Chinese Blood Donation Movement Association, "快樂捐血，愛在金門" (Happy blood donation, love in Kinmen), updated 4 Jan 2021. https://www.cbda.org.tw/magazine/Post/829?vol=38. Quote: "以船運方式將捐血車整台運輸過去" (the bloodmobile is shipped over whole by sea), with collection run by the Taipei Blood Center twice a year.
- **[S15]** 42 CFR 482.15(b)(1) (CMS Emergency Preparedness Condition of Participation, hospitals), eCFR. https://www.ecfr.gov/current/title-42/section-482.15. Quote: "The provision of subsistence needs for staff and patients, whether they evacuate or shelter in place, include, but are not limited to the following: (i) Food, water, medical, and pharmaceutical supplies."

## Rows: transport → fuel

| coupling | consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|---|
| transport → fuel | import_terminal | core | seaport | transport access (berth, channel, tanker/LNG-carrier calls) | logistic | A marine import terminal exists to receive tankers or LNG carriers, and it cannot receive anything without the seaport's berth and approaches. Outbound it is mostly pipeline-fed (LNG send-out is gas pipeline), so the dependency is on the receiving side. | S1 (the three crude ports, three LNG terminals); S4 ("…from refineries and ports to terminals…"); S7 (Maritime: "Ports and Port Facilities") | literature | Tankage on site: oil importers hold ≥60 days' stock by law (S5, stockpile held across the company, not necessarily at the terminal); LNG terminals hold "less than two weeks" (S6). | Taiwan imports 99.75% of its petroleum (S2); all crude lands at Mai Liao, Kaohsiung or Shalung (S1). LNG terminals are the thinnest buffer. |
| transport → fuel | refinery | core (coastal refinery with its own berth or mooring); none directly (inland refinery fed by crude pipeline) | seaport | transport access (crude tanker receipt) | logistic | In an import-dependent island every barrel of crude arrives by sea. Coastal refineries berth tankers themselves. An inland refinery is fed by pipeline from a port-side import terminal or tank farm, so its transport dependency runs through that node (fuel → fuel, not modeled) rather than directly. | S1 (ports; four refineries); S2 (Taoyuan refinery "sources its crude oil from the Shalun fuel depot") | literature | Crude and product tankage; ≥60 days of supply required of refiners (S5). | Mailiao (Formosa) and Dalin/Kaohsiung (CPC) are coastal; Taoyuan (CPC) is inland, fed from Shalun (S1, S2). Conditional on siting (see Conditions). |
| transport → fuel | tank_farm | optional | seaport (coastal tank farm with jetty); freight_yard (truck loading rack) | transport access | logistic | Bulk storage is mostly filled and drawn by pipeline, which is not transport. It depends on transport only when it has a jetty (fed by coastal tanker or barge) or a truck rack (drawn by road). | S4 ("Most diesel fuel moves by pipeline… to terminals"; "Barges and trains also move diesel fuel to terminals"); S3 (2,221 km trunk pipeline) | literature | Days to weeks of stock by design. | CPC's trunk pipeline (Pingtung to Keelung) links refineries to its storage and distribution centres (S3), so main-island tank farms are mostly pipeline-fed. |
| transport → fuel | depot | core | freight_yard (road haulage, the depot's outbound tank-truck dispatch and any truck-fed inbound); seaport (offshore-island depots fed by coastal tanker) | transport access | logistic | A depot's job is to load tank trucks for filling stations and large users, so it is useless without road haulage even when its inbound supply comes by pipeline. Offshore-island depots also receive by sea. | S4 ("Trucks transport the diesel fuel from the terminals to retail service stations and to large-volume consumers…"); S7 (Fuel Distribution component) | literature | A few days of throughput in tankage (judgment; no source found). | CPC distribution centres at Kinmen and Matsu (S3) cannot be pipeline-fed from Taiwan; that they are fed by coastal tanker is judgment (no source fetched). Main-island centres are on the trunk pipeline, so their inbound is pipeline and only outbound truck dispatch uses transport. |

airport serves no fuel class. Airports are fuel consumers (CPC runs aviation fuelling stations at eight airports, S3), which is fuel → transport, not this coupling.

## Rows: transport → healthcare

| coupling | consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|---|
| transport → healthcare | tertiary | core | freight_yard (road haulage of pharmaceuticals, devices, medical gases, linen, food); seaport and airport (upstream imports into an island) | transport access (resupply) | logistic | Hospitals run on continuous resupply by truck from distributors, and on an island those goods first cross a port or airport. After Maria, goods reached the port but blocked roads and a shortage of trucks kept them there. | S7 ("Medical supply chain capable of adequately resupplying medical care providers"); S8 (quote above); S9; S11 | literature | CMS requires plans for "medical, and pharmaceutical supplies" while sheltering in place (S15), but sets no day count. Typical on-hand stock is days (judgment). | Taiwan imports most drugs and devices by sea and air (judgment; no Taiwan source fetched). Offshore-island tertiary transfer is by air: Penghu to Taiwan by helicopter and C-130 (S13). |
| transport → healthcare | regional | core | freight_yard; seaport and airport upstream | transport access (resupply) | logistic | Same mechanism as tertiary, with smaller stocks and more reliance on scheduled distributor runs. | S7; S8; S9; S11 | literature | As tertiary (S15). | Offshore-island regional hospitals (Penghu, Kinmen, Matsu) depend on air and sea for resupply and patient transfer out (S13). |
| transport → healthcare | clinic | core | freight_yard | transport access (resupply) | logistic | Clinics hold small stocks and restock from distributors by road. Consumption is low, so the buffer is long, but the dependency is universal. | S7; S11 ("reduce access to critical healthcare services") | literature (mechanism); judgment (that it is universal for clinics) | Longest buffer of the four classes, days to weeks (judgment). | None found. |
| transport → healthcare | blood_bank | core | freight_yard (road courier to hospitals, collection runs); airport (islands, optional by setting); seaport (islands, bloodmobile or bulk moves, optional) | transport access (blood-product distribution, cold chain) | logistic | Blood products have short shelf life (platelets are kept about 5 days; not verified this session) and move daily from the blood centre to hospitals. Islands without their own processing are resupplied by air. | S7 (Medical Supply Chain: "Blood/Blood Products"); S12 ("flown to the neighbor islands almost daily"; up to 24 h for urgent top-up) | literature (S12 is a news report; the mechanism is uncontroversial) | Hospital transfusion-service inventory of days (judgment). | Kinmen collection is run by the Taipei Blood Center, whose bloodmobile goes over by ship (S14). That processed units for Penghu, Kinmen and Matsu move by air was not verified (Chinese searches found nothing fetchable), so the airport link is judgment for Taiwan. |

## Conditions (subtype-dependent rows)

1. **refinery, by siting.** Add an attribute `crude_receipt ∈ {marine, pipeline}`. marine gives core on seaport. pipeline gives none directly; the transport exposure is carried by the upstream import_terminal or tank_farm. Default for an island world: marine. Taiwan: 3 marine, 1 pipeline (Taoyuan).
2. **tank_farm, by access.** `has_jetty` gives a seaport edge and `has_truck_rack` gives a freight_yard edge. Neither gives none. This is the density-driven optional edge.
3. **depot, by location.** Main-island depots are pipeline-in and truck-out, so the core edge is freight_yard only. Depots on offshore islands add a seaport edge. Express this as `on_offshore_island` (or no pipeline connection to a refinery or tank farm).
4. **import_terminal, LNG vs oil.** Both are core on seaport. They differ in buffer (LNG under two weeks against oil's statutory 60 days, S5/S6) and in outbound (LNG goes out by gas pipeline, oil by pipeline or truck), not in dependency.
5. **healthcare on offshore islands.** Every healthcare class gains an airport edge (blood products, urgent supplies, patient transfer) and a seaport edge (bulk resupply). Express this with `on_offshore_island` or `road_connected_to_mainland = false`. On the main island the core edge is freight_yard only, and seaport and airport sit upstream of the freight yards rather than feeding hospitals directly.

## Disagreements and flags

1. **Staff access is service, not logistic, and does not run through any permitted supplier class.** The brief lists staff access as a mechanism for transport → healthcare, and S10 finds "transportation problems" the leading barrier to reporting (49% able to report in a severe snow storm). But staff reach hospitals over roads, bridges and rail (road_junction, bridge, rail_node), which the author's ruling does not allow as supplier classes, and the dependency type would be service. With one type per row I graded the rows logistic (resupply). Decision needed: either accept that staff access is not modeled in Phase 1, or allow road_junction, bridge and rail_node as suppliers of a service-type edge.
2. **freight_yard as a stand-in for road haulage.** Real tank trucks and medical distributors run from company yards and distribution centres, not a generic "truck warehouse and yard". The stand-in is defensible, but a freight_yard outage in the model will overstate loss (real fleets reroute) unless the road network carries the flow. Flag for the solver: this is a node standing in for a network.
3. **rail.** In the US, rail and barge move fuel to terminals (S4). In Taiwan no rail fuel movement was found. rail_node is not a supplier class, which is fine for Taiwan but would be wrong for a continental setting.
4. **Pipeline-fed fuel nodes.** The evidence says most bulk fuel movement between refinery, tank farm and depot is by pipeline (S3, S4), which is a fuel → fuel or physical_flow path and not transport. The transport → fuel coupling is real (import terminals, coastal refineries, depot outbound), but it is narrower than "tanker-truck distribution from terminals and tank farms to depots" suggests. On Taiwan's main island, depots are pipeline-fed inbound.
5. **Excluded transport → water, transport → power.** Nothing in this lane contradicts those exclusions. Out of lane, note that Taiwan's coal and LNG power plants depend on seaports as heavily as refineries do (S1 for LNG), so the exclusion of transport → power (coal delivery) deserves a sentence of justification in Appendix B.

## Could not verify
- The FEMA original PDF (403); I used a third-party mirror of the same v2.0 toolkit (same title and version). Check it against fema.gov before citing.
- PubMed was rate-limited; the abstracts were read via Europe PMC.
- The Penghu blood-supply news item (Liberty Times, 403) and the IBMS remote-island lab article (403). Air transport of blood to Taiwan's offshore islands is therefore judgment.
- CISA HPH Sector-Specific Plan PDF (403), so there is no CISA quote on healthcare's dependence on transportation.

---

<!-- file: lane_fuel.md -->
# Lane: FUEL supplier layer: node-class dependency rows

Five couplings: fuel → power, telecom, water, transport and healthcare. There is one row per consumer class, 21 rows in total. Source keys such as [S6] point to the list at the end. I opened every source listed there this session (by fetch or by downloading the PDF). Where a sentence is in quotation marks, it was read in the fetched text.

## The key ruling: two kinds of fuel dependency

| | Primary fuel | Backup-generator resupply ("the buffer has a buffer") |
|---|---|---|
| Consumers | generation (LNG and oil), airport, seaport, freight_yard | exchange, mast, data_centre, cable_landing, treatment, pumping, tertiary, regional, clinic, blood_bank |
| When it binds | Always. Fuel is the consumer's working input. | Only after power → X has failed **and** the on-site tank has run down. It is a second-order edge. |
| Delivery | By pipe (LNG terminal to gas-fired plant; refinery to large airport) or within the port (bunkers) | By tanker truck from a depot over roads |
| Type | physical_flow (generation; pipeline-fed airport); logistic (seaport, freight_yard) | **logistic** |

**Why backup resupply is logistic and not physical_flow:**
1. **Mechanism.** The fuel moves by truck over the road network. There is no fixed conduit. The Communications Sector-Specific Plan says so outright: "The Communications Sector generally relies on diesel fuel to power its backup generators and the Transportation Sector to deliver those fuels" [S8]. EPA's water guidance is built around truck resupply: refuelling plans, "contracts with multiple fuel vendors", and "Risks associated with conducting a resupply operation in a seriously-disrupted operational environment" [S13].
2. **Timescale.** The on-site tank (12 h to 96 h) is there precisely so the refill can arrive in hours to days. That is the logistic band.
3. **Substitutability.** It is moderate. Any depot with a truck can serve the site, and EPA advises "multiple vendors from different supplier regions" [S13].

**The one exception** is a standby generator that runs on natural gas. It is fed by pipe: "Natural gas generators do not require truck refueling" [S13]. That is physical_flow, but the gas-distribution main is not a fuel-layer node class. See Question 3.

**Core or optional.** A backup edge is **core** where a fixed generator is required or standard for the class: exchange, data_centre, cable_landing, treatment, tertiary, regional and blood_bank. It is **optional** where many real sites have batteries only or share rotating portable generators: mast, pumping and clinic.

**Modelling consequence for the next stage (flagged, not decided here).** A core backup edge should not make the consumer fail when the fuel layer fails while grid power is up. The edge carries weight only once power → X is lost and the tank buffer is spent. The buffer notes below give the tank sizes.

## Table

### fuel → power

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| generation | core (**conditional on subtype**: LNG or oil thermal = core; hydro = none; coal = see Disagreement 2) | LNG plant: import_terminal (LNG), via the gas transmission pipeline. Oil-fired plant: tank_farm, refinery (and an oil import_terminal where it is co-located). | fuel (natural gas; fuel oil) | physical_flow | A gas-fired plant burns regasified LNG sent from the terminal by pipeline, and it stops when the gas stops. An oil-fired plant draws fuel oil from bulk storage by pipe or jetty. | [S20] EIA *Taiwan Analysis Brief* (Apr 2026): Taiwan "has three liquefied natural gas (LNG) regasification terminals … through which it imports all of its LNG"; gas was 43% of 2024 generation; "Taiwan mainly used natural gas for power generation (78%)". [S21] CPC: trunk network of "approximately 2,221 kilometers" supplying "Taiwan Power Company (Taipower)". [S22] Taipower's Taichung terminal supplies "units 1 & 2 at Taichung Power Plant, as well as units 4, 5 & 6 at Tunghsiao Power Plant". | literature | No real on-site gas store at the plant; the buffer is the terminal tanks and the pipeline. Taiwan's national gas stock covers "10 to 11 days of use" [S20][S24]. Oil-fired plants hold fuel oil in on-site tanks (days; judgment). | Terminals, from [S20]: Yung-An, Kaohsiung (1990); Taichung (2009); Taoyuan/Guantang (2025, first cargo 1 Apr 2025, built partly to fuel the Datan expansion [S23]). Taipower is building its own Taichung LNG terminal [S22]. S&P: "once the island is blockaded, its natural gas supply is not expected to sustain for more than two weeks" [S24]. |
| generation, hydro subtype | none | none | — | — | A hydro plant turns stored water head into power and burns no fuel. Any diesel on site (gate and black-start standby) is tiny and incidental. | EIA [S20] lists hydro as a separate, non-fuel generation source (3% of 2024 capacity). | judgment (self-evident physics; no source says it outright) | — | Taipower conventional hydro and pumped storage (4% of capacity [S20]) are both fuel-free. |
| transmission_substation | none | none | — | — | Substations switch and transform power; they burn no fuel. Their control and protection ride through on station DC batteries, not generators. | None found stating it. I would look to IEEE 485/1188 (station batteries) and NERC PRC-005 (station DC supply). | judgment | Station batteries (hours). | — |
| distribution_substation | none | none | — | — | As for transmission substations. | None found. | judgment | Station batteries. | — |

### fuel → telecom (all four rows are backup-generator resupply)

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| exchange | core | depot (primary); tank_farm (large bulk drops) | fuel (diesel) | logistic | Central offices carry batteries plus a fixed standby engine. The engine's tank has to be refilled by truck during a long outage. | [S8] DHS *Communications Sector-Specific Plan* (2015): diesel for backup generators, delivered by the Transportation Sector. [S6] FCC 07-177, *Order on Reconsideration* (Katrina Panel; 4 Oct 2007): §12.2 required "a minimum 24 hours of emergency backup power for assets inside central offices" (the rule never took effect; OMB disapproved it and the FCC withdrew it in 2008 [S28]). | standard (the FCC rule as adopted, though never in force) + literature (DHS SSP) | Batteries, then the generator's on-site tank. The FCC's intended floor was 24 h. | No Taiwan central-office rule found. |
| mast | optional | depot | fuel (diesel; petrol for small portable generators) | logistic | Many cell sites have batteries only. Some have fixed generators; others rely on portable generators brought in and refuelled by truck. | [S7] FCC CSRIC IV WG9 (Dec 2014): batteries "generally sized for two to eight hours"; "if a shared portable generator solution has to be refueled every 8-12 hours, it may not be a practical solution"; road closures limit access for refuelling vehicles. [S6] ¶: the "design standard is for eight hours or more of backup power (generators, batteries or both)". [S9] Puerto Rico (FCC field hearing, 17 Nov 2022): carriers installed "generators and batteries in most cell sites"; "daily demand of 75,000 gallons of fuel"; "Trucks of 10,000 gallons of fuel were only being served 3,000 or 5,000 gallons". | literature | Batteries 2–8 h; a portable generator needs refuelling every 8–12 h [S7]. | Typhoon Danas (Aug 2025): power loss took masts down; carriers planned "200餘台可攜式緊急發電機" (more than 200 portable generators) [S26]. NCC disaster-response base stations at substations target "備援電力達72小時以上" (backup power of more than 72 h) [S27]. |
| data_centre | core | depot; tank_farm | fuel (diesel) | logistic | Tiered data centres carry engine generators with contracted on-site fuel storage and refill by truck. | [S10] Uptime Institute Journal (Klesner, Jun 2014), on the Tier Standard: "12 hours of minimum fuel storage as a starting point for Tier-defined data centers." [S19] EIA: large facilities "have diesel generators for backup and emergency power supply". | standard (Uptime Tier, as reported by Uptime) | 12 h or more on site. Often 24–72 h in practice (judgment). | — |
| cable_landing | core | depot | fuel (diesel) | logistic | A cable landing station powers its PFE (which feeds the repeaters) from the grid, with battery and generator backup. The generator is refilled by truck. | [S11] Equinix (15 Oct 2024): PFE works by "converting battery power to a constant current"; a station needs "on-site power infrastructure connected to a stable energy grid with battery and generator backup". | judgment (industry source only; no standard or government report found. I would look to ITU-T L-series or ICPC recommendations.) | PFE batteries, then the generator tank. | Not found. |

### fuel → water (backup-generator resupply)

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| reservoir | none | none | — | — | An upland impoundment holds and releases water by gravity; it has no powered process that needs fuel. | None found stating it. | judgment | — | — |
| treatment | core | depot; tank_farm | fuel (diesel mainly; natural gas or propane at some sites) | logistic | Design standards require dedicated standby power so treated water keeps flowing during an outage. The generator tank is refilled by truck. | [S12] *Recommended Standards for Water Works* (Ten States Standards, 2022), §2.6: "Dedicated standby power shall be provided so that water may be treated and/or pumped to the distribution system during power outages to meet the average day demand." [S13] EPA *Power Resilience Guide* (EPA 800-R-19-001, Jun 2019): "You must maintain fuel on-site and have multiple ways to obtain additional fuel". | standard | EPA case note: fuel for "a generator at 70% load for five days" [S13]. | Taiwan Water Corporation practice not found. |
| pumping | optional | depot | fuel (diesel; petrol for portable units) | logistic | Larger booster stations have fixed generators. Small utilities often rotate portable generators between stations, so a station is not permanently fuel-coupled. | [S12] §6.3.4: "a power supply shall be provided from a standby or auxiliary source". [S13]: "Smaller water utilities can rotate several portable, gasoline generators between lift and pump stations". | standard (Ten States) and literature (EPA). They pull in different directions, so graded optional. | Portable unit supplied with about 24 h of fuel ("the generator must be delivered with a 24-hour fuel supply") [S13]. | — |
| storage | none | none | — | — | Treated-water tanks and towers are passive and gravity-fed. | [S12] §7.1.1 treats storage as the buffer for source and treatment outages, not as a power or fuel consumer. | judgment | — (storage is itself a buffer) | — |

### fuel → transport (primary fuel)

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| seaport | core | tank_farm and import_terminal (usually co-located, supplying bunkers); refinery (where adjacent); depot (diesel for cargo-handling equipment) | fuel (marine bunkers; diesel) | logistic | Ships bunker at the port, by barge or at the berth from port-side storage. Cargo-handling equipment runs mainly on diesel. Service degrades over days as fuel runs short. | [S15] CPC *Downstream Operations*: "marine bunkering stations for international vessels at Keelung, Suao, Taichung, Kaohsiung, and Hualien ports". [S18] RMI (Reback et al., 10 Jul 2024): "Today, most cargo handling equipment runs on diesel." | literature | Terminal and yard tank inventory (days; judgment). | The five CPC bunkering ports are listed under source. |
| airport | core (**type conditional on how fuel is received**) | pipeline-fed: refinery, tank_farm, import_terminal. Truck-fed: depot. | fuel (jet fuel) | physical_flow (large, pipeline-fed airports; logistic for truck-fed ones. See Conditional subtypes.) | Aircraft cannot be dispatched without jet fuel. Major airports receive it by product pipeline into an on-airport fuel farm; small ones by tanker truck. | [S16] CPC press release (26 May 2023): jet fuel from 桃園煉油廠 (Taoyuan Refinery) "泵輸桃園機場" (pumped to Taoyuan Airport). [S17] CNBC (10 May 2021), on the Colonial Pipeline shutdown: it "directly services seven airports"; American Airlines added fuel stops at Charlotte. [S15] CPC runs "aviation fueling stations at all of Taiwan's airports". | literature | Fuel-farm inventory; an analyst estimated "We can draw inventory for probably a week" [S17]. | Taoyuan is supplied by pipeline from the adjacent Taoyuan refinery [S16]. CPC fuels every Taiwan airport [S15]. |
| freight_yard | core | depot (primary; bulk delivery to an on-site dispenser, or a large filling point); tank_farm (large yards) | fuel (diesel) | logistic | A truck yard's fleet runs on diesel, delivered by tanker to on-site tanks or bought at depots. | [S19] EIA *Diesel fuel explained*: "Most of the products we use are transported by trucks and trains with diesel engines". | literature | On-site dispenser tank (days; judgment). | CPC runs 14 product distribution centres island-wide [S15] (these are the real counterparts of the depot class). |
| bridge | none | none | — | — | Consumes nothing in Phase 1 (per the brief). | brief | — | — | — |
| road_junction | none | none | — | — | Consumes nothing in Phase 1 (per the brief). | brief | — | — | — |
| rail_node | none | none | — | — | Consumes nothing in Phase 1 (per the brief). Diesel traction exists, but it sits outside Phase 1 scope. | brief; [S19] (diesel trains) | — | — | — |

### fuel → healthcare (backup-generator resupply)

| consumer_class | depends | supplier_classes | commodity | dependency_type | rationale | source | evidence_grade | buffer_note | taiwan_note |
|---|---|---|---|---|---|---|---|---|---|
| tertiary | core | depot; tank_farm | fuel (diesel) | logistic | Hospitals must run an emergency power supply system, and on a long outage its generators live on trucked fuel. Sandy showed how the chain fails: the hospital generators themselves were fine, but at Bellevue "the fuel feed to the generators stopped working" [S5]. | [S1] 42 CFR 482.15(e)(3): "Hospitals that maintain an onsite fuel source to power emergency generators must have a plan for how it will keep emergency power systems operational during the emergency, unless it evacuates." (e)(1) cites NFPA 99 and NFPA 110. [S2] Mackey, *CSE Magazine* (20 Jul 2022): Level 1, Type 10; "typically must be Class 96 (minimum 96 hours of runtime) or have an operational plan to supply 96 hours of fuel". | standard (CMS rule; NFPA 110 as reported, since the NFPA text itself was not fetched) | NFPA 110 Level 1 / Type 10 / Class 96 practice: 96 h of fuel, on site or contracted [S2]. | NTUH: generators' daily tanks "連續運轉 12 小時以上" (run continuously for more than 12 hours); the three campuses can keep running "至少兩天以上" (at least two days) [S25] (a practice account, not a regulation). MOHW rule text not found. |
| regional | core | depot | fuel (diesel) | logistic | The same CMS condition of participation applies to every hospital, whatever its size. | [S1]; [S2] | standard | As tertiary. Smaller plants often hold less fuel on site and rely more on contracted delivery (judgment). | As tertiary. |
| clinic | optional | depot | fuel (diesel; petrol for portable units) | logistic | Outpatient clinics have no federal generator requirement. Only some have one (surgical centres, dialysis, larger clinics). | [S3] 42 CFR 491.12 (RHC/FQHC) has no emergency-and-standby-power paragraph, unlike 482.15(e). CMS's general rule asks only for policies on "alternate sources of energy" (482.15(b)(1)(ii) wording) [S1]. | standard (by absence of a requirement) | Often none. Where present, a small tank (hours to a day; judgment). | — |
| blood_bank | core | depot | fuel (diesel or petrol) | logistic | Blood stock is lost if the cold chain breaks, so blood refrigeration is put on a standby generator. | [S4] WHO, *Manual on the management, maintenance and use of blood cold chain equipment* (2005), §4.7.2: "All blood bank refrigerators, freezers, cold rooms and freezer rooms should be connected to a stand-by electricity generator." Standby generators "generate electricity using petrol or diesel fuel". | literature (WHO guidance; "should", not a requirement) | Generator tank, plus the thermal inertia of refrigerators (hours). | — |

## Which fuel classes serve which consumers (summary)

| supplier class | serves |
|---|---|
| import_terminal (LNG) | gas-fired generation only (by pipeline) |
| import_terminal (oil or product) | tank_farm, seaport bunkers, pipeline-fed airport |
| refinery | pipeline-fed airport, oil-fired generation, seaport (where adjacent) |
| tank_farm | oil-fired generation, airport, seaport; bulk drops to data_centre, treatment, tertiary |
| depot | every backup-generator consumer (exchange, mast, data_centre, cable_landing, treatment, pumping, all four healthcare classes), freight_yard, truck-fed airport, port diesel for cargo-handling equipment |

## Conditional subtypes, and how to express them

1. **generation: `fuel_kind ∈ {lng, oil, coal, hydro}`.** lng → import_terminal(lng), physical_flow, core. oil → tank_farm or refinery, physical_flow, core. hydro → none. coal → no fuel-layer supplier (Disagreement 2).
2. **import_terminal: `product ∈ {lng, oil}`.** It decides which consumers the terminal can serve. An LNG terminal must never be picked as a supplier for jet fuel, bunkers or diesel.
3. **airport: `fuel_receipt ∈ {pipeline, truck}`**, correlated with airport size. pipeline → physical_flow from refinery, tank_farm or import_terminal. truck → logistic from depot. The dependency is core either way; only the type and supplier classes change.
4. **Backup-generator consumers: `standby_fuel ∈ {diesel, natural_gas, none}`.** diesel → logistic from depot. natural_gas → physical_flow, but from no fuel-layer class (Question 3). none → no edge. This is also how optional rows (mast, pumping, clinic) should be drawn: `none` is the draw for sites that are not coupled.
5. **mast: `has_fixed_generator`** (optional, rising with density). A portable-generator mast is coupled only once a unit has been deployed. Phase 1 can treat it as not coupled.

## Disagreements (the 21 couplings are unchanged)

1. **The logistic fuel edges imply transport edges that the 21 exclude.** DHS states directly that communications relies "on diesel fuel to power its backup generators and the Transportation Sector to deliver those fuels" [S8]. EPA says the same for water, and CSRIC notes road closures block refuelling [S7][S13]. Yet transport → telecom and transport → water are excluded; only transport → healthcare and transport → fuel are modelled. If fuel → telecom and fuel → water are typed logistic, the delivery path over roads is real but invisible. **Ways to reconcile:** (a) route logistic fuel edges over the transport layer in the solver, so transport is an indirect supplier through fuel. This leaves the 21 intact, since transport → fuel is modelled. Or (b) state it as a modelling simplification. For the design side to decide.
2. **Coal generation has no supplier.** Coal was 40% of Taiwan's 2024 generation [S20]. The fuel layer has no coal class, and transport → power (coal delivery) is excluded. A coal "thermal" plant therefore has no fuel dependency anywhere in the model, which is wrong in the real world (coal stock runs down over weeks; S&P puts coal stock at 39 days [S24]). This is acceptable only if it is stated as scope.
3. **The gas transmission network is abstracted away.** The import_terminal → generation edge stands in for CPC's roughly 2,221 km trunk pipeline [S21]. A pipeline cut is not a separate failure point. The edge's physical_flow type is still right.
4. **fuel → power has only one consuming class.** Substations do not depend on fuel. That is consistent with the rationale ("fuel to power" is a supply cross-feed to generation), not a conflict.

## Questions for the design side

1. Should backup-generator edges be **gated on power loss** (active only after power → X fails and the tank buffer runs out)? Or should they be drawn as ordinary edges whose buffer comes from the buffer_note? The table cannot express this, and it changes the answer keys.
2. Pumping is graded **optional**, although the Ten States Standards say "shall" (§6.3.4). EPA documents portable-generator rotation among small stations [S13]. Confirm optional.
3. Where a standby generator runs on natural gas (pipe, not truck), is there a supplier node, or does the site count as not fuel-coupled?
4. Seaport is typed **logistic** even though some bunkers arrive by berth-side pipe. The case for logistic is that barge delivery is the norm and the timescale is days. Confirm, or split it the way airport is split.

## Sources (every one opened this session)

- **S1** US CMS, 42 CFR §482.15, *Condition of participation: Emergency preparedness* (hospitals), paragraphs (b)(1)(ii) and (e)(1)–(3). https://www.law.cornell.edu/cfr/text/42/482.15
- **S2** Mackey, P.E., "Hospital emergency power supply systems," *Consulting-Specifying Engineer*, 20 Jul 2022 (NFPA 110 Level, Type and Class). https://www.csemag.com/hospital-emergency-power-supply-systems/ (NFPA 110 itself not fetched.)
- **S3** US CMS, 42 CFR §491.12 (RHC/FQHC emergency preparedness). https://www.law.cornell.edu/cfr/text/42/491.12
- **S4** WHO, *Manual on the management, maintenance and use of blood cold chain equipment*, 2005, §4.7.2. https://iris.who.int/server/api/core/bitstreams/1d6e2201-c68f-4158-8240-f91dd1da8db6/content
- **S5** CBS News, "What caused generators to fail at NYC hospitals?", 2 Nov 2012 (event evidence only). https://www.cbsnews.com/news/what-caused-generators-to-fail-at-nyc-hospitals/
- **S6** FCC 07-177, *Order on Reconsideration*, Katrina Panel recommendations, EB Docket 06-119, released 4 Oct 2007. https://docs.fcc.gov/public/attachments/FCC-07-177A1.pdf
- **S7** FCC CSRIC IV Working Group 9, *Infrastructure Sharing During Emergencies: Backup Power*, Dec 2014. https://transition.fcc.gov/pshs/advisory/csric4/CSRIC_WG%209_Backup_Power_Reccomendations%20_11-24-2014.pdf
- **S8** DHS, *Communications Sector-Specific Plan: An Annex to the NIPP 2013*, 2015. https://www.cisa.gov/sites/default/files/publications/nipp-ssp-communications-2015-508.pdf
- **S9** Statement of Enrique Volckers Nin, FCC field hearing (Puerto Rico), 17 Nov 2022. https://www.fcc.gov/sites/default/files/field-hearing-11172022-statement-enrique-volckers-nin.pdf
- **S10** Klesner, K. (Heslin, K., ed.), "Data center fuel system design and reliability," *Uptime Institute Journal*, Jun 2014. https://journal.uptimeinstitute.com/fuel-system-design-reliability/
- **S11** Equinix, "What Is a Cable Landing Station?", 15 Oct 2024. https://blog.equinix.com/blog/2024/10/15/what-is-a-cable-landing-station/
- **S12** Great Lakes–Upper Mississippi River Board, *Recommended Standards for Water Works*, 2022 ed., §§2.6, 6.3.4, 7.1.1. https://files.dep.state.pa.us/Water/BSDW/Public_Water_Supply_Permits/2022_Recommended_Standards_for_Water_Works.pdf
- **S13** US EPA, *Power Resilience Guide for Water and Wastewater Utilities*, EPA 800-R-19-001, Jun 2019 (a 2023 update exists). https://www.epa.gov/sites/default/files/2016-03/documents/160212-powerresilienceguide508.pdf
- **S15** CPC Corporation, Taiwan, *Downstream Operations*. https://www.cpc.com.tw/en/cp.aspx?n=2610
- **S16** CPC press release, 桃園機場油品化驗合格 (Taoyuan Airport fuel passes laboratory tests), 26 May 2023. https://www.cpc.com.tw/News_Content.aspx?n=28&s=71152
- **S17** CNBC, "Pipeline outage forces American Airlines to add stops…", 10 May 2021. https://www.cnbc.com/2021/05/10/colonial-pipeline-shutdown-forces-airlines-to-consider-other-ways-to-get-fuel.html
- **S18** Reback, M., Sanders, N., Muñoz, P., Waddell, A., "The Time Is Now for Zero-Emissions Cargo Handling Equipment…", RMI, 10 Jul 2024. https://rmi.org/the-time-is-now-for-zero-emissions-cargo-handling-equipment-at-americas-busiest-cargo-ports
- **S19** US EIA, *Diesel fuel explained: Use of diesel*. https://www.eia.gov/energyexplained/diesel-fuel/use-of-diesel.php
- **S20** US EIA, *Taiwan Analysis Brief*, Apr 2026. https://www.eia.gov/international/content/analysis/countries_short/Taiwan/Taiwan.pdf
- **S21** CPC Corporation, Taiwan, *Natural Gas*. https://www.cpc.com.tw/en/News_Content.aspx?n=2671&s=2375
- **S22** CTCI e-newsletter 465, "CTCI Wins EPC Contract for Taipower Taichung LNG Receiving Terminal". https://www.ctci.com/e-newsletter/EN/465/hot-news/article-05.html
- **S23** Global Energy Monitor, *Taoyuan LNG Terminal*. https://www.gem.wiki/Taoyuan_LNG_Terminal
- **S24** Yep, E., "Taiwan vulnerable to LNG supply risks in the event of a maritime blockade," S&P Global, 30 May 2024. https://www.spglobal.com/energy/en/news-research/latest-news/lng/053024-taiwan-vulnerable-to-lng-supply-risks-in-the-event-of-a-maritime-blockade
- **S25** 善科教育基金會 (Sancode Education Foundation), 停電時醫院該怎麼辦？ (What should a hospital do in a power outage?; NTUH practice). https://www.sancode.org.tw/activities_info.php?type=3&nid=181
- **S26** 經濟日報 (Economic Daily News, UDN), 颱風丹娜絲重創基地台 (Typhoon Danas badly damages base stations), 4 Aug 2025. https://money.udn.com/money/story/5612/8915851
- **S27** 經濟日報 (Economic Daily News, UDN), NCC 防救災基地台 (NCC disaster-response base stations), 24 Oct 2025. https://money.udn.com/money/story/5612/9093768
- **S28** Lexology, "FCC abandons backup power rule for cell sites" (2008). https://www.lexology.com/library/detail.aspx?g=c7e48731-8049-4ca5-943f-9a9def04951d

Not verified, and so not relied on: the NFPA 110 and NFPA 99 texts (paywalled; reported through S2); FAA AC 150/5230-4C (the FAA server refused the download); Rinaldi, Peerenboom & Kelly 2001 (the full text could not be fetched); the MOHW 醫療機構設置標準 (Medical Institution Establishment Standards) annex on emergency power; Taiwan Water Corporation standby-power practice.

---

<!-- file: REVIEW.md -->
# Independent review: node-class dependency table, merged draft v0.1

Reviewer: independent (did not build the table). Date: 2026-09-29.
Inputs read: BRIEF.md, MERGED_DRAFT.md, all five lane files. Sources below were re-fetched by the reviewer this session, or read in the local copies in this folder where noted.

Verdict key: **confirmed** (the source says what the row claims) / **overstated** (the source is real and the quote is right, but it does not carry the weight the row puts on it) / **wrong** (the source does not say it) / **unreachable**.

---

## 1. Source checks

| # | Row(s) | Source | What the row claims | What the source says | Verdict |
|---|---|---|---|---|---|
| 1 | power → tertiary, regional; fuel → tertiary, regional | 42 CFR 482.15(e)(1)–(3) (Cornell LII) | Generators under NFPA 99/101/110; fuel plan | (e)(1) location per NFPA 99/101/110; (e)(2) testing per NFPA 99/110/101; (e)(3) "Hospitals that maintain an onsite fuel source … must have a plan for how it will keep emergency power systems operational during the emergency, unless it evacuates." No dual utility feed and no fuel duration in the CFR text. | **confirmed** (for the generator and fuel-plan claims only) |
| 2 | fuel → tertiary (buffer: "Class 96") | Mackey, *CSE Magazine* 2022 | NFPA 110 Class 96 | Quote is verbatim: "typically must be Class 96 … or have an operational plan to supply 96 hours of fuel". The article ties the 96 h to the Joint Commission's 96-hour emergency plan, not to an NFPA 110 requirement. NFPA 110 leaves the Class to the authority having jurisdiction. | **overstated** (the "Std" grade and the "NFPA 110 Class 96" label are too strong; it is accreditation practice, reported by a trade magazine) |
| 3 | power → tertiary ("two feeds from two different substations") | 王榮坤, 科學月刊 no. 630, 2022 | Tertiary hospitals are fed from two substations | Quote confirmed: "院區的供電分別來自兩個不同的高壓電變電站". The author writes from his own hospital (NTUH). It is not a rule, and neither CMS nor NFPA 99 requires two utility feeds. | **overstated** (one hospital's practice turned into a class-wide supplier rule) |
| 4 | power → mast | GAO-21-297 | 49% of Maria cell outages were from power loss | "49 percent were not operational because of the power outage"; 79% by October; backup "ranging from several hours to one day". | **confirmed** |
| 5 | power → exchange | CPUC D.20-07-011 / D.21-02-029 | 72 h backup | 72 h in Tier 2/3 High Fire-Threat Districts (wireless); wireline 72 h only "in locations with insufficient mobile wireless coverage". | **confirmed** (state-level, narrow scope; buffer evidence, not dependency evidence) |
| 6 | telecom → generation | NERC COM-001-3 | R8 requires Generator Operator communications; buffer note says COM-001 "requires an alternative communication path" | R8 requires Interpersonal Communication for the GOP. Alternative Interpersonal Communication is required only of the RC, TOP and BA (R2, R4, R6). **Not of the Generator Operator.** It is also a North American standard; Taipower is not NERC-registered. | **overstated** (the dependency claim holds; the buffer-note claim is wrong) |
| 7 | telecom → transmission_substation, generation | NERC RSTC, *Risks and Mitigations for Losing EMS Functions*, v4 2024 | EMS/SCADA loss mechanism; ~73 min average | Quotes and the 73-minute average are confirmed. But the document attributes EMS losses mainly to software, maintenance and internal communications. External carrier failure appears only as isolated lessons learned. | **overstated** (it shows control depends on communications, not on the *public* telecom layer) |
| 8 | telecom → power (all three rows); Issue E | US DOE OE, *Power Grid and Communications Interdependencies*, Sep 2023 | Communications support grid functions | "Grid communications now rely on a mixture of private, utility-owned infrastructure and commercial leased infrastructure." It gives no split. | **confirmed**, and it cuts against the rows' supplier classes (see Finding 1) |
| 9 | telecom → distribution_substation (Taiwan note), transmission_substation ("ADCC covers 161/69 kV") | Taipower Smart Grid DDCC page | DDCC monitors and controls substation devices; ADCC covers 161/69 kV substations | DDCC quote confirmed ("21 Siemens systems and 1 SNC Lavalin"). **The page does not mention ADCC at all**, and says nothing about what network carries the SCADA. | **wrong** (the ADCC claim); **confirmed** (the DDCC claim) |
| 10 | (reviewer's own check for Issue E) | 台電月刊 Vol. 700, "高速光纖 精準智慧" | — | Taipower's communications division runs "光纜長度超過1萬公里" (more than 10,000 km of optical cable), including OPGW on transmission towers. "台電所屬發、變電站及大部分的服務所都有光纜連結構成綿密的通信網" (Taipower's power plants, substations and most service offices are linked by optical cable into a dense communications network), supporting "電力指揮調度" (power dispatch and command). | New evidence; see Finding 1 |
| 11 | transport → import_terminal, refinery; fuel → generation | US EIA, *Taiwan Country Analysis Brief*, Apr 2026 | Three crude ports; three LNG terminals; gas 43% and coal 40% of 2024 generation; 10–11 days of gas | All confirmed verbatim. | **confirmed** |
| 12 | transport → refinery (Taoyuan pipeline-fed) | Boone, *Global Taiwan Brief*, 2023 | Taoyuan refinery fed from Shalun, so no transport edge | "sources its crude oil from the Shalun fuel depot" is confirmed. **The article does not say how** (pipeline is inferred). | **overstated** (the "pipeline" part is judgment) |
| 13 | transport → tank_farm, depot | US EIA, *Diesel fuel explained* | Most diesel moves by pipeline to terminals; trucks go from terminals to retail | Both quotes confirmed. | **confirmed** |
| 14 | fuel → generation (LNG) | CTCI e-newsletter 465 | The Taichung terminal feeds Taichung units 1–2 and Tunghsiao 4–6 | Confirmed verbatim. | **confirmed** |
| 15 | power → airport | FAA AC 150/5340-30J Ch. 9 (local copy ac30j.txt) | Second feed under Configuration B; Configuration C for "small airports" | The configurations apply **per visual aid, not per airport**. Configuration B (an alternate prime source) covers "CAT II HIRL, centerline lights, and touchdown zone lights" only. Configuration C is "all lighting aids not covered in Configurations A and B", not small airports. Configuration A (the engine generator) is the usual standby. The AC covers visual aids only, not ATC or terminals. | **overstated** |
| 16 | fuel → data_centre | Uptime Institute Journal (Klesner 2014) | 12 h minimum fuel | "12 hours of minimum fuel storage as a starting point for Tier-defined data centers." | **confirmed** (an industry certification scheme, not a code; "Std" is generous) |
| 17 | fuel → exchange; Issue B | DHS *Communications SSP* 2015 | Backup diesel is delivered by the Transportation Sector | "The Communications Sector generally relies on diesel fuel to power its backup generators and the Transportation Sector to deliver those fuels." Note that the lane's local copy (fuelsrc/commssp.pdf, 471 bytes) is a failed download; the reviewer fetched the source live. | **confirmed** |
| 18 | fuel → exchange (graded Std) | FCC 07-177 (local copy) | 24 h central office / 8 h cell site rule | The rule text is confirmed. The "design standard is for eight hours or more … at every cell site" sentence is Verizon Wireless's internal standard, quoted from an ex parte filing, not the FCC's. The rule never took effect. | **overstated** (cannot carry a "standard" grade) |
| 19 | telecom → tertiary, regional (typed control; graded Std) | 42 CFR 482.15(c)(3) (eCFR) | Supports the claim that hospitals depend on telecom for control | Text: "Primary and alternate means for communicating with (i) Hospital's staff. (ii) … emergency management agencies." This is an emergency-communications *planning* rule. It says nothing about clinical systems, and if anything it describes a buffer (the alternate means). | **overstated** (misapplied to support "control") |
| 20 | telecom → tertiary, regional | Larsen et al., *JAMIA* 25(2), 2018 | Downtime disrupts care; lab results 48.7% | Figures confirmed (48.7%; 46% of reports with procedures absent or not followed). The paper is about **EHR downtime of any cause**, not telecom outages. | **overstated** (not evidence of a telecom dependency) |
| 21 | telecom → tertiary ("lab results delayed by 62%") | ASPR TRACIE EHR downtime collection | Results delayed 62% | Confirmed, but the figure comes from Larsen et al. 2019, *Applied Clinical Informatics* 10(3), not the 2018 JAMIA paper. It concerns EHR downtime, not telecom. | **overstated** |
| 22 | telecom → seaport | Kramek, Brookings 2013 | "Today, ports rely as much on computer networks as on human stevedores." | The real sentence is "ports rely as much upon networked computer and control systems as they do upon stevedores". The lane's "verbatim" quote is a paraphrase. The "grind to a halt in days" quote was not found. The paper is about port-internal and cyber systems, not external carriers. | **overstated** (misquoted; mechanism is IT, not telecom) |
| 23 | water → refinery (graded Std) | 29 CFR 1910.106(i)(5)(ii) (local copy osha106.html) | Refineries need fire water | Verbatim confirmed. It says nothing about where the water comes from (fire-water ponds and own supply are common). | **confirmed** (need), **overstated** (as proof of water-*layer* dependence) |
| 24 | water → tank_farm, depot (graded Std) | 29 CFR 1910.106(f)(8) (local copy) | Fire water | "Suitable fire-control devices, such as small hose **or portable fire extinguishers**" satisfy the rule. It does not require a water supply. | **overstated** (does not support a water dependency; grade should be judgment) |
| 25 | water → coastal thermal generation | Boyle Eng. for SDG&E (Encina), 1995 | Coastal plants buy fresh water from the district | Confirmed. But the same document is a study of *replacing* that supply with on-site desalting (400 gpm RO) because district water was unreliable. | **confirmed**, and it shows the edge is removable (see Finding 7) |
| 26 | fuel → blood_bank | WHO blood cold chain manual 2005 §4.7.2 (local copy) | Blood refrigeration should be on a standby generator | "should be connected to a stand-by electricity generator." | **confirmed** ("should"; graded Lit, which is correct) |
| 27 | telecom → tank_farm, import_terminal | 49 CFR 195.446 (eCFR) | SCADA-controlled pipeline facilities must plan manual operation | Applicability and the manual-operation quote are confirmed. It is silent on whether SCADA rides public or private telecom. | **confirmed** (control mechanism), **overstated** (public-layer dependence) |

Summary: 27 checks. 12 confirmed, 14 overstated, 1 wrong, 0 unreachable. Nothing was fabricated. The recurring fault is grade and scope inflation, not invented sources. A real source is stretched to cover a claim it does not make: a planning rule read as a dependency, an IT outage read as a telecom outage, one hospital read as a class, one lighting aid read as a whole airport.

---

## 2. Findings

Severity: **C** = would corrupt the truth (changes which nodes fail, so it changes answer keys); **M** = would mislead (a wrong grade, type or rationale that a reader or committee would catch, but the world is mostly right); **m** = minor.

**F1. telecom → power: the supplier classes point at the public telecom layer, but Taiwan's grid control runs on Taipower's own fibre.** Severity **C**.
- *Rows:* telecom → generation, transmission_substation, distribution_substation. The same applies, less strongly, to telecom → treatment and pumping, and to telecom → tank_farm and import_terminal (CPC's pipeline SCADA).
- *Problem:* The rows name `exchange` and `mast` as suppliers. In a Taiwan-calibrated world, a strike on public exchanges would black out grid control in the model, but not in reality.
- *Evidence:*
  - DOE 2023: "a mixture of private, utility-owned infrastructure and commercial leased infrastructure."
  - 台電月刊 Vol. 700: more than 10,000 km of Taipower-owned optical cable, including OPGW, linking "發、變電站" (power plants and substations) for dispatch.
  - NERC's EMS reference attributes EMS losses mainly to internal causes.
  - The lane's own EPA source (S4) lists "utility-owned fiber optic" among water utilities' links.
- *Fix:* This is a design decision, so raise it; do not guess. There are two options:
  - (a) Carry a per-consumer `leased_path_share` in the recipe. Taiwan transmission and generation would be low, and distribution and water medium.
  - (b) Rule that the telecom layer includes utility private networks. Then those networks also need power, a node class and a place in the world.

  Until one is decided, keep the transmission_substation and generation rows' dependency, but grade their public-layer supplier classes as judgment.

**F2. Backup-fuel edges are marked "core" like primary edges, with no gating on power loss.** Severity **C**.
- *Rows:* fuel → exchange, mast, data_centre, cable_landing, treatment, pumping, tertiary, regional, clinic, blood_bank.
- *Problem:* A solver reading "core" will fail a hospital when its depot is struck while grid power is up. That is false, and it will pull depots into the answer keys as high-value targets.
- *Evidence:*
  - Appendix B: "the generators that buffer a power loss themselves run on fuel — the buffer has a buffer."
  - 42 CFR 482.15(e)(3) makes the fuel plan conditional on running on emergency power.
  - The fuel lane says this itself ("A core backup edge should not make the consumer fail when the fuel layer fails while grid power is up").
- *Fix:* Add a field `role ∈ {primary_supply, buffer_resupply}`. For `buffer_resupply`, the edge's effect is to extend the buffer on the consumer's power → X dependency. It never fails the consumer on its own. "Core" then means only that the consumer has a fixed generator. See Issue A.

**F3. freight_yard is used as the sole supplier node for transport → healthcare, depot and tank_farm, which creates false single points of failure.** Severity **C**.
- *Rows:* transport → tertiary, regional, clinic, blood_bank, depot, tank_farm (truck rack).
- *Problem:* Hospital resupply, blood couriers and tank trucks use the road *network*. They come from distributors' own depots and the blood centre's own vans, not from a generic "truck warehouse and yard". Knocking out one freight_yard would starve every hospital attached to it, and the optimizer will find that artefact.
- *Evidence:*
  - The transport lane's Disagreement 2 ("this is a node standing in for a network").
  - NASEM 2020 (Maria): goods sat in the port because of "blocked roads and shortages of trucks and drivers". That is a road-network and fleet failure, not a yard failure.
  - FEMA Lifelines: "Multimodal routes … are clear of debris and accessible".
- *Fix:* Do one of the following:
  - (a) Make the transport → healthcare and transport → fuel (depot) supply *path-based*: the consumer is served if any seaport, airport or freight_yard of the right kind reaches it over the road graph. Roads are then carriers, not suppliers, which respects the Phase 1 rule that roads consume nothing.
  - (b) Require every consumer to take k ≥ 2 freight_yard suppliers, with k in the recipe.

  Either choice is a design decision. Record it as a known simplification in any case.

**F4. The tertiary "two feeds from two different substations" rule rests on one hospital.** Severity **C**.
- *Row:* power → tertiary.
- *Problem:* Applied class-wide, it makes every tertiary hospital immune to a single-substation loss. That changes the answer keys.
- *Evidence:*
  - Check 3: the source is the author's own hospital (NTUH), not a rule.
  - Check 1: CMS and NFPA 99 require an essential electrical system and a generator, not dual utility feeds.
- *Fix:* Make the second feed a recipe attribute: `dual_utility_feed` with a probability per class, placeholder (open decision: tertiary_dual_feed_share). The base row becomes one distribution_substation.

**F5. Coal generation (40% of Taiwan's 2024 output) has no fuel supplier. The gap can be closed inside the 21.** Severity **C** (for a Taiwan-calibrated or blockade-relevant world).
- *Rows:* fuel → generation (coal).
- *Problem:* Two-fifths of the generation fleet is immune to every fuel and port strike. The draft treats this as a consequence of excluding transport → power, but fuel → power *is* one of the 21.
- *Evidence:*
  - EIA Taiwan brief (coal 40%; confirmed).
  - S&P puts coal stock at about 39 days (fuel lane S24).
  - Taichung and the other coastal coal plants receive coal at their own coal harbours.
- *Fix:* This is for the design side, since it changes world content. Add `product = coal` to `import_terminal` (a coal pier or yard). Coal generation then depends on it through fuel → power (logistic or conveyor, with a long buffer of stockpile days). This adds no coupling. Otherwise, write the omission into Appendix B as a stated scope limit.

**F6. telecom → healthcare is typed "control" on evidence that does not show control.** Severity **M**.
- *Rows:* telecom → tertiary, regional, clinic, blood_bank.
- *Problem:* 42 CFR 482.15(c)(3) is an emergency-communications planning rule (Check 19). Larsen 2018 and the 62% figure are about EHR downtime from any cause (Checks 20–21). OneBlood was ransomware. None shows that loss of the *telecom layer* removes a command or monitoring signal that steers the hospital. The dissertation's own examples of control are SCADA, dispatch and ATC.
- *Fix:* Type these rows **service**. Carry the short onset for hosted-EHR sites in the buffer (`ehr_hosted` shortens it). Re-grade them: tertiary and regional as literature (mechanism) + judgment (telecom attribution); clinic as judgment. See Issue G.

**F7. water → coastal thermal: the draft conditions on cooling mode, but the presence of the edge depends on the make-up water source.** Severity **M**.
- *Row:* water → generation (coastal once-through).
- *Problem:* "Core (small volume)" asserts that essentially every coastal plant depends on the municipal system. The only source is one US plant in 1995, and that source is a study of removing the dependence through on-site desalting (Check 25). No Taiwan source was found either way.
- *Fix:*
  - Condition presence on `makeup_water_source ∈ {municipal, own_intake_or_desal}`. Cooling mode then sets only the magnitude.
  - Default: municipal, with a small requirement and a long buffer from demineralized-water storage.
  - Grade as judgment for Taiwan.
  - Record that for a Taiwan-calibrated world the water → power coupling is thin, because inland thermal plants are rare. See Issue I.

**F8. Airport power configurations are misread.** Severity **M**.
- *Row:* power → airport.
- *Evidence:* Check 15. Configurations A, B and C are assigned per lighting aid. B (a second utility source) applies only to CAT II HIRL, centreline and touchdown-zone lights. C is not "small airports".
- *Fix:*
  - Supplier: one distribution_substation. Buffer: engine generator within 15 s (Configuration A; JO 6950.2F).
  - Add a second prime source only where the airport has `cat_ii = true`.
  - Replace the lane's `airport_power_configuration ∈ {A,B,C}` with `cat_ii: bool` and `has_standby_generator: bool`.

**F9. Grades are inflated throughout.** Severity **M**. The Std grades that do not hold:
- power → exchange: FCC 07-177 never took effect.
- fuel → exchange: same (Check 18).
- fuel → tertiary: "NFPA 110 Class 96" is Joint Commission practice reported in a trade magazine (Check 2).
- water → tank_farm and depot: 1910.106(f)(8) is satisfied by extinguishers (Check 24).
- water → tertiary: the grade leans in part on a TWC news item.
- telecom → generation: COM-001-3 is a US/NERC standard, and Taipower is outside NERC.
- fuel → data_centre: Uptime Tier is an industry certification, not a code.
- fuel → clinic: "Std (by absence)" is not a grade.

*Fix:* Re-grade each as Lit or Jdg. Add a `jurisdiction` note (US / TW) wherever a US standard stands in for Taiwan practice.

**F10. Telecom-layer rows lean on IT-outage evidence, which will mis-calibrate the buffers.** Severity **M**.
- *Rows:* telecom → seaport (Kramek is about internal networks and is misquoted; Check 22), blood_bank (OneBlood ransomware), tertiary and regional (EHR downtime), transmission_substation (EMS losses, mostly internal).
- *Fix:* Keep the rows, but mark each rationale as "IT-system analogue". Do not take buffer durations from these sources. Correct the Kramek quote to its real wording.

**F11. Factual errors inside rows.** Severity **m**.
- telecom → generation buffer note: "COM-001 requires an alternative communication path". It does not require one of a Generator Operator (Check 6).
- telecom → transmission_substation Taiwan note: "Taipower ADCC covers the 161/69 kV substations (S13)". S13 does not mention ADCC (Check 9).
- transport → refinery Taiwan note: "fed from Shalun" by pipeline. The mode is not in the source (Check 12).
- The ASPR 62% figure is from Larsen 2019 (*ACI*), not the 2018 JAMIA paper.

*Fix:* Correct or strike each one.

**F12. transport → depot models an outbound delivery as an inbound dependency.** Severity **M**.
- *Row:* transport → depot (core, freight_yard).
- *Problem:* On the main island a depot's inbound supply is pipeline (CPC's 2,221 km trunk line). Road haulage is how its product reaches customers. If the row stays, it is correct only if the depot's function is defined as *delivered* fuel.
- *Fix:* State that definition in the recipe or specification. Then this row plus fuel → X carries the trucked-delivery leg as a two-hop cascade, which answers Issue B without routing (see below). The same wording applies to tank_farm's truck rack.

**F13. data_centre water "none if dry or liquid cooled" contradicts Appendix B.** Severity **m**.
- *Row:* water → data_centre.
- *Evidence:* Appendix B: compute data centres carry "heavy inbound power and water couplings".
- *Fix:* Default to evaporative. Allow `dry_or_liquid` only if Appendix B is amended, and flag it as a specification question.

**F14. fuel → seaport lists import_terminal without a product restriction.** Severity **m**.
- *Problem:* An LNG terminal cannot supply bunker oil or diesel. The fuel lane says so in its summary, but the merged row does not.
- *Fix:* Change the supplier to `import_terminal[product=oil]`.

**F15. fuel → generation (oil) is graded Lit with no source.** Severity **m**.
- *Fix:* Cite one, or grade it Jdg.

**F16. Rows carrying two types break the one-type-per-row rule.** Severity **m**.
- *Rows:* telecom → airport ("C Ctl / O Svc"); fuel → airport ("PF / L").
- *Fix:* Split each into subtype rows keyed on `towered` and `fuel_receipt`, so that every emitted row has one type.

**F17. telecom → storage "optional control".** Severity **m**.
- *Problem:* The dependent function is pump control. The lane says so ("degrades the pumps upstream, not the tank").
- *Fix:* Set the row to none and fold the level telemetry into the telecom → pumping row. See Issue H.

**F18. water → refinery "core".** Severity **m**.
- *Evidence:* About 15% groundwater and 5% seawater self-supply (DOE 2016) sit outside the layer.
- *Fix:* Keep it core, since roughly 80% draw from the layer (municipal plus river or lake), but add `water_source` so that a self-supplied refinery gets no edge.

**F19. Dependencies that are possibly missing.** Severity **m**. None is strong enough to change a row today; each belongs in the report:
- power → reservoir. Large dams have powered gates, and off-stream reservoirs are pump-filled. The brief's gravity definition holds for the "upland impoundment" class as defined.
- power → refinery. Formosa Mailiao is largely self-generating. The self_generation_share attribute proposed by the lane covers this.
- water → airport and water → seaport. Weak, but excluded by Appendix B. Keep the exclusion.

---

## 3. Agreement with the design issues A–I

| Issue | View | Recommendation |
|---|---|---|
| **A. Backup-fuel edges second-order** | **Agree, and it is not optional.** Appendix B already answers it ("the buffer has a buffer"). Ungated edges would corrupt the answer keys (F2). | Keep the edges, since the three couplings are among the 21. Give them `role = buffer_resupply`. Their only effect is to extend the power dependency's buffer, and they are active only while power → X is unserved. Do **not** fold them away into a buffer property alone: Appendix B names them as couplings, and the depot is a real node whose loss matters in a long outage. |
| **B. Trucked fuel travels over roads** | Agree the path is real (DHS Comms SSP, confirmed). Routing fuel edges over the transport layer (the lane's option a) would bring back the excluded transport → telecom and transport → water by another name. | Use the two-hop that already exists: transport → depot (defined as the delivery function, F12), then depot → consumer through fuel → X. State in Appendix B that road delivery to backup consumers is carried through the depot. No new routing is needed. |
| **C. Phase 1 "consume nothing" for rail, junctions, bridges** | Agree it contradicts the evidence and Appendix B's "rail on manual fallback". | Cheapest consistent fix: amend the Appendix B sentence to drop "and rail", or add "(rail from Phase 2)". Otherwise make rail_node an optional telecom → transport and power → transport consumer. Either way the text and the table must match. |
| **D. Coal has no supplier** | Agree it is a real hole. The draft's framing misses that fuel → power is modeled. | Add `import_terminal[product=coal]` → coal generation under fuel → power (F5). This is a design decision; otherwise state the scope limit explicitly. |
| **E. Utility private telecom** | **Strongly agree**; this is the most consequential issue. It is confirmed by DOE 2023 and by Taipower's 10,000 km of company-owned fibre. | See F1. Decide between a leased-share parameter and folding private networks into the telecom layer before any telecom → power answer key is trusted. |
| **F. Staff access to hospitals** | Agree it is real (Qureshi 2005) and has no permitted supplier. It is service, not logistic. | Declare it out of scope for Phase 1 in Appendix B. Do not bolt it onto the logistic rows. If it is added later, carry it as road-graph reachability, the same mechanism as F3(a). |
| **G. Clinical IT typed control** | **Disagree with the draft's choice.** The evidence shows EHR downtime harm, not remote command. The dissertation's own examples of control are SCADA, dispatch and ATC. | Type telecom → healthcare as **service**. Carry the hours-scale onset for hosted-EHR sites in the buffer (F6). Keep ports, refineries and depots as service. |
| **H. Storage and reservoirs are buffers** | Agree. | For water storage, a `none` row in power, fuel and telecom (F17), and use the storage node's volume as the buffer on the downstream consumers' water edge. Reservoir telecom stays optional (dam gates are real). |
| **I. Coastal thermal plants** | Agree the dependency is thin. The deciding attribute is the make-up water source, not the cooling mode. | Condition presence on `makeup_water_source`, and let cooling mode set the magnitude (F7). Grade it judgment for Taiwan. Say in Appendix B or Chapter 6 that water → power is thin in a Taiwan-like world. |

---

## 4. Where the table contradicts the Appendix B rationale

1. **"long at ports and rail on manual fallback"** (telecom). rail_node is `none` in every telecom → transport row, so the table has no rail on manual fallback.
2. **"the buffer has a buffer"** (backup-generator chain). The table records fuel → telecom, water and healthcare as ordinary core or optional edges, not as buffers of the power buffer (F2).
3. **"Compute data centers are carried … with heavy inbound power and water couplings."** The table lets data_centre have no water edge when it is dry- or liquid-cooled (F13).
4. **"Supply cross-feeds add … water to power."** Read as a bulk cooling-water feed, this is contradicted in magnitude for coastal once-through plants, which are most of Taiwan's thermal fleet. The table keeps the edge but only as a thin one (F7). It is not a contradiction of presence.
5. **"Supply cross-feeds add fuel to power."** The coupling covers gas and oil only; 40% of Taiwan's generation (coal) takes no fuel. This is not a textual contradiction, but it is a large silent carve-out that Appendix B does not state (F5).
6. **Excluded "transport → telecom" and "transport → water."** The table types fuel → telecom and fuel → water as *logistic*, which by the dissertation's own definition means "movement over the transport network". The typing leans on the excluded couplings. Resolve it with the depot two-hop wording (Issue B).
7. **"Telecom … reaches all five others on a long, node-heterogeneous buffer … losing visibility and coordination first."** The table types healthcare, water treatment and pumping, and the power classes as control, with hours-scale buffers. Water and power fit "visibility first". Healthcare, typed control on IT-downtime evidence, does not fit "long" (F6). This one is mild.

No contradiction was found for the power sentences ("short buffer … except where a generator or battery buffers it"), for "transport logistics adds transport to fuel and transport to healthcare", or for the excluded water → transport and transport → power edges.

---

## 5. Overall verdict

The draft is honest work, but it is not ready to serve as ground truth.

**What holds up:**
- No source is fabricated, and most quotes check out verbatim.
- The core/none calls for the obvious rows (power → everything that has a motor; water → hospitals; LNG terminal → gas-fired generation; seaport → import terminal) are sound.
- The lanes flagged most of their own weaknesses.

**What does not:**
- Grades and scope are inflated in about half the rows spot-checked. Planning rules, IT outages, single facilities and per-lighting-aid rules are presented as standards for a whole class.
- **Four problems would change the answer keys, not just the prose:**
  - telecom → power pointed at the public layer when Taiwan runs grid control on its own fibre;
  - backup-fuel edges treated as primary;
  - freight_yard used as a single-node stand-in for road networks;
  - a dual-substation rule for tertiary hospitals drawn from one hospital.
- Coal's missing supplier is a fifth, and it can be fixed inside the 21.

These five need design decisions before the generator encodes the table. Once they are made and the grades are corrected (F9–F11), the table would be defensible. Until then, treat it as a well-sourced draft, not a truth manifest.
