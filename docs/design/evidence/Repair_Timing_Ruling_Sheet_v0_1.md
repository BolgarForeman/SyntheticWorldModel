# Repair timing: service restored versus rebuilt: ruling sheet v0.1

*2026-10-22 · design side, for Foreman · to be ruled one item at a time · raised while ruling item 11 of the MIP crew-rules sheet · changes the world, so it is a registry change with a decision record*

## Why this sheet

Foreman, 2026-10-22: "Rebuilding a substation is on the order of months. Getting a substation up and running is done in hours of going down. Days if we have widespread damage and a lot of facilities out at once." And: don't throw the baby out with the bathwater.

The world today has one repair time per facility, and it is the rebuild.
- **Where it comes from.** Every facility draws a repair time from the Hazus MR4 earthquake restoration functions: mean days to restored function, by class and damage state (`repair.hazus_restoration_days`, decision 0011). The crew does 8, 24, 72 or 168 h of work by damage state (`repair.crew_work_h`). Everything else is the "parts lead", which holds no crew: max(0, Hazus time − crew work − 2 h).
- **What it gives in the pilot,** measured from the built world (each node draws its own):

| Damage state | Parts lead, min to max | Median |
|---|---|---|
| Slight | 0–106 h | 9 h |
| Moderate | 0–445 h | 64 h |
| Extensive | 0–2,837 h | 486 h |
| Complete | 30–5,406 h | 1,889 h (about 79 days) |

- **Where it bites.** The pilot's storms damage only lines. Facility jobs come from strikes and criticality runs, at complete damage, so a struck facility is effectively out for the window.
- **The one quick path today:** the mobile units, a mobile substation (distribution substations, 12–24 h including travel) and a mobile cell site (masts, about 14 h). The pilot has one of each. No other class has a quick path (`repair.emergency.other_classes`, ruling T11).

Hazus is the right number for what it measures: the time to get the facility's own function fully back, procurement and rebuilding included. It is the wrong number for what the 72-hour window turns on: when the node gives service again. Utilities get service back through workarounds long before the rebuild:
- switching and rerouting round the damaged equipment;
- temporary repairs with stocked spares;
- mobile units;
- in the worst case, a spare large transformer, moved and energised in 3–4 weeks.

A new large power transformer takes up to 36 months to procure today; before 2020 it was under a year (US DOE, *Large Power Transformer Resilience*, 2024). That is the "months" end, and Hazus can keep it.

## Items to rule

**R1. Two quantities, not one.**
- **A. Keep Hazus as the rebuild; add a separate "service restored" time** (*recommended*).
  - The rebuild stays in the true world and the manifest as now: the facility's full return, usually beyond the window.
  - Service restored is a new, shorter path. The crew arrives, works for the class's service-restore time, and the node then gives service, at full or at a partial share.
  - Whichever path finishes first sets the node's state.
- **Ruled A by Foreman, 2026-10-22.**
- **B. Shorten the Hazus times.** One quantity again, but it would no longer mean what its source measures.
- **C. As now.**

**R2. Slight and moderate damage: is there any parts wait?**
- **A. None.** Repairs at these states use stocked spares, so the job is the 2 h assessment plus crew work (8 h or 24 h) (*recommended*). The Hazus remainder becomes the rebuild record only. A slight hit is then back in about 10 h of crew time, a moderate one in about 26 h.
**Ruled A by Foreman, 2026-10-23.**
- **B. A short regional-stock lead,** a registry placeholder (for example 12 h, like a fuel delivery).
- **C. As now:** the Hazus remainder, median 9 h and 64 h.

**R3. Extensive and complete damage: how does service come back inside the window?**
- **A. Only through a quick path the class has** (*recommended*). That means a mobile unit, rerouting through ties already in the world, or a new temporary-service time for each class that has a credible one. Each class's entry is a registry row with a source, or a judged placeholder.
  - Likely candidates: substations, by temporary bus or bypass, hours to a day; masts, by mobile cell site, as now.
  - Classes without a credible quick path stay out: plants, bridges, refineries, towered lines beyond their 72 h emergency rebuild.
  - A struck plant stays out for the window, which keeps the attack meaningful.
**Ruled A by Foreman, 2026-10-23, with this class table unchanged.** Each row is a "good reason" claim with a placeholder time, to be sourced in the rules review:

| Class | Quick path | Time (placeholder) |
|---|---|---|
| Distribution substation | Mobile substation (as now) | 12–24 h including travel |
| Transmission substation | Temporary bus or bypass, or a transmission-class mobile unit | about 24 h of crew work |
| Mast | Mobile cell site (as now) | about 14 h |
| Pumping station | Portable pumps | about 8 h |
| Water storage | Bypass the tank, pump straight to the network | about 4 h |
| Airport | Rapid runway repair, limited operations | about 24 h |
| Generation, import terminal, tank farm, depot, refinery | None | out for the window |
| Telecom exchange | None (rerouting only where the network has the links) | out |
| Tertiary, regional, clinic, blood bank | None for the building | out |
| Seaport, freight yard, bridge | None | out |
| Reservoir | Unrepairable (as now) | out |

Settled under R4: the new quick paths are crew jobs; only the two mobile units use a pool.

- **B. Give every class a temporary-service time.** Simpler, but it would claim a quick path for plants and bridges that has no basis.
- **C. As now:** only the two mobile units.

**R4. Widespread damage takes days.**
- **A. From contention alone** (*recommended*). Delay comes from the limited crews (2 in the pilot) and mobile units (1 of each), which the engine already models, and from the crew order. Checked later against a realism range: Taipower's restoration curves after typhoons (for example Krathon, 2024), part of the open decision on realism ranges.
**Ruled A by Foreman, 2026-10-23.** The new quick paths (R3) are crew jobs, worked in the default crew order; no new unit pools. The check against Taipower's restoration curves is a Phase 5 realism item.
- **B. Add a shared spares pool** that runs out when many facilities are hit at once. More realistic at study scale, but a new mechanism with no data behind it yet. Deferred to Phase 5 (realism) unless the A check fails.

**R5. What this reopens.** This changes three earlier rulings, so they move into the registry's history with this sheet's decision record:
- ruling T6, that the pilot storm causes only slight and moderate damage because extensive and complete "run for weeks";
- ruling T11, that no other class has an emergency mode;
- decision 0011's split of the Hazus time into crew work and lead.

**Confirmed by Foreman, 2026-10-23.** The pilot storm stays at slight and moderate facility damage; only T6's reason is restated (the storm's results are kept, not because heavy damage would stop crew order mattering).

Item 11 of the MIP sheet (a job opens when its parts arrive) stands for whatever wait remains: the rebuild, and R2 B if chosen.

## After the rulings

- A registry pull request: the new entries, each with its source or placeholder, and the old values moved into history. Decision 0020.
- The spec, §4.4a and §4.5, "Repair and crews": both paths, and which governs.
- The engine-fix PR (E1, E2, item 11) carries the new repair path, since both change the same code. Every reference run, golden and answer key that moves is re-solved and explained. The offensive and criticality keys will move.
- The MIP sheet's C1 and C2 follow the ruled paths.
