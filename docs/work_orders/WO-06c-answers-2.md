# Work Order 6c: second answers to PR 14

*2026-10-09 · ruled by Foreman (the author) · applies to branch `wo6c/power-lines` after commit 022d4d9 · record as a second addendum to decision 0013*

The directional reading worked: the ridge factor's coverage fell from 56% to 31–43% of the land. But a crest is sped up from either side, so the peak gust rose to 135.7 m/s. That is about 40% above Taiwan's highest measured gust. Spec §4.3b is corrected on this branch to match these answers.

## Answers

**1. Put a ceiling on the speed-up (question 1).**
- The factor on wind speed becomes min(1 + K1K2K3, ceiling). It applies to the wind every structure reads.
- The design factor in answer 2 does not take the ceiling.
- **Add the registry rule `storm.ridge_factor_ceiling`:** grade J, status calibrated, overridable from a recipe by name.
- **Calibrate its value:** the ceiling at which the pilot's highest gust at pole height, over its 8 scenarios, equals 95.2 m/s. Report it to 2 decimals and store it.
  - Use the same gust the report's "highest gust" uses: 10-minute wind × factor × gust factor.
  - If the highest gust exceeds 95.2 m/s even with the ceiling at 1, report it and stop.
- **Sources for the rule:**
  - CNA, 2023-10-05, "颱風小犬籠罩蘭嶼陣風逾17級吹壞風速計 破台灣126年紀錄", https://www.cna.com.tw/news/aloc/202310050015.aspx; quote "晚上9時53分蘭嶼氣象站測得陣風為每秒95.2公尺". Taiwan's highest measured gust, breaking a 126-year record.
  - Newtalk, 2023-10-05, https://newtalk.tw/news/view/2023-10-05/891156: Koinu was a moderate typhoon (中度颱風), the pilot's class.
  - The previous Lanyu peak, 89.8 m/s in Typhoon Alex (1984), goes in the reasoning.
- **Reasoning to record:** the code's factor is a design envelope for isolated hills; applied to every crest of a spine it overshoots. The code keeps deciding where the speed-up applies and its shape. The observed record decides how much.

**2. Towers designed for their site defaults to true (question 2).**
- Change `storm.towers_designed_for_site` to true, status ruled. Move false into its history.
- The tower's design factor stays the code's worst-direction factor, without the ceiling: a structure there is designed to the code.

**3. Recalibrate the pole-line median after answers 1 and 2.**
- Rerun `tools/calibrate_line_curve.py` at β 0.4 with the ceiling stored and towers designed for their site.
- Store the best single median that puts the pilot within 5 points of 10%, and severity 70 within 5 points of 30%. Move 201.7763 into the rule's history.
- If no single median meets both windows, store the closest, report it, and stop.

**4. Keep the code's two isolation conditions as two separate tests (question 4).**
- (a) The feature stands more than twice the terrain height within 3.22 km upwind.
- (b) No feature of similar height lies within min(100H, 3.22 km) upwind.
- Both must hold, together with H/Lh ≥ 0.2, the minimum height and the upper half.
- Add a test where (a) fails while (b) holds, and one the other way round.

**5. §4.3b's achieved shares (question 3).** The design side updates the spec after your report. Make no spec edits.

## Report back

**1. The ceiling.**
- Its calibrated value.
- The highest gust, at pole height and at tower height, with the scenario.
- The share of land where the ceiling binds.

**2. Ridge-factor coverage and mean factor per scenario, after the ceiling.**

**3. Towered lines down per scenario, with the setting true, and whether the PR 6b limit holds.**

**4. Line loss.**
- The new median.
- The pilot and severity-70 shares, with each window's result.

**5. Every golden change, explained.**

Then the PR is ready for review to merge.
