# Work Order 9b: answers, PR 23 (apply on this branch before merge)

*2026-10-19 · design side; question 2 ruled by Foreman (the author) · apply on `wo9b/goldens`, push to PR 23 · spec now v0.15*

## Review

- **Stop check:** passed. Both fixture worlds equal the pilot in every stage hash, the manifest's true world and all 8 reference runs.
- **Hidden couplings:** accepted as built. A coupling is listed as hidden when it is switched off or either end's layer is hidden; each keeps its `switched_on` flag, so the two kinds stay distinct. Record it as a `CHOICE:` in the code and in decision 0017 (it is world-neutral and manifest-only).
- **`withheld_links`:** accepted.
- **E2:** accepted; the remote is the same repository.

## Answers

1. **The error streams' seed (design side).** Yes, that is the intended reading. The spec has one root seed; error streams are keyed by their own stable names (structure §1, CLAUDE.md §4). There is no separate error-seed field, and none is to be added. C1 reseeds the `errors/` streams; it holds trivially in Phase 1 and bites from Phase 3. Say so in the test's docstring.

2. **The area a file says it covers (ruled by Foreman, option A).** Fixed by the terrain, never by what is emitted.
   - An OpenStreetMap extract's bounds (`.osm` `<bounds>`, `.pbf` header box) and every Overpass query's search area are the world's whole map area: the smallest latitude and longitude box holding the terrain grid's four corners, at the file's precision (7 decimals).
   - Hiding a layer or withholding links must move nothing in any other file.
   - Unchanged: a shapefile's header box and an Overpass element's own `bounds` stay the extent of what that file or element holds, as the real formats define them.
   - Alternatives recorded in the spec: the island's land plus a margin; the extent of what was emitted.
   - Spec v0.15 §4.6 carries the ruling (committed on this branch). Add it to decision 0017.

## Apply

1. Change the extract bounds and the Overpass search areas to the map area.
2. Test: in each fixture world, the `.osm` bounds, the `.pbf` header box and every Overpass search area equal the pilot's.
3. Regenerate the goldens and explain every change. The pilot's bounds and query areas change once. Nothing in the world moves.
4. Push, confirm CI green on both platforms, report.
