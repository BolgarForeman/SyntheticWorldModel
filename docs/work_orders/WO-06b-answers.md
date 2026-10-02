WORK ORDER 6, PR 6b (#13) — ANSWERS (design side, 2026-10-02, confirmed by Foreman)

Apply these as one follow-up commit on wo6b/scenarios, before merge. Spec §4.3b on this branch is updated to match. Record them as a second addendum to docs/decisions/0012. Every changed registry value moves its old value into history, citing decision 0012.

Context: at severity 50 the pilot lost 53–75% of its overhead line length in every scenario, far beyond real storms (about a third of Taipower customers lost power in Soudelor 2015, a strong typhoon, many through trips cleared without a crew). Three causes: each line was judged by its single peak gust; the design side's per-km anchor (J) was too severe; and the gust factors in §4.3b were wrong.

1. Lines by the kilometre. Each km of a pole line fails or survives at its own local 3-second gust; a line is down if any of its kilometres fails. Each failed kilometre is a failure point. Record per line: failure points and where they are.

2. Calibrate the pole curve. Keep β 0.3 as a placeholder shape. Set the median so that, averaged over each recipe's scenarios:
   - the pilot (severity 50) loses about 10% of overhead line length;
   - the severity-70 fixture loses about 30%.
   This is a declared calibration, not silent tuning: record the targets, the resulting median and the reasoning in the registry (grade J; anchor: targets sit below observed outage shares because many outages clear without a crew). Move the old anchor (0.05 per km at 45 m/s) into history. If one median cannot hit both targets within ±5 percentage points, report both results and the spread that would; do not change β yourself.

3. Gust factors. Correct to Harper, Kepert & Ginger (2010), WMO guidelines, Table 1.1, 10-minute to 3-second: 1.38 at the coast ("off-sea", onshore winds at a coastline) and 1.66 inland ("in-land", roughly open terrain). Keep your 1 km ramp between them. Fetch the table and quote it in the registry entry. Source: https://www.systemsengineeringaustralia.com.au/download/WMO_TC_Wind_Averaging_27_Aug_2010.pdf

4. Towers keep reading the peak gust against the Fani curve. Report how often towered lines fail per scenario after answers 1–3. Rare failures at pilot severity are acceptable; if more than one towered line fails in more than two of the eight scenarios, report it and stop.

5. Lines from transmission to distribution substations run on towers (J, Taipower practice to check later). This adds to your towers-or-poles CHOICE.

6. Repair per failure point (Foreman's ruling). Crew work = 6 h × the line's failure points, no lead time, plus road travel from the crew base to the line's midpoint. In Phase 1 one line is one job for one crew; splitting a line across crews comes later. A towered line that collapses counts as one failure point for now (tower repair times are open; flag it in the report).

The coder's other choices in the PR 6b report are accepted as marked (straight feeds, travel to the midpoint, one damage stream per scenario, the facility_damage_cap control without a version bump).

Report per scenario after the commit: lines down, failure points, km down, towered lines down, and the scenario mean line-length share for both recipes. Explain every golden change. CI green on both platforms, then Foreman merges PR #13.
