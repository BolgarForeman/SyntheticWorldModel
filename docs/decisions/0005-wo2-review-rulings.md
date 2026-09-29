# 0005 — Work Order 2 review rulings

- **Date:** 2026-09-28
- **Decided by:** the design conversation, confirmed by Foreman
- **Recorded by:** the Work Order 2 revision (pull request #3)
- **Full text:** `docs/work_orders/WO-02-review.md`

## Context

The design review of pull request #3 found the code, tests and cross-platform identity sound. It asked for face-validity fixes to the ground before any layer is sited on it, and answered the four questions in the Work Order 2 report. While building the revision, the code side found that R4 and R5.4 conflict for a north-south spine, and Foreman ruled on it.

## Decisions

- **R1 Wetland.** Wetland forms only on low, flat ground near river mouths and on coastal lowland, in patches rather than a continuous fringe. Its share still rises with lowland and wetland.
- **R2 Rivers.** Rivers read as dendritic drainage:
  - channels gather in valleys and join before the sea;
  - both flanks drain from near the ridge;
  - the network at river density 40 is visibly denser than before.

  Rivers are drawn above the land cover in the preview.
- **R3 Coastline.** Coastline complexity 0 may be smooth; 50 shows bays and headlands; 100 is strongly indented. It is tested as a monotonic response of coastline length ÷ the perimeter of an equal-area circle.
- **R4 Domain.** Land fills about 35% of the domain, keeping a sea border wide enough for the outlying islands.
- **R5.1 Grid.** Fixed at 256 × 256 for all of Phase 1; revisited at Phase 5.
- **R5.2 Base relief.** Maximum elevation = 100 m + mountainous/100 × 3,900 m. The 4,000 m ceiling is unchanged; the floor keeps drainage meaningful at every setting.
- **R5.3 Minimum town.** Every world has at least one town. At urban density 0, one minimum town is placed, with the validation note "urban density 0: one minimum town placed so siting has an anchor". Its size (1 km²) is a CHOICE.
- **R5.4 Proportions.** The spine island's length-to-width ratio is 3 : 1. It is a generic island type, not Taiwan.
- **R4 against R5.4: the spine runs diagonally.** For Phase 1, the spine runs north-west to south-east.
  - A north-south 3 : 1 island can fill at most about 22–25% of a square domain.
  - The diagonal lets both the shape and the land share hold in the square grid.
  - The orientation carries no meaning in a synthetic world; it was chosen for that reason alone.

  Ruled by Foreman, 2026-09-28.
- **R6 Preview.** The legend moves outside the map. The scale bar, caption statistics and city outlines stay.
- **R7 Small items.**
  - Square roots are taken with `math.sqrt` or `numpy.sqrt` (correctly rounded under IEEE), not `** 0.5`.
  - `src/swm/preview.py` joins the `CLAUDE.md` §5 layout.
  - The stale "Superseded content" paragraph is removed from `docs/design/README.md`: the one design-document edit authorised.
