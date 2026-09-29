WORK ORDER 2 — REVIEW AND REVISION (design side, 2026-09-28, confirmed by Foreman)

Status: revise on this pull request (#3) before merge. The code, tests and cross-platform identity are sound: CI passes on Windows and Linux, the design documents are untouched, and every mapping is in one table as asked. The revisions below are face-validity fixes to the ground itself. Siting reads rivers, wetlands, coast and cities, so they are settled now rather than after layers are built on them.

Record the rulings in docs/decisions/0005-wo2-review-rulings.md. Mapping changes are CHOICE-level. Say in the pull request which golden hashes changed and why, then regenerate the preview.

R1 Wetland. Wetland currently forms a thin ring around the whole coast. That reads as an artefact, not a landscape. Wetland should occur only in low, flat cells near river mouths and on coastal lowlands, and in patches, not as a continuous fringe. Its share still rises with lowland and wetland. Test it: at the pilot settings, most coastal land cells are not wetland, and wetland cells cluster near river mouths.

R2 Rivers. The river network is connected in the data (accumulation only grows downstream), but the preview shows straight, parallel east–west runs. That is the usual D8 artefact on smooth planar slopes. Rivers should read as dendritic drainage:
  - channels gather in valleys and join before reaching the sea;
  - both flanks of the spine drain from near the ridge;
  - at river density 40 on this island, the network is visibly denser than 53 km.
Give the surface enough small-scale relief that flow converges; the method is yours, within A8. Draw rivers above the land-cover colours in the preview so no reach appears to stop short of the coast. Add a test that the number of river mouths is well below the number of river cells touching the coast in parallel runs; pick a robust statistic and state it.

R3 Coastline. At coastline complexity 50 the shore is too smooth. It should show some bays and headlands. At 0 it may be smooth; at 100 it should be strongly indented. Keep the monotonic-response test pattern and add this index to it, using a measure such as coastline length ÷ the perimeter of a circle of equal area.

R4 Domain margin. Land is about 15% of the domain, so most cells are sea. Tighten the domain so land fills about 35% of it, keeping a sea border wide enough for the outlying islands. This improves resolution at no cost (pilot cells fall to roughly 130 m).

R5 Answers to your questions:
  1. Grid: keep a fixed 256 × 256 for all of Phase 1. With R4, the small preset's cells are about 300 m, which is adequate for 20 nodes per layer. Revisit at Phase 5.
  2. Base relief: yes. Maximum elevation = 100 m + mountainous/100 × 3,900 m. A flat island has no drainage, so a floor keeps rivers meaningful at every setting. The 4,000 m ceiling is unchanged.
  3. Cities: every world has at least one town. At urban density 0, place one small town and add a validation note ("urban density 0: one minimum town placed so siting has an anchor").
  4. Proportions: the spine island's length-to-width ratio becomes 3 : 1. It is a generic island type, not Taiwan.

R6 Preview. Move the legend outside the map; it currently hides the second outlying island. Otherwise it's good: scale bar, caption statistics and city outlines all stay.

R7 Small items:
  - Replace `** 0.5` with an explicit square root (math.sqrt or numpy.sqrt), which IEEE guarantees to be correctly rounded; a power function is not guaranteed.
  - Add src/swm/preview.py to the CLAUDE.md §5 layout.
  - Remove the stale "Superseded content" paragraph from docs/design/README.md. It refers to the pilot spec's old closing section, which v0.4 already dropped. This one edit is authorised.

Acceptance: as in Work Order 2, plus the tests above. Post the regenerated preview in the pull request so the author can look again before merging.
