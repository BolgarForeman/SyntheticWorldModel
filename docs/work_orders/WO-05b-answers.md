WORK ORDER 5, PR 5b (#9) — ANSWERS (design side, 2026-09-29, confirmed by Foreman)

Apply these as one follow-up commit on wo5b/buffers, before merge. Record them as a second addendum to docs/decisions/0010. Every value changed in modeling_rules.yaml moves its old value into history, citing decision 0010.

1. Delivery rate of stores: confirmed. A store delivers its volume ÷ the days of stock it holds. Fuel depot 3 days and reservoir 365 days stand, status placeholder, grade J, to be revisited with the realism ranges.

2. Energy content: confirmed. LNG 22.5 GJ/m³ and coal 20 GJ/m³ stand. Add a published source for each to its registry entry (for example the IEA or EIA conversion factors), with the quote. If no source can be fetched, keep the value, mark it placeholder, and say so in the report.

3. Generator reliability: confirmed. Use Marqusee & Jenket's own figures:
   - well maintained: fails to start 0.13%, mean time to failure 1,662 h;
   - poorly maintained: 1.65%, 61 h.
   The share of generators well maintained stays 1.0 by default, status placeholder, and becomes a recipe-overridable rule. A lower share is a sensitivity run later, not the default: a poorly maintained set fails on average at 61 h, inside the 72 h window.

4. Mast and clinic diesel generators: set the diesel standby share to 0 for both. This matches §4.4a (clinics have no generator by default; masts carry the Taiwan 4 h battery). The "no fuel target" notes go away. Explain the golden change.

5. Designated disaster-response masts: the share stays 0 until a source gives a count. Status open, with that reasoning.

6. Default compliance gap for classes §4.4a does not list:
   - blood banks and cable landings take the recipe's reserves gap (30% default), status placeholder;
   - the national LNG, oil and coal stocks take a gap of 0. They are statutory stockholding obligations reported to the government, and a 30% default shortfall would contradict their S grade. Record this as its own registry rule, with that reasoning.

7. Missing telecom tolerance rows: add both, grade J, status placeholder:
   - airport, not towered: T = 24 h, d = 0.8. Flights run on radio; telecom loss mainly hits bookings and fuel orders;
   - tank farm, not pipeline-connected (truck-fed): T = 12 h, d = 0.6, the same as a fuel depot, which works the same way.
   Add both rows to spec §4.4a in the same commit (docs/design/World_Generator_Structure.md, noted as an addition of 2026-09-29 under decision 0010).

The coder's seven choices in the PR 5b report are accepted as marked (CHOICE: comments stay).

After this commit: CI green on both platforms, then Foreman merges PR #9. Then the terrain island-count fix as its own pull request, then PR 5c.
