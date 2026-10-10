# Work Order 7a: answers to PR 15 (apply in PR 7b)

*2026-10-09 · ruled by Foreman (the author) · PR 15 is merged · apply these on `wo7b/engine` before Parts D–G · record as an addendum to decision 0014*

## Answers

**1. Sources (question 1).** Replace the unverified entries with these. Each was read on 2026-10-09.
- **Data centre make-up water:**
  - Uptime Institute Journal, "Implications of economizers in Tier Certified data centers": https://journal.uptimeinstitute.com/implications-of-economizers-in-tier-certified-data-centers/.
  - Quotes: "a Tier III facility requires 12 hours of Concurrently Maintainable makeup water"; "Many owners have chosen to exceed 12 hours for additional risk avoidance."
  - This is Uptime's own publication. Mark it verified.
- **Purified boiler water:**
  - Bureau of Indian Standards, IS 13268:1992, *Demineralization plant — guidelines*, §4.2.3, archived copy: https://dn790003.ca.archive.org/0/items/gov.in.is.13268.1992/is.13268.1992.html.
  - Quote: "Normally, in power plants clients prefer to have the storage capacity for 16 to 24 hours."
  - Record in the reasoning that it is withdrawn and superseded by the 2023 edition, and that the 1992 text is the one cited.
  - The status stays placeholder until Taiwan's environmental impact statements are read.
- **Seaport dependence on power:**
  - Emerging Risks, "Ports urged to up power outage resilience" (29 January 2026), reporting TT Club: https://www.emergingrisks.co.uk/ports-urged-to-up-power-outage-resilience/.
  - Quotes: "ports are more dependent than ever on electrical systems for cranes, pumps, security, and digital operations"; TT Club recommends ports "Establish robust emergency power and fuel plans, including maintained generators and backup batteries."
  - It is a secondary report of TT Club's guidance; say so.

**2. One stream per line for storm damage (question 2).**
- Each line's damage draws, and each facility's, come from its own child stream, keyed by the scenario index and the element's stable id. Removing or adding an element must not move any other element's draws (CLAUDE.md §4).
- Apply this before the reference runs are saved, and regenerate the scenario goldens.
- Then re-measure the line-loss shares:
  - if the pilot (target 10%) or severity 70 (target 30%) leaves its 5-point window, rerun `tools/calibrate_line_curve.py` and store the best single median, with the old value in history;
  - if no single median meets both, report it and stop.
- Report the tower table again against the PR 6b limit.

**3. Mast-to-mast links (question 3).**
- Work Order 3 B5's allowance is superseded by the 2026-10-09 ruling (decision 0013 audit, Work Order 7 Part 0).
- Record this in decision 0014.

**4. Theta symbols (question 4).** Follow Appendix A v1.7, Definition 2.7:
- **F:** the combining function (the minimum rule). As you have it.
- **g_δ:** the degradation transfer function. Covers the transfer forms and the consumers' failure modes (throttle, trip, floor) and the telecom tolerance form. Move failure modes from h_φ to g_δ.
- **h_φ:** the reserve dynamics family, indexed by commodity. Stocks, refill and resupply.
- **R:** the recovery transfer function (repair, crews, manual switching).
- **γ:** the cascade convergence parameters (the step and the settling cap).
- **χ:** the performance function, an analysis entry.
  - Add one analysis entry: weighted service-hours at end-use nodes, counted as a fraction when supply is partial.
  - The service weights stay outside Θ, as objectives.
- **The storm rules:** no symbol.

Report the corrected counts by sub-type and symbol.

**5. Pump capacity (question 5).**
- Expose the pumping capacity the requirements stage already sizes as a registry limit: relaxed value unlimited, range open.
- The engine uses it as the pumps' maximum delivery. Storage refills from what remains after serving demand.
- If the requirements stage does not size pump capacity, report it rather than inventing a value.

**6. Overrides outside a ruled range (your CHOICE, accepted).**
- A recipe may set a limit outside its ruled range, so sensitivity runs can go beyond it.
- When it does, the resolved recipe and every run record a note naming the rule, the value and the range.

## Then

Build Parts D–G of `docs/work_orders/WO-07.md` on this branch, and open PR 7b into main. Report it in the §11 format with the items Work Order 7 lists, plus:
- the corrected Theta counts;
- the line-loss shares after answer 2;
- the pump capacity values.
