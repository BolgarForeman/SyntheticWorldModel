# Work Order 8: answers to PR 17 (apply on this branch before merge)

*2026-10-10 · ruled by Foreman (the author) · apply on `wo8/emission`, then update PR 17 · record as an addendum to decision 0015 · spec now v0.11*

## Answers

**1. OpenStreetMap ids: 12 digits (question 1).**
- Start the ids at 900,000,000,000, not 9,000,000,000,000.
  - They then fit Geofabrik's 12-character `osm_id` field exactly, so the shapefiles need no departure. Remove the widened field and its declared departure.
  - They are still about 70 times above any real id, so leak protection holds.
- The same ids appear in all three OpenStreetMap forms.
- This amends ruling E3. Update decision 0015, the id test (≥ 9e11, unique, sorted), and the spec reference (now v0.11 §4.6).

**2. Coordinates at each source's real precision (question 2).**
- **OpenStreetMap:** 7 decimal places.
- **WRI:** 4 decimal places.
- **OurAirports and the facility register:** measure the decimal counts from the real files in the same local check you ran on the headers (through `machine.toml`). Record each count beside its recorded header, with the check's date.
  - The register's coordinates are our declared departure, so state the precision you chose for it and why. It is a `CHOICE:`.
- **The truth manifest** stays at 7 decimals.
- **Rounding is part of the clean emission, not error** (spec v0.11 §4.1a). Make two changes:
  - The correspondence test compares each emitted location with the true one within that source's rounding (half a unit in the last decimal place), not exactly.
  - The outline-centre test does the same.
  - Note this in the TRACE entry so the Phase 3 realized-error check measures against the clean, rounded file.

**3. WRI commissioning year and owner stay empty (question 3).**
- Leave both columns empty in Phase 1 and declare them in the manifest's departures list ("columns the world does not hold").
- Phase 6 draws them at fill rates measured from the real file.
- Work Order 8 B2 was wrong to say the commissioning year comes "from the world": no such world value exists. Note the correction in decision 0015.

**4. Unique names for major facilities, shared names allowed for minor ones (question 4).**
- **Major classes:** plants, transmission substations, hospitals, airports and ports. Two of the same class in one town must not share a name.
  - Each repeat takes a direction word (North, South, East, West) from its position relative to the town centre. Pick it by comparing the absolute east and north offsets and their signs. Use comparisons only, with no trigonometry (CLAUDE.md §4).
  - If two land in the same direction, number them in sorted world-id order ("Selimere North Substation 2").
  - Apply this in every source's naming style.
- **Minor classes:** masts, pumping stations and distribution substations. They may share a name, as now.
- Put the major/minor class split and the direction words in the registry as placeholders (J), ruled 2026-10-10.
- **Test:** no two major facilities of the same class in one town share a name in any source, on the pilot and the 10-node world.

**5. A level with no hospitals is a file holding only its header (question 5).**
- Write all three hospital-level files in every world. An empty level is a valid CSV holding only its header row.
- **Test:** the file set under `sources/` is the same for every fixture world.

## Your choices: accepted as stated

- **OpenStreetMap:**
  - the tag table;
  - the cable landing as `telecom=connection_point`;
  - roads as `highway=primary`;
  - the port's cargo area at half the harbour's size.
- **OurAirports:** continent `OC`.
- **Register:**
  - contract classes 1 and 2;
  - statistics month 11412;
  - every bed acute and insured.
- **WRI:** the name form "<Town> Thermal Power Station".
- **Geofabrik:** the road flags and the place population.

All of these stay as placeholders where they set a number. Each is listed in decision 0015.

## Verification items

- **osmium.** Work Order 8 A5 asks that the extract open in osmium. Add one step to the Linux CI job:
  - install `osmium-tool` from the distribution's packages;
  - run `osmium fileinfo -e` on the pilot build's `island.osm.pbf`;
  - fail if it errors.

  Report its output in the PR. Windows needs nothing.
- **Overpass queries.** You inferred the hospital, industrial and telecom queries from the tags in the landed files, because the query text was not saved. Mark them in the code and the evidence file as "inferred from landed tags, query text not saved". I will ask the pipeline side for the real query text, and they will be replaced when it arrives.
- **QGIS image.** A PyQGIS render is acceptable.

## Then

1. Apply 1–5 and the verification items on this branch.
2. Regenerate the goldens.
3. Explain every golden change. Expect only:
   - ids;
   - WRI coordinate rounding;
   - the major-facility names;
   - the registry stamp;
   - the hand-trace pack, where it shows ids or names.

   Anything else is reported, not accepted.
4. Push to PR 17 and report in the §11 format, including:
   - the measured decimal counts per source;
   - the osmium output;
   - the names that changed in the pilot.
