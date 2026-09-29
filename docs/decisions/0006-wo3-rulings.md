# 0006 — Work Order 3 rulings

- **Date:** 2026-09-28 (answers) and 2026-09-29 (the two follow-up rulings)
- **Decided by:** the design conversation, confirmed by Foreman
- **Recorded by:** Work Order 3
- **Full text:** `docs/work_orders/WO-03.md` (Part E) and `docs/work_orders/WO-03-answers.md`

## Context

Work Order 3 puts the infrastructure on the ground, anchors the world at Point Nemo, and adds the first GIS export. Before building, the code side probed the pilot island. As literally read, the airport's flat run fails on every island tested, and some other siting rules can fail on real islands. The answers set how those cases are handled. Two further questions came up after the answers; Foreman ruled on both.

## Decisions

### Part E (Work Order 3)

- **E1 Peak height.** After relief is carved, elevation is rescaled so the highest point equals 100 m + mountainous/100 × 3,900 m, to within 1 dm. The pilot's peak becomes 2,440 m, and the terrain golden hashes change.
- **E2 Source scope and the OpenStreetMap backbone.**
  - Each source declares the node classes it can carry, in `SOURCE_SCOPES` in the schema, with a source note per row.
  - OpenStreetMap is the backbone on every layer; the specialised sources cross it. WRI carries generation, OurAirports airports, the World Port Index seaports, and the facility register healthcare facilities.
  - A world node whose class no switched-on source covers is real but unemitted. It is reported per layer, and the truth manifest will record it.
  - `osm_roads_rail` is renamed `osm_transport` ("OpenStreetMap transport"). Its scope is every transport class.
  - OpenInfraMap is built from OpenStreetMap, so its errors are correlated with OpenStreetMap's.
  - The pilot uses OpenStreetMap on every layer, plus WRI (power), the facility register (healthcare) and OurAirports (transport).
- **E3 Design README.** The version column shows structure v0.4.

### Answers to the pre-build questions

1. **The airport's flat run.**
   - It is a straight run of at least 2.5 km, in one of four directions (north–south, east–west, or one of the two diagonals).
   - Every cell must be land, and none river or wetland.
   - The height may vary by no more than 2% of the run's length (50 m).
   - The run's middle must lie within about 5 km of a city.
   - The site is a weighted draw among the qualifying runs.
   - All the numbers are CHOICE.
   - The runway is recorded as a line (both end points) in the node's truth geometry, as well as the airport's point.
2. **When a siting rule can't be met.** The node goes to the best available site, and a siting note records which rule was relaxed and by how much. The note appears in the layer statistics, is printed by `swm layers`, and will go into the truth manifest.
   - **Hard floor:** if a class has no eligible land cell at all, the stage fails with an error naming the class and the rule.
   - Nothing is ever silently regenerated.
3. **The bridge in a one-city world** sits where the road from the city to the airport, freight yard or seaport crosses a river. If no road crosses a river, it goes on the river cell nearest the road network, joined by a spur road, with a siting note.
4. **Roads never cross the sea** (bays, inlets, open water off the coast).
   - A transport link whose straight line would cross the sea becomes the shortest two-segment path through a land waypoint. If none works, it uses the shortest land path on the grid, simplified to a polyline, with a siting note.
   - Rivers are crossed normally. Each link records its other river crossings as `river_crossings`, so later work orders can promote them to bridge nodes.
   - Other layers may cross the sea on straight lines (submarine power cables, telecom cables, pipelines), marked `crosses_sea = true`.
   - Link geometry is a polyline in general; a straight link is a two-point polyline.
   - Links are straight segments in Phase 1. Terrain-following routes on land are Phase 5.
5. **Rail.** There is no rail in Phase 1 and no schema switch. Larger worlds get road junctions only.
6. **Attributes.** Every range is in the attribute CHOICE table with its unit. The voltages are Taiwan placeholders (open decision: realism ranges).
   - **Power:**
     - `capacity_mw` for generation;
     - `capacity_mva` for substations;
     - `voltage_kv`: transmission 345 or 161 kV (69 kV at substations serving small loads), distribution 22.8 or 11.4 kV (Taipower's levels);
     - `fuel_type` for generation.
   - **Transport:**
     - airport `size_class` in OurAirports' values (`small_airport`, `medium_airport`, `large_airport`);
     - seaport `size_class` in the World Port Index's values (V, S, M, L);
     - freight yards carry `area_m2`;
     - bridges carry `length_m` and `deck_class` (road);
     - neither freight yards nor bridges have a size class.
   - **Telecom:** only telecom carries `operator` in Phase 1.
7. **Hash changes.** The stream record changes because of the `osm_transport` rename, which is expected and explained in the pull request, alongside the terrain hash change from E1.

### Follow-up rulings (2026-09-29)

- **The bridge on a river-free island** sits at the main road's lowest land crossing of a valley (a viaduct), with a siting note. Counts stay exact. This refines answer 2's hard floor: the floor applies to classes with no eligible land at all, not to a bridge whose river cells are absent.
- **Tree layers.** Water and fuel keep their tree signature and stop at n − 1 links, with a note giving the realised against the recipe value. They are tested against the tree's maximum.
- **The feasible range for links per node.** A connected layer needs at least n − 1 links, and a small layer can't hold more than a complete graph. The realised links per node are compared with the recipe value held within that feasible range, and a note records any shortfall or excess.
