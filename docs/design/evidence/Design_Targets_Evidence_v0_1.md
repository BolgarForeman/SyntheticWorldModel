# Design targets: evidence bundle v0.1 (2026-09-29)

Contains the brief, four research lanes and the independent review. The companion ruling sheet is SWM_Design_Targets_Ruling_Sheet_v0_1.

---

<!-- file: BRIEF.md -->
# Brief: design targets for the unobserved quantities of a synthetic infrastructure world

## What this is for
A generator builds synthetic six-layer infrastructure worlds for a PhD dissertation: power, telecom, water, transport, fuel and healthcare. These worlds are the known truth that optimization answer keys are computed against. No real data source reports some quantities, so the generator draws them for each element. Each draw is centred on a **design target**: what the governing standard, code or authoritative guidance says that class of element should have. Two levers then move the truth away from the target:
- **heterogeneity:** the spread around the target;
- **compliance gap:** the mean shortfall from the target.

A wrong target misplaces the whole world, so every target must be defensible against a real source.

A dependency table for the same world was built this way earlier, and its evidence is in:
/tmp/claude-0/-home-claude-syntheticworldmodel/15967ef4-0a43-5dab-891d-05fc8e96e262/scratchpad/deptable/
(lane_*.md and REVIEW.md). **Read the lane files first.** Their buffer_note columns and source lists already cover much of the backup-power and fuel-tank evidence. Reuse what was verified there, cite it, and note which of its claims the independent review found overstated (see REVIEW.md, section 1). Do not re-derive what is already solid.

## Node classes
- **Power:** generation (thermal: LNG, oil or coal; or a hydro dam), transmission substation, distribution substation.
- **Telecom:** exchange, mast, data_centre, cable_landing.
- **Water:** reservoir, treatment, pumping, storage.
- **Transport:** seaport, airport, freight_yard, bridge.
- **Fuel:** import_terminal (LNG, oil, coal), tank_farm, depot, refinery.
- **Healthcare:** tertiary (tertiary hospital), regional (regional hospital), clinic, blood_bank.

The reference setting is a Taiwan-like island. Where Taiwan practice is found, give it alongside the US standard, and mark which is which.

## Rules for every target
- A target is a **number with units**, or a small set of numbers by class or size. Give the figure, the unit, the source, and a verbatim quote where you can.
- Evidence grade:
  - **S:** a standard, code or regulation that requires it;
  - **L:** literature or a government report that measures or recommends it;
  - **J:** judgment, with no source found. Say plainly what you looked for.
- Mark jurisdiction (US / TW / international).
- Never invent a figure, a citation or a quote. Fetch every source you cite with WebFetch. Paywalled standards (NFPA) may be cited through a reliable secondary source, but say so.
- Where sources give a range, give the range and say which value you would take as the centre and why.
- Keep it concise. Write your output as Markdown to the path you are given, then reply with a short summary.

---

<!-- file: lane_reserves.md -->
# Lane: RESERVES — design targets for stock buffers

A reserve is a stock held against one inbound dependency. The generator draws the stock. The run divides it by the draw to get buffer time. This lane gives, for each consumer class and dependency where a stock exists:

- the target as **stock in physical units**, written as target hours × rated draw;
- the equivalent **hours at rated draw**;
- the evidence grade and jurisdiction.

It also lists where no stock exists, and proposes context factors.

Grades: **S** is a standard, code or regulation; **L** is literature or a government report; **J** is judgment. Jurisdiction: **US**, **TW**, **JP** (Japan, used as a comparator where Taiwan gives the structure of a rule but no number; the resemblance between the TW and JP water standards is my reading, not a sourced lineage), **intl**.

Every source was fetched this session (2026-09-29), or was read in the local copy in `deptable/fuelsrc/`, which is noted where so. Where a figure comes from the dependency-table lanes, it is cited with its lane key, and the review verdict (`deptable/REVIEW.md` §1) is carried over.

---

## 0. Conventions (read first)

1. **The fuel-to-hours conversion.** On-site diesel is sized from the generator's rated output:
   - rule of thumb: "0.07 gallons/hour x kW size of the generator x 24 hours/day = gallons of fuel required per day" [R-EPA], which is **0.265 L per kW per hour at full load**;
   - so `stock_L = target_h × 0.265 × P_gen_kW`.

   Generator rating relative to site load is a separate unobserved quantity, outside this lane.
   `# CHOICE-candidate:` run the division at rated load. EPA notes generators "should run closer to 70% or 80% load", so the real endurance is about 1.25–1.4× longer. Whether draw means rated or expected load is a design decision (Q1).
2. **Batteries** are stocked in kWh: `stock_kWh = target_h × site_load_kW`.
3. **Batteries and a generator in sequence.** Batteries bridge until the generator starts. They carry the load again only if the generator fails or runs dry. The simplest consistent rule is `buffer_h = fuel_h + battery_h` (Q2).
4. **Bulk-energy stocks** (oil, LNG, coal) are defined in law as days of the previous year's average use. For coal this is explicit: "上一年度之平均使用燃料三十天以上數量" [R-TW-COAL] (at least 30 days of the previous year's average fuel use). So **rated draw = previous-year average daily use** for these classes. Hours = days × 24.
5. **Water storage** is stocked in m³ and expressed as hours of **average-day demand** of the zone it serves. The JP and TW standards are written against **maximum-day** demand. Converting one to the other needs a peaking factor, `placeholder (open decision: max_day_to_avg_day_factor)`. The conversions below use 1.25 as an illustration only.

---

## 1. Targets by consumer class

### 1a. Backup-generator fuel (a stock against power loss)

In the dependency table, fuel → X for these classes is `buffer_resupply` (REVIEW F2). The tank below is the buffer on power → X, and the depot edge only refills it.

| consumer class | target (centre) | range in sources | stock formula | grade · jur. | evidence (verbatim where available) | why this centre |
|---|---|---|---|---|---|---|
| **tertiary** | **72 h** | 48–96 h | 72 × 0.265 × P_gen L | L · US; S · JP; L · TW (one hospital) | **US:** NFPA 110 Class X is "usually between 48 and 96 hours" (CSE, secondary; NFPA paywalled) [R-CSE]. "typically must be Class 96 … or have an operational plan to supply 96 hours of fuel" [R-MACKEY]. *Review Check 2: this is Joint Commission practice reported by a trade magazine, not an NFPA 110 requirement. Grade L, not S.* CMS 482.15(e)(3) requires a fuel **plan**, with no duration [R-CMS]. **JP:** disaster base hospitals must "３日分程度の燃料を確保しておくこと" (secure about 3 days of fuel), with generators of "通常時の６割程度の発電容量" (about 60% of normal generating capacity) [R-JP-MHLW]. **TW:** NTUH day tanks "連續運轉 12 小時以上" (more than 12 h of continuous running); the three campuses can run "至少兩天以上" (at least two days) [R-TW-NTUH, lane S25]. *Review Check 3: one hospital, practice only.* No MOHW figure was found (§5). | 72 h is the JP rule for designated disaster hospitals, which are the tertiary analogue. It sits between NTUH's ≥48 h and the US 96 h plan, and the US 96 h may be met partly by contract rather than stock. |
| **regional** | **48 h** | 24–96 h | 48 × 0.265 × P_gen L | J (informed by L) | The US rules do not vary by size: the same CMS and NFPA regime applies [R-CMS][R-CSE]. JP sets 3 days **only** for designated disaster base hospitals, and non-designated hospitals have no fixed figure [R-JP-MHLW]. 48 h is the bottom of the NFPA Class X range. | This is criticality applied as a context factor (§3). If the design side prefers "the standard does not distinguish", set it to 72 h. See Q3. |
| **clinic** | **none by default**; where a generator exists, **8 h** | 0–24 h | 8 × 0.265 × P_gen L | S (absence) · US; J | RHC/FQHC rule 42 CFR 491.12 has no emergency and standby power paragraph [lane fuel S3]. *Review F9: "Std by absence" is not a grade; treat as J.* | Most clinics hold no stock. `has_generator` is a placeholder (open decision: clinic_generator_share). The 8 h is J. |
| **blood_bank** | **48 h** (standalone centre); inherits the hospital's value if hospital-based | 24–72 h | 48 × 0.265 × P_gen L | L (need) · intl; J (duration) | "All blood bank refrigerators, freezers, cold rooms and freezer rooms should be connected to a stand-by electricity generator." [R-WHO §4.7.2, local who.txt]. No duration is given. Cold-chain hold-over is separate: ice-lined units "may hold the temperature below +10 °C for up to 17 hours following a power cut"; solar units hold "at least 24 hours" [R-WHO]. | Set equal to regional. Hold-over is thermal inertia, not a stock, so it is not modelled as a reserve (Q4). |
| **exchange** | **24 h fuel + 4 h battery** | fuel 24–72 h; battery 3–8 h | 24 × 0.265 × P_gen L; 4 × load kWh | L · US | CPUC D.08-09-014 records the FAR finding that "most service providers have backup power for 24 hours at central office facilities and four to eight hours at remote terminals", and the recommendation of "24 hours of fuel storage at the central office facilities with contingency plans for rapid resupply" [R-CPUC08]. FCC 07-177 set 24 h for central offices but never took effect [lane power S-FCC07; review Check 18]. CPUC 72 h applies only in Tier 2/3 fire districts, and for wireline only where "insufficient mobile wireless coverage" exists [lane power S-CPUC; review Check 5]. Battery: "Industry standards for battery backup power for remote terminals provide for a minimum of three to four hours with a design objective of 8 hours" [R-CPUC08]. That is for remote terminals, used here as an analogue. **TW:** no central-office rule found (§5). | 24 h is the documented US practice. The 4 h battery is J, taken from the remote-terminal minimum. |
| **mast** (battery; generator rare) | **4 h battery** (tower site); **2 h** (remote building site); **72 h** (disaster-response site) | 2–8 h ordinary; 72 h designated | 4 × site load kWh | **S · TW**; L · US | 公眾電信網路基地臺設置使用管理辦法 Art. 22 (amended 2024-08-21) [R-TW-NCC22]: open-field tower sites "其備用電源容量須達四小時以上" (backup capacity of at least four hours); remote-area building sites "須達二小時以上" (at least two hours); disaster-response sites "須達七十二小時以上" (at least 72 hours). **No figure is set for ordinary urban building-mounted sites.** US: batteries "generally sized for two to eight hours" (CSRIC IV) [lane fuel S7]. Verizon's internal standard is 8 h (an ex parte filing, not the FCC) [review Check 18]. NENA urged "generators with a minimum of five days fuel supply" [R-FCC07, local f.txt line 505]; this was advocacy, never adopted. | The TW rule governs. For urban building sites with no rule, use 4 h (J, the middle of CSRIC's 2–8 h). The share of disaster-response sites is placeholder (open decision: mast_disaster_site_share). |
| **data_centre** | **72 h** | 12–96 h | 72 × 0.265 × P_gen L | L (industry certification) · intl; L · TW (one operator) | Uptime: "12 hours of minimum fuel storage as a starting point for Tier-defined data centers" [lane fuel S10; review Check 16 confirmed, industry scheme]. TIA-942, as reported by a training provider (standard paywalled): Rating 2 "24 hours", Rating 3 "72 hours", Rating 4 "96 hours", each "as allowed by AHJ" [R-CAPLINE]. **TW:** Chunghwa Telecom IDC Sanchong gives generator fuel of "55小時 (依機房負載情況而定)" (55 hours, depending on data-hall load) [R-TW-CHT]. | TIA Rating 3 is the modal commercial and colocation design, and the Taiwan carrier IDC (55 h) is close to it. Key the target on `rating ∈ {1..4}` → {belly tank ≈ 8 h, 24, 72, 96} if the design side wants a subtype. |
| **cable_landing** | **48 h** | 24–72 h | 48 × 0.265 × P_gen L | J | No standard or report found. I searched for ICPC recommendations, ITU-T L-series and operator landing-station specifications. The only source found is Equinix: stations need "battery and generator backup", with no duration [lane fuel S11]. | Landing stations are carrier buildings between a central office (24 h) and a carrier IDC (55 h) in criticality. Taking the midpoint is J. |
| **treatment** | **48 h** | 24–120 h | 48 × 0.265 × P_gen L | S (capacity) · US; L/J (duration) | Ten States §2.6: standby power "to meet the average day demand". That sets **capacity**, not duration [R-10SS, local ts.txt]. EPA: "One utility manager recommends storing enough fuel to run a generator at 70% load for five days" [R-EPA]. AWWA: plan for "power disruptions that last for several days to weeks" [lane power S-AWWA]. For comparison (wastewater, not this class), Texas 30 TAC §217.36 ties duration to local history: at least "the longest power outage on record for the past 60 consecutive months", with on-site fuel "for the duration of the emergency" where that exceeds 48 h [R-TX217]. **TW:** Taiwan Water practice not found. | No drinking-water rule sets hours. 48 h is J, placed between one day and EPA's single-utility 5 days, and it can be raised by the hazard factor (§3). |
| **pumping** | **24 h** where a fixed generator exists; otherwise none | 0–24 h | 24 × 0.265 × P_gen L | L · US | EPA: a portable unit "must be delivered with a 24-hour fuel supply"; "Smaller water utilities can rotate several portable, gasoline generators between lift and pump stations" [lane fuel S13]. Ten States §6.3.5 allows a second independent substation instead of a generator [lane power S-10SS]. | 24 h is the only duration in the sources. `standby_mode ∈ {generator, second_substation, none}` is set by the recipe; only `generator` carries a stock. |

### 1b. Water storage (a stock against loss of water supply upstream)

| element | target (centre) | range | stock | grade · jur. | evidence | why this centre |
|---|---|---|---|---|---|---|
| **storage** (tank or tower serving a zone) | **12 h of maximum-day demand ≈ 15 h of average-day** (at an illustrative peaking factor of 1.25) | 12–24 h of average-day | m³ = target_h × zone average-day m³/h | S · JP (guideline); S · US; S · TW (no number) | **JP:** 水道施設設計指針 2012 (JWWA Design Guideline, published on MLIT): "計画一日最大給水量の12時間分を標準とする" (12 hours of planned maximum-day supply is the standard) [R-JP-JWWA]. A city standard repeats it: "一日最大給水量の１２時間分に、消火用水量を上乗せ" (12 hours of maximum-day supply, plus fire-fighting water) [R-JP-IWAKI]. **US:** Ten States §7.1.1(a): "The minimum storage capacity … for systems not providing fire protection shall be equal to the average daily consumption", reducible where standby power exists; §7.1.1(c): turnover of "5 days or less" [R-10SS, local ts.txt]. **TW:** 自來水工程設施標準 Art. 85: effective capacity for "設計最大日供水量之時間變化加消防用水量" (the time variation of maximum-day design supply, plus fire water). **No hours are given** [R-TW-WSES]. | Taiwan's standard follows the Japanese structure but omits the number. The JP 12 h of maximum-day is the closest numeric anchor for a TW-like world. The US figure of one average day (24 h) is the upper bound for systems without fire flow. Fire reserve is additional (Q5). |
| **reservoir** (upland impoundment) | outside this lane | — | — | — | The reservoir is itself raw-water storage, and its volume is observed (dam registers). | — |

Taiwan consumers also keep rooftop and basement tanks (the water lane's "5-day supply and 2-day cut-off" note). That is a consumer-side stock that the world does not model except at hospitals (§1c).

### 1c. Healthcare stocks other than fuel

| stock | target (centre) | range | unit | grade · jur. | evidence | why this centre |
|---|---|---|---|---|---|---|
| **hospital on-site water** (tertiary and regional) | **72 h at 300 L per bed per day = 900 L per bed** | 72–96 h | m³ = 0.3 × beds × 3 | L · TW (guideline citing accreditation and WHO) | 醫院之旱災、停水、水短缺緊急應變指引 (hospital drought and water-outage response guideline; issuer and year not stated; hosted at gtma.org.tw): "依據醫院評鑑基準(條號1.8.1 符合項目4)確認醫院持續運作至少三天為最基本需求" (under hospital accreditation criterion 1.8.1 item 4, at least three days of continued operation is the basic requirement). The storage calculation follows the WHO *Hospital Safety Index Guide for Evaluators*: "醫院緊急狀況供水量為 72 小時，每日每床 300 公升" (emergency water supply of 72 hours at 300 litres per bed per day) [R-TW-HWATER]. **US:** a trade article uses **300 gallons** per bed per day for "four days" and attributes neither figure [R-PHCP]. The CDC/AWWA guide sets no duration and cites Joint Commission EM.02.02.09 ("identify alternative means of providing water") [R-CDC-EWSP]. **JP:** "適切な容量の受水槽の保有" (keep a receiving tank of adequate capacity) plus 3 days of drinking water for disaster base hospitals [R-JP-MHLW]. | The TW guideline gives an explicit number and ties it to accreditation. **Note the unit gap:** 300 L (TW, citing WHO) against 300 gal (US trade article) is a 3.8× difference. I did not open the WHO HSI text, so the 300 L figure is secondary (Q6). |
| **clinic water** | **none** | — | — | J | No source requires clinic water storage. The water lane has "Minimal; clinics close". | — |
| **blood inventory** (a stock against loss of collection or processing, and against transport loss to hospitals) | **7 days** of average daily issue (TW) | TW 7–10 d; US ≥3 d | blood units = days × daily issue | L · TW; L · US | **TW:** the Taiwan Blood Services Foundation identifies "seven to 10 days" as the safe level; the reported national average was "just 3.8 days" (Feb 2026) [R-TW-FT]. CNA: "血液安全庫存量為7至10天" (the safe blood inventory is 7 to 10 days), with the national figure at 5 days (June 2026) [R-TW-CNA]. **US:** America's Blood Centers: "3 or more days have enough blood to meet normal operating demands"; "a 2-day supply" is low; "a day or less" is critical [R-ABC]. | 7 d is the lower edge of the stated TW safe band. Observed TW stock often runs at 4–5 days, which is a real compliance gap for the gap lever to carry. Shelf life caps the stock: platelets "Storage 5 days" [R-WHO]. The platelet cap is a component-level rule and is noted, not modelled. |
| hospital medicines, food and supplies (a stock against transport loss) | **3 days** | — | days × daily use | S · JP | "食料、飲料水、医薬品等について … ３日分程度を備蓄しておくこと" (stockpile about 3 days of food, drinking water, medicines and similar) [R-JP-MHLW]. | Not in the brief's list. It is included because it is the only stock on transport → healthcare. Q7. |

### 1d. Primary-fuel stocks at transport consumers (a stock against fuel supply loss)

| consumer | target (centre) | range | unit | grade · jur. | evidence | why this centre |
|---|---|---|---|---|---|---|
| **airport** (jet fuel farm) | **5 days** of average daily uplift | 3–10 d | m³ = days × daily uplift | L (incident reports, anecdote) · US; J | PHMSA/FAAC jet-fuel infrastructure report: Seattle-Tacoma "had only a few days supply on hand"; San Jose "had a 10 day supply of jet fuel"; Reno "had a 3 day supply of jet fuel" [R-PHMSA]. An analyst on Colonial: "We can draw inventory for probably a week" [lane fuel S17]. **TW:** none found. Taoyuan is pipeline-fed from the adjacent refinery [lane fuel S16]. | No standard exists. 5 d is the middle of the reported cases. `fuel_receipt = pipeline` could take the lower end and `truck` the upper (J). |
| airport standby generator (airfield lighting) | fuel hours not found | — | — | — | FAA AC 150/5340-30J and JO 6950.2F set start time (15 s), not fuel duration [lane power S-FAA30J, S-FAA6950]. | Use 24 h (J), or omit. Q8. |
| **seaport** (diesel for cargo-handling equipment) | **3 days** | 1–7 d | m³ = days × daily use | J | No source found. I searched for port-authority fuel-storage norms. Bunker stocks sit in co-located tank farms and import terminals, not in the port node [lane fuel S15]. | J. |
| **freight_yard** (on-site dispenser tank) | **3 days** | 1–7 d | m³ = days × daily use | J | No source found. | J. |

### 1e. Bulk-energy stocks

| element | target (centre) | range | unit | grade · jur. | evidence | why this centre |
|---|---|---|---|---|---|---|
| **import_terminal, LNG** (national gas safety stock) | **11 days** (legal floor in 2025); **14 days** from 2027 | 7–14 d (legal path); tank capacity 20–24 d | t LNG = days × previous-year average daily send-out | **S · TW** | MOEA Energy Administration: "安全存量天數2019年至少為7天，2027年達14天，儲槽容積天數2019年為15天，2027年達24天" (safety stock at least 7 days in 2019, reaching 14 in 2027; tank-capacity days 15 in 2019, reaching 24 in 2027). The table gives 2022: 8 d / 16 d; 2025: 11 d / 20 d. The legal basis was set in 2018: "已明定天然氣進口業者應儲備天然氣安全存量" (gas importers are required to hold a safety stock) [R-TW-MOEA-GAS]. Observed: "10 to 11 days of use" (MOEA estimate, 2026) [R-EIA-TW, local eia.txt]; "about 16 days" operating turnover at Yung-An and Taichung (INDSR) [R-INDSR]. | Choose the legal floor for the world's reference year. A recipe key `reference_year` selects 11 or 14. |
| gas-fired generation (on-site gas) | **none** | — | — | L | "No real on-site gas store at the plant" [lane fuel, fuel → power row]. | The stock sits at the terminal. |
| **import_terminal (oil) and tank_farm** (oil security stockpile) | **60 days** industry-held + **30 days** government-held = **90 days** national | 90 d legal; ~146 d observed | kL = days × daily supply | **S · TW** | Energy Administration (English): refiners and importers "maintain an oil security stockpile of no less than sixty days of supply"; "the government must also maintain an oil security stockpile of no less than 30 days" [R-TW-MOEA-OIL]. The same wording appears in Petroleum Administration Act Art. 24 [lane transport S5]. Observed: "enough oil stockpiled to last 146 days" (MOEA 2024, via EIA) [R-EIA-TW]; S&P "about 146 days" [R-SP]. LPG: "液化石油氣則應儲備25日之安全存量" (LPG 25 days) [R-INDSR; secondary]. | Legal floor. Allocation across facilities is J: the industry 60 d sits pro rata in terminals, refineries and tank farms; the government 30 d in designated tank farms (Q9). The calculation basis for "days" was not retrieved. |
| **refinery** (crude and product stock) | part of the 60-day industry stock | — | kL | S · TW (aggregate) | As above. | J allocation. |
| **depot** (product for delivery) | **3 days** of outbound delivery | 2–7 d | kL | J | No source found. I searched for CPC depot norms and API bulk-plant guidance. | J. |
| **coal generation** (on-site stockpile) | **30 days** of previous-year average burn | 30 d legal; ~39 d observed TW; ≥60 d typical US | t coal = days × previous-year average daily burn | **S · TW**; L · US | 能源管理法 implementing standard (能源供應事業及能源用戶…應儲存之安全存量): "燃煤火力電廠上一年度之平均使用燃料三十天以上數量" (coal-fired plants: at least 30 days of the previous year's average fuel use) [R-TW-COAL]. Observed: "coal is about 39 days" [R-SP]. INDSR: "火力電廠需有30天以上的安全存量" (thermal plants must hold 30 days or more) [R-INDSR]. US: "more than 90% of coal-fired power plants currently having enough coal on hand to generate electricity for 60 days or more" [R-EIA-COAL]. | The legal floor. Observed TW stock is above it (a negative compliance gap). This depends on the design side adding `import_terminal[product=coal]` (REVIEW F5); without a supplier, this stock never binds. |
| **oil-fired generation** | **J: 30 days** | — | kL | J | No source found. Oil is a small share of TW generation [R-EIA-TW]. | Set equal to the coal rule by analogy. |

---

## 2. Where no stock buffer exists

The world has only stock buffers. So each dependency below has **zero buffer**: the consumer fails when the supply fails, subject only to the dependency's own onset.

| dependency | consumer classes with **no** stock | why |
|---|---|---|
| **telecom → any** | every class | Communications cannot be stocked. The dependency-table buffers for telecom (manual fallback, crews switching by hand) are **degradation onsets, not stocks**. If the model has only stock buffers, telecom loss takes effect at once. Q10 asks whether that is intended. |
| **power → X** | transmission_substation and distribution_substation (they are the supply; station DC batteries serve their own protection and control, not an inter-layer dependency); seaport (cranes have no standby) [lane power]; freight_yard (unless cold storage, J); tank_farm and depot (none, except the Florida-type 72 h rack rule, which is US state-only [lane power S-FL526]); import_terminal (LNG: "small emergency generators to enable orderly shutdown" only [lane power S-LNG]), so zero operating stock; refinery (self-generation is a share of load, not a stock); clinic (default); pumping where `standby_mode ≠ generator`; mast sites with no battery (none by the TW rule) | — |
| **fuel → X (primary)** | gas-fired generation (the pipeline has no on-site store); hydro (no fuel) | The stock is upstream at the LNG terminal. |
| **water → X** | clinic; distribution and transmission substations (no water dependency); data_centre (make-up tanks of "roughly 1–2 days" are the water lane's unverified judgment, so **no target is set here**, Q11); tertiary and regional hospitals **do** hold stock (§1c) | — |
| **transport → X** | tank_farm and depot (their product stock is the buffer against *supply* loss, not transport loss; for delivery, the stock sits at the depot); clinic (no stated stock) | Hospital supplies and blood are covered in §1c. |

---

## 3. Context factors: how the target should shift

Every factor is a multiplier or an override on the class target. Where the evidence is a rule, the rule is quoted.

| factor | direction | evidence | proposed form |
|---|---|---|---|
| **Criticality (designation)** | Up, sharply, for designated elements | **TW:** NCC designated disaster-response base stations need **72 h** against 4 h for ordinary tower sites (18×) [R-TW-NCC22]. **JP:** 3 days of fuel, water and supplies apply only to designated disaster base hospitals [R-JP-MHLW]. **Intl:** TIA-942 Rating 2/3/4 → 24/72/96 h [R-CAPLINE]. | `designated: bool` drawn by class. When true, the target is overridden to the designated value: mast 72 h, hospital 72 h, data_centre by rating. This is a step override, not a smooth multiplier. |
| **Hazard exposure** | Up where the hazard lengthens outages | **US:** CPUC 72 h applies only "in Tier 2 and Tier 3 High Fire-Threat Districts" [lane power S-CPUC]. Texas wastewater: duration ≥ "the longest power outage on record for the past 60 consecutive months" [R-TX217]. Florida nursing homes and ALFs: "96 hours" of fuel, applied uniformly across the state [R-FL-EPP]. This is a hurricane-state rule; the source does not state the rule's motivation. | `hazard_zone ∈ {ordinary, high}`. High raises backup-fuel targets to max(class target, 72 h). A continuous form is the Texas rule: target = max(class target, recipe `longest_outage_h` for the zone). The Texas form is the most defensible because it is a rule, but it needs an outage-history field. |
| **Remoteness / outlying island** | **Mixed evidence.** Resupply time argues up, but the only rule found goes **down**. | **TW:** remote-area building base stations need only **2 h**, against 4 h for tower sites, relaxed for structural weight [R-TW-NCC22]. Against that: EPA asks for plans to refuel "those in remote locations" [R-EPA]; neighbour-island blood can take "up to 24 hours" to arrive by air [lane transport S12]; NENA sought 5 days of fuel at wireless sites [R-FCC07]. No outlying-island (Penghu, Kinmen, Matsu) fuel-stock rule was found; the Matsu Daily article returned 404. | J: `outlying_island: bool` → multiply bulk and backup-fuel targets by a resupply-interval factor, `placeholder (open decision: island_resupply_factor)`, for example 2×. Record the NCC 2 h rule as the one counter-case, and do **not** apply the island factor to mast batteries. |
| **Size** | Up with size or rank inside a class | CO 24 h against remote terminal 4–8 h [R-CPUC08]. Tower 4 h against building-site 2 h [R-TW-NCC22]. Data-centre rating [R-CAPLINE]. The tertiary/regional split (§1a). US hospital rules do **not** vary with size [R-CMS]. | Implement size through class and subtype (already present), not as a continuous multiplier. No source supports a smooth size elasticity. |
| **Reference year** (bulk stocks only) | Up over time for TW gas | 7 → 8 → 11 → 14 days (2019 → 2027) [R-TW-MOEA-GAS]. | `reference_year` selects the legal floor. |

---

## 4. Questions for the design side

1. Is draw rated load or expected load? It changes endurance by about 1.25–1.4× (§0.1).
2. Should battery and generator hours add in sequence at sites that have both?
3. Regional hospitals: 48 h (criticality-adjusted) or 72 h (the standards do not distinguish)?
4. Thermal hold-over (blood refrigerators, 17–24 h) is buffer time without a stock. Omit it, or model it as a pseudo-stock?
5. Should the fire reserve in distribution storage count toward the water buffer?
6. Hospital water: 300 L per bed per day (TW, citing WHO HSI) or 300 gal (US trade article)? The WHO HSI original was not opened.
7. Add hospital supply stock (3 days, JP) as the buffer on transport → healthcare?
8. Airport standby-generator fuel: no source. Omit it, or use 24 h (J)?
9. How should the 60-day and 30-day oil stockpile be allocated across import_terminal, refinery and tank_farm nodes?
10. Is zero buffer on all telecom dependencies intended? The dependency table recorded onsets of hours to days.
11. data_centre make-up water: no verified figure. Set none, or use J 24 h?

## 5. Searched for and not found

- Taiwan MOHW hospital emergency-generator fuel duration. 醫療機構設置標準 was not retrieved in full. 醫院緊急醫療能力分級評定基準 (2019) has no infrastructure criteria.
- A Taiwan central-office (機房) backup-power rule.
- Taiwan Water Corporation standby-fuel practice.
- A Taiwan outlying-island fuel-stock rule.
- Landing-station fuel specifications (ICPC, ITU-T).
- Airport and port fuel-storage norms.
- The IEA 90-day obligation (the fetch was not approved, so it is not cited).
- The calculation basis for Taiwan oil "days".

## 6. Review carry-overs (from `deptable/REVIEW.md` §1)

These claims were found **overstated** and are graded down here:

- the "NFPA 110 Class 96" hospital figure (Check 2);
- the FCC 24 h and 8 h rules, which never took effect (Check 18);
- the Verizon 8 h standard, which is a company figure, not the FCC's (Check 18);
- NTUH, which is one hospital (Check 3).

Uptime 12 h (Check 16) was **confirmed** but is an industry scheme. CPUC 72 h (Check 5) was confirmed, with its narrow scope.

## Sources

Fetched this session unless marked local.

- **R-EPA** US EPA, *Power Resilience Guide for Water and Wastewater Utilities*, EPA 800-R-19-001 (local `fuelsrc/epa.txt`). https://www.epa.gov/sites/default/files/2016-03/documents/160212-powerresilienceguide508.pdf
- **R-10SS** *Recommended Standards for Water Works*, 2022, §§2.6, 7.1.1 (local `fuelsrc/ts.txt`). https://files.dep.state.pa.us/Water/BSDW/Public_Water_Supply_Permits/2022_Recommended_Standards_for_Water_Works.pdf
- **R-CSE** CSE Magazine, *The role of NFPA 110…* (lane power S-NFPA). https://www.csemag.com/role-of-nfpa-110-and-interaction-with-other-codes/
- **R-MACKEY** Mackey, *CSE* 2022 (lane fuel S2). https://www.csemag.com/hospital-emergency-power-supply-systems/
- **R-CMS** 42 CFR 482.15. https://www.law.cornell.edu/cfr/text/42/482.15
- **R-JP-MHLW** 厚生労働省, 第12回救急・災害医療提供体制等の在り方に関する検討会 資料 (12th meeting of the MHLW study group on emergency and disaster medical care; 2019-03-29). https://www.mhlw.go.jp/content/10802000/000497051.pdf
- **R-TW-NTUH** 善科教育基金會, 停電時醫院該怎麼辦？ (What should a hospital do in a power outage?; local `fuelsrc/san.html`). https://www.sancode.org.tw/activities_info.php?type=3&nid=181
- **R-WHO** WHO, *Manual on the management, maintenance and use of blood cold chain equipment*, 2005 (local `fuelsrc/who.txt`).
- **R-CPUC08** CPUC D.08-09-014. https://docs.cpuc.ca.gov/published/FINAL_DECISION/87681-06.htm
- **R-FCC07** FCC 07-177 (local `fuelsrc/f.txt`).
- **R-TW-NCC22** 公眾電信網路基地臺設置使用管理辦法 (Regulations on the Establishment and Use of Public Telecommunications Network Base Stations), Art. 22, amended 2024-08-21. https://www.rootlaw.com.tw/LawArticle.aspx?LawID=A040410000006300-1130821
- **R-CAPLINE** Capitoline Training, *How much diesel fuel does a data centre need?* (secondary report of TIA-942). https://www.capitolinetraining.com/how-much-diesel-fuel-does-a-data-centre-need/
- **R-TW-CHT** 中華電信 IDC (Chunghwa Telecom data centre), 新北三重機房 (New Taipei Sanchong site). https://www.idc.hinet.net/Environment_Location_New_Taipei_Sanchong.html
- **R-TX217** 30 Tex. Admin. Code §217.36. https://law.cornell.edu/regulations/texas/30-Tex-Admin-Code-SS-217-36
- **R-JP-JWWA** 水道施設設計指針 2012 (JWWA Design Guideline for Waterworks Facilities; MLIT copy). https://www.mlit.go.jp/common/830003599.pdf
- **R-JP-IWAKI** いわき市水道局, 水道施設設計基準 (Iwaki City waterworks design standard). https://www.city.iwaki.lg.jp/www/contents/1001000002120/simple/sekkeikijun07_1.pdf
- **R-TW-WSES** 自來水工程設施標準 (Waterworks Engineering Facilities Standard; 2003), Arts. 75, 85. https://law.moea.gov.tw/LawContent.aspx?id=FL027518
- **R-TW-HWATER** 醫院之旱災、停水、水短缺緊急應變指引 (hospital drought and water-outage emergency response guideline). https://gtma.org.tw/upload/file/1/14279580280.pdf (saved to `targets/src/gtma.pdf`)
- **R-PHCP** PHC News, *Hospital Emergency Water Needs*. https://www.phcppros.com/articles/15571-hospital-emergency-water-needs
- **R-CDC-EWSP** CDC/AWWA, *Emergency Water Supply Planning Guide for Hospitals*, 2019. https://www.cdc.gov/water-emergency/media/pdfs/2024/07/emergency-water-supply-planning-guide-2019-508.pdf
- **R-TW-FT** Focus Taiwan, 2026-02-20. https://focustaiwan.tw/society/202602200006
- **R-TW-CNA** 中央社 (Central News Agency), 2026-06-28. https://www.cna.com.tw/news/ahel/202606280061.aspx
- **R-ABC** America's Blood Centers, blood supply widget. https://americasblood.org/widget/
- **R-PHMSA** PHMSA/FAAC, jet fuel infrastructure report. https://www.transportation.gov/sites/dot.gov/files/docs/PHMSA_jetfuel_infrastructure_report_faac_rec_14.pdf
- **R-TW-MOEA-GAS** 經濟部能源署 (MOEA Energy Administration), 確保天然氣供應穩定 (Ensuring stable natural gas supply). https://www.moeaea.gov.tw/ECW/populace/content/Content.aspx?menu_id=8748
- **R-TW-MOEA-OIL** MOEA Energy Administration (English), oil security. https://www.moeaea.gov.tw/ECW/english/content/Content.aspx?menu_id=8675
- **R-EIA-TW** US EIA, *Taiwan Analysis Brief*, Apr 2026 (local `fuelsrc/eia.txt`).
- **R-SP** Yep, S&P Global, 2024-05-30. https://www.spglobal.com/energy/en/news-research/latest-news/lng/053024-taiwan-vulnerable-to-lng-supply-risks-in-the-event-of-a-maritime-blockade
- **R-INDSR** 國防安全研究院 (Institute for National Defense and Security Research), 緊急時期能源與電力供應韌性… (Energy and power supply resilience in emergencies). https://indsr.org.tw/respublicationcon?uid=12&resid=1855&pid=1102
- **R-TW-COAL** 能源供應事業及能源用戶…應儲存之安全存量 (the safety-stock standard for energy suppliers and energy users under the Energy Administration Act). https://law.moea.gov.tw/LawContent.aspx?id=GL000527
- **R-EIA-COAL** US EIA, *Today in Energy* 62684. https://www.eia.gov/todayinenergy/detail.php?id=62684
- **R-FL-EPP** Miami-Dade OEM, summary of the Florida nursing-home and ALF emergency power rules. https://www.miamidade.gov/fire/library/OEM/nursing-hime-rule.pdf

---

<!-- file: lane_requirements.md -->
# Lane: node requirements per commodity (design targets)

Date: 2026-09-29. A requirement is what a node draws from each supplier layer in **normal operation**. Coupling strength is later derived as supplier capacity divided by it.

Grades: **S** standard or code; **L** literature or government data; **J** judgment. Jurisdiction: US / TW / Intl. "Derived" means that I did the arithmetic on fetched figures, and the arithmetic is shown.

## 0. Reused from the dependency-table lanes, and what the review changes

- **Taipower Art. 46.** lane_power had the article text but not the Attachment 6 thresholds. They are now retrieved (§6).
- **Backup fuel is not a normal-operation requirement** (REVIEW F2). A hospital, exchange, mast or pump that has a generator draws **zero fuel while grid power is up**. §3 gives its generator burn rate only so the reserve can be turned into hours when power is lost. Do not add it to the fuel requirement.
- **Coastal thermal make-up water** (REVIEW F7, check 25). The Encina source shows the municipal edge can be removed. It sets the size of the requirement only where `makeup_water_source = municipal`.
- **Data centre water** (REVIEW F13): default to evaporative cooling.
- **Refinery water** (REVIEW F18): no layer draw if self-supplied.
- **Overstated claims I have not reused:**
  - NFPA 110 "Class 96" (REVIEW check 2);
  - the FCC 07-177 cell-site hours (check 18);
  - "two substations" as a class-wide rule for tertiary hospitals (check 3). §6 shows Taipower requires two circuits only above set contract capacities.

---

## 1. Electrical load (average MW in normal operation)

| Class | Target (centre) | Range / basis | Size proxy | Grade, jurisdiction | Source |
|---|---|---|---|---|---|
| **tertiary** | **2.5 kW per bed** (for example 800 beds → 2.0 MW; 1,000 beds → 2.5 MW) | TW upper bound **2.9 kW/bed** (derived: 13.54 t CO2e per bed per year ÷ 0.529 kg CO2e/kWh = 25.6 MWh/bed/yr; an upper bound because hospitals also burn fuel). US **8.2 kW/bed** (derived: CBECS 2018 inpatient electricity 65 billion kWh ÷ AHA 907,216 staffed beds). German public hospitals **0.9 kW/bed** (7,786 kWh/bed/yr, the 2009 Fraunhofer figure cited in [R5]). | beds | L (TW bound, US, EU) + **J** for the centre and the tertiary/regional split | [R1][R2][R3][R4][R5] |
| **regional** | **2.0 kW per bed** | Same band. A lower acuity mix gives less per bed. | beds | J (within the L band) | as above |
| **clinic** | **0.027 MW** per clinic | CBECS 2018 outpatient: 238,000 kWh per building per year = 27 kW average; 17.4 kWh/ft²/yr | class constant (floor area if the generator gets it) | L, US | [R2] |
| **blood_bank** | **0.03–0.1 MW**; centre 0.05 | No source found. I searched for blood-centre energy benchmarks and for CBECS "laboratory". I took the outpatient intensity and scaled it up for cold rooms. | class constant | **J** | — |
| **exchange** | **0.2 MW**; range 0.05–1 | No central-office load figure found. ECM's "350 kW to 8 MW" is for internet hosting sites, not exchanges. I searched ECM, EnerSys and telephone-switching surveys. | class constant | **J** | [R6] (context only) |
| **mast** | **0.006 MW** (4G); **0.012 MW** (5G) | 4G "around 6kW … rising to 8-9kW at peak". 5G "around 11.5Kw" (Huawei); "14kW on average and 19kW at peak" (ABI, a projection). | class constant, subtype 4G/5G | L (trade press citing analysts), Intl | [R7] |
| **data_centre** | **IT MW × PUE**, with PUE = **1.57** | Uptime survey average PUE "stuck in the 1.55 to 1.59 band" since 2020; newer sites about 1.45–1.48 | capacity (MVA × power factor 0.9 ≈ site MW). If capacity is IT MW, multiply by PUE. | L, Intl | [R8] |
| **cable_landing** | **0.1 MW**; range 0.02–0.5 | One 7,000 km system: PFE "7.1 kW", terminal equipment "41.5 kW"; the coastal station "~90 kW" before optimisation | number of cable systems landed (× 0.1 MW) | L (conference paper) for one system; J for the per-system scaling | [R9] |
| **treatment** (water) | **0.37 kWh/m³ × plant flow** (surface); **0.48** (groundwater) | EPRI: 1 MGD 0.392; 10 MGD 0.371; 100 MGD 0.372 kWh/m³. "About 80 to 85 percent" of this is high-service pumping into distribution. Example: 100,000 m³/day → 1.55 MW. | treatment m³/day | L, US | [R10] |
| **pumping** | **P (kW) = 9.81 × Q (m³/s) × H (m) / η**, with η = 0.7 | Physics. Head H is not a generator attribute; I would draw 30–60 m (**J**). Example: 0.5 m³/s at 45 m → 0.32 MW. | flow m³/day (and a drawn head) | S (engineering identity) for the formula, J for H and η | — |
| **seaport** (container) | **25 kWh of electricity per box handled** → 1 M boxes/yr ≈ 2.9 MW | ECLAC: median "8 litres" of diesel equivalent per dry box (LAC 2015). Only "32%" of terminal energy in LAC was electricity. STS cranes "7.9 kwh per move". Reefers are 40% of terminal energy where on shore power. The 25 kWh is derived: 8 L × ~10 kWh/L (an **unverified** conversion) × 0.32. | WPI size class → boxes/yr (the mapping is **J**) | L for inputs, J for the per-box electricity | [R11][R12] |
| **airport** | **3 kWh per passenger** → 40 M pax/yr ≈ 14 MW | Vienna 2019: 91.9 GWh of electricity out of 177 GWh total at "3 kWh per traffic unit" (derived: ≈1.6 kWh electricity per traffic unit). Kansai 2011: 7.38 kWh electrical per passenger. Greek airports: 4–18 kWh/pax total energy. I took a centre between the two electricity figures. | airport size class → annual pax (mapping **J**) | L, Intl, + J centre | [R13] |
| **freight_yard** | **0.5 MW** | No source found. I looked for rail and truck yard electricity benchmarks. | class constant | **J** | — |
| **refinery** | **7.0 kWh purchased per barrel** of crude run → 100 kb/d ≈ 29 MW | Derived: EIA 2025 purchased electricity 42,672 million kWh ÷ (16,731 kb/d × 365). Excludes self-generation; set `self_generation_share` (lane_power). | crude capacity b/d | L, US | [R14][R15] |
| **tank_farm** | **1 MW** | No benchmark found. Transfer pumps only: use the pumping formula on the rack flow. | throughput or tank capacity | **J** | — |
| **depot** | **0.1 MW** | No benchmark found. | class constant | **J** | — |
| **import_terminal (LNG)** | **~10 kWh per tonne** of LNG sent out → about **1.1–1.5 MW per Mtpa** | No published terminal figure reachable. Physics: send-out pumps to about 80 bar ≈ 6.6 kWh/t; ORV seawater pumps ≈ 2.4 kWh/t; plus in-tank pumps and BOG compressors. Context: heat to regasify "~730 kJ/kg" [R16]. | send-out Mtpa | **J** (physics estimate) | [R16] |
| **import_terminal (oil)** | **2 MW** | No source found. Pumps: use the pumping formula. | throughput | **J** | — |
| **import_terminal (coal)** | **1 MW** (unloaders and conveyors) | No source found. | throughput | **J** | — |

**The 69/161 kV question in practice.** At these targets, a tertiary hospital (2–3 MW) sits below Taipower's 5,000/10,000 kW high-voltage allowance (§6), so it is distribution-connected. A 100 kb/d refinery (about 29 MW) and a large data centre sit at or near the 30 MW line for 161 kV.

## 2. Water demand (m³/day)

| Class | Target | Basis | Size proxy | Grade, jurisdiction | Source |
|---|---|---|---|---|---|
| **tertiary** | **1.0 m³ per bed per day** | TW design code Table A-1, 醫院: 高級 "1000 以上" L per bed; 中級 "500 以上"; 其他 "250 以上". Also staff 120 L, nurses 160 L and visitors 8 L each (not in the per-bed figure). Wastewater code cross-check: 350 L/person/day at 1.5 persons per bed = 525 L per bed. | beds | **S, TW** (design basis, a floor: "以上") | [R17][R18] |
| **regional** | **0.5 m³ per bed per day** | Same table, 中級 | beds | S, TW | [R17] |
| **clinic** | **2 m³/day** | No per-clinic figure. The code's per-person values (staff 120 L, visitors 8 L) times a small clinic's headcount | class constant | J (built on S unit values) | [R17] |
| **blood_bank** | **5 m³/day** | No source found | class constant | **J** | — |
| **data_centre** | **1.8 L per kWh** of site energy → **43 m³/day per MW** of site load | LBNL: "approximately 1.8 liters (0.46 gallons) per kWh of total data center site energy". Dry or air-cooled sites are near zero, but the default is evaporative (F13). | site MW | L, US | [R19] |
| **refinery** | **1.5 m³ of water per m³ of crude** → 100 kb/d ≈ 23,850 m³/day | DOE: "about 1.5 barrels of water to process 1 barrel of crude oil". Varies with once-through vs recirculating cooling. About 60% take municipal water. | crude capacity b/d; zero if `water_source = self` | L, US | [R20] |
| **generation, recirculating (tower)** | **1.7 m³/MWh** consumed (withdrawal about 2.3) | USGS 2015 tower consumption 0.18–0.70 gal/kWh = 0.68–2.65 m³/MWh; withdrawal 0.25–0.95 gal/kWh. I took the midpoint because the source gives a range, not a median. | MW output | L, US; J centre | [R21] |
| **generation, coastal once-through** | **~2,000 m³/day per plant** (boiler make-up, seals, potable use), only if `makeup_water_source = municipal` | Encina: fresh water "purchased from the local water district"; a 400 gpm RO plant was sized to replace it (= 2,180 m³/day). One plant; its MW is not in the source. | class constant (per plant) | L (one US plant) + J | lane_water [S3]; REVIEW check 25 |
| **hydro, reservoir, storage** | 0 (see lane_water) | — | — | — | lane_water |

## 3. Fuel draw

**Thermal generation (per MWh generated).** These are US operating averages. No Taipower heat-rate source was retrieved.

| Fuel | Heat rate | Energy per MWh | Physical per MWh | Grade | Source |
|---|---|---|---|---|---|
| Coal | 10,777 Btu/kWh (2024) | 11.4 GJ | 0.52 t (1.14 lb/kWh, 2022) | L, US | [R22][R23] |
| Natural gas / LNG (fleet) | 7,754 Btu/kWh | 8.2 GJ | 210 m³ of gas (7.42 ft³/kWh, 2022) | L, US | [R22][R23] |
| Gas combined cycle | 7,548 Btu/kWh (tested, 2024) | 8.0 GJ | — | L, US | [R24] |
| Gas turbine (peaker) | 10,999 Btu/kWh | 11.6 GJ | — | L, US | [R24] |
| Petroleum | 11,200 Btu/kWh (steam 10,331; GT 13,083) | 11.8 GJ | 0.30 m³ (0.08 gal/kWh) | L, US | [R22][R23][R24] |

**Recommendation:** carry fuel draw in **GJ/MWh**. This avoids an unsourced LNG tonne conversion. Centre on combined cycle (8.0) for LNG plants and on steam (10.0) for coal. Size proxy: generation MW × capacity factor.

**Backup generator at rated load: 269 L/h per MW.** Generator Source chart, 1,000 kW row: "21.6 | 36.4 | 52.1 | 71.1" gal/h at ¼, ½, ¾ and full load. That gives 269 L/h at full load, 197 L/h at ¾ and 138 L/h at ½, per MW. The chart is a vendor's own "estimate". Grade: L (trade), Intl. Source [R25].
- This is **not** a normal-operation requirement; see §0.
- It turns the fuel reserve into buffer hours: reserve L ÷ (genset MW × load fraction × rate).
- **Size proxy:** the node's electrical requirement from §1. The genset is sized to the essential load, which is placeholder (open decision: essential_load_fraction).

**Airport jet fuel. J.** No clean per-passenger or per-movement figure was fetched. The inputs I did fetch mix military use and uplift abroad: EIA kerosene-jet product supplied is 1,737 kb/d for 2025 [R15b]. Recommendation: requirement = departures × mean uplift, placeholder (open decision: jet_uplift_per_departure_m3). Size proxy: airport size class.

**Freight-yard diesel. J.** No source found. ECLAC gives a comparable port figure of 4.7 L diesel equivalent per box for horizontal moves [R11]. Recommendation: yard diesel requirement = lifts/day × 4.7 L, as placeholder (open decision: freight_yard_diesel).

## 4. Telecom

**Recommendation: make the telecom requirement binary (served or not served) for every consumer class.**

Coupling strength for telecom → X then becomes a **count of independent served paths** (1, 2, …) rather than a capacity ratio.

Reasons:
- No emitted or drawn attribute carries bandwidth.
- The dependency types for telecom are control and service (lane_telecom, REVIEW F6). What fails is the presence of a signal path, not a shortfall in Mb/s.
- A bandwidth requirement would be a number the world cannot check against any supplier capacity. That would break the "Plant quietly" rule by making the telecom term arbitrary.

This changes what "coupling strength" means for one layer, so it is a **specification question** (Q2).

## 5. Size proxies, summary

- **beds:** tertiary, regional (power, water).
- **class constant:** clinic, blood_bank, exchange, mast (4G/5G subtype), freight_yard, depot.
- **capacity MVA:** data_centre (power; water through site MW); transmission and distribution substations are suppliers, not consumers.
- **treatment m³/day:** treatment (power); pumping (power, through flow and head).
- **WPI size class:** seaport. The generator needs a table from class to boxes/yr (**J**; Q3).
- **airport size class:** airport. The generator needs a table from class to passengers/yr (**J**; Q3).
- **crude b/d:** refinery (power, water).
- **Mtpa / throughput:** import terminals, tank_farm.
- **generation MW × capacity factor:** thermal generation (fuel, water).

## 6. Transmission vs distribution threshold (Taipower 營業規章 Art. 46(三)(一))

The table was retrieved **verbatim** from the Taipower letter 電配售部業字第10800032292號 (26 Feb 2019), which carries the revised 營業規章 text [R26]. **Caveat:** rootlaw lists a later version (2022-09-07) whose table did not render [lane_power S-TW-TP]. The thresholds should be checked against that version (Q4).

| Contract capacity (契約容量) | Supply voltage |
|---|---|
| "未滿 100 瓩" (under 100 kW) | "應以低壓供電" (low voltage) |
| 100 kW to under 1,000 kW (22.8 kV areas: under 2,000 kW) | "應以高壓供電" (high voltage). Under 500 kW may take 220/380 V. |
| 1,000 kW (22.8 kV areas: 2,000 kW) to under 30,000 kW | "除下列情形外，應以 69 千伏特供電" (69 kV, except where): in 11.4 kV areas under **5,000 kW**, or in 22.8 kV areas under **10,000 kW**, the customer may take high voltage on request. In planned areas the limits are 7,500 kW at 11.4 kV and 15,000 kW at 22.8 kV. Above 5,000 kW (11.4 kV) or 10,000 kW (22.8 kV) the customer must also apply for standby supply "以兩回線經常供電" (two circuits in regular service). |
| 30,000 kW to under 225,000 kW | "應以 161 千伏特供電" (161 kV). Under 60,000 kW may take 69 kV. At 69 kV, 40,000 kW or more needs two circuits. |
| 225,000 kW and over | 345 kV. Under 450,000 kW may take 161 kV, with two circuits at 225,000 kW or more. |

Also (三): a customer who provides land for a Taipower-built substation may be served at high voltage up to **15,000 kW** from an 11.4 kV secondary substation, or **30,000 kW** from an 11.4/22.8 kV distribution substation.

**Recommended generator rule (TW):**
- `load_mw < 10` → distribution_substation (22.8 kV practice; 5 for 11.4 kV areas).
- `10 ≤ load_mw < 30` → 69 kV. In the generator's two-class scheme this is transmission_substation.
- `load_mw ≥ 30` → transmission_substation (161 kV).
- Replace placeholder `transmission_connection_threshold_mw` with **10 MW**. Grade **S, TW**.
- Treat contract capacity as roughly peak demand, so apply the threshold to peak (= requirement × peak factor, placeholder (open decision: peak_to_average_factor)), not to the average.

**By-product for REVIEW F4.** Taipower *requires* two regular circuits above 5,000/10,000 kW at high voltage and above 40,000 kW at 69 kV. A defensible `dual_utility_feed` rule is therefore "true if peak load is at or above that line". This replaces the one-hospital claim. At the §1 targets most tertiary hospitals fall **below** it.

**US.** No single national threshold exists; it is set utility by utility in tariffs. I did not search individual US tariffs.

## 7. Questions for the design side

1. **Hospital per-bed centre.** US (8.2), TW bound (≤2.9) and EU (0.9) kW/bed differ nine-fold. I centred on TW (2.5/2.0), which is judgment inside the bound. Should the world take TW or US as its reference?
2. **Telecom requirement.** Binary, with coupling strength as a path count (§4)? This changes what coupling strength means for one layer.
3. **Class-to-size tables** for WPI harbour size and airport size class (boxes/yr, passengers/yr) are not in the specification, and I found no source that maps them.
4. **The Taipower table version.** Confirm that the 2022 營業規章 kept the 2019 thresholds.
5. **Peak vs average.** Requirements here are averages. Does coupling strength use average or peak? The connection threshold should use peak.

## Sources (all fetched this session unless marked)

- [R1] MOHW, 酷熱夏天!醫院省電大作戰. https://www.mohw.gov.tw/fp-3797-43466-1.html. "2016年有150家醫院填報資料，平均每病床碳排放量為13.54公噸"
- [R1b] MOENV, 105年度電力排放係數. https://ghgregistry.moenv.gov.tw/Upload/News3/00000283_001.pdf. "0.529公斤CO2e/度"
- [R2] EIA CBECS 2018, Tables C13 and C14. https://www.eia.gov/consumption/commercial/data/2018/ce/pdf/c14.pdf (c13.pdf). Inpatient "7,631" thousand kWh per building and 28.8 kWh/ft²; outpatient 238 and 17.4; inpatient total 65 billion kWh, 2,259 million ft².
- [R3] AHA Fast Facts (2024 survey). https://www.aha.org/statistics/fast-facts-us-hospitals. 907,216 staffed beds.
- [R4] Yuanlin Christian Hospital energy slides, citing the 2018 非生產性質行業能源查核年報 (regional-hospital average EUI 204.9–210.6 kWh/m²·yr). https://energy.csd.org.tw/base/10001/door//Data/Downloads/83/02%E5%93%A1%E6%9E%97%E5%9F%BA%E7%9D%A3%E6%95%99%E9%86%AB%E9%99%A2.pdf (context only)
- [R5] González González et al., *Energies* 11(9) 2279, 2018. https://www.mdpi.com/1996-1073/11/9/2279. Fraunhofer 2009: "7786 kWh of electricity per bed"
- [R6] ECM, "Powering Telecom and Info Technology Systems". https://www.ecmweb.com/power-quality-magazine-archive/article/20885043/powering-telecom-and-info-technology-systems
- [R7] DCD, "Power to the 5G people". https://www.datacenterdynamics.com/en/analysis/power-5g-people/
- [R8] Uptime Institute Journal, "Global PUEs — are they going anywhere?". https://journal.uptimeinstitute.com/global-pues-are-they-going-anywhere/
- [R9] Xtera, SubOptic 2019, "Electrical power: greener solutions". https://www.xtera.com/wp-content/uploads/2022/12/SubOptic-2019-Electrical-power-greener-solutions.pdf
- [R10] EPRI, *Water & Sustainability (Vol. 4): U.S. Electricity Consumption for Water Supply & Treatment*, 2002, Table 2-1. https://www.circleofblue.org/wp-content/uploads/2010/08/EPRI-Volume-4.pdf
- [R11] ECLAC, FAL Bulletin 350, "Energy consumption and container terminal efficiency", 2016. https://repositorio.cepal.org/bitstreams/087344f9-dfa6-46a3-a48f-e1c0fb19a273/download
- [R12] (authors not checked) "Factors causing peak energy consumption of reefers at container terminals", *J. Shipping & Trade* 2019. https://link.springer.com/article/10.1186/s41072-019-0040-y
- [R13] Sino-German Energy Partnership, *Energy Efficiency in Airports: Technical Guidelines*. https://energypartnership.cn/fileadmin/china/newsroom_docs/Energy_Efficiency_in_Airports.pdf
- [R14] EIA Refinery Capacity Report, Table 10a (2025). https://www.eia.gov/petroleum/refinerycapacity/table10.pdf
- [R15] EIA, refinery gross input (2025: 16,731 kb/d). https://www.eia.gov/dnav/pet/pet_pnp_unc_dcu_nus_a.htm
- [R15b] EIA, product supplied. https://www.eia.gov/dnav/pet/pet_cons_psup_dc_nus_mbblpd_a.htm
- [R16] liquefiednaturalgas.org, Regasification. https://liquefiednaturalgas.org/technology/regasification/
- [R17] 內政部, 建築物給水排水設備設計技術規範 (2022-12-29 version), Appendix Table A-1. https://www.rootlaw.com.tw/Attach/L-Doc/A040040101052700-1111229-1000-001.pdf
- [R18] 建築物污水處理設施 table (F-1: 醫院、療養院、診所, 350 L/person/day, 1.5 persons per bed). http://www.rootlaw.com.tw/Attach/L-Doc/A040040101045700-0990906-1000-003.pdf
- [R19] LBNL, *United States Data Center Energy Usage Report*, LBNL-1005775, 2016. https://eta-publications.lbl.gov/sites/default/files/lbnl-1005775_v2.pdf
- [R20] US DOE, *Refinery Water Study*, 2016. https://www.energy.gov/sites/prod/files/2016/03/f30/US%20DOE%20Refinery%20Water%20Study.pdf
- [R21] Harris & Diehl, USGS SIR 2019-5103, Tables 6–7. https://pubs.usgs.gov/sir/2019/5103/sir20195103.pdf
- [R22] EIA Electric Power Annual, Table 8.1. https://www.eia.gov/electricity/annual/html/epa_08_01.html
- [R23] EIA FAQ 667. https://www.eia.gov/tools/faqs/faq.php?id=667
- [R24] EIA Electric Power Annual, Table 8.2. https://www.eia.gov/electricity/annual/html/epa_08_02.html
- [R25] Generator Source, Diesel fuel consumption chart. https://generatorsource.com/tools-info/fuel-consumption-charts/
- [R26] 台灣電力公司函 電配售部業字第10800032292號 (2019-02-26), attachment 營業規章 Art. 46. https://www.elecpe.org.tw/wp-content/uploads/groupdownload/OfficalDocument/2-36.pdf

---

<!-- file: lane_repair.md -->
# Lane: repair rates, crews and depots

Date: 2026-09-29. Grades follow BRIEF.md: **S** is a standard, code or regulation; **L** is literature or a government report; **J** is judgment. Jurisdiction is marked US, TW or intl.

**Reuse from the dependency-table lanes.** The lane files in `deptable/` and REVIEW.md do not cover repair times, crews or depots. The only overlap is the depot's role as the trucked-fuel supplier (lane_fuel.md, rows under "depot"). That role is a separate use of the word "depot" from the repair depot here; see Question 4. Nothing below repeats their evidence, and none of the claims REVIEW.md §1 found overstated are used.

**Source access.** FEMA's website returned HTTP 403 to every direct download from this session. WebFetch reached the Hazus 6.1 Earthquake Technical Manual but cut it off after the table of contents. That was enough to confirm the table titles in 6.1, but not the values. The values below come from the full text of **Hazus-MH MR4 Earthquake Technical Manual** (FEMA/NIBS), taken from a university mirror (civil.ist.utl.pt, `hazus_mr4_earthquake_tech_manual.pdf`). The 6.1 titles match the MR4 tables one for one, for example Table 8-27 "Restoration Functions for Electric Power System Components (All Normal Distributions)", which is MR4 Table 8.22.a. I have not seen the 6.1 values themselves (see Question 1). I could not open the Hazus Hurricane Technical Manual, so I cannot say whether it has lifeline restoration functions.

---

## 1. Repair and restoration time per node class

### 1.1 The Hazus restoration functions (US, grade L)

Hazus describes restoration by facility class and damage state as a **normal distribution of days to full function**. It says where the functions come from. Most are "best fit to ATC-13 data" (expert opinion, California, 1985). Substations and distribution circuits come from "a G&E report (1994)". Hazus is a FEMA methodology, not a code, so it is grade **L**, not S.

The table gives mean days (σ in brackets), by damage state: slight, moderate, extensive, complete. The generator works in hours, so multiply by 24.

| Node class | Hazus class (MR4 table) | Slight | Moderate | Extensive | Complete | Mapping |
|---|---|---|---|---|---|---|
| generation | Generation facilities (8.22.a) | 0.5 (0.1) | 3.6 (3.6) | 22 (21) | 65 (30) | direct |
| transmission_substation, distribution_substation | Electric substations (8.22.a) | 1.0 (0.5) | 3.0 (1.5) | 7.0 (3.5) | 30 (15) | direct (Hazus splits substations by voltage for fragility only; restoration is shared) |
| *(power line edges)* | Distribution circuits (8.22.a) | 0.3 (0.2) | 1.0 (0.5) | 3.0 (1.5) | 7.0 (3.0) | direct |
| exchange, data_centre, cable_landing | Communication facility (8.30.a) | 0.5 (0.2) | 1 (1.0) | 7 (7.0) | 40 (40) | direct for exchange; J for data_centre and cable_landing |
| mast | Communication facility (8.30.a) | as above | | | | J: Hazus MR4 has no cell-site class |
| reservoir | none | — | — | — | — | J: Hazus has no restoration function for dams |
| treatment | Water treatment plants (8.1.a) | 0.9 (0.3) | 1.9 (1.2) | 32 (31) | 95 (65) | direct |
| pumping | Pumping plants (8.1.a) | 0.9 (0.3) | 3.1 (2.7) | 13.5 (10) | 35 (18) | direct |
| storage | Water storage tanks (8.1.a) | 1.2 (0.4) | 3.1 (2.7) | 93 (85) | 155 (120) | direct |
| seaport | Waterfront structures (7.14.a) | 0.6 (0.2) | 3.5 (3.5) | 22 (22) | 85 (73) | direct |
| | Cranes/cargo handling (7.14.a) | 0.4 (0.35) | 6 (6) | 30 (30) | 75 (55) | direct |
| airport | Tower, terminal, hangars (7.16.a) | 0 (0) | 1.5 (1.5) | 50 (50) | 150 (120) | direct |
| | Runways (7.16.a) | 2.5 (2.5) (slight and moderate combined) | | 35 (35) | 85 (65) | direct |
| freight_yard | Railway facilities (7.10.a) | 0.9 (0.05) | 1.5 (1.5) | 15 (15) | 65 (50) | J: a truck yard is not a rail facility; nearest class |
| bridge | Highway bridges (7.4) | 0.6 (0.6) | 2.5 (2.7) | 75 (42) | 230 (110) | direct |
| refinery | Refineries (8.17.a) | 0.4 (0.1) | 3.0 (2.2) | 14 (12) | 190 (80) | direct |
| tank_farm | Tank farms (8.17.a) | 0.9 (0.5) | 7.0 (7.0) | 28 (26) | 70 (55) | direct |
| import_terminal, depot | Tank farms (8.17.a) | as above | | | | J: nearest class |
| tertiary, regional, clinic, blood_bank | Essential facilities: EFHL, EFHM, EFHS hospitals; EFMC clinics and labs (6.11) | 5 (1) | 20 (2) | 90 (10) | 180 (20) | direct for hospitals and clinics; J for blood_bank (EFMC) |

Hazus defines the damage states by the share of equipment lost. For substations, for example, "ds4 is defined as the failure of 70% of disconnect switches … 70% of circuit breakers, 70% of current transformers … or by failure of 70% of transformers", and "ds5 is defined as the failure of all disconnect switches, all circuit breakers, all transformers, or all current transformers" (MR4 §8.5.6).

**What to take as the centre.** Take the Hazus mean for each class and state, converted to hours. Take σ/mean as the evidence-based **default heterogeneity** for that cell. The ratio runs from 0.06 (rail facilities, slight) to 1.0 (communications, moderate and above), so a single heterogeneity value for all classes would discard what Hazus says.

**Three cautions before these become targets:**
1. **The hazard does not match.** The functions are earthquake damage states built from 1985 expert opinion. The pilot's disruption is a storm. The damage-state logic carries across hazards, but the mix of damage states does not. A storm leaves mostly slight and moderate facility damage, with the heavy damage on lines and poles (§1.2).
2. **They already contain crews.** A Hazus curve is the functionality of a class population over time, under the resources of its time. Using the mean as one node's repair duration and then also limiting crews counts the scarcity twice, to some degree. Hazus treats water pipelines differently. There it models crews explicitly: "a 4-person crew needs 4 hours to fix a leak, while the same 4-person crew needs 8 hours to fix a break", with "# Available Workers" left to the user (MR4 Table 8.1.c). For facilities it gives durations only. §3 builds on the same split.
3. **They are long against a 72-hour window.** A substation's moderate mean is 3.0 days, which is the entire 72-hour window. Every extensive or complete state runs past it. In a 72-hour restorative model, only slight and moderate damage can finish (Question 2).

### 1.2 Empirical restoration

| Event | Figure | Source | Jurisdiction, grade |
|---|---|---|---|
| **Typhoon Soudelor 2015** | Outages peaked at about 4.34–4.39 M customers. Two days after landfall, "已修復近98%用戶、約429萬戶，尚有約9萬用戶未復電" (98% restored, about 4.29 M; about 90,000 still out). About 7,000 mountain households, cut off "因道路崩坍、路基流失中斷" (by road collapse and washed-out roadbed), "今日仍無法進入搶修" (still could not be reached for repair that day). "台電出動4千人" (Taipower deployed 4,000 people). | Anue 鉅亨 news, 10 Aug 2015, citing Taipower (news.cnyes.com/news/id/639047). Commercial Times (ctee.com.tw, 10 Aug 2015): some areas were out "超過40小時" (more than 40 hours). | TW, L (press reporting Taipower figures) |
| **Typhoon Kong-rey 2024** (landfall 31 Oct) | 1 Nov, 10:00: 863,174 households had lost power and 761,468 were restored, "復電近九成" (nearly 90%). 2 Nov, 15:00: of 957,061 affected, 929,280 were restored (over 97%). The rest were "主要集中在花東地區及部分縣市山區" (mainly in Hualien–Taitung and the mountain districts). "花東地區，因用戶位置分散，往往零星戶數就需花上半天進行搶修" (in Hualien–Taitung, customers are so scattered that a handful of households can take half a day to repair). At Lishan, crews already stationed there before the storm made repairs "以步行方式" (on foot) because the road was blocked. | MOEA press releases, news_id 117817 and 117829 | TW, L (government press release) |
| **Typhoon Krathon 2024** (landfall 3 Oct) | Over 320,000 households lost power. A 69 kV line broke at landfall. Where slopes failed and roads collapsed, crews waited: "一旦道路搶通將立即趕赴山區搶修" (they will go up the mountain as soon as the road is cleared). Kaohsiung had "30根斷桿" (30 broken poles) and nearly 140 tripped loops and feeders. | MOEA news_id 116112; CNA 3 Oct 2024 | TW, L |
| **Chi-Chi earthquake 1999** | The quake damaged "全台622座高壓電塔及17處變電所" (622 high-voltage towers and 17 substations island-wide) and cut power to "649萬戶" (6.49 M households). The Chungliao switching station, the north–south hub, was destroyed. Northern critical facilities (government, the airport, transit, hospitals, water) were back "by 5am yesterday morning", about 1 day. Rationing ran until "10月10日始解除全台限電" (island-wide rationing was lifted only on 10 October), about 19 days. The black start took "3次嘗試" (three attempts). | TVBS/CNA, 20th-anniversary piece citing Taipower; Taipei Times, 22 Sep 1999; zh.wikipedia 台灣大停電列表 (for the 10 October date, the weakest of the three sources) | TW, L (the Wikipedia date is corroboration only) |
| **Hurricane Maria 2017** (Puerto Rico) | "it took 192 days to restore service to 95% of PREPA's customers". The mainland regression for the same storm intensity gives 20.5 days. "after 35 days 44 municipalities had no grid connections and after 84 days, 9 municipalities had still absolutely no connection". More than 50,000 poles had to be replaced (about 10% or more), against "a typical 1 to 3 percent". The last customer was restored after 328 days. | Kwasinski et al., "Hurricane Maria Effects on Puerto Rico Electric Power Infrastructure", *IEEE PETS Journal* 2019 (author accepted manuscript on IEEE Xplore); NCDP Columbia case study 2025 (the 328 days); NPR and CNN, Aug 2018 | US territory, L |
| **Hurricane Irma 2017** (FPL) | 4.4 M customers affected. Service was restored to "essentially all … 10 days after the massive storm exited". The workforce peaked at "more than 28,000 … from 30 states and Canada". | FPL newsroom, 22 Sep 2017 | US, L (utility release) |

**How this lines up with Hazus (J).** Taiwan's typhoon restoration of distribution service, 88–98% within 1–2.5 days, matches the Hazus distribution-circuit moderate-to-extensive means (1–3 days). Chi-Chi's 19 days of rationing, after substation and tower damage, falls between the Hazus substation extensive mean (7 days) and complete mean (30 days). Maria is the far tail: about 9 times the mainland expectation. The sources put that down to the island, scarce materials and crews, and governance, not to the damage states alone.

### 1.3 Context factors that change repair time

| Factor | Effect | Evidence | Grade |
|---|---|---|---|
| **Road access** | Areas on an arterial or collector road had 7% fewer outage days (95% CI 1–13%). Moderate landslide areas took 5.5% more days (CI 1–10%), and high landslide areas 11.4% more (CI 2–21%). | Azad & Ghandehari, *IEEE Access* 9 (2021), Maria, quasi-Poisson regression on nighttime lights over 889 barrios | L (US) |
| **Terrain and elevation** | Weak once access is controlled: "a 50 percent increase in elevation increases the outage days by 1.2% (95% CI = 0.34% - 2.0%)". The strong effect is **blocked roads**. Soudelor left about 7,000 households unreachable. At Lishan, crews had to walk in. | Azad & Ghandehari 2021; Anue 2015; MOEA 117829 | L (US, TW) |
| **Distance from the storm track** | 50 km farther from landfall meant 30% fewer outage days (CI 26–33%). This is hazard intensity, not distance to a depot. The world already carries it through the storm field. | Azad & Ghandehari 2021 | L |
| **Rural, dispersed service** | Rural counties had "longer power outages and much slower and uneven restoration times". In Hualien–Taitung, a handful of scattered households can take half a day. | Mitsova et al., *Natural Hazards* 2018 (Irma); MOEA 117829 | L (US, TW) |
| **Distance or travel time to the depot** | No study was found that isolates depot distance as a coefficient. Crew-routing models treat it as explicit travel time, not a multiplier (Bent, Coffrin & Van Hentenryck 2010; Morshedlou et al. 2018). **Recommendation:** add travel time over the road network as its own term (§3), rather than scaling repair duration by distance. | — | J (structure from L) |
| **Outlying island** | The strongest factor, but confounded with other causes. The island "severely affected resource availability that, for example, limited the deployment of mutual assistance restoration crews"; materials "had to be flown or barged". Taipower sends crews in advance: "針對部分易受災的山區及離島地區，台電已超前部署派遣搶修人力與機具進駐" (for disaster-prone mountain areas and outlying islands, Taipower has already sent repair crews and equipment to stay on site). | Kwasinski et al. 2019; EEI testimony, Torres, 11 Apr 2018; MOEA 123257 (pre-typhoon release, 2026) | L (US, TW) |
| **Node class** | Class matters more than any context factor. At complete damage, a distribution circuit takes 7 days and a highway bridge 230, in Hazus means. | Hazus MR4 (§1.1) | L |

**Proposed context model (J).** Repair time = the class and damage-state target (Hazus) + road travel time from the crew's depot or previous job + an **access multiplier** on the target:
- 1.00 with arterial access;
- 1.07 without it (the inverse of Azad's 7%);
- a further 1.06 for moderate landslide exposure and 1.11 for high.

For an outlying island with no resident depot, add a fixed **mobilisation delay** for crossing. I found no source giving a number for this delay, so it needs a decision (Question 5).

---

## 2. Crews and depots

### 2.1 What a utility keeps

| Item | Figure | Source | Grade |
|---|---|---|---|
| Taipower district service offices (區營業處) | "全臺區營業處共分有24處" (24 in total). Penghu, Kinmen and Matsu have their own offices. Small islands run their own power stations (Green Island and Lanyu under Taitung; Qimei, Wang'an and others under Penghu). | zh.wikipedia 台灣電力公司 (accessed 2026-09-29) | TW, L (secondary; Taipower's own pages refused connections from this session) |
| Area per district office | 36,197 km² ÷ 24 ≈ **1,500 km² per office**, or about 0.97 M people per office (population 23.3 M, Dec 2025) | en.wikipedia Taiwan (area, population); derived | TW, J (derived) |
| Crew size (工作班) | Krathon: "16班84人" (16 crews, 84 people), 5.3 per crew. Kong-rey: "63班共430名" (63 crews, 430 people), 6.8 per crew. Hazus uses 4-person pipeline crews. | MOEA 116112, 117829; Hazus MR4 Table 8.1.c | TW, L; US, L |
| Island-wide mobilisation | Before a typhoon: "7,316名人力、3,325輛車輛及6,634台各式機具" (7,316 staff, 3,325 vehicles and 6,634 pieces of equipment) across supply, generation and distribution (MOEA 123257, 2026). Soudelor: 4,000+ staff. Taipower employs 30,535 in total (Apr 2026). | MOEA; Anue; zh.wikipedia | TW, L |
| Local strength in one area | During Krathon, the Kaohsiung and Fengshan district offices together fielded "432名工程人員、88輛工程車" (432 field engineering staff and 88 service trucks) before help arrived from outside. | CNA, 3 Oct 2024 | TW, L |
| US peak surge | FPL, Irma: more than 28,000 workers for 4.4 M affected customers, about 6.4 per 1,000, mostly mutual aid. Puerto Rico, Maria: about 3,000 "industry lineworkers and support personnel" for 1.47 M customers, about 2 per 1,000. | FPL newsroom; Torres EEI testimony 2018 | US, L |

**Normalisation.** I found **no standard or norm** in the US or Taiwan that sets crews per customer, per km², or per asset. Utilities size their standing crews for routine work and surge through mutual aid. The ratios above are observed, not required, so crew counts are grade J with L anchors.

### 2.2 Mutual aid norms

- **US.** Mutual aid is voluntary and runs on request: "crews do not arrive automatically; a formal request for mutual assistance must be made by the affected electricity provider. The recipient of the assistance pays for it, and companies providing the mutual assistance are compensated, at cost" (Torres, EEI, 2018). It is organised through Regional Mutual Assistance Groups and EEI's National Response Event framework, which pools "all available EEI member emergency restoration resources (including contractors)" (Bonenberger, EEI, DOE Electricity Advisory Committee, Feb 2018). Delay costs dearly: "the six weeks delay in requesting mutual aid assistance hampered recovery efforts" (Kwasinski et al., quoting their ref. [21]). Past a point, more crews do not help: "only so many trucks and so many workers can fit into one space at a time. Access to materials, not the size of the workforce, at times has slowed the restoration" (Torres).
- **TW.** Taipower's 跨區支援機制 (cross-district support mechanism) moves crews between district offices. In Krathon, 7 district offices sent 16 crews to Kaohsiung and Pingtung on landfall day. The northern offices were called at noon and on the road that afternoon. In Kong-rey, 15 district offices had sent 63 crews within about two days.
- **For a 72-hour window (J).** In Taiwan, outside crews arrive in about 6–24 hours; in the US, a surge arrives in about 1–3 days; for Maria it took weeks.

### 2.3 Setting crew and depot counts

**Depots (J, anchored to TW).** One depot for each district-office-sized area, about 1,500 km².
- **A 400 km² island of about 3 towns** gets **1 depot**, sited in the largest town. That follows Taipower practice: Penghu, Kinmen and Matsu each have their own office even though they are much smaller than 1,500 km². Add a second depot only if the mountain spine cuts road access between towns (Question 6).
- **A Taiwan-scale world** gets about 24 depots, sited by urban extent. Each outlying island group with its own grid gets a resident depot.

**Crews (J).** The evidence supports two different kinds of crew, and the model should say which one it means.
- **Line crews** (distribution, 5–7 people). Taipower mobilises about 7,300 staff island-wide, or about 1,200 crews at about 6 each. That is about 50 crews per district office, or about 1 per 30 km². Pro rata, a 400 km² island would have about 13 line crews. This is derived and includes contractors and non-field staff, so it is a ceiling.
- **Facility repair crews** (substation, plant, pumping and treatment equipment). These are specialised and far scarcer. I found no count for them in the US or in Taiwan.

**Is 2 crews defensible for the pilot?** **Yes, as a declared scarcity setting. No, as a calibrated count.**
- *For it:* The restorative model sequences repair of failed **nodes**, which is facility-class work. A small island's specialised facility crews could plausibly number one or two. Two crews over 5–8 failed nodes also keeps brute-force enumeration of orders tractable, and makes sequencing matter.
- *Against it:* Line crews on a 400 km² island would number about 10 or more. Real crews also belong to separate owners: Taipower, the water utility, the telecom carrier and CPC each repair their own layer. One pool of 2 shared across six layers is a modelling simplification, not something observed.

**Recommendation.** Keep 2 for the pilot and label it `placeholder (open decision: crew count)`. Report a sensitivity run at 1, 2 and 3 crews. For the full build, consider one crew pool per layer owner (Question 3).

---

## 3. How to represent repair in the exact-tier optimisation

**Recommendation.** Represent a **node** repair as a **fixed processing time** drawn per element: the class and damage-state target (§1.1), scaled by the access multiplier (§1.3). Add **sequence-dependent travel time** over the road network from the crew's depot or previous job. Crews are identical parallel machines. The node returns to service when its job completes. Represent a damaged **edge** (a line or a pipe) as **work content consumed at a rate**: crew-hours per km, or per break. The model must not become a smooth rate for nodes.

**Why:**
1. **This is the structure the exact-tier literature uses.**
   - Cavdaroglu et al. (2013), *Annals of OR* 203: "determine the set of components (or tasks) that will be temporarily installed or repaired, assign these tasks to work groups, and then determine the schedule of each work group".
   - Nurre et al. (2012), *EJOR* 223: "work groups must be allocated to build nodes and arcs into a network in order to maximize the cumulative weighted flow in the network over a horizon". This is a time-indexed integer program with processing times.
   - Bent, Coffrin & Van Hentenryck (2010): the power restoration vehicle routing problem "combine[s] vehicle routing and power restoration scheduling problems", which is where the travel term comes from.
   - Morshedlou, González & Barker (2018), *Transportation Research Part B* 118: crews "dispatched from depots to a road network", with arrival times as variables. Their "restoration rate" rises with the number of crews assigned, and that model is the rate alternative.
2. **Hazus uses the same split.** Facilities get durations by damage state. Pipelines get a crew-limited rate ("Days needed to finish all repairs = (1/available work) * [...]", MR4 §8.1.7).
3. **It fits the pilot's brute force.** With fixed durations and travel, each repair order gives one deterministic finish time per node. Unserved demand-hours are then exact, and the MIP can be checked against enumeration. With a rate model, splitting crews across jobs makes the solution space continuous, so brute force over orders no longer covers it.
4. **It keeps the transport coupling.** Travel over the road network means a damaged bridge delays repairs. The Soudelor, Kong-rey and Krathon releases all name blocked roads as a cause of delay.

**Implementation notes, subject to repository rules §4:**
- **Normal draws are not allowed.** Hazus gives normal distributions, but a normal draw needs log and cos, which CLAUDE.md forbids. Instead, draw uniformly on [μ − √3σ, μ + √3σ]. That matches the mean and standard deviation using only sqrt. Where μ − √3σ < 0 (many cells, since σ ≈ μ), a floor is needed, and the floor moves the mean. This should be a recorded `CHOICE:` (Question 1).
- **Work in whole hours.** Round durations to whole hours to fit an hourly, time-indexed 72-hour horizon.
- **Mutual aid.** If it is modelled, add it as a crew count that steps up at a set hour. It should not be a rate.

---

## Questions for the design side

1. **The Hazus version, and draws with σ ≈ μ.** Can the values be confirmed against the 6.1 manual? FEMA blocked this session, and only the MR4 values were seen. And should the uniform-equivalent draw be floored at 1 hour, or at a fraction of μ, where σ is close to μ?
2. **Damage states against the 72-hour window.** Every extensive and complete Hazus mean exceeds 72 hours. Should the storm generate only slight and moderate facility damage in the pilot? Or should the window be longer? Or should heavily damaged nodes stay failed for the whole window?
3. **One crew pool or one per owner.** Should the full build keep one shared crew pool, or give each layer owner its own?
4. **Two meanings of "depot".** The fuel layer's `depot` node class (trucked diesel) and the repair depot where crews are based are different things. Should the repair depot get its own name, such as `crew_base`, so the manifest does not conflate them?
5. **The mobilisation delay for an outlying island.** I found no figure for it. Should it be a placeholder?
6. **A second depot when the spine blocks roads.** Should a mountain spine that breaks road connectivity trigger a second depot on the pilot island?
7. **Reservoir repair.** Hazus has no class for it. Should a damaged dam be treated as not repairable within the window (J)?

## Searched for and not found
- Any US or Taiwan standard that sets crew counts per customer, per km² or per asset.
- A Taipower count of crews per district office, or of service stations (服務所). Taipower's own sites refused connections from this session.
- Restoration statistics published by Taipower as a series. Only press releases were found.
- The Hazus Hurricane manual's content on lifelines (FEMA returned 403).
- Counts of specialised facility repair crews.
- A coefficient that isolates distance to the depot.

## Sources (all fetched this session unless marked)
- FEMA/NIBS, *Hazus-MH MR4 Earthquake Model Technical Manual*, Tables 6.11, 7.4, 7.10.a, 7.14.a, 7.16.a, 8.1.a, 8.1.c, 8.17.a, 8.22.a, 8.30.a; mirror http://www.civil.ist.utl.pt/~mlopes/conteudos/DamageStates/hazus_mr4_earthquake_tech_manual.pdf (local copy `targets/repair/hazus_mr4.pdf`).
- FEMA, *Hazus Earthquake Model Technical Manual, Hazus 6.1*, July 2024: https://www.fema.gov/sites/default/files/documents/fema_hazus-earthquake-model-technical-manual-6-1.pdf (table titles only, via WebFetch).
- Kwasinski, Andrade, Castro-Sitiriche, O'Neill-Carrillo, "Hurricane Maria Effects on Puerto Rico Electric Power Infrastructure", *IEEE PETS Journal*, 2019: https://ieeexplore.ieee.org/ielaam/6687318/8673665/8644031-aam.pdf
- Azad & Ghandehari, "A Study on the Association of Socioeconomic and Physical Cofactors Contributing to Power Restoration After Hurricane Maria", *IEEE Access* 9, 2021: https://par.nsf.gov/servlets/purl/10293624
- Mitsova et al., "Socioeconomic vulnerability and electric power restoration timelines in Florida: the case of Hurricane Irma", *Natural Hazards*, 2018: https://par.nsf.gov/servlets/purl/10066853
- Hosein, *Powerless: Puerto Rico's Grid Collapse…*, NCDP Columbia, 2025: https://ncdp.columbia.edu/wp-content/uploads/2025/08/Puerto_Rico_Grid_Collapse_Case_Study.pdf
- Torres (EEI), testimony to the House Energy and Commerce Committee, 11 Apr 2018: https://democrats-energycommerce.house.gov/sites/evo-subsites/democrats-energycommerce.house.gov/files/documents/Testimony-Torres-OI-Hrg-on-Update-on-the-Restoration-of-Puerto-Rico%E2%80%99s-Electric-Infrastructure-2018-04-11.pdf
- Bonenberger (EEI), "Mutual Assistance Agreements", DOE Electricity Advisory Committee, Feb 2018: https://www.energy.gov/sites/prod/files/2018/02/f49/1_Mutual%20Assistance%20Agreements%20-%20David%20Bonenberger%2C%20EEI.pdf
- FPL newsroom, 11 and 22 Sep 2017 (Irma): https://newsroom.fpl.com/2017-09-22-FPL-completes-service-restoration-to-more-than-4-4-million-customers-impacted-by-historic-Hurricane-Irma
- NPR, 15 Aug 2018: https://www.npr.org/2018/08/15/638739819/nearly-a-year-after-maria-puerto-rico-officials-claim-power-totally-restored ; CNN, 7 Aug 2018: https://www.cnn.com/2018/08/07/us/puerto-rico-maria-power-restored-wxc-trnd/
- MOEA press releases (Taipower): Krathon news_id=116112; Kong-rey 117817, 117829; Bavi pre-typhoon 123257: https://www.moea.gov.tw/MNS/populace/news/News.aspx?kind=1&menu_id=40&news_id=<id>
- CNA, 3 Oct 2024: https://www.cna.com.tw/news/aloc/202410030342.aspx
- Anue 鉅亨, 10 Aug 2015: https://news.cnyes.com/news/id/639047 ; Commercial Times: https://www.ctee.com.tw/news/20150810700058-439901
- 台電月刊 633, "復電是需要時間的": https://tpcjournal.taipower.com.tw/article/717 (WebFetch summary only; it gives 450 萬戶 for Soudelor and says field staff need "至少要3至5年訓練" (at least 3 to 5 years of training))
- TVBS/CNA, 921 twentieth anniversary: https://news.tvbs.com.tw/life/1203756 ; Taipei Times, 22 Sep 1999: https://www.taipeitimes.com/News/quake/archives/1999/09/22/3506 ; zh.wikipedia 台灣大停電列表 and 台灣電力公司; en.wikipedia Taiwan
- Charlwood, Little & Lou, ICLR Research Paper no. 6 (Chi-Chi substations and dams), 2000: https://www.iclr.org/wp-content/uploads/PDFS/chi-chi-taiwan-earthquake.pdf (via WebFetch: "the lack of redundancy in the major transmission grid made much of Taiwan vulnerable")
- Cavdaroglu, Hammel, Mitchell, Sharkey & Wallace, *Annals of OR* 203:279–294, 2013: https://link.springer.com/article/10.1007/s10479-011-0959-3 (abstract via WebFetch)
- Nurre et al., *EJOR* 223(3):794–806, 2012: https://ideas.repec.org/a/eee/ejores/v223y2012i3p794-806.html
- Morshedlou, González & Barker, *Transportation Research Part B* 118:66–89, 2018: https://www.sciencedirect.com/science/article/abs/pii/S0191261518303539 (abstract via WebFetch)
- Bent, Coffrin & Van Hentenryck, "Vehicle routing for the last mile of power system restoration", 2010: https://www.osti.gov/biblio/1041202

---

<!-- file: lane_mode_strength_gap.md -->
# Lane: failure mode, coupling strength, compliance gap, and distributions

Lane date: 2026-09-29. Scope: the four items set by the caller, under targets/BRIEF.md.

Grades: **S** is a standard, code or regulation. **L** is literature or a government report. **J** is judgment. Jurisdiction is marked [US], [TW] or [Intl].

Reuse from deptable/: I cite the lane files only where the review (deptable/REVIEW.md §1) confirmed the source. Where the review found a source overstated, I say so, and I do not rest a target on it. Lane sources that are still overstated and are not used here:
- FCC 07-177 as a standard;
- "NFPA 110 Class 96";
- COM-001-3 alternative path;
- Kramek;
- Larsen / ASPR 62% as telecom evidence.

How I fetched sources: every source listed in §6 was fetched this session. Most came through WebFetch. Four came through curl or E-utilities, because WebFetch was blocked or returned a captcha: PubMed abstracts; the Argonne and NERC PDFs; and the Ten States text, read from the local copy deptable/rsww.txt. Their rows in §6 say so.

---

## 0. Two framing points that affect every item

**0a. Failure mode is not the transfer function g_δ, and the design side should say which one the generator draws.** The dissertation already has a per-type shape on the edge:
- r_e = κ·g_δ(s_u), where g_δ is the edge transfer function (Foundations v3.11 §3.3; Ch4 v4.1 eq. 4.6);
- the canon tendencies for g_δ are: physical flow linear or concave, logistic threshold, control step, service gradual.

Throttle or trip (Structure §4.4; Pilot Spec) is a different question: how the consumer's state responds when its received supply ratio R_φ(v) falls below 1. This lane treats the failure mode as that consumer-side response:
- **throttle:** s_v^cascade = R_φ;
- **trip:** s_v^cascade = 0 whenever R_φ < 1 (or below a dropout threshold θ).

If the mode is instead meant to pick the g_δ family, then the Foundations defaults already answer item 1, and the mode would double-count them. See Q1.

**0b. The κ cap and the spec wording disagree.** Structure §4.4 says a consumer on a direct line "may have three times its need". The dissertation caps κ(e) to [0,1]: Symbol Register "κ(e) ∈ [0,1]", and Appendix A v1.7 gives "two feeds … κ = 1.0 on each". Under the cap, a threefold headroom on one feed is lost: it reads 1.0. It also changes behaviour under partial source damage. With a source at state 0.4:
- the capped form r = min(1,3)·0.4 gives 0.4;
- a capacity-true form r = min(1, 3·0.4) gives 1.

§2 recommends keeping the dissertation's form, and recording the uncapped ratio as a diagnostic. See Q4.

---

## 1. Failure mode (throttle or trip)

### 1.1 Canon default per dependency type (consumer response)

| Type | Default | Why | Evidence | Grade |
|---|---|---|---|---|
| physical_flow | **trip** | Most single facilities are driven by motors, electronics and burners with protective dropout. Below a voltage or pressure floor, equipment disconnects rather than running at a fraction. | NERC LMWG *Dynamic Load Modeling* TRD (draft 2025): "contactors have proved to drop out at voltage levels around 45-55% nominal voltage in about 1-3 cycles"; "75% of motor A will trip at 50% voltage in 20 ms". The foundational network-flow restoration model (Lee, Mitchell & Wallace 2007) uses binary input dependence: the child arc's capacity is set to 0 "if the parent's demand was not fully met" (as described by Kaul & Rumpf 2021/22). | L [US] |
| logistic | **throttle** | Logistic supply lands in stock. A reduced delivery rate lets the consumer ration and run reduced; it does not stop at the first missed load. | Uri: fuel problems produced "outages, derates or failures to start" (FERC–NERC 2021). Derates are throttle. GAO-21-297: fuel "in short supply" during Maria, with service kept up by refuelling. No source measures rationing behaviour directly. | J (L context) [US] |
| control | **throttle** | Losing the signal pushes the consumer to manual or last-setpoint operation at reduced capability; it does not stop. | NERC RSTC EMS reference (review: quotes confirmed), mitigation "Manning substations during EMS events". 49 CFR 195.446 requires "adequate means for manual operation of the pipeline" (confirmed). Telecom lane, generation: "keeps running but cannot be dispatched automatically". | L [US] |
| service | **throttle** | Manual or paper fallback over days (the dissertation's own definition; ruling R6 types telecom → healthcare as service). | Foundations Def 2.4: service is "Highest — substitution possible", "Days to weeks". No quantitative source. | J |

Physical flow is the only type where trip is the default. This fits the Foundations "linear" tendency for g_δ: the edge delivers in proportion, and the facility then cannot run on the fraction. Q1 asks the design side to confirm this reading.

### 1.2 Class-level departures (throttle or trip against the type default)

| Class (type) | Mode | Evidence | Grade |
|---|---|---|---|
| distribution_substation, transmission_substation (power in, PF) | **throttle** | A shortfall is met by shedding feeders, which is a proportional aggregate. The NERC LMWG load model itself represents the loss as fractions of load tripping. | J (L mechanism) |
| treatment (power, PF) | **throttle** | Ten States §2.6 [S]: "Dedicated standby power shall be provided so that water may be treated and/or pumped … to meet the average day demand", against a plant sized to "the design maximum day demand". The design itself anticipates reduced-flow operation. | S [US] |
| pumping (power, PF) | **throttle** if the station has more than one pump; **trip** if it has one | Each motor trips (NERC), but a multi-pump station stages down. Ten States §6.3.5 asks independent substations to run the station "at its rated capacity", which assumes whole-station operation. | J (L mechanism) |
| tertiary, regional (power, PF) | **throttle** (to the essential electrical system) | NFPA 99 via CSE (Davoudi 2015): the life-safety and critical branches are restored "within 10 sec"; equipment branch "at appropriate time-lag intervals"; loads not on these branches are not served. [TW] 王榮坤 2022: "非必要性負載" (air conditioning, lifts) are curtailed, and generator capacity must exceed "維生負載及必要性負載的總和". The shape is really a step to an essential fraction (Q2). | S via secondary [US]; L [TW] |
| blood_bank, clinic (power, PF) | trip (the default) | Refrigeration is either held in band or lost; WHO 2005 §4.7.2 puts it on standby because of that (confirmed in the review). | L [Intl] |
| mast, exchange, cable_landing, data_centre (power, PF) | trip (the default); the battery or generator is the reserve | GAO-21-297: remote sites "typically have a battery backup for only a few hours". [TW] CNA 2024-04-03: 172 base stations out after the Hualien quake, main cause "電力傳輸中斷". | L [US][TW] |
| generation, gas-fired (fuel, PF by pipeline) | trip per unit, **throttle** per multi-unit plant | Turbine makers "specify a minimum fuel gas pressure at their battery limit" (Cheresources guideline; the page does not state a trip setpoint). Uri: fuel supply issues gave outages *and* derates, and 87% of fuel-caused events were natural gas (FERC–NERC). I found no source that splits trips from derates. | L (mixed) [US] |
| import_terminal, LNG (power, PF) | trip (the default) | "small emergency generators to enable orderly shutdown in the event of a power supply failure" (power lane S-LNG; technical paper, not peer-reviewed). | L-weak [Intl] |
| refinery, seaport, freight_yard, airport (power, PF) | **throttle** | Run cuts, partial crane operation, and airfield lighting on Configuration A generators (review F8). No source measures partial operation at the class level. | J |
| airport, towered (telecom, control) | **trip** | Telecom lane S6, DOT OIG AV2017020: loss of FTI circuits led to ground stops, and re-routing took "several days". The review did not re-check this source. | L [US] |
| generation (telecom, control) | throttle (the default) | "Keeps running but cannot be dispatched automatically" (telecom lane S2; the review confirmed the EMS quotes). | L [US] |
| Fuel edges with role `buffer_resupply` (ruling R2) | not applicable: they extend runtime only | By R2 they never fail the consumer, so a mode draw on them has no effect. The generator should skip them. | — |

### 1.3 Heterogeneity default (the share departing from the canon)

- **Recommend 10%, with a sensitivity range of 0–25%. Grade J.**
- What I looked for: any measured share of facilities within a class that behave against the class norm on a supply shortfall. I found none.
- The nearest analogue is the NERC LMWG load-model fractions. Within one motor class, 75% trip at 50% voltage, so 25% do not. For Motor B the figures are "30% … at 55%" and "an additional 30% … at 50%".
- Those are device mixes inside a load, not facility-level departures. They bound the lever from above (about 25%). A facility aggregates many devices, which makes the node-level mode more uniform than the device-level mode.
- The draw should apply to the class canon (§1.2), not the type canon. See Q3.

---

## 2. Coupling strength κ

### 2.1 How interdependency models compute it

| Model | Form | Grade |
|---|---|---|
| Lee, Mitchell & Wallace 2007, *IEEE SMC-C* 37:1303 | Binary input dependence: x_kl ≤ u_kl · y, where y = 0 unless the parent's demand is "fully met". The original is paywalled; the form is quoted from Kaul & Rumpf. | L |
| Kaul & Rumpf, "A linear input dependence model for interdependent networks" (arXiv 2102.05248; *EJOR* 302(2), 2022) | x_kl ≤ α·x_ij + β. In the LP-relaxation case, **α = u_kl / u_ij**: child capacity per unit of parent flow. This is a capacity ratio, and it "permits partial functionality from partial delivery". | L |
| Holden, Val, Burkhard & Nodwell 2013, *Safety Science* 53:51 | A linear conversion coefficient α relates a node's consumption of commodity n to its production of k (for example, electricity per unit of water treated). This is the requirement side of κ. | L |
| Sharma & Gardoni 2022, *RESS* 217:108042 | "Interface functions work as correction factors …"; "typical mathematical forms … are logic gates or logistic regression type expressions". Logic gates correspond to trip. | L |
| Ouyang 2014, *RESS* 121:43 | A review that groups models into six families: empirical, agent-based, system dynamics, economic theory, network-based and other. Flow-based network models are the family that carries capacities. Only the abstract was read. | L |

None of these caps a per-edge capacity ratio in exactly the dissertation's way. The dissertation's κ = min(1, capacity ÷ requirement) is closest to Kaul & Rumpf's α, normalised by the child's need.

### 2.2 Recommended formula (+, −, ×, ÷, sqrt, min only)

For edge e = (u → v), commodity φ:

```
share_uv    = req_v / Σ_{w ∈ consumers_φ(u)} req_w          # pro-rata allocation (CHOICE)
alloc_uv    = cap_u × share_uv
line_uv     = line capacity (below; = +∞ where the commodity has no line term)
headroom_e  = min(alloc_uv, line_uv) / req_v                # uncapped; manifest diagnostic
κ(e)        = min(1, headroom_e)
```

- **Pro-rata allocation** reads cap_u ÷ Σreq, which is the supplier's own margin (1.3 under ruling 0007 for power). It is the same for every consumer of u. Differences between consumers therefore come from the line term, as Structure §4.4 intends.
- The only root is Euclidean distance: `L = sqrt(dx² + dy²) × circuity`.

**Line capacity for power, with no explicit feeders.** Use the load–distance limit of a radial feeder, taking the smaller of the voltage-drop limit and the thermal limit:

```
S_vd(L)  = D_pct / (K_drop × L)        # kVA deliverable at the end of a feeder of length L
line_uv  = min(S_thermal, S_vd(L_uv))
```

The terms:
- **K_drop** is the "voltage drop … for serving 1 kVA load … located 1 mile away" (Kersting, via Kekatos lecture 3). The example value is 3.53×10⁻⁴ %/kVA-mile for a 12.47 kV line at power factor 0.9. Grade L [US].
- **D_pct** is the primary-feeder share of the voltage budget. RUS Bulletin 1724D-113 (2012) gives a "Maximum Volts Drop 8" on a 120 V base (6.67%) for the primary, inside ANSI C84.1 Range A of 114–126 V. Grade S via USDA guidance [US].
- **S_thermal** is the feeder's thermal rating. "Typical feeder ratings near 12 MVA for 13.8 kV and roughly 30 MVA for 34.5 kV" (EEPower 2026, a trade article). Grade L-weak [US]. For Taiwan, the distribution voltages are 11.4 and 22.8 kV (telecom lane S13, DDCC). I found no Taipower feeder rating, so the TW value is J.
- **Worked example.** At 12.47 kV with the 6.67% budget, a 5 MW (≈5.6 MVA) consumer 10 miles out gets S_vd ≈ 6.67 / (3.53e-4 × 10) ≈ 1.9 MVA. That gives κ ≈ 0.34, the "barely enough" end. A consumer 1 mile out is thermal-limited, with headroom ≈ 2 or more, so κ = 1.
- **Customers taking transmission-level supply** (large treatment plants, LNG terminals, by the power lane) have no feeder term: line_uv = +∞.
- **Circuity** is a placeholder (open decision: line_circuity). I found no source.

**Other commodities.**
- *Communications:* bandwidth is not the binding quantity. κ = 1, times the public share for ruling R1 edges (see Q5).
- *Transport access:* under R3 (`any_reachable`), κ = 1 per reachable origin.
- *Fuel `buffer_resupply`:* κ scales the refill rate of the reserve, not the supply margin.
- *Water:* same form, with cap_u from storage or pumping throughput. The main's line term is J, because no mains are explicit.

---

## 3. Compliance gap evidence (measured shortfalls from design targets)

| Quantity (target) | Measured | Implied gap | Grade |
|---|---|---|---|
| Hospital backup power **delivered** over a long outage | Marqusee & Jenket 2020, *Applied Energy* 268, from large non-public (DoD) data: poorly maintained EDGs are "50% likely to fail within 48 h"; a well-maintained single EDG is "only 80% likely" to carry a two-week outage. | Assuming a constant hazard (my derivation), expected runtime inside a 96 h target is ≈92.9 h when well maintained (**≈3%** short) and ≈51.9 h when poorly maintained (**≈46%** short). | L [US] (derivation J) |
| Hospital emergency power testing (EC.02.05.07) | Joint Commission *EC News* July 2021, Fig. 1: **56.25%** of critical access hospitals surveyed in 2020 were noncompliant; EC.02.05.01 was 68.75%. For all hospitals in 2018, EC.02.05.01 was 78.7% (PSQH). | Citation rates mostly reflect testing and documentation, not a size shortfall. The source does not give the sample size. | L [US] |
| Hospital fuel endurance (96 h is accreditation practice, not an NFPA rule; see the review, Check 2) | Tulane University Hospital ran on generators "for up to 36 hours before running out of fuel" (Taylor 2007, Katrina). Multiple generator failures in NYC in 2003 (Beatty et al. 2006, abstract). Sandy: Bellevue's fuel feed failed (fuel lane S5, event evidence only). | One hospital: ≈62% short of 96 h. No denominator. | L (case) [US] |
| Hospital day tank (TW) | 王榮坤 2022: "每日使用的油箱容量必須能使機組連續運轉12小時以上". | This is a target, not a measurement. No TW compliance data was found. | L [TW] |
| Cell-site battery hours (target 8 h: FCC 07-177 proposal, never in force; 72 h CPUC in Tier 2/3 fire districts) | Typical "two to four hours" (Inside Towers 2020, trade). CSRIC IV WG9: "generally sized for two to eight hours" (fuel lane S7). GAO-21-297: "several hours to one day". Verizon reported "eight hours or more" at all sites (Light Reading 2012). | Against 8 h: **50–75%** short (typical), about 37% (CSRIC midpoint), **≤0** for one carrier (negative gap). Against 72 h: over 90%. | L [US] |
| Cell-site generator presence | "In California, 77% of cell sites don't have backup generators" (Public Knowledge 2020, citing a CPUC document I could not retrieve). Marin County: "57 percent of cell sites … were out of service" in October 2019 (CPUC D.20-07-011, p. 7). | This is a presence share. It belongs in `has_fixed_generator` or `standby_fuel = none`, not in the continuous gap. | L (secondary) [US] |
| Central office fuel (24 h) | CPUC 2008 AB 2393 report: industry best practice is "24 hours fuel storage at the central office facilities", "4 hours (minimum) … at remote terminals". No measured shortfall found. | 0 (J) | L target [US] |
| Water standby power (average day demand; Ten States §2.6) | Texas, Uri: 2,080 community systems issued boil-water advisories. Among large providers, "85% lost power"; "many had backup generators" but "not all were operable due to low fuel supplies or cold temperatures" (Tomko et al. 2023, *PLOS Water*, citing a survey). Texas SB 3 "does not mandate emergency backup power" (Texas Lyceum). | No share. The presence gap is real but unmeasured. | L (qualitative) [US] |
| Data-centre fuel (Uptime 12 h minimum) | Nothing measured found. | 0 (J). Operators probably exceed it (a negative gap), but I have no source. | J |

**Negative gaps (exceeding the target):**
- Verizon's ≥8 h battery at all sites against the 8 h proposal, and against the typical 2–4 h.
- NTUH-style multiple 1,500 kW sets with ≥12 h day tanks, where the local rule is unknown.
- No quantitative negative-gap evidence for water or hospitals.

**Recommended defaults (centre; range):**

| Quantity | Centre | Range | Grade | Why |
|---|---|---|---|---|
| Cell-site battery reserve against 8 h | **50%** | 0–75% | L | 2–4 h typical |
| Hospital backup delivered reserve | **15%** | 3–46% | J, bracketed by L | Maintenance citation rates over 50% push the centre off the well-maintained end |
| Exchange, data-centre fuel | **0%** | −25% to 25% | J | Nothing measured |
| Water standby | **20%** | 0–50% | J | Uri shows inoperable units, but there is no share |

**Presence gaps** should be drawn through the R9 attributes, not through the continuous gap:
- mast without a generator: 77% (CA);
- clinic and pumping: J.

---

## 4. Distributions under the arithmetic rule

Checked numerically in targets/distcheck.py (standard-library Python; offline verification only).

| Candidate | Positive and right-skewed? | Can spread = h × target hold for all h? | Verdict |
|---|---|---|---|
| Triangular by inverse CDF | Yes, with the mode near the minimum | **No.** With min ≥ 0, the largest CV is 0.707 (min = mode = 0). It is 0.54 with the mode at 0.2 of the range. The lever cannot reach h > 71%. | Simple (sqrt only) but caps the lever |
| Sum of n uniforms (Irwin–Hall) | No: symmetric | CV on [0, 2m] = 1/√(3n): 0.58, 0.41, 0.33 … | Rejected |
| **Quantile table, linearly interpolated** | Yes (any shape) | **Yes, exactly** (below) | **Recommended** |

Triangular inverse CDF, for reference: x = a + sqrt(u(b−a)(c−a)) when u < (c−a)/(b−a), else b − sqrt((1−u)(b−a)(b−c)).

**The recommended method:**
1. **Offline**, build a lognormal-shaped quantile table for each point of a CV grid (for example 0, 0.05, …, 2.0). Use fixed u-knots (0, .001, .005, .01, .025, .05, .1 … .9, .95, .975, .99, .995, .999, 1), with the ends clipped at the 10⁻⁴ quantiles.
   - Choose σ by bisection so that the **piecewise-linear table itself** has the grid CV exactly. Then scale it to mean 1.
   - Store the knots as decimal constants with provenance. The log and exp are used only offline, so the §4 rule holds at build time.
   - Why lognormal: "the lognormal distribution is the most commonly used for equipment/system maintainability analysis" (Reliability Analytics, citing MIL-HDBK-338).
2. **Moments are exact in closed form.** With X piecewise linear in u:
   - mean = Σ Δu(q_i + q_{i+1})/2;
   - E[X²] = Σ Δu(q_i² + q_i q_{i+1} + q_{i+1}²)/3.

   Checked: at CV 0.1, 0.3, 0.5, 1.0 and 1.5, the mean is 1.000000 and the SD equals the CV to 6 decimal places.
3. **Runtime.** For target T, gap g and heterogeneity h, the required CV relative to the mean is c = h ÷ (1 − g). Take the grid tables A and B that bracket c.
   - Plain linear weighting of the quantiles is off by about 1%: at a true 0.70 it gives 0.694.
   - Instead solve the quadratic (V_A + V_B − 2C)w² + 2(C − V_A)w + (V_A − c²) = 0 for w. Here C is the exact piecewise-linear cross-moment Σ Δu(2a_i b_i + a_i b_{i+1} + a_{i+1} b_i + 2a_{i+1} b_{i+1})/6 − 1. This uses one sqrt. Checked: SD = 0.700000.
   - Then x = T(1 − g)·Q_w(u), with Q_w = (1 − w)A + wB and u from `random()` on the element's own stream.
   - The result is positive (a convex mix of positive tables), mean exactly T(1 − g), SD exactly h·T. At h = 0 the draw collapses to T(1 − g).
4. Every operation is +, −, ×, ÷ and sqrt, all of which IEEE 754 rounds correctly. That meets the cross-platform rule.

Two questions on this method: which spread statistic "spread" means (Q6), and the g = 100 corner (Q7).

---

## 5. Questions for the design side

1. **What is the failure mode?** Is it the consumer's response to R_φ < 1, as this lane assumes, or does it select the g_δ family? The Pilot Spec puts the mode on the edge; Structure §4.4 ties it to "equipment class". Is it drawn per edge, or per (node, commodity)?
2. **Hospitals.** Should the throttle for hospitals be a step to an essential fraction (the NFPA 99 branches; the TW 維生 and 必要性 loads) rather than s = R? That would need a third mode, or a floor parameter. If it is added, what should the essential fraction be? I found no source for its size.
3. **Where the canon sits, and the draw.** Should the canon mode be set per type × class (§1.2) rather than per type? Structure §4.4 says "their dependency type's canon default". If the canon stays per type, systematic class departures such as treatment and substations would have to come from the random 10%.
4. **κ cap.** Should the "three times its need" wording in §4.4 be read as the uncapped headroom? Proposed: keep κ = min(1, ·) per the dissertation, and record the uncapped headroom in the manifest. Or should r_e use min(1, headroom·g_δ(s_u)), which departs from Def. 3.3?
5. **Telecom κ.** For edges under R1 (public telecom share), does κ equal the public share? Where does the private remainder go in the supply margin: as a constant floor, or as an unmodelled edge?
6. **Spread statistic.** Heterogeneity means "spread … as a percentage of the target". Is the spread the standard deviation (this lane's assumption), or a range or interquantile measure?
7. **g = 100.** At a compliance gap of 100 the mean is 0, so a positive quantity must have zero spread. The recipe range is −50 to 100. Should g be capped below 100, or should the draw be forced to 0 there?
8. **Generator reliability.** Should backup-generator reliability (Marqusee & Jenket) be carried in the compliance gap on the reserve, as done in §3, or as a separate availability draw? It is a performance failure, not a size shortfall.

---

## 6. Sources (all fetched this session)

- NERC LMWG, *Dynamic Load Modeling Technical Reference Document* (draft, approved redline 2025-08-19). https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/0-rstc-agenda-links/20251210_1_14_DRAFT_Dynamic-Load-Modeling-Technical-Reference_2025_8_19_LMWG_Approved-Redline.pdf
- WECC, *Composite Load Model Specification* (2024): parameter names only, no defaults. https://www.wecc.org/sites/default/files/documents/meeting/2024/WECC%20Comp%20Load%20Model%20Specification_final.pdf
- FERC news release on the final February 2021 freeze report: the 44.2% and 31.4% figures; 87% of fuel issues were natural gas. https://www.ferc.gov/news-events/news/final-report-february-2021-freeze-underscores-winterization-recommendations
- FERC–NERC phase 2 presentation (curl): "outages, derates or failures to start". https://www.nerc.com/globalassets/standards/projects/2021-07/ferc-presentation-phase-2.pdf
- FERC preliminary findings presentation, 23 Sep 2021: 1,121 of 1,293. https://www.ferc.gov/sites/default/files/2021-09/February%202021%20Cold%20Weather%20Grid%20Operations_Preliminary%20Findings%20and%20Recommendations-09-23-21_Full%20Presentation.pdf
- Cheresources, "Guidelines for fuel gas supply to gas turbines". https://www.cheresources.com/invision/blog/4/entry-366-guidelines-for-fuel-gas-supply-to-gas-turbines/
- Davoudi, V., "Emergency and standby power in hospitals", *CSE*, 15 Oct 2015 (NFPA 99 secondary). https://www.csemag.com/emergency-and-standby-power-in-hospitals/
- 王榮坤, 〈停電時醫院該怎麼辦？〉, 科學月刊 630, Jun 2022. https://www.scimonth.com.tw/archives/5737
- Ten States Standards, *Recommended Standards for Water Works* 2022, §§2.6, 6.3.4, 6.3.5 (local copy deptable/rsww.txt; source PDF at files.dep.state.pa.us).
- GAO-21-297 (2021). https://www.gao.gov/assets/720/714079.pdf
- CNA, 強震影響三大電信172個基地台, 3 Apr 2024. https://www.cna.com.tw/news/ahel/202404030090.aspx
- Kaul, H. & Rumpf, A., "A linear input dependence model for interdependent networks", arXiv:2102.05248 (*EJOR* 302(2), 2022). https://arxiv.org/pdf/2102.05248
- Lee, E.E., Mitchell, J.E. & Wallace, W.A., *IEEE Trans. SMC-C* 37(6):1303–1317, 2007, doi:10.1109/TSMCC.2007.905859. Only the Crossref and Semantic Scholar metadata were fetched; the form is cited via Kaul & Rumpf.
- Holden, R., Val, D.V., Burkhard, R. & Nodwell, S., *Safety Science* 53:51–60, 2013. https://www.sciencedirect.com/science/article/pii/S0925753512002172
- Sharma, N. & Gardoni, P., *RESS* 217:108042, 2022. https://www.sciencedirect.com/science/article/pii/S0951832021005470
- Ouyang, M., *RESS* 121:43–60, 2014 (abstract). https://www.sciencedirect.com/science/article/abs/pii/S0951832013002056
- Kekatos, V., ECE 595 Lecture 3, "Approximate Feeder Analysis" (after Kersting, ch. 3). https://engineering.purdue.edu/~kekatos/pdsa/Lecture3.pdf
- USDA RUS Bulletin 1724D-113 (2012). https://www.rd.usda.gov/media/file/download/uep-bulletin-1724d-113.pdf
- EEPower, "Primary Distribution Systems—Part 1" (Sheikh, 2026). https://eepower.com/technical-articles/primary-distribution-systemspart-1-design-of-feeders-and-laterals/
- Marqusee, J. & Jenket, D., "Reliability of emergency and standby diesel generators", *Applied Energy* 268, 2020 (abstract and highlights). https://www.sciencedirect.com/science/article/abs/pii/S030626192030430X
- Joint Commission, *EC News* July 2021. https://digitalassets.jointcommission.org/api/public/content/assets/1/7/ecn_24_2021_07.pdf
- PSQH, "Once again, safety issues top list of most-cited TJC standards" (2018 data). https://www.psqh.com/news/once-again-safety-issues-top-list-of-most-cited-tjc-standards/
- Joint Commission FAQ, Emergency Generator – Fuel Capacity. https://www.jointcommission.org/standards/standard-faqs/laboratory/environment-of-care-ec/000001246/
- Taylor, I.L., "Hurricane Katrina's impact on Tulane's teaching hospitals", *Trans Am Clin Climatol Assoc* 2007. https://pmc.ncbi.nlm.nih.gov/articles/PMC1863583
- Beatty, M.E. et al., *Public Health Rep* 121(1):36–44, 2006 (abstract via E-utilities). PMID 16416696.
- Inside Towers, "Wireless carriers' power predicament", 1 Sep 2020. https://insidetowers.com/cell-tower-news-wireless-carriers-power-predicament/
- Public Knowledge, 1 Oct 2020 (the 77% figure). https://publicknowledge.org/the-california-wildfires-show-why-we-need-a-national-backup-power-mandate-to-keep-americans-connected-during-disasters/
- Light Reading, "Sandy: the case for better cell site backup?", 2012. https://www.lightreading.com/2g-3g-4g/sandy-the-case-for-better-cell-site-backup-
- CPUC D.20-07-011 (Cal OES copy). https://www.caloes.ca.gov/wp-content/uploads/PSC/Documents/11h-CPUC-decision-20-07-011.pdf
- CPUC AB 2393 Final Analysis Report, 9 May 2008. https://docs.cpuc.ca.gov/publisheddocs/EFILE/PD/82464.pdf
- Tomko, B. et al., *PLOS Water* 2023. https://journals.plos.org/water/article?id=10.1371%2Fjournal.pwat.0000137
- Texas Lyceum, *Power Outages and Boil Water Notices in Texas*. https://www.texaslyceum.org/assets/docs/Executive%20Summary%20%2B%20Research%20Texas%20Lyceum%20(1).pdf
- Reliability Analytics, "Maintainability theory" (citing MIL-HDBK-338). https://reliabilityanalytics.com/blog/2011/09/03/maintainability-theory/

**Searched for and not found:**
- a measured facility-level share of throttle-or-trip departures;
- a gas-turbine low-pressure trip setpoint from a primary source;
- a CPUC primary for the 77% figure;
- the count of NYC hospitals with generator failures in 2003;
- US or TW shares of water systems without standby power;
- the TW 醫療機構設置標準 text (robots-blocked);
- the NCC base-station backup rule (403);
- Taipower feeder ratings.

---

<!-- file: REVIEW.md -->
# Independent review: design targets for unobserved quantities (four lanes)

Reviewer: independent (did not do the research). Date: 2026-09-29.
Read: BRIEF.md, lane_reserves.md, lane_requirements.md, lane_repair.md, lane_mode_strength_gap.md, and deptable/MERGED_DRAFT.md, lane_power.md and REVIEW.md for the cross-checks.
Every source in §1 was re-fetched by me this session or read in the local copy named. `distcheck.py` was re-run and extended.

Verdict key: **confirmed** (says what the lane claims) / **overstated** (real, quote right, but carries less than the lane puts on it) / **wrong** (does not say it) / **unreachable**.

---

## 1. Source checks

| # | Target (lane) | Source, how reached | Lane claim | What the source says | Verdict |
|---|---|---|---|---|---|
| 1 | Transmission threshold 10 MW (req §6) | Taipower 營業規章 Art. 46 in 電配售部業字第10800032292號 (local `elecpe.txt`, lines 758–818) | Table thresholds 100 / 1,000 (2,000) / 5,000 or 10,000 / 30,000 / 225,000 kW | Table confirmed verbatim. But (a) for 1,000 (2,000)–30,000 kW the rule is "應以 69 千伏特供電", and high voltage is an exception "用戶申請…如技術無困難" up to 5,000 kW (11.4 kV areas) or 10,000 kW (22.8 kV areas). (b) The two-circuit clause ("契約容量 5,000 瓩以上者…以兩回線經常供電") sits inside item 2, **planned development areas only** (11.4 kV, 5,000–7,500 kW); the 10,000 kW clause is item 3, planned areas at 22.8 kV. Outside planned areas a customer above 5,000/10,000 kW simply moves to 69 kV; there is no two-circuit rule for 69 kV below 40,000 kW. | **confirmed** (thresholds); **overstated** (the lane's general two-circuit rule and the dual-feed by-product for F4) |
| 2 | Mast battery 4 h / 2 h / 72 h (res §1a) | 公眾電信網路基地臺設置使用管理辦法 Art. 22, rootlaw (WebFetch) | Tower 4 h, remote building 2 h, disaster 72 h | "空地型鐵塔式基地臺之備用電源容量須達四小時以上"; "偏遠地區設置於建築物上之**大型**基地臺…二小時以上"; "經主管機關指定為應具防救災功能之大型基地臺…七十二小時以上". | **confirmed** (minor: the lane drops 大型 "large" from the 2 h and 72 h classes; the "structural weight" motive in res §3 is the lane's speculation, not in the text) |
| 3 | LNG safety stock 7→8→11→14 d; tank 15→16→20→24 d (res §1e) | MOEA Energy Administration menu 8748 (WebFetch) | As stated | Table and "2018年已明定天然氣進口業者應儲備天然氣安全存量" confirmed. The page does not state the "days" basis (the lane's "previous-year average daily send-out" is borrowed from the coal rule). | **confirmed** (basis for gas days is the lane's inference) |
| 4 | Oil 60 d industry + 30 d government (res §1e) | MOEA EA English menu 8675 (WebFetch) | As stated | Both quotes confirmed; no calculation basis for days. | **confirmed** |
| 5 | Oil observed 146 d; gas 10–11 d (res §1e) | EIA Taiwan brief (local `deptable/fuelsrc/eia.txt` l.83, l.176) | As stated | Confirmed verbatim. | **confirmed** |
| 6 | Coal 30 d of previous-year average (res §1e) | law.moea.gov.tw GL000527 (WebFetch) | As stated | "燃煤火力電廠上一年度之平均使用燃料三十天以上數量" confirmed (last amended 2018-03-09). The standard sets no figure for oil-fired plants, which supports the lane's J for oil. | **confirmed** |
| 7 | Hospital water 72 h × 300 L/bed/day (res §1c) | 醫院之旱災、停水、水短缺緊急應變指引 (local `targets/src/gtma.pdf`) | As stated | "依據醫院評鑑基準(條號1.8.1 符合項目4)確認醫院持續運作至少三天為最基本需求"; "儲水量計算方式**建議可依**…WHO…醫院緊急狀況供水量為 72 小時，每日每床 300 公升". A recommendation, not a rule; grade L is right. | **confirmed** |
| 7b | WHO HSI original (for #7) | who.int, iris.who.int (curl: HTML stubs); PubMed 24521616 (WebFetch: HTTP 429, rate-limited; not retried) | — | Not read. | **unreachable** |
| 8 | "300 gallons per bed per day" conflict (res Q6) | HFM Magazine, *Code blue* (reviewer's own fetch) | — | US "average daily consumption estimated between 235 and 300 gallons per bed, excluding HVAC". So 300 gal is **normal consumption**, not an emergency ration. | New evidence; resolves Q6 (Finding 1) |
| 9 | TW hospital power bound 2.9 kW/bed (req §1) | MOHW fp-3797-43466 (WebFetch) | 13.54 t CO2e/bed/yr, an upper bound | "平均每病床碳排放量為13.54公噸" confirmed; the reporting system covers electricity, oil and gas, so the lane is right to treat it as an upper bound on electricity. | **confirmed** |
| 10 | US 8.2 kW/bed inputs (req §1) | CBECS 2018 C14 (local `c14.txt` l.33) | Inpatient 7,631 thousand kWh/bldg, 28.8 kWh/ft² | Confirmed. The per-bed division against AHA staffed beds mixes two populations (CBECS buildings vs AHA hospitals); fine as a US order of magnitude. | **confirmed** |
| 11 | Hospital water demand 1,000 / 500 L/bed/day (req §2) | 建築物給水排水設備設計技術規範 Table A-1 (local `plumb.txt` l.1772) | 高級 ≥1000, 中級 ≥500, 其他 ≥250 L/bed | Confirmed. 高級/中級 is a plumbing sizing grade, not accreditation tier; mapping 高級→tertiary and 中級→regional is judgment. | **confirmed** (mapping is J) |
| 12 | Hazus substations 1/3/7/30 d; distribution circuits; generation (rep §1.1) | Hazus-MH MR4 Table 8.22.a (local `repair/hazus_mr4.txt` l.22490) | As tabulated | All nine cells and σ confirmed. | **confirmed** |
| 13 | Hazus water treatment, pumping, storage (rep §1.1) | MR4 Table 8.1.a (l.19192) | As tabulated | Confirmed. | **confirmed** |
| 14 | Hazus communication, oil, essential facilities (rep §1.1) | MR4 Tables 8.30.a, 8.17.a, 6.11 | As tabulated | Confirmed (EF: 5/20/90/180 d, σ 1/2/10/20, identical for all hospital sizes). | **confirmed** |
| 15 | Hazus 6.1 values (rep Q1) | fema.gov (curl: 403 HTML stub; the three "PDFs" in `repair/` are 496-byte HTML error pages, not manuals) | — | Not read. | **unreachable** |
| 16 | Marqusee & Jenket generator reliability (mode §3) | ScienceDirect abstract (WebFetch) | 50% fail within 48 h (poorly maintained); 80% carry two weeks (well maintained, single EDG) | "Poorly maintained generators are 50% likely to fail within 48 h"; "Well maintained generators are 20% likely to fail within two weeks"; single EDG. Constant-hazard arithmetic re-done: 93.1 h and 51.9 h expected runtime inside 96 h. The data are DoD, and for **one** generator; hospitals run several sets. | **confirmed** (quote); **overstated** as a hospital reserve gap (Finding 10) |
| 17 | Joint Commission 56.25% (mode §3) | *EC News* July 2021 (WebFetch) | 56.25% EC.02.05.07 noncompliance | Figure 1, "Top 10–Cited EC and LS Standards for **Critical Access Hospitals** in Full-Year 2020": 56.25% and 68.75%. Both are exact sixteenths (9/16, 11/16), which suggests a sample of about 16 surveys; the source gives no n. CAHs are rural hospitals of ≤25 beds. | **overstated** (a tiny CAH sample about testing records, used to set a tertiary reserve gap) |
| 18 | Kong-rey restoration (rep §1.2) | MOEA 117817, 117829 (local html) | 863,174 / 761,468; 957,061 / 929,280; half a day for scattered households; Lishan on foot; 63 crews 430 people | All confirmed verbatim. | **confirmed** |
| 19 | Soudelor restoration (rep §1.2) | Anue 639047 (local html) | 98%, 4.29 M, 90,000 out, 4,000 staff, 7,000 households unreachable | All confirmed verbatim. | **confirmed** |
| 20 | Krathon (rep §1.2, §2.1) | MOEA 116112 (local html) | 320,000+ out; 16 crews 84 people | "逾32萬戶"; "7個區處共16班84人" confirmed. | **confirmed** |
| 21 | Backup burn 269 L/h per MW (req §3) | Generator Source chart (WebFetch) | 1,000 kW: 21.6 / 36.4 / 52.1 / 71.1 gal/h | Confirmed, with the vendor's "estimate" disclaimer. Agrees with EPA 0.07 gal/kW/h (0.265 L) to 1.5%. | **confirmed** |
| 22 | EPA fuel rule and 70–80% load (res §0) | EPA 800-R-19-001 (local `fuelsrc/epa.txt` l.860, l.1485, l.850) | As stated | Confirmed. | **confirmed** |

Summary: 22 checks. 17 confirmed, 3 overstated (#1 two-circuit reading, #16 as applied, #17), 0 wrong, 2 unreachable (WHO HSI original, Hazus 6.1). No fabricated figure or quote. As in the dependency-table review, the faults are in how sources are applied, not in the sources themselves.

---

## 2. Findings

Severity: **C** = would corrupt the truth (changes which nodes fail, or when, so it changes answer keys); **M** = would mislead (a reader or committee would catch it; the world is mostly right); **m** = minor.

### F1. Hospital water stock and draw use different quantities, so the buffer is 22 h, not 72 h. **C**
- Reserves: stock = 72 h × **300 L**/bed/day = 900 L/bed (an emergency ration, per the TW guideline citing WHO).
- Requirements: tertiary draws **1,000 L**/bed/day and regional 500 in normal operation (Table A-1).
- The run divides stock by draw, so buffer_h = 900 ÷ 1,000 × 24 = **21.6 h** (tertiary) and 43 h (regional).
- The "300 L vs 300 gal" question is not a unit conflict. 300 gal (≈1,136 L) is US **normal** use (HFM: 235–300 gal/bed/day), which matches TW 高級 1,000 L. 300 L is the curtailed emergency ration.
- **Fix.** Keep 900 L/bed (0.9 m³/bed) as the stock. Add an **emergency water fraction**: while drawing on the stock, the hospital draws 300 L/bed/day, i.e. 0.30 of the tertiary requirement and 0.60 of the regional requirement. The buffer is then 72 h at the curtailed draw. Answer Q6: litres.

### F2. Binary telecom, throttle as s = R, and zero telecom buffer together make telecom loss instantly fatal to every consumer. **C**
- Requirements makes telecom binary, so R ∈ {0, 1}.
- The mode lane defaults control and service to throttle, s = R. At R = 0 throttle gives s = 0: exactly trip.
- Reserves gives telecom zero buffer.
- So a hospital, treatment plant or generator that loses its exchange goes to state 0 at once. That contradicts every lane's own evidence (manual operation, "keeps running but cannot be dispatched", paper fallback over days).
- A second clash: requirements makes telecom κ a **path count** (1, 2, …), but the dissertation fixes κ ∈ [0, 1], and the mode lane sets telecom κ = 1 × public share.
- **Fix.**
  1. Keep the requirement binary.
  2. Keep κ ∈ [0, 1] on each edge (1, or the public share under R1). Redundancy comes from the number of edges, not a κ above 1.
  3. Add a **residual floor** to the control and service modes: on total loss the consumer falls to `floor_δ`, not 0 (placeholder (open decision: control_floor, service_floor); J centre 0.5 for control, 0.7 for service). This is the same "step to a fraction" that the mode lane asks for at hospitals (its Q2). One mechanism covers both.

### F3. The cell-site compliance gap is measured against a rule that never took effect, and it would be applied to a different target. **C**
- The mode lane sets a 50% gap "against 8 h" (FCC 07-177, never in force, which the same lane lists as not to be used). It says the NCC rule returned 403.
- The reserves lane fetched the NCC rule (I confirmed it). The TW target is 4 h.
- Applying a 50% gap to a 4 h target gives a mean of 2 h. That double-counts a US shortfall against a US proposal on top of a TW legal minimum.
- **Fix.** Measure the gap against the TW 4 h. There is no TW compliance evidence. A US "2–4 h typical" against 4 h is 0–50%. Centre on **15%, range 0–50% (J)**. Drop the 77% California no-generator share from TW masts, which run on batteries by rule.

### F4. With the quantile table, "compliance gap = 0" still leaves most elements below the standard, and the upper tail is implausible. **C**
I re-ran the lane's table (distcheck.py, extended):

| CV (h ÷ (1−g)) | share below the mean | 5th pct | max |
|---|---|---|---|
| 0.25 | 55% | 0.65 | 2.4× |
| 0.5 | 60% | 0.41 | 5.1× |
| 1.0 | 66% | 0.18 | 15× |
| 2.0 | 74% | 0.05 | 48× |

- At g = 0, h = 0.5, 60% of hospitals hold less than 72 h, and one in twenty holds under 30 h.
- At h = 1, some hospital holds 15 × 72 h (45 days) of diesel.
- The moments are exact, but the lever's meaning is not what a reader will assume. Regulated stocks cluster at or just above the rule, with a shortfall tail, and have a physical ceiling (tank size).
- **Fix.** Keep the arithmetic, which is sound and cross-platform. Change what it is applied to:
  1. Anchor the table so the **median**, not the mean, equals T(1 − g). The target then reads as "the typical element".
  2. Cap the top knot at a named ceiling, placeholder (open decision: stock_ceiling_factor); J 3×.
  3. State in the specification that g = 0 means "centred on the standard", not "all compliant".

  Alternatively, draw stocks as a mixture: a compliant share at T and a shortfall share on the table below T. That is closer to how inspection data look, but it needs a compliant-share figure, which no lane found.

### F5. The κ line term can make a consumer short of supply in the undisturbed world. **C**
- The mode lane's own worked example gives a 5 MW consumer 10 miles out κ ≈ 0.34.
- With physical_flow defaulting to trip on R < 1, that consumer is dead at t = 0 before any disruption.
- A real utility would not connect it that way.
- **Fix.**
  - Add a world check: undisturbed R_φ(v) ≥ 1 for every consumer. "Barely enough" means headroom just above 1, not below it.
  - Where the line term fails, the generator attaches the consumer to a nearer or higher-voltage supplier (which is what the Taipower threshold does) rather than emitting an infeasible world.
  - Recompute K_drop for 11.4 kV and 22.8 kV. The 12.47 kV US value misstates a TW-like world by about 10–20%.

### F6. The 10 MW threshold picks the less common voltage area and treats the exception as the rule. **C**
- **10,000 kW** is the high-voltage ceiling in **22.8 kV** areas. In **11.4 kV** areas it is **5,000 kW**.
- As far as I know, 11.4 kV is Taipower's predominant distribution voltage, with 22.8 kV in newer and planned areas. I did not verify this from a source.
- Above 1,000 kW (2,000 kW) the default is 69 kV. High voltage is a customer-requested exception.
- The dual-feed by-product is misread (source check #1).
- **Fix.**
  - Default `transmission_connection_threshold_mw` = **5** (S · TW, 11.4 kV areas).
  - Add a recipe key `distribution_voltage_kv ∈ {11.4, 22.8}` (default 11.4) that switches it to 10.
  - Apply it to **peak**, as the lane says.
  - `dual_utility_feed` is true only for ≥ 40 MW at 69 kV (and ≥ 225 MW at 161 kV), plus planned-area high-voltage customers. There is no Taipower basis for dual feeds at tertiary hospitals below 69 kV (REVIEW F4 stands).

### F7. Hazus calendar days are used as crew processing time, and they do not fit a 72 h storm pilot. **C**
- Hazus means are days to restored function for a class population. They include assessment, parts, access and queueing. The lane notes this ("they already contain crews") but still uses them as the time a crew is held.
- With 2 crews:
  - a moderate substation (mean 72 h, uniform-equivalent range 10–134 h) ties up a crew for the whole window;
  - any extensive or complete state never finishes;
  - a hospital with *slight* damage (Hazus EF: 5 d) stays out all window.
- Repair ordering then barely matters, which defeats the pilot's purpose.
- The Taiwan evidence (88–98% of customers restored in 1–2.5 days) is about lines and poles, not facility repairs.
- **Fix.** Split each repair into two parts:
  1. A **lead time** that does not hold a crew: access, parts, assessment. Drawn, placeholder.
  2. **Crew work content** in crew-hours. J anchors from the TW releases, e.g. slight 4–8 h, moderate 12–36 h.

  Keep Hazus as the evidence-based upper bound on lead time plus work, and as the source of the CV per damage state.

  For the storm pilot:
  - generate only slight and moderate damage at facilities;
  - apply no direct damage to healthcare nodes, which fail through their dependencies;
  - leave extensive and complete nodes failed for the whole window.

### F8. Two lanes propose incompatible draw methods. **M**
- Repair uses a uniform on [μ − √3σ, μ + √3σ] with a floor that moves the mean.
- Mode/gap uses the lognormal-shaped quantile table.
- **Fix.** Use one method: the quantile table. For a Hazus cell, take T = μ and CV = σ/μ (0.06–1.0). The table is positive by construction, so no floor is needed and the mean is kept. This removes repair Q1(b).

### F9. The "tertiary 2–3 MW, below the line" conclusion rests on an 800–1,000-bed example. **M**
- Taiwan medical centres commonly run 1,000 to over 3,000 beds (J; not fetched this session).
- At 2.5 kW/bed and a peak factor near 1.5, a 1,500-bed centre peaks at about 5.6 MW, which is above the 11.4 kV ceiling (F6).
- The per-bed figure is defensible: it sits inside the TW bound (check #9) and I found no TW facility total to test it (the searches for 醫學中心 annual kWh returned nothing usable).
- **Fix.** Do not state a class-level connection outcome. Let drawn beds × kW/bed × peak factor decide it per node.

### F10. The hospital reserve gap is built on the wrong evidence. **M**
- The Joint Commission 56.25% is a count of testing and documentation citations at critical access hospitals (n ≈ 16).
- Marqusee is single-generator DoD reliability. A hospital with N+1 sets fails far less often.
- Neither measures fuel held against a target.
- **Fix.** Carry generator reliability as a separate availability draw (answer to mode Q8), with Marqusee's per-set failure rates, not as a stock gap. Set the hospital fuel-stock gap to **0%, range −25% to 25% (J)**. TW accreditation (F11) inspects it.

### F11. A Taiwan hospital anchor was cited but not followed up. **M**
- The water guideline cites 醫院評鑑基準 1.8.1 item 4: "持續運作至少三天" (continued operation for at least three days). Accreditation applies to regional hospitals as well as medical centres.
- If 1.8.1 covers utilities generally (its heading was not retrieved), it gives a TW basis of 72 h for both classes, fuel included. That replaces the JP analogue.
- **Fix.** Retrieve 醫院評鑑基準 1.8.1. Meanwhile set **regional = 72 h** (answer to reserves Q3), since the only TW rule found does not distinguish.

### F12. The hospital essential fraction exists in the lanes' own sources. **M**
- The mode lane says "I found no source for its size".
- The reserves lane quotes MHLW: disaster base hospitals keep generators of "通常時の６割程度の発電容量" (about 60% of normal generating capacity).
- **Fix.** Set essential_load_fraction = **0.6** (S · JP for designated hospitals; J elsewhere). Use it for the hospital power floor (F2) and for P_gen in the fuel conversion.

### F13. The dependency table's fixed supplier classes contradict the load rule. **M**
- Airports are "distribution only" in the dependency table, but the requirements target gives a 40 M-passenger airport 14 MW.
- LNG terminals are "transmission" always, but the requirements estimate (1.1–1.5 MW/Mtpa) puts a 6 Mtpa terminal at 7–9 MW.
- **Fix.** Apply `peak_mw ≥ threshold → transmission_substation` to every consumer class. Drop the per-class fixed entries, except refinery, which the load rule already sends to transmission.

### F14. A target is missing: the resupply rate on `buffer_resupply` edges. **M**
- The mode lane says κ "scales the refill rate of the reserve", but no lane gives a rate or lead time.
- In a 72 h window, whether a 72 h hospital tank is topped up decides whether it runs dry. That makes this the most answer-key-relevant missing target.
- **Fix.** Add `resupply_lead_time_h` and `delivery_volume_L` per depot → consumer edge.
  - The only anchor: EPA says a portable unit "must be delivered with a 24-hour fuel supply" (lane fuel S13).
  - Otherwise J, e.g. a 12 h lead time and one 24 h load per delivery. Mark it placeholder.

### F15. Bulk stocks cannot bind in a 72 h pilot. **m**
- LNG 11 d, oil 90 d, coal 30 d and blood 7 d are all correct as defaults (checks #3–6).
- They matter only for multi-week blockade runs.
- **Fix.** Accept them as they stand. Answer Q9 with the simplest rule and move on.

### F16. The access multipliers are misapplied and below resolution. **m**
- Azad & Ghandehari measure area-level outage days per barrio, not facility repair time.
- Factors of 1.06–1.11 on a job of a few hours round away in whole hours.
- **Fix.** Drop them. Keep road-network travel time and a blocked-road reachability rule (a node is unreachable until its access edge is repaired). That rule carries the strong effect the TW releases describe.

### F17. US values are used where TW values exist. **m**
- Heat rates: Taipower publishes unit heat rates in its statistics.
- K_drop at 12.47 kV (F5).
- EPRI 2002 treatment energy.
- **Fix.** Keep them as L · US with that label. Replace them if TW values are fetched, and do not grade them TW.

### F18. Data-centre load is taken from rated capacity. **m**
- MVA × 0.9 is the rating, not the average draw. Operating sites run well below it.
- **Fix.** Multiply by `it_utilisation` (placeholder (open decision: data_centre_utilisation); J 0.6).

### F19. Hazus 6.1 is unverified, and the local 6.1 files are error pages. **m**
- `repair/fema_hazus-*-6-1.pdf` and `-5-1.pdf` are 496-byte HTML error pages.
- The MR4 values are confirmed. The 6.1 titles match (the lane saw them).
- **Fix.** Cite MR4 explicitly and note 6.1 as unverified. Delete the stub files so no one cites them as read.

---

## 3. Consolidated design questions (deduplicated), with recommended answers

Source lanes: Res = reserves, Req = requirements, Rep = repair, Mode = mode/strength/gap, Rev = raised by this review.

| # | Question (origin) | Recommended answer | Reason |
|---|---|---|---|
| 1 | Is the draw for backup fuel rated or expected load? (Res Q1) | **Expected load**: essential fraction × site load (F12), with the Generator Source part-load curve. Store the target as hours at that load. | Hours are what the answer key uses. At rated load P_gen cancels and the stock is understated by 1.3–1.9×. |
| 2 | Do battery and generator hours add? (Res Q2) | **Yes**, fuel_h + battery_h. | The battery carries the load again only after the generator fails or runs dry, so the sum is the endurance. |
| 3 | Regional hospital: 48 h or 72 h? (Res Q3) | **72 h**. | The TW accreditation criterion does not distinguish (F11), and neither do CMS or NFPA. |
| 4 | Blood thermal hold-over: omit it, or treat it as a pseudo-stock? (Res Q4) | **Omit it** in Phase 1. | 17–24 h matters only for a blood bank with no generator, which the defaults do not create. |
| 5 | Does the fire reserve count toward the water buffer? (Res Q5) | **No.** | It is legally held back for fire flow. Counting it overstates potable endurance. |
| 6 | Hospital water: 300 L or 300 gal per bed per day? (Res Q6) | **300 L** as the emergency draw. 300 gal is US normal use (F1). | Resolves the units and the stock/draw mismatch together. |
| 7 | Add a 3-day hospital supply stock on transport → healthcare? (Res Q7) | **Yes**, 72 h, J/S · JP. | It is the only buffer on that edge. Without it, road loss is instantly fatal. |
| 8 | Airport standby-generator fuel? (Res Q8) | **Omit it.** | Airfield lighting on standby does not change the airport's supplier role in the model. |
| 9 | Allocate the 60 d + 30 d oil stockpile how? (Res Q9) | **Pro rata by tank capacity** across import_terminal, refinery and tank_farm. Government 30 d only at tank_farms. | It cannot bind in 72 h (F15), so the simplest rule serves. |
| 10 | Telecom: binary requirement, and what does κ mean? (Req Q2, Mode Q5) | **Binary requirement.** κ ∈ [0, 1] per edge (1, or the public share under R1). Redundancy comes from edge count. | Keeps the dissertation's κ definition (F2). |
| 11 | What happens on total telecom loss: zero buffer? (Res Q10; merged with Mode Q2 on the hospital essential fraction) | Add a **step-to-floor** mode: control → 0.5, service → 0.7 (J). Hospital power → 0.6 (JP). | One mechanism covers both. Avoids instant total failure (F2). |
| 12 | Data-centre make-up water? (Res Q11) | **None.** | No verified figure. Most TW colocation sites are air- or chiller-cooled on closed loops (J). |
| 13 | Hospital kW per bed: TW or US reference? (Req Q1) | **TW**: 2.5 / 2.0 kW/bed. | It sits inside the TW bound (check #9). The world is TW-like. |
| 14 | Tables from WPI size and airport class to boxes and passengers? (Req Q3) | Put them in the recipe as placeholders, anchored to TW ports and airports' published throughput (J). | No source maps the classes. Recipe values are visible and tunable. |
| 15 | Taipower table version and voltage area? (Req Q4, Rev) | Confirm against the 2022 營業規章. **Default 5 MW** (11.4 kV) with a recipe switch to 10 (F6). | 11.4 kV is, to my knowledge, the predominant voltage. 10 MW applies only in 22.8 kV areas. |
| 16 | Does coupling strength use average or peak? (Req Q5) | **Average** for κ. **Peak** for the connection threshold. | κ describes normal delivery. Contract capacity is sized on peak. |
| 17 | Can the Hazus values be confirmed against 6.1? (Rep Q1a) | **Cite MR4.** Note 6.1 as unverified (F19). | MR4 is confirmed locally; FEMA returns 403. |
| 18 | Draw method for σ ≈ μ, and what "spread" means (Rep Q1b, Mode Q6) | **The quantile table for all draws.** Spread = **SD**. Median-anchored with a ceiling (F4, F8). | One method, positive by construction, exact moments. |
| 19 | Damage states against the 72 h window (Rep Q2) | Pilot: **slight and moderate only** at facilities. Extensive and complete nodes stay failed. Split lead time from crew work (F7). | Otherwise repair ordering has no effect. |
| 20 | One crew pool or one per owner? (Rep Q3) | Pilot: **one pool of 2**, declared as a scarcity setting. Full build: **per owner**. | Matches the lane's argument. Owners repair their own layers. |
| 21 | Two meanings of "depot"? (Rep Q4) | **Rename** the repair base `crew_base`. | Keeps manifest names unambiguous. |
| 22 | Mobilisation delay for an outlying island? (Rep Q5) | **Placeholder**, J centre 12 h. | Taipower pre-positions island crews, so the delay applies only to surge crews. |
| 23 | Second depot if the spine blocks roads? (Rep Q6) | **No** for the pilot. Handle it through blocked-road reachability (F16). | Keeps the pilot small. The road network already carries the effect. |
| 24 | Reservoir repair? (Rep Q7) | **Not repairable within the window.** | There is no Hazus class, and dam repair is weeks. |
| 25 | Is the failure mode the consumer response or the g_δ family? (Mode Q1) | **The consumer response to R_φ**, drawn per (node, commodity). | g_δ is already canon on the edge. Drawing both would double-count. |
| 26 | Canon mode per type or per type × class? (Mode Q3) | **Per type × class** (Mode §1.2). The 10% heterogeneity draws against that. | Systematic class behaviour should not come from noise. |
| 27 | κ cap: read "three times its need" as uncapped headroom? (Mode Q4) | **Keep κ = min(1, ·)**. Record the uncapped headroom in the manifest. Fix the Structure §4.4 wording. | Def. 3.3 governs. Headroom stays visible for analysis. |
| 28 | g = 100 corner? (Mode Q7) | **Cap g at 95** in the recipe schema. At g ≥ 95, represent the absence through the presence attribute instead. | Absence is a presence gap (R9), not a continuous gap. |
| 29 | Generator reliability: gap or availability? (Mode Q8) | A **separate availability draw** (fail to start, fail to run), per set (F10). | It is a performance failure, not a size shortfall. |
| 30 | What does g mean given skew? (Rev) | g shifts the **median**. State that g = 0 means centred, not compliant (F4). | Otherwise 60% of "compliant" worlds sit below the rule. |
| 31 | Undisturbed feasibility (Rev) | Add the world check "undisturbed R_φ(v) ≥ 1 for all v" (F5). | A world that is short before the storm corrupts every answer key. |
| 32 | Resupply rate on `buffer_resupply` edges (Rev) | Add lead time and delivery volume as placeholders: J 12 h and 24 h of fuel per delivery (F14). | This decides hospital run-dry inside 72 h. |

**Count: 32.** The lanes raised 31 (reserves 11, requirements 5, repair 7, mode 8). Deduplication gives 29 (rows 1–29):
- Four telecom and floor questions become two: Res Q10, Req Q2, Mode Q5 and Mode Q2 → rows 10–11.
- Rep Q1 is split in two: the version (row 17), and the draw floor, merged with Mode Q6 (row 18).

This review adds 3 (rows 30–32), and extends row 15.

---

## 4. Verdict

The sourcing is honest and mostly solid. Of 22 re-checked sources, 17 say exactly what the lanes claim, none is fabricated, and the Taiwan legal anchors are verbatim: the NCC mast hours, the LNG, oil and coal stock floors, and the Taipower table. The lanes should not yet be used as the centre of the synthetic truth, because they do not agree with each other on the quantities that decide answer keys in a 72-hour pilot:
- the hospital water stock and draw are in different regimes (a 22 h buffer, not 72 h);
- binary telecom plus throttle plus zero buffer makes any telecom loss instantly total;
- the cell-site gap targets a US proposal while the stock targets the TW rule;
- the κ line term can leave consumers short before any disruption;
- Hazus calendar days, used as crew processing time, make repair ordering irrelevant inside the window.

The 10 MW threshold should default to 5 MW (11.4 kV areas), and the Taipower two-circuit rule was misread. The quantile-table arithmetic is correct and cross-platform. What needs fixing is its meaning: anchor it on the median and cap the tail, so that "no compliance gap" does not quietly place most elements below the standard. With F1–F7 fixed and questions 1, 6, 10, 11, 15, 18, 19, 30, 31 and 32 decided, the targets are defensible for the pilot.

---

# Addendum (v0.2): emergency repair and telecom tolerance

---

<!-- file: lane_emergency_repair.md -->
# Lane: emergency (temporary) repair versus permanent repair

Date: 2026-09-29. Grades follow BRIEF.md: **S** is a standard, code or regulation; **L** is literature or a government or utility report; **J** is judgment. Jurisdiction is marked US, TW, JP or intl.

**What this builds on.** lane_repair.md gives the permanent repair (Hazus MR4 restoration means, confirmed by REVIEW.md checks #12–14). REVIEW F7 splits a permanent repair into a lead time that holds no crew plus crew work. REVIEW F8 sets the quantile table as the one draw method. Both are assumed here. The portable-generator refuelling and 24 h fuel evidence is reused from `deptable/lane_fuel.md` (S7 CSRIC IV WG9; S13 EPA), which the dependency-table review confirmed. The Marqusee & Jenket generator-failure figures are reused, with the caution in REVIEW F10: they are DoD data for a single generator.

**Source access.** Taipower's own sites refused or reset connections, and so did its substation-capacity PDF for secondary (69 kV) substations. The primary-substation list came through WebFetch. IEEE Xplore and ResearchGate refused the Lee, Mitchell & Wallace (2007) full text, and only its abstract was read (via OpenAlex). Every other source below was fetched this session. Local copies are in `targets/emerg/`.

---

## 0. The findings that change the model

1. **Two different things are called "emergency measures".** Only one of them is a repair.
   - A **node substitute** replaces the damaged node's own function. Examples: a mobile substation, a cell-on-wheels, a temporary bridge, a field hospital.
   - A **supply substitute** replaces a commodity the node has lost from upstream. Examples: portable generators at pump stations, generator vehicles at hospitals, water trucks, fuel trucks.

   Most of what Taiwan fields in a typhoon is the second kind:
   - Taiwan Water Corporation's 567 emergency generators and 62 water trucks;
   - the carriers' planned 200 or so portable generators;
   - TEPCO's 238 high-voltage generator vehicles in Typhoon Faxai.

   These belong on the dependency edge, as a mobile supplier or a buffer. They do not belong in the node's repair job (§3).
2. **Inside a 72-hour storm window, emergency repair matters for only two classes.** If the storm produces only slight and moderate facility damage (REVIEW Q19), an emergency mode beats the permanent repair only where the permanent repair takes longer than the emergency set-up:
   - **distribution substations** at moderate damage: a mobile substation takes 12–24 h, against the Hazus mean of 72 h;
   - **masts**: a cell-on-wheels takes about 14 h.

   Elsewhere, either the permanent repair is already short, or the emergency measure itself takes 3 days or more:
   - a temporary bridge takes 72 h;
   - a mobile gas turbine takes about 14–15 days;
   - an airport reopens partially after about 3 days.
3. **Restored capacity is small and specific to the commodity.**
   - A nominal mobile transformer is **25 MVA**. Taiwan's distribution substations (D/S) have **120–240 MVA** installed, so c ≈ 0.1–0.2 of nameplate.
   - A temporary bridge in Taiwan first carried only cars of **5 t or less**, on one lane, in three daily time windows. For trucked fuel and freight, c = 0 for about 8 weeks.
4. **Durability does not bind inside 72 h for a mobile substation. It does bind for anything that runs on fuel.**
   - A mobile substation stays in place for months ("up to 6 months").
   - A generator-powered unit needs refuelling every 8–12 h. That is a buffer with resupply, and the resupply machinery of REVIEW F14 already covers it.
   - A temporary bridge is more fragile. Taiwan temporary bridges were washed out by the next typhoon twice (2023, 2024).
5. **Model it as two modes, not a sequence, inside the window.** Each eligible damaged node gets two alternative modes of one repair job:
   - **E:** emergency, drawing a unit from a finite pool;
   - **P:** permanent.

   Within 72 h, a permanent repair started after an emergency one almost never finishes, so a sequence would add machinery that never acts. Switch to the sequence (E, then P, with the unit released when P finishes) only if the window is lengthened past about 7 days (§4).

---

## 1. Per node class: emergency measure, time, capacity, durability, eligible damage states

- e is the time from dispatch to service, in hours, including set-up. Road travel over the network is added separately, as in lane_repair §3.
- c is restored capacity as a fraction of the node's original capacity, or of its undisturbed peak where stated.
- "Eligible DS" lists the damage states for which the emergency mode is worth offering. It is offered where it exists and is faster than the permanent repair.

### 1.1 Power

| Class | Measure | e (h): centre [range] | c: centre [range] | Durability and limits | Eligible DS | Grade, jurisdiction |
|---|---|---|---|---|---|---|
| distribution_substation | Mobile substation or mobile transformer on a trailer | **18 [6–24]** | **min(1, 25 MVA ÷ node peak MVA)**; about 0.14 of a 180 MVA TW D/S nameplate [0.1–0.4] | Stays until the permanent unit arrives: used "for transformer failure replacements (up to 6 months)". Runs hot with no overload margin: temperature rise "Up to 115" °C against 65 for a fixed unit; "the overload capability is less"; full-load losses 1.5% against <0.5%. **Cap at nameplate; no emergency overload.** No evidence of a higher failure rate was found. | moderate, extensive, complete (a completely destroyed 161/13.2 kV substation was served by a mobile). Not slight: Hazus slight is 24 h, about the same as e. | L · US (DOE 2006, Versant); TW capacity L; c formula J |
| transmission_substation | None within the window. A mobile covers only ≤100 MVA and ≤230–245 kV. A rapid-spare transformer (RecX) took 106 h. | — | c ≈ 0 against TW E/S of 1,000–4,000 MVA | — | none in a 72 h window | L · US; J for TW |
| generation | Mobile gas turbine (TM2500, up to about 35–37 MW) | **~14 days** ("~14 days install time"; Puerto Rico: 15 days from arrival to grid) | 35 MW against a plant of hundreds of MW, so ≪ 0.1 | Emergency fleet and fuel | none in window | L · US/intl |
| *(line edges, for reference)* | Temporary poles; generators on the utility side of the meter; emergency feeding (JP 応急送電) | — | — | Restored lines re-failed: Puerto Rico's curves were non-monotonic because of "lines that failed after they were brought back to service … weakened vegetation" | out of this lane's scope (edges) | L · US |

**Evidence.**
- **DOE, *Benefits of Using Mobile Transformers and Mobile Substations for Rapidly Restoring Electrical Service* (EPAct §1816 report to Congress, Aug 2006).**
  - "their deployment capability (roughly 12 to 24 hours) is a major advantage"
  - "Mobile transformers are most widely available in the medium-power range (10 to 100 MVA) with HV ratings to 245 kV"
  - "MTS systems are typically below 50 MVA in size, with high-side voltages not exceeding 230 kV"
  - Table 3 gives MVA low 5, **nominal 25**, high 100.
  - "roughly 500 to 600 mobile transformers in service (slightly greater than 1% of the medium-power transformer inventory)". Table 4 puts 45,000 medium-power transformers against 600 mobile.
  - "utilities use them only until a suitable stationary unit is obtained"
  - "the losses and costs … are generally too high for them to be used as long-term replacements"
  - The report contradicts itself on impedance. Its text says MTS "have lower impedance, which results in higher fault currents", but Table 2 gives %Z 12–15% (mobile) against <10% (fixed). Neither figure is used here.
  - Dyersburg, TN (2006): a 161/13.2 kV, 10/13/16 MVA substation "was completely destroyed … Service was restored using a mobile transformer from the TVA while a new substation is constructed".
  - "A typical substation … Three transformers, each with a nominal 25-MVA rating".
- **Versant Power (US utility).** It can "mobilize this unit within six hours". The unit can "match the capacity of our largest distribution substations". It is the "largest of three mobile substations Versant Power has in its Bangor Hydro District".
- **Taipower**, 超高壓及一次變電所供電能力資訊 (2023 data). The D/S rows give 主變裝置容量 of 120, 180 (most rows), 230 and 240 MVA. Examples: 宜市D/S 120, 樹林D/S 180, 利澤D/S 240. The E/S rows are in the thousands (汐止E/S 2500). The 69 kV secondary-substation list returned 403 (Question 3).
- **DHS, RecX.** The units were "installed and energized in less than six days (106 hours)" against "the 30 days that are typically required". Flexible spares were expected "to provide a service life of 5-10 years, rather than the conventional 40-year life".
- **GE Vernova, TM2500 product page:** "Up to 37 MW", "~14 days install time". **Turbomachinery Magazine (Puerto Rico 2017):** two TM2500 units were connected to the grid "just 15 days after its equipment arrived on site". Kwasinski et al.: San Juan was powered "by mid-October with a 50MW temporary unit".

### 1.2 Telecom

| Class | Measure | e (h) | c | Durability and limits | Eligible DS | Grade, jurisdiction |
|---|---|---|---|---|---|---|
| mast | Cell-on-wheels, cell-on-light-truck, or a mobile base-station vehicle (行動基地台車), with satellite backhaul where the fibre or microwave is also lost | **14 [8–24]** (FirstNet "14-hour on-air objective") | **0.5 [0.3–1.0]** of the site's traffic | Runs on its own generator: a portable generator "has to be refueled every 8-12 hours" (CSRIC IV WG9, via lane_fuel S7). So it is a fuel buffer, and resupply over a passable road is required. | all, including complete (it replaces the site), if a road and a pad are reachable | e: L · US. c: **J**; no source for COW capacity against a macro site was found. |
| exchange | Technology recovery trailers (AT&T NDR: "65+ technology recovery trailers"; an older brochure gives "95 SEMI TRAILERS") | **not found** | not found | — | **none in the pilot (J)**: no deployment time was found | L · US (fleet only) |
| data_centre, cable_landing | No field emergency repair. Service moves elsewhere (failover), which the world does not model. | — | — | — | none | J |

**Evidence.**
- **TW, Typhoon Danas (2025).**
  - CNA, 21 Jul 2025: Chunghwa Telecom deployed "16台行動基地台車" (16 mobile base-station vehicles), 6 with OneWeb LEO satellite systems; 3,104 person-trips. Taiwan Mobile deployed "10部" satellite-equipped mobile vehicles.
  - CNA, 4 Aug 2025: "30餘輛行動基地台車在嘉南地區提供服務" (over 30 mobile base-station vehicles serving the Chiayi–Tainan area). 33 base stations were still awaiting repair, with a deadline of "10月底前全數復原完畢" (all restored by the end of October). That is about 3 months of emergency service for structurally destroyed sites.
  - Commercial Times, 4 Aug 2025 (MODA): 28 vehicles with LEO satellite terminals had been sent to Tainan and Chiayi. The three carriers will each buy 3 more (9 in total). Another "31 輛未設置衛星終端設備的行動車" (31 mobile vehicles without satellite terminals) will be refitted. The carriers also plan "200餘台可攜式緊急發電機" (more than 200 portable emergency generators).
- **TW, Typhoon Koinu (2023; Chunghwa Telecom release, 12 Oct 2023).** It "出動行動車進入滿洲鄉架設臨時台提供緊急通訊服務" (sent a mobile vehicle into Manzhou to set up a temporary site). Lanyu was restored with helicopter support.
- **US.**
  - FirstNet Authority, *Understanding the FirstNet Deployable Program*: "72 FirstNet Satellite Cell on Light Truck (SatCOLT) and Cell on Wheels (COW) deployables" and a "14-hour on-air objective for emergent incident responses". The FirstNet One aerostat stays aloft "for about 2 weeks".
  - AT&T NDR infographic: "450+ portable market cell sites", "11K+ portable generators", "65+ technology recovery trailers".

### 1.3 Water

| Class | Measure | e (h) | c | Durability and limits | Eligible DS | Grade, jurisdiction |
|---|---|---|---|---|---|---|
| treatment | Mobile treatment unit (移動式淨水設備), plus water trucks (a supply substitute) | not found for disasters | ≈ 0: a 500 t/day unit against a plant of tens of thousands of t/day or more | — | **none (J)**: c is too small to matter | L · TW (unit sizes); J |
| pumping | Physical damage: portable pump or bypass (J). Power loss: a portable generator, which is a **supply substitute** | not found | Power substitute: **0.5 [0.3–1.0] (J)**, since "Some stations have too many motors for a portable generator to run" | Fuel: "delivered with a 24-hour fuel supply" (EPA). Then resupply. | physical damage: moderate (J) | L · US (EPA); fleet L · TW |
| storage | Bypass: pump straight into the network (J) | not found | J | — | moderate, extensive (J) | J |
| reservoir | none | — | — | — | none (lane_repair Q7) | J |

**Evidence.**
- Taiwan Water Corporation, pre-typhoon release (udn, 25 Aug 2026): "備妥567台緊急發電機" (567 emergency generators ready), "調度62台水車待命" (62 water trucks on standby), 3,054 staff and 357 contractors.
- China Times, 23 May 2021 (drought, not a disaster): "日產水500噸的大型移動式淨水設備18台" (18 large mobile units of 500 t/day) and "日產水15噸的小型移動式淨水設備15台" (15 small units of 15 t/day).
- EPA, *Power Resilience Guide for Water and Wastewater Utilities* (800-R-19-001, local `epapwr.txt`): "Some stations have too many motors for a portable generator to run. Running all the motors could cause the generator to kick-off"; "Keep smaller generators on trailers for emergencies"; "the generator must be delivered with a 24-hour fuel supply".

### 1.4 Transport

| Class | Measure | e (h) | c | Durability and limits | Eligible DS | Grade, jurisdiction |
|---|---|---|---|---|---|---|
| bridge | Temporary steel bridge (鋼便橋), Bailey-type or modular (JP 応急組立橋); or a river-bed track (河床便道) | **72 [72–96]**: TW 3 days; JP "15人・３日" (15 people, 3 days) | Light vehicles: about 0.1 (single lane, 3 windows a day, derived). **Heavy vehicles: 0** until upgraded, about 8 weeks in the TW case. The JP kit carries B live load (trucks and buses). | In service for months to years (JP: about 3.5 months to about 2 years). **More fragile:** TW temporary bridges were washed out by the next typhoon in 2023 and 2024. | extensive, complete. Not slight or moderate: the Hazus means of 0.6 and 2.5 days are already ≤ e. | L · TW, JP |
| airport | Partial reopening: one runway, part of the traffic | **72** (Kansai, 3 days) | **0.3–0.5 (J)**: domestic flights only, one of two runways | Full operations after 17 days | moderate, extensive | L · JP |
| seaport | Partial or restricted berths | not found | J | Kobe: "less than half of the port facilities were rebuilt a year after the quake"; "fully reconstructed within 26 months" | J | L · JP (permanent only) |
| freight_yard | none found | — | — | — | none (J) | J |

**Evidence.**
- **TW, Xiaqingshui Bridge (下清水橋), 0403 Hualien earthquake 2024** (Commercial Times, 20 May 2024).
  - The Highway Bureau finished the steel temporary bridge on 6 April, three days after the quake.
  - It first allowed "5噸以下小客車單線雙向通行" (cars of 5 t or less, one lane used in both directions), in three daily windows: 06–08, 12–13 and 17–19.
  - Large vehicles were to be allowed from about 30 May, at "15公里以下" (15 km/h or less).
  - The permanent bridge was due by the end of the year. Commercial Times, 20 Dec 2024: "經8個月搶修施作，提前完成橋梁原址重建，於昨晚6時恢復雙向通行" (after 8 months of work, the rebuild on the original site finished early, and two-way traffic resumed at 6 pm on 19 December). So the emergency bridge served for about 8.5 months.
- **JP, MLIT.**
  - Kinki Regional Bureau (Fukui): the 応急組立橋 is 16–40 m long, with an 8 m roadway, and needs "15人・３日". It is removed once the original bridge is repaired.
  - Kanto Technical Office report: 2 bridges held. Deployments lasted about 2 years (1992–94), about 1 year 8 months (1995–97) and about 3.5 months (1998). Both kits are "B活荷重" (B live load).
- **TW, fragility of temporary bridges.**
  - Commercial Times, 5 Oct 2023: the temporary bridge at Taluowan Creek (Lushan Hot Spring), built after Typhoon Khanun had destroyed the original, was washed out by Typhoon Koinu.
  - Commercial Times, 27 Jul 2024: the Mingbakelu steel temporary bridge on the Southern Cross-Island Highway was damaged by Typhoon Gaemi ("鋼便橋受損4跨", four spans damaged). The river-bed track was being pushed through with "13部" (13) excavators, but no duration was given.
- **TW, a large permanent temporary bridge.** The Mataian Creek steel temporary bridge (udn) is 560 m long and 12 m wide, two lanes each way, and opened on 1 Jan 2026 after the bridge was destroyed on 23 Sep 2025. That is weeks, not a 72 h measure.
- **JP, Kansai Airport, Typhoon Jebi (4 Sep 2018).**
  - It was expected "to reopen to domestic flights on Friday (September 7)"; "one of the two runways was also flooded" (Air Cargo News).
  - It "resumed full operations" on 21 Sep with "99 percent of pre-typhoon passenger flights" (Japan Times, 21 Sep 2018).
- **JP, Kobe 1995 (NZSEE bulletin).** The Meishin Expressway had "one lane of emergency traffic on 2 February" (day 16), two thirds open on 17 February, and full restoration on 31 July. Traffic in mid-February was "only 30%" of the pre-quake level.

### 1.5 Fuel

| Class | Measure | e (h) | c | Durability and limits | Eligible DS | Grade, jurisdiction |
|---|---|---|---|---|---|---|
| depot, tank_farm | Drums and mini-lorries; surge tank-truck delivery from an undamaged depot. This is a **supply substitute**. | not a repair | — | — | none as a repair (J) | L · JP, US |
| import_terminal, refinery | none within the window | — | — | — | none | J |

**Evidence.**
- **JP, Noto 2024** (METI Chubu). Of 36 core and resident service stations, 14 lost power and 12 reopened on their own generators. Reopening ran at about 30% by day 3, 50% by day 5 and 90% by day 10 (other stations: 20%, 30–40% and 60%). "10台を超えるタンクローリー" (more than 10 tank trucks) served an area normally run with a few. Deliveries used "ドラム缶・ミニローリー等" (drums, mini-lorries and the like).
- **US, Sandy 2012** (DoD update): "approximately 230 trucks with approximately 1.6 million gallons of fuel capacity"; "51 Generators (500-2000KW)".

### 1.6 Healthcare

| Class | Measure | e (h) | c | Durability and limits | Eligible DS | Grade, jurisdiction |
|---|---|---|---|---|---|---|
| tertiary, regional | Field hospital or Federal Medical Station. It is a **new node**, not a repair. | **24–48** for the cache, plus set-up (a 10–12 person team) | **Acute care: 0.** It takes 50–250 "stable primary or chronic care" patients at "low acuity". | It needs "a structurally intact, accessible building … functioning utilities", so it cannot sit inside a damaged hospital's lost utilities | none as a repair (J) | L · US |
| clinic, blood_bank | none found | — | — | — | none | J |
| *(hospital power loss)* | Generator vehicles or USACE-installed generators. These are **supply substitutes**. | Installation "can consume an entire day" (USACE) | — | Long use "requires routine maintenance to keep functioning"; the single-EDG failure rates (REVIEW #16) apply with caution | — | L · US, JP |

**Evidence.**
- FEMA, *Key Planning Factors* KPF6 §2.2 (Federal Medical Stations): the "cache of equipment and supplies will be delivered in 24-48 hours"; "a 10-12 person set up team"; "low acuity care for patients with chronic illnesses"; it requires "a structurally intact, accessible building".
- US Army (2017): in Puerto Rico, 365 generators were operating by 1 November. Priority went to "hospitals, emergency shelters, water facilities, and wastewater treatment plants". Installation "can consume an entire day".
- **JP, Typhoon Faxai 2019** (METI Resilience WG, 005_04):
  - "高圧発電機車（他電力含む）約4,000名、238台" (238 high-voltage generator vehicles, including other utilities'), of which "他電力からの高圧発電機車174台" (174 came from other utilities), plus 122 low-voltage units.
  - They were prioritised to "病院や公共施設などの重要施設" (hospitals and important public facilities).
  - Restoration took about 280 h to reach 99%.
  - TEPCO's own review (191031j0201) notes that some sites had "電源車接続時には必要な要員を配備中に復旧" (the grid came back while the connection crew was still being assembled). That is evidence that e for a generator vehicle is often longer than the grid's own restoration.

---

## 2. Fleet sizes (how many units a pool holds)

| Fleet | Figure | Source | Grade |
|---|---|---|---|
| **Taipower mobile substations (移動式變電所)** | **Not found.** Taipower's pre-typhoon releases (MOEA 123257, 8 Jul 2026; udn, 27 Aug 2026) list only staff, vehicles and "各式機具" (equipment of all kinds): 7,316 / 3,325 / 6,634, and 7,215 / 3,338 / 3,902. | MOEA; udn | — |
| US mobile transformers | ~600 in service, against ~45,000 medium-power transformers (about 1.3%) | DOE 2006, Table 4 | L · US |
| One US utility | 3 mobile substations in one district (Versant, Bangor Hydro) | Versant | L · US |
| **TW mobile base-station vehicles** | **≥ 59 across the three carriers** (derived: 28 satellite-equipped vehicles deployed in Danas, plus 31 without satellite to be refitted); Chunghwa Telecom deployed 16. Nine more are planned. | Commercial Times, 4 Aug 2025; CNA, 21 Jul 2025 | L · TW (the sum is derived, and is a floor) |
| US deployable cell sites | AT&T: 450+ portable cell sites and 40+ flying COWs; FirstNet: 72 SatCOLT/COW | AT&T NDR; FirstNet | L · US |
| TW Water emergency generators | 567, plus 62 water trucks | udn, 25 Aug 2026 | L · TW |
| JP generator vehicles in one event | 238 high-voltage (174 from other utilities) plus 122 low-voltage | METI 2019 | L · JP |
| JP emergency bridges | 2 at the Kanto Technical Office | MLIT Kanto | L · JP |

**Pool sizes for the pilot island (about 400 km², J).**
- **Mobile substation: 1.** The US ratio of about 1 mobile per 75 medium transformers, or about 1 per 25 three-transformer substations, gives 0 for a small island. Taipower's practice of resident depots on the outlying islands argues for keeping one. Label it `placeholder (open decision: mobile_substation_pool)`.
- **Cell-on-wheels: 1.** TW has ≥ 59 over 36,197 km², about 1 per 600 km², which gives 0.7 for 400 km². Label it `placeholder (open decision: mobile_cell_pool)`.
- **Temporary bridge kits: 0** in the pilot, because e = 72 h equals the window.

---

## 3. Node substitutes and supply substitutes are different model objects

| | Node substitute (repair mode) | Supply substitute (mobile supplier) |
|---|---|---|
| Examples | mobile substation, cell-on-wheels, temporary bridge | portable generator, generator vehicle, water truck, fuel truck |
| What it restores | the damaged node's own output | an input the node has lost from upstream |
| Where it lives in the model | an alternative mode of the node's repair job | a mobile supplier edge, with its own buffer and resupply (the REVIEW F14 machinery) |
| Literature | Cavdaroglu et al. 2013: components "temporarily installed or repaired" | Lei, Chen, Li & Hou 2019, *IEEE TSG*: co-dispatch of "repair crews (RCs) and mobile power sources (MPSs)"; Su et al. 2023, *IEEE TCNS*: MPS routing with travel and service times |

Putting portable generators inside the repair job would count one physical scarcity in two places: the generator pool and the dependency buffer. It would also make "repair" of a node that is physically intact meaningless. **Recommendation:** leave supply substitutes out of the pilot. The buffers already carry the first 24–72 h (lane_reserves). For the full build, consider them as their own pool (Question 2).

---

## 4. Representing emergency repair in the exact-tier optimisation

### 4.1 Recommendation: two modes of one job, not a sequence, inside a 72 h window

For each damaged node whose class and damage state are eligible (§1), the repair is **one job with two alternative modes**. This is the multi-mode resource-constrained scheduling structure of Talbot (1982, *Management Science* 28(10)).

- **Mode P (permanent).**
  - Lead time ℓ: holds no crew (REVIEW F7).
  - Then crew work w: holds one crew.
  - Restored capacity 1.
  - Fragility back to base.
- **Mode E (emergency).**
  - Road travel from the pool's base, then set-up e: holds one crew and **one unit from the class's pool**.
  - The crew is released at the end of e.
  - The **unit is not released within the horizon**, because it stays until the permanent repair (months, per DOE).
  - Restored capacity c. For a bridge, c is a vector by vehicle class: light and heavy.
  - The node carries a fragility multiplier φ and, if it runs on fuel, a fuel buffer.

**Why modes and not "E, then P":**
1. **P after E never finishes inside the window for an eligible state.** The eligible states are the ones where the Hazus permanent mean is at or above the window: substation moderate 3 d, extensive 7 d; bridge extensive 75 d. A sequence would add a precedence arc and a unit-release event that never fire. That is a complication with no effect on the answer key. This is the "no general frameworks for one use" rule (CLAUDE.md §2).
2. **It keeps brute force exact.** Each eligible node adds one binary mode choice. With at most about 2–3 eligible nodes in the pilot (substations and masts, §0.2), enumeration grows by at most 2³ = 8 times the order count.
3. **The pool is what makes the choice interesting.** With 1 mobile substation and 2 damaged substations, the solver must decide which one gets it. That is a sequencing and allocation decision of the kind the pilot is meant to expose.

**When to switch to a sequence.** If the window is lengthened past about 7 days, or if a second hazard is modelled, P can finish after E. Then use two jobs per node:
- E, and then P with the precedence E → P;
- the unit is released to the pool when P completes;
- capacity steps from c to 1 when P completes;
- φ applies only between E and P.

This is the only form in which a temporary unit's limited lifetime and elevated fragility change an answer key.

### 4.2 Parameters and centres

| Parameter | Centre | Source | Recipe status |
|---|---|---|---|
| e, distribution substation | 18 h (plus road travel) | DOE 12–24 h; Versant 6 h to mobilise | L; the centre is the DOE midpoint (J) |
| c, distribution substation | min(1, 25 MVA ÷ node peak MVA) | DOE nominal 25 MVA | L for 25 MVA; the peak-load basis is J (Question 3) |
| e, mast | 14 h (plus travel) | FirstNet objective | L · US |
| c, mast | 0.5 | none found | `placeholder (open decision: mobile_cell_capacity_fraction)` |
| Fuel life of a generator-powered emergency unit | 8–12 h per fill, centre 10 h | CSRIC IV WG9 | L; model it as a buffer with resupply (REVIEW F14) |
| e, bridge | 72 h | TW 0403; MLIT | L |
| c, bridge (light, heavy) | (0.1, 0) | TW 0403 (derived: single lane, 5 of 24 h) | L/J |
| φ, fragility multiplier on an emergency-repaired node | 1 in the pilot. It is recorded in the manifest and has no effect unless a second hazard is modelled. | TW temporary bridges washed out twice; no quantified rate found | `placeholder (open decision: temporary_fragility_multiplier)`; J |
| Pools | mobile substation 1, mobile cell 1, bridge kit 0 | §2 | placeholders |

Draw e and c with the quantile table (REVIEW F8). The heterogeneity comes from the source ranges: e for substations 6–24 h; c from 25–50 MVA over the node's peak.

### 4.3 Restoration-scheduling literature on temporary versus permanent

- **Cavdaroglu, Hammel, Mitchell, Sharkey & Wallace (2013), *Annals of OR* 203.** "Determine the set of components (or tasks) that will be temporarily installed or repaired". Temporary installation and repair are **alternatives** for a task. That is the mode structure recommended here (abstract only; the full text was not reached).
- **Arif (2026), "Temporary measures for distribution network restoration after natural disasters", *Electric Power Systems Research* 255, 112788.** An MILP that "optimizes the selection and deployment of portable power sources and temporary lines", "integrating portable substations, generators, temporary lines, crew routing, and network reconfiguration". It uses a "two-phase time representation: Day-1 … during active restoration, while Day-2 approximates sustained operation". This is the closest match: temporary measures and repairs are separate decision variables. The abstract and summary were read via WebFetch; the full text is paywalled.
- **Lei, Chen, Li & Hou (2019), *IEEE Transactions on Smart Grid*** (arXiv 1806.07581). Co-optimises repair crews and mobile power sources over the road network. This is the supply-substitute side (§3).
- **Lee, Mitchell & Wallace (2007), *IEEE Trans. SMC-C* 37(6).** An interdependent layered network-flow model of restoration in lower Manhattan. The abstract read via OpenAlex does not mention temporary components, so none is claimed for it here.
- **What I did not find.** No scheduling model was found that repairs the same component first temporarily and then permanently, with an elevated failure rate in between. Two nearby works do not make that distinction:
  - a road crew-scheduling model (Moreno et al. 2024, optimization-online) lists "installing temporary bridges, applying temporary road patches" in its motivation but "treats all repairs identically";
  - the Almeida, Goerlandt & Pelot (2022) review of road repair divides "short and long-term response phases", not temporary and permanent repairs of one component.

  The E-then-P sequence in §4.1 is therefore a modelling choice (J), not something taken from the literature.

---

## 5. Questions for the design side

1. **Does Hazus "restoration" already include temporary measures?** Hazus fits its curves to ATC-13 "social function" restoration, which is function, not rebuild. If the ATC-13 experts counted a mobile substation as restored function, then Hazus P and the E mode overlap. The author's ruling reads Hazus as full, durable restoration. Confirm that reading (not verifiable from MR4).
2. **Supply substitutes** (portable generators, generator vehicles, water and fuel trucks). Should they stay out of the pilot, with buffers carrying the window? Or should they enter the full build as their own pool on the dependency edge (the MPS model)?
3. **Which TW substation does `distribution_substation` represent?** It could be the 161 kV D/S (120–240 MVA, fetched) or the 69/11.4 kV secondary substation (not reached). And is c based on the node's peak load (recommended) or on its nameplate?
4. **Mobile-cell capacity fraction.** No source was found. Accept 0.5 as a placeholder?
5. **Bridge capacity by vehicle class.** Should a temporary bridge restore light traffic only (c_heavy = 0), which cuts trucked fuel? Should the road layer carry a vehicle-class attribute for that?
6. **Mode or sequence.** Accept modes inside a 72 h window, with the sequence form kept for a longer window or a second hazard?
7. **Pool sizes and the pool base.** Mobile substation 1, mobile cell 1 for the pilot? Should they be based at the `crew_base` (REVIEW Q21)?
8. **Exchange.** With no deployment time found for recovery trailers, should the exchange have no emergency mode?

## 6. Searched for and not found

- The **Taipower mobile-substation fleet**. I searched for 移動式變電所, 移動式變電站, 移動變電所, 移動式變壓器 and Taipower mobile substation. Taipower's pages refused connections, and its press releases list only generic equipment counts.
- **Chunghwa Telecom's total fleet** of 行動基地台車. Only event deployments were found (16 vehicles). Its 2024 statements on the Legislative Yuan deployment give no fleet size.
- Deployment time for **Taiwan Water's portable generators** and mobile treatment units in a disaster.
- **Cell-on-wheels capacity** compared with a macro site.
- **Central-office recovery-trailer** set-up times.
- **Seaport emergency-berth** timing (Kobe: only the permanent figures).
- A quantified **failure rate for temporary repairs** (only TW washout anecdotes for bridges, and Puerto Rico's re-failed lines).

## Sources (fetched this session unless marked)

- DOE, *Benefits of Using Mobile Transformers and Mobile Substations for Rapidly Restoring Electrical Service*, report to Congress under EPAct 2005 §1816, Aug 2006: https://www.energy.gov/oe/articles/benefits-using-mobile-transformers-and-mobile-substations-rapidly-restoring-electrical (PDF; local `emerg/doe_mts.pdf`, `doe_mts.txt`)
- Versant Power, "Introducing Versant Power's new mobile substation": https://www.versantpower.com/about/news-press-releases/blog-details/introducing-versant-power-s-new-mobile-substation
- DHS S&T, *RecX – Emergency Spare Transformer Strategy*: https://www.dhs.gov/sites/default/files/publications/RecX%20-%20Emergency%20Spare%20Transformer%20Strategy-508.pdf
- DOE, *Large Power Transformers and the U.S. Electric Grid*, 2012 (lead times 5–16 months): https://www.energy.gov/sites/prod/files/Large%20Power%20Transformer%20Study%20-%20June%202012_0.pdf
- Delta Star, DOE RFI submission (mobiles "in use in a matter of hours"): https://www.energy.gov/sites/prod/files/2015/09/f26/Delta%20Star_Submission_RFI_Transformer%20Reserve.pdf
- Taipower, 超高壓及一次變電所供電能力資訊 (2023): https://www.taipower.com.tw/_upload/358/2024020109512789563.pdf
- GE Vernova, TM2500: https://www.gevernova.com/gas-power/products/gas-turbines/tm2500 ; Turbomachinery Magazine, APR Energy in Puerto Rico: https://www.turbomachinerymag.com/view/apr-energy-helps-to-restore-critically-needed-power-in-puerto-rico
- Kwasinski et al. 2019, *IEEE PETS Journal* (local `repair/kwasinski.txt`; as lane_repair)
- FirstNet Authority, *Understanding the FirstNet Deployable Program*: https://www.firstnet.gov/sites/default/files/FirstNet_Deployables.pdf
- AT&T NDR infographic: https://about.att.com/ecms/dam/pages/disaster-recovery/network-recovery/network-disaster-recovery-infographic.pdf ; NDR brochure 2019: https://about.att.com/ecms/dam/pages/disaster_relief/NDR_edited_04.22.19.pdf
- CNA, 21 Jul 2025 (Danas, three carriers): https://www.cna.com.tw/news/ahel/202507210313.aspx ; CNA, 4 Aug 2025: https://www.cna.com.tw/news/afe/202508040028.aspx ; Commercial Times, 4 Aug 2025 (MODA): https://www.ctee.com.tw/news/20250804701545-430104
- Chunghwa Telecom, Koinu release, 12 Oct 2023: https://www.cht.com.tw/zh-tw/home/cht/messages/2023/1012-1010 ; statement, 3 Jun 2024: https://www.cht.com.tw/zh-tw/home/cht/messages/2024/0603-1810
- CSRIC IV WG9 (via `deptable/lane_fuel.md` S7); EPA 800-R-19-001 (local `epapwr.txt`; lane_fuel S13)
- Taiwan Water Corporation pre-typhoon release, udn, 25 Aug 2026: https://money.udn.com/money/story/7307/9713488 ; China Times, 23 May 2021: https://www.chinatimes.com/realtimenews/20210523001628-260405
- MOEA (Taipower), 8 Jul 2026: https://www.moea.gov.tw/MNS/populace/news/News.aspx?kind=1&menu_id=40&news_id=123257 ; udn, 27 Aug 2026: https://udn.com/news/story/7266/9717167
- Commercial Times: Xiaqingshui, 20 May 2024: https://www.ctee.com.tw/news/20240520700756-431401 and 20 Dec 2024: https://www.ctee.com.tw/news/20241220701052-431401 ; Mingbakelu, 27 Jul 2024: https://www.ctee.com.tw/news/20240727700499-431401 ; Lushan temporary bridge, 5 Oct 2023: https://www.ctee.com.tw/news/20231005701057-431401 ; udn, Mataian Creek: https://money.udn.com/money/story/7307/9239020
- MLIT Kinki (Fukui), 応急組立橋: https://www.kkr.mlit.go.jp/fukui/bousai/kuruma/saigai/oukyu.html ; MLIT Kanto Technical Office report: https://www.ktr.mlit.go.jp/ktr_content/content/000105737.pdf
- Air Cargo News, Sep 2018: https://www.aircargonews.net/airlines/2018/09/kansai-airport-set-to-re-open-to-domestic-flights-after-devastating-typhoon/ ; Japan Times, 21 Sep 2018: https://www.japantimes.co.jp/news/2018/09/21/national/kansai-airport-bounces-back-typhoon-kobe-itami-likely-help-anyway/ ; nippon.com: https://www.nippon.com/en/features/h00284/
- PreventionWeb, Kobe 1995: https://www.preventionweb.net/news/1995-kobe-earthquake-reflecting-past-lessons-and-assessing-modern-resilience ; NZSEE bulletin, Kobe transport restoration: https://bulletin.nzsee.org.nz/article/download/618/595
- METI Chubu, Noto fuel supply: https://www.chubu.meti.go.jp/d51sekiyu/press_2024/20250121/20250205_1_saigaizinennryoukyoukyuugaiyo.pdf ; DoD Sandy update: https://content.govdelivery.com/accounts/USDOD/bulletins/5abd04
- FEMA, KPF6 §2.2, Federal Medical Stations: https://www.fema.gov/cbrn-tools/key-planning-factors-chemical-incident/kpf6/2/2-2 ; US Army, Puerto Rico power mission: https://www.army.mil/article/196385/power_mission_in_puerto_rico_set_to_be_largest_ever_in_us
- METI Resilience WG, Faxai: https://www.meti.go.jp/shingikai/enecho/denryoku_gas/denryoku_gas/resilience_wg/pdf/005_04_00.pdf ; TEPCO, 31 Oct 2019: https://www.tepco.co.jp/press/release/2019/pdf4/191031j0201.pdf
- Hazus-MH MR4 Tables 7.4/7.5, 8.22.a/b, 8.30.a/b (local `repair/hazus_mr4.txt`)
- Cavdaroglu et al. 2013: https://link.springer.com/article/10.1007/s10479-011-0959-3 ; Arif 2026: https://www.sciencedirect.com/science/article/abs/pii/S0378779626000817 ; Lei et al. 2019: https://arxiv.org/abs/1806.07581 ; Su et al. 2023: https://par.nsf.gov/servlets/purl/10425425 ; Lee, Mitchell & Wallace 2007 (abstract via OpenAlex, doi:10.1109/TSMCC.2007.905859); Talbot 1982, doi:10.1287/mnsc.28.10.1197 (bibliographic record via OpenAlex); Moreno et al. 2024: https://optimization-online.org/wp-content/uploads/2024/01/MorenoEtAl2024oo.pdf ; Almeida, Goerlandt & Pelot 2022: https://www.sciencedirect.com/science/article/abs/pii/S0038012122001926

---

<!-- file: lane_tolerance.md -->
# Lane: TOLERANCE BUFFER for telecom loss

**The ruling this lane serves.** Losing telecom is not an instant total failure. A facility that loses telecom keeps full function on manual or local fallback for a **tolerance period T** (hours). If telecom is still not back, it then drops to a **degraded level d**, a fraction of normal function. No stock is involved, so this is not a reserve.

Appendix B: "the dependent runs degraded, losing visibility and coordination first and failing only as unhandled faults accumulate — near-zero at air traffic control, long at ports and rail on manual fallback."

**Conventions**
- Grades follow the brief: **S** standard, code or regulation; **L** literature or a government report; **J** judgment.
- **L-an** marks an **IT-system analogue**, per review F10. Examples are EHR downtime, ransomware and CrowdStrike. These show how a facility behaves once its systems go down. They do not show what an outside-carrier outage takes down.
- Jurisdiction is marked [US], [TW], [CA] or [JP].
- Every source was fetched this session (2026-09-29). Sources carried over from `deptable/lane_telecom.md` keep their S-keys and the review's verdict. New sources are keyed T1 onward.

---

## 0. Mechanism (recommended)

**Step (default).** Let t be the hours since the facility's last telecom edge was lost. Then:

```
s(t) = 1         for t < T
s(t) = d_eff     for t ≥ T
```

**Linear ramp (optional).** Hospitals only (see §2). W is the ramp width in hours; W = 0 gives the step:

```
s(t) = 1 − (1 − d_eff) · min(1, (t − T) / W)     for t ≥ T
```

**Public share (question 4 of the brief; see §3):**

```
d_eff = 1 − κ · (1 − d)
```

Here κ is the edge's public-telecom share (1 where ruling R1 does not apply). T is **not** scaled.

This uses only +, −, ×, ÷ and min, with no exponential. It replaces the class-free floors in `targets/REVIEW.md` row 11 (control 0.5, service 0.7, both J) with per-class values.

**Restoration.** When telecom returns, s returns to 1 at once. The step form is not symmetric. A backlog after recovery, such as data re-entry, is ignored. ASPR gives it as "If our EHR was down for 4 hours, staff get 8 hours to put the data into the EHR" [T9]. `# CHOICE-candidate:` ignore the backlog in Phase 1.

---

## 1. Recommended table

T is the tolerance in hours. d is the degraded fraction, before the public share is applied. Where a range is given, the centre is the value in bold.

| Class | Type (dep. table) | T centre (range) | T grade | d centre (range) | d grade | What drives the step down |
|---|---|---|---|---|---|---|
| generation | control | **4 h** (1–12) | L [US] for the lower bound; J for the centre | **0.8** (0.6–0.95) | J | The plant holds its last setpoint under local control, but AGC and dispatch are lost, so it cannot follow load or respond to frequency. |
| transmission_substation | control | **12 h** (4–24) | L [US] (censored) | **0.9** (0.8–1.0) | J | The site is staffed on callout and switches by hand, with flows reported verbally. Faults are handled slowly, and protection misoperations become possible. |
| distribution_substation | control | **12 h** (4–24) | J | **0.85** (0.7–0.95) | J | Remote switching and feeder automation (DDCC) are lost. In steady state the load is still served. After a fault, isolation and restoration need a truck roll. |
| treatment (water) | control | **24 h** (8–72) | J (L-an [US]: no loss of service on manual) | **0.9** (0.8–1.0) | J | Process control is local and staffed. The plant loses set-points and alarms from the system and coordination with pumps and tanks. |
| pumping (water) | control | **12 h** (4–48) | J | **0.8** (0.6–0.9) | J | Unmanned stations fall back to local float or pressure logic. They are invisible to the control room, and tanks drain or overflow until staff start roving. |
| reservoir | control (optional row) | **72 h** (24–168) | J | **0.95** (0.9–1.0) | J | Gravity flow continues. Only remote gate and dam telemetry is lost. |
| airport, towered | control | **0 h** (0–0.1) | L [US] | **0.2** (0–0.5) | J | ATC voice and radar circuits are lost, which brings ground stops within minutes. Afterwards only procedural or visual operation is possible. |
| airport, untowered | service (optional row) | **24 h** (8–72) | J | **0.9** (0.8–1.0) | J | Flight-plan filing, NOTAMs and fuel card payment are lost. Visual operations continue. |
| seaport | service | **24 h** (4–48) | J | **0.5** (0.3–0.7) | L-an [US] | Manual gate processing on paper. Customs and EDI release is lost, trucks queue, and throughput falls. |
| freight_yard | service | **24 h** (8–72) | J | **0.6** (0.4–0.8) | J | Phone and paper dispatch, with manual documents. |
| refinery | service | **72 h** (24–168) | J | **0.8** (0.6–0.9) | J | The process runs on its own site control system. Pipeline nominations and scheduling of crude and product movements are lost. |
| tank_farm, pipeline-connected | control | **1 h** (0–4) | L-an [US] + S [US] | **0.5** (0.2–0.8) | L-an [US] / J | The pipeline control room loses SCADA. The trunk line stops or runs only on manually operated local lines, while the truck rack keeps loading by hand. |
| tank_farm, truck/rail only | service (optional row) | **24 h** (8–72) | J | **0.8** (0.6–0.9) | J | Manual bills of lading. Remote tank gauging is lost. |
| import_terminal | control | **2 h** (0.5–8) | J | **0.7** (0.5–0.9) | J | Send-out continues on the terminal's own control system. Nominations and coordination with the grid or pipeline control room move to voice or radio fallback. |
| depot | service | **12 h** (4–48) | J (L-an [CA] for payments) | **0.6** (0.4–0.8) | J | Manual loading authorisation. Card and fleet authorisation is lost. |
| tertiary, EHR on site | service (R6) | **24 h** (4–24) | S [TW] + L [CA] | **0.85** (0.7–0.95) | L [CA] / J | NHI VPN and card checks fall back to exception codes. Paging, outside phones, virtual care and staff call-in are lost. The EHR itself keeps running. |
| tertiary, EHR hosted off site | service (R6) | **0.5 h** (0.5–4) | L [US] (hospital policy) | **0.65** (0.55–0.8) | L-an [US] | Paper downtime procedures. Lab turnaround slows about 62%, elective work is cancelled, and the ED stays open. |
| regional, on site / hosted | service | same as tertiary | same | same | same | Same mechanism. The hosted share is higher (dependency table C3). |
| clinic, EHR on site | service | **24 h** (8–24) | S [TW] | **0.8** (0.6–0.9) | J | Patients are seen under NHI exception codes, with upload within 24 h. E-prescribing and MediCloud queries are lost. |
| clinic, EHR hosted | service | **0.5 h** (0.5–4) | L [US] | **0.6** (0.4–0.8) | L-an [US] / J | Paper charts. Non-urgent visits are cancelled. |
| blood_bank | service | **24 h** (8–48) | J | **0.5** (0.3–0.7) | L-an [US] | Manual labelling, which "take[s] significantly longer". Distribution slows. The shelf inventory at hospitals is a separate reserve. |

**Where "near-zero tolerance" is justified.** It is justified only at the **towered airport** (and any radar-served approach). It is **not** justified for pipeline-connected tank farms, where T ≈ 1 h is short but not zero: a controller's stop order takes about an hour to complete, and some local lines return to manual within hours.

No other class has evidence for T below about 30 minutes. For hosted-EHR hospitals, the policy's 30-minute trigger is the earliest scripted step.

**Choosing between step and ramp.**
- Use the step for every class.
- The ramp is recommended only for tertiary and regional hospitals, where the evidence has tiers (§2): T = 0.5 h, W = 3.5 h, with d reached at 4 h. This applies to hosted EHR only.
- For an on-site EHR, a single step at 24 h is enough.

---

## 2. Evidence by class

### Power
- **NERC EMS-loss statistics [T1] (L [US]).** "There were 263 EMS events reported between 2019 and 2023 … approximately 73 minutes in duration on average." Also: "the loss of EMS functions did not lead to the loss of generators, transmission lines, or customer load."
  - The mitigation it names is "Manning substations during EMS events so that system operators and field personnel can take actions as needed (e.g., open/close breakers)". It also reports that PRASE volunteer entities "would remain capable of executing their restoration plan without SCADA/EMS availability."
  - *Caveat (review Check 7):* most of these EMS losses were internal, not carrier failures. What the source supports is the lower bound on T: operators run the system for hours without SCADA and lose no load.
- **Carrier-caused SCADA loss, NERC Lesson Learned LL20180801 [T2] (L [US]).** This is the direct telecom evidence.
  - Cause: "The TelCo experienced a major network outage … multiple hardware failures within the TelCo's network." Most of the utility's substations lost data circuits.
  - Response: the company "initiated callouts to staff key Bulk Electric System (BES) substations".
  - Duration: "Approximately eight hours after the event first occurred, the TelCo reported that all network issues had been resolved".
  - No loss of load is reported (the document is silent). The event ran **8 h with the system held on staffed fallback**.
- **Fibre failure, NERC LL20231101 [T3] (L [US]).** Communications were "interrupted for 11 hours and 30 minutes". "Field personnel were dispatched to staff all remote transmission substations" and flows were obtained "verbally". One 230 kV line tripped through a relay misconfiguration during signal degradation.
  - This is the first recorded degradation: **after hours, not at once**. The cause was internal fibre, not a carrier.
- **Why T = 12 h for transmission.** Both long events (8 h and 11.5 h) ended while the system was still holding, so they are right-censored lower bounds on T. 12 h is the upper observed value. It is not a demonstrated limit.
  - In a storm, the same crews are needed for repair, which argues against going longer (J).
- **Generation.** No carrier-specific event was found. The T = 4 h centre is J. It rests on the 73-minute mean with zero loss of generation [T1], and on the fact that a plant at its last setpoint cannot follow load for long.
  - Taipower's plants are on its own fibre (review Check 10), so under R1 κ is small and d_eff stays close to 1 whatever d is.
- **Distribution.** There is no event source, so this is J. The DDCC covers "automated switches, and devices within substation" (S13, review Check 9, confirmed).
  - In steady state a distribution substation without SCADA still serves load, since many US rural ones have none. The loss shows up only when a fault needs switching.
  - `Q-T1` asks whether d should apply to supply or to switching or repair time.

### Water
- **Treatment.** The EPA incident checklist [T4] (L [US]) calls for training "Include the manual operation of water collection, storage, treatment and conveyance systems" and "switch to manual operation if necessary". It gives no durations.
  - Arkansas City, KS, Sept 2024 [T5] (L-an [US], cyber) "switched to manual operations"; "there has been no disruption to service". The duration was not reported.
  - The centre T = 24 h is J. It stands for one staffed shift cycle before the lost coordination with remote sites begins to bite.
- **Pumping.** The mechanism is in the dependency table (S4). No duration source was found, so it is J.
- **Taiwan.** No Taiwan Water Corporation source was found.

### Airport
- **Towered airport (L [US]).**
  - Newark, 28 April 2025: controllers "temporarily los[t] radar and communications"; the loss lasted "about 30 seconds", plus "30 to 60 seconds for aircraft to reappear". The FAA "issued several ground delays and ground stops" [T6].
  - 9 May 2025: "lost communications and radar … about 90 seconds … due to a telecommunications outage", traced to "antiquated copper telecommunications wiring connecting radar data to the Philadelphia TRACON" [T7].
  - A 30–90 second loss produced ground stops, which gives **T ≈ 0**.
- **The degraded level d = 0.2 is J.**
  - Chicago 2014 [T8]: O'Hare had "more than 80 percent", and Midway "90 percent", of normal volume back by day 3. That recovery came from re-routing control to neighbouring facilities, which in the model is a second telecom edge, not tolerance.
  - The same holds for the FAA target of "90 percent capacity at the top 30 airports … within 24 hours" (DOT OIG, S6; the fetch this session confirmed the quote).
  - With no telecom path at all, only non-radar or visual operation remains. I found no source giving its rate as a fraction.
  - The EWR cap of 28 + 28 against a baseline of 77 operations per hour [T10] reflects runway construction plus the equipment problems, so it is not usable as d.
- **Taiwan:** not found (same gap as the dependency table).

### Seaport and freight yard
- Every source found is an **IT analogue** (F10). No outage caused by an outside carrier stopping a port was found.
- **APM Terminals, NotPetya 2017 [T11] (L-an [US]).** The terminal was "fully closed June 27-29" and "reopened June 30, but only partially and manually". It "remained in manual mode until July 6", when "approximately 70% of our gate facility with technology" returned. On manual: "At least 2,500 trucks a day were backed up".
  - This supports d of about 0.3–0.7 on paper. No throughput figure was given for the manual days, so the centre 0.5 is J inside an L-an range.
- **DP World Australia 2023 [T12]** was halted from 10 to 13 November with "30,000 shipping containers" in backlog. **Nagoya 2023 [T13]** suspended "all cargo operations" from 4 to 6 July.
  - Both show that d → 0 **when the terminal operating system itself is down**. An outside telecom loss leaves an on-site TOS running and cuts customs, EDI and gate appointments. That is why T is set at 24 h and d at 0.5, not 0.
  - The Kramek wording is corrected per review Check 22 and is not used for durations.

### Fuel
- **Pipeline-connected tank farm.**
  - 49 CFR 195.446 requires "adequate means for manual operation of the pipeline safely" (S11, review Check 27, confirmed) (S [US]). The rule sets the fallback, not a duration.
  - Colonial Pipeline, May 2021 [T14] (L-an [US]; the IT network was attacked, and OT was shut as a precaution): "At approximately 5:55 AM EDT, employees began the shutdown process. By 6:10 AM EDT … all 5,500 miles of pipelines had been shut down"; "within hours … were able to return some of our local lines to manual operation". The restart came on 12 May, about 5 days later.
  - This gives T ≈ 1 h (the ransom note was found "just before 5:00 AM"). The trunk line went to 0 with partial manual local lines. The tank farm's own truck rack does not depend on SCADA, so d = 0.5 is J.
- **Import terminal, refinery and depot.** No outage source was found; these are J.
  - The depot's payment loss has a partial analogue in Rogers 2022: "Businesses … were not able to process transactions made by debit cards, e-transfers and some credit cards" [T15] (L [CA]).
  - CPC terminal automation was not found.

### Healthcare
- **Downtime tiers found**, from one hospital's policy (Stony Brook Medicine, STARS/PowerChart downtime procedure, revised Aug 2022) [T16] (L [US]):

  | Threshold | Policy text |
  |---|---|
  | 30 min | "The process for activating the Read Only Database will begin after 30 minutes of downtime." |
  | 1 h | "If the problem is not resolved within one hour, the brief outage recording … will be replaced with extended outage recording." |
  | 2 h | The read-only database is activated for "an expected duration of 2 hours or greater". |
  | 4 h | "If the downtime is greater than 4 hours (extended downtimes) surgical secretary will do scheduling." |
  | 24 h | "Scheduling during a downtime of 24 hours or more will be handled by Central Scheduling by manually scheduling future appointments." |

- **ONC SAFER Guide 2, Contingency Planning (2025) [T17] (L [US], federal self-assessment guidance, not a rule):**
  - The warm-site switch should come "ideally before the system has been unavailable due to unplanned activities for 2 hours". Downtimes "lasting over 24 hours" get an in-depth review.
  - For small practices: "at least a cellphone-based, wireless Internet access point that is capable of running a cloud-hosted EHR as a backup". In the model this is a second (mast) edge, not tolerance.
- **These tiers give the hosted-EHR ramp:** T = 0.5 h (the scripted fallback starts), with d reached at 4 h ("extended downtime").

- **The degraded level for hosted EHR (L-an [US]):**
  - The lab-result delay is "an average of 62%" (ASPR TRACIE, S16; the review traces it to Larsen 2019, *ACI*). A 62% delay gives lab throughput of 1 ÷ 1.62 = 0.62, so centre d = 0.65.
  - CrowdStrike, 19 July 2024 [T18]: Mass General Brigham "canceled all non-urgent medical visits"; "emergency rooms remain open". This fits d well above 0 and well below 1.
- **On-site EHR against an outside-carrier outage.** The best direct telecom evidence is the Rogers outage of **8 July 2022**. The brief's "2021" is a slip: April 2021 was an earlier, smaller Rogers outage [T15].
  - Duration: "approximately 15 – 19 hours with some services and customers remaining unconnected up to 4 days" [T19] (L [CA]).
  - Hospitals reported "technical challenges with hospital communication networks and the cancellation of virtual medical appointments" [T19].
  - Hamilton Health Sciences: "Patient care continues", because "most HHS systems are with Bell" [T20].
  - Southlake Regional: staff could not call in sick; it opened a "24-hour command centre" and "implemented downtime procedures" [T21].
  - Result: full care for about 15–19 h, with coordination and staffing losses rather than clinical ones. Hence T = 24 h and d = 0.85 (J centre in an L-supported direction).
  - Carrier diversity (Bell as well as Rogers) is two edges, which is redundancy by edge count (targets review row 10).
- **Taiwan NHI exception procedure [T22] (S [TW]).** The NHIA's report form lists "網路故障造成讀卡機無法使用" (network failure prevents use of the card reader) and "醫療資訊系統(HIS)當機" (HIS crash) as recognised abnormal conditions, with "24 小時內上傳就醫資料" (upload visit data within 24 hours).
  - A clinic guidance page [T23] states that patients are still seen: "請以異常代碼代替患者健保卡之就醫序號" (use an exception code in place of the NHI card's visit number), and this "不影響醫療院所申報權益" (does not affect the facility's claim rights).
  - This is the only **S-grade** tolerance found in any class. It supports T = 24 h for clinics and on-site-EHR hospitals in a Taiwan-like world.
- **Hurricane Maria [T24] (L [US]):** the Puerto Rico Hospital Association testified to "a communication breakdown between its hospitals, doctors, and service providers" and that "Cayey had no way of communicating with the outside world for three months". This is confounded with power, roads and fuel, so it is not usable for T or d. It confirms only that hospitals kept operating through long telecom loss.
- **Blood bank.** OneBlood 2024 (ransomware) [T25] (L-an [US]): "operating at a significantly reduced capacity"; "Manual processes take significantly longer to perform and impacts inventory availability". Over 250 hospitals were asked to activate critical shortage protocols. No number was given, so d = 0.5 is J inside the L-an direction.

### Taiwan telecom outages (Matsu, February 2023)
- The cables were cut on 2 and 8 February 2023. Access was limited for about 50 days, to 31 March [T26].
- Chunghwa Telecom's microwave backup carried "語音通話、政府國安與民生等電路 … 不受影響" (voice, government and security, and essential civil circuits were unaffected), while "行動及寬頻上網 … 會有網路壅塞" (mobile and broadband data would be congested) [T27].
- Capacity went from 2.2 Gbps at first, against 8–9 Gbps normal use, to 10.6 Gbps by 25 December 2023 [T26, T28]. "Preferential bandwidth access" went to "government agencies, military units, hospitals" [T26].
- **I found no report of the effect on Matsu's hospital, banks or port**, in English or Chinese; I searched for 連江縣立醫院 (the county hospital), 健保 (NHI), 郵局 (post office), 提款 (cash withdrawal) and 刷卡 (card payment).
- What Matsu shows for the model: in a real Taiwan cable cut, loss was **partial and prioritised**, not binary. In the model that is a second (microwave) edge with priority, not a tolerance.

---

## 3. Does the public telecom share scale T or d? (brief item 4)

**Recommendation: scale d only, as `d_eff = 1 − κ(1 − d)`. Leave T unscaled.**

- **T is a property of the fallback procedure:** how long staff can run a substation or pump station by hand before faults pile up. It does not depend on what share of the signal path was public. The NERC events [T2, T3] held for 8–11.5 h regardless of the carrier.
- **The private share keeps its part of the function.** Under R1(a) the private remainder belongs to the consumer's own layer and survives a public-telecom strike. The unserved part of the function is therefore at most κ, and the depth of the step is κ(1 − d).
- **The public share should enter once only.** If κ also enters the supply margin (targets review row 10), then with a binary requirement the edge can only be served or unserved. κ should appear in the step depth, **not** also as a partial requirement. Otherwise it is counted twice. This is `Q-T2`.
- **Worked example (illustrative only):**
  - Taipower transmission, κ = 0.2 (placeholder low, R1): d_eff = 1 − 0.2 × 0.1 = **0.98**.
  - Hosted-EHR hospital, κ = 1: d_eff = **0.65**.
- **The alternative, scaling T by 1 ÷ κ, is rejected.** It makes T infinite at κ = 0 and has no mechanism behind it.

---

## 4. Choices and questions

`# CHOICE-candidate:` entries (for the design side):
1. A step by default, and a linear ramp only for hosted-EHR hospitals.
2. Restoration returns s to 1 at once, and the re-entry backlog is ignored.
3. On-site against hosted EHR switches T and d (dependency-table attribute C3 and R9 "records hosted off site").
4. The public share scales the step depth, not T.

Questions:
- **Q-T1.** For substations, does d reduce *supply* or *switching and repair speed*? The evidence says steady-state supply is untouched, and the loss is in fault handling. If the answer is repair speed, T and d here should become a switching-delay multiplier in the repair lane. Both options would be linear.
- **Q-T2.** Confirm that κ enters only as the step depth (§3) and not also as a partial telecom requirement.
- **Q-T3.** Towered airport: d = 0.2 is J. Should the model treat "ATC re-routed to a neighbour facility" as a second telecom edge? That would be consistent with redundancy by edge count, and it is how the 80–90% recoveries were achieved [T8, S6].
- **Q-T4.** Manual fallback needs staff to reach the sites. In a compound storm with roads cut, T is optimistic. Ruling R8 puts staff access out of scope. Should the report state this as a known optimism?
- **Q-T5.** The dependency table sets telecom → storage to none (F17). This lane gives no row for storage. Confirm.

**Not found (what I looked for):**
- Taiwan: Taipower rules on staffing substations when SCADA is lost (台電 變電所 無人化 遙控); Taiwan Water SCADA fallback; CAA/ANWS ATC contingency.
- Matsu effects on the hospital, banks or port.
- Any outside-carrier outage at a port, freight yard, depot, refinery or LNG terminal.
- The non-radar arrival rate as a fraction of radar rate.
- BJC's Epic downtime tiers (the fetch was blocked).
- The TTUHSC clinic policy (404).

---

## Sources

Carried over from `deptable/lane_telecom.md`, with the review's verdicts:
- **S6** DOT OIG AV2017020. Re-fetched this session; the 90% / 24 h target and the Chicago and Austin quotes were confirmed.
- **S11** 49 CFR 195.446 (confirmed).
- **S13** Taipower DDCC (DDCC confirmed; ADCC wrong).
- **S16** ASPR TRACIE (the 62% figure confirmed; it comes from Larsen 2019, *ACI*).
- Review Check 10: 台電月刊 (Taipower monthly) Vol. 700, on Taipower's own fibre.

New:
- **T1** NERC RSTC, *Risks and Mitigations for Losing EMS Functions Reference Document*, v4, 2024. https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/emswg/risks_mitigations_losing_ems_functions_refdoc.pdf
- **T2** NERC Lesson Learned LL20180801, *Loss of Substation Data Circuits to SCADA*. https://www.nerc.com/globalassets/programs/event-analysis/lessons-learned/ll20180801_loss_of_substation_data_circuits_to_scada.pdf
- **T3** NERC Lesson Learned LL20231101, *Loss of Communication to Transmission Substations*. https://www.nerc.com/globalassets/programs/event-analysis/lessons-learned/ll20231101_loss_of_communication_to_transmission_substations.pdf
- **T4** US EPA, *Incident Action Checklist: Cybersecurity*, 2017. https://www.epa.gov/sites/default/files/2017-11/documents/171013-incidentactionchecklist-cybersecurity_form_508c.pdf
- **T5** SecurityWeek, "Kansas Water Facility Switches to Manual Operations Following Cyberattack", Sept 2024. https://www.securityweek.com/kansas-water-facility-switches-to-manual-operations-following-cyberattack/
- **T6** CBS News, "What's causing delays at Newark airport?", 2025. https://www.cbsnews.com/news/newark-airport-delays-ground-stops-equipment-issues/
- **T7** *Flying*, "Newark Airport Suffers Another 90-Second Radar Outage", May 2025. https://www.flyingmag.com/newark-airport-suffers-another-90-second-radar-outage/
- **T8** AOPA, "Chicago-area ops recovering", 30 Sept 2014. https://www.aopa.org/news-and-media/all-news/2014/september/30/chicago-fire
- **T9** ASPR TRACIE, *Paper-Based Hospital Records* TA response, 2017. https://files.asprtracie.hhs.gov/documents/aspr-tracie-ta-paper-based-hospital-records-073117-508.pdf
- **T10** FAA, *Operating Limitations at Newark Liberty International Airport: Interim Order*, Federal Register, 23 May 2025. https://www.federalregister.gov/documents/2025/05/23/2025-09376/operating-limitations-at-newark-liberty-international-airport-interim-order-establishing-targeted
- **T11** Transport Topics, "APM Terminal Cyber Attack Costs Drivers Time, Wages", 2017. https://www.ttnews.com/articles/apm-terminal-cyber-attack-costs-drivers-time-wages
- **T12** Transport Topics, "Australia Cyberattack Leaves 30,000 Containers Stuck at Ports", Nov 2023. https://www.ttnews.com/articles/australia-cyberattack-ports
- **T13** SecurityWeek, "Japan's Nagoya Port Suspends Cargo Operations Following Ransomware Attack", July 2023. https://www.securityweek.com/japans-nagoya-port-suspends-cargo-operations-following-ransomware-attack/
- **T14** J. Blount (Colonial Pipeline), testimony to the Senate HSGAC, 8 June 2021. https://www.hsgac.senate.gov/wp-content/uploads/imo/media/doc/Testimony-Blount-2021-06-08.pdf
- **T15** Wikipedia, "2022 Rogers Communications outage" (used for the date, the April 2021 precedent and the Interac loss; secondary). https://en.wikipedia.org/wiki/2022_Rogers_Communications_outage
- **T16** Stony Brook Medicine, *STARS/PowerChart Downtime Procedures for Inpatient/Outpatient*, rev. Aug 2022. https://extranet.stonybrookmedicine.edu/sites/default/files/DowntimeProcedure-UpdatedApril2023.pdf
- **T17** ONC, *SAFER Guide 2: Contingency Planning*, 2025. https://www.healthit.gov/wp-content/uploads/2025/06/SAFER-Guide-2.-Contingency-Planning-Final.pdf
- **T18** Fierce Healthcare, "Global IT outage takes down health system EHRs …", 19 July 2024. https://www.fiercehealthcare.com/health-tech/global-it-outage-takes-down-health-system-ehrs-forces-hospitals-cancel-non-emergency
- **T19** City of Toronto, *Attachment 3: Rogers Communications July 2022 Outage Impact*, 2023. https://www.toronto.ca/legdocs/mmis/2023/ex/bgrd/backgroundfile-239381.pdf
- **T20** Hamilton Health Sciences, "Most HHS systems not impacted by Rogers service disruption", July 2022. https://www.hamiltonhealthsciences.ca/share/most-hhs-systems-not-impacted-by-rogers-service-disruption/
- **T21** NewmarketToday, "Rogers outage impacted emergency services, highlighted gaps", 2022. https://www.newmarkettoday.ca/local-news/rogers-outage-impacted-emergency-services-highlighted-gaps-5590376
- **T22** 衛生福利部中央健康保險署 (NHIA), 健保卡作業異常狀況報備單 (NHI card abnormal-condition report form), rev. 112-07 (July 2023). https://www.nhi.gov.tw/ch/dl-12938-aa60b91d203c49678f62b02093dc48b4-1.pdf
- **T23** Clinic guidance page, 當無法正常使用健保卡 (when the NHI card cannot be used; secondary, restating NHIA practice). https://www.sc-dr.com.tw/content-detail.php?type=4&id=1446
- **T24** J. Plá-Cortés, Puerto Rico Hospital Association, FCC field hearing testimony, 21 Feb 2020. https://www.fcc.gov/sites/default/files/puerto-rico-hearing-02212020-pla-cortes.pdf
- **T25** The Record, "Ransomware attack on major US blood center prompts hundreds of hospitals to …", July 2024. https://therecord.media/ransomware-attack-blood-center-shortage-protocols-hospitals
- **T26** *The Diplomat*, "After Chinese Vessels Cut Matsu Internet Cables, Taiwan Shows Its Communications Resilience", April 2023. https://thediplomat.com/2023/04/after-chinese-vessels-cut-matsu-internet-cables-taiwan-shows-its-communications-resilience/
- **T27** 中華電信 (Chunghwa Telecom), 台馬第三海纜中斷，中華電信啟動微波備援 (Taiwan–Matsu cable No. 3 cut; Chunghwa activates microwave backup), 8 Feb 2023. https://www.cht.com.tw/zh-tw/home/cht/messages/2023/0208-1530
- **T28** 馬祖日報 (Matsu Daily), 2023 年度回顧：112 年台馬斷纜 (2023 year in review: the 2023 Taiwan–Matsu cable cuts). https://www.matsu-news.gov.tw/news/article/217731

---

<!-- file: REVIEW2.md -->
# Independent review 2: emergency repair and telecom tolerance lanes

Date: 2026-09-29. Scope: `lane_emergency_repair.md` (ER) and `lane_tolerance.md` (TOL), read against BRIEF.md, REVIEW.md (the earlier review, cited as R1-F*, R1-Q*) and the Hazus MR4 text in `repair/hazus_mr4.txt`. Severity: **C** changes an answer key or a ruling; **M** changes a target or a grade; **m** a wording, citation or tidiness fix. Reviewer's own fetches are in `scratchpad/rv2/`.

---

## 1. Source checks

17 sources checked (10 required plus 7). 11 confirmed as used; 5 confirmed in the quote but overstated or misread in use; 1 wrong attribution; none unreachable; none fabricated.

| # | Claim (lane) | Source and how checked | Verbatim found | Verdict |
|---|---|---|---|---|
| 1 | Mobile substation 12–24 h; "up to 6 months"; nominal 25 MVA; 500–600 units; Dyersburg (ER §1.1) | DOE 2006 EPAct §1816 report, local `emerg/doe_mts.txt` l.127, 500–503, 472, 653, 666 | "their deployment capability (roughly 12 to 24 hours) is a major advantage"; "mobile systems were used for transformer failure replacements (up to 6 months)"; Table 3 low 5 / nominal 25 / high 100 MVA; "roughly 500 to 600 mobile transformers in service"; Dyersburg "completely destroyed … Service was restored using a mobile transformer". Same page: "large-utility-class transformers require a 6-month to 1-year lead time". | **confirmed**. Caveat: the 12–24 h is a general statement about moving a unit "from one task to another", so it most likely includes transport (Finding 12). |
| 2 | Versant "within six hours" (ER §1.1) | Versant Power blog (WebFetch) | "We can mobilize this unit within six hours"; "the only mobile substation that can carry the full load of our largest distribution subs"; three units in Bangor Hydro | **confirmed**. It says *mobilize*, not in service, so it is not a lower bound on e. It also serves "5,000+ customers", which makes it a small US substation. |
| 3 | FirstNet 72 deployables, 14 h on-air, aerostat ~2 weeks (ER §1.2) | FirstNet_Deployables.pdf (WebFetch) | "72 FirstNet Satellite Cell on Light Truck (SatCOLT) and Cell on Wheels (COW) deployables"; "14-hour on-air objective for emergent incident responses"; "about 2 weeks" | **confirmed**. It is a stated *objective*, not a measured time. |
| 4 | Xiaqingshui temporary bridge: 3 days, ≤5 t cars, one lane, three daily windows, heavy vehicles ~30 May at ≤15 km/h (ER §1.4) | Commercial Times, 20 May 2024 (WebFetch plus curl of the article body) | "公路局上月6日搭建完成鋼便橋後，先開放5噸以下小客車單線雙向通行"; "有望提前在30日開放大型車輛通行"; "大車需降速至15公里以下". **Also:** "發現一旁日據時代舊有下清水橋橋台結構及承載力尚佳，便在長度10米的舊橋面上，增設密排銲接12米長戰備鋼梁", and "由於地震後公路邊坡持續不穩定…目前仍採每天3時段管制通行，管制路段北端為仁水隧…" | **quotes confirmed; overstated in use.** The 3-day build reused the intact abutments of the adjacent Japanese-era bridge, so it is a best case. The three daily windows control the whole Suhua road section because of unstable slopes; they are not a bridge capacity limit (Finding 3). |
| 5 | Permanent bridge after 8 months; reopened 6 pm 19 Dec (ER §1.4) | Commercial Times, 20 Dec 2024 (curl) | "經8個月搶修施作，提前完成橋梁原址重建，於昨晚6時恢復雙向通行"; "檢視一旁日治時期留下的舊橋，結構仍完好，震後第3天即拓寬，改作為臨時便橋" | **confirmed**. The second quote confirms the old-bridge reuse. |
| 6 | Taiwan Water: 567 generators, 62 water trucks, 3,054 staff, 357 contractors (ER §1.3) | udn, 25 Aug 2026 (WebFetch) | "備妥567台緊急發電機、調度62台水車待命"; "357家合作搶修廠商及3054名內部人力" | **confirmed** |
| 7 | Chunghwa: 16 vehicles, 6 OneWeb, 3,104 person-trips; Taiwan Mobile: 10 (ER §1.2) | CNA, 21 Jul 2025 (WebFetch) | "16台行動基地台車，包括6台具備Oneweb低軌衛星設備"; "3104人次"; Taiwan Mobile "OneWeb衛星行動車」共10部" | **confirmed** |
| 8 | 28 satellite-equipped vehicles; 3 more each (9); 31 to be refitted; 200+ generators (ER §1.2, §2) | Commercial Times, 4 Aug 2025 (WebFetch) | "共有 28 輛搭載低軌道衛星終端設備"; "各增購 3 台(共9台)"; "將 31 輛未設置衛星終端設備的行動車進行改裝"; "預計購置200餘台可攜式緊急發電機" | **confirmed**. The ≥59 fleet is the lane's own sum, and the lane labels it a derived floor. |
| 9 | 30+ vehicles in Chiayi–Tainan; 33 sites awaiting repair; done by end of October (ER §1.2) | CNA, 4 Aug 2025 (WebFetch) | "每日仍有30餘輛行動基地台車在嘉南地區提供服務"; "33站待修復"; "預定10月底前全數復原完畢" | **confirmed**. "About 3 months of emergency service" is an inference: the source does not say that every one of the 33 sites had a vehicle. |
| 10 | NERC: 263 EMS events, ~73 min mean, no loss of generation, lines or load, manning substations (TOL §2) | NERC RSTC reference document v4 (WebFetch) | "There were 263 EMS events reported between 2019 and 2023"; about 73 minutes on average; no event "that led to the loss of generation, transmission lines, or customer load"; "Manning substations during EMS events…" | **confirmed**. The same document names "communications/maintenance" as the major contributors to complete loss of monitoring or control, so "mostly internal" (the lane, following R1 Check 7) is looser than the source. |
| 11 | NERC LL20180801: TelCo outage, callouts to staff substations, ~8 h (TOL §2) | NERC PDF (curl + pdftotext) | "initiated callouts to staff key Bulk Electric System (BES) substations"; "Approximately eight hours after the event first occurred, the TelCo reported that all network issues had been resolved" | **confirmed**. It is silent on load, as the lane says. The trigger was a scheduled late-night circuit transfer that coincided with the TelCo outage. |
| 12 | Newark 28 Apr 2025: ~30 s loss, 30–60 s to reappear; FAA "issued several ground delays and ground stops" (TOL §2) | CBS News (WebFetch, twice) | "about 30 seconds"; "30 to 60 seconds for aircraft to reappear"; the ground-stop sentence is present | **overstated.** The article ties the ground stops to "the past week" as a whole: staffing (controllers on leave after the outage), runway construction and equipment. It does not tie them to the 30 s loss itself (Finding 10). |
| 13 | Newark 9 May 2025: ~90 s, telecom outage, copper wiring to Philadelphia TRACON (TOL §2) | *Flying* (WebFetch) | "the disruption, which lasted about 90 seconds, was due to a telecommunications outage"; "antiquated copper telecommunications wiring" | **confirmed** |
| 14 | Stony Brook downtime tiers: 30 min, 1 h, 2 h, 4 h, 24 h (TOL §2) | Stony Brook PDF (curl + pdftotext) | All five quotes are present, and the document is "Revision August 2022". | **confirmed**, with a caveat. The 2 h tier ("expected duration of 2 hours or greater") sits under *Scheduled* System Downtimes. The unscheduled checklist tiers are "30 min. to 4 hours" and "greater than 4 hours". |
| 15 | NHI exception rule: network failure and HIS crash listed; upload within 24 h (TOL §2) | NHIA form 11207 (WebFetch) | "網路故障造成讀卡機無法使用"; "醫療資訊系統(HIS)當機"; "24 小時內上傳就醫資料" | **quotes confirmed; overstated in use.** The rule sets an administrative upload deadline. It is not a tolerance limit on care (Finding 4). |
| 16 | Rogers 2022: 8 July; April 2021 precedent; "not able to process transactions made by debit cards, e-transfers and some credit cards" [T15] (TOL §2) | Wikipedia (curl + grep); City of Toronto attachment T19 (curl + pdftotext) | Wikipedia: 8 July 2022 and the April 2021 outage are confirmed, but it has only "Interac was taken offline … unable to accept debit card transactions". The quoted sentence is in **T19** (l.93), along with "approximately 15 – 19 hours … up to 4 days" and the hospital sentence. | **wrong attribution** (the quote belongs to T19, not T15). The substance is confirmed. |
| 17 | ASPR: "down for 4 hours … 8 hours to put the data into the EHR" (TOL §0) | ASPR TRACIE PDF (WebFetch) | "For example, if we were down for 4 hours, staff get 8 hours to put the data into the EHR." | **confirmed** |
| — | Hazus: what the restoration curves measure (ER Q1) | Local `repair/hazus_mr4.txt` l.13792, 14350–14360, 22421–22530 | See Finding 2 | used to answer ER Q1 |

---

## 2. Findings

### F1. The case for emergency repair in the pilot rests on the Hazus mean that R1-F7 already replaced. **M**
- ER §0.2 and §4.1 compare e (18 h) with the Hazus substation-moderate mean of 72 h. R1-F7 splits the permanent repair into two parts: a lead time that holds no crew, and crew work (J anchors: moderate 12–36 crew-hours).
- R1-Q19 restricts pilot damage at facilities to slight and moderate. That rules out every extensive or complete case the lane lists: bridges, destroyed masts, the Dyersburg-type substation.
- What is left is one comparison. At moderate damage, mode E gives c ≈ 0.14 after e + travel (about 18–24 h) and holds a crew for e. Mode P gives c = 1 after lead time + work (≥ 12–36 h) and holds a crew for the work.
  - E wins only when the placeholder lead time is long.
  - E also spends crew-hours that P would have used. In a pool of 2 crews, that is the scarce resource.
- **Consequence.** Whether E ever appears in a pilot answer key depends almost entirely on two J numbers: the lead time and e. That makes it an artefact of the placeholders, not evidence.
- **Fix.** Do not include emergency modes in the pilot. Write the two-mode structure into the specification for the full build, where extensive and complete states and longer windows occur. If the design side does want the allocation decision in the pilot, use one mobile substation, e = 12 h excluding travel, and report in the manifest which nodes it dominated for.

### F2. Hazus restoration is restoration of function. For substations at extensive and complete damage, it already includes temporary measures. **M** (answers ER Q1)
- **What MR4 says.** Its curves give "distributions on functionality" and "Percent Functional" (l.14382, 14781). The essential-facility, highway and railway curves are fitted to "ATC-13 data for the social function classifications" (l.13792, 14350, 15471). **Substations are fitted to "a G&E report (1994)"** (l.22481), not to ATC-13, so ER Q1's attribution is wrong for the one class that matters. Nothing in MR4 says "permanent", "durable" or "rebuild". It also says "better restoration curves can be developed, given knowledge of available resources" (l.22236).
- **An internal test.** Hazus complete damage to a substation is "failure of all … transformers" (l.22472), and its mean restoration is **30 days** (σ 15). DOE (the same PDF the lane cites, l.655) gives a "6-month to 1-year lead time" for large transformers. A return to function in 30 days after every transformer has failed is possible only with spares, mobiles or temporary bypasses. Hazus substation extensive/complete therefore already contains temporary measures.
- **For bridges, Hazus matches durable rebuild.** Complete damage is 230 d (σ 110), and Xiaqingshui's rebuild on the original site took about 8.5 months (about 260 d).
- **Ruling impact.** The earlier reading "Hazus = durable restoration" holds for bridges. It does **not** hold for substations at extensive or complete damage, where an E mode would count the mobile twice. At moderate damage (3 d) the source cannot settle the question. None of this touches the pilot while R1-Q19 stands.

### F3. The temporary-bridge figures are a best case, and the capacity derivation uses the wrong constraint. **M**
- The 3-day build laid 12 m military beams on the "structurally sound" abutments of the adjacent 1920s bridge (source check #4). A free-standing temporary bridge takes longer. MLIT's "15人・３日" covers only 16–40 m spans. The Mataian Creek example took weeks.
- The three daily windows (06–08, 12–13, 17–19) were traffic control on the Heren–Chongde road section because of unstable slopes. They were not a limit of the bridge. So c_light = 0.1 ("5 of 24 h") is derived from a road-closure regime, not from bridge capacity. Taken alone, the bridge gave one lane in both directions for vehicles of 5 t or less.
- **Fix.** Centre e at 72 h and state that it assumes a reusable substructure; the range should run to weeks. Re-derive c_light as a single-lane share (J, about 0.5 of light-vehicle flow) and keep c_heavy = 0 for about 8 weeks. None of this enters the pilot (no bridge kits, no extensive or complete damage).

### F4. The Taiwan NHI rule proves that a fallback exists. It does not prove T = 24 h. **M**
- "24 小時內上傳就醫資料" is a deadline for uploading visit records. Nothing in it says care degrades, or must degrade, after 24 h. The clinic page says patients continue to be seen under exception codes, and the claim rights are unaffected.
- "The only S-grade tolerance found in any class" is therefore overstated. The rule is S · TW for *the existence of a manual fallback with no loss of care*. T = 24 h for clinics and on-site-EHR hospitals is **J**. It is plausibly longer, bounded only by coordination and staffing losses (the Rogers evidence).
- **Fix.** Regrade T to J for those rows, and keep the S · TW citation for the mechanism.

### F5. The tolerance hours are inverted for staffed process plants. **M**
- **Generation** has T = 4 h, while its transmission substation has T = 12 h. A generating plant has a control room staffed around the clock and can take dispatch by voice. An unmanned substation needs callout staff to reach it. So the plant should tolerate at least as long as the substation.
- The lane's reason, loss of AGC so the plant "cannot follow load", is a *system* effect of losing automatic dispatch. It is not a loss of the node's capacity, and d = 0.8 turns it into 20% of capacity lost. Under R1 Taipower's κ is small, so the cost is small in a Taipower-like world, but the target is still wrong in kind.
- **import_terminal** has T = 2 h beside refinery at 72 h and tank_farm at 1 h. An LNG or oil import terminal is a staffed plant with its own DCS, like a refinery. The 1–2 h evidence is Colonial Pipeline (source T14), a precautionary shutdown of a pipeline that followed a cyberattack. It is an L-an for a trunk pipeline, not for a terminal.
- **Fix.**
  - generation: T 12 h (4–24), d 0.95 (0.9–1.0), J;
  - import_terminal: T 12 h (4–48), d 0.8, J;
  - tank_farm (pipeline-connected): keep T = 1 h, but regrade it J with an L-an analogue (Colonial was a policy shutdown, not a telecom loss).

### F6. Substation d applied to supply contradicts the lane's own evidence. **M** (answers TOL Q-T1)
- In both NERC carrier events, and across 263 EMS events, no load was lost. The lane's own text says steady-state supply is untouched and that the loss is in fault handling. Yet the table sets d = 0.9 for transmission and 0.85 for distribution substations as a cut to *supply*.
- **Fix.** For substations, set d = 1 on supply. Represent the effect of telecom loss as a **switching and repair lead-time penalty** on repair jobs at that substation while telecom is out: an additive truck-roll time, which is a placeholder and linear. In the pilot, that penalty is the only channel from telecom to power, which is consistent with Taipower's own fibre (κ small).

### F7. A delay in turnaround is converted into a loss of throughput. **m**
- "62% delay → 1 ÷ 1.62 = 0.62 throughput" confuses latency with rate. A lab whose turnaround is 62% longer can still process the same number of samples.
- **Fix.** Keep d = 0.65 for hosted-EHR hospitals as J, supported in direction by the CrowdStrike cancellations of non-urgent work. Drop the arithmetic.

### F8. The IT analogues are applied with their full severity, unevenly across classes. **m**
- For ports, the lane correctly says an outside telecom loss leaves the terminal operating system running, so d ≠ 0.
- For the blood bank, it takes d = 0.5 from OneBlood, a ransomware attack that took down the blood bank's *own* systems.
- An outside-carrier loss at a blood bank with its systems on site leaves labelling and inventory working, and cuts only ordering and coordination.
- **Fix.** Set blood_bank d to 0.7 (0.5–0.9), J, the same reasoning the lane used for ports.

### F9. Seaport 0.5 against freight_yard 0.6 has no basis. **m**
- Both values are J. A rail freight yard that loses its dispatch and signalling communications falls back to phone and paper block working, which is at least as limiting as a port's paper gate.
- **Fix.** Use one value for both, 0.5 (0.3–0.7), J, and record that the order between them is unknown.

### F10. The Newark evidence shows the mechanism, not the timing. **m**
- The ground stops in the CBS article belong to a week of staffing, runway and equipment problems. So "a 30–90 s loss produced ground stops" is overstated.
- T ≈ 0 for a towered airport still holds on mechanism: once radar and voice are lost, separation service stops immediately.
- **Fix.** Cite it that way. For a Taiwan-like world, note that ANWS/CAA circuits may be private, which would make κ small. That belongs with TOL Q-T3.

### F11. The Rogers quote is attributed to the wrong source. **m**
- The "debit cards, e-transfers and some credit cards" sentence is in T19 (City of Toronto), not T15 (Wikipedia).
- **Fix.** Cite T19.

### F12. Travel time may be counted twice in e for the mobile substation, and the lower end of the range is misread. **m**
- The DOE figure of 12–24 h is a general deployment capability, which likely includes road transport. The lane adds network travel on top of it.
- Versant's 6 h is the time to *mobilize*, not the time to energise.
- **Fix.** If emergency modes are built at all (F1), use e excluding travel at about 12 h (8–18 h), J inside the DOE figure.

### F13. An inert parameter is carried "for later". **m**
- φ = 1, "recorded in the manifest and no effect unless a second hazard is modelled", is a switch for later. CLAUDE.md §2 forbids that.
- **Fix.** Leave φ out of the pilot schema. Keep the washout evidence in the design notes.

### F14. After these fixes, telecom coupling acts on only a few classes in a 72 h pilot. **m** (a consequence, not an error)
- With T ≥ 12 h and d ≥ 0.8 for most classes, and κ small for Taipower, telecom loss inside 72 h moves only these classes:
  - the towered airport;
  - the pipeline-connected tank farm;
  - hosted-EHR hospitals and clinics;
  - the seaport and freight yard after 24 h.
- Replacing R1-Q11's class-free floors (0.5 and 0.7) with these values weakens the telecom layer considerably.
- **Fix.** The design side should confirm that the pilot scenario still exercises telecom through at least one of these classes. Otherwise the carried-versus-flattened contrast on telecom will be empty by construction.

### F15. The step's combination rules are unspecified. **m**
- **(a) Combining shortfalls.** The lane does not say how s(t) combines with a simultaneous shortfall of power or water at the same node.
- **(b) Several telecom edges.** When a node has several telecom edges with different κ, the lane does not say which κ enters d_eff.
- Both change answer keys. See questions 17 and 18.

### F16. Supply substitutes: the separation is right, and leaving them out biases the pilot toward pessimism. **m**
- The line between node substitute and supply substitute is correct. Putting portable generators inside a node's repair job would count one physical scarcity in two places, as the lane argues.
- But Taiwan practice relies mainly on supply substitutes (567 generators at Taiwan Water), and it **pre-positions** them before landfall. Leaving them out entirely makes water pumping in the pilot too fragile.
- A pre-positioned generator is static. It is simply an on-site backup buffer at the stations that received one, so no routing is needed.
- See question 2.

### On the formula d_eff = 1 − κ(1 − d)
The formula is sound. It is linear, it uses only permitted operations, it gives d_eff = 1 at κ = 0 and d at κ = 1, and it leaves T alone, which fits the mechanism. The lane's rejection of scaling T by 1/κ is right. Two conditions apply:
1. κ must mean the *public share of the node's telecom need*. It must not also appear as a partial requirement (TOL Q-T2), which would count it twice.
2. The private remainder must not *also* be modelled as a separate telecom edge. If it is, losing the public edge never triggers "last telecom edge lost", and the κ scaling double-protects the node. Choose one representation (question 18).

### On the two-mode representation
The structure is sound for a 72 h window: alternative modes (as in Talbot 1982 and Cavdaroglu 2013), a finite pool, the unit held past the horizon, and no E-then-P sequence. It keeps brute force exact at 2^k per eligible node. It is correct, but not needed in the pilot (F1). For the full build, add one rule the lane does not give: how a partial capacity c at a substation is shared among its downstream consumers (question 9).

---

## 3. Consolidated questions with recommended answers

Origin: ER = emergency-repair lane (Q1–Q8), TOL = tolerance lane (Q-T1–T5 and its four CHOICE-candidates), Rev = raised here. The two lanes raised 17 in all. Merging ER Q7 into ER Q6, and the TOL on-site/hosted choice into the TOL step/ramp choice, leaves 15 (rows 1–15). This review adds 5 (rows 16–20).

| # | Question (origin) | Recommended answer | Reason |
|---|---|---|---|
| 1 | Does Hazus restoration already include temporary measures? (ER Q1) | **Yes for substations at extensive and complete damage; no for bridges; open at moderate.** Offer no E mode where Hazus already contains it. | A 30-day return to function after all transformers fail is impossible without temporaries (6–12 month lead time). Bridge complete damage (230 d) matches the Xiaqingshui rebuild (F2). |
| 2 | Supply substitutes: leave them out of the pilot, or give them their own pool? (ER Q2) | **No routed pool in the pilot.** Model pre-positioned portable generators as an on-site buffer at a drawn share of pumping stations (placeholder). The routed mobile-power-source pool goes into the full build. | Taiwan pre-positions before landfall, which is static and needs no routing. Leaving them out entirely overstates water fragility (F16). |
| 3 | Which Taipower substation is `distribution_substation`? Is c based on peak or nameplate? (ER Q3) | **The D/S feeding 11.4/22.8 kV**, consistent with the 5 MW (11.4 kV) threshold (R1-Q15). **c is based on the node's undisturbed peak load.** | The load to be served is what the answer key needs. Nameplate overstates the need. |
| 4 | Mobile-cell capacity fraction of 0.5? (ER Q4) | **Accept it as a placeholder (J)**, only when masts get an E mode (full build). | No source was found, and it does not enter the pilot (F1). |
| 5 | Bridge capacity by vehicle class? (ER Q5) | **Not in the pilot.** In the full build, use two classes: c_light ≈ 0.5 (single lane, J) and c_heavy = 0 for about 8 weeks. The road layer carries a vehicle-class attribute. | c_heavy decides trucked fuel. The 0.1 came from road-section control, not the bridge (F3). |
| 6 | Modes or a sequence? Pool sizes and base? (ER Q6, Q7) | **Modes** for any window up to about 7 days. **Pilot pools: 0**, since there is no emergency repair in the pilot. Full build: mobile substation 1 and mobile cell 1, based at `crew_base`. | Under R1-F7 and R1-Q19, E's value in the pilot would come from placeholders alone (F1). |
| 7 | Exchange: no emergency mode? (ER Q8) | **Yes, no emergency mode.** | No deployment time was found. Recovery trailers are a fleet figure only. |
| 8 | Substation d: supply, or switching and repair? (TOL Q-T1) | **Switching and repair.** Supply d = 1. Telecom loss adds a lead-time penalty (placeholder) to repair jobs at that substation. | Every source shows no loss of load (F6). |
| 9 | Does κ enter only as the step depth? (TOL Q-T2) | **Yes.** It must not also be a partial requirement. | Otherwise it is counted twice. |
| 10 | Is ATC re-routed to a neighbouring facility a second telecom edge? (TOL Q-T3) | **Yes.** Keep d = 0.2 for no-path operation as J. For Taiwan, check whether ANWS circuits are private (κ). | Redundancy by edge count is how the 80–90% recoveries happened. |
| 11 | Staff access makes T optimistic in a compound storm? (TOL Q-T4) | **Yes. State it in the report as a known optimism.** | R8 puts staff access out of scope, and hiding the bias would be worse. |
| 12 | No telecom → storage row? (TOL Q-T5) | **Confirm: none.** | This is consistent with R1-F17 and the dependency table. |
| 13 | Step by default, with a ramp only for hosted-EHR hospitals; on-site and hosted switch T and d (TOL CHOICE 1, 3) | **Accept.** Ramp: T 0.5 h, reaching d at 4 h, based on the unscheduled 30 min / 4 h tiers. | The ramp is linear and has tiered evidence. The 2 h tier comes from scheduled downtime (source check #14). |
| 14 | Restoration returns s to 1 at once, and the backlog is ignored? (TOL CHOICE 2) | **Accept for Phase 1.** | The backlog costs data re-entry, not function. |
| 15 | Does the public share scale T or d? (TOL CHOICE 4) | **d only**, as d_eff = 1 − κ(1 − d). | T belongs to the fallback procedure. Scaling T by 1/κ diverges at κ = 0. |
| 16 | Generation and import-terminal tolerance (Rev, F5) | **generation:** T 12 h, d 0.95. **import_terminal:** T 12 h, d 0.8. **tank_farm (pipeline):** T 1 h, regraded J. All J. | Staffed plants with their own DCS tolerate at least as long as an unmanned substation. AGC loss is a system effect. |
| 17 | How does the telecom step combine with a power or water shortfall at the same node? (Rev, F15a) | **The minimum of the per-commodity service levels.** | They are separate limiting inputs. A product would compound them and count one outage twice. |
| 18 | Which κ enters d_eff when a node has several telecom edges, and how is the private remainder represented? (Rev, F15b) | **κ is one node-level public share.** The private remainder is folded into κ and is never a separate telecom edge. The step triggers when every public telecom edge is lost. | One representation avoids double protection and keeps κ's meaning as ruled in R1-Q10. |
| 19 | NHI grade and T for clinics and on-site-EHR hospitals (Rev, F4) | **S · TW for the fallback; J for T = 24 h**, with range 24–72 h. | The 24 h is an upload deadline, not a limit on care. |
| 20 | Blood bank and port/freight d (Rev, F8, F9) | **blood_bank:** d 0.7 (0.5–0.9). **seaport and freight_yard:** d 0.5 (0.3–0.7). All J. | The IT analogues show the terminal's own systems down. An outside-carrier loss is milder, and the order between port and yard is unknown. |

---

## 4. Verdict

The sourcing is honest. Of 17 checks, every number the lanes quote is in its source. There is one wrong attribution (Rogers) and no fabrication. The problems are in how three sources are read:
- the Xiaqingshui bridge reused an old substructure, and its time windows were road-section control;
- the NHI 24 h is an upload deadline;
- the Newark ground stops belong to the week's wider problems, not to the 30 s outage.

**Emergency-repair lane.** The split between node substitutes and supply substitutes, and the two-mode structure with a finite pool, are sound and ready for the specification. The lane's case that emergency repair matters in a 72 h pilot rests on the unsplit Hazus mean that R1-F7 retired, and R1-Q19 removes every state where the lane's evidence is strong. Recommendation:
- no emergency modes in the pilot;
- pre-positioned generators modelled as static buffers;
- the two-mode structure written into the specification for the full build.

The Hazus text answers ER Q1. Hazus is restoration of function. For substations at extensive and complete damage it already contains temporary measures, so the "durable restoration" ruling should be narrowed to bridges and to lower damage states.

**Tolerance lane.** The mechanism is sound: a step, a hospital-only ramp, and d_eff = 1 − κ(1 − d) with T unscaled. So is the evidence base, which is the best direct telecom evidence yet: the NERC carrier events, Rogers and Matsu. The table needs these corrections before it becomes the centre of the truth:
- F5: generation and the import terminal are inverted against the substations;
- F6: substations should lose switching speed, not supply;
- F4: regrade the NHI T to J;
- F7: drop the latency-to-throughput arithmetic;
- F8 and F9: make the IT-analogue severities consistent.

Questions 8, 16, 17 and 18 must be decided before the solver is specified, because each one changes answer keys. After the fixes, the design side should confirm that the pilot scenario still routes telecom loss through a class that reacts inside 72 h (F14).
