# Work Order 8: answers to the PR 17 update (apply on this branch before merge)

*2026-10-11 · ruled by Foreman (the author) · apply on `wo8/emission`, then update PR 17 · add to the decision 0015 addendum · spec now v0.12*

## Answers

**1. A repeated group keeps one plain name (question 1).**
- Your reading is the ruling.
- The member with the lowest world id keeps the plain name. Each repeat takes a direction word, then a number if two share a direction.

**2. Every facility type is unique within its town unless it is on the shared-name list (question 2).**
- The default flips: name uniqueness applies to every class except those on a shared-name list.
- The shared-name list holds six classes:
  - masts;
  - pumping stations;
  - distribution substations;
  - water storage tanks;
  - road junctions;
  - fuel depots.
- Every other class takes the direction-word rule when it repeats within a town. That covers exchanges, data centres, cable landings, water works, reservoirs, refineries, tank farms, import terminals, freight yards, bridges, rail nodes, clinics and blood banks, and it keeps the five ruled groups (plants, transmission substations, hospitals, airports, ports).
- A class added later is unique by default.
- **Keep the unnamed share separate.** The 20% unnamed share still applies only to masts, pumping stations and distribution substations (ruling E4).
  - Split `emission.names.minor_classes` into two rules:
    - `emission.names.shared_name_classes`: the six classes above;
    - `emission.names.unnamed_classes`: the three, unchanged.
  - Replace `emission.names.major_classes` with the default-unique logic. Keep the class groups that share a name word, such as hospital (tertiary and regional), as a grouping rule.
  - All are placeholders (J), ruled 2026-10-11, with the old values moved into history.
- **Test:** on the pilot and the 10-node world, no two elements outside the shared-name list share a name within one town, in any source.

**3. Overpass "inferred" mark in the evidence (question 3).**
- The design side has added a line to `docs/design/evidence/Emission_Ruling_Sheet_v0_2.md`. Nothing for you to do.

## Accepted

- **The two extra golden changes:**
  - the register's coordinates at 6 decimals, which follows from ruling 2 (your `CHOICE:` stands);
  - the first comment line of each `.overpassql` file, which follows from the verification item.
- **Your four choices:**
  - the register at 6 decimals;
  - the lowest id keeps the plain name, and numbering starts at 2;
  - a point on a diagonal counts as east or west;
  - hospitals as one naming group.

## Then

1. Apply 2.
2. Regenerate the goldens, and explain every change. Expect only:
   - names of repeated non-shared classes;
   - the registry stamp.
3. Push to PR 17 and report in the §11 format, listing every name that changed in the pilot and in the 10-node world.

Once CI passes, PR 17 is ready to merge.
