# Hand trace of scenario 7: design side

*v0.1 · 2026-10-11 · design side (Claude), one of two independent traces (Foreman's ruling C) · sealed until Foreman's trace is done*

**Independence.** This trace never read:
- the engine's code (`src/swm/dynamics/`);
- the saved reference runs (`tests/golden/pilot_reference_runs/`);
- the pack's timeline pages (`tables.pdf` pages 5–6, `timeline.csv`).

**Sources used:**
- the pack's nodes, dependencies and damage tables, and the map;
- the spec, World_Generator_Structure v0.12 §4.4a and §4.5;
- for what the pack lacks:
  - the truth manifest;
  - the layers-stage link records;
  - the scenarios stage output (failure-point positions), from running the generator's stages only.

Each lookup outside the pack is listed in the last section.

## 1. The damage

| Element | What it is | Failure points (km along the line) | Crew work |
|---|---|---|---|
| SWM-POW-L0004 | power line, plant (POW-0001) → distribution substation POW-0003, on towers, 2.78 km | 1 (km 1.39) | 72 h (towered) |
| SWM-TEL-L0001 | telecom line, exchange (TEL-0001) → mast TEL-0002, 20.9 km | 1 (km 12.5) | 6 h |
| SWM-TEL-L0002 | telecom line, exchange (TEL-0001) → mast TEL-0003, 15.6 km | 2 (km 9.5, 11.5) | 2 × 6 h |

No facility is damaged.

## 2. What the damage cuts

**Power (L0004).**
- POW-0003 is fed both directly from the plant (L0004) and from the transmission substation POW-0002 (L0002).
- With L0004 down, POW-0003 still receives full supply through POW-0002. There are no line capacity limits in Phase 1 (§4.5: no power-flow model).
- So no power node loses supply, and every electricity coupling delivers in full for the whole run.
- No substation is ever de-energized, so no manual switching trip arises.

**Telecom (L0001, L0002).**
- Within-layer links carry the layer's commodity from the first stage down (§4.5, "Links and lines"). A mast receives service from the exchange over its line.
- Mast TEL-0002 (line L0001) and mast TEL-0003 (line L0002) receive nothing from hour 0. Their state is 0 under either response, throttle (R = 0) or trip (R < 0.9).
- Their batteries are not drawn: the masts' power is intact, and a battery buffers power, not backhaul.
- Mast TEL-0004 (line L0003, intact) is unaffected.

**Knock-on through the switched-on couplings.**
- **TEL-0002** supplies no switched-on coupling (CPL-0035 is off). No knock-on.
- **TEL-0003 → POW-0003** (CPL-0026, communications, κ 0.5, threshold). POW-0003 still receives 0.5 from TEL-0004 (CPL-0027). Its tolerance row:
  - substation, T = 12 h, d = 1.0;
  - so d_eff = 1 − κ(1 − d) = 1;
  - no supply effect at any hour.
- **TEL-0003 → POW-0004** (CPL-0029, κ 0.5, threshold). POW-0004 still receives 0.5 from the exchange (CPL-0028). Same tolerance, d_eff = 1, so no effect.
  - POW-0004's listed failure mode on telecom is trip. I read §4.5 as "the tolerance acts first, then d_eff", so the trip never applies while d = 1 (see question 3).
- **No other switched-on coupling** has a mast as supplier. The exchange, plant, substations, water, fuel, transport and hospitals keep full supply for 72 h. No stock is drawn and no fuel delivery is triggered.

## 3. Crews

**Setup:**
- 2 crews at base CRB-0001, by the airport.
- Default order:
  1. towered lines and transmission substations;
  2. distribution substations and feeds to end uses;
  3. everything else.
- Ties go to the shorter travel, then the lower id.

**Jobs:**
- L0004 is priority 1.
- The two telecom lines are priority 3 (or priority 2 if a line to a mast counts as a feed to an end use). Either way they rank equal, and the tie goes to the shorter travel:
  - TEL-L0002's first point: 2.999 h from base;
  - TEL-L0001's point: 4.504 h.
- So TEL-L0002 comes first.

**Crew 1: L0004.**

| Hours | Activity |
|---|---|
| 0 → 1.798 | travel to km 1.39 (road 1.01 km, then 3.55 km off road at 2 km/h) |
| 1.798 → 3.798 | crew-bound lead, 2 h |
| 3.798 → 75.798 | repair, 72 h |

L0004 is not back inside the 72 h horizon. That changes no supply, because of the redundant feed.

**Crew 2: TEL-L0002, then TEL-L0001.**

| Hours | Activity |
|---|---|
| 0 → 2.999 | travel to TEL-L0002 km 9.5 (road 5.45 km, then 5.72 km off road) |
| 2.999 → 4.999 | crew-bound lead, 2 h (once per job) |
| 4.999 → 10.999 | repair point 1 |
| 10.999 → 11.999 | travel 2.0 km along the line, off road, to km 11.5 (1.0 h) |
| 11.999 → **17.999** | repair point 2. **TEL-L0002 is restored, and mast TEL-0003 is back.** |
| 17.999 → 18.566 | travel to TEL-L0001 km 12.5. The two points are 1.13 km apart, crossed off road directly (0.567 h); see question 1. |
| 18.566 → 20.566 | crew-bound lead, 2 h |
| 20.566 → **26.566** | repair. **TEL-L0001 is restored, and mast TEL-0002 is back.** |

Crew 2 has no job left after 26.566 h. There are no emergency units to place: the mobile cell site goes to damaged masts, and no mast is damaged.

## 4. Result

The engine works in 15-minute steps, so a repair that completes inside a step takes effect at the end of that step.

| End-use node | State | Hours out |
|---|---|---|
| SWM-TEL-0003 (mast) | 0 from hour 0 to 18.00 | **18.00** (17.999 continuous) |
| SWM-TEL-0002 (mast) | 0 from hour 0 to 26.75 | **26.75** (26.566 continuous) |
| every other node | 1 for all 72 h | 0 |
| **Total** | | **44.75 h** (44.57 continuous) |

**Last repair inside the horizon:** TEL-L0001 at 26.566 h. L0004 completes at 75.798 h, outside it.

**Stocks:** none drawn. **Deliveries:** none. **Manual switching trips:** none.

## 5. Readings the spec leaves open (to compare with Foreman's trace and the engine)

1. **Travel between jobs.** Crews move job to job, but the world records travel only from the base.
   - I crossed off road directly between nearby failure points (0.567 h).
   - Going back to the road and along it would take about 8 h, and TEL-0002 would return near 34 h.
2. **Crew-bound lead per failure point or per line.** I applied it once per line ("one line is one job"). Applied per failure point, TEL-0003 returns at 20.0 h and TEL-0002 at 30.6 h.
3. **Tolerance versus failure mode.** I read "the tolerance acts first, then d_eff" as replacing the failure mode on telecom after T. If instead the failure mode applies after T, POW-0004 (telecom: trip) trips at 12 h until TEL-0003 returns at 18 h. Every load it feeds also has a POW-0002 feed, so even then nothing goes out, unless a dual feed needs both feeds.
4. **Two in-feeds to one node.** I read each feed as able to carry the whole need, with no capacity limit. If supply were instead shared by feed (say ½ each), a lost feed would leave R = 0.5.
5. **Which nodes are end uses.** The 15 scored end uses are not listed in the pack. My total assumes the masts are end uses.

## 6. What the pack lacked (the fix list)

I had to look outside the pack for each of these:
1. **Within-layer links:** id, from, to, length, on towers or not, and how a node with two in-feeds combines them.
2. **Damage:** each failure point's position along its line, and its travel time from the base.
3. **Crews:**
   - count and base;
   - travel time to every node and failure point;
   - the rule for travel between jobs;
   - each job's priority group and the Lifeline weights.
4. **Rules with numbers:**
   - crew-bound lead and parts lead per element;
   - line work per failure point;
   - manual switching time;
   - trip point, floor and threshold;
   - tolerance T, d, κ and d_eff per node;
   - battery recharge;
   - delivery timing and size;
   - refill rules;
   - step length.
5. **Nodes:**
   - the end-use flag and service weight;
   - capacities (plant, treatment, pumps);
   - stock quantities and draw rates;
   - generator fail-to-start and fail-to-run draws;
   - the manual-switching flag.
6. **Dependencies:** feed configuration (single or dual), and which edges are fuel-resupply edges.
7. **Map:**
   - the eastern cluster is unreadable;
   - line ids and failure points are not marked;
   - the frame is stretched to the storm track.
8. **Answer key:** the timeline pages sit in the same pack. A blind trace needs them printed separately.
