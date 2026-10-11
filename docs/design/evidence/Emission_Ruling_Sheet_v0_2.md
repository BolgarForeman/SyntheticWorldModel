# Emission: ruling sheet v0.2 (ruled)

*2026-10-10 · ruled by Foreman, one item at a time · prerequisite to SyntheticWorldModel Work Order 8 · supersedes v0.1*

**As ruled:** E1–E3 and E5–E8 as recommended below. E2 adds that the manifest keeps every true outline and route (see E7). E4 is changed: names are plain, pronounceable invented names (for example "Corvan", "Telmar", "Brenna Point"), not the fantasy-style names first floated. A borrowed fictional world was rejected (rights, collisions with real namesakes, too few names), and so were fantasy-style invented names (hard to say, and unserious in briefings). Leaks are flagged by the identifiers, not the names.

## What this is

Work Order 8 writes the world out as source files: one set per source switched on, in the source's real container, schema and idioms (spec §4.6). Each world also gets its truth manifest (§4.8) and a printable pack for the pilot's hand trace (§6). Phase 1 emits with zero error; error induction comes in Phase 3. So these files are the clean emission that Phase 3 corrupts and that the pipeline must ingest.

The pilot switches on seven sources:

| Layer | Sources | Nodes only |
|---|---|---|
| Power | OpenStreetMap, WRI Global Power Plant Database | no |
| Telecom | OpenStreetMap | no |
| Water | OpenStreetMap | no |
| Transport | OpenStreetMap, OurAirports | no |
| Fuel | OpenStreetMap | yes |
| Healthcare | OpenStreetMap, government facility register | yes |

The real pipeline (MCIN_Pipeline) ingests:
- a Geofabrik OpenStreetMap extract (`taiwan-251128`, PBF);
- the WRI database CSV;
- OurAirports `airports.csv`;
- address-only registers that wait on a geocoder (Trust Holding Bin TB-6).

The emitted files should look to the pipeline like those.

## The rulings

**E1. OpenStreetMap as one extract.**
- All switched-on OpenStreetMap sources go into one `.osm.pbf` file for the island, as a Geofabrik extract does. That is not one file per layer.
- Each source's scope decides which features it contributes, and its own error settings apply to those features in Phase 3.
- Written with pyosmium (BSD-2), with fixed timestamps, version 1, and one synthetic user and changeset.
- An `.osm` XML copy is written alongside for reading by eye.
- Recommended.

**E2. Points or areas.**
- Real OpenStreetMap maps most facilities as areas: plants, substations, hospitals, water works, ports, airports, tank farms and refineries.
- Masts, clinics and fuel depots are often single points.
- Recommendation: emit the classes usually mapped as areas as closed ways with a footprint, and the rest as nodes.
  - Footprints are rectangles sized by class from registry placeholders (J), drawn per node.
  - The facility's true location is the centroid.
- Power lines are ways through `power=tower` nodes, with voltage and circuit tags. Links in other layers on emitted layers are ways too (`man_made=pipeline`, telecom `communication=line`, water `man_made=pipeline` + `substance=water`). Node-only layers emit no links.
- Recommended.

**E3. Identifiers.**
- OpenStreetMap ids from a reserved high range starting at 9,000,000,000,000, far above any real id, so a synthetic object can never be mistaken for a real one.
- The country is ISO 3166's user-assigned code: `XS` / `XSW`, "Synthetic World".
- WRI: `gppd_idnr` as `XSW0000001`…, with country `XSW`, country_long "Synthetic World".
- OurAirports: `ident` as `XS-0001`… (OurAirports' own form for airfields without an ICAO code). No ICAO or IATA codes, `iso_country` `XS`, `iso_region` `XS-01`….
- Recommended.

**E4. Names.**
- Real sources carry names, and name matching is part of how sources are joined.
- Ruled: invent plain, pronounceable town names from a fixed list of soft syllables in the registry, then name facilities by town and class, in the source's own style. For example, OpenStreetMap "Valmera Substation", and the register's longer formal name.
- No real place names, ever.
- Sources may name the same asset differently, as real ones do. In Phase 1 the difference is only style; Phase 3 adds name errors.
- Recommended.

**E5. The facility register: address or coordinates.**
- Taiwan's real register gives addresses, not coordinates, and the pipeline needs a geocoder for it.
- Options:
  - **A.** Emit coordinates in the register's columns (a declared simplification).
  - **B.** Emit synthetic addresses and a synthetic gazetteer to geocode them against.
- Recommendation: A for Phase 1, declared in the manifest; B in Phase 6 (source fidelity), when the pipeline's geocoder exists.

**E6. Scored and context attributes.**

Each source marks which attributes count toward the error rate (§4.7). Recommended scored set:
- location;
- class or type;
- capacity (MW, beds, m³/day, as the source carries it);
- voltage on lines.

Name, operator, dates, and the long tail of tags are context. They are emitted, may be corrupted, but are not scored.

**E7. The truth manifest.**
- Includes the true geometry: every outline's corners and centre, every line's route and tower points, and the feeds' routes (ruled with E2).
- One YAML file per world (plus the existing GeoPackage inspection export) holding the §4.8 list:
  - the cross-source correspondence (which records in which files are the same true element);
  - every unobserved value with its target and levers;
  - hidden layers and couplings;
  - scored and context lists;
  - θ\* by registry hash, and the Theta List;
  - seeds and the spawn tree.
- In Phase 1 the planted-error list is empty, and says so.
- Recommended.

**E8. The printable hand-trace pack.**
- A one-page map: nodes with ids, lines, couplings switched on, the crew base and the storm track.
- Plus tables:
  - nodes with class and stocks;
  - dependencies with κ and failure mode;
  - scenario 7's damage list and reference-run timeline.
- Written as a PDF with fixed metadata (byte-identical), and the tables also as CSV.
- Recommended.

## Decided without a ruling

- Coordinates are WGS 84, rounded to 7 decimals (§4.1a).
- Files are sorted and written with fixed formatting, so the identity check covers them.
- Emission code receives only observed quantities. The separation test is extended to every writer.
- A zero-error emission is the clean emission. The property test "zero error reproduces the clean emission" waits for Phase 3.

## Also ruled for Work Order 8

**Later phases:** bilingual names; synthetic addresses with a gazetteer and the pipeline's geocoder (Phase 6).


**Refill rate of water stocks from the main** (ruled 2026-10-10):
- default: the rate it drained;
- range: half that rate (twice as long) to the same rate;
- relaxed value: instant refill.

## Note added 2026-10-11

- **Overpass views.** The pipeline saved no query text for its hospital, industrial and telecom Overpass pulls. The generator's queries for those three were inferred from the tags in the landed files, and are marked "inferred from landed tags, query text not saved" in the code, in each `.overpassql` and in the manifest. The ports query is the pipeline's own. Replace the three when the pipeline side supplies the real text.
