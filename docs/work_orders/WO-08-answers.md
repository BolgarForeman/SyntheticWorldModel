# Work Order 8: answers to the pre-build stop

*2026-10-10 · ruled by Foreman (the author) · applies to branch `wo8/emission` · record in decision 0015*

The stop was right. Two premises in Emission Ruling Sheet v0.2 were wrong:
- the pipeline lands no single facility register with codes and addresses;
- it ingests no OpenStreetMap PBF.

Spec v0.10 §4.6 is corrected on this branch to match these answers.

## Answers

**1. The facility register is three real-style file types, joined on the institution code (question 1).**

| Emitted file | Modelled on | Rows | Columns |
|---|---|---|---|
| Institution register | H6, the health ministry's institution register | every healthcare facility (hospitals, clinics, blood banks) | H6's header: institution code, name, county and district, specialties and the rest. Latitude and longitude replace the address |
| Hospital lists, one file per level | H2–H4, the national health insurance hospital lists | hospitals only; the level is which list a hospital is in (medical centre, regional, district) | H2–H4's header: code, name, type, contract class. Latitude and longitude replace the address |
| Beds table | H1 | one row per hospital | H1's header: beds by institution code |

- **Institution codes** are register-style with an `XS` prefix, the same code across all three file types, so the pipeline's join on the code is exercised.
- **Column headers** are copied exactly from the real files the pipeline lands, in Chinese where the real ones are. Values are in English.
- **Scored for this source:** location, class, level and beds, as ruled in E6.
- **Left out:** H5, the emergency-hospitals PDF the pipeline extracts. It comes in Phase 6 with source fidelity, along with addresses and a gazetteer.

**2. OpenStreetMap in three forms, built from the same synthetic features (question 2).**
- **The canonical extract:** `island.osm.pbf`, with `island.osm` beside it, as Work Order 8 Part A specifies.
- **Geofabrik-style free shapefiles:**
  - for the layers the pipeline reads from Geofabrik's `taiwan-…-free` set (roads, points of interest, and the rest it uses);
  - same layer names, file names and attribute columns as the real set on disk;
  - only the classes Geofabrik's free set really carries.
- **Overpass-style GeoJSON:** one file per query the pipeline actually runs (power, telecom, water, industrial, ports and any others in its saved queries), in the same response structure.
  - Use each saved query's tag filter to decide which features the file holds.
  - Use the ports tag families from the pipeline's ports check: `landuse=harbour` areas with `industrial=port` pieces inside.
- **One set of features, several views.** A feature may appear in one view, several, or the PBF only, exactly as its tags would place it in the real files.
- **The truth manifest** records every element's id or record in each view.
- **Identity on both platforms.** Shapefiles store a date in the `.dbf` header: fix it, and confirm the files are byte-identical on Windows and Linux.
- **What to copy and from where:** layer names, columns and query texts are schema, not data. Copy them from the real files on disk and from the pipeline repository, record their source and version in code, and report them.

**3. `machine.toml` (question 3).**
- Create this repository's own `machine.toml`, gitignored, with `data_root = "C:/Users/brian/Work/Data"`.
- `machine.example.toml` stays as the checked-in template.

## Then

Build Work Order 8 Parts 0 and A–E with these answers, and open one PR into main. Report in the §11 format with everything Work Order 8 lists, plus:
- the Geofabrik layer list and the Overpass queries reproduced;
- the three register headers.
