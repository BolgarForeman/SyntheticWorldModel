# Degradation profiles by node class, v0.3 (ruled)

*2026-10-10 · ruled by Foreman · companion to Dynamics Ruling Sheet v0.3 · supersedes v0.2 · each profile is a single-node test in Work Order 7*

**Changes from v0.2** (ruled 2026-10-10, PR 7b answers): generation fuel and airport fuel corrected to the world as built; hospital water refills from the main.

**Changes from v0.1:** the four gaps are ruled (see the end); every limit now carries a range and a relaxed value.

## How to read a profile

Each profile says what happens to one node when each of its supplies is cut at hour 0, with everything else intact. It is built only from rules already ruled:
- the dependency table (§4.3a);
- failure modes (D2);
- reserves and tolerance (§4.4a);
- buffers and refill (D5);
- repair (D6).

**Notation:**
- **State** runs from 1 (full) to 0 (out).
- **Trip:** off while the share received is below 90%.
- **Throttle:** runs at the share received.
- **Floor:** drops to a fixed level.
- **T / d:** telecom tolerance. Full function for T hours, then the degraded level d. Public share κ deepens it: d_eff = 1 − κ(1 − d).
- **The node's state** is the lowest of its responses at each step (typed weakest link).
- **Restoration:** every supply that returns lifts its response at once.

"Gap" marks a point the rules do not settle; each gap comes to Foreman for a ruling.

## Power

**Generation** (thermal: LNG, oil or coal)
- **Fuel cut:** LNG and oil plants trip: their stocks are held upstream, at the import terminal and the tank farms, not at the plant (gas-fired plants are fed by pipeline and hold almost no gas on site). Coal plants run on their own 30-day pile, so a cut has no effect inside 72 h.
- **Water cut:** Taiwan's large thermal plants cool with seawater, so the mains supplies boiler and process water, not cooling. The plant runs on its stock of purified (demineralized) water, default 24 h (range 6–48 h; relaxed value unlimited), then trips. The stock refills from the mains once it returns. Source: India's standard for demineralization plants, IS 13268:1992 §4.2.3, "Normally, in power plants clients prefer to have the storage capacity for 16 to 24 hours" (L, India); Taipower's environmental impact statements are flagged as the Taiwan source to replace it.
- **Telecom (control) cut:** 12 h at full, then 0.95, scaled by the 20% public share. Effectively no effect.

**Transmission substation**
- **Power in (its line from the plant) cut:** throttle at the share received. One line, so 0 until repaired.
- **Telecom cut:** no supply effect. Remote switching is lost: when a repair elsewhere should re-energize this substation, power returns only after a crew travels there and switches by hand. Time on site 1 h (range 0.5–2 h; relaxed value zero), plus travel calculated from distance exactly as for repair crews (road, then off road), uncapped. The trip uses a crew like any other job. It does not apply when the repair is at the substation itself (J; no published figure found).

**Distribution substation**
- **Power in cut:** throttle at the share received. Through two lines (L0002 and L0004), either one supplies it, so it holds at 1 until both fail.
- **Telecom cut:** as for a transmission substation.

## Telecom

**Exchange**
- **Power cut:** the battery covers first, then the generator (24 h fuel), then deliveries every 24 h after hour 12. On battery and generator it holds at 1. It trips only if the generator fails to start and the battery runs out, or the fuel chain breaks.
- **When power returns:** the battery recharges in 12 h; the tank refills only by delivery.

**Mast**
- **Power cut:** 4 h battery at full, then trip to 0. The pilot's masts have no generator (Work Order 5 answers).
- **Backhaul (telecom link) cut:** 0 at once. Nothing covers lost backhaul.
- **When power returns:** the battery recharges in 12 h, so a second outage soon after leaves it with less than 4 h.
- **Emergency:** a mobile cell site restores it to 0.5 about 14 h after dispatch, if the mast is damaged.

**Data centre**
- **Power cut:** generator with 72 h fuel; holds at 1.
- **Water (cooling) cut:** runs on its stock of make-up water, default 12 h (range 0–48 h; relaxed value unlimited), then trips. Source: Uptime Institute, "a Tier III facility requires 12 hours of Concurrently Maintainable makeup water"; "many owners have chosen to exceed 12 hours" (industry standard, US). Air-cooled data centres with no water dependency are a later option.

**Cable landing**
- **Power cut:** generator with 48 h fuel; holds at 1, then trips unless resupplied.

## Water

**Reservoir**
- **Telecom (control) cut:** 72 h at full, then 0.95. Effectively no effect.

**Water treatment**
- **Power cut:** generator with 48 h fuel. Throttle when its generator can't carry it.
- **Telecom cut:** 24 h at full, then 0.9 scaled by the 50% public share, giving 0.95.

**Pumping**
- **Power cut:** throttle at the share received (a multi-pump station runs fewer pumps). A pre-positioned generator covers it only where the recipe's share places one.
- **Telecom cut:** 12 h at full, then 0.8 scaled, giving 0.9.

**Water storage**
- Consumes nothing. When the pumps feeding it fall short, it drains at the downstream draw until empty, then its consumers lose water.
- When the pumps return, it refills from their spare capacity while still serving demand.

## Transport

**Seaport, freight yard**
- **Power cut:** no power means no cargo. Backup power for cargo handling: default 0 h (range 0–48 h, where 48 h means a highly reinforced port that can still work cargo; relaxed value unlimited). Ports' dependence on power for cranes, pumps, security and digital operations: TT Club (2026). Later: distinguish crane-dependent terminals from roll-on/roll-off (drive-on, drive-off) terminals, which need far less power to move cargo.
- **Telecom cut:** 24 h at full, then 0.5.
- **Fuel cut:** throttle.

**Airport**
- **Power cut:** trip.
- **Telecom cut, towered:** trip at once (T = 0, d = 0.2, mode trip).
- **Telecom cut, not towered:** 24 h at full, then 0.8.
- **Fuel cut:** pipeline-fed airports trip; truck-fed airports throttle (fewer flights on the fuel that arrives).

**Bridge, road junction**
- No supplies, and not damaged in Phase 1.

## Fuel

**Import terminal**
- **Power cut:** trip.
- **Telecom (control) cut:** 12 h at full, then 0.8, scaled by the public share.
- **Transport (seaport) cut:** throttle.

**Tank farm**
- **Power cut:** trip.
- **Telecom (control) cut:** pipeline-connected, 1 h at full then 0.5; truck-fed, 12 h then 0.6.

**Depot**
- **Power cut:** trip.
- **Telecom cut:** 12 h at full, then 0.6.
- **Road (transport) cut:** throttle.
- **When the depot is out, every buffer-resupply delivery it makes stops.** This is the "buffer has a buffer" chain.

**Refinery**
- **Power cut or water cut:** trip.
- **Telecom cut:** 72 h at full, then 0.8.

## Healthcare

**Tertiary and regional hospital**
- **Power cut:**
  - The generator fails to start 0.13% of the time; if it fails, the hospital is at 0.
  - If it starts, the hospital drops to the floor of 0.6 (essential services) with about 72 h of fuel at essential load.
  - Deliveries come at 12 h, then every 24 h, while the depot and road are up. In practice it holds at 0.6 indefinitely unless the fuel chain breaks.
- **Water cut:** drops to the emergency ration and runs on stored water, about 72 h, then trips. The stored water refills from the main once supply returns.
- **Telecom cut:** records on site, 24 h at full then 0.85; records hosted off site, 0.5 h at full, ramping to 0.65 by 4 h.
- **Supplies (transport) cut:** 72 h of stock, then throttle.

**Clinic**
- **Power cut:** trip at once; no generator by default.
- **Water cut:** trip.
- **Telecom cut:** 24 h at full, then 0.8.
- **Supplies (transport) cut:** throttle.

**Blood bank**
- **Power cut:** generator with 72 h fuel, then trip unless resupplied.
- **Blood stock:** 7 days.
- **Telecom cut:** 24 h at full, then 0.7.

## Gaps, as ruled (2026-10-09)

1. **Generation make-up water:** a stock of purified boiler water, 24 h default, range 6–48 h. Cooling is by seawater, so the mains dependency is boiler and process water.
2. **Substation telecom loss:** a manual switching trip, 1 h on site (0.5–2 h) plus calculated travel, using a crew. Replaces the ×1.5 placeholder.
3. **Data centre make-up water:** 12 h default (Uptime Tier III minimum), range 0–48 h.
4. **Seaport backup power:** 0 h default, range 0–48 h; no power means no cargo. Crane versus roll-on/roll-off terminals later.

## Ranges and relaxed values (ruled 2026-10-09)

Every limit in these profiles is a registry rule with a default, a range, and a relaxed value: **unlimited** for stocks and capacities (fuel, batteries, water, backup power, crews, pump capacity), **zero** for delays and losses (lead times, travel, switching time, telecom tolerance loss). A recipe can relax any limit by name, one at a time or all but one, for sensitivity runs. Relaxing is stored as a flag, never as a large number. Relaxing a limit is distinct from removing the dependency: an unlimited water stock keeps the plant dependent on the main, but the dependency never bites. Every run records which limits it relaxed, in the Theta List. A test proves that relaxing a limit never makes the outcome worse.

Every profile becomes a test in Work Order 7: isolate the node, cut one supply at hour 0, run 72 h, and compare against the profile above. Each limit is also tested at its relaxed value.
