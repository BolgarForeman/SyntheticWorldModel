# Storm hazards: ruling sheet v0.1

*2026-09-30 · for Foreman · prerequisite to SyntheticWorldModel Work Order 6*

**Ruled 2026-09-30 by the author: H1–H10 all as recommended.** Recorded as decision 0012 and in structure v0.7 §4.3b.

## What this is

Work Order 6 turns a storm into damage. It builds three things:
- a typhoon as a field over the island;
- the rule that turns the field at each element into a damage state;
- the pilot's 5–8 scenarios.

Every rule below changes what the world contains, so each needs your ruling.

Evidence came from three research lanes and an independent reviewer:
- **Lane A:** what fails, by facility class.
- **Lane B:** the shape of the storm field.
- **Lane C:** what damage means for function, and how scenarios are drawn.
- **The reviewer** re-checked 23 load-bearing claims: 15 confirmed, 6 overstated, 2 unreachable, none wrong, and nothing invented.

Full evidence: `SWM_Hazards_Evidence_v0_1_CAO_2026-09-30.md`.

Grades: **S** standard or regulation · **L** literature or government report · **J** judgment. Jurisdiction: **TW** Taiwan · **JP** Japan · **US**.

## The finding that shapes everything

**Typhoons damage lines, not facilities.** Most real outages come from poles and overhead lines coming down, and from facilities losing grid power or their telecom backhaul. Few facilities are damaged themselves.
- **Faxai 2019 (Japan):** 934,900 households out, about 2,000 poles broken, 2 transmission towers down. The government review found that no cell mast collapsed from wind. Most pole failures were secondary damage: trees and buildings falling (about 74%), flying debris (14%), landslides (12%). JP, L.
- **Hurricane Ian 2022 (US):** of 1,096 cell sites out, 69% lost power, 29% lost backhaul, and 2.3% were physically damaged (FCC). US, L.
- **Hurricane Katrina 2005:** 72,447 poles destroyed, while 300 substations were taken off-line, not necessarily damaged (US Department of Energy). US, L.
- **Taiwan:** Soudelor 2015 (about 1,000 poles down, lines tripped, no collapses) and Danas 2025 (about 3,500 poles, about 1 million households) fit the same pattern. TW, L (partly secondary sources).
- **Facilities** are damaged mainly by **flooding**. FEMA's Hazus Flood model shuts a facility down when water reaches a set depth: substations, power plants, and water treatment and pumping plants at 4 ft; tank farms at any depth; hospitals at 0.5 ft. US, L.
- **Hazus Hurricane has no wind-damage model for utilities or transport at all.** US, L.

The existing plan assumed the storm damages facilities. This evidence says the pilot storm should mainly cut **overhead lines**, and flood a few **low-lying facilities**. The cascade, the buffers and the repair crews then do the rest, which is what the pilot is built to test.

## Rulings needed

**H1. What the storm can damage.**
- **Overhead power lines:** the power layer's own links, plus the power feeds from a substation to its consumers. These fail by wind.
- **Aerial telecom backhaul:** the telecom links. They fail with the same pole-line fragility, since aerial fibre rides the same poles. J.
- **Facilities:** fail by flood only. None fails from wind in Phase 1. This follows Faxai (no mast fell from wind) and Hazus (no wind model for lifelines).
- **Not damaged in Phase 1:** buried water mains, roads and bridges. Roads stay open, which is a declared restriction; road blockage and bridge scour come later.
- Recommended.

**H2. The storm's wind field.** A typhoon moves on a straight track across the island. Its wind at each place is built in this order:
1. **The wind profile.** Use a modified Rankine profile: wind falls with the square root of distance beyond the radius of maximum wind. Its exponent of 0.5 needs only square roots. The literature range is 0.4–0.6 (Geoscience Australia). L.
2. **Sea to land.** Land keeps 0.83 of the sea wind, most of the drop within 1 km of the coast (Vickery et al. 2009). US, L.
3. **Local surface.** Use Taiwan's building wind code terrain classes: 0.476 of open-ground wind in a city core, 0.662 in a town, 1.0 in the open or on the coast. The factors are S; using them in a hazard field is J.
4. **Mountain lee.** Places in the lee of the spine keep 0.6 of the wind. The bound rests on typhoons losing over 40% of their intensity crossing Taiwan's Central Mountain Range, as quoted in Wu & Kuo 1999. Whether that 40% is wind or pressure is unconfirmed, so this factor is J.
5. **Random variation.** Add a spatially smooth random field built only from the permitted arithmetic: a Wendland kernel, valid in 2-D. Correlation length 10 km and spread 10%, both placeholders, J.

Winds are 10-minute sustained speeds, as Taiwan's weather agency (CWA) reports them. They are converted to 3-second gusts for the line fragilities: ×1.75 inland and ×1.30 at the coast (WMO). L.
- Recommended.

**H3. Storm severity.** Anchor the 0–100 severity control to Taiwan's typhoon classes, replacing the spec's "100 = every exposed element in the hazard core fails".
- Severity 0 means no storm.
- Otherwise, peak 10-minute wind at sea = 17.2 + 0.53 × severity m/s:
  - mild (17.2–32.6 m/s) is severity 1–29;
  - moderate (32.7–50.9 m/s) is 29–64;
  - strong (51 m/s and up) is 64–100, topping out at about 70 m/s.
- Severity also sets the rainfall for the flood rule, on Taiwan's Water Resources Agency flood-map ladder: 300 mm in 24 h up to severity 33, 450 mm to 66, and 600 mm above.
- The pilot runs at **severity 50**: a moderate typhoon, about 44 m/s at sea, with 450 mm of rain.
- The CWA classes are S (TW). The linear map between them is J.
- Recommended.

**H4. Flood.**
- **Flood depth** at a facility = the scenario's flood stage minus the site's height above the nearest river or stream. That height is the standard single flood index (Nobre 2011; below 5.3 m is waterlogged-prone).
- **Flood stage:** 1 m at 300 mm, 2 m at 450 mm and 3 m at 600 mm of rain. Placeholders, J, until a Taiwan depth source is read. The next document to read is the national disaster-reduction centre's flood map handbook (NCDR).
- **A facility floods out** when the depth reaches its Hazus threshold:
  - substations, power plants, and water treatment and pumping: 1.2 m (4 ft);
  - tank farms and depots: any water;
  - hospitals, clinics and blood banks: 0.15 m (0.5 ft), measured from grade;
  - telecom facilities: 1.2 m, borrowing the substation value, since Hazus maps them without a damage rule (J);
  - water storage: on-ground tanks 7.3 m (24 ft);
  - reservoirs, ports and airports: not flood-damaged in Phase 1.
- **Damage state:** up to 0.5 m over the threshold is **slight**; beyond that is **moderate**. The cut is J. The pilot storm stays within slight and moderate at facilities, as already ruled. Worlds outside the pilot may reach extensive (1.5 m over) and complete (3 m over), also J.
- US, L for the thresholds.
- Recommended.

**H5. Overhead lines.**
- **Failure chance:** a line's chance of failing in a scenario comes from a stored table indexed by 3-second gust, per km of line.
- **Anchor:** wood distribution poles fail with probability 0.02–0.12 at a 100 mph (45 m/s) gust when new, and 0.1–0.9 when old (US, L). The table is centred on 0.05 per km at 45 m/s. J for the per-km conversion.
- **Transmission towers** collapse only near 285 km/h gusts (Cyclone Fani curves, L). They never fail at pilot severity, which matches Soudelor's lines tripping rather than falling.
- **Repair:** a failed line goes back up after crew work of 6 h, with no lead time, from the nearest crew base. Placeholder, J, anchored on Taipower's typical restoration within 1–3 days of large typhoons.
- **Crews:** crews now repair lines as well as facilities, so the restorative model sequences crews across failed nodes and failed lines.
- Recommended.

**H6. What damage does to function.**
- A damaged facility is **off** (condition 0) from the storm until its repair completes, then fully back (condition 1). Slight damage repairs quickly (Hazus: about a day for most classes), which reproduces Hazus's own figure of nearly full function one day after slight damage.
- Most interdependent-infrastructure models use this failed-or-working switch (Dueñas-Osorio 2007; Ouyang & Dueñas-Osorio 2014; Lee, Mitchell & Wallace 2007). L.
- Partial capacity by damage state, where substations would be the only class with a physical basis, comes later. Declared.
- Recommended.

**H7. Hospitals.** Hospitals are damaged only by flood. Hazus's hurricane evidence is that most hospitals stay open on backup power. Their storm outages therefore come through the cascade: losing power, water or telecom, cushioned by their 72 h of fuel and water. The Hazus earthquake tables, where every damaged hospital closes for days, do not apply to a typhoon. US, L.
- Recommended.

**H8. Scenarios.**
- Each scenario draws its own track position and angle, peak wind within the severity's class band, and random-variation field.
- Each element then fails independently given the field. This is the standard Hazus structure; the literature stresses keeping the field's spatial correlation, which the shared field does (Adachi & Ellingwood 2009; Jayaram & Baker 2010). L.
- Correlation beyond the field (two nearby lines failing together for reasons the field doesn't carry) is left out and declared.
- The pilot keeps 8 scenarios, equally weighted. Published studies use 30–200. The pilot's "expected" unserved demand-hours are over these 8 as an illustrative set, not a probability estimate of real storms. That is stated in the run note.
- Recommended.

**H9. Protect condition.**
- A protected element cannot be damaged in any scenario. This is the fortification convention of defender–attacker models: Brown et al. 2006 say a defended asset "becomes invulnerable". L.
- It overstates the value of real hardening, which lowers failure chance rather than removing it, so the pilot's defensive answers are an upper bound. Declared.
- Because the pilot spec already names "a hardened pole line" as an instance, **protect condition can target an overhead line as well as a facility**. Cost 2 either way.
- Recommended.

**H10. Damage-state names.** Keep slight, moderate, extensive and complete, the Hazus lifeline names our repair times use. Hazus Hurricane's own names (minor, moderate, severe, destruction) are not used.
- Recommended.

## Decided without a ruling (technical)

- Winds are stored in m/s at 10-minute averaging, and gust conversion happens only at the line fragility.
- Every curve that needs exp or erf (tower and pole fragility, any lognormal) is built offline into a stored table in the rules registry, as the draws are.
- The field is drawn on the terrain grid. Each element reads the field at its location; a line reads its peak gust along its length.
- Every hazard rule goes in the rules registry with its source, grade and Theta role (θ\*-dynamics).
- Spec §4.4a gains the ruled crew work for extensive (72 h) and complete (168 h) damage.
- The seismic and flood-plain hazards stay switched off and unbuilt in Phase 1.

## Then

Once H1–H10 are ruled, the rulings go into spec v0.7 (§4.3 shared causes, rewritten), and Work Order 6 is drafted from them.
