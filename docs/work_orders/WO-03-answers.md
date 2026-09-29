WORK ORDER 3 — ANSWERS FROM THE DESIGN SIDE (2026-09-28, confirmed by Foreman)

Build to these, and record them in decision 0006 alongside Part E. The probes you ran before building were the right move.

1. Airport flat run: accept your definition.
   - A straight run of at least 2.5 km in one of the four directions.
   - Every cell on land, and none on river or wetland.
   - Height varying by no more than 2% of the run's length (50 m).
   - Within about 5 km of a city.
   - Weighted draw among the qualifying runs.
   - All numbers are CHOICE.
   - Record the runway as a line (both end points) in the node's truth geometry, as well as the airport's point.

2. When a siting rule can't be met: option (b), with one hard floor.
   - The node goes to the best available site, and a siting note records which rule was relaxed and by how much. The note appears in the layer statistics, is printed by `swm layers`, and later goes into the truth manifest.
   - Hard floor: if a class has no eligible land cell at all (every candidate is sea, river or wetland), the stage fails with an error naming the class and the rule. That is option (a), and it can only happen on degenerate recipes.
   - Nothing is ever silently regenerated.
   - Add a test that a mountainous, river-free recipe builds, with the expected notes.

3. The bridge in a one-city world: accept your proposal.
   - Put it where the road from the city to the airport, freight yard or seaport crosses a river.
   - If no road crosses a river, rule 2 applies: the bridge goes on the river cell nearest the road network, joined by a short spur road, with a siting note.

4. Roads across the sea: not acceptable, even in Phase 1. A road over a bay is wrong in the truth, and it would mislead a hand trace. This rule is about sea cells only: bays, inlets and open water off the coast.
   - Rivers are different. Roads cross rivers normally. The one explicit bridge node sits on such a crossing.
   - Other river crossings are part of their road link and cannot fail on their own in Phase 1. Record their count per link as river_crossings in the truth, so later work orders can promote them to bridge nodes.
   - A transport link whose straight line crosses the sea becomes the shortest two-segment path through a land waypoint: a dog-leg polyline. Record its true length.
   - If no single waypoint works, use the shortest land path on the grid, simplified to a polyline, and add a siting note.
   - Other layers may cross the sea on straight lines, because submarine power cables, telecom cables and pipelines are real. Mark such links with crosses_sea = true in the truth.
   - Link geometry becomes a polyline in general. A straight link is a two-point polyline.
   - Terrain-following routes on land remain Phase 5.

5. Rail: no rail in Phase 1, and no schema switch. Larger worlds get road junctions only. Record it.

6. Attributes: accept your table, with these corrections and notes.
   - Distribution voltage is 22.8 kV or 11.4 kV (Taipower's levels), not 22.
   - Transmission is 345 kV or 161 kV. Also allow 69 kV at transmission substations serving small loads.
   - Keep these marked as Taiwan placeholders (open decision: realism ranges).
   - Airport size classes use OurAirports' own values: small_airport, medium_airport, large_airport.
   - Seaport harbour sizes use the World Port Index's values: V, S, M, L (very small to large).
   - Freight yards carry area_m2. Bridges carry length_m and deck class (road). Neither has a size class.
   - Operator: telecom only in Phase 1, as in the mockup.
   - Put every range in the attribute CHOICE table with its unit.

7. Stream record change from the osm_transport rename: expected. Explain it in the pull request, alongside the terrain hash change from E1.

Proceed to the pull request.
