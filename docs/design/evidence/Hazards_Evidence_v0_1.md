# Storm hazards: evidence v0.1

*2026-09-30 · research lanes A (fragility by class), B (storm field shape), C (damage to function, scenarios), and an independent review · prerequisite to SyntheticWorldModel Work Order 6*

The ruling sheet is `SWM_Hazards_Ruling_Sheet_v0_1`. Read the review (last section) before relying on any lane claim: it marks 6 claims overstated and 3 grades inflated.

---

# Lane A: fragility by facility class under typhoon / hurricane hazard

Grades: S = standard or regulation, L = literature or government report, J = judgment. Jurisdiction: TW, JP, US, IN (India), INT.
Every figure below was read from the fetched source. Local copies of the PDFs are in `hazards/src/`. The one exception is Wikipedia, which is marked as a secondary source.

---

## 0. Headline findings (read this first)

1. **Links and distribution assets take the physical damage. Facilities mostly lose function.** Four sources agree: Taiwan (Taipower), Japan (the Faxai government review), US (the DOE 2005/2008 hurricane comparison) and the FCC cell-site outage data. At facilities, the usual failure is loss of grid power or backhaul, not structural damage. This matches the pilot ruling that facilities take only slight or moderate damage.
2. **For facilities, flood depth drives the damage state (storm surge on the coast, rain flooding inland). Wind mostly does not.** The one detailed facility-level flood method is FEMA Hazus Flood. It uses a step threshold (a "functional depth") plus tabulated depth-damage lookups. It does not use lognormal curves.
3. **FEMA Hazus Hurricane does not model lifelines at all**, whether by wind or by surge. For wind, it has building-type damage functions only, and those include hospitals. Anything that would drive a wind fragility for substations, masts, water, fuel or transport has to come from the literature.
4. **Published wind fragilities that come with numbers exist mainly for transmission towers and distribution poles, which are links, not nodes.** Transmission-tower median collapse speeds cluster at about 280–295 km/h 3-s gust (about 78–82 m/s). That is above any gust recorded in Taiwan in the storms I checked.
5. **Runtime arithmetic.** Hazus Flood lookups (1-ft steps, linear interpolation) and the piecewise-linear critical/collapse line model can be computed with +, −, ×, ÷ only, as published. Lognormal curves (the transmission towers of Raj et al., and the wood poles, substation wind and cell towers in the literature) need Φ(ln x). They must be stored as lookup tables with linear interpolation, precomputed offline.

---

## 1. Driving hazard by class

| Class | Driving hazard (evidence) | Mechanism of loss in the record |
|---|---|---|
| Power generation (thermal) | Coastal flood / surge, rarely. Wind: no. | DOE 2009 (US, L): "The power outages experienced during the 2005 and 2008 hurricanes were not due to power plant closings… none of the plants experienced any significant damage or flooding." Sang et al. (US, L, citing DOE 2009): "generators are usually not prone to damage by hurricanes, as they are protected in an indoor environment… a small number of issues are reported for generators due to flooding." |
| Power generation (hydro dam) | Rain flood / sediment; landslide on access | No fragility found (J). Hazus treats dams as "High Potential Loss" facilities, which get exposure analysis only. Hazus Hurricane: "Impacts to high potential loss facilities are not included in the wind or surge models." |
| Transmission / distribution substation | Flood depth (surge; also pluvial for underground rooms). Wind: minor. | DOE 2009 Table 2 (US, L), "Substations Off-line": Katrina 300, Rita 508, Wilma 241, Gustav 368, Ike 383. "Off-line" is not "damaged". Gaemi 2024 (TW, L, news, *CTEE* 2024-07-26): distribution rooms flooded in Kaohsiung (三民區山東街、大福街、苓雅區興中二路等配電室淹水), which needed pumps. |
| Distribution poles / lines (link) | **Wind, mostly through secondary impact** (trees, debris), then landslide | Faxai (JP, L, 総務省検証レポート 2020): poles failed mainly from secondary damage, 倒木や建物の倒壊（約74％）、看板等の飛来物（約14％）、土砂崩れ等の地盤影響（約12％）. Krathon 2024 (TW, L, MOEA release): 大範圍樹木倒塌壓斷或電桿傾倒; 鐵皮及招牌外物飛落碰觸桿線130處. |
| Transmission towers (link) | Wind (extreme gusts, terrain-amplified) | Faxai: towers designed for 40 m/s (10-min mean). Two collapsed under an estimated ~70 m/s peak gust and ~50 m/s 10-min mean in special terrain (JP, L/S). |
| Telecom mast (cell site) | Power loss and backhaul cut. Structural wind failure is rare. | Faxai and Hagibis (JP, L): 風を原因として倒壊した基地局はない (no base station collapsed from wind). FCC Ian (US, L): 2.3% of outaged sites were down because of damage (see §3). |
| Telecom exchange / data centre | Flood (basement plant); grid power | Faxai MIC report no. 9: 主な停波原因は伝送路断及び停電 (main causes: transmission-line cut and power loss). No fragility with numbers found. Hazus lists communications offices as "Mapping Only" in the Flood model. |
| Cable landing | Coastal surge / wave; no data | None found (J). I searched Hazus and the literature named above. |
| Water: reservoir | Rain → turbidity (raw water quality), not structural | Soudelor (TW, L-secondary, Wikipedia): Nanshi River turbidity "reached record levels in just two hours", overwhelming purification; water cut to 429,248 homes. |
| Water: treatment / pumping / storage | Flood depth; **grid power** | Hazus Flood gives pumping plants and treatment a functional depth of 4 ft (§2). Faxai: water outage 139,744 homes, attributed to the long power outage (この長期間にわたる停電の影響により…断水). |
| Transport: bridge | Rain flood (scour, debris, deck washout) | Morakot 2009 (TW, L): "Approximate 200 highway bridges in Taiwan are damaged" (Wang & Wang, CECI). Hazus Flood models bridges by scour only. |
| Transport: seaport / airport | Surge / waves (coastal) | Jebi 2018 (JP, L, nippon.com): Kansai airport "runways were flooded by the storm surge", closed from 4 Sep and partly reopened on 7 Sep. The access bridge was struck by a tanker. Hazus: ports and airports "not analyzed". |
| Transport: freight yard | Flood depth | None found (J). |
| Fuel: refinery / terminal / tank farm / depot | Surge flood (2005); **power loss** (2008) | DOE 2009 (US, L): "Although some refinery shutdowns lasted from two to three weeks, these outages were primarily caused by lack of electricity supply rather than on-site damage." Rita 2005: "Due to severe damage and flooding, more than 2 MMBD… remained offline two weeks after". |
| Healthcare: hospital / clinic / blood bank | Grid power (function); flood depth (structure). Wind: roof and window damage only. | Hazus Hurricane §8.1.8.4 (US, L): hospitals in the Ike survey "were noted to have closed due to lack of power, but most had emergency back-up power in place". Faxai (JP, L): DMAT moved patients out of fully blacked-out hospitals (完全停電の病院や自家発電稼働病院における搬送需要). The review concluded that emergency power and fuel at hospitals were insufficient. |

---

## 2. Published fragility and damage functions

### 2.1 FEMA Hazus Flood (Hazus 6.1 Flood Technical Manual, July 2024; Inventory Technical Manual 6.1). US, L.

- **Curve form:** percent damage against depth (ft) above equipment height, tabulated in 1-ft steps with linear interpolation. "Utility System Components reach maximum damage at 10 feet of flooding." Functionality is a **step at the functional depth**: "If the depth of flooding at the component location exceeds the functional depth threshold by 0.1 feet or more, the component will be considered non-functional." *No median or dispersion.* The whole thing needs arithmetic only.
- **Where the damage functions come from:** the USACE New York District 1985 Passaic River studies included "models for 10 utility facilities, such as electric power substations, pump houses, and water treatment plants". The values themselves sit in the software's Damage Functions dialog, not in the manual. The one example given is the wastewater default WDFLT: **27% damage at 5.5 ft above equipment height**, and roughly 40% at the 10 ft cap, read from Fig 10-1. I did not retrieve the other utility tables numerically.
- **Default parameters (Inventory Tech. Manual Tables 10-5, 10-7, 10-9, 10-11, 10-13):**

| Hazus class | Equipment height (ft) | Functional depth (ft) | Analysed? |
|---|---|---|---|
| Substations ESSL/ESSM/ESSH; power plants EPPL/EPPM | 0 | 4 | **No.** "Component is not analyzed in the flood model, mapping only". Footnote 28: electric damage functions exist "however, these damage functions are not enabled" |
| Potable water pumping plants PPPL/M/S, wells | 0 | 4 | Yes |
| Wastewater treatment WWTL/M/S | 0 | 4 | Yes |
| Refineries ORFL/M/S | 0 | 4 | Yes |
| Oil pumping plant OPP; tank farm OTF | 0 | 0 | Yes. Tank farm note: "Assume tank bottom is at grade and tanks will not float." |
| Hospitals EFHS/M/L, medical clinic EFMC (Table 7-15) | first floor 3 ft; COM6/COM7 building curves | **0.5** | Yes |
| Communications offices / broadcast | none | none | Mapping only |

- **Bridges (Table 9-2):** probability of failure, used as damage, applies only to scour-critical bridges (NBI scour index 1–3 or U) that are inundated. Depth has no effect ("The depth and type of flooding do not impact results"). Single-span, 100-yr flood: 5% / 2% / 1% for scour index 1 / 2 / 3. At 500-yr ×2, at 1,000-yr ×1.5 again. Continuous spans are 25% of those values. Hazus calls these relationships "estimates based on the best available information and expert opinion… not been calibrated."
- **Hospital restoration (Table 8-1):** maximum days to restoration is 360 / 540 / 720 / 900 for depth bands −4–0 / 0–4 / 4–8 / 8–25 ft. These bands dwarf a 72-h window. Repair times are already decided from MR4, so this is for context only.

### 2.2 FEMA Hazus Hurricane (Hazus 6.1 Hurricane Model Technical Manual). US, L.

- **Scope, verbatim:** "Transportation systems… Impacts to transportation systems are not included in the wind or surge models." "Utility systems… Impacts to utility systems are not included in the wind model." Essential facilities (hospitals) are handled building by building for wind; the surge model gives percent damage; "Hazus does not provide a combined wind and surge damage or loss for essential facilities."
- **Hospitals:** wind damage uses the steel-commercial building models. Damage states follow the strip-mall definitions (Table 5-61): 0 none (roof cover ≤2%), 1 minor, 2 moderate, 3 severe, 4 destruction. The curves are tabulated against peak gust (PGWS, mph) in the software, not given as lognormal parameters. Tables 5-94 to 5-96 give only per-storm average damage state.
- **Hospital loss of function:** "Modeled loss of function of a day is assumed to occur close to 1% of the building's value (roof cover cost)." Calibrated to phone surveys after Ike 2008, Ivan 2004 and Charley 2004 (the HMTAP 440 data).
- **Damage-state naming mismatch.** Hazus Hurricane uses *none / minor / moderate / severe / destruction*. The brief's *slight / moderate / extensive / complete* are the Hazus Earthquake (MR4) names. Mapping one set onto the other is a J choice for the design side.

### 2.3 Transmission towers (link). Wind, lognormal in gust speed.

Raj, Kumar & Bhatia (arXiv 2107.06072). Empirical, from Cyclone Fani 2019 in Odisha: 87 towers collapsed and 41 partially damaged. IN, L. IM = 3-s gust, km/h. Table 1, 50th percentile, combined uncertainty:
- Functionality disruption: median **280.4 km/h** (77.9 m/s), β **0.088**
- Collapse: median **292.5 km/h** (81.3 m/s), β **0.104**
- Their comparison table recomputes other published curves as median / β: Quanta Technology (2009, Texas hurricanes 1999–2008) 284 / 0.035; Panteli et al. (2017, UK) 294 / 0.25; Fu et al. (2019, China) 223.5 / 0.04. These are "evaluated based on 50th percentile… and… 84th percentile" of the original curves.
- **Japanese design reference (JP, S via L):** 技術基準で求められる風圧荷重 40m/s（10 分間平均風速）. The Faxai collapse was at an estimated 最大瞬間風速約 70m/s、10 分間平均風速約 50m/s. That is one real failure at about 252 km/h gust, below the Fani median. It shows terrain speed-up and the dispersion in practice.
- Range: medians run 223–294 km/h. **Centre: about 285 km/h gust, β about 0.10** for collapse (Quanta and Fani are both empirical from hurricanes or cyclones). For a Taiwan pilot, any storm that stays below about 210 km/h gust gives near-zero tower failures. That fits the Taiwan record, where recorded failures are poles, not towers. **Runtime:** lognormal, so store it as a table.

### 2.4 Transmission line segments, piecewise-linear by voltage. US, L.

Poudyal et al. (arXiv 2311.15118), in the Panteli style: P = 0 below v_crit, rising linearly to 1 at v_col (maximum sustained wind, m/s):

| kV | v_crit (m/s) | v_col (m/s) |
|---|---|---|
| 115 | 25 | 55 |
| 161 | 30 | 60 |
| 230 | 35 | 65 |
| 500 | 45 | 75 |

This form is **directly arithmetic-only**. The values are the authors' assumptions, not empirical, so treat them as L-weak.

### 2.5 Distribution poles (link). Wind, lognormal.

Serrano-Fontova et al. 2023 (IEEE Access 11, review; INT, L) compares class-5 wood-pole curves at a 3-s gust of 100 mph (44.7 m/s). Failure probability for new poles is **0.02 / 0.08 / 0.12**, and for old poles **0.1 / 0.2 / 0.9**. The three curves are Darestani & Shafieezadeh 2019 [73], Shafieezadeh et al. 2014 [74] and Lee & Ham 2021 [81]. Per-curve medians and β were not given as numbers in the review, and I did not retrieve the original papers. The field record (Faxai) says most pole failures are **secondary** (about 74% trees and buildings falling on them). A structural pole curve therefore under-predicts, and a tree-exposure term matters more than pole class.

### 2.6 Substations under wind

Winkler et al. 2010 (RESS 95, doi 10.1016/j.ress.2009.11.002) used "log-normal fragility curves for substations and utility poles" built from "HAZUS-MH 3 Internal Data Files". Watson & Etemadi 2020 (cited in PNNL-33587) use a lognormal against 3-s gust, again from Hazus internal tables. **I did not retrieve the numbers** because the source is paywalled or the data is internal. Evidence that wind matters little at substations comes from §1 (they go off-line rather than get damaged). Recommendation (J): no wind fragility for substation nodes in the pilot; use flood depth only.

### 2.7 Cell towers / masts

Lognormal wind curves exist: Bilionis & Vamvatsikos 2019 for a 48 m Greek tower, and Tian et al. 2020 for a 60 m tower, both cited in PNNL-33587. Numbers not retrieved. The empirical record says structural collapse is negligible. Japanese masts are designed to the Building Standard Act's regional base wind of at least 40 m/s. Recommendation (J): make mast state depend on power and backhaul, not on wind fragility.

### 2.8 Water, fuel, data centre, cable landing, port, airport, freight yard, blood bank

Beyond the Hazus Flood thresholds in 2.1, **none found** for typhoon or hurricane hazards. PNNL-33587, a compendium: "Ports: Not specifically addressed; Airports: Not specifically addressed; Fuel tank farms/terminals: Not specifically addressed"; its water entries are earthquake only.

---

## 3. Taiwan and Japan (and US) outage evidence

**Taiwan (Taipower; news and ministry releases, L):**
- Soudelor 2015: peak 4.85 million households without power (Wikipedia, secondary; this was the record). Earlier same-day counts in the press: 3.84 million on 8 Aug (*Epoch Times*) and 4.34 million on 10 Aug (*CTEE*). Cause: 部分配電線路受斷落樹木及招牌壓損、部分輸電線路亦受強風影響跳脫 (transmission lines *tripped*, not collapsed). About 1,000 poles down, per CNA 2025 citing it as the previous record. Water cut to 429,248 homes and landline to 64,992 (Wikipedia). Peak gust 211 km/h at Pengjia Islet.
- Danas 2025: about 1 million households; **2,454 poles** snapped or toppled (CNA, 10 Jul 2025, a new record, more than twice Soudelor). The later total is 電桿倒斷及流失約3499支 with 1,009,238 households (*GVM*, 21 Jul 2025). Base stations affected in Chiayi: 551, with 542 restored by 1 Aug. Tower structural damage was mentioned only for Zhuqi (主塔損毀嚴重).
- Krathon 2024 (Kaohsiung and Pingtung): 294,625 households. In Pingtung: 9 poles broken, 45 tilted, 91 lines severed, and 130 debris strikes on lines (MOEA).
- Gaemi 2024 (Kaohsiung): 47,647 households; distribution rooms and 6 basements flooded (*CTEE*).
- Morakot 2009: rain-driven, over 2,500 mm. About 200 highway bridges damaged, through scour, debris, deck washout and burial (Wang & Wang, CECI).
- **Gap:** I could not retrieve NCC counts of base stations by cause for a typhoon (the NCC pages render with JavaScript). No Taiwan hospital-impact data was found.

**Japan:**
- Faxai 2019 (Chiba): peak **934,900 households**; about 2,000 poles broken (電柱約2,000本が折損, TEPCO); **2 towers** collapsed; about 280 h to 99% restoration. Water: 139,744 homes. Pole-failure causes were 74% trees and buildings, 14% flying debris and 12% landslide. Mobile outages were caused by long power outage exhausting backup power (非常用電源が維持できない) and by line cuts. No base stations collapsed from wind.
- Noto 2024 is an earthquake, not a typhoon, but it gives a useful cause split: 基地局の主な停波原因は、７割弱が停電、６割弱が伝送路断（複合要因が３割弱）. That is 0.7 power, 0.6 backhaul and 0.3 both, per the 情報通信審議会 2024 report.

**US:**
- Gulf 2005/2008 (DOE 2009, Table 2): poles destroyed: Katrina 72,447, Rita 14,817, Wilma about 14,000, Gustav 11,478, Ike 10,300. Transmission structures damaged: 1,515 / 3,550 / NA / 241 / 238. Substations off-line: 300 / 508 / 241 / 368 / 383. "The prime cause of electricity outages… was damage to the electricity transmission and distribution systems."
- Ian 2022, FCC DIRS on 30 Sep 2022, about 2 days after landfall: 1,096 of 14,188 cell sites out: **damage 25 (2.3%), transport 320 (29%), power 751 (69%)**. Another 466 sites were up on backup power. In Lee County, at the landfall point, 1 of 145 outages was due to damage. By 5 Oct: 153 out, of which damage 12, transport 52 and power 89.
- Michael 2018 (FCC, via *Urgent Comms*): power-caused cell failures were mostly fixed within 48 h; backhaul failures (for example "at least 33 separate fiber cuts") caused the extended outages.

---

## 4. Do links carry the damage? Yes.

- In every storm with an asset breakdown, damaged-unit counts for poles, lines and towers are 10² to 10⁴ times the counts of damaged facilities. Soudelor: about 1,000 poles, towers only tripped. Danas: 2,454 to 3,499 poles. Faxai: about 2,000 poles and 2 towers. Katrina: 72,447 poles against 300 substations *off-line*. DOE names T&D as "the prime cause".
- Telecom node outages are driven by power and backhaul: US Ian 69% power and 29% transport against 2.3% damage. JP Noto: about 70% power and 60% backhaul. JP Faxai: zero wind collapses of masts.
- Water outages follow power (Faxai) or raw-water turbidity (Soudelor), not plant damage.
- Refinery outages in 2008 followed power loss; in 2005 they followed flood damage (surge).

**What this implies for the pilot (J, for the design side; not a ruling):** a storm acting only on nodes will understate real disruption. Most of the realistic signal comes from (a) wind on distribution and power links, dominated by tree exposure, and (b) the facility's dependency on power and backhaul within the 72 h window, set against its backup duration. Physical node damage (slight or moderate) comes mainly from flood depth, and wind contributes only for building envelopes (hospital roofs).

---

## 5. Runtime-arithmetic notes

- Lognormal curves (§2.3 towers, and §2.5–2.7 if adopted): precompute Φ(ln(x/θ)/β) offline into a gust-indexed table (for example every 5 km/h, the Hazus convention being 5 mph). Interpolate linearly at runtime. Quantise the stored values.
- Hazus Flood: already a 1-ft lookup with interpolation, plus a step at the functional depth, so no change is needed.
- Piecewise-linear line model (§2.4): arithmetic-only as published.
- Hazus Hurricane building curves: tabulated against gust in the software. They would have to be exported as a table. The manual does not print them.

---

## 6. Summary table

| Class | Driving hazard | Curve source | Median / dispersion per damage state | Grade | Jurisdiction |
|---|---|---|---|---|---|
| Generation, thermal | Coastal flood (rare); not wind | Hazus Flood EPPL/EPPM (not enabled); DOE 2009 | Step: functional depth 4 ft, equipment height 0 ft; no median/β | L | US |
| Generation, hydro dam | Rain flood / landslide | Hazus: HPL, exposure only | none found | J | US |
| Transmission substation | Flood depth | Hazus Flood ESSH (mapping only); Winkler 2010 wind (not retrieved) | Step: functional depth 4 ft; wind: none retrieved | L (flood) / J (wind) | US |
| Distribution substation | Flood depth (incl. underground rooms) | Hazus Flood ESSL/ESSM; Gaemi 2024 | Step: functional depth 4 ft; none | L | US / TW |
| Telecom exchange | Grid power; flood | Hazus (mapping only); MIC Faxai | none found | L (evidence) | JP / US |
| Telecom mast | Power + backhaul; wind negligible | FCC Ian; MIC Faxai; Bilionis & Vamvatsikos 2019 (not retrieved) | none retrieved; empirical: 2.3% of outages from damage (Ian); 0 wind collapses (Faxai) | L | US / JP |
| Data centre | Grid power; flood | none | none found | J | — |
| Cable landing | Surge / waves | none | none found | J | — |
| Water reservoir | Rain → turbidity | Soudelor record | none found | L (evidence) | TW |
| Water treatment | Flood depth; power | Hazus Flood WWTx / potable defaults | Step: functional depth 4 ft; % damage table (WDFLT 27% at 5.5 ft above equipment, max ~40% at 10 ft) | L | US |
| Water pumping | Flood depth; power | Hazus Flood PPPL/M/S | Step: functional depth 4 ft; % table (not retrieved numerically) | L | US |
| Water storage | Flood depth | Hazus Flood potable tanks (defaults not retrieved) | none retrieved | L | US |
| Seaport | Surge / waves | Hazus: not analysed; Jebi (Kansai) | none found | J / L (evidence) | JP |
| Airport | Surge / waves | Hazus: not analysed; Jebi | none found | L (evidence) | JP |
| Freight yard | Flood | none | none found | J | — |
| Bridge | Rain flood (scour, debris) | Hazus Flood Table 9-2; Morakot | P(failure) given scour-critical and inundated: single span, 100-yr: 5 / 2 / 1% (scour index 1 / 2 / 3); ×2 at 500-yr; ×1.5 again at 1,000-yr; continuous span = 25% | L | US / TW |
| Fuel import terminal / tank farm | Surge flood; power | Hazus Flood OTF, OPP | Step: functional depth 0 ft, equipment height 0 | L | US |
| Refinery | Surge flood (2005); power (2008) | Hazus Flood ORFx; DOE 2009 | Step: functional depth 4 ft | L | US |
| Fuel depot | Flood | (use tank-farm defaults, J) | none found | J | — |
| Hospital (tertiary / regional) | Power (function); flood (structure); wind (envelope) | Hazus Flood EFHx; Hazus Hurricane §5.6.8.4, §8.1.8.4 | Flood: functional depth 0.5 ft, first floor 3 ft, COM6 curve. Wind: tabulated against PGWS (not in manual); 1 day loss of function at ~1% building loss | L | US |
| Clinic | as hospital | Hazus Flood EFMC | Functional depth 0.5 ft, COM7 | L | US |
| Blood bank | Power (cold chain) | none | none found | J | — |
| Link: transmission tower / line | Wind (gust) | Raj et al. (Fani); Quanta 2009; Panteli 2017; Fu 2019 | Collapse 292.5 km/h, β 0.104; functionality disruption 280.4 km/h, β 0.088 (3-s gust); others 223.5–294 km/h, β 0.035–0.25. Centre ≈285 km/h, β≈0.10 | L | IN / US / UK / CN; JP check |
| Link: transmission line segment | Wind (sustained) | Poudyal et al. 2023 | Piecewise-linear: v_crit / v_col = 25/55 (115 kV), 30/60 (161), 35/65 (230), 45/75 (500) m/s | L (assumed values) | US |
| Link: distribution pole / line | Wind, via trees and debris (74% / 14%) + landslide (12%) | Serrano-Fontova 2023 review of [73][74][81]; Faxai review | P(fail) at 100 mph gust: new 0.02–0.12, old 0.1–0.9; medians not retrieved | L | INT / JP / TW |
| Link: road | Landslide, flood, fallen trees | Faxai (tree blockage), Morakot | none found | J | — |
| Link: telecom line | Wind via trees / poles | MIC Faxai; FCC Michael | none found | L (evidence) | JP / US |
| Link: water main | Landslide / bridge loss | Hazus (mapping only) | none found | J | — |

## 7. Open items for the design side

1. Map Hazus Hurricane *minor / moderate / severe* and Hazus Flood *% damage* onto the brief's *slight / moderate / extensive / complete*. This is J, and the design side needs to decide it.
2. Decide whether the pilot storm acts on links (poles, lines, roads) as well as nodes. The evidence says most real disruption is there.
3. Decide whether facility state should be a conditional function of power and backhaul plus backup duration, rather than a fragility draw.
4. The Taiwan data gaps listed above: NCC base-station outages by cause, a Taipower asset-level breakdown for each typhoon, and hospital impacts.


---

# Lane B: the spatial shape of a typhoon hazard field (built with +, −, ×, ÷, sqrt only)

Grades: **S** = standard or regulation, **L** = literature or government report, **J** = judgment (what was looked for is stated). Jurisdiction: TW / JP / US / INT.
"Fetched" means the source was retrieved in this session. Any quote not fetched is labelled as such.

---

## 1. Parametric wind profiles

Symbols: V(r) is the wind at radius r from the storm centre, Vm is the maximum wind, Rm is the radius of maximum wind.

| Profile | Formula | Typical parameters | Permitted operations only? |
|---|---|---|---|
| **Rankine / modified Rankine** | V = Vm·(r/Rm) for r ≤ Rm; V = Vm·(Rm/r)^x for r > Rm | x = 0.5 by default in TCRM. Its source code says: *"The literature indicates 0.4 < alpha < 0.6 (e.g. see Holland, 1980)"* ([Geoscience Australia TCRM, `wind/windmodels.py`, RankineWindProfile](https://github.com/GeoscienceAustralia/tcrm/blob/master/wind/windmodels.py)). L, INT (AU) | **Yes, if x is a multiple of 1/4.** x = 0.5 is `sqrt(Rm/r)`. x = 0.25 is `sqrt(sqrt(.))`. x = 0.75 is the product of those two. Other values of x need a table. |
| **Jelesnianski (1965)** | V = 2·Vm·Rm·r / (Rm² + r²) | Only Rm and Vm | **Yes. It is purely rational.** Source: TCRM `JelesnianskiWindProfile` code (fetched). L, INT. The outer decay is 1/r, which is steeper than x = 0.5. |
| **Holland (1980)** | Cyclostrophic normalised form: V = Vm·sqrt[(Rm/r)^B · exp(1 − (Rm/r)^B)] ([Willoughby & Rahn 2004, MWR 132, eq. 4](https://faculty.fiu.edu/~willough/PUBS/HEW&RAHN_04.pdf); the fetched text lost its bracket, and I have written the standard form here) | B: *"mean and standard deviation are 1.31 ± 0.36"*, fitted on 0.5 < B < 2.5. RMW: *"geometric mean radius of maximum wind for the complete sample is 47.5 km"* (Willoughby & Rahn 2004). Also B = 1.881 − 0.00557·RMW − 0.01097·lat, sB = 0.286 (Powell et al. 2005, quoted in [Vickery et al. 2009, *Hurricane hazard modeling*](https://www.aoml.noaa.gov/hrd/Powell/HurrHaz_2009.pdf)). L, US | **No.** It needs exp and a non-integer power. **Tabulate it:** store g(u) = u^B·exp(1 − u^B) on a fixed grid of u = Rm/r in [0, 1] and [1, u_max] for each stored B, and interpolate linearly. The table is built offline and checked into the rules registry as quantised decimals. The runtime only does a lookup plus sqrt. |
| **Willoughby et al. (2006)** | Inner: V = Vm·(r/Rm)^n for r ≤ R1. Outer: V = Vm·[(1−A)·e^((Rm−r)/X1) + A·e^((Rm−r)/X2)] for r ≥ R2, with X2 = 25 km. Transition: blend with the weight w(ξ) = 126ξ⁵ − 420ξ⁶ + 540ξ⁷ − 315ξ⁸ + 70ξ⁹, where ξ = (r−R1)/(R2−R1). R2 − R1 = 25 km (15 km if Rm ≤ 20 km). | Rm = 46.4·e^(−0.0155·Vmax,G + 0.0169·abs(lat)); X1 = 317.1 − 2.026·Vmax,G + 1.915·abs(lat); n = 0.4067 + 0.0144·Vmax,G − 0.0038·abs(lat); A = 0.0696 + 0.0049·Vmax,G − 0.0064·lat (A < 0 is set to 0). Winds in m/s, distances in km. Source: [stormwindmodel "Details" vignette](https://github.com/geanders/stormwindmodel/blob/master/vignettes/Details.Rmd), citing Willoughby et al. 2006, MWR 134, eqs 1a, 4, 7a, 10a–c. This is a secondary source; the AMS original returned 403. L, US | **Partly.** The transition polynomial is permitted. The r^n and exp terms are not. Root-finding for R1 is iterative but uses only permitted operations. **Tabulate** the exp terms as e^(−k) on a fixed grid of k. For a stored n, (r/Rm)^n is tabulated the same way. |

**Note on the pilot's scale.** The pilot world is about 400 km², which is roughly 20 × 20 km. That is smaller than one RMW (about 30–50 km). Within the world, the profile only sets a gradient of roughly ±30% across the island. The choice between the Rankine x = 0.5 profile and Holland matters much less than the storm-centre distance and the terrain factors. (J: I compared the profile shapes over 0 to 2·Rm.)

## 2. How terrain modifies the field

**Sea to land (surface roughness).**
- Marine surface to gradient wind: *"mean modeled value of U10/Umax … is 0.716"* near the RMW. Outside it, the mean ratios are 0.698 (observed) and 0.686 (modelled). Sea to open land: *"the maximum reduction in the mean wind speed … using the ESDU model is about 17%"*. So land/sea is about 0.83. The transition fetch was reduced to 20 km, and *"at a distance of about 1 km approximately 60% of the transition … has already occurred"*. Source: [Vickery, Powell et al. 2009, JAMC 48](https://www.aoml.noaa.gov/hrd/Powell/Vickery_Powell_Diraj_2009.pdf). L, US.
- Gradient to surface reduction factor f_r = 0.9 over water and 0.72 over land ("80% of that"). Source: Knaff et al. 2011, Fig. 3, via the stormwindmodel vignette (fetched; secondary). This gives land/sea = 0.80. L, US.
- **Taiwan building wind code** (建築物耐風設計規範, 內政部, revised 2014 and in force from 2015-01-01; [TKU copy](https://windexpert.ce.tku.edu.tw/newcode/Dfiles/New_wind_code.pdf), fetched). Table 2.2 sets the power-law exponent α and the gradient height zg for 10-min mean winds:
  - 地況 A (city centre): α = 0.32, zg = 500 m
  - 地況 B (suburb or town): α = 0.25, zg = 400 m
  - 地況 C (open ground, *"海岸或湖岸地區"*, i.e. coast or lakeshore areas): α = 0.15, zg = 300 m
  - Commentary: *"地況 A、B 與 C，相對於 10 分鐘平均風速之α值分別取為 0.32、0.25 與 0.15"* (for terrain classes A, B and C, α is taken as 0.32, 0.25 and 0.15 for 10-min mean winds). Gradient wind = (300/10)^0.15·V10(C) = *"1.666 V10(C)"*.
  - **S, TW.**
  - Derived by me from the code's formula (J-arithmetic on S inputs), for the 10 m wind as a ratio to class C: **C = 1.000, B = 0.662, A = 0.476.** These are three constants. Store them in the registry; no runtime power is needed.
- **Topographic speed-up** on isolated hills and ridges: K_zt = (1 + K1·K2·K3)², where K1, K2 and K3 come from code Tables 2.3(a–c) (Taiwan code §2.6). This applies to hilltop masts and exchanges. It is a tabulated form, so it is permitted. **S, TW.** Note that K_zt multiplies pressure. The wind multiplier is (1 + K1·K2·K3).

**Central Mountain Range (CMR) and the lee side.**
- CMR size: *"average elevation of about 3000 m and a dimension of 300 km × 100 km"* ([Wu & Kuo 1999, BAMS 80, p. 67](https://typhoon.as.ntu.edu.tw/wu_paper/1999-wu-kuo.pdf)). L, TW.
- Storm-wide weakening: *"westbound typhoons tend to move cyclonically around the northern side of the CMR and experience an average intensity decrease of over 40%, beginning about 12 h before the storm centers reach the island"* (Wu & Kuo 1999, citing Brand & Blelloch 1974, MWR 102, 708–713). **About 60% or less of the intensity is retained across the island.** L, TW.
- Case study: Typhoon Herb (1996). *"measured surface wind near the storm's center dropped from 53 to 44 m s⁻¹ in 6 h"* and the storm *"weakened by 24 hPa during the 7-h period its center was over land"*. That is **about 83% retained after 6 h over land.** L, TW.
- Track: *"deflections tend to be larger for weaker and slower-moving storms"*. *"Mesoscale secondary low centers can form on the lee side of the CMR"* (Wu & Kuo 1999). I found no deflection distance in km that I could fetch; the Lin et al. papers returned 403 or 429. For a 20 km world, deflection only changes where the straight corridor sits. **J: treat the track as straight.**
- Lee-side station winds: winds are *"relatively small when the stations are in the leeside of the mountain of the cyclonic flow"*. Taipei gusts follow *"Vg=0.45+2.38Vm"* ([Yeh, Shieh & Wu, AMS 26th Hurricanes conf., 13D.5](https://ams.confex.com/ams/pdfpapers/75845.pdf)). L, TW. **No published lee-side retention fraction was found.** I looked in Wu & Kuo 1999, Yeh et al., and the MDPI Atmosphere 2018 paper on westward typhoons (which describes the "sheltering effects of western Taiwan" but gives no ratio).

**Inland decay over time.**
- Kaplan & DeMaria (1995), J. Appl. Meteor. 34: V(t) = Vb + (R·V0 − Vb)·e^(−αt). The form is confirmed from the NHC/Kaplan 2007 slides and Frontiers 2021. The US parameter values (R, α, Vb) **could not be verified by fetch**, so none are given here.
- DeMaria et al. (2006) revised the model for islands and peninsulas by scaling decay with the fraction of the storm over land (NHC slides, fetched). L, US.
- For the pilot, the storm crosses 20 km in about 1–2 h, so time decay is second-order. **J: omit it, or fold it into the lee factor.**

## 3. Rain-driven flood susceptibility from terrain

- **HAND** (Height Above Nearest Drainage). Nobre et al. 2011, J. Hydrol. 404, 13–29 ([PDF](https://lerf.eco.br/img/publicacoes/2011_0811%20Height%20Above%20the%20Nearest%20Drainage%20a%20hydrologically%20relevant%20new%20terrain%20model.pdf)): classes are waterlogged < 5.3 m, ecotone 5.3–15.0 m, and upland > 15 m (*"5.3 m and 15.0 m as the best thresholds"*). L, INT (Brazil). HAND is computed with a D8 flow walk and subtraction only, so it is permitted.
- HAND flood classes from Santos et al. 2021, Floresta e Ambiente 28(2) ([SciELO](https://www.scielo.br/j/floram/a/YQScj8XGqKqtMTBLbHRkjFw/?format=html&lang=en)): *"Very high: 0-3 m; High: 3-7 m; Medium: 7-12 m; Low: 12-15 m; Very low: >15 m"*. The authors say this was not validated against observed floods. L, INT.
- Ranking of conditioning factors: curvature, elevation and slope rank highest; distance to river ranks 8th of 13 (Al-Kindi & Alabri 2024, Earth Syst. Environ. 8, 63–81; Oman). L, INT. Rankings are site-specific. I found no Taiwan ranking I could fetch.
- **Taiwan practice:** the Water Resources Agency (經濟部水利署) third-generation flood potential maps (2014–15) are built from *"24小時之雨量"* (24-hour rainfall) scenarios of 300, 450 and 600 mm, *"基於設計降水條件、特定地形地貌資料及客觀水理模式演算模擬"* (simulated from design rainfall, terrain data and hydraulic models) ([NCDR 3D 災害潛勢地圖](https://dmap.ncdr.nat.gov.tw/1109/disaster-topics/)). **S/L, TW.** These three rainfall levels give a natural scenario ladder.
- Terrain enhancement of rain: the CMR *"substantially increas[ed] the total rainfall produced by Typhoon Herb (by almost a factor of 3)"*, with a *"maximum 24-h rainfall of 1798 mm over the CMR"* (Wu & Kuo 1999). L, TW.

**Centre I would take:** use HAND as the single flood index. It combines elevation and distance to river in one hydrologically meaningful number. Set flood-prone as HAND < 5.3 m (Nobre), with graded sub-classes at 3 and 7 m (Santos). Add slope only as a mask (flat, slope < 7.6%, which is Nobre's plateau/slope split) so that steep channel-side cells are not flagged.

## 4. Spatial correlation and correlated random fields

**Published correlation lengths.** I found no fetchable, citable figure in km for a wind-residual or flood-damage correlation length. I looked in:
- the Vickery 2009 hazard review, which states the model error term is *"un-correlated"* with a *"coefficient of variation of 10%"* (Vickery et al. 2009a);
- the ResearchGate paper "Spatial Correlation and Wind Speed Uncertainties of Hurricane Wind Field Model" (429 on every attempt);
- Metin et al. 2020 NHESS 20:967 (no km value);
- Li et al. 2016 Struct. Safety 59 (correlation between successive storms, not in space);
- the WegenerNet rain study (O & Foelsche 2019 HESS 23:2863), where the correlation distance varies with season and timescale and no single value is given;
- the Chenyulan watershed radar-rain kriging paper (Chen et al. 2020 Remote Sens. 12:1427; spherical variogram, range not stated).

**So the correlation length is J.** In a parametric field, most spatial correlation is carried *deterministically* by the track and profile. Residual noise only needs a short range.
- Proposal: range c = 10 km for wind residual (J, about Rm/4, which smooths within one district). Use the 10% coefficient of variation from Vickery 2009a (L, US) as the amplitude.
- Flood residual range: 3–5 km (J, the scale of a small sub-catchment in the 450 km² Chenyulan).
- Both go to the registry as `placeholder (open decision: hazard_correlation_length)`.

**Compact-support kernels** (Wendland 1995, AICM 4; generalised form from [Bevilacqua, Faouzi, Furrer & Porcu 2019, Ann. Stat. 47(2)](https://arxiv.org/pdf/1607.06921), fetched). Let t = distance / c, and (·)₊ = max(·, 0).
- Askey: (1 − t)₊^μ. This is positive definite in ℝ^d iff μ ≥ (d+1)/2.
- κ = 1: (1 − t)₊^(μ+1)·(1 + (μ+1)·t), valid for μ ≥ (d+1)/2 + 1. **In 2-D, μ = 3 gives φ(t) = (1 − t)₊⁴·(1 + 4t).** This is the classic Wendland φ₃,₁ (C² smooth).
- κ = 2: (1 − t)₊^(μ+2)·(1 + (μ+2)·t + t²·(μ² + 4μ + 3)/3). **In 2-D, μ = 4 gives φ(t) = (1 − t)₊⁶·(1 + 6t + 35t²/3)** (C⁴).
- Both are polynomials, so only + − × ÷ are used. Distance needs sqrt. **All permitted.**

**Drawing the field with permitted operations** (J, method only; standard linear algebra):
1. Build the n × n covariance matrix at facility locations, C_ij = σ²·φ(d_ij/c). For the pilot, n = 24.
2. Take the Cholesky factor L. It uses only + − × ÷ and sqrt. Write the loop explicitly in a fixed order, not with LAPACK, so the summation order is fixed.
3. Set the field to L·z, where z is a vector of standard normals.
4. Box–Muller and polar methods need log, cos or sin, so they are not permitted. Use either:
   - the Irwin–Hall sum of 12 uniforms minus 6 (exact mean 0 and variance 1; tails truncated at ±6 — fine for 10% noise), or
   - a stored inverse-normal table indexed by a uniform.
5. Grid points (for maps) can be done the same way, or with a kernel-convolution sum Σ φ(|x − s_k|/c)·z_k over a coarse lattice s_k.

## 5. Intensity categories for Taiwan, and averaging periods

**CWA (formerly CWB) intensity classes** (["An overview of the tropical cyclone database at the Central Weather Bureau of Taiwan", 2022, Springer s44195-022-00023-1](https://link.springer.com/article/10.1007/s44195-022-00023-1), fetched; the author list was not retrieved, so cite it by title and DOI):

| CWA class | Maximum sustained wind (10-min) | Beaufort |
|---|---|---|
| Tropical depression 熱帶性低氣壓 | < 17.2 m/s | ≤ 7 |
| Mild typhoon 輕度颱風 (the paper says "tropical storm") | 17.2–32.6 m/s | 8–11 |
| Moderate typhoon 中度颱風 | 32.7–50.9 m/s | 12–15 |
| Strong typhoon 強烈颱風 | ≥ 51.0 m/s | ≥ 16 |

- Quote: *"maximum sustained wind (10-min-averaged) below 17.2 m s−1 … A tropical storm has wind speeds between 17.2 and 32.6 m s−1. A moderate typhoon has winds of 32.7–50.9 m s−1, while a strong typhoon has wind speeds of 51.0 m s−1 or greater."*
- The Beaufort mapping is from Tainan City government, citing CWB: *"輕度颱風相當風力8~11級，中度颱風相當風力12~15級，強烈颱風相當風力16級以上"* (mild typhoons correspond to Beaufort 8–11, moderate to 12–15, and strong to 16 and above) ([Tainan disaster site](https://web.tainan.gov.tw/publicdisaster/News_Content.aspx?n=21784&s=7637731)).
- **L/S, TW.** The CWB database also records R15 and R25 (radii of 15 and 25 m/s winds), but not RMW.

**Averaging periods.** The paper states: *"The CWB and RSMC Tokyo … reported maximum sustained surface winds averaged over a 10-min time interval"*, whereas JTWC and NHC use 1-min. JMA is 10-min too (JP). The Taiwan wind code is 10-min.

WMO conversions ([Harper, Kepert & Ginger 2010, WMO/TD-No. 1555](https://www.systemsengineeringaustralia.com.au/download/WMO_TC_Wind_Averaging_27_Aug_2010.pdf), fetched). **S/L, INT.**
- 10-min = K × 1-min, with K = 0.93 at sea, 0.90 off-sea, 0.87 off-land and 0.84 in-land. The report recommends 0.93 at sea *"rather than the historical 0.88"*.
- Gust factors at 10 m:

| Exposure | G(3 s, 10 min) | G(60 s, 10 min) |
|---|---|---|
| In-land | 1.75 | 1.28 |
| Off-land | 1.60 | 1.22 |
| Off-sea | 1.45 | 1.17 |
| At-sea | 1.30 | 1.11 |

This matters because the hazard field should be kept as a **10-min mean (CWA convention)**. Convert to 3-s gust by the WMO factor only at the point where a US fragility (Hazus hurricane fragilities are in peak gust) is looked up.

---

## Recommended field construction

| Step | What | Source | Grade |
|---|---|---|---|
| 1. Track | Straight line through the storm corridor at a stored heading. Centre positions at fixed hourly steps over the 72 h window. The distance from each facility to the centre is computed with sqrt. The site hazard is the maximum over steps. | Straight track is a small-domain simplification (Wu & Kuo 1999 deflection is qualitative) | J |
| 2. Intensity | Draw Vm (10-min, marine) inside the CWA mild–moderate band. For slight or moderate damage, keep it about 25–40 m/s. The Beaufort label follows the CWA table. | CWB database paper; Tainan / CWB | L/S, TW |
| 3. Profile | Modified Rankine with x = 0.5: V = Vm·r/Rm inside Rm, and Vm·sqrt(Rm/r) outside. Rm is drawn around 30–50 km (geometric mean 47.5 km). Keep Jelesnianski as a rational alternative. If Holland is wanted, use a stored table g(u; B = 1.3). | TCRM (0.4 < x < 0.6); Willoughby & Rahn 2004 | L, INT/US |
| 4. Sea to land | Multiply by 0.80–0.83 on land cells, applied over a 1 km coastal ramp (linear in distance, about 60% of the reduction reached by 1 km). I would take **0.83** (ESDU/Vickery, open terrain), then apply step 5 for rougher classes. | Vickery et al. 2009; Knaff 2011 via stormwindmodel | L, US |
| 5. Local roughness | Multiply by the Taiwan code class ratio at 10 m: C (open or coast) 1.000, B (town) 0.662, A (city core) 0.476. These are stored constants. Ridge-top sites get (1 + K1·K2·K3) from the code tables. | 建築物耐風設計規範 Table 2.2 and §2.6 | **S, TW** |
| 6. Mountain lee | Multiply by a lee factor L_f in [0.6, 1.0]. It falls linearly with the fraction of the upwind path from the centre that crosses ridge cells above a stored height. L_f = 0.6 at full blocking comes from the ">40%" storm-wide weakening crossing the CMR. The per-site shape of the function is my own. Registry: `placeholder (open decision: lee_factor_shape)`. | Brand & Blelloch 1974 via Wu & Kuo 1999; Herb 83% retained | L (bound), J (shape), TW |
| 7. Flood | A separate field. Pick a rain scenario from the WRA ladder (300 / 450 / 600 mm per 24 h), with an orographic multiplier up to about ×3 on ridge catchments (Herb). A facility is flood-exposed when HAND < h(scenario), with h stepping over 3 → 5.3 → 7 m. Slope below 7.6% is the flat mask. | WRA/NCDR; Nobre 2011; Santos 2021; Wu & Kuo 1999 | S/L TW (rain ladder), L INT (HAND), J (the mapping from rain to h) |
| 8. Noise | Multiply wind by (1 + ε), where ε is a Gaussian field with σ = 0.10 and a Wendland φ(t) = (1 − t)₊⁴(1 + 4t) covariance, c = 10 km. Draw it by explicit Cholesky, with normals from Irwin–Hall. The flood threshold gets its own field with c = 3–5 km, from a separate spawn-tree stream. | Vickery 2009a (CoV 10%); Wendland 1995 / Bevilacqua et al. 2019; the c values are placeholders | L (σ, kernel), J (c) |
| 9. Output units | Keep the field as a 10-min mean at 10 m. Convert with the WMO G(3 s, 10 min) factor for the exposure only at the fragility lookup: 1.75 in-land, 1.45 off-sea. | WMO/TD-1555 | S/L, INT |

**Open questions for the design side**
1. The lee-factor shape (step 6). No per-site Taiwan figure was found. Should it be accepted as J with the 0.6 bound?
2. The residual correlation lengths (step 8). No published km value was found. Should they be accepted as placeholders?
3. The Kaplan–DeMaria parameters were not verified. Step 6 currently folds time decay into the lee factor; confirm that is acceptable.
4. Step 7 needs a rule linking the rain scenario to the HAND stage h. It is J; a Taiwan WRA depth-by-scenario source would replace it. That source is not fetched: the NCDR handbook PDF is the next thing to read.


---

# Lane C: what a damage state means for function, and how scenarios are drawn

Grades: S = standard or regulation, L = literature or government report, J = judgment. Jurisdiction is marked TW, JP, US or INT.

**Primary source read in full:** FEMA, *Hazus Earthquake Model Technical Manual, Hazus 4.2 SP3* (October 2020). I downloaded the PDF through the Wayback Machine copy of fema.gov/sites/default/files/2020-10/fema_hazus_earthquake_technical_manual_4-2.pdf, because fema.gov refused direct downloads (HTTP 403). It is cited below as "EQ-TM". I also read FEMA, *Hazus-MH 2.1 Hurricane Model Technical Manual* ("HU-TM"), again from the Wayback copy of fema.gov/sites/default/files/2020-09/fema_hazus_hurricane-model_technical-manual_2.1.pdf.

**Edition caveat:** the brief fixes "Hazus MR4". I could not fetch the MR4 (2009) manuals. The lifeline restoration tables below come from the 4.2 manual. They are the ATC-13 (1985) and G&E (1994) fits that Hazus has carried for many editions, but I have **not verified** that they are unchanged since MR4. Someone should check them against an MR4 copy before the rule registry cites "MR4".

**Taiwan first:** Taiwan's loss-estimation system (TELES, from NCREE, Taiwan's national earthquake engineering centre) has no lifeline restoration functions of its own. Yeh, Loh and Tsai (2003) state: "The analysis framework of TELES follows the approach of HAZUS, which has been developed in the United States." That paper covers buildings and casualties, not the function of lifelines (source: https://www.ncree.org/ncree-jrc/CD/address/C-H-Yeh.pdf; grade L, TW). The Taiwan anchor therefore points back to Hazus (US). I found no Japanese restoration-by-damage-state table in the time available (grade J; searched TELES and NCREE lifeline pages).

---

## 1. Functionality right after the event, by damage state

### 1.1 What the Hazus numbers are and are not

- Hazus restoration curves are **normal cumulative distribution functions in time**. Each curve has a mean and a standard deviation in days for every (class, damage state) pair. The "discretized" tables sample those curves at 1, 3, 7, 30 and 90 days.
- EQ-TM says (p. 8-54 and similar wording on pp. 7-48, 7-61 and 8-69): "Although not directly used in Hazus, the discretized restoration functions are presented here as guidance."
- What the curves mean: "Restoration curves describe the fraction or percentage of the component that is expected to be open or operational as a function of time following the earthquake. For example, an extensively damaged facility might be closed (0% functional) immediately following the earthquake, but 100% functional after 30 days." (EQ-TM §6.8, p. 6-31; the same text for transport is on p. 7-1.)
- **Interpretation (J):** the fraction is the share of a *population* of facilities in that damage state that are back in service by day t. For a single node, it is the probability that the node is back by day t. It is **not** a partial-capacity multiplier for one facility.
- There is no "day 0" column. Evaluating the normal curve at t = 0 gives small non-zero values, such as Φ(−1) = 0.16 wherever the mean equals the standard deviation. Those values are **artefacts of the normal fit**, not observations. The manual's own words ("closed (0% functional) immediately") say day 0 is 0.
- Hazus's reading of the percentages (EQ-TM p. 6-31):
  - "0-25% functionality – building/facility is likely to be non-functional"
  - "25-75% functionality – building/facility is likely to allow limited operations"
  - "75-100% functionality – building/facility is likely to be functional"
- Caveat, verbatim: "Functionality estimates also do not consider direct utility outage or potential cascading effects." (p. 6-31)
- Power coupling, verbatim (p. 8-67): "Loss of electric power is assumed to affect only the Slight and Moderate damage states of other utility systems that depend on power." This matters for the pilot, which has only Slight and Moderate damage.
- These are **earthquake** restoration functions: ATC-13 expert opinion, plus the G&E 1994 report for substations and distribution circuits. The Hazus hurricane model has **no** lifeline restoration functions (grade L, US).

### 1.2 Day-1 percent functional (EQ-TM discretized tables) and verbatim damage-state definitions

**Electric substations.** Table 8-28, p. 8-55. Continuous parameters, Table 8-27, mean ± standard deviation in days: 1 ± 0.5, 3 ± 1.5, 7 ± 3.5, 30 ± 15.

| Day | Slight | Moderate | Extensive | Complete |
|---|---|---|---|---|
| 1 | 50 | 9 | 4 | 3 |
| 3 | 100 | 50 | 13 | 4 |
| 7 | 100 | 100 | 50 | 7 |

Definitions (p. 8-53):
- **Slight:** "the failure of 5% of the disconnect switches (i.e., misalignment), or the failure of 5% of the circuit breakers ..., or by the building being in the Slight damage state."
- **Moderate:** "the failure of 40% of disconnect switches ..., 40% of circuit breakers ..., failure of 40% of current transformers ..., or by the building being in the Moderate damage state."
- **Extensive:** "the failure of 70% of disconnect switches ..., 70% of circuit breakers, 70% of current transformers ..., or by failure of 70% of transformers ..., or by the building being in the Extensive damage state."
- **Complete:** "the failure of all disconnect switches, all circuit breakers, all transformers, or all current transformers, or by the building being in the Complete damage state."
- Note: this is the only Hazus class whose damage states are defined as *fractions of subcomponents failed*. That is a physical basis for a continuous condition (see §2).

**Generation facilities.** Table 8-28. Day 1: Slight 100, Moderate 24, Extensive 16, Complete 2. Mean ± standard deviation in days: 0.5 ± 0.1, 3.6 ± 3.6, 22 ± 21, 65 ± 30.
- **Slight:** "turbine tripping, light damage to the diesel generator, or by the building being in the Slight damage state."
- **Moderate:** "chattering of instrument panels and racks, considerable damage to boilers and pressure vessels, or ... Moderate damage state."

**Communication facilities** (central offices and broadcasting stations). Table 8-37, p. 8-70. Continuous parameters, Table 8-36: 0.5 ± 0.2, 1 ± 1, 7 ± 7, 40 ± 40.

| Day | Slight | Moderate | Extensive | Complete |
|---|---|---|---|---|
| 1 | 99 | 50 | 20 | 16 |
| 3 | 100 | 98 | 28 | 18 |

The Extensive and Complete day-1 values of 20 and 16 come from the normal fit where the mean equals the standard deviation (see §1.1). Definitions (pp. 8-69 to 8-70):
- **Slight:** "Slight damage to the communication facility building, or inability of the center to provide services during a short period (a few days) due to loss of electric power and backup power, if available."
- **Moderate:** "Moderate damage to the communication facility building, a few digital switching boards being dislodged, or the central office being out of service for a few days due to loss of electric power ... and backup power (typically due to overload), if available."
- **Extensive:** "severe damage to the communication facility building resulting in limited access to facility, or by many digital switching boards being dislodged, resulting in malfunction."
- **Complete:** "Complete damage to the communication facility building, or damage beyond repair to digital switching boards."

**Potable water.** Table 8-2, p. 8-7. Continuous parameters, Table 8-1.

| Class | Day | Slight | Moderate | Extensive | Complete |
|---|---|---|---|---|---|
| Water treatment plant | 1 | 65 | 23 | 16 | 7 |
| Water treatment plant | 3 | 100 | 82 | 18 | 8 |
| Pumping plant | 1 | 65 | 22 | 10 | 3 |
| Pumping plant | 3 | 100 | 50 | 15 | 4 |
| Storage tank | 1 | 30 | 20 | 13 | 10 |

Definitions (pp. 8-4 to 8-5):
- **Treatment plant, Slight:** "malfunction of the plant for a short time (less than three days) due to loss of electric power and backup power, if any, considerable damage to various equipment, light damage to sedimentation basins, ... Loss of water quality may occur."
- **Treatment plant, Moderate:** "malfunction of plant for about a week due to loss of electric power and backup power, if any, extensive damage to various equipment, considerable damage to sedimentation basins ... Loss of water quality is imminent."
- **Treatment plant, Extensive:** "extensive damage to the pipes connecting the different basins and chemical units. This type of damage will likely result in the shutdown of the plant."
- **Treatment plant, Complete:** "the complete failure of all piping, or extensive damage to the filter gallery."
- **Pumping plant, Slight:** "malfunction of the plant for a short time (less than three days) due to loss of electric power and backup power, if any, or Slight damage to building."
- **Pumping plant, Moderate:** "the loss of electric power for about a week, considerable damage to mechanical and electrical equipment, or Moderate damage to the building."
- **Pumping plant, Extensive:** "the building being extensively damaged, or the pumps being badly damaged beyond repair."
- **Storage tank, Slight:** "minor damage ... without loss of its contents or functionality."

**Ports.** Table 7-17, p. 7-49. Continuous parameters, Table 7-16.
- Waterfront structures, day 1: Slight 96, Moderate 24, Extensive 17, Complete 12.
- Cranes and cargo handling equipment, day 1: 96, 20, 17, 9.
- Definitions (pp. 7-47 to 7-48):
  - **Waterfront structures, Slight:** "minor ground settlement resulting in a few piles ... getting broken and damaged. Cracks are formed on the surface of the wharf. Repair may be needed."
  - **Waterfront structures, Moderate:** "considerable ground settlement with several piles ... broken and damaged."
  - **Cranes, Slight:** "slight damage to structural members with no loss of function for the stationary equipment ... Minor repair and adjustments may be required before the crane becomes operable."
  - **Cranes, Moderate:** "derailment due to differential displacement of parallel track. Rail repair and some repair to structural members is required."

**Airports.** Table 7-22, p. 7-62. Continuous parameters, Table 7-21.
- Control towers, terminals and hangars, day 1: Slight 100, Moderate 37, Extensive 16, Complete 11.
- Runways, day 1: Slight and Moderate together 27, Extensive 17, Complete 10.
- Definitions (pp. 7-59 to 7-60): buildings take the damage state of the building. Runways: "Slight damage is defined as minor ground settlement or heaving of the runway surface" and "Moderate damage is defined the same as Slight damage."

**Fuel.** Table 8-21, p. 8-41. Continuous parameters, Table 8-20.
- Refineries, day 1: Slight 100, Moderate 19, Extensive 14, Complete 0.
- Tank farms, day 1 **as printed**: Slight 58, Moderate "7.0", Extensive "28.0", and no Complete row.
  - **Defect in the source:** the printed Moderate and Extensive values equal the *mean days* from Table 8-20, and Extensive 28 on day 1 is higher than 17 on day 3. That is impossible for a restoration curve.
  - Recomputed from Table 8-20 (0.9 ± 0.5, 7 ± 7, 28 ± 26, 70 ± 55), day 1 is Slight 58, Moderate 20, Extensive 15, Complete 10 (my arithmetic).
- Definitions (pp. 8-38 to 8-39):
  - **Tank farm, Slight:** "malfunction of the plant for a short time (less than three days) due to loss of backup power or light damage to the tanks."
  - **Tank farm, Moderate:** "malfunction of the tank farm for a week or so due to loss of backup power, extensive damage to various equipment, or considerable damage to tanks."
  - **Refinery, Slight:** "malfunction of the plant for a short time (a few days) ..."
  - **Refinery, Moderate:** "malfunction of plant for a week or so ..."

**Hospitals and clinics.** EQ-TM Table 6-20, p. 6-32 (essential facilities). Every class, including small, medium and large hospitals (EFHS, EFHM, EFHL) and medical clinics and labs (EFMC), has the same parameters: Slight 5 ± 1 days, Moderate 20 ± 2, Extensive 90 ± 10, Complete 180 ± 20.
- Day-1 functional is about 0% for **every** damage state (Φ(−4) ≈ 0.00003 for Slight). Day 3 is 2% for Slight.
- The manual adds that estimates "do not take emergency response or contingency plans into consideration (e.g., hospitals which could operate their emergency room from the parking lot)."
- **Hurricane model (HU-TM §7.9.5.3, pp. 7-48 to 7-49):** hospital loss of function is modelled in *days as a function of wind speed*, not by damage state. It is "the average amount of time (days) that all beds in a hospital will be unavailable to patients". Also: "Modeled loss of function of a day is assumed to occur close to 1% of the buildings value (roof cover cost)". And from Hurricane Ike: "most had emergency back-up power in place aiding in their ability to stay open." (L, US)

**Mapping the pilot's node classes onto Hazus classes (J where noted):**

| Pilot node class | Hazus class | Grade |
|---|---|---|
| transmission and distribution substations | electric substations | L |
| exchange, data_centre, cable_landing | communication facility | J; mast has no Hazus class, J |
| treatment, pumping, storage | treatment plant, pumping plant, storage tank | L |
| reservoir | none (the dam is outside Hazus lifelines) | J |
| seaport | waterfront structures, cranes | L |
| airport | airport buildings and runway | L |
| freight_yard | railway facilities (stations, dispatch and maintenance: mean 1.5 days Moderate) | J |
| import_terminal, tank_farm, depot | tank farm | J for depot |
| refinery | refinery | L |
| generation | generation facilities | L |
| tertiary and regional hospital | large or medium hospital (EFHL, EFHM) | L |
| clinic | medical clinics and labs (EFMC) | L |
| blood_bank | medical clinics and labs (EFMC) | J |

**Arithmetic constraint:** the normal curve needs erf at runtime, which the generator may not use. Store the discretized percentages (or the curve pre-evaluated at hours 0 to 72) as a lookup table in the rule registry.

---

## 2. Continuous condition or an on/off switch?

**What Hazus does.**
- At facility level, the damage state is discrete. A facility's expected functionality is the probability-weighted mix: "FPc = Σ FRi × P[dsi]" (EQ-TM Equation 8-3, p. 8-67: "FPc is the combined facility functionality, FRi is the facility restoration percent for damage state i, P[dsi] is the occurrence probability of damage state i").
- So a continuous functionality number in Hazus is an *expectation over discrete states*, not a physical partial capacity (L, US).
- Service is then evaluated in terms of whether each facility is functioning. EQ-TM p. 8-65: "power service outages for the Study Region are assumed to be dependent on the nonfunctionality of substations servicing the region."

**What interdependent-infrastructure models do.** Most use binary component states once a damage state is drawn.
- Dueñas-Osorio, Craig & Goodno (2007), *Earthquake Engng Struct. Dyn.*, doi:10.1002/eqe.626. They remove components according to "network component conditional probabilities of exceeding predefined performance levels" (companion 2004 abstract, via Consensus). Binary removal (L, US).
- Ouyang & Dueñas-Osorio (2014), *Structural Safety*, doi:10.1016/j.strusafe.2014.01.001. Hurricane hazard model plus "component fragility models, a power system performance model, and a system restoration model" (abstract). Components fail or survive (L, US).
- Lee, Mitchell & Wallace (2007), *IEEE Trans. SMC-C*, doi:10.1109/TSMCC.2007.905859. An interdependent layered network-flow model: disrupted nodes and arcs are removed and then restored by decision (L, US).
- Johansen & Tien (2018), *Reliab. Eng. Syst. Saf.* A Bayesian network in which each component either functions or does not. The companion ICASP13 paper (Lee & Tien 2019) describes components that "fail together under a hazard" (L, US). I could not fetch the Johansen & Tien full text; this rests on the companion paper.
- Ouyang (2014) review, *RESS*, doi:10.1016/j.ress.2013.06.040. Groups models as "empirical ... agent based ... system dynamics ... economic theory ... network based" (abstract). Network-based models dominate and are mostly binary (L, INT). The characterisation is from the abstract only.
- Liang et al. (2025), *RESS*, doi:10.1016/j.ress.2025.112001. Names the common practice as a weakness: "oversimplified damage models assuming binary states or damage independence". They propose "multi-state damage-functionality mappings" (abstract) (L, INT).
- Bhuiyan et al. (2020), *EJOR*, doi:10.1016/j.ejor.2020.02.016. Multi-level post-disruption *capacity*: "a facility's post-disruption capacity depends probabilistically on the protection decision" (abstract) (L, US).

**Recommendation (J).** The damage state should switch function in time, not scale capacity:
- At t = 0, any facility at Slight damage or worse has condition 0 (off). This follows the Hazus definitions: "malfunction of the plant for a short time", "out of service for a few days".
- Each facility gets a restoration time. It comes back at condition 1 at that time.
- The time is either drawn per facility from the Hazus curve through a stored table, or set to a fixed quantile.
- Over the 72-hour window, the node's capacity is a step function.

This keeps the answer key a mixed-integer problem that brute force can check. It also matches how Hazus itself defines functionality.

A continuous condition in [0, 1] can be defended only in two cases:
- as the expectation (Equation 8-3), which is wrong for a single scenario; or
- for substations, whose damage states are defined by the fraction of switches and breakers failed (5%, 40%, 70%, 100%).

If the design wants partial capacity, substations are the only class with a physical basis for it. Pilot consequence: Slight damage restores within 72 hours for every lifeline class, while Moderate often does not. Hospitals are the exception: Hazus says a hospital with *any* damage is closed for about 5 days or more, and the hurricane evidence (backup power keeps hospitals open) points the other way. **This needs a design decision.**

---

## 3. How scenarios are generated

**Conditional independence given the hazard field.**
- Hazus applies each facility's fragility to the intensity at that site, one facility at a time. The substation example (EQ-TM pp. 8-65 to 8-67) computes damage-state probabilities for substation 1 at 0.15 g and substation 2 at 0.3 g separately. No correlation between facilities beyond the field is modelled (L, US).
- Lee & Kiremidjian (2007), *Earthquake Spectra*, doi:10.1193/1.2791001: "prior research ... assumes no spatial ground motion correlation and no structure-to-structure damage correlation", and "assuming no correlation in ground motion and in damage may potentially underestimate uncertainty in the overall loss estimation" (abstract) (L, US).
- Adachi & Ellingwood (2009), *CACAIE*, doi:10.1111/j.1467-8667.2008.00583.x: forecasts "should consider the impact of spatial correlation of seismic intensities on system function and serviceability" (abstract) (L, US).
- Jayaram & Baker (2010), *EESD*, doi:10.1002/eqe.988: "the uncertainties in the ground-motion intensities and the spatial correlations between ground-motion intensities at various sites must be modeled in order to obtain unbiased estimates of lifeline risk" (abstract) (L, US).
- Hurricane transmission (L, US): Ma et al. (2022), *RESS*, doi:10.1016/j.ress.2021.108072: "the spatial correlation among structures is modeled efficiently by a random field based technique" (abstract).

**Recommendation (J):** a shared latent typhoon field, then independent draws per node given the field.
- This is the Hazus-standard structure.
- The field itself carries the main correlation, which is what the three papers above say must not be dropped.
- Damage correlation beyond the field (same construction type, same site) is recognised (Lee & Kiremidjian; Lee & Tien's "geographic interdependencies"), but it is a refinement. Leave it out of the pilot and state the assumption.

**How many scenarios.**
- Jayaram & Baker (2010) reduced the catalogue to "just 150 intensity maps", using importance sampling plus k-means with re-weighting, and matched risk estimates from full Monte Carlo (L, US).
- Chowdhury, Chen & Zhang (arXiv 2601.21371) ran scenario-tree sizes of 30 to 200 in sensitivity tests (L, US, preprint).
- Miller & Baker (2015), *EESD*, doi:10.1002/eqe.2506: optimisation-based selection of a subset of damage maps with rates.
- Jia et al. (2024), *RESS*, doi:10.1016/j.ress.2024.110086: hierarchical clustering of Monte Carlo scenarios, with a reported "100-fold enhancement in computational time" (L, INT).
- Arab et al. (2015), *IEEE TSG*, doi:10.1109/TSG.2015.2388736: a stochastic pre-hurricane integer programme for the IEEE 118-bus test system (L, US).

The pilot's 5 to 8 scenarios is far below any published count. It is defensible only as a hand-traceable illustration, with the scenarios weighted and stated to be a reduced set (J). If they are a reduction, keep the Jayaram and Baker style weights in the manifest.

**Not verified:** the brief names "Salmeron, Wood & Morton" for stochastic pre-storm hardening. I could not find such a paper. The nearest I found is the Brown, Carlyle, Salmerón & Wood work cited in §4, which covers attacks, not storms. **Do not cite it until someone locates it.**

---

## 4. Protection and hardening

There are two recognised ways to model protection.

**(a) Protected means immune.** This is standard in defender–attacker–defender and fortification models:
- Brown, Carlyle, Salmerón & Wood (2006), "Defending Critical Infrastructure", *Interfaces*, doi:10.1287/inte.1060.0252.
- Church & Scaparra (2007), *Geographical Analysis* 39. Scaparra & Church (2008) summarise it as "the subset of q facilities which, when fortified, provides the best protection against the worst-case loss of r non-fortified facilities" (abstract).
- Lozano & Smith (2017), *INFORMS J. Comput.*: "the attacker next damages a subset of unprotected assets" (abstract).

These are grade L (US). They are intentional-attack models, though Church & Scaparra's abstract also names "natural disaster". For weather hazards, hardened-lines-cannot-fail formulations are widely attributed to Yuan et al. (2016), *IEEE TSG*, doi:10.1109/TSG.2015.2513048, and Ma et al. (2018), *IEEE TSG*, doi:10.1109/TSG.2016.2591885. **I could not get their full text, so the "cannot fail" wording for these two is unverified (J).**

**(b) Hardening shifts or lowers the fragility.**
- Peeta et al. (2010), *Computers & OR*, doi:10.1016/j.cor.2009.12.006: "investment decreases the likelihood of failure ... the investment decisions in the first stage alter the survival probabilities of the corresponding links" (L, US and TR).
- Yücel et al. (2018), *EJOR*: "the failure probability of a strengthened link decreases" (L).
- Li et al. (arXiv 2207.00741): decision-dependent fragility curves (L).
- Hazus itself offers separate fragility functions for facilities with anchored and unanchored components: "Damage functions available within Hazus are the functions for facilities with unanchored components. User's wishing to analyze facilities with anchored components could revise the existing damage functions" (EQ-TM p. 8-41 and elsewhere). That is a curve shift (L, US).
- Tan et al. (arXiv 1711.02205) model hardening as reducing *repair time*, not failure (L).

**Verdict on the pilot's "protect condition" (condition held at 1 in every scenario):**
- It is a recognised modelling choice. It is the fortification or immunity convention of (a), and grade L rests on Brown et al. (2006) and Church & Scaparra (2007).
- For a *natural* hazard, the more common and more physical choice is (b).
- Immunity makes the value of protection an upper bound, and it makes the answer key insensitive to how strong the field is at a protected node.
- Recommendation (J): keep immunity for the pilot, since it keeps brute force exact. State it as the fortification convention, cite (a), and name (b) as the alternative the flattened and carried comparison does not test.

---

## 5. Summary table: percent functional at day 1 (Hazus EQ-TM 4.2 discretized tables)

Hazus has no day-0 column. My recommended value at t = 0 is **0 for every damage state from Slight upward** (the facility is switched off, then restored), following EQ-TM §6.8: "closed (0% functional) immediately".

| Class | Slight | Moderate | Extensive | Complete | Source | Grade |
|---|---|---|---|---|---|---|
| Electric substation | 50 | 9 | 4 | 3 | EQ-TM Table 8-28 (G&E 1994) | L, US |
| Generation facility | 100 | 24 | 16 | 2 | EQ-TM Table 8-28 (ATC-13 SF-29a) | L, US |
| Communication facility | 99 | 50 | 20 | 16 | EQ-TM Table 8-37 (ATC-13 SF-33a) | L, US |
| Water treatment plant | 65 | 23 | 16 | 7 | EQ-TM Table 8-2 | L, US |
| Water pumping plant | 65 | 22 | 10 | 3 | EQ-TM Table 8-2 | L, US |
| Water storage tank | 30 | 20 | 13 | 10 | EQ-TM Table 8-2 | L, US |
| Port waterfront structures | 96 | 24 | 17 | 12 | EQ-TM Table 7-17 | L, US |
| Port cranes and cargo handling | 96 | 20 | 17 | 9 | EQ-TM Table 7-17 | L, US |
| Airport buildings (tower, terminal, hangar) | 100 | 37 | 16 | 11 | EQ-TM Table 7-22 | L, US |
| Airport runway | 27 | 27 | 17 | 10 | EQ-TM Table 7-22 | L, US |
| Refinery | 100 | 19 | 14 | 0 | EQ-TM Table 8-21 | L, US |
| Tank farm (recomputed from the normal parameters; the printed table is defective) | 58 | 20 | 15 | 10 | EQ-TM Table 8-20 | L, US; recompute J |
| Hospital (small, medium, large) and clinic | 0 | 0 | 0 | 0 | EQ-TM Table 6-20 (5 ± 1, 20 ± 2, 90 ± 10, 180 ± 20 days) | L, US |
| TW anchor | uses Hazus | | | | Yeh, Loh & Tsai 2003 (TELES) | L, TW |

**Questions for the design side:**
1. Should hospital function follow Hazus earthquake Table 6-20 (closed at least 5 days at any damage), or the hurricane-model evidence that backup power keeps hospitals open?
2. The MR4 table values need confirming.
3. Should restoration time be a per-node random draw from a stored table, or a fixed quantile?


---

# Independent review of hazard lanes A, B, C

Reviewer: fresh instance, did not write the lanes. Date 2026-09-30.

## Summary count

Load-bearing sub-claims checked: **23**
- **CONFIRMED: 15**
- **OVERSTATED: 6**. These are the Hazus Hurricane lifeline scope, the "0% functional immediately" reading, the DOE power-plant quote, the "10²–10⁴×" link/node ratio, the "no Taiwan gust near tower medians" framing, and the 10% CoV used as a correlated field.
- **UNREACHABLE: 2**. These are the Brand & Blelloch primary text, and whether the Hazus 4.2 restoration values equal MR4.
- **WRONG: 0**
- **Fabricated-looking citations: none found.** I spot-checked arXiv 2601.21371, 2311.15118, 2107.06072 and 1607.06921, the Liang 2025 RESS DOI, and the Jian et al. CWB paper. All exist and match.
- **Grade inflation:** 3 instances (§3). **Cross-lane contradictions:** 5 (§4).

### How I verified
- **FEMA PDFs.** fema.gov returns 403, and curl to Wayback is blocked by egress. The lanes' saved PDFs carry genuine FEMA metadata: Hazus 6.1 Hurricane (Oct 2024, 809 pp), Flood 6.1 (Jul 2024), Inventory 6.1 (Sep 2024), and EQ 4.2 SP3 (Oct 2020, 436 pp). I extracted text from these PDFs myself (pdftotext) and did not rely on the lanes' .txt files.
- **Web sources.** I fetched these independently with WebFetch: Wu & Kuo 1999, Vickery et al. 2009 (JAMC), Vickery et al. 2009 (hazard review), the CWB database paper, the Bevilacqua et al. arXiv paper, TEPCO, Brown et al. 2006 (NPS copy), Church & Scaparra 2007 (Kent and SciSpace copies), and the Taipei Times.
- **Local copies only.** The FCC and Japanese-government PDFs come from the lanes' src/ copies. fcc.gov returned 403 to me. The PDF metadata checks out: the FCC report was created 2022-09-30.

---

## 1. The ten required checks

### 1. Hazus Hurricane does not model utility or transport lifelines — **OVERSTATED** (Lane A, headline 3 and §2.2)
Hazus 6.1 Hurricane TM §2.2, verbatim:
> "Impacts to transportation systems are not included in the wind or surge models."
> "Utility systems, including potable water, electric power, wastewater, communications, and liquid fuels (oil and gas), are treated in a manner similar to transportation systems. Impacts to utility systems are not included in the wind model. **Damage, loss, and a functionality assessment can be modeled for potable water, wastewater, natural gas, and electric power facilities in the flood (surge) model.**"

- **Transport:** CONFIRMED for both wind and surge.
- **Utilities:** the exclusion is **wind only**. Lane A's §2.2 quote cuts the sentence off before the surge clause, and its headline says "at all, whether by wind or by surge". That is not what the manual says.
- **A source-level tension the design side should know about:** for electric power specifically, the Inventory TM §10.5 says "Analysis is not performed for Electric Power Systems but can be mapped for reference". Flood TM footnote 28 says the electric damage functions "are not enabled". So the Hurricane manual's claim that electric facilities can be modelled in surge is contradicted by the Flood and Inventory manuals of the same release.
- **Net:** water, wastewater and fuel facilities do get Hazus surge and flood treatment. Electric and communications facilities do not.

### 2. Hazus Flood functional depths, and substations and communications as map-only — **CONFIRMED**
Inventory TM 6.1:
- **Table 10-13:** ESSL, ESSM, ESSH, EPPL, EPPM and EPPS are all "Slab on grade, 0, 4, Component is not analyzed in the flood model, mapping only capabilities."
- **Table 10-5:** PWTL/M/S (water treatment) 0 / 4; PPPL/M/S (pumping) 0 / 4.
- **Table 10-7:** WWTL/M/S 0 / 4.
- **Table 10-11:** ORFL/M/S 0 / 4; OPP 0 / 0; OTF "0, 0, Assume tank bottom is at grade and tanks will not float."
- **Table 7-15:** EFHS, EFHM, EFHL "Basement, 3 [ft first floor], COM6, 0.5"; EFMC "COM7, 0.5".
- **§10.6:** "Communication facilities are not analyzed in the flood model but are able to be mapped."
- **Flood TM §10.4.2:** "exceeds the functional depth threshold by 0.1 feet or more, the component will be considered non-functional". §10.4.1: "Utility System Components reach maximum damage at 10 feet of flooding". Eq. 10-2: "27% Damage = WDFLT damage function damage at 5.5 ft (8.5 ft depth − 3 ft equipment height)".

Notes:
- Lane A says water-storage defaults were "not retrieved", but they are in Table 10-5 beside the pumping plants:
  - on-ground tanks (PSTGC, PSTGS, PSTGW): functional depth 24 ft;
  - above-ground steel (PSTAS): 80 ft;
  - buried concrete (PSTBC): 4 ft.
- Lane A's "~40% at 10 ft" is read off a figure (Fig 10-1), so it is J, not L.
- **Open ambiguity:** the manual does not say whether the hospital's 0.5 ft functional depth is measured from grade or from the 3 ft first floor. The design side must decide.

### 3. Faxai 2019 pole-failure cause split and counts; no mast collapsed from wind — **CONFIRMED**
Government verification report (検証レポート 中間とりまとめ, 令和２年１月, 一連の災害に係る検証チーム), §2.5:
> 「電柱については、倒木や建物の倒壊（約 74％）、看板等の飛来物（約 14％）、土砂崩れ等の地盤影響（約 12％）による二次被害が原因とされるものが大半であった。」

(For poles, most failures were attributed to secondary damage: trees and buildings falling, about 74%; flying debris such as signboards, about 14%; ground effects such as landslides, about 12%.)

On base stations:
> 「台風第 15 号、第 19 号における災害においては、風を原因として倒壊した基地局はない。」

(In the Typhoon 15 and 19 disasters, no base station collapsed because of wind.)

The same report gives the peak outage as 934,900 households (9/9 07:50) and the time to 99% restoration as about 280 hours. The Cabinet Office case sheet gives water outage as 139,744 households. The TEPCO feature (fetched) says 「電柱約2,000本が折損し」「送電鉄塔2基が倒壊」 (about 2,000 poles broken; 2 transmission towers collapsed).

Notes:
- **Wording.** The sentence says the *majority* (大半) of pole failures were secondary. The 74 / 14 / 12 split sums to 100%, so it describes the causes of the secondary failures. The share of direct-wind failures is not given. Lane A §6 ("Wind, via trees and debris (74% / 14%) + landslide (12%)") is acceptable, but it should say "of secondary-cause failures".
- **Attribution.** Lane A calls it the "総務省検証レポート". It is the inter-ministry 検証チーム report, which the local copy reproduces as 総務省 council reference material 56-4.
- **Scope.** The no-collapse statement covers Typhoons 15 *and* 19, and 基地局 includes antenna masts. Lane A has this right.

### 4. FCC Hurricane Ian cell-site outage split — **CONFIRMED**
FCC DIRS report, 30 Sep 2022, TOTAL row: "14,188 1,096 7.7% 25 320 751 466". That is:
- damage 25 / 1,096 = 2.28%;
- transport 29.2%;
- power 68.5%;
- 466 sites up on backup power.

Lee County row: "394 145 36.8% 1 50 94 73". The 5 Oct report TOTAL is "8,097 153 1.9% 12 52 89". Everything Lane A states matches.

### 5. Katrina: 72,447 poles against 300 substations off-line — **CONFIRMED** (and one misuse found)
DOE OE/ISER, *Comparing the Impacts of the 2005 and 2008 Hurricanes on U.S. Energy Infrastructure* (Feb 2009), Table 2:
> "Utility Poles Destroyed 72,447 … Substations Off-line 300"

The text also says "Entergy New Orleans did not report the number of poles destroyed, and as a result infrastructure impacts from Katrina are underestimated."

**OVERSTATED elsewhere in Lane A §1 (generation row).** The quote "none of the plants experienced any significant damage or flooding" is joined by an ellipsis to the sentence about power-plant closings. In the source it refers only to "**Three nuclear power plants** [that] lay within the area affected by Hurricane Katrina". It is not a statement about all generation. The refinery quote ("primarily caused by lack of electricity supply rather than on-site damage") is accurate and applies to 2008.

### 6. Taiwan wind-code terrain factors and CWA intensity classes — **CONFIRMED**
Taiwan wind code (建築物耐風設計規範及解說, amended 103.6.12 and in force from 104.1.1, i.e. 1 Jan 2015), Table 2.2:
- A: α 0.32, zg 500 m
- B: α 0.25, zg 400 m
- C: α 0.15, zg 300 m

Commentary: 「地況 A、B 與 C，相對於 10 分鐘平均風速之α值分別取為 0.32、0.25 與 0.15」 (for terrain A, B and C, α is taken as 0.32, 0.25 and 0.15 relative to the 10-minute mean wind). Also 「即為 1.666 V10(C)」 (that is, 1.666 V10(C)). Terrain C is 「平坦開闊之地面或草原或海岸或湖岸地區」 (flat open ground, grassland, or coast or lakeshore areas).

I recomputed (10/zg)^α relative to C: B = 0.6623 and A = 0.4763. The K(z) floor is at 5 m (Eq. 2.7), so 10 m is unaffected. The K_zt hill factor applies only when its conditions hold: H > 4.5 m (C) or 18 m (A/B), H/Lh ≥ 0.2, and no similar obstacle within 100H or 3.22 km. Lane B omits these conditions.

The CWB database paper is Jian et al. 2022, *TAO* 33:26 (fetched; Lane B left the authors blank). Verbatim: "maximum sustained wind (10-min-averaged) below 17.2 m s−1"; "between 17.2 and 32.6"; "32.7–50.9"; "51.0 m s−1 or greater". And: "The CWB and RSMC Tokyo…reported maximum sustained surface winds averaged over a 10-min time interval."

### 7a. Brand & Blelloch: >40% weakening crossing Taiwan — **CONFIRMED as secondary; primary UNREACHABLE**
Wu & Kuo 1999 (fetched): "westbound typhoons tend to move cyclonically around the northern side of the CMR and experience an average intensity decrease of over 40%, beginning about 12 h before the storm centers reach the island" (Brand and Blelloch 1974). Herb: "dropped from 53 to 44 m s−1 in 6 h" and the CMR size quote are confirmed. AMS returned 403 for Brand & Blelloch, so **the intensity metric (maximum wind or central-pressure deficit) is unverified**.

Two problems with how Lane B uses the figure for L_f = 0.6:
- **Different quantities.** The figure is a storm-wide decrease in intensity that starts 12 h before landfall. L_f is a per-site lee-shelter multiplier. Using one for the other is J, not "L (bound)".
- **Metric.** If B&B measured intensity by pressure, 40% does not translate into a 0.6 wind factor.

### 7b. Vickery 2009 land/sea ratio of about 0.83 — **CONFIRMED** (quote paraphrased)
The source is Vickery, **Wadhera**, Powell & Chen 2009, JAMC 48:381–405. Lane B cites "Vickery, Powell et al.".
- p. 394: "the maximum reduction in the mean wind speed using the ESDU model is about 17%".
- p. 393: "at a distance of about 1 km approximately 60% of the transition (or wind speed reduction) has already occurred"; "the limiting fetch distance is reduced to 20 km".
- p. 393, actual wording: "The mean value of U10/Umax obtained from the model is 0.716." Lane B's version, "mean modeled value of U10/Umax … is 0.716", is written as a verbatim quote but is a paraphrase. The number is correct.
- 0.83 is the *maximum* reduction, sea to open terrain. Lane B uses it as a fixed factor, which is a reasonable centre.

### 8. Wendland kernels valid in 2-D — **CONFIRMED**
Bevilacqua, Faouzi, Furrer & Porcu (Ann. Stat.; arXiv 1607.06921, fetched): φ_{μ,κ} is positive definite on ℝ^d when "μ ≥ λ(d, κ) := (d + 1)/2 + κ". In 2-D:
- κ = 1 needs μ ≥ 2.5, so μ = 3 gives (1−t)₊⁴(1+4t) = Wendland φ₃,₁, valid up to d = 3.
- κ = 2 needs μ ≥ 3.5, so μ = 4 gives (1−t)₊⁶(1+6t+35t²/3) = φ₃,₂.

I checked the algebra and it is correct. Irwin–Hall (sum of 12 uniforms minus 6) has mean 0 and variance 1 exactly. It is correct.

### 9. Hazus day-1 functionality, "0% functional immediately", 4.2 vs MR4, and the tank-farm error
- **Day-1 tables: CONFIRMED.** EQ TM 4.2 SP3, verified cell by cell:
  - Table 8-28, substation 50 / 9 / 4 / 3, generation 100 / 24 / 16 / 2;
  - Table 8-37, communications 99 / 50 / 20 / 16;
  - Table 8-2, water treatment plant 65 / 23 / 16 / 7, pumping 65 / 22 / 10 / 3, storage 30 / 20 / 13 / 10;
  - Table 8-21, refinery 100 / 19 / 14 / 0;
  - Table 6-20, hospitals and clinic 5±1, 20±2, 90±10, 180±20 days.
  - The quotes "Although not directly used in Hazus…", "do not consider direct utility outage…" and "Loss of electric power is assumed to affect only the Slight and Moderate damage states…" are verbatim.
- **"0% functional immediately": OVERSTATED (Lane C §1.1, §2, §5).** The sentence is an example about one damage state: "For example, an **extensively damaged** facility might be closed (0% functional) immediately following the earthquake." Lane C uses it to set t = 0 → off for **every** state from Slight upward. That contradicts the tables Lane C itself reports: Slight generation and refinery are 100% at day 1, and communications 99%. Hazus's own Slight definitions are also mostly short or power-related ("less than three days", "turbine tripping"). "Slight = off at t=0" is J and should be labelled J, not attributed to §6.8.
- **4.2 not MR4: CONFIRMED** (the PDF says "Hazus 4.2 SP3, October 2020"). **Whether the values are identical to MR4: UNREACHABLE.** Lane C's caveat stands, and someone must check an MR4 copy before the registry cites "MR4".
- **Tank-farm table error: CONFIRMED.** The Table 8-21 day-1 column prints Moderate "7.0" and Extensive "28.0", which equal the Table 8-20 mean days (7.0 ± 7.0, 28.0 ± 26.0). I recomputed Φ((1−μ)/σ): Slight Φ(0.2) = 0.58; Moderate Φ(−0.857) = 0.20; Extensive Φ(−1.04) = 0.15; Complete Φ(−1.25) = 0.10. That is 58 / 20 / 15 / 10, matching Lane C. The day-3 and day-7 printed values (29, 50 / 17, 21) match the normal fit, so only the day-1 cells are corrupt.
- **Minor:** Lane C's tank-farm Slight quote is exact ("due to loss of backup power"). The refinery wording differs ("loss of electric power and backup power, if any"), but Lane C quotes each correctly.

### 10. Fortification convention: a protected asset cannot be interdicted — **CONFIRMED**
- **Brown, Carlyle, Salmerón & Wood 2006** (NPS copy, fetched): "For simplicity, we assume that if asset k is defended, i.e., wk = 1, then that asset becomes invulnerable." Also "a defended station becomes invulnerable, and the attacker gains no benefit by attacking it." Verbatim, so this is fully confirmed.
- **Church & Scaparra 2007**, *Geographical Analysis* 39. There is no single verbatim sentence saying "cannot be interdicted". The model enforces it through constraint (11) and the text "the fortification of j will disrupt its interdiction". The paper also says: "we assume that 'fortified' facilities are protected against intentional strikes." The abstract does name "man-made or natural disaster". CONFIRMED in substance. When citing, quote the model's assumption, not a paraphrase.
- Lane C's caveat that these are intentional-attack models is correct. The Yuan 2016 and Ma 2018 "cannot fail" wording stays unverified, as Lane C says.

---

## 2. Other load-bearing claims found problematic

| # | Lane | Claim | Verdict | Evidence |
|---|---|---|---|---|
| a | A §0.4, §2.3 | Tower collapse medians (~280–295 km/h) are "above any gust recorded in Taiwan in the storms I checked" | **OVERSTATED as context.** The Fani numbers are confirmed: 87 collapsed, 41 partial; Table 1 gives 292.5 / 0.104 and 280.4 / 0.088; Quanta 284 / 0.035, Panteli 294 / 0.25, Fu 223.5 / 0.04. | Typhoon Koinu (2023) set a Taiwan record gust of **95.2 m/s (343 km/h)** at Lanyu (Taipei Times, citing CWA). Faxai towers failed at an estimated ~70 m/s (252 km/h) gust. The pilot inference (storms below ~210 km/h give near-zero tower failure) still holds. "Taiwan never reaches tower medians" does not. |
| b | A §4 | Damaged link counts are "10² to 10⁴ times" damaged facilities | **OVERSTATED.** Katrina gives 72,447 / 300 ≈ 2.4 × 10². | The comparison sets *destroyed* poles against *off-line* substations. The ratio also reflects population size (poles far outnumber substations). Per-asset failure probability is the quantity a design rule needs, and none of the lanes computes it. |
| c | A §1 | DOE: "none of the plants experienced any significant damage" | **OVERSTATED** (see check 5) | The quote refers to the 3 nuclear plants only. |
| d | A §2.4 | Poudyal piecewise-linear v_crit / v_col | CONFIRMED (Table: "VOLTAGE LEVEL-BASED CRITICAL AND COLLAPSE SUSTAINED WIND", 115 kV 25 / 55, 161 kV 30 / 60) | The values are in *US maximum sustained* wind, which is 1-min by NHC convention. Lane B's field is 10-min, so these need the WMO K ≈ 0.93 conversion. No lane flags this. |
| e | B step 8 | CoV 10% as the amplitude of a *correlated* residual field | **Source says the opposite on correlation.** | Vickery et al. 2009 (hazard review, fetched): "an **un-correlated** wind field modeling error term … coefficient of variation of 10%". The 10% can be used as an amplitude, but the lane should say the source treats it as uncorrelated. |
| f | A §1 | Hazus Hurricane: hospitals "closed due to lack of power, but most had emergency back-up power" | CONFIRMED (6.1 TM). Lane C cites the same passage from HU-TM 2.1, which is consistent. | — |
| g | A §3 | Noto 2024 cause split 7割弱 power / 6割弱 backhaul / 3割弱 both | CONFIRMED (情報通信審議会 答申 text) | It comes from an earthquake, as Lane A says. |

Not independently checked (secondary or news): the Taiwan counts for Soudelor, Danas, Krathon and Gaemi (CNA, CTEE, GVM, Wikipedia); Jebi and Kansai; Morakot "≈200 bridges"; Willoughby & Rahn B = 1.31 ± 0.36 and 47.5 km; the Willoughby 2006 coefficients via stormwindmodel; HAND thresholds; the WMO gust factors; and Yeh, Loh & Tsai 2003 (TELES). None of these carries a pilot rule by itself except the WMO factors. Those should get a direct check before the 3-s-gust conversion is registered.

---

## 3. Grade inflation

1. **Lane B step 5 is graded "S, TW".** The α and zg inputs are S. The derived ratios, and their use as a *hazard-field* roughness multiplier, are the reviewer's own arithmetic and a J modelling choice (a design-pressure convention used as a site-wind model). Grade it **S inputs / J application**. Lane B's own §2 text says "J-arithmetic on S inputs", but the summary table drops that.
2. **Lane B step 6 is graded "L (bound)" for L_f = 0.6.** It is a secondary citation of a storm-wide intensity decrease with an unverified metric, applied as a per-site factor. Grade it **J**, with Brand & Blelloch via Wu & Kuo as context.
3. **Lane C §5 attributes "t = 0 value 0 for every damage state from Slight upward" to EQ-TM §6.8.** It is J and contradicts the same manual's day-1 tables. Also, Lane A's Hazus Flood "~40% at 10 ft" is read from a figure (J), and it is shown in the Lane A §6 table next to L values.

Secondary sources are generally labelled honestly: Wikipedia, stormwindmodel, and Johansen & Tien via its companion paper.

## 4. Contradictions between lanes

1. **Flood hazard units (A vs B). This is the biggest gap.** Lane A's only facility-level rule is Hazus Flood *depth in feet* against a functional depth (4 ft, 0 ft, 0.5 ft, 24 ft). Lane B's flood field produces only a binary HAND exposure (HAND < h). It has no inundation depth, so none of Lane A's thresholds can be applied. A depth rule (for example depth = h(scenario) − HAND, clipped at 0) would be a new J choice that needs a decision.
2. **Slight damage and function (A vs C).** Lane A's evidence (DOE, FCC, Hazus Hurricane on hospitals) says facilities mostly stay structurally intact and lose function through power and backhaul, with backup covering hours to days. Lane C sets every Slight-damaged facility to off at t = 0. Hazus's own day-1 values (generation 100, communications 99) side with Lane A.
3. **Hospitals (A and C vs Hazus EQ).** Both lanes flag this: EQ Table 6-20 closes a hospital with *any* damage for about 5 days, while the hurricane evidence says backup power keeps hospitals open. The design side must rule.
4. **Hazus Hurricane scope (A vs source, relevant to C).** Lane A says there is no surge treatment of lifelines. The Hurricane TM says water, wastewater and gas (and nominally electric) can be modelled in surge. Lane C's "hurricane model has no lifeline restoration functions" is consistent with the source.
5. **Wind averaging period (A vs B).** Lane B fixes the field at a 10-min mean and converts to a 3-s gust only at lookup. Lane A mixes three bases: 3-s gust (Fani, Serrano-Fontova), US sustained (1-min, Poudyal), and a Japanese 10-min design value. No lane gives the conversion for the 1-min cases.
6. **Damage-state vocabulary (A vs C, and the brief).** Hazus Hurricane uses none / minor / moderate / severe / destruction, while the brief and Lane C use the EQ names slight / moderate / extensive / complete. Lane A flags this correctly. It is still an open J mapping.

## 5. Bottom line for the design side

The numbers the lanes quote from primary sources are accurate. I found no invented figure or citation. The risks are in interpretation:
- **Overreach:** the "at all" in the Hazus Hurricane lifeline scope, the "0% at t=0 for Slight" rule, and the nuclear-plant quote applied to all generation.
- **A flood field that cannot yet drive the depth thresholds.**
- **Lee and roughness factors graded above what supports them.**

Fix these before any of them enter `modeling_rules.yaml`.
