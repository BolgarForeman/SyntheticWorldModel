WORK ORDER 6c — Mapped power lines

Branch: wo6c/power-lines. It already exists on GitHub, holding this work order and docs/design/World_Generator_Structure.md at v0.8 (§4.2 mapped power lines; §4.3a rule 4; §4.3b routes and ridges; repair travel). Build on it. One pull request.

Why: the world's power links are straight two-point segments. The real sources (OpenStreetMap power=line) map power lines as routed objects with towers, and the storm and the crews both depend on where a line actually runs: over a ridge or around it, near a road or far from one. This work order makes power lines mapped elements before the dynamics (Work Order 7) are built on them.

Spec: World_Generator_Structure.md v0.8 §4.2, §4.3a (rule 4), §4.3b. CLAUDE.md. Decisions 0001–0012, and 0013 below. The spec is the authority; raise anything that clashes with the terrain or the layers as built.

PART A — POWER LINES AS ELEMENTS (layers stage)

A1 Each power link becomes a mapped power line: id, end points (a plant or a substation of any class), voltage class, circuits, structure (towers), route, tower points, length along the route. Keep the existing link ids so downstream references hold; record the change of meaning in decision 0013.

A2 Which lines exist: mapped lines join plants and substations of any class. Keep the pilot's five (L0001–L0005), including the two plant-to-distribution-substation lines (realistic in Taiwan: 161 kV distribution substations fed straight from a plant). Audit every layer's links for any link that joins classes its signature does not allow, and report; do not change other layers' links in this PR.

A3 Route: least-cost path on the terrain grid (8 neighbours, deterministic tie-breaking by cell index), with per-cell cost = step length × (1 + slope weight × slope + height weight × elevation ÷ peak), plus a fixed cost per river crossing; sea cells impassable. Weights are registry placeholders (J); start at slope weight 10, height weight 1, river crossing 0.5 km equivalent, and report each pilot line's route length against its straight length and whether it crosses the spine. Do not tune to a target.

A4 Voltage: 161 kV for lines leaving a plant and between substations; 69 kV for lines to a distribution substation unless it is fed from a plant (161 kV). Placeholder (J), registry.

A5 Tower points along each route at a 350 m placeholder spacing (J; typical 161 kV spans run 300–400 m). Record them; emission (Work Order 8) will need them for OSM power=tower nodes.

A6 Only the integer-safe arithmetic is allowed (+, −, ×, ÷, sqrt); a Dijkstra on the grid needs nothing else.

PART B — FEEDS ALONG ROADS (couplings stage)

B1 Power feeds from a substation to its consumers run along the road network in the true world: substation to its nearest road point, along roads to the consumer's nearest road point, then the last leg straight. On poles. Record the route and length. They are never emitted (they stay unobserved; the separation test covers them).

B2 Rule 4 change: any substation can supply any power consumer. Loads of 5 MW or more still take a transmission substation; smaller consumers take the nearest eligible substation of either class, under the concentration and supplier-not-nearest controls. Update the §4.3a power rows' supplier lists in the registry (history kept, decision 0013). Report every pilot feed that changes supplier.

PART C — THE STORM READS ROUTES (scenarios stage)

C1 Lines read the wind kilometre by kilometre along their true route: mapped lines along the terrain route, feeds along the road route. Replace the straight-segment cell walk.

C2 Ridge and hill speed-up: apply Taiwan's building wind code topographic factor, Kzt = 1 + K1·K2·K3 (§2.6, Formula 2.8; Tables 2.3(a)–(c)), where its conditions hold. Wind speed × √Kzt. Fetch the code (https://windexpert.ce.tku.edu.tw/newcode/Dfiles/New_wind_code.pdf), quote Formula 2.8 and Tables 2.3(a)–(c) in the registry, and store K3 from the code's table (it needs exp otherwise). How H and Lh are measured on the grid is your CHOICE; state it. Use line height 30 m for towers and 10 m for poles (J) for K3.

C3 Re-run the PR 6b calibration tool with routed lines at β 0.4. If the pilot and the severity-70 fixture leave their ±5-point windows around 10% and 30%, report the new shares and the median that restores them; do not change the stored median without a ruling.

PART D — CREWS REACH THE FAILURE POINT (repair stage)

D1 Line repair travel: road travel from the crew's position to the road point nearest the failure point, then the off-road distance at a placeholder 2 km/h (walking and carrying; J). Record per failure point.

PART E — RECORD AND PREVIEW

E1 docs/decisions/0013-mapped-power-lines.md: the rulings of 2026-10-02 (mapped lines, any-class end points, routes, feeds along roads, any substation supplies any consumer, ridge factor, off-road crew travel), and the later-phase list in spec v0.8 "Changes from v0.7".

E2 `swm layers --preview` (or the storm preview) shows the routed power lines with tower points, and the feeds' road routes in a lighter style. Post the pilot preview and one storm scenario preview in the PR.

TESTS
- Routes: deterministic on both platforms; never cross sea; every route starts and ends at its line's end points; a route over the spine is flagged.
- Least cost: on a constructed grid with a ridge and a valley, the route takes the valley when the detour is cheaper and crosses when it is not.
- Feeds: follow roads; never emitted (separation).
- Rule 4: a 5 MW load takes a transmission substation; a small load takes the nearest substation of either class.
- Ridge factor: Kzt reproduces the code's table values at their knots; 1 off the feature; not applied where the conditions fail.
- Storm: kilometre walk along the route; property test that a longer exposed route never lowers a line's failure chance.
- Identity (golden) on both platforms; explain every golden change (layers, couplings, scenarios, repair).

Out of scope: the dynamics (Work Order 7); emission (Work Order 8); routing of water mains, pipelines and fibre; line capacity limits; partial line failures; power flow.

Report in CLAUDE.md §11 format, including per pilot line: straight vs routed length, ridge crossing, voltage, towers; feeds that changed supplier; the new calibration shares.
