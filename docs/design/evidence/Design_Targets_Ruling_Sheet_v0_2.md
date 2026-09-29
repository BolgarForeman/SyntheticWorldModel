# Design targets for the unobserved quantities: ruling sheet v0.2

*2026-09-29 · for Foreman · prerequisite to SyntheticWorldModel Work Order 5 · v0.2 adds the tolerance buffer and emergency repair*

## What this is

Work Order 5 draws the quantities no source reports:
- each node's requirements (what it draws from each layer);
- reserves (the stock that buys time when supply stops);
- coupling strength;
- failure mode;
- repair times;
- crews.

Each draw is centred on a design target, the value a code, standard or authoritative guidance sets for that kind of facility. The two levers (heterogeneity and compliance gap) then move the truth away from it.

The targets were built the same way as the dependency table:
- **Research lanes:** four, one each for reserves, requirements, repair and crews, and failure mode, strength and compliance.
- **Independent review:** the reviewer re-checked 22 sources. 17 were confirmed, 3 overstated, 2 unreachable, and none were wrong or fabricated.

Full evidence: `SWM_Design_Targets_Evidence_v0_1_CAO_2026-09-29.md` (the lanes and the review, with every source and quote).

Grades: **S** standard or regulation · **L** literature or government report · **J** judgment. Jurisdiction: **TW** Taiwan · **JP** Japan · **US**.

## The targets at a glance (as recommended)

**Reserves.** A reserve is stock; buffer time = stock ÷ draw, computed in the run.

| Element | Target | Basis |
|---|---|---|
| Tertiary and regional hospital, generator fuel | 72 h at essential load | TW accreditation (3 days of continued operation); JP disaster-hospital rule · S/L |
| Clinic, generator | none by default | No requirement found (US CMS 491.12) · S |
| Blood bank | generator fuel 72 h; blood stock 7 days | TW Blood Services Foundation 7–10 days · L |
| Hospital water | 72 h at 300 L per bed per day (emergency ration) | TW hospital guideline · L |
| Hospital supplies (transport dependency) | 72 h stock | JP practice · J/L |
| Mast battery | 4 h; 72 h at designated disaster-response sites | TW base-station regulations Art. 22 (2024) · S |
| Exchange | batteries plus 24 h fuel | US industry practice recorded by the California regulator · L |
| Data centre | 72 h fuel | TIA-942 Rating 3 (secondary source) · L |
| Cable landing, water treatment | 48 h fuel | J |
| Distribution water storage | 12 h of peak-day demand | JP design guideline · L |
| LNG | 11 days (2025), rising to 14 in 2027 | TW law · S |
| Oil | 60 days held by industry plus 30 held by government | TW Petroleum Administration Act · S |
| Coal plants | 30 days of the previous year's average burn | TW rule · S |
| Anything against telecom loss | no stock possible | By nature |

**Requirements** (normal-operation draw, scaled by the size attributes the world already has):

| Element | Target | Basis |
|---|---|---|
| Hospital electricity | tertiary 2.5 kW per bed, regional 2.0 | Taiwan bound (sources vary nine-fold) · L/J |
| Hospital water | tertiary 1.0 m³ per bed per day, regional 0.5 | TW building plumbing code · S |
| Mast | about 6 kW (4G) | L |
| Water treatment | 0.37 kWh per m³ | L |
| Refinery | about 7 kWh per barrel | L |
| Thermal generation fuel | LNG combined cycle 8.0 GJ/MWh, coal about 11 | US 2024 heat rates · L |
| Telecom | served or not (binary) | Recommended; no bandwidth attribute exists |
| Supply from a transmission substation | peak load of 5 MW or more (11.4 kV areas; 10 MW in 22.8 kV areas) | Taipower Business Regulations Art. 46 · S |

**Repair.** FEMA Hazus restoration days by facility class and damage state (slight, moderate, extensive, complete), from the MR4 technical manual. FEMA blocked the current 6.1 values, which remain unverified. Road access is the strongest measured context factor (Hurricane Maria study).

## Rulings needed (these change what the world contains)

**T1. Anchor on Taiwan first.** Use a Taiwan rule wherever one exists, then Japan, then US, and show the grade on every target.
- Recommended.

**T2. Hospitals.**
- Tertiary and regional both hold 72 h of generator fuel. Taiwan's accreditation does not distinguish them.
- Clinics hold none by default.
- On generator power a hospital runs its essential load, about 60% (JP), not full load.
- Recommended.

**T3. Hospital water.**
- Stock sized as 72 h at the emergency ration (300 L per bed per day).
- Normal draw 1.0 / 0.5 m³ per bed per day.
- In a water outage the hospital drops to the emergency ration, and the stock then lasts 72 h.
- The reviewer caught that mixing the two gave 21.6 h, not 72.
- Recommended.

**T4. Telecom loss is a tolerance buffer.** Ruled by Foreman, 2026-09-29.
- There is no stock behind it, so this answers open decision 7 for telecom.
- When telecom is lost, a facility keeps full function on manual fallback for T hours, then steps down to a degraded level d.
- Only the public-network share of the signal counts (ruling R1). The effective step is d_eff = 1 − public share × (1 − d); T is not scaled.
- Values below are from the tolerance lane, with the independent review's corrections applied. Most are judgment.

| Class | T (hours) | d after T | Basis |
|---|---|---|---|
| Towered airport | 0 | 0.2 | L (US: 90-second radar and radio losses at Newark 2025 disrupted operations) |
| Tank farm, pipeline-connected | 1 | 0.5 | S (US pipeline control-room rule) plus judgment |
| Generation | 12 | 0.95 | L (US: 263 control-system losses in 2019–23, no generation lost); review raised it from 4 h |
| Import terminal | 12 | 0.8 | J; review raised it from 2 h |
| Transmission and distribution substations | 12 | 1.0 | L (US: substations staffed by hand for 8 h, no load lost). Loss slows switching and repair; it does not cut supply |
| Pumping | 12 | 0.8 | J |
| Water treatment | 24 | 0.9 | J |
| Reservoir | 72 | 0.95 | J |
| Seaport, freight yard | 24 | 0.5 | IT-outage analogue plus judgment |
| Depot | 12 | 0.6 | J |
| Refinery | 72 | 0.8 | J |
| Hospital, records on site | 24 | 0.85 | TW rule that care continues and records are uploaded within 24 h, plus US hospital downtime policies |
| Hospital, records hosted off site | 0.5, ramping to d by 4 h | 0.65 | US hospital downtime tiers |
| Clinic | 24 (range 24–72) | 0.8 | TW rule; the rule proves the fallback, the hours are judgment |
| Blood bank | 24 | 0.7 | J |

When telecom and power or water fall short together, the facility takes the lowest of the levels, not their product.

**T5. Transmission connection at 5 MW** (Taipower's 11.4 kV-area rule), with a recipe switch to 10 MW (22.8 kV areas).
- The same rule, not a fixed class list, decides every consumer's supplying substation.
- Before the code relies on the thresholds, check them against the 2022 Taipower rules.
- Recommended.

**T6. Repair in the pilot.**
- Split repair into a lead time that holds no crew (assessment, parts) and crew work hours.
- The pilot storm causes slight and moderate damage only at facilities. Hazus extensive and complete damage lasts weeks, so inside a 72-hour window repair ordering would stop mattering.
- Keep the pilot's 2 crews as a declared scarcity, in one pool, and run 1, 2 and 3 crews as a sensitivity test.
- Rename the repair base `crew_base`, so it is not confused with the fuel depot class.
- Recommended.

**T7. Compliance gaps.**
- Defaults: hospital backup 15%, water 20%, exchanges and data centres 0%, masts 0% against the Taiwan 4-hour rule (not 50% against a US rule that never took effect).
- Generator reliability (fails to start, fails to run) is a separate availability draw per generator, not part of the gap (military reliability data, Marqusee & Jenket 2020).
- All placeholders.
- Recommended.

**T8. Fuel resupply for backup generators.** No lane found a figure, and it decides whether a hospital runs dry inside 72 h. Placeholders:
- 12 h lead time from the depot;
- each delivery carries 24 h of fuel.
- Recommended, to be revisited with the realism ranges.

**T9. What the levers mean.**
- Draws come from a skewed, positive table (reserves and repair times are right-skewed), built with only the permitted arithmetic.
- The compliance gap shifts the median. A gap of 0 means centred on the target, not that every element complies; state this plainly in the spec.
- Cap the gap at 95. Total absence is carried by the presence attributes (no generator, no battery), not by a gap of 100.
- Recommended.

**T10. Coupling strength.**
- κ = min(1, available supply ÷ requirement), as the dissertation defines it. The spec's "three times its need" becomes an uncapped headroom recorded in the truth manifest.
- For telecom, κ is the public-network share under ruling R1.
- Add a world check: in the undisturbed world every consumer is fully supplied. A world that is short before the storm corrupts every answer key.
- Recommended.

**T11. Emergency repair.** Ruled by Foreman, 2026-09-29: model emergency repair alongside permanent repair.
- Each eligible damaged node gets two alternative repair modes:
  - **Emergency:** crew travel plus set-up, using one unit from a finite pool (mobile substation, mobile cell site). It restores reduced capacity for the rest of the event.
  - **Permanent:** lead time plus crew work, restoring full capacity.
- Inside a 72-hour window a sequence (emergency first, then permanent) adds nothing, because permanent repair never finishes in the window.
- Where it pays inside 72 hours:
  - **Distribution substation:** mobile substation, 12–24 h including travel. It restores about 25 MVA, measured against the node's normal peak load (US DOE).
  - **Mast:** mobile cell site, about 14 h (FirstNet target). Capacity 0.5 (placeholder).
  - Bridges (temporary bridge, about 3 days in Taiwan's best case), transmission substations and plants do not pay inside 72 hours.
- Portable generators and water trucks replace lost supply, not a damaged node. They are modelled as pre-positioned on-site buffers at a share of pump stations (Taiwan pre-positions them before a typhoon), not as a routed fleet.
- The reviewer found that Hazus substation restoration already counts temporary measures, for example a 30-day mean for complete damage where a new large transformer takes 6–12 months. The "Hazus is durable restoration" reading holds for bridges only.
- **Pilot choice: ruled (a), 2026-09-29.**
  - **(a) Recommended:** a pool of 1 mobile substation and 1 mobile cell site, so the restorative model faces a real choice of where to send it.
  - **(b)** The reviewer's option: pool 0 in the pilot, and the two-mode design in the full build only. The numbers are placeholders, and with slight and moderate damage only, emergency repair may barely change the answer keys.

## Decided without a ruling (technical, as the review recommended)

- Buffer hours are computed at expected load, not rated load.
- Battery and generator hours add.
- Fire-reserve water does not count toward the potable buffer.
- Airport standby fuel is left out.
- Oil stockpiles are allocated pro rata by tank capacity.
- Data centres get no make-up water in Phase 1.
- Blood cold-chain hold-over is left out.
- A reservoir cannot be repaired inside the window.
- The failure mode is the consumer's response, drawn per node and commodity. The edge's transfer form stays as set.
- The canon mode is set per dependency type and class. Heterogeneity default is 10%.
- κ uses average requirement; the connection threshold uses peak.
- Port and airport size-to-throughput tables go in the recipe as placeholders, anchored to Taiwan's published port and airport throughput.
- An outlying-island mobilisation delay of 12 h is a placeholder.
- No second crew base in the pilot.
- Cite Hazus MR4 and note 6.1 as unverified.

## Then

Once T1–T11 are ruled:
- the targets become spec §4.4a (World_Generator_Structure v0.6), with the evidence cited;
- the spec also fixes the five narrowed supplier lists in §4.3a;
- Work Order 5 is drafted from them.

The pilot's hand trace can be fixed after Work Order 5, when every number it needs exists.

## Rulings recorded (Foreman, 2026-09-29)

- T1: Taiwan first. The fallback order after Taiwan is to be decided later.
- T2, T3, T5, T6 and T7–T10: agreed as recommended.
- T4: tolerance buffer, agreed.
- T11: emergency repair, with pilot (a), a pool of one mobile substation and one mobile cell site.
- New: every rule and target lives in a modeling rules registry with its source and reasoning, rendered as a Modeling Rules page, and changed only by reviewed edits (Work Order 5, Part A).
