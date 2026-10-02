# 0012 — The storm: hazard field, flood and damage

- **Date:** 2026-09-30
- **Decided by:** the author (Foreman), H1–H10 all as recommended on the ruling sheet
- **Recorded by:** Work Order 6, Part C (PR 6a)
- **Sources:**
  - `docs/design/evidence/Hazards_Ruling_Sheet_v0_1.md`;
  - `docs/design/evidence/Hazards_Evidence_v0_1.md` (three research lanes and an independent review: 23 load-bearing claims, 15 confirmed, 6 overstated, 2 unreachable, none wrong);
  - structure v0.7 §4.3b.

## Context

The plan so far assumed the storm damages facilities. The evidence says typhoons mostly cut poles and overhead lines, and facilities lose supply rather than being damaged themselves:
- Faxai 2019: about 2,000 poles broke, and no mast collapsed from wind;
- Hurricane Ian 2022: 2.3% of the cell sites out were physically damaged;
- Hazus Hurricane has no wind model for lifelines.

Facilities are damaged mainly by flood. Every rule below changes what the world contains, so each needed a ruling.

## Decisions

- **H1. What the storm can damage.**
  - Wind brings down overhead power lines: the power layer's links, and the feeds from a substation to its consumers.
  - Wind also brings down aerial telecom links, with the same pole-line fragility (J).
  - Facilities fail by flood only; none fails from wind in Phase 1.
  - Buried water mains, roads and bridges are not damaged in Phase 1. Roads stay open; this restriction is declared.
- **H2. The wind field.** A typhoon on a straight track. The wind at each place is built in order:
  1. modified Rankine profile, exponent 0.5 (L);
  2. land keeps 0.83 of the sea wind, the drop mostly within 1 km of the coast (L, US);
  3. Taiwan wind-code surface factors: city core 0.476, town 0.662, open or coast 1.0 (S for the factors, J for their use);
  4. the lee of the spine keeps 0.6 (J);
  5. random variation from a Wendland kernel, correlation length 10 km, spread 10% (J, placeholders).

  Winds are 10-minute speeds. They convert to 3-second gusts only at the line fragility: ×1.75 inland, ×1.30 at the coast (WMO, L).
- **H3. Severity.**
  - 0 means no storm; otherwise V_max at sea = 17.2 + 0.53 × severity m/s, on the CWA classes (S, TW; the linear map is J).
  - Rainfall is 300 mm up to severity 33, 450 mm up to 66, and 600 mm above.
  - The pilot runs at severity 50: a moderate typhoon near 44 m/s at sea, with 450 mm.
- **H4. Flood.**
  - Flood depth = the scenario's flood stage (1, 2 or 3 m by rainfall, J) − the site's height above the nearest drainage (Nobre 2011, L).
  - Facilities flood out at their Hazus functional depths (L, US):
    - substations, power plants, treatment and pumping: 1.2 m;
    - tank farms and depots: any water;
    - hospitals, clinics and blood banks: 0.15 m from grade;
    - telecom facilities: 1.2 m, borrowed from substations (J);
    - on-ground storage: 7.3 m.
  - Reservoirs, ports and airports are not flood-damaged in Phase 1.
  - Damage state by depth over the threshold (J): up to 0.5 m slight, above 0.5 m moderate, above 1.5 m extensive, above 3 m complete. The pilot caps facility damage at moderate.
- **H5. Overhead lines.**
  - Failure chance comes from a stored table by 3-second gust, per km, centred on 0.05 per km at 45 m/s (L anchor, J per-km conversion).
  - Transmission towers collapse only near 285 km/h (L).
  - A failed line takes 6 h of crew work with no lead time, travelling from the crew base (J). Crews repair lines as well as facilities.
- **H6. Damage and function.** A damaged element is off from the storm until its repair completes, then fully back (L). Partial capacity by damage state comes later (declared).
- **H7. Hospitals** are damaged by flood only. Their storm outages come through the cascade, cushioned by their reserves (L, US).
- **H8. Scenarios.**
  - Each scenario draws its own track, peak wind within the class band, and variation field.
  - Elements fail independently given the field (L); correlation beyond the field is left out (declared).
  - The pilot keeps 8 equally weighted scenarios, an illustrative set rather than a probability estimate.
- **H9. Protection.** A protected element cannot be damaged in any scenario: the fortification convention (Brown et al. 2006, L). Defensive answers are therefore an upper bound (declared). Protection can target a facility or an overhead line, at cost 2 either way.
- **H10. Damage-state names:** slight, moderate, extensive and complete, as the Hazus lifeline repair times use.

Also decided without a ruling, as technical matters:
- winds are stored in m/s at 10-minute averaging;
- every curve that needs exp or erf is built offline into a stored table;
- each element reads the field at its location, and a line reads its peak gust along its length;
- every hazard rule carries its Theta role (θ*-dynamics);
- structure §4.4a gains crew work of 72 h for extensive damage and 168 h for complete;
- the seismic and flood-plain hazards stay off and unbuilt in Phase 1.

## Consequences

- **PR 6a** builds the wind field, the severity anchor, the flood field and the storm preview.
- **PR 6b** builds the fragility tables, the scenario damage draws, overhead-line repair and the checks.
- Every §4.3b number is a rule in the registry, with `theta_role: dynamics`.

## Addendum: answers to PR 6a (#12)

- **Date:** 2026-10-02
- **Decided by:** the design side, confirmed by the author (Foreman)
- **Source:** `docs/work_orders/WO-06a-answers.md`
- **Spec:** structure v0.7 §4.3b, updated on the branch to match

Every changed registry value keeps its old value in history, citing this decision.

The design review of the first pilot preview found three problems:
- the lee came out in stripes;
- every scenario hit the whole island at full strength, so the 8 scenarios barely differed;
- the only power plant flooded in every scenario.

1. **Scenario variety.** The profile stays "peak over the passage". Each scenario now draws two more values (J, placeholders):
   - its closest approach to the island's centre, 0–40 km, so some tracks pass offshore;
   - its radius of maximum wind, 20–60 km.
2. **Flood varies by scenario.**
   - Each scenario draws its 24-hour rainfall within ±75 mm of its rung (moderate: 375–525 mm).
   - Flood stage = (rain − 150 mm) ÷ 150 mm, in m (J).
   - Power plants and transmission substations stand on 2 m platforms, so their 1.2 m threshold is reached at 3.2 m above grade (J, placeholder). Real plants are built above the design flood; Hazus assumes slab on grade. No node moves.
3. **The lee** is measured against the smooth spine line of decision 0005: a place is in the lee when the spine line lies between it and the nearest point of the track. A flat island (mountainous 0) has no lee. The terrain now records its spine line for this; the line is not hashed, so the terrain goldens are unchanged.
4. **Wooded land** takes the town factor, 0.662: Taiwan's wind code and ASCE 7 both class wooded ground with suburbs. Wetland and bare ground stay open (1.0).
5. **Flood thresholds:**
   - refineries: 1.2 m (Hazus 4 ft);
   - import terminals: 1.2 m, on raised quays (J);
   - freight yards, bridges, road junctions and rail nodes: not flood-damaged in Phase 1.
6. **The city core** is the largest city, as built; to be revisited at real scale (Phase 5).

The coder's PR 6a choices and the deviation stand as marked, including:
- pits floored at height 0;
- per-facility records reading node positions from the layers.
