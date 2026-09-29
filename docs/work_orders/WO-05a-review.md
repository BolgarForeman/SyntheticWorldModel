WORK ORDER 5, PR 5a — REVIEW AND ANSWERS (design side, 2026-09-29, confirmed by Foreman)

Status: revise on this pull request (#7) before merge. The registry, the Modeling Rules page and the requirements stage are what was asked for. The page shows 301 rules: 78 ruled, 215 placeholder, 8 open.

Make one follow-up commit on this branch covering the items below. Record the answers in docs/decisions/0010-wo5a-answers.md.

0. CI fix. Lint fails on both platforms, so the tests never ran in CI. The failures are three docstring errors in tools/build_quantile_table.py:
   - D401 on solve();
   - D103 on main();
   - one more D-rule on a helper near line 66.
   Fix them and confirm the full suite passes in CI.

1. Size ports and airports to the city they serve (world content).
   - The seaport and airport size class follows the size of the city they serve: its urban footprint relative to the world's cities, scaled from the Taiwan anchors. It is not "largest city gets the largest class".
   - The pilot should come out with a small port and a small airport. Put the mapping from footprint to class in the registry, marked placeholder with its reasoning.
   - Report the pilot's new seaport and airport loads.

2. Size generation to all load (world content).
   - Total generation capacity = total peak load of every power consumer, distribution-fed and transmission-fed alike, × the reserve margin (1.3), converted with the power factor.
   - This replaces sizing from distribution substation capacity only.
   - Transmission substations must carry at least the load they feed.
   - Report the pilot's new generation figure.

3. Every rule is overridable by a recipe. Each override is listed beside the registry hash in the resolved recipe and stamped on the world. Remove the per-rule "overridable" restriction; keep the stamp.

4. Add placeholder targets, grade J, for the fuel draws of airports (jet fuel, scaled by passenger throughput), seaports (bunkers and cargo-handling diesel, scaled by container throughput) and freight yards (diesel, scaled by area). Mark each as a placeholder with reasoning. PR 5b needs them for coupling strength.

5. Confirmed as reported:
   - Transport access is served or not, like telecom.
   - Rows that already name a transmission substation keep it below the threshold (refinery, LNG terminal), because the dependency table names it from evidence.
   - A tertiary hospital large enough for rule 4 stays single-fed when the world has only one transmission substation. Record a note.
   - Unsourced sizes (data centre IT load, refinery crude run, LNG send-out, water at fuel facilities) stay as placeholders marked open.

6. Failure-mode heterogeneity: set the recipe default to 10%. The spec governs; the 30% predates the ruling. You may do this here or in PR 5b; say which.

7. Retire the unused Work Order 1 stream unobserved/requirements, and state the stream_record change.

8. Interface mockup: no change now. The new recipe fields (distribution_voltage_kv, modeling_rules) are logged for the Phase 7 interface.

Regenerate every golden file that changes, explain each change in the pull request, and report the pilot's edge count.
