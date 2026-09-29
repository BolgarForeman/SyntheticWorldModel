WORK ORDER 4, PR 4b — REVIEW AND ANSWERS (design side, 2026-09-29, confirmed by Foreman)

Status: revise on this pull request (#6) before merge. CI is green on both platforms. The pilot lands at 49 edges with nothing tuned, and the narrowed supplier lists match the ruling. Make one follow-up commit on this branch covering the four answers below, and add them to docs/decisions/0008-wo4-answers.md.

1. Two-way against a core dependency. Never leave a core dependency without a supplier in order to satisfy the two-way setting.
   - When breaking a mutual pair would leave a core dependency unsupplied, keep the mutual pair and record a note ("mutual pair kept: no other eligible supplier").
   - Report realised mutual pairs against the setting.
   - An optional dependency may still be dropped with a note, as now.
   - On the pilot, the distribution substation keeps its telecom control feed, and the resulting substation–exchange loop stays. It is the power–telecom coupling Appendix B calls the sharpest single coupling, and it belongs in the hand trace.
   - Add a test: at two-way 0, no core dependency is ever left without a supplier.
   - Regenerate the pilot golden files and the schematic, and state the edge-count change in the pull request.

2. Mutual pairs among hidden couplings. Confirmed: count them among hidden (generated but switched off) pairs too, so that hiding a coupling changes only its switched_on flag. Hidden couplings are part of the true world.

3. The schematic, for the hand trace:
   - Give each node label a pale background (the page colour at high opacity) so arrows never obscure it.
   - Print every switched-on coupling edge as a table beside or below the schematic: edge id, supplier (id and class), consumer (id and class), dependency type, feed configuration, role.
   - Also write that table as couplings_edges.csv (sorted by edge id, fixed formatting) from `swm couplings`.
   - It is for inspection and stays outside the identity check.

4. The four unused couplings/* streams registered in Work Order 1: retire them and record why in decision 0008. Streams are keyed by name, so no other stream moves. State the stream_record change in the pull request.

Also accepted as reported:
- backs_dependency is null when the power pair backing it is not generated;
- two-way 100 is measured against the achievable set of mutual pairs;
- the eight CHOICE items listed in the report stand for now.
