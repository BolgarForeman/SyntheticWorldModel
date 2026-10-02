WORK ORDER 6, PR 6a (#12) — ANSWERS (design side, 2026-10-02, confirmed by Foreman)

Apply these as one follow-up commit on wo6/hazards, before merge. Spec §4.3b on this branch is already updated to match (v0.7, "Changes from v0.6" note). Record them as an addendum to docs/decisions/0012. Every changed registry value moves its old value into history, citing decision 0012.

Context from the design review of the scenario 0 preview:
- the lee comes out in stripes across the island (measured against jagged crest cells);
- every scenario hits the whole island at full strength (R_max > island, every track over land), so the 8 scenarios barely differ;
- the pilot's only power plant (POW-0001, 0.1 m above drainage) floods in all 8 scenarios, which would make every scenario a total generation loss and the defensive answer trivial.

1. Profile and scenario variety. Keep "peak over the passage". Each scenario draws:
   - its closest approach to the island's centre, 0–40 km (so some tracks pass offshore);
   - its radius of maximum wind, 20–60 km.
   Both ranges J, placeholders, in the registry. Report per scenario: closest approach, R_max, share of land inside R_max.

2. Flood varies by scenario, and power facilities stand on platforms.
   - Each scenario draws its 24 h rainfall within ±75 mm of its severity's rung (moderate 375–525 mm); flood stage = (rain − 150 mm) ÷ 150 mm, in metres (300 → 1, 450 → 2, 600 → 3). J.
   - Power plants and transmission substations stand on platforms 2 m above grade; their 1.2 m Hazus threshold is measured from the platform (flood at 3.2 m above grade). J, placeholder, reasoning: real plants are built above the design flood; Hazus assumes slab on grade.
   - The layout does not change; no node moves.
   Report which facilities flood in which scenarios after this change; do not tune.

3. Lee. Measure it against the smooth spine line of decision 0005, not crest cells: a place is in the lee when the spine line lies between it and the nearest point of the track. A flat island (mountainous 0) has no lee. Post the scenario 0 and scenario 3 previews again.

4. Wooded land takes the town factor, 0.662 (Taiwan wind code and ASCE 7 both class wooded ground with suburbs). Wetland and bare ground stay open, 1.0. L/J.

5. Flood thresholds: refineries 1.2 m (Hazus 4 ft); import terminals 1.2 m (raised quays, J). Freight yards, road junctions, rail nodes and bridges are not flood-damaged in Phase 1.

6. City core = the largest city, as built; to be revisited at real scale (Phase 5).

Choices and the deviation in the PR 6a report are accepted as marked (CHOICE: comments stay), including pits floored at height 0 and per-facility records reading node positions from the layers.

After this commit: explain every golden change, CI green on both platforms, previews posted, then Foreman merges PR #12. Then PR 6b on wo6b/scenarios from main.
