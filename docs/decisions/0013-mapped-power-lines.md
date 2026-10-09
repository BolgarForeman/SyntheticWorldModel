# 0013 — Mapped power lines

- **Date:** 2026-10-02
- **Decided by:** the author (Foreman)
- **Recorded by:** Work Order 6c
- **Sources:** structure v0.8 §4.2, §4.3a (rule 4) and §4.3b; `docs/work_orders/WO-06c.md`

## Context

The world's power links were straight two-point segments. Real sources (OpenStreetMap power=line) map power lines as routed objects with towers. Both the storm and the crews depend on where a line actually runs: over a ridge or around it, near a road or far from one. Power lines therefore become mapped elements before the dynamics (Work Order 7) is built on them. This replaces Work Order 3's "straight segments in Phase 1, terrain routes in Phase 5" for power lines only.

## Decisions (2026-10-02)

1. **Mapped lines.** Power lines are elements as OpenStreetMap maps them. Each records:
   - its end points;
   - its voltage class: 161 kV from a plant and between transmission substations, 69 kV to a distribution substation unless a plant feeds it;
   - circuits;
   - its structure: towers for every mapped line, with tower points at a placeholder spacing;
   - its route and length along the route.

   **The power links keep their ids** (SWM-POW-L…), so downstream references hold. What changes is their meaning: a link's points are now its terrain route, and its length is the route's length.
2. **Any-class end points.** Mapped lines join plants and substations of any class: plant to transmission substation, plant to distribution substation, and substation to substation. A facility in another layer never draws from a plant or a line directly; it draws from a substation.
3. **Routes.** Each line follows a least-cost path over the terrain:
   - steep slope, high ground and river crossings cost more, and the sea cannot be crossed;
   - the weights are registry placeholders (J): slope 10, height 1, river crossing 0.5 km;
   - a route that crosses the spine is recorded as a ridge crossing.
4. **Feeds along roads.** Below the distribution substations nothing is mapped. The feeds to facilities exist in the true world on poles. Each runs from its substation to the nearest road point, along the roads, then straight to its consumer. Feeds are never emitted; the analyst must infer them.
5. **Any substation supplies any consumer** (§4.3a rule 4), since every substation can step down. Loads of 5 MW or more still take a transmission substation; smaller consumers take the nearest eligible substation of either class, under the concentration and supplier-not-nearest controls. The §4.3a power rows name both classes; their old supplier lists are kept in the registry's history.
6. **Ridge factor.** Every line reads the wind along its true route: mapped lines along their terrain route, feeds along their road route. On isolated hills, ridges and escarpments the wind is raised by Taiwan's building wind code topographic factor (建築物耐風設計規範及解說 §2.6, Formula 2.8, Tables 2.3(a)–(c)), where the code's conditions hold. The factor is S (TW); its use on power lines is J.
7. **Off-road crew travel.** A crew reaches a line failure by road to the road point nearest the failure, then off road at a placeholder 2 km/h (walking and carrying, J).

## Later phases (recorded at the author's request; structure v0.8, "Changes from v0.7")

- Per-scenario sharing rules when a supplier is short: pro rata, priority lines, full support until exhausted, and others.
- Partly failed lines.
- Line capacity limits after Phase 1.
- A power-flow model in Phase 5.
- Routing of water mains, pipelines and fibre, if the data supports it.

## Addendum: answers to PR 14 (2026-10-03)

- **Decided by:** the author (Foreman)
- **Source:** `docs/work_orders/WO-06c-answers.md`; structure v0.8 §4.3b as corrected on the branch

Reading the ridge factor for the worst of eight directions everywhere is the code's design envelope, not one storm. It put a speed-up on 55% of the pilot's land and broke the PR 6b tower limit.

1. **The storm's own direction.** Each place reads the topographic factor for the direction its wind blows at its peak, snapped to the nearest of the 8 grid directions (largest dot product; ties go to the lowest index):
   - to the right of the track the wind travels along the track's direction of travel, and to the left against it;
   - within the radius of maximum wind a place meets the eyewall from both sides and takes the worse of the two directions;
   - the inflow angle is neglected (J);
   - the rotation is the new registry rule `storm.rotation: counterclockwise` (Northern Hemisphere, J), because every storm rule is taken from Taiwan;
   - the isolation check reaches min(100H, 3.22 km) upwind of the crest, the code's own reach.
2. **Towers designed for their site.** New registry rule `storm.towers_designed_for_site` (J, placeholder, default false). When true, a tower reads its gust divided by its site's worst-direction factor at tower height. The default is ruled after both result tables are seen.
3. **Recalibration.** The pole-line median is recalibrated with `tools/calibrate_line_curve.py` at a spread of 0.4, with towers not designed for their site. The best single median within 5 points of both targets is stored, and 159.9394 m/s moves to the rule's history ("recalibrated for routed lines and the directional ridge factor").
4. **The pilot's edge range** is 40–55, widened from 40–50, because rule 4 added a feed (`docs/design/Pilot_Spec.md`).
5. **Kzt** = (1 + K1K2K3)², so wind speed takes 1 + K1K2K3, as implemented. The spec is corrected.
6. **Feeds from transmission substations run on poles,** as built. The spec is corrected.
7. **Circuits** stay at 1 as a placeholder. In Phase 1 a failed line fails whole.
8. **Local road density below the mapped transport layer is not modelled; off-road legs are therefore long.** This is a declared limitation of Phase 1.
9. **The pilot needs no mutual pair.** Its `two_way_pct` is 0, and the hand trace needs no loop. The generic tests of the "keep a mutual pair" rule stay.

The mast-to-mast and reservoir-to-reservoir links found by the A2 audit are generator bugs. They become Part 0 of Work Order 7.

## Second addendum: second answers to PR 14 (2026-10-09)

- **Decided by:** the author (Foreman)
- **Source:** `docs/work_orders/WO-06c-answers-2.md`; structure v0.8 §4.3b as updated on the branch

Reading the storm's own direction cut the ridge factor's coverage, but a crest is sped up from either side, so the pilot's peak gust rose to 135.7 m/s, about 40% above Taiwan's highest measured gust.

1. **Ceiling on the speed-up.** The factor on the wind is min(1 + K1K2K3, ceiling), for every structure. The code still decides where the speed-up applies and its shape; the observed record decides how much.
   - **Rule:** `storm.ridge_factor_ceiling` (J; new registry status `calibrated`).
   - **Calibration:** set by `tools/calibrate_ridge_ceiling.py` so that the pilot's highest 3-second gust at pole height, over its 8 scenarios, equals 95.2 m/s. That is Taiwan's highest measured gust: Lanyu, Typhoon Koinu, 2023, a moderate typhoon (CNA; Newtalk). The previous Lanyu peak was 89.8 m/s, in Typhoon Alex, 1984.
   - **Value:** 1.169085, stored to 2 decimals as **1.17**, which gives 95.27 m/s.
   - **Towers:** the tower design factor does not take the ceiling.
2. **Towers designed for their site:** `storm.towers_designed_for_site` is ruled **true**; false moves to its history.
3. **Recalibration.** The pole-line median is recalibrated at a spread of 0.4 with the ceiling and the tower setting in place. It is **163.6914 m/s**: pilot 7.8%, severity 70 32.1%, both within 5 points. 201.7763 moves to history.
4. **Two isolation tests.** The code's two isolation conditions are tested separately:
   - (a) the feature stands more than twice the terrain within 3.22 km upwind;
   - (b) nothing of similar height lies within min(100H, 3.22 km) upwind.

   Both must hold, with H/Lh ≥ 0.2, the minimum height and the upper half.
5. **Spec text.** The design side updates §4.3b's achieved shares after the report. No spec edits on the coding side.
