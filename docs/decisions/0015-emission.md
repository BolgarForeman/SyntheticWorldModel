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
