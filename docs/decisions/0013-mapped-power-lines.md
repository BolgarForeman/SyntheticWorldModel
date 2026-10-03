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
