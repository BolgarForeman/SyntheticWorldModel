# 0015 — Emission: the sources, the truth manifest and the hand-trace pack

- **Date:** 2026-10-10
- **Decided by:** the author (Foreman). E1–E8 in the Emission Ruling Sheet v0.2; the main-refill rule; the answers to the Work Order 8 stop.
- **Recorded by:** Work Order 8 (one PR, Parts 0 and A–E)
- **Sources:**
  - `docs/work_orders/WO-08.md` and `docs/work_orders/WO-08-answers.md`;
  - the Emission Ruling Sheet v0.2;
  - structure v0.10 §4.6 and §4.8.

## Context

The world exists only as truth. The pipeline under test reads real-format source files, so the world must be written out as those files:
- with every record traceable to the true element it came from;
- with nothing unobserved leaking into the sources.

The hand trace also needs a printed pack it can check against the engine.

## Decisions

- **Part 0: the main-refill rule.** `reserves.main_refill_rate_fraction` is the rate at which water from the main refills a stock, as a fraction of its drain rate.
  - Default 1.0, range 0.5–1.0, grade J; relaxed means at once.
  - The engine reads it.
- **E1. Separation.**
  - The emission stage (`stages/emission.py`) projects the world onto an `ObservedWorld` that carries only observed quantities.
  - Every writer in `emit/` receives only that world, or the OpenStreetMap objects built from it.
  - The truth manifest reads everything. The trace pack, which needs the engine, sits at the command level.
- **E2. Geometry.**
  - Area classes are drawn as axis-aligned rectangles centred on the true point. Each rectangle's size is drawn per node on its own `emission/footprint/<layer>` stream, within the registry's ranges.
  - Links become ways through their towers or routes.
- **E3. Identifiers.**
  - OpenStreetMap ids start at 9 000 000 000 000, in sorted world-id order.
  - The other sources use reserved codes:
    - WRI: `XSW`, `XSW0000001…`;
    - OurAirports: `XS-0001…`, with no ICAO, IATA or GPS code;
    - the register: `XS` plus eight digits.
  - Every country field is XS or XSW.
- **E4. Names.**
  - Towns are named from the registry's syllables on a per-town stream, drawn again until unique.
  - Facilities are named "<Town> <word>".
  - 20% of each minor class (masts, pumping stations, distribution substations) is left unnamed.
  - Names are English only.
- **E5. Coordinates.** WGS 84 at 7 decimals everywhere. In the register's address column, latitude and longitude stand in for the address.
- **E6. Scored and context attributes** per source, listed in the manifest.
- **E7. The truth manifest** (`truth/manifest.yaml`) holds:
  - the planted errors: none, marked "zero-error emission (Phase 1)";
  - the cross-source correspondence;
  - the true geometry;
  - every unobserved value;
  - the hidden layers and couplings;
  - the declared departures;
  - θ\* as the registry fingerprint plus the Theta List;
  - the seeds and the spawn tree.

  The GIS inspection export gains the true footprints, the towers and the feed routes.
- **E8. Byte identity.** Every emitted file is the same on Windows and Linux:
  - **PBF:** uncompressed blobs;
  - **OSM XML:** fixed metadata, with timestamp 2026-01-01T00:00:00Z, version 1, user `swm` and changeset 1;
  - **shapefiles:** the `.dbf` header date fixed at 2026-01-01;
  - **spreadsheet:** a stored zip with a fixed date;
  - **PDFs:** no compression, no creation date and a fixed producer.

**The answers to the Work Order 8 stop:**
1. **The facility register is three real-style file types, joined on the `XS` institution code:**
   - an institution register modelled on H6 (every facility, an `.ods`);
   - hospital lists modelled on H2–H4 (one CSV per level);
   - a beds table modelled on H1.

   Each copies the real header exactly, with values in English. H5 is left for Phase 6.
2. **OpenStreetMap comes in three forms, all built from the same features:**
   - the PBF extract, with an `.osm` copy;
   - Geofabrik-style free shapefiles: all 18 layers, with Geofabrik's class rules;
   - Overpass-style responses for each query the pipeline runs: hospital, industrial, telecom and the ports check.

   Ports are `landuse=harbour` areas with an `industrial=port` piece inside. The manifest records every element's record in each view.
3. **`machine.toml`** is this repository's own file, gitignored, with `data_root = "C:/Users/brian/Work/Data"`.

## Departures, as declared in the manifest

- Geofabrik's `osm_id` column is C(13), one wider than the real C(12), to hold the reserved 13-digit ids.
- The real WRI file has coordinates at 4 decimals; the world writes 7.
- The three landed Overpass pulls kept no query text, so their queries are inferred from the tags in the real files.
- The register's spreadsheet is named in ASCII; the real file is named in Chinese.
- PBF blobs are uncompressed, which the format allows; Geofabrik compresses its extracts.
- Source overlap is Phase 3: in Phase 1, every true element in a source's scope appears in that source.

## Addendum: the PR 17 answers

- **Date:** 2026-10-10
- **Decided by:** the author (Foreman)
- **Source:** `docs/work_orders/WO-08-pr-answers.md`; structure v0.11 §4.1a and §4.6

**Rulings**

1. **OpenStreetMap ids have 12 digits.** They start at 900,000,000,000, which amends E3. They fit Geofabrik's C(12) `osm_id` field, so the widened field and its declared departure are gone. They are still about 70 times any real id, and the same ids appear in all three OpenStreetMap forms.
2. **Each source is written at its real precision.** This replaces "7 decimals in every source". Rounding is part of the clean emission, not error. The truth manifest stays at 7.

   | Source | Decimals | Basis |
   |---|---|---|
   | OpenStreetMap | 7 | ruled |
   | WRI | 4 | ruled; measured as 4 in every value of the real file |
   | OurAirports | 6 | measured, the most common count worldwide and for Taiwan; trailing zeros dropped, as the real file writes them |
   | Facility register | 6 | CHOICE: the real files carry addresses, so there is nothing to measure. It takes OurAirports' 6, the other point source, about 0.1 m |

   The counts were measured on 2026-10-10 by `tools/check_source_headers.py` through `machine.toml`, and are recorded beside each header in `swm.emit.headers`.
3. **WRI's commissioning year and owner stay empty in Phase 1,** declared as columns the world does not hold. Phase 6 draws them at fill rates measured from the real file.

   Correction: Work Order 8 B2 said the commissioning year comes "from the world"; no such world value exists.
4. **Major facilities are unique by name within their town.** The major groups are plants, transmission substations, hospitals (tertiary and regional together), airports and ports.
   - A repeat takes a direction word from its side of the town centre. The side is found by comparing the absolute east and north offsets and their signs, with no trigonometry.
   - Repeats that share a side are numbered.
   - Minor classes (masts, pumping stations, distribution substations) may share a name.
   - The class split and the direction words are registry placeholders (J): `emission.names.major_classes`, `emission.names.minor_classes` and `emission.names.direction_words`.
   - Choices: the lowest world id keeps the plain name; numbering of a shared side starts at 2; a point exactly on a diagonal counts as east or west.
5. **Every hospital-level file is written in every world,** header-only when a level is empty.

**Verification**
- **osmium:** Linux CI runs `osmium fileinfo -e` on the pilot extract.
- **Overpass:** the hospital, industrial and telecom queries are marked "inferred from landed tags, query text not saved" in the code, in each `.overpassql` and in the manifest. They are replaced when the pipeline supplies the real text.
- **QGIS:** the PyQGIS render is accepted.

**Choices accepted as stated:**
- the tag table;
- the cable landing as `telecom=connection_point`;
- roads as `highway=primary`;
- the port's cargo area at half the harbour's size;
- continent `OC`;
- contract classes 1 and 2;
- statistics month 11412;
- every bed acute and insured;
- "<Town> Thermal Power Station";
- the Geofabrik road flags and place population.

Each stays a placeholder where it sets a number.

**Departures, as now declared:** the list above stands, with these changes:
- the C(13) `osm_id` and the WRI 7 decimals are gone;
- added: the register's 6 decimals, a choice;
- added: the empty WRI columns.
