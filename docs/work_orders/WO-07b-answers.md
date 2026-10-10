# Work Order 7b: answers to the paused report

*2026-10-10 · ruled by Foreman (the author) · applies to branch `wo7b/engine` after commit 3ca3a8e · record as a second addendum to decision 0014*

The stop was correct. With one stream per element, the pilot's realized line-loss share moved from 7.8% to 4.1% at the same median: the curve did not change, the draws did. With 8 scenarios and a handful of lines, the realized share is dominated by which kilometres happen to fail, so fitting the median to it fits the dice. The engine work is accepted, with the corrections below.

## Answers

**1. Calibrate to the expected line loss (question 1).**
- The calibration target is the **expected** share of overhead line length lost, not one realized draw:
  - for each scenario and each line, take 1 − Π(1 − p_km) over its kilometres, where p_km is the kilometre's failure probability from the stored curve at its gust (towers by their own curve, with the site factor as now);
  - weight by line length;
  - divide by total overhead line length;
  - average over the scenarios.
- The arithmetic is + − × ÷ only, from the stored tables, with no random draws.
- Change `tools/calibrate_line_curve.py` to measure this. Find the single median at β 0.4 that puts the pilot's expected share within 5 points of 10% and severity 70's within 5 points of 30%.
- Store it, with 163.7317 moved into history. Status: calibrated.
- Record in the rule's reasoning that the targets apply to the expected share.
- Report, for both recipes:
  - the expected share;
  - the realized share beside it;
  - the tower table against the PR 6b limit.
- If no single median meets both windows on the expected share, report it and stop.
- Spec §4.3b is updated on this branch.

**2. The engine's choices (question 2).** Nine stand as built:
- feed groups as in the undisturbed supply check;
- own-layer supply rebuilt each pass;
- telecom response R + (1 − R) × tolerance level;
- battery before generator;
- shortfall-share drain, with a hospital on its floor drawing its full essential load;
- own-layer response at the class default with no draw;
- failure points worked in order along the line;
- repairs take effect at the next step;
- sea trips as straight distance plus mobilisation.

Record each in decision 0014 as ruled. Three change:
- **Pump capacity is shared pro rata by demand,** not split equally. This is the pro rata rule of §4.5 for links inside a layer. Storage refills from what remains.
- **A missed fuel delivery goes out as soon as it can:** at the first step at which the depot is up and a road reaches the consumer. The schedule then continues every `delivery_h` from that delivery.
- **Hospital water refills from the main** once supply returns, like purified and make-up water. Supplies and blood still need deliveries, and do not refill inside the window.

**3. Generation fuel (question 3).** The profile was wrong, not the code.
- LNG and oil plants trip on a fuel cut: their stocks are held at the terminal and the tank farms.
- Coal plants run on their own 30-day pile.
- Use `docs/design/evidence/Degradation_Profiles_v0_3.md` (on this branch) and make the tests follow it.

**4. Airport fuel (question 4).** Pipeline-fed airports trip; truck-fed airports throttle. Profiles v0.3 says so. Keep both tests.

## Then

Finish PR 7b as Work Order 7 Parts E–G describe:
- save the 8 reference runs with the new median as goldens;
- write decision 0014's second addendum and the TRACE note;
- open the PR into main.

Report in the §11 format with:
- the expected and realized line-loss shares;
- the tower table;
- the E3 summary table for the saved runs;
- the scenario 7 timeline;
- the test counts.
